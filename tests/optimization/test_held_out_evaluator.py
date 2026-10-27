import json

import pandas as pd
import pytest

from utopia.optimization.held_out_evaluator import evaluate_common_suite


def test_native_held_out_evaluator_completes_common_diagnostics(tmp_path):
    run_id = "held-out-1"
    docs = tmp_path / "docs" / run_id
    checkpoints = tmp_path / "checkpoints" / run_id
    docs.mkdir(parents=True)
    checkpoints.mkdir(parents=True)

    pd.DataFrame([
        {"year": 1, "num_submissions": 2},
        {"year": 2, "num_submissions": 1},
    ]).to_parquet(docs / "ecosystem_year.parquet", index=False)
    pd.DataFrame([
        {"paper_id": "p1", "accepted": True},
        {"paper_id": "p2", "accepted": False},
        {"paper_id": "p3", "accepted": False},
    ]).to_parquet(docs / "paper.parquet", index=False)
    pd.DataFrame([
        {
            "event_id": f"e{index}", "year": 1 + index // 4,
            "paper_id": f"p{1 + index // 2}", "reviewer_id": f"r{index % 4}",
        }
        for index in range(5)
    ]).to_parquet(docs / "review_action.parquet", index=False)
    pd.DataFrame([
        {"agent_id": "r0", "year": 1, "is_active": True},
        {"agent_id": "r1", "year": 1, "is_active": True},
        {"agent_id": "r0", "year": 2, "is_active": True},
        {"agent_id": "r1", "year": 2, "is_active": False},
    ]).to_parquet(docs / "agent_year.parquet", index=False)

    counts = {
        "targets": 2, "validated": 2, "submitted": 2,
        "declined_by_agent": 0, "dropped": 0, "evaluated": 2,
        "decided": 2, "funded": 1, "allocations_recorded": 1,
        "allocations_applied": 1, "generation_attempts": 2,
        "semantic_invalid_attempts": 0, "sanitized_reference_attempts": 0,
        "request_error_attempts": 0,
    }
    (checkpoints / "funding_application_trace_year_1.summary.json").write_text(
        json.dumps({"year": 1, "passed": True, "counts": counts}), encoding="utf-8"
    )
    ledger = {
        "transactions": [
            {"category": "grant_income", "delta": 20.0},
            {"category": "industry_income", "delta": 5.0},
        ],
        "years": {
            "2": {
                "r0": {"closing_balance": 30.0},
                "r1": {"closing_balance": 10.0},
            }
        },
    }
    (checkpoints / "checkpoint_year_2.json").write_text(
        json.dumps({
            "resource_ledger": ledger,
            "yearly_results": [
                {"peer_review": {"score_metrics": {"total_reviews": 5}}}
            ],
        }),
        encoding="utf-8",
    )
    objective = {
        "metrics": {
            "active-researcher-fraction": {
                "metric_version": "1.0.0", "status": "measured", "value": 0.5,
                "slice_results": {},
            },
            "topic-entropy": {
                "metric_version": "1.0.0", "status": "measured", "value": 0.8,
                "slice_results": {},
            },
            "review-burden-per-active-researcher": {
                "metric_version": "1.0.0", "status": "measured", "value": 1.2,
                "slice_results": {},
            },
        }
    }

    result = evaluate_common_suite(
        run_id=run_id,
        output_root=tmp_path,
        candidate={"reviews_per_paper": 2},
        objective_evaluation=objective,
    )

    assert result["evaluator"]["version"] == "1.0.0"
    assert result["metrics"]["review-coverage"]["value"] == pytest.approx(5 / 6)
    assert result["metrics"]["submission-count"]["value"] == 3
    assert result["metrics"]["decision-count"]["value"] == 3
    assert result["metrics"]["accepted-paper-count"]["value"] == 1
    assert result["metrics"]["attrition-fraction"]["value"] == 0.5
    funding = result["metrics"]["funding-and-resource-ledger"]
    assert funding["status"] == "measured"
    assert funding["value"]["allocations"]["applied"] == 1
    assert funding["value"]["resource_inflow"] == {
        "status": "measured",
        "grant_income": 20.0,
        "industry_income": 5.0,
        "total_income": 25.0,
    }
    assert funding["value"]["ending_resources"]["mean"] == 20.0


def test_review_coverage_is_unknown_for_zero_submissions(tmp_path):
    run_id = "held-out-zero"
    docs = tmp_path / "docs" / run_id
    checkpoints = tmp_path / "checkpoints" / run_id
    docs.mkdir(parents=True)
    checkpoints.mkdir(parents=True)
    pd.DataFrame([{"year": 1, "num_submissions": 0}]).to_parquet(
        docs / "ecosystem_year.parquet", index=False
    )
    pd.DataFrame(columns=["paper_id", "accepted"]).to_parquet(
        docs / "paper.parquet", index=False
    )
    pd.DataFrame(columns=["event_id", "year", "paper_id", "reviewer_id"]).to_parquet(
        docs / "review_action.parquet", index=False
    )
    pd.DataFrame([{"agent_id": "r0", "year": 1, "is_active": True}]).to_parquet(
        docs / "agent_year.parquet", index=False
    )
    (checkpoints / "checkpoint_year_1.json").write_text(
        json.dumps({
            "yearly_results": [
                {"peer_review": {"score_metrics": {"total_reviews": 0}}}
            ]
        }),
        encoding="utf-8",
    )

    result = evaluate_common_suite(
        run_id=run_id,
        output_root=tmp_path,
        candidate={"reviews_per_paper": 3},
        objective_evaluation={"metrics": {}},
    )

    coverage = result["metrics"]["review-coverage"]
    assert coverage["status"] == "unknown"
    assert coverage["value"] is None
    assert "no submissions" in coverage["reason"]
