from __future__ import annotations

import json
from pathlib import Path

import pytest

from utopia.optimization.continuum import (
    DesignFreedom,
    OptimizationCoordinate,
    SearchMethod,
    continuum_capability_map,
    mutable_raw_ids,
    run_black_box_episode,
    run_differentiable_episode,
    run_hybrid_episode,
)
from utopia.optimization.differentiable_system import (
    DifferentiableSystemSpace,
    QuadraticAnalyticSurrogate,
    SyntheticBlackBoxEvaluator,
    load_differentiable_design,
)
from utopia.optimization.objective_compiler import (
    compile_objective,
    load_objective_spec,
    load_validated_metric_registry,
)


ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "tests/fixtures/differentiable-system-design/design.synthetic-test.json"
DESIGN_SCHEMA = ROOT / "research/specs/differentiable-system-design-v0.schema.json"
OBJECTIVE_FIXTURES = ROOT / "tests/fixtures/objective-constitution"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _inputs():
    design = load_differentiable_design(DESIGN, DESIGN_SCHEMA)
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
    compilation = compile_objective(
        objective,
        registry,
        objective_schema=_json(objective_schema_path),
        registry_schema=_json(registry_schema_path),
        evidence_root=ROOT,
    )
    loss = compilation["compiled_phases"][0]["loss_spec"]
    space = DifferentiableSystemSpace(design)
    surrogate = QuadraticAnalyticSurrogate(design["surrogate"])
    evaluator = SyntheticBlackBoxEvaluator(
        space, design["objective_binding"]["loss_spec"]["sha256"]
    )
    return design, space, surrogate, evaluator, loss


def test_design_freedom_is_nested_and_independent_from_search_method():
    _, space, _, _, _ = _inputs()
    parameters = set(mutable_raw_ids(space, DesignFreedom.PARAMETERS))
    mechanisms = set(
        mutable_raw_ids(space, DesignFreedom.MECHANISM_CONFIGURATION)
    )
    structure = set(mutable_raw_ids(space, DesignFreedom.GRAPH_STRUCTURE))

    assert parameters < mechanisms < structure
    assert all(item.startswith("parameter:") for item in parameters)
    assert any(item.startswith("implementation-logit:") for item in mechanisms)
    assert any(item.startswith("presence-logit:") for item in structure)
    assert any(item.startswith("edge-logit:") for item in structure)
    assert OptimizationCoordinate(
        DesignFreedom.PARAMETERS, SearchMethod.BLACK_BOX
    ).to_dict() == {
        "design_freedom": "parameters",
        "search_method": "black-box",
    }
    with pytest.raises(ValueError, match="declared frontier"):
        OptimizationCoordinate(
            DesignFreedom.OPEN_ENDED_SYSTEM, SearchMethod.BLACK_BOX
        )


@pytest.mark.parametrize(
    "freedom",
    [
        DesignFreedom.PARAMETERS,
        DesignFreedom.MECHANISM_CONFIGURATION,
        DesignFreedom.GRAPH_STRUCTURE,
    ],
)
def test_gradient_search_only_changes_variables_exposed_by_freedom(freedom):
    design, space, surrogate, evaluator, loss = _inputs()
    report = run_differentiable_episode(
        space=space,
        freedom=freedom,
        surrogate=surrogate,
        optimizer_config={**design["inner_optimizer"], "iterations": 8},
        evaluator=evaluator,
        loss_spec=loss,
        scenarios=design["outer_validation"]["scenarios"],
    )
    initial = report["inner"]["initial_raw"]
    optimized = report["inner"]["optimized_raw"]
    mutable = set(report["mutable_raw_ids"])

    assert any(optimized[key] != initial[key] for key in mutable)
    assert all(
        optimized[key] == initial[key] for key in set(space.raw_ids) - mutable
    )
    assert report["projected"]["outer_evaluation"]["system_fingerprint"] == report[
        "projected"
    ]["system_fingerprint"]


def test_black_box_structure_search_is_result_dependent_and_uses_common_projection():
    design, space, _, evaluator, loss = _inputs()
    report = run_black_box_episode(
        space=space,
        freedom=DesignFreedom.GRAPH_STRUCTURE,
        evaluator=evaluator,
        loss_spec=loss,
        scenarios=design["outer_validation"]["scenarios"],
        seed=41,
        budget=4,
        initial_random=2,
    )

    assert report["coordinate"] == {
        "design_freedom": "graph-structure",
        "search_method": "black-box",
    }
    assert len(report["records"]) == 4
    assert report["records"][2]["suggestion"]["phase"] == "adaptive"
    assert report["records"][2]["suggestion"]["based_on_observation_id"]
    for record in report["records"]:
        projected = record["projected"]
        assert projected["system_fingerprint"] == projected["outer_evaluation"][
            "system_fingerprint"
        ]
        assert projected["coordinate"] == report["coordinate"]


def test_hybrid_uses_gradient_center_then_black_box_feedback_without_bypassing_outer():
    design, space, surrogate, evaluator, loss = _inputs()
    report = run_hybrid_episode(
        space=space,
        freedom=DesignFreedom.GRAPH_STRUCTURE,
        surrogate=surrogate,
        optimizer_config={**design["inner_optimizer"], "iterations": 8},
        evaluator=evaluator,
        loss_spec=loss,
        scenarios=design["outer_validation"]["scenarios"],
        seed=91,
        black_box_budget=3,
    )

    assert report["gradient_initializer"]["final_surrogate_loss"] < report[
        "gradient_initializer"
    ]["initial_surrogate_loss"]
    assert report["black_box"]["records"][0]["suggestion"]["phase"] == "initial"
    assert report["black_box"]["records"][2]["suggestion"]["phase"] == "adaptive"
    assert all(
        record["projected"]["outer_evaluation"]["status"] == "complete"
        for record in report["black_box"]["records"]
    )


def test_capability_map_marks_open_ended_synthesis_as_a_real_gap():
    _, space, _, _, _ = _inputs()
    capability = continuum_capability_map(space)

    assert capability["axes"] == {
        "design_freedom": "what the optimizer may change",
        "search_method": "how proposals are generated",
    }
    assert capability["rows"][-1]["freedom"] == "open-ended-system"
    assert capability["rows"][-1]["status"] == "declared-frontier-not-implemented"
    assert "schedule" in capability["known_gap"]


def test_explicit_technical_failure_never_becomes_a_numeric_penalty():
    design, space, _, _, loss = _inputs()

    class FailedEvaluator:
        def evaluate(self, system, loss_spec, scenarios):
            return {
                "status": "failed",
                "loss": None,
                "system_fingerprint": system.fingerprint,
                "reason": "synthetic technical failure",
            }

    report = run_black_box_episode(
        space=space,
        freedom=DesignFreedom.PARAMETERS,
        evaluator=FailedEvaluator(),
        loss_spec=loss,
        scenarios=design["outer_validation"]["scenarios"],
        seed=13,
        budget=1,
    )

    observation = report["records"][0]["observation"]
    assert observation["status"] == "failed"
    assert observation["loss"] is None
    assert report["best_loss"] is None

