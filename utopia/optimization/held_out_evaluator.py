"""Versioned native-artifact evaluator for the common held-out metric suite."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping


SCHEMA = "scienceutopia.held-out-run-evaluation.v1"
EVALUATOR_ID = "metric-conditioned-native-evaluator"
EVALUATOR_VERSION = "1.0.0"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _checkpoint_year(path: Path) -> int:
    try:
        return int(path.stem.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return -1


def _unknown(metric_id: str, version: str, reason: str, sources: list[str]) -> dict[str, Any]:
    return {
        "metric_id": metric_id,
        "metric_version": version,
        "status": "unknown",
        "value": None,
        "reason": reason,
        "source_artifacts": sources,
    }


def _measured(
    metric_id: str,
    version: str,
    value: Any,
    sources: list[str],
    *,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "metric_id": metric_id,
        "metric_version": version,
        "status": "measured",
        "value": value,
        "source_artifacts": sources,
    }
    if details is not None:
        result["details"] = dict(details)
    return result


def _review_and_activity(
    docs: Path, checkpoints: Path, candidate: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    import pandas as pd

    actions_path = docs / "review_action.parquet"
    ecosystem_path = docs / "ecosystem_year.parquet"
    paper_path = docs / "paper.parquet"
    results: dict[str, dict[str, Any]] = {}
    try:
        ecosystem = pd.read_parquet(ecosystem_path)
        if ecosystem.empty or "num_submissions" not in ecosystem:
            raise ValueError("num_submissions is missing")
        submissions = int(ecosystem["num_submissions"].sum())
        results["submission-count"] = _measured(
            "submission-count", "1.0.0", submissions, [ecosystem_path.name]
        )
    except (OSError, ValueError, KeyError, ImportError) as error:
        submissions = None
        results["submission-count"] = _unknown(
            "submission-count", "1.0.0", f"submission count unavailable: {error}",
            [ecosystem_path.name],
        )

    try:
        papers = pd.read_parquet(paper_path)
        if "accepted" not in papers:
            raise ValueError("accepted decision is missing")
        if papers["accepted"].isna().any():
            raise ValueError("one or more decisions are missing")
        decisions = len(papers)
        accepted = int(papers["accepted"].astype(bool).sum())
        results["decision-count"] = _measured(
            "decision-count", "1.0.0", decisions, [paper_path.name]
        )
        results["accepted-paper-count"] = _measured(
            "accepted-paper-count", "1.0.0", accepted, [paper_path.name]
        )
    except (OSError, ValueError, KeyError, ImportError) as error:
        for metric_id in ("decision-count", "accepted-paper-count"):
            results[metric_id] = _unknown(
                metric_id, "1.0.0", f"paper decisions unavailable: {error}",
                [paper_path.name],
            )

    try:
        reviews_per_paper = candidate.get("reviews_per_paper")
        if isinstance(reviews_per_paper, bool) or not isinstance(reviews_per_paper, int):
            raise ValueError("frozen candidate reviews_per_paper is missing")
        if reviews_per_paper < 1:
            raise ValueError("reviews_per_paper must be positive")
        if submissions is None:
            raise ValueError("submission count is unavailable")
        if submissions == 0:
            raise ValueError("coverage is undefined because there were no submissions")
        actions = pd.read_parquet(actions_path)
        required = {"event_id", "year", "paper_id", "reviewer_id"}
        if not required.issubset(actions.columns):
            raise ValueError("review-action identity fields are missing")
        if actions["event_id"].duplicated().any():
            raise ValueError("review-action event ids are duplicated")
        completed = len(actions)
        checkpoint_paths = sorted(
            checkpoints.glob("checkpoint_year_*.json"), key=_checkpoint_year
        )
        if not checkpoint_paths:
            raise ValueError("final checkpoint is missing")
        checkpoint = json.loads(checkpoint_paths[-1].read_text(encoding="utf-8"))
        aggregate_reviews = sum(
            int(item.get("peer_review", {}).get("score_metrics", {}).get("total_reviews", 0))
            for item in checkpoint.get("yearly_results", [])
        )
        if completed != aggregate_reviews:
            raise ValueError(
                "review actions do not reconcile with checkpoint total_reviews "
                f"({completed} != {aggregate_reviews})"
            )
        expected = submissions * reviews_per_paper
        results["review-coverage"] = _measured(
            "review-coverage",
            "1.0.0",
            completed / expected,
            [actions_path.name, ecosystem_path.name, checkpoint_paths[-1].name],
            details={
                "completed_review_actions": completed,
                "submission_rounds": submissions,
                "declared_reviews_per_paper": reviews_per_paper,
                "expected_review_actions": expected,
                "above_one": completed > expected,
            },
        )
    except (OSError, ValueError, KeyError, ImportError) as error:
        results["review-coverage"] = _unknown(
            "review-coverage", "1.0.0", str(error),
            [actions_path.name, ecosystem_path.name, "frozen-system-spec"],
        )
    return results


def _attrition(docs: Path) -> dict[str, Any]:
    import pandas as pd

    path = docs / "agent_year.parquet"
    try:
        agents = pd.read_parquet(path)
        required = {"agent_id", "year", "is_active"}
        if agents.empty or not required.issubset(agents.columns):
            raise ValueError("required agent-year fields are missing")
        first_year = agents["year"].min()
        initial_ids = set(agents.loc[agents["year"] == first_year, "agent_id"])
        if not initial_ids:
            raise ValueError("initial cohort is empty")
        cohort = agents.loc[agents["agent_id"].isin(initial_ids)]
        attrited_ids = set(
            cohort.loc[~cohort["is_active"].astype(bool), "agent_id"]
        )
        return _measured(
            "attrition-fraction",
            "1.0.0",
            len(attrited_ids) / len(initial_ids),
            [path.name],
            details={
                "initial_researchers": len(initial_ids),
                "ever_inactive_researchers": len(attrited_ids),
                "first_year": int(first_year),
            },
        )
    except (OSError, ValueError, KeyError, ImportError) as error:
        return _unknown(
            "attrition-fraction", "1.0.0", f"attrition unavailable: {error}",
            [path.name],
        )


def _numeric_distribution(values: list[float]) -> dict[str, Any]:
    ordered = sorted(values)
    total = math.fsum(values)
    if total > 0:
        n = len(ordered)
        gini = (
            2 * math.fsum((index + 1) * value for index, value in enumerate(ordered))
            / (n * total)
            - (n + 1) / n
        )
    else:
        gini = 0.0
    return {
        "n": len(values),
        "total": total,
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "population_sd": statistics.pstdev(values),
        "min": min(values),
        "max": max(values),
        "gini": gini,
    }


def _funding_resource(checkpoints: Path) -> dict[str, Any]:
    trace_paths = sorted(checkpoints.glob("funding_application_trace_year_*.summary.json"))
    checkpoint_paths = sorted(
        checkpoints.glob("checkpoint_year_*.json"), key=_checkpoint_year
    )
    sources = [path.name for path in trace_paths]
    if checkpoint_paths:
        sources.append(checkpoint_paths[-1].name)
    components: dict[str, Any] = {}
    missing: list[str] = []

    count_fields = (
        "targets", "validated", "submitted", "declined_by_agent", "dropped",
        "evaluated", "decided", "funded", "allocations_recorded",
        "allocations_applied", "generation_attempts", "semantic_invalid_attempts",
        "sanitized_reference_attempts", "request_error_attempts",
    )
    try:
        if not trace_paths:
            raise ValueError("funding trace summaries are missing")
        totals = {field: 0 for field in count_fields}
        years = []
        for path in trace_paths:
            summary = json.loads(path.read_text(encoding="utf-8"))
            if summary.get("passed") is not True:
                raise ValueError(f"{path.name} did not pass conservation checks")
            counts = summary.get("counts", {})
            for field in count_fields:
                if not isinstance(counts.get(field), int):
                    raise ValueError(f"{path.name} is missing integer {field}")
                totals[field] += counts[field]
            years.append({"year": summary.get("year"), **{field: counts[field] for field in count_fields}})
        components["application_pipeline"] = {
            "status": "measured", "totals": totals, "years": years,
        }
        components["allocations"] = {
            "status": "measured",
            "recorded": totals["allocations_recorded"],
            "applied": totals["allocations_applied"],
            "funded_decisions": totals["funded"],
        }
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        missing.append(f"application pipeline: {error}")
        components["application_pipeline"] = {"status": "unknown", "reason": str(error)}
        components["allocations"] = {"status": "unknown", "reason": str(error)}

    try:
        if not checkpoint_paths:
            raise ValueError("final checkpoint is missing")
        checkpoint = json.loads(checkpoint_paths[-1].read_text(encoding="utf-8"))
        ledger = checkpoint.get("resource_ledger")
        if not isinstance(ledger, dict):
            raise ValueError("resource ledger is missing")
        transactions = ledger.get("transactions")
        years = ledger.get("years")
        if not isinstance(transactions, list) or not isinstance(years, dict) or not years:
            raise ValueError("resource ledger transactions or yearly balances are missing")
        grant = math.fsum(
            float(item["delta"]) for item in transactions
            if item.get("category") == "grant_income"
        )
        industry = math.fsum(
            float(item["delta"]) for item in transactions
            if item.get("category") == "industry_income"
        )
        final_year = max(years, key=lambda value: int(value))
        final_rows = list(years[final_year].values())
        balances = [float(row["closing_balance"]) for row in final_rows]
        if not balances or any(not math.isfinite(value) for value in balances):
            raise ValueError("final closing balances are empty or non-finite")
        components["resource_inflow"] = {
            "status": "measured",
            "grant_income": grant,
            "industry_income": industry,
            "total_income": grant + industry,
        }
        components["ending_resources"] = {
            "status": "measured",
            "year": int(final_year),
            **_numeric_distribution(balances),
        }
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        missing.append(f"resource ledger: {error}")
        components["resource_inflow"] = {"status": "unknown", "reason": str(error)}
        components["ending_resources"] = {"status": "unknown", "reason": str(error)}

    status = "measured" if not missing else ("partial" if len(missing) == 1 else "unknown")
    result = {
        "metric_id": "funding-and-resource-ledger",
        "metric_version": "1.0.0",
        "status": status,
        "value": components,
        "source_artifacts": sources,
    }
    if missing:
        result["reason"] = "; ".join(missing)
    return result


def evaluate_common_suite(
    *,
    run_id: str,
    output_root: str | Path,
    candidate: Mapping[str, Any],
    objective_evaluation: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one completed run without changing any optimizer state."""
    root = Path(output_root)
    docs = root / "docs" / run_id
    checkpoints = root / "checkpoints" / run_id
    metrics = dict(objective_evaluation.get("metrics", {}))
    metrics.update(_review_and_activity(docs, checkpoints, candidate))
    metrics["attrition-fraction"] = _attrition(docs)
    metrics["funding-and-resource-ledger"] = _funding_resource(checkpoints)
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "evaluator": {
            "id": EVALUATOR_ID,
            "version": EVALUATOR_VERSION,
            "implementation_sha256": _sha(Path(__file__)),
        },
        "metrics": metrics,
    }
