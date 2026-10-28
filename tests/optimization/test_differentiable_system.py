from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from utopia.optimization.differentiable_system import (
    DifferentiableSystemSpace,
    QuadraticAnalyticSurrogate,
    load_differentiable_design,
    optimize_relaxed,
    run_synthetic_proof,
    validate_differentiable_design,
)
from utopia.optimization.objective_compiler import (
    compile_objective,
    load_objective_spec,
    load_validated_metric_registry,
)
from utopia.system import validate_system_spec


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/differentiable-system-design/design.synthetic-test.json"
DESIGN_SCHEMA = ROOT / "research/specs/differentiable-system-design-v0.schema.json"
REPORT_SCHEMA = ROOT / "research/specs/differentiable-system-design-report-v0.schema.json"
OBJECTIVE_FIXTURES = ROOT / "tests/fixtures/objective-constitution"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _compiled_objective() -> dict:
    objective_schema_path = ROOT / "research/specs/objective-spec-v1.schema.json"
    registry_schema_path = (
        ROOT / "research/specs/validated-metric-card-registry-v1.schema.json"
    )
    objective = load_objective_spec(
        OBJECTIVE_FIXTURES / "objective-spec.synthetic-test.json",
        objective_schema_path,
    )
    registry = load_validated_metric_registry(
        OBJECTIVE_FIXTURES / "validated-metric-cards.synthetic-test.json",
        registry_schema_path,
    )
    return compile_objective(
        objective,
        registry,
        objective_schema=_json(objective_schema_path),
        registry_schema=_json(registry_schema_path),
        evidence_root=ROOT,
    )


def _inputs() -> tuple[dict, dict, dict, dict]:
    design = load_differentiable_design(FIXTURE, DESIGN_SCHEMA)
    schema = _json(DESIGN_SCHEMA)
    compilation = _compiled_objective()
    loss = compilation["compiled_phases"][0]["loss_spec"]
    return design, schema, compilation, loss


def test_design_is_whole_system_prospective_and_not_an_active_campaign_input():
    design, _, _, _ = _inputs()
    families = {item["family"] for item in design["system_template"]["mechanisms"]}

    assert design["status"] == "prospective-synthetic-proof-only"
    assert design["active_campaign_effect"] == "none"
    assert {
        "research",
        "evaluation",
        "publication",
        "funding",
        "governance",
        "communication",
    } <= families
    serialized = json.dumps(design, sort_keys=True)
    assert "held_out" not in serialized
    assert "metric-conditioned-v1.1" not in serialized


def test_analytic_pullback_matches_finite_difference_for_all_variable_kinds():
    design, _, _, _ = _inputs()
    space = DifferentiableSystemSpace(design)
    surrogate = QuadraticAnalyticSurrogate(design["surrogate"])
    raw = space.initial_raw()
    prediction = surrogate.predict_and_gradient(space.features(raw))
    analytic = space.pullback(raw, prediction.feature_gradient)
    epsilon = 1e-6

    representatives = [
        "parameter:research:exploration-rate",
        "presence-logit:evaluation",
        "implementation-logit:evaluation:open",
        "edge-logit:research-evaluation",
    ]
    for raw_id in representatives:
        plus, minus = dict(raw), dict(raw)
        plus[raw_id] += epsilon
        minus[raw_id] -= epsilon
        plus_loss = surrogate.predict_and_gradient(space.features(plus)).mean
        minus_loss = surrogate.predict_and_gradient(space.features(minus)).mean
        numerical = (plus_loss - minus_loss) / (2.0 * epsilon)
        assert analytic[raw_id] == pytest.approx(numerical, rel=1e-5, abs=1e-6)


def test_gradient_inner_loop_reduces_synthetic_surrogate_loss():
    design, _, _, _ = _inputs()
    space = DifferentiableSystemSpace(design)
    result = optimize_relaxed(
        space,
        QuadraticAnalyticSurrogate(design["surrogate"]),
        design["inner_optimizer"],
    )

    assert len(result["trace"]) == design["inner_optimizer"]["iterations"] + 1
    assert result["trace"][0]["raw_gradient_norm"] > 0
    assert result["trace"][-1]["surrogate_mean"] < result["trace"][0]["surrogate_mean"] * 0.1


def test_projection_is_deterministic_valid_and_removes_dangling_edges():
    design, _, _, _ = _inputs()
    space = DifferentiableSystemSpace(design)
    raw = space.initial_raw()
    raw["presence-logit:governance"] = -10.0
    raw["edge-logit:governance-funding"] = 10.0

    first = space.project(raw)
    second = space.project(raw)
    validate_system_spec(first.system_spec).require_valid()
    assert first.system_spec.fingerprint == second.system_spec.fingerprint
    assert "governance-core" not in {
        mechanism.mechanism_id for mechanism in first.system_spec.mechanisms
    }
    decision = next(
        item
        for item in first.decisions
        if item["kind"] == "edge-projection"
        and item["id"] == "governance-funding"
    )
    assert decision["selected"] is False
    assert decision["reason"] == "dangling-endpoint-force-absent"


def test_synthetic_end_to_end_report_preserves_outer_validation_and_audits():
    design, schema, compilation, loss = _inputs()
    report = run_synthetic_proof(design, schema, compilation, loss)
    report_errors = list(
        Draft202012Validator(_json(REPORT_SCHEMA)).iter_errors(report)
    )

    assert report_errors == []
    initial = report["outer_validation"]["records"]["initial"]
    optimized = report["outer_validation"]["records"]["optimized"]
    assert optimized["black_box"]["loss"] < initial["black_box"]["loss"]
    assert optimized["black_box"]["loss_spec_sha256"] == design[
        "objective_binding"
    ]["loss_spec"]["sha256"]
    assert optimized["system_fingerprint"] == optimized["black_box"]["system_fingerprint"]
    assert report["outer_validation"]["relaxation_projection_gap"] >= 0
    assert report["outer_validation"]["protocol"]["data_role"] == (
        "synthetic-development-validation-not-confirmatory"
    )
    assert report["audit"]["observed_goodhart_flags"] == report[
        "outer_validation"
    ]["goodhart_flags"]
    assert "validated policy optimum" in report["audit"]["prohibited_claims"]


def test_objective_and_loss_bindings_fail_closed():
    design, schema, compilation, loss = _inputs()
    wrong_compilation = copy.deepcopy(compilation)
    wrong_compilation["status"] = "changed"
    with pytest.raises(ValueError, match="compilation hash mismatch"):
        run_synthetic_proof(design, schema, wrong_compilation, loss)

    wrong_loss = compilation["compiled_phases"][1]["loss_spec"]
    with pytest.raises(ValueError, match="LossSpec binding hash mismatch"):
        run_synthetic_proof(design, schema, compilation, wrong_loss)


@pytest.mark.parametrize(
    "mutate, message",
    [
        (
            lambda value: value["surrogate"]["targets"].pop(
                "edge:research-evaluation"
            ),
            "targets must cover exactly",
        ),
        (
            lambda value: value["surrogate"].__setitem__(
                "conditioned_loss_sha256", "0" * 64
            ),
            "different LossSpec",
        ),
        (
            lambda value: value["system_template"]["edges"][0].__setitem__(
                "source_port", "missing"
            ),
            "unresolved source",
        ),
    ],
)
def test_semantic_validation_rejects_incomplete_or_unresolved_designs(
    mutate, message
):
    design = _json(FIXTURE)
    mutate(design)
    with pytest.raises(ValueError, match=message):
        validate_differentiable_design(design, _json(DESIGN_SCHEMA))


def test_projection_instability_audits_discrete_boundaries_not_continuous_rounding():
    design, schema, compilation, loss = _inputs()
    report = run_synthetic_proof(design, schema, compilation, loss)
    sensitive = report["outer_validation"]["projection_instability"][
        "sensitive_raw_ids"
    ]

    assert all(not raw_id.startswith("parameter:") for raw_id in sensitive)
    assert report["outer_validation"]["projection_instability"][
        "sensitive_fraction"
    ] <= 1.0
