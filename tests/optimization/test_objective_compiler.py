import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from utopia.optimization.loss import evaluate_loss, validate_loss_spec
from utopia.optimization.objective_compiler import (
    canonical_sha256,
    compile_objective,
    load_objective_spec,
    load_validated_metric_registry,
    metric_card_sha256,
    validate_metric_registry,
    validate_objective_spec,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/objective-constitution"
OBJECTIVE_PATH = FIXTURES / "objective-spec.synthetic-test.json"
REGISTRY_PATH = FIXTURES / "validated-metric-cards.synthetic-test.json"
EXPECTED_PATH = FIXTURES / "compiled-losses.expected.synthetic-test.json"
OBJECTIVE_SCHEMA_PATH = ROOT / "research/specs/objective-spec-v1.schema.json"
REGISTRY_SCHEMA_PATH = ROOT / "research/specs/validated-metric-card-registry-v1.schema.json"
COMPILATION_SCHEMA_PATH = ROOT / "research/specs/objective-compilation-v1.schema.json"


def inputs():
    objective_schema = json.loads(OBJECTIVE_SCHEMA_PATH.read_text(encoding="utf-8"))
    registry_schema = json.loads(REGISTRY_SCHEMA_PATH.read_text(encoding="utf-8"))
    objective = load_objective_spec(OBJECTIVE_PATH, OBJECTIVE_SCHEMA_PATH)
    registry = load_validated_metric_registry(REGISTRY_PATH, REGISTRY_SCHEMA_PATH)
    return objective, registry, objective_schema, registry_schema


def compiled():
    objective, registry, objective_schema, registry_schema = inputs()
    return compile_objective(
        objective,
        registry,
        objective_schema=objective_schema,
        registry_schema=registry_schema,
        evidence_root=ROOT,
    )


def test_synthetic_fixture_compiles_to_deterministic_phase_loss_specs():
    result = compiled()
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    compilation_schema = json.loads(COMPILATION_SCHEMA_PATH.read_text(encoding="utf-8"))

    assert list(Draft202012Validator(compilation_schema).iter_errors(result)) == []
    assert result["schema"] == "scienceutopia.objective-compilation.v1"
    assert result["status"] == "synthetic-test-only"
    assert result["hard_constraints"] == []
    assert result["objective_spec"]["sha256"] == expected["objective_spec_sha256"]
    assert result["metric_registry"]["sha256"] == expected["metric_registry_sha256"]
    assert len(result["compiled_phases"]) == 2
    for actual, wanted in zip(result["compiled_phases"], expected["phases"], strict=True):
        loss = actual["loss_spec"]
        validate_loss_spec(loss)
        assert actual["phase"]["id"] == wanted["id"]
        assert actual["loss_spec_sha256"] == wanted["loss_spec_sha256"]
        assert loss["per_run"]["intercept"] == wanted["intercept"]
        assert {term["metric_id"]: term["coefficient"] for term in loss["per_run"]["terms"]} == wanted["coefficients"]


def test_normative_choices_remain_visible_in_receipt_not_hidden_constraints():
    result = compiled()
    objective, _, _, _ = inputs()

    assert result["tradeoffs"] == objective["tradeoffs"]
    assert result["goodhart_audit"] == objective["goodhart_audit"]
    assert result["measurement_evidence_policy"] == objective["measurement_evidence_policy"]
    assert result["constitution_summary"]["governance"] == objective["governance"]
    assert result["constitution_summary"]["time_horizon"] == objective["time_horizon"]
    assert result["constitution_summary"]["distribution"] == objective["distribution"]
    assert all(phase["component_receipts"] for phase in result["compiled_phases"])
    assert all(receipt["measurement_evidence_refs"] for phase in result["compiled_phases"] for receipt in phase["component_receipts"])
    assert all("hidden vetoes" in phase["loss_spec"]["interpretation"] for phase in result["compiled_phases"])


def test_compiled_loss_specs_execute_with_existing_loss_evaluator():
    result = compiled()
    evaluations = [
        {
            "run_id": f"synthetic-{seed}",
            "metrics": {
                "synthetic-verified-progress-index": {"status": "measured", "value": 0.8},
                "synthetic-review-lifecycle-cost": {"status": "measured", "value": 0.2},
            },
        }
        for seed in (1, 2, 3)
    ]
    explore = evaluate_loss(result["compiled_phases"][0]["loss_spec"], evaluations)
    consolidate = evaluate_loss(result["compiled_phases"][1]["loss_spec"], evaluations)
    assert explore["status"] == "complete"
    assert explore["loss"] == pytest.approx(-0.3)
    assert consolidate["loss"] == pytest.approx(-0.55)


def test_compilation_is_reproducible_and_uses_no_current_campaign_probe():
    first = compiled()
    second = compiled()
    assert canonical_sha256(first) == canonical_sha256(second)
    rendered = json.dumps(first, sort_keys=True)
    for forbidden in (
        "participation-review-tradeoff-probe",
        "topic-diversity-probe",
        "review-burden-probe",
        "active-researcher-fraction",
        "topic-entropy",
    ):
        assert forbidden not in rendered


def test_unvalidated_metric_card_is_rejected():
    objective, registry, objective_schema, registry_schema = inputs()
    invalid = copy.deepcopy(registry)
    invalid["cards"][0]["status"] = "report-only"
    objective["components"][0]["metric_card_ref"]["sha256"] = metric_card_sha256(invalid["cards"][0])
    with pytest.raises(ValueError, match="not validated for optimization"):
        compile_objective(objective, invalid, objective_schema=objective_schema, registry_schema=registry_schema, evidence_root=ROOT)


def test_metric_card_hash_mismatch_is_rejected():
    objective, registry, objective_schema, registry_schema = inputs()
    invalid = copy.deepcopy(objective)
    invalid["components"][0]["metric_card_ref"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        compile_objective(invalid, registry, objective_schema=objective_schema, registry_schema=registry_schema, evidence_root=ROOT)


def test_missing_required_measurement_scope_is_rejected():
    objective, registry, objective_schema, registry_schema = inputs()
    invalid = copy.deepcopy(registry)
    invalid["cards"][0]["evidence_refs"].remove("progress-reliability")
    objective["components"][0]["metric_card_ref"]["sha256"] = metric_card_sha256(invalid["cards"][0])
    with pytest.raises(ValueError, match="lacks evidence scopes"):
        compile_objective(objective, invalid, objective_schema=objective_schema, registry_schema=registry_schema, evidence_root=ROOT)


def test_measurement_artifact_hash_is_verified():
    objective, registry, objective_schema, registry_schema = inputs()
    invalid = copy.deepcopy(registry)
    invalid["evidence"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        compile_objective(objective, invalid, objective_schema=objective_schema, registry_schema=registry_schema, evidence_root=ROOT)


def test_measurement_artifact_cannot_escape_declared_root():
    objective, registry, objective_schema, registry_schema = inputs()
    invalid = copy.deepcopy(registry)
    invalid["evidence"][0]["artifact"] = "../outside-evidence.json"
    with pytest.raises(ValueError, match="escapes the evidence root"):
        compile_objective(objective, invalid, objective_schema=objective_schema, registry_schema=registry_schema, evidence_root=ROOT)


def test_hard_constraint_and_implicit_single_objective_phase_fail_closed():
    objective, _, objective_schema, _ = inputs()
    constrained = copy.deepcopy(objective)
    constrained["hard_constraints"] = [{"metric": "synthetic-floor"}]
    with pytest.raises(ValueError, match="expected"):
        validate_objective_spec(constrained, objective_schema)

    single = copy.deepcopy(objective)
    single["components"][1]["weights"][0]["value"] = 0.0
    with pytest.raises(ValueError, match="at least two positive tradeoff components"):
        validate_objective_spec(single, objective_schema)


def test_broken_references_and_non_adversarial_goodhart_evidence_fail_closed():
    objective, registry, objective_schema, registry_schema = inputs()
    bad_objective = copy.deepcopy(objective)
    bad_objective["constructs"][0]["stakeholder_refs"].append("missing-party")
    with pytest.raises(ValueError, match="unresolved references"):
        validate_objective_spec(bad_objective, objective_schema)

    bad_registry = copy.deepcopy(registry)
    bad_registry["evidence"][1]["scope"] = "construct-validity"
    with pytest.raises(ValueError, match="not adversarial-validity"):
        validate_metric_registry(bad_registry, registry_schema)


def test_fixture_is_explicitly_synthetic_and_future_only():
    objective, registry, _, _ = inputs()
    evidence = json.loads((FIXTURES / "measurement-evidence.synthetic-test.json").read_text(encoding="utf-8"))
    assert objective["status"] == "prospective-future-campaign"
    assert objective["governance"]["active_campaign_effect"] == "none"
    assert objective["measurement_evidence_policy"]["promotion_boundary"] == "future-campaign-only"
    assert registry["status"] == "prospective-synthetic-test-only"
    assert evidence["status"] == "synthetic-test-only-not-empirical-validation"
