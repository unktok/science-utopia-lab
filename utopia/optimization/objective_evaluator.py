"""Evaluate completed runs against a frozen Metric Constitution.

This module evaluates simulator artifacts.  It never changes a design, metric,
threshold, or constitution, and it never converts missing evidence into a pass.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping

from utopia.optimization.metric_constitution import constitution_sha256


SCHEMA = "scienceutopia.objective_evaluation.v1"
EVALUATOR_ID = "harness-metric-evaluator"
EVALUATOR_VERSION = "1.1.0"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _checkpoint_year(path: Path) -> int:
    try:
        return int(path.stem.rsplit("_", 1)[1])
    except (IndexError, ValueError):
        return -1


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _unknown(metric: Mapping[str, Any], reason: str, sources: Iterable[str]) -> dict[str, Any]:
    return {
        "metric_id": metric["id"],
        "metric_version": metric["version"],
        "status": "unknown",
        "value": None,
        "unit": metric["unit"],
        "reason": reason,
        "source_artifacts": list(sources),
        "slice_results": _unknown_slices(metric, reason),
    }


def _unknown_slices(metric: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        slice_id: {"status": "unknown", "value": None, "reason": reason}
        for slice_id in metric.get("stakeholder_slice_refs", [])
    }


def _measured(
    metric: Mapping[str, Any], value: float | bool, sources: Iterable[str], *,
    slice_reason: str | None = None,
    slice_results: Mapping[str, Any] | None = None,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "metric_id": metric["id"],
        "metric_version": metric["version"],
        "status": "measured",
        "value": value,
        "unit": metric["unit"],
        "source_artifacts": list(sources),
        "slice_results": {},
    }
    if slice_reason:
        result["slice_results"] = _unknown_slices(metric, slice_reason)
    if slice_results is not None:
        result["slice_results"] = dict(slice_results)
    if details:
        result["details"] = dict(details)
    return result


def _integrity_metric(metric: Mapping[str, Any], docs: Path, checkpoints: Path) -> dict[str, Any]:
    native_path = docs / "integrity_checks.json"
    trace_paths = sorted(checkpoints.glob("funding_application_trace_year_*.summary.json"))
    sources = [native_path.name, *(path.name for path in trace_paths)]
    if not native_path.exists():
        return _unknown(metric, "native integrity report is missing", sources)
    try:
        native = _read_json(native_path)
        native_passed = bool(native) and all(item.get("passed") is True for item in native)
        trace = [_read_json(path) for path in trace_paths]
    except (OSError, json.JSONDecodeError, TypeError) as error:
        return _unknown(metric, f"integrity evidence is unreadable: {error}", sources)
    if not trace_paths:
        return _unknown(metric, "funding application trace summaries are missing", sources)
    trace_passed = all(item.get("passed") is True for item in trace)
    failures = [
        failure
        for item in native + trace
        for failure in item.get("failures", [])
    ]
    return _measured(
        metric, native_passed and trace_passed, sources,
        details={"native_reports": len(native), "trace_reports": len(trace), "failures": failures},
    )


def _load_tables(docs: Path):
    import pandas as pd

    return pd.read_parquet(docs / "agent_year.parquet"), pd.read_parquet(
        docs / "ecosystem_year.parquet"
    )


def _minimum_slice_support(
    metric: Mapping[str, Any], slice_requirements: Mapping[str, Mapping[str, Any]]
) -> int:
    return max(
        (
            int(slice_requirements[slice_id]["minimum_support"])
            for slice_id in metric.get("stakeholder_slice_refs", [])
            if slice_id in slice_requirements
        ),
        default=1,
    )


def _lower_band_ids(agents, first_year: Any) -> tuple[set[str] | None, str | None]:
    if "resource_band" not in agents.columns:
        return None, "outcome-independent resource-band membership is not recorded"
    initial = agents.loc[agents["year"] == first_year, ["agent_id", "resource_band"]]
    if initial["resource_band"].isna().any() or initial["agent_id"].duplicated().any():
        return None, "initial resource-band membership is missing or duplicated"
    band_counts = agents.groupby("agent_id")["resource_band"].nunique(dropna=False)
    if (band_counts != 1).any():
        return None, "resource-band membership changes during the run"
    return set(initial.loc[initial["resource_band"] == "lower-band", "agent_id"]), None


def _active_fraction(
    metric: Mapping[str, Any], docs: Path,
    slice_requirements: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    source = "agent_year.parquet"
    slice_reason = (
        "Protected resource-band membership was not recorded independently of outcomes; "
        "an end-of-run funding quantile would condition the slice on the result."
    )
    try:
        agents, _ = _load_tables(docs)
        required = {"agent_id", "year", "is_active"}
        if agents.empty or not required.issubset(agents.columns):
            return _unknown(metric, "required agent-year fields are missing", [source])
        first_year, final_year = agents["year"].min(), agents["year"].max()
        initial_ids = set(agents.loc[agents["year"] == first_year, "agent_id"])
        final = agents.loc[
            (agents["year"] == final_year) & agents["agent_id"].isin(initial_ids),
            ["agent_id", "is_active"],
        ]
        if not initial_ids or set(final["agent_id"]) != initial_ids:
            return _unknown(metric, "final status is missing for one or more initial researchers", [source])
        value = float(final.drop_duplicates("agent_id")["is_active"].astype(bool).sum()) / len(initial_ids)
        lower_ids, slice_error = _lower_band_ids(agents, first_year)
        slice_results = None
        if not slice_error:
            minimum_support = _minimum_slice_support(metric, slice_requirements)
            if len(lower_ids) < minimum_support:
                slice_error = (
                    f"lower resource band has support {len(lower_ids)} below required "
                    f"{minimum_support}"
                )
            else:
                lower_final = final.loc[final["agent_id"].isin(lower_ids)]
                slice_results = {
                    "low-resource-researchers": {
                        "status": "measured",
                        "value": float(lower_final["is_active"].astype(bool).sum()) / len(lower_ids),
                        "support": len(lower_ids),
                    }
                }
        return _measured(
            metric, value, [source], slice_reason=slice_error or slice_reason,
            slice_results=slice_results,
            details={
                "initial_researchers": len(initial_ids),
                "active_initial_researchers_at_end": int(round(value * len(initial_ids))),
                "first_year": int(first_year),
                "final_year": int(final_year),
            },
        )
    except (OSError, ValueError, KeyError, ImportError) as error:
        return _unknown(metric, f"active fraction could not be evaluated: {error}", [source])


def _topic_entropy(metric: Mapping[str, Any], docs: Path) -> dict[str, Any]:
    source = "ecosystem_year.parquet"
    try:
        _, ecosystem = _load_tables(docs)
        if ecosystem.empty or not {"year", "topic_entropy"}.issubset(ecosystem.columns):
            return _unknown(metric, "run-end topic entropy is missing", [source])
        final = ecosystem.sort_values("year").iloc[-1]
        value = float(final["topic_entropy"])
        if not math.isfinite(value):
            return _unknown(metric, "run-end topic entropy is non-finite", [source])
        details = {"year": int(final["year"])}
        if "occupied_directions" in final:
            details["occupied_directions"] = int(final["occupied_directions"])
        return _measured(metric, value, [source], details=details)
    except (OSError, ValueError, KeyError, ImportError) as error:
        return _unknown(metric, f"topic entropy could not be evaluated: {error}", [source])


def _review_burden(
    metric: Mapping[str, Any], docs: Path, checkpoints: Path,
    slice_requirements: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    agent_source = "agent_year.parquet"
    checkpoint_paths = sorted(checkpoints.glob("checkpoint_year_*.json"), key=_checkpoint_year)
    sources = [agent_source, *(path.name for path in checkpoint_paths[-1:])]
    slice_reason = (
        "Protected resource-band membership and reviewer-level actions are not jointly "
        "recorded in the evaluation tables."
    )
    if not checkpoint_paths:
        return _unknown(metric, "final checkpoint is missing", sources)
    try:
        agents, _ = _load_tables(docs)
        if agents.empty or "is_active" not in agents:
            return _unknown(metric, "active researcher-time is missing", sources)
        active_steps = int(agents["is_active"].astype(bool).sum())
        checkpoint = _read_json(checkpoint_paths[-1])
        yearly = checkpoint.get("yearly_results", [])
        reviews = sum(
            int(item.get("peer_review", {}).get("score_metrics", {}).get("total_reviews", 0))
            for item in yearly
        )
        if active_steps <= 0:
            return _unknown(metric, "active researcher-time is zero", sources)
        slice_results = None
        slice_error = None
        first_year = agents["year"].min() if "year" in agents else None
        lower_ids, slice_error = _lower_band_ids(agents, first_year)
        action_path = docs / "review_action.parquet"
        if not slice_error:
            minimum_support = _minimum_slice_support(metric, slice_requirements)
            if len(lower_ids) < minimum_support:
                slice_error = (
                    f"lower resource band has support {len(lower_ids)} below required "
                    f"{minimum_support}"
                )
            elif action_path.exists():
                import pandas as pd

                actions = pd.read_parquet(action_path)
                if not {"event_id", "reviewer_id"}.issubset(actions.columns):
                    slice_error = "review-action fields are missing"
                elif actions["event_id"].duplicated().any() or len(actions) != reviews:
                    slice_error = "review-action events do not reconcile with aggregate reviews"
                else:
                    lower_steps = int(
                        agents.loc[agents["agent_id"].isin(lower_ids), "is_active"]
                        .astype(bool).sum()
                    )
                    if lower_steps <= 0:
                        slice_error = "active lower-resource researcher-time is zero"
                    else:
                        lower_reviews = int(actions["reviewer_id"].isin(lower_ids).sum())
                        slice_results = {
                            "low-resource-researchers": {
                                "status": "measured",
                                "value": lower_reviews / lower_steps,
                                "support": len(lower_ids),
                                "review_actions": lower_reviews,
                                "active_researcher_steps": lower_steps,
                            }
                        }
                        sources.append(action_path.name)
            elif reviews == 0:
                lower_steps = int(
                    agents.loc[agents["agent_id"].isin(lower_ids), "is_active"]
                    .astype(bool).sum()
                )
                slice_results = {
                    "low-resource-researchers": {
                        "status": "measured", "value": 0.0,
                        "support": len(lower_ids), "review_actions": 0,
                        "active_researcher_steps": lower_steps,
                    }
                }
            else:
                slice_error = "review-action table is missing"
        return _measured(
            metric, reviews / active_steps, sources,
            slice_reason=slice_error or slice_reason, slice_results=slice_results,
            details={"review_actions": reviews, "active_researcher_steps": active_steps},
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, ImportError) as error:
        return _unknown(metric, f"review burden could not be evaluated: {error}", sources)


def _compare(value: Any, comparator: str, threshold: Any) -> bool:
    return {
        "==": value == threshold,
        ">=": value >= threshold,
        "<=": value <= threshold,
        ">": value > threshold,
        "<": value < threshold,
    }[comparator]


def _state_for_rule(rule: Mapping[str, Any], metrics: Mapping[str, Mapping[str, Any]], key: str) -> dict[str, Any]:
    refs = rule.get("metric_refs", [])
    referenced = [metrics[ref] for ref in refs if ref in metrics]
    if len(referenced) != len(refs) or any(item["status"] != "measured" for item in referenced):
        state = "unknown"
        reason = "one or more referenced metrics are unavailable"
    else:
        threshold = rule[key]
        aggregate_pass = all(
            _compare(item["value"], threshold["comparator"], threshold["value"])
            for item in referenced
        )
        slices = [slice_result for item in referenced for slice_result in item["slice_results"].values()]
        slice_fail = any(
            item["status"] == "measured"
            and not _compare(item["value"], threshold["comparator"], threshold["value"])
            for item in slices
        )
        if not aggregate_pass or slice_fail:
            state, reason = "fail", "threshold failed"
        elif any(item["status"] == "unknown" for item in slices):
            state, reason = "unknown", "a required protected slice is unknown"
        else:
            state, reason = "pass", None
    return {"id": rule["id"], "state": state, "metric_refs": refs, "reason": reason}


def evaluate_run(
    *, run_id: str, output_root: str | Path, constitution: Mapping[str, Any]
) -> dict[str, Any]:
    declared = [
        item for item in constitution["layers"]["evaluator_governance"]["evaluators"]
        if item["id"] == EVALUATOR_ID
    ]
    if len(declared) != 1 or declared[0]["version"] != EVALUATOR_VERSION:
        declared_versions = [item.get("version") for item in declared]
        raise ValueError(
            f"constitution evaluator version {declared_versions!r} does not match "
            f"implementation {EVALUATOR_VERSION}"
        )
    root = Path(output_root)
    docs, checkpoints = root / "docs" / run_id, root / "checkpoints" / run_id
    manifest_path = docs / "run_manifest.json"
    try:
        manifest = _read_json(manifest_path)
    except (OSError, json.JSONDecodeError):
        manifest = {}
    registry = {metric["id"]: metric for metric in constitution["metric_registry"]}
    slice_requirements = {
        item["id"]: item for item in constitution.get("stakeholder_slices", [])
    }
    implementations = {
        "integrity-checks-pass": lambda metric: _integrity_metric(metric, docs, checkpoints),
        "active-researcher-fraction": lambda metric: _active_fraction(
            metric, docs, slice_requirements
        ),
        "topic-entropy": lambda metric: _topic_entropy(metric, docs),
        "review-burden-per-active-researcher": lambda metric: _review_burden(
            metric, docs, checkpoints, slice_requirements
        ),
    }
    metrics = {
        metric_id: implementations[metric_id](metric)
        if metric_id in implementations
        else _unknown(metric, "metric implementation is not registered", [])
        for metric_id, metric in registry.items()
    }
    constraints = [
        _state_for_rule(rule, metrics, "threshold")
        for rule in constitution["layers"]["hard_constraints"]
    ]
    capabilities = [
        _state_for_rule(rule, metrics, "minimum_or_reserve")
        for rule in constitution["layers"]["capability_preservation"]
    ]
    objectives = []
    for commitment in constitution["layers"]["commitments"]:
        for objective in commitment["objectives"]:
            refs = objective["metric_refs"]
            referenced = [metrics[ref] for ref in refs]
            if any(item["status"] != "measured" for item in referenced):
                objective_status = "unknown"
            elif any(
                slice_result["status"] == "unknown"
                for item in referenced for slice_result in item["slice_results"].values()
            ):
                objective_status = "partial"
            else:
                objective_status = "measured"
            objectives.append({
                "commitment_id": commitment["id"],
                "objective_id": objective["id"],
                "priority_class": objective["priority_class"],
                "direction": objective["direction"],
                "metric_refs": refs,
                "status": objective_status,
                "values": {ref: metrics[ref]["value"] for ref in refs},
            })
    if any(item["state"] == "fail" for item in constraints + capabilities):
        eligibility = "infeasible"
    elif any(item["state"] == "unknown" for item in constraints + capabilities):
        eligibility = "unknown"
    else:
        eligibility = "feasible"
    gaps = [
        {"metric_id": metric_id, "reason": result.get("reason", "required slice unknown")}
        for metric_id, result in metrics.items()
        if result["status"] == "unknown" or any(
            item["status"] == "unknown" for item in result["slice_results"].values()
        )
    ]
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "constitution": {
            "id": constitution["constitution_id"],
            "version": constitution["version"],
            "sha256": constitution_sha256(constitution),
        },
        "evaluator": {
            "id": EVALUATOR_ID,
            "version": EVALUATOR_VERSION,
            "relation": "same_producer",
            "implementation_sha256": _file_sha256(Path(__file__)),
        },
        "run_provenance": {
            "source_commit": manifest.get("git_commit"),
            "scientific_config_hash": manifest.get("scientific_config_hash"),
            "manifest_sha256": _file_sha256(manifest_path) if manifest_path.exists() else None,
        },
        "comparison_eligibility": eligibility,
        "hard_constraints": constraints,
        "capabilities": capabilities,
        "objective_vector": objectives,
        "metrics": metrics,
        "measurement_gaps": gaps,
    }


def write_evaluation(evaluation: Mapping[str, Any], output_root: str | Path) -> Path:
    path = Path(output_root) / "docs" / evaluation["run_id"] / "objective_evaluation.json"
    path.write_text(json.dumps(evaluation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def summarize_evaluations(
    evaluations: Iterable[Mapping[str, Any]], rows: Iterable[Mapping[str, Any]],
    constitution: Mapping[str, Any],
) -> list[dict[str, Any]]:
    row_by_run = {row["run_id"]: row for row in rows}
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for evaluation in evaluations:
        grouped[row_by_run[evaluation["run_id"]]["design_id"]].append(evaluation)
    minimum_runs = {
        metric["id"]: int(metric["uncertainty"]["minimum_runs"])
        for metric in constitution["metric_registry"]
    }
    objective_metric_ids = {
        ref
        for commitment in constitution["layers"]["commitments"]
        for objective in commitment["objectives"]
        for ref in objective["metric_refs"]
    }
    required_runs = max((minimum_runs[ref] for ref in objective_metric_ids), default=1)
    summaries = []
    for design_id, items in sorted(grouped.items()):
        metric_values: dict[str, list[float]] = defaultdict(list)
        for item in items:
            for metric_id, result in item["metrics"].items():
                value = result["value"]
                if result["status"] == "measured" and type(value) in {int, float}:
                    metric_values[metric_id].append(float(value))
        eligibility_states = [item["comparison_eligibility"] for item in items]
        reasons = []
        if len(items) < required_runs:
            reasons.append(f"requires at least {required_runs} runs for objective uncertainty")
        if any(state == "infeasible" for state in eligibility_states):
            reasons.append("one or more runs are infeasible")
        if any(state == "unknown" for state in eligibility_states):
            reasons.append("one or more runs have unknown constraint or capability state")
        summaries.append({
            "design_id": design_id,
            "run_count": len(items),
            "required_minimum_runs": required_runs,
            "comparison_eligibility_states": eligibility_states,
            "authorized_for_ranking": not reasons,
            "blocking_reasons": reasons,
            "metric_summaries": {
                metric_id: {
                    "n": len(values),
                    "mean": statistics.fmean(values) if values else None,
                    "median": statistics.median(values) if values else None,
                    "min": min(values) if values else None,
                    "max": max(values) if values else None,
                }
                for metric_id, values in sorted(metric_values.items())
            },
        })
    return summaries
