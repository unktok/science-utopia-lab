import json
from pathlib import Path

import pytest

from utopia.optimization.loss import (
    evaluate_loss,
    load_loss_spec,
    loss_spec_sha256,
    validate_loss_spec,
)


ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "research/objectives/losses/engineering-continuity-demo-v1.json"


def evaluation(run_id, participation, burden):
    return {
        "run_id": run_id,
        "metrics": {
            "active-researcher-fraction": {
                "status": "measured",
                "value": participation,
                "slice_results": {},
            },
            "review-burden-per-active-researcher": {
                "status": "measured",
                "value": burden,
                "slice_results": {},
            },
        },
    }


def test_demo_loss_is_versioned_and_hash_stable():
    spec = load_loss_spec(SPEC_PATH)

    assert spec["status"] == "engineering_demo"
    assert spec["direction"] == "minimize"
    assert loss_spec_sha256(spec) == loss_spec_sha256(json.loads(json.dumps(spec)))


def test_loss_aggregates_valid_runs_without_constraints_or_vetoes():
    spec = load_loss_spec(SPEC_PATH)
    result = evaluate_loss(spec, [
        evaluation("r1", 0.8, 2.0),
        evaluation("r2", 0.9, 3.0),
        evaluation("r3", 1.0, 2.0),
    ])

    assert result["status"] == "complete"
    assert result["valid_runs"] == 3
    assert result["rejected_runs"] == []
    assert result["mean"] == pytest.approx((0.3 + 0.25 + 0.1) / 3)
    assert result["loss"] >= result["mean"]


def test_unmeasured_metric_rejects_run_instead_of_inventing_penalty():
    spec = load_loss_spec(SPEC_PATH)
    incomplete = evaluation("missing", 0.9, 2.0)
    incomplete["metrics"]["active-researcher-fraction"]["status"] = "unknown"
    result = evaluate_loss(spec, [
        evaluation("r1", 0.8, 2.0),
        evaluation("r2", 0.9, 3.0),
        incomplete,
    ])

    assert result["status"] == "insufficient_valid_runs"
    assert result["loss"] is None
    assert result["rejected_runs"][0]["run_id"] == "missing"


def test_loss_spec_rejects_duplicate_inputs_and_maximize_direction():
    spec = load_loss_spec(SPEC_PATH)
    spec["direction"] = "maximize"
    spec["per_run"]["terms"].append(dict(spec["per_run"]["terms"][0]))

    with pytest.raises(ValueError, match="direction.*duplicate"):
        validate_loss_spec(spec)
