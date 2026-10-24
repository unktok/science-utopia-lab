import json
from pathlib import Path

import pandas as pd

from utopia.optimization.metric_constitution import load_metric_constitution
from utopia.optimization.objective_evaluator import (
    evaluate_run,
    summarize_evaluations,
    write_evaluation,
)


ROOT = Path(__file__).resolve().parents[2]
CONSTITUTION = ROOT / "research/specs/example-metric-constitution-v1.json"


def _artifacts(tmp_path, *, native_passed=True):
    run_id = "run-1"
    docs = tmp_path / "docs" / run_id
    checkpoints = tmp_path / "checkpoints" / run_id
    docs.mkdir(parents=True)
    checkpoints.mkdir(parents=True)
    agents = []
    for year in (1, 2):
        for index in range(10):
            agents.append({
                "agent_id": f"r{index}", "year": year,
                "is_active": not (year == 2 and index == 9),
            })
    pd.DataFrame(agents).to_parquet(docs / "agent_year.parquet", index=False)
    pd.DataFrame([
        {"year": 1, "topic_entropy": 0.5, "occupied_directions": 2},
        {"year": 2, "topic_entropy": 0.8, "occupied_directions": 3},
    ]).to_parquet(docs / "ecosystem_year.parquet", index=False)
    (docs / "integrity_checks.json").write_text(json.dumps([
        {"year": 1, "passed": native_passed, "failures": [] if native_passed else ["bad"]}
    ]))
    (checkpoints / "funding_application_trace_year_1.summary.json").write_text(
        json.dumps({"passed": True, "failures": []})
    )
    (checkpoints / "checkpoint_year_2.json").write_text(json.dumps({
        "yearly_results": [
            {"peer_review": {"score_metrics": {"total_reviews": 4}}},
            {"peer_review": {"score_metrics": {"total_reviews": 6}}},
        ]
    }))
    return run_id


def test_evaluates_vector_without_treating_unknown_slice_as_pass(tmp_path):
    run_id = _artifacts(tmp_path)
    constitution = load_metric_constitution(CONSTITUTION)

    result = evaluate_run(run_id=run_id, output_root=tmp_path, constitution=constitution)

    assert result["hard_constraints"][0]["state"] == "pass"
    assert len(result["evaluator"]["implementation_sha256"]) == 64
    assert result["run_provenance"]["source_commit"] is None
    assert result["metrics"]["active-researcher-fraction"]["value"] == 0.9
    assert result["metrics"]["topic-entropy"]["value"] == 0.8
    burden = result["metrics"]["review-burden-per-active-researcher"]
    assert burden["value"] == 10 / 19
    assert burden["slice_results"]["low-resource-researchers"]["status"] == "unknown"
    assert result["capabilities"][0]["state"] == "unknown"
    assert result["comparison_eligibility"] == "unknown"
    assert result["objective_vector"][0]["status"] == "partial"
    assert result["objective_vector"][0]["values"] == {
        "active-researcher-fraction": 0.9
    }
    path = write_evaluation(result, tmp_path)
    assert json.loads(path.read_text())["schema"] == "scienceutopia.objective_evaluation.v1"


def test_failed_hard_constraint_makes_run_infeasible(tmp_path):
    run_id = _artifacts(tmp_path, native_passed=False)
    result = evaluate_run(
        run_id=run_id, output_root=tmp_path,
        constitution=load_metric_constitution(CONSTITUTION),
    )
    assert result["hard_constraints"][0]["state"] == "fail"
    assert result["comparison_eligibility"] == "infeasible"


def test_known_capability_failure_is_not_masked_by_unknown_slice(tmp_path):
    run_id = _artifacts(tmp_path)
    docs = tmp_path / "docs" / run_id
    agents = pd.read_parquet(docs / "agent_year.parquet")
    agents.loc[agents["year"] == 2, "is_active"] = False
    agents.to_parquet(docs / "agent_year.parquet", index=False)

    result = evaluate_run(
        run_id=run_id, output_root=tmp_path,
        constitution=load_metric_constitution(CONSTITUTION),
    )

    assert result["capabilities"][0]["state"] == "fail"
    assert result["comparison_eligibility"] == "infeasible"


def test_design_readiness_enforces_minimum_runs_and_unknown_capability(tmp_path):
    run_id = _artifacts(tmp_path)
    constitution = load_metric_constitution(CONSTITUTION)
    evaluation = evaluate_run(run_id=run_id, output_root=tmp_path, constitution=constitution)
    rows = [{"run_id": run_id, "design_id": "d1"}]

    summary = summarize_evaluations([evaluation], rows, constitution)[0]

    assert summary["run_count"] == 1
    assert summary["required_minimum_runs"] == 5
    assert summary["authorized_for_ranking"] is False
    assert summary["metric_summaries"]["active-researcher-fraction"]["mean"] == 0.9
    assert any("at least 5" in reason for reason in summary["blocking_reasons"])
    assert any("unknown" in reason for reason in summary["blocking_reasons"])
