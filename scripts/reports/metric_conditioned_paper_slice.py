"""Build the complete metric-conditioned paper slice from sealed artifacts.

The command is intentionally fail-closed.  It validates the three completed
optimization arms, simultaneous winner freeze, complete common held-out split,
cross-objective loss matrix, runtime registries, and provenance chain before it
writes any result artifact.  Outputs are staged and published atomically.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import statistics
import tempfile
from typing import Any, Iterable, Mapping

from scripts.figures.metric_conditioned_results import (
    EXPERIMENTAL,
    REPORT_SCHEMA,
    SYNTHETIC,
    normalize_report,
    render,
)
from utopia.optimization.harness import digest
from utopia.optimization.metric_conditioned_study import (
    EVALUATION_SNAPSHOT_SCHEMA,
    FREEZE_SCHEMA,
    STUDY_SCHEMA,
)
from utopia.optimization.metric_conditioned_analysis import build_analyses
from utopia.optimization.loss import loss_spec_sha256


ROOT = Path(__file__).resolve().parents[2]
SLICE_SCHEMA = "scienceutopia.metric-conditioned-paper-slice.v1"
STATE_SCHEMA = "scienceutopia.closed-loop-state.v1"
SNAPSHOT_SCHEMA = "scienceutopia.closed-loop-snapshot.v1"
PAPER_OUTPUT = ROOT / "paper/generated/metric-conditioned"
T95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    24: 2.064,
    30: 2.042,
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _file_sha(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _provenance_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT.resolve()))
    except ValueError:
        return str(resolved)


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _t_critical_95(df: int) -> float:
    if df in T95:
        return T95[df]
    lower = max((key for key in T95 if key <= df), default=None)
    if lower is not None and df < 30:
        return T95[lower]
    return 1.96


def _uncertainty(values: Iterable[float]) -> dict[str, Any]:
    numbers = [float(value) for value in values]
    if not numbers or any(not math.isfinite(value) for value in numbers):
        raise ValueError("uncertainty requires finite observations")
    mean = statistics.fmean(numbers)
    if len(numbers) == 1:
        return {
            "n": 1,
            "mean": mean,
            "sample_sd": None,
            "standard_error": None,
            "ci95_low": None,
            "ci95_high": None,
            "method": "undefined_for_n_lt_2",
        }
    sample_sd = statistics.stdev(numbers)
    standard_error = sample_sd / math.sqrt(len(numbers))
    half_width = _t_critical_95(len(numbers) - 1) * standard_error
    return {
        "n": len(numbers),
        "mean": mean,
        "sample_sd": sample_sd,
        "standard_error": standard_error,
        "ci95_low": mean - half_width,
        "ci95_high": mean + half_width,
        "method": "two_sided_student_t_95",
    }


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = quantile * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _aggregate_loss_uncertainty(
    values: Iterable[float], *, dispersion_weight: float, estimate: float
) -> dict[str, Any]:
    numbers = [float(value) for value in values]
    if len(numbers) < 2 or len(numbers) > 7:
        raise ValueError("exact aggregate bootstrap requires 2-7 held-out seeds")
    aggregates = []
    for indexes in itertools.product(range(len(numbers)), repeat=len(numbers)):
        sample = [numbers[index] for index in indexes]
        aggregates.append(
            statistics.fmean(sample)
            + dispersion_weight * statistics.pstdev(sample)
        )
    per_seed = _uncertainty(numbers)
    return {
        "n": len(numbers),
        "estimate": float(estimate),
        "per_seed_mean": per_seed["mean"],
        "sample_sd": per_seed["sample_sd"],
        "standard_error": per_seed["standard_error"],
        "ci95_low": _percentile(aggregates, 0.025),
        "ci95_high": _percentile(aggregates, 0.975),
        "dispersion_weight": dispersion_weight,
        "bootstrap_resamples": len(aggregates),
        "method": "exact_nonparametric_bootstrap_of_loss_aggregate_95_percentile",
    }


def _seed_map(items: Iterable[Mapping[str, Any]], value_key: str) -> dict[int, float]:
    result: dict[int, float] = {}
    for item in items:
        value = item.get(value_key)
        if _finite(value):
            seed = item.get("seed")
            if isinstance(seed, bool) or not isinstance(seed, int) or seed in result:
                raise ValueError("seed observations require unique integer seeds")
            result[seed] = float(value)
    return result


def _numeric_summary(values: Iterable[float]) -> dict[str, Any]:
    numbers = [float(value) for value in values]
    return {
        "n": len(numbers),
        "mean": statistics.fmean(numbers) if numbers else None,
        "median": statistics.median(numbers) if numbers else None,
        "population_sd": statistics.pstdev(numbers) if numbers else None,
        "min": min(numbers) if numbers else None,
        "max": max(numbers) if numbers else None,
    }


def _flatten_numeric(value: Any, prefix: str = "") -> dict[str, float]:
    flattened: dict[str, float] = {}
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"status", "reason"}:
                continue
            path = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten_numeric(item, path))
    elif _finite(value):
        flattened[prefix] = float(value)
    return flattened


def _structured_summary(values: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    by_path: dict[str, list[float]] = {}
    for value in values:
        for path, number in _flatten_numeric(value).items():
            by_path.setdefault(path, []).append(number)
    return {
        path: _numeric_summary(numbers)
        for path, numbers in sorted(by_path.items())
    }


def _equal_number(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is right
    return _finite(left) and _finite(right) and math.isclose(
        float(left), float(right), rel_tol=0.0, abs_tol=1e-12
    )


def _verify_summary(
    actual: Mapping[str, Any], expected: Mapping[str, Any], *, label: str
) -> None:
    if set(actual) != set(expected):
        raise ValueError(f"{label} summary fields are inconsistent")
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if key == "n":
            if actual_value != expected_value:
                raise ValueError(f"{label} summary count is inconsistent")
        elif not _equal_number(actual_value, expected_value):
            raise ValueError(f"{label} summary {key} is inconsistent")


def _analysis_digest(value: Mapping[str, Any]) -> str:
    """Hash analyses while ignoring only scientifically irrelevant row order."""
    normalized = json.loads(json.dumps(value, allow_nan=False))
    for key in ("paired_tradeoffs", "gaming_flags"):
        normalized[key] = sorted(
            normalized.get(key, []),
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
    rank = normalized.get("rank_reversal", {})
    for key in ("pairwise_kendall_tau_b", "winner_reversals"):
        rank[key] = sorted(
            rank.get(key, []),
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
    return digest(normalized, length=64)


def _paired_uncertainty(
    left: Mapping[int, float], right: Mapping[int, float]
) -> dict[str, Any]:
    seeds = sorted(set(left) & set(right))
    result = _uncertainty(left[seed] - right[seed] for seed in seeds)
    result["seeds"] = seeds
    result["estimand"] = "left_minus_right_on_common_held_out_seeds"
    return result


def _sqlite_rows(path: Path, query: str) -> list[dict[str, Any]]:
    uri = f"file:{path.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(query).fetchall()]
    finally:
        connection.close()


def _registry_summary(
    path: Path,
    *,
    expected_runs: int,
    label: str,
    allow_terminal_failures: bool = False,
) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing {label} registry: {path}")
    rows = _sqlite_rows(path, "SELECT * FROM runs ORDER BY run_id")
    if len(rows) != expected_runs:
        raise ValueError(f"{label} registry has {len(rows)}/{expected_runs} runs")
    terminal_failures = [
        row
        for row in rows
        if row["status"] == "failed" and row["attempt"] >= row["max_attempts"]
    ]
    unresolved = [
        row["run_id"]
        for row in rows
        if row["status"] != "complete"
        and not (allow_terminal_failures and row in terminal_failures)
    ]
    if unresolved:
        raise ValueError(f"{label} registry has unresolved runs: {unresolved}")
    attempts = _sqlite_rows(
        path, "SELECT * FROM attempts ORDER BY run_id, attempt"
    )
    if any(item["status"] == "running" for item in attempts):
        raise ValueError(f"{label} registry contains a running attempt")
    tables = {
        row["name"]
        for row in _sqlite_rows(
            path, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    }
    links = (
        _sqlite_rows(path, "SELECT * FROM artifact_links ORDER BY logical_run_id")
        if "artifact_links" in tables
        else []
    )
    adopted = {item["logical_run_id"] for item in links}
    invalid_adoptions = [
        row["run_id"]
        for row in rows
        if row["run_id"] in adopted and row["status"] != "complete"
    ]
    if invalid_adoptions:
        raise ValueError(
            f"{label} registry adopts non-complete runs: {invalid_adoptions}"
        )
    executed = [row for row in rows if row["run_id"] not in adopted]
    missing_runtime = [
        row["run_id"] for row in executed if not _finite(row.get("wall_seconds"))
    ]
    if missing_runtime:
        raise ValueError(f"{label} executed runs lack runtime: {missing_runtime}")
    wall_seconds = [
        float(item["wall_seconds"])
        for item in attempts
        if _finite(item.get("wall_seconds"))
    ]
    attempts_missing_wall_seconds = sum(
        not _finite(item.get("wall_seconds")) for item in attempts
    )
    source_commits = {
        row.get("source_commit")
        for row in rows
        if isinstance(row.get("source_commit"), str) and row.get("source_commit")
    }
    if "run_execution_identities" in tables:
        for item in _sqlite_rows(
            path,
            "SELECT identity_json FROM run_execution_identities ORDER BY run_id",
        ):
            identity = json.loads(item["identity_json"])
            commit = identity.get("producer_source_commit")
            if isinstance(commit, str) and commit:
                source_commits.add(commit)
    return {
        "registry_sha256": _file_sha(path),
        "logical_runs": len(rows),
        "complete_logical_runs": sum(row["status"] == "complete" for row in rows),
        "terminal_failed_logical_runs": len(terminal_failures),
        "executed_physical_runs": len(executed),
        "adopted_logical_runs": len(links),
        "physical_run_wall_seconds": _uncertainty(wall_seconds),
        "physical_run_wall_seconds_total": sum(wall_seconds),
        "attempts": len(attempts),
        "attempts_missing_wall_seconds": attempts_missing_wall_seconds,
        "failed_attempts": sum(item["status"] == "failed" for item in attempts),
        "source_commits": sorted(source_commits),
    }


def _verify_freeze(freeze: Mapping[str, Any]) -> None:
    if freeze.get("schema") != FREEZE_SCHEMA:
        raise ValueError(f"winner freeze must use {FREEZE_SCHEMA}")
    expected = freeze.get("freeze_sha256")
    immutable = dict(freeze)
    immutable.pop("freeze_sha256", None)
    immutable.pop("frozen_utc", None)
    if not isinstance(expected, str) or digest(immutable, length=64) != expected:
        raise ValueError("winner freeze hash does not match its contents")


def _validate_inputs(
    *,
    manifest: Mapping[str, Any],
    campaign_specs: Mapping[str, Mapping[str, Any]],
    loss_specs: Mapping[str, Mapping[str, Any]],
    states: Mapping[str, Mapping[str, Any]],
    snapshots: Mapping[str, Mapping[str, Any]],
    freeze: Mapping[str, Any],
    evaluation_snapshot: Mapping[str, Any],
    report: Mapping[str, Any],
) -> tuple[list[str], list[int]]:
    if manifest.get("schema") != STUDY_SCHEMA:
        raise ValueError(f"study manifest must use {STUDY_SCHEMA}")
    if manifest.get("decision_policy") != "report_only":
        raise ValueError("paper slice requires the preregistered report-only policy")
    arms = list(campaign_specs)
    if len(arms) != 3 or set(states) != set(arms) or set(snapshots) != set(arms):
        raise ValueError("paper slice requires exactly the three declared campaign arms")
    reference = campaign_specs[arms[0]]
    for arm in arms[1:]:
        for field in (
            "study_template",
            "fidelity",
            "seed_sets",
            "optimizer",
            "budget",
            "execution",
        ):
            if campaign_specs[arm].get(field) != reference.get(field):
                raise ValueError(f"campaign arms differ on controlled field {field}")
    if reference.get("seed_sets", {}).get("optimization") != manifest.get(
        "common_optimization_seeds"
    ) or reference.get("seed_sets", {}).get("held_out_evaluation") != manifest.get(
        "common_held_out_evaluation_seeds"
    ):
        raise ValueError("campaign seed sets differ from the study manifest")
    _verify_freeze(freeze)
    study_id = manifest["id"]
    study_revision = freeze.get("study_revision")
    if freeze.get("study_id") != study_id or len(freeze.get("winners", [])) != 3:
        raise ValueError("winner freeze does not match the three-arm study")
    if evaluation_snapshot.get("schema") != EVALUATION_SNAPSHOT_SCHEMA:
        raise ValueError("held-out snapshot schema is invalid")
    if (
        evaluation_snapshot.get("study_id") != study_id
        or evaluation_snapshot.get("study_revision") != study_revision
        or evaluation_snapshot.get("winner_freeze_sha256") != freeze["freeze_sha256"]
    ):
        raise ValueError("held-out snapshot does not match the winner freeze")
    if report.get("schema") != REPORT_SCHEMA:
        raise ValueError(f"cross-evaluation report must use {REPORT_SCHEMA}")
    if (
        report.get("study_id") != study_id
        or report.get("study_revision") != study_revision
        or report.get("winner_freeze_sha256") != freeze["freeze_sha256"]
    ):
        raise ValueError("cross-evaluation report does not match the winner freeze")
    if report.get("decision_policy") != "report_only":
        raise ValueError("cross-evaluation report changed the decision policy")

    winners = {item["campaign_id"]: item for item in freeze["winners"]}
    if set(winners) != set(arms):
        raise ValueError("winner freeze arm set differs from the manifest")
    source_commits = set()
    for arm in arms:
        state = states[arm]
        snapshot = snapshots[arm]
        spec = campaign_specs[arm]
        winner = winners[arm]
        loss_id = winner.get("loss_spec", {}).get("id")
        if (
            loss_id not in loss_specs
            or winner["loss_spec"].get("sha256") != loss_spec_sha256(loss_specs[loss_id])
        ):
            raise ValueError(f"{arm} winner LossSpec provenance is inconsistent")
        if state.get("schema") != STATE_SCHEMA or snapshot.get("schema") != SNAPSHOT_SCHEMA:
            raise ValueError(f"{arm} state or snapshot schema is invalid")
        if (
            state.get("campaign_id") != arm
            or state.get("revision") != snapshot.get("revision")
            or state.get("revision") != winner.get("campaign_revision")
        ):
            raise ValueError(f"{arm} revision chain is inconsistent")
        if snapshot.get("campaign") != spec:
            raise ValueError(f"{arm} snapshot campaign differs from the manifest spec")
        if snapshot.get("loss_spec") != loss_specs[loss_id]:
            raise ValueError(f"{arm} snapshot LossSpec differs from the manifest spec")
        expected = spec["budget"]["max_suggestions"]
        suggestions = state.get("suggestions", [])
        if len(suggestions) != expected:
            raise ValueError(f"{arm} has {len(suggestions)}/{expected} suggestions")
        terminal = {"observed_complete", "observed_invalid"}
        if any(item.get("status") not in terminal for item in suggestions):
            raise ValueError(f"{arm} contains unresolved suggestions")
        matched = [
            item for item in suggestions
            if item.get("suggestion", {}).get("suggestion_id") == winner["suggestion_id"]
        ]
        if len(matched) != 1 or matched[0].get("status") != "observed_complete":
            raise ValueError(f"{arm} frozen winner is not one complete suggestion")
        source = snapshot.get("source", {})
        if source.get("tree_dirty") is not False or not isinstance(source.get("commit"), str):
            raise ValueError(f"{arm} was not run from a clean pinned source")
        source_commits.add(source["commit"])
    if source_commits != {freeze.get("source_commit")}:
        raise ValueError("campaign snapshots and winner freeze use different source commits")

    held_out_seeds = list(manifest["common_held_out_evaluation_seeds"])
    if evaluation_snapshot.get("held_out_seeds") != held_out_seeds:
        raise ValueError("held-out snapshot uses an unexpected seed set")
    if (
        evaluation_snapshot.get("metric_suite") != manifest["held_out_metric_suite"]
        or evaluation_snapshot.get("held_out_evaluator")
        != manifest["held_out_evaluator"]
    ):
        raise ValueError("held-out snapshot metric contract differs from the manifest")
    snapshot_runs = evaluation_snapshot.get("runs", [])
    expected_runs = len(arms) * len(held_out_seeds)
    if len(snapshot_runs) != expected_runs:
        raise ValueError(f"held-out snapshot has {len(snapshot_runs)}/{expected_runs} runs")
    for arm in arms:
        arm_runs = [item for item in snapshot_runs if item.get("campaign_id") == arm]
        if sorted(item.get("seed") for item in arm_runs) != sorted(held_out_seeds):
            raise ValueError(f"{arm} held-out seeds are incomplete")
        if any(
            item.get("design_id") != winners[arm].get("design_id")
            or item.get("loss_spec_id") != winners[arm]["loss_spec"].get("id")
            for item in arm_runs
        ):
            raise ValueError(f"{arm} held-out runs do not use its frozen winner")
    expected_run_ids = {item["run_id"] for item in snapshot_runs}
    if set(report.get("common_run_evaluations", {})) != expected_run_ids:
        raise ValueError("common held-out evaluations do not match the sealed run set")

    losses = report.get("loss_by_frozen_winner", {})
    if set(losses) != set(arms):
        raise ValueError("cross-evaluation rows differ from frozen arms")
    loss_ids = {winner["loss_spec"]["id"] for winner in winners.values()}
    if len(loss_ids) != 3:
        raise ValueError("three distinct LossSpecs are required")
    for arm in arms:
        if set(losses[arm]) != loss_ids:
            raise ValueError(f"{arm} cross-evaluation is not a complete 3x3 matrix")
        expected_arm_run_ids = {
            item["run_id"] for item in snapshot_runs if item["campaign_id"] == arm
        }
        for loss_id, cell in losses[arm].items():
            values = cell.get("held_out_seed_values", [])
            measured = _seed_map(values, "loss")
            weight = float(loss_specs[loss_id]["across_seeds"]["dispersion_weight"])
            expected_loss = statistics.fmean(measured.values()) + weight * statistics.pstdev(
                measured.values()
            ) if measured else None
            if (
                cell.get("status") != "complete"
                or not _finite(cell.get("loss"))
                or sorted(measured) != sorted(held_out_seeds)
                or {item.get("run_id") for item in values} != expected_arm_run_ids
                or any(item.get("missing_reason") is not None for item in values)
                or expected_loss is None
                or not math.isclose(float(cell["loss"]), expected_loss, abs_tol=1e-12)
            ):
                raise ValueError(f"incomplete cross-evaluation cell {arm}/{loss_id}")
    if report.get("raw_registry_report", {}).get("report_errors"):
        raise ValueError("held-out report contains evaluation errors")
    declared_profiles = {
        (item["id"], item.get("slice"))
        for item in manifest["held_out_metric_suite"]
    }
    for arm, profiles in report.get("held_out_metric_profiles", {}).items():
        if arm not in arms:
            raise ValueError(f"unexpected metric-profile arm {arm}")
        actual_profiles = {(item["id"], item.get("slice")) for item in profiles}
        if actual_profiles != declared_profiles:
            raise ValueError(f"held-out metric suite is incomplete for {arm}")
        for profile in profiles:
            if not profile.get("complete"):
                raise ValueError(
                    f"incomplete held-out metric {arm}/{profile.get('id')}/{profile.get('slice')}"
                )
            if len(profile.get("seed_values", [])) != len(held_out_seeds):
                raise ValueError(f"held-out metric has the wrong seed count for {arm}")
            seed_values = profile["seed_values"]
            if sorted(item.get("seed") for item in seed_values) != sorted(held_out_seeds):
                raise ValueError(f"held-out metric has the wrong seed set for {arm}")
            if any(
                item.get("status") != "measured"
                or item.get("missing_reason") is not None
                for item in seed_values
            ):
                raise ValueError(f"held-out metric has non-measured values for {arm}")
            values = [item.get("value") for item in seed_values]
            label = f"{arm}/{profile.get('id')}/{profile.get('slice')}"
            if all(_finite(value) for value in values):
                _verify_summary(
                    profile.get("summary", {}),
                    _numeric_summary(float(value) for value in values),
                    label=label,
                )
                if profile.get("structured_summary"):
                    raise ValueError(f"{label} mixes scalar and structured summaries")
            elif all(isinstance(value, Mapping) for value in values):
                expected_structured = _structured_summary(values)
                actual_structured = profile.get("structured_summary", {})
                if set(actual_structured) != set(expected_structured):
                    raise ValueError(f"{label} structured summary paths are inconsistent")
                for path, expected_summary in expected_structured.items():
                    _verify_summary(
                        actual_structured[path],
                        expected_summary,
                        label=f"{label}/{path}",
                    )
                if profile.get("summary") != _numeric_summary([]):
                    raise ValueError(f"{label} mixes structured and scalar summaries")
            else:
                raise ValueError(f"{label} contains non-finite or mixed metric values")
    if set(report.get("held_out_metric_profiles", {})) != set(arms):
        raise ValueError("held-out metric profiles are missing an arm")
    required_analyses = {
        "rank_reversal",
        "paired_tradeoffs",
        "gaming_flags",
        "generalization",
        "secondary_resolution",
    }
    if set(report.get("analyses", {})) != required_analyses:
        raise ValueError("cross-evaluation report lacks preregistered analyses")
    recomputed_analyses = build_analyses(
        freeze=freeze,
        profiles=report["held_out_metric_profiles"],
        losses=report["loss_by_frozen_winner"],
    )
    if _analysis_digest(recomputed_analyses) != _analysis_digest(report["analyses"]):
        raise ValueError("cross-evaluation analyses do not match recomputed inputs")
    rank_columns = report["analyses"]["rank_reversal"].get("columns", {})
    for loss_id in loss_ids:
        column = rank_columns.get(f"loss:{loss_id}", {})
        if (
            set(column.get("ranks", {})) != set(arms)
            or set(column.get("raw_order", [])) != set(arms)
            or len(column.get("raw_order", [])) != len(arms)
        ):
            raise ValueError(f"rank-reversal analysis is incomplete for {loss_id}")
    return arms, held_out_seeds


def _cross_objective_uncertainty(
    report: Mapping[str, Any], arms: list[str], loss_specs: Mapping[str, Mapping[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cells: dict[str, Any] = {}
    paired: list[dict[str, Any]] = []
    loss_ids = sorted(next(iter(report["loss_by_frozen_winner"].values())))
    seed_maps: dict[tuple[str, str], dict[int, float]] = {}
    for arm in arms:
        cells[arm] = {}
        for loss_id in loss_ids:
            item = report["loss_by_frozen_winner"][arm][loss_id]
            values = _seed_map(item["held_out_seed_values"], "loss")
            seed_maps[(arm, loss_id)] = values
            cells[arm][loss_id] = _aggregate_loss_uncertainty(
                values.values(),
                dispersion_weight=float(
                    loss_specs[loss_id]["across_seeds"]["dispersion_weight"]
                ),
                estimate=float(item["loss"]),
            )
    for loss_id in loss_ids:
        for index, left in enumerate(arms):
            for right in arms[index + 1:]:
                paired.append({
                    "kind": "held_out_loss",
                    "measure_id": loss_id,
                    "direction": "minimize",
                    "left_arm": left,
                    "right_arm": right,
                    **_paired_uncertainty(
                        seed_maps[(left, loss_id)], seed_maps[(right, loss_id)]
                    ),
                })
    return cells, paired


def _metric_uncertainty(
    report: Mapping[str, Any], arms: list[str]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    metrics: dict[str, Any] = {arm: {} for arm in arms}
    seed_maps: dict[tuple[str, str], dict[int, float]] = {}
    directions: dict[str, str] = {}
    for arm in arms:
        for profile in report["held_out_metric_profiles"][arm]:
            key = profile["id"] + (f"/{profile['slice']}" if profile.get("slice") else "")
            values = _seed_map(profile["seed_values"], "value")
            if not values:
                continue
            metrics[arm][key] = {
                "direction": profile["direction"],
                **_uncertainty(values.values()),
            }
            seed_maps[(arm, key)] = values
            directions[key] = profile["direction"]
    paired = []
    for key in sorted(directions):
        if not all((arm, key) in seed_maps for arm in arms):
            continue
        for index, left in enumerate(arms):
            for right in arms[index + 1:]:
                paired.append({
                    "kind": "held_out_metric",
                    "measure_id": key,
                    "direction": directions[key],
                    "left_arm": left,
                    "right_arm": right,
                    **_paired_uncertainty(seed_maps[(left, key)], seed_maps[(right, key)]),
                })
    return metrics, paired


def _flatten_design(value: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    def visit(prefix: str, item: Any) -> None:
        if isinstance(item, Mapping):
            for key in sorted(item):
                visit(f"{prefix}.{key}" if prefix else str(key), item[key])
        elif isinstance(item, list):
            result[prefix] = json.dumps(item, sort_keys=True, separators=(",", ":"))
        else:
            result[prefix] = item

    visit("", value)
    return result


def build_slice(
    *,
    manifest_path: Path,
    study_root: Path,
    campaign_roots: Mapping[str, Path],
    classification: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _read_json(manifest_path)
    campaign_specs = {}
    loss_specs = {}
    for relative in manifest.get("campaigns", []):
        path = Path(relative)
        if not path.is_absolute():
            path = ROOT / path
        spec = _read_json(path)
        campaign_specs[spec["id"]] = spec
        loss_path = Path(spec["loss_spec"])
        if not loss_path.is_absolute():
            loss_path = ROOT / loss_path
        loss_spec = _read_json(loss_path)
        loss_specs[loss_spec["id"]] = loss_spec
    if set(campaign_roots) != set(campaign_specs):
        raise ValueError("--campaign-root assignments must match manifest campaigns exactly")

    freeze_path = study_root / "winner-freeze.json"
    evaluation_snapshot_path = study_root / "held-out-evaluation/snapshot.json"
    report_path = study_root / "held-out-evaluation/cross-evaluation.json"
    held_out_registry_path = study_root / "held-out-evaluation/runs.sqlite3"
    freeze = _read_json(freeze_path)
    evaluation_snapshot = _read_json(evaluation_snapshot_path)
    report = _read_json(report_path)
    states = {
        arm: _read_json(root / "campaign-state.json")
        for arm, root in campaign_roots.items()
    }
    snapshots = {
        arm: _read_json(root / "campaign-snapshot.json")
        for arm, root in campaign_roots.items()
    }
    arms, held_out_seeds = _validate_inputs(
        manifest=manifest,
        campaign_specs=campaign_specs,
        loss_specs=loss_specs,
        states=states,
        snapshots=snapshots,
        freeze=freeze,
        evaluation_snapshot=evaluation_snapshot,
        report=report,
    )

    runtime_by_arm = {}
    for arm in arms:
        spec = campaign_specs[arm]
        expected = spec["budget"]["max_suggestions"] * len(
            manifest["common_optimization_seeds"]
        )
        runtime_by_arm[arm] = _registry_summary(
            campaign_roots[arm] / "runs.sqlite3",
            expected_runs=expected,
            label=arm,
            allow_terminal_failures=True,
        )
        commits = runtime_by_arm[arm]["source_commits"]
        if commits and commits != [freeze["source_commit"]]:
            raise ValueError(f"{arm} registry source commit differs from the freeze")
    held_out_runtime = _registry_summary(
        held_out_registry_path,
        expected_runs=len(arms) * len(held_out_seeds),
        label="held-out evaluation",
    )
    if held_out_runtime["adopted_logical_runs"]:
        raise ValueError("held-out evaluation unexpectedly contains adopted runs")

    winner_loss_ids = {item["loss_spec"]["id"] for item in freeze["winners"]}
    if set(loss_specs) != winner_loss_ids:
        raise ValueError("campaign LossSpecs differ from the winner freeze")
    cross_uncertainty, loss_effects = _cross_objective_uncertainty(
        report, arms, loss_specs
    )
    metric_uncertainty, metric_effects = _metric_uncertainty(report, arms)
    winners = {item["campaign_id"]: item for item in freeze["winners"]}
    distinct_designs = len({item["design_id"] for item in winners.values()})
    loss_columns = {
        key: value
        for key, value in report["analyses"]["rank_reversal"]["columns"].items()
        if key.startswith("loss:")
    }
    best_by_loss = {
        key.removeprefix("loss:"): value.get("raw_order", [None])[0]
        for key, value in loss_columns.items()
    }
    rank_orders = {
        key.removeprefix("loss:"): value.get("raw_order", [])
        for key, value in loss_columns.items()
    }
    rank_reversal = len({tuple(order) for order in rank_orders.values()}) > 1
    best_system_changed = len(set(best_by_loss.values())) > 1
    triggered_gaming = [
        item for item in report["analyses"]["gaming_flags"] if item.get("triggered")
    ]
    loss_effects_excluding_zero = [
        item
        for item in loss_effects
        if item["ci95_low"] > 0 or item["ci95_high"] < 0
    ]
    arms_by_design: dict[str, list[str]] = defaultdict(list)
    for arm, winner in winners.items():
        arms_by_design[winner["design_id"]].append(arm)
    optimization_runtime_total = sum(
        value["physical_run_wall_seconds_total"] for value in runtime_by_arm.values()
    )
    figure_summary = normalize_report(
        report,
        states,
        classification=classification,
    )
    figure_summary["cross_evaluation"]["uncertainty"] = cross_uncertainty

    provenance_files = {
        "study_manifest": manifest_path,
        "winner_freeze": freeze_path,
        "evaluation_snapshot": evaluation_snapshot_path,
        "cross_evaluation_report": report_path,
        "held_out_registry": held_out_registry_path,
    }
    for arm, root in campaign_roots.items():
        provenance_files[f"{arm}/state"] = root / "campaign-state.json"
        provenance_files[f"{arm}/snapshot"] = root / "campaign-snapshot.json"
        provenance_files[f"{arm}/registry"] = root / "runs.sqlite3"
    source_hashes = {
        key: {"path": _provenance_path(path), "sha256": _file_sha(path)}
        for key, path in provenance_files.items()
    }
    slice_data = {
        "schema": SLICE_SCHEMA,
        "provenance": {
            "data_classification": classification,
            "study_id": manifest["id"],
            "study_version": manifest["version"],
            "study_revision": freeze["study_revision"],
            "source_commit": freeze["source_commit"],
            "winner_freeze_sha256": freeze["freeze_sha256"],
            "source_files": source_hashes,
        },
        "experimental_contract": {
            "independent_variable": "LossSpec",
            "controlled": {
                "design_space": "identical across arms",
                "optimizer": campaign_specs[arms[0]]["optimizer"],
                "suggestion_budget_per_arm": campaign_specs[arms[0]]["budget"][
                    "max_suggestions"
                ],
                "optimization_seeds": manifest["common_optimization_seeds"],
                "held_out_seeds": held_out_seeds,
            },
            "decision_policy": "report_only",
            "claim_boundary": (
                "The study identifies objective-conditioned simulated systems and "
                "trade-offs; it does not identify a universally best real science policy."
            ),
        },
        "winners": {
            arm: {
                "loss_spec": winners[arm]["loss_spec"],
                "proposal_index": winners[arm]["proposal_index"],
                "suggestion_id": winners[arm]["suggestion_id"],
                "design_id": winners[arm]["design_id"],
                "system_fingerprint": winners[arm]["system_fingerprint"],
                "optimization_loss": winners[arm]["optimization_observation"]["loss"],
                "design": winners[arm]["source_candidate"],
                "design_flat": _flatten_design(winners[arm]["source_candidate"]),
            }
            for arm in arms
        },
        "cross_objective_evaluations": report["loss_by_frozen_winner"],
        "held_out_metric_profiles": report["held_out_metric_profiles"],
        "cross_objective_uncertainty": cross_uncertainty,
        "held_out_metric_uncertainty": metric_uncertainty,
        "paired_effects": loss_effects + metric_effects,
        "preregistered_analyses": report["analyses"],
        "conclusions": {
            "distinct_frozen_designs": distinct_designs,
            "objectives_selected_different_systems": distinct_designs > 1,
            "best_system_by_held_out_loss": best_by_loss,
            "rank_order_by_held_out_loss": rank_orders,
            "rank_reversal_across_losses": rank_reversal,
            "best_system_changed_across_losses": best_system_changed,
            "triggered_gaming_flags": triggered_gaming,
            "held_out_loss_pairwise_contrasts": len(loss_effects),
            "held_out_loss_pairwise_intervals_excluding_zero": len(
                loss_effects_excluding_zero
            ),
            "all_pairwise_held_out_loss_intervals_include_zero": not bool(
                loss_effects_excluding_zero
            ),
            "arms_by_frozen_design": {
                design: sorted(group) for design, group in sorted(arms_by_design.items())
            },
            "universal_winner_selected": False,
        },
        "runtime": {
            "optimization_by_arm": runtime_by_arm,
            "held_out_evaluation": held_out_runtime,
            "optimization_physical_wall_seconds_total": optimization_runtime_total,
            "held_out_physical_wall_seconds_total": held_out_runtime[
                "physical_run_wall_seconds_total"
            ],
            "all_physical_wall_seconds_total": (
                optimization_runtime_total
                + held_out_runtime["physical_run_wall_seconds_total"]
            ),
            "attempts_missing_wall_seconds": sum(
                item["attempts_missing_wall_seconds"]
                for item in runtime_by_arm.values()
            )
            + held_out_runtime["attempts_missing_wall_seconds"],
            "logical_optimization_runs": sum(
                item["logical_runs"] for item in runtime_by_arm.values()
            ),
            "physical_optimization_runs": sum(
                item["executed_physical_runs"] for item in runtime_by_arm.values()
            ),
            "adopted_optimization_runs": sum(
                item["adopted_logical_runs"] for item in runtime_by_arm.values()
            ),
            "terminal_failed_optimization_runs": sum(
                item["terminal_failed_logical_runs"]
                for item in runtime_by_arm.values()
            ),
        },
        "figure_data": figure_summary,
    }
    return slice_data, figure_summary


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _arm_label(figure_data: Mapping[str, Any], arm: str) -> str:
    return next(item["label"] for item in figure_data["arms"] if item["id"] == arm)


def _format_ci(item: Mapping[str, Any], digits: int = 3) -> str:
    point = item.get("estimate", item.get("mean"))
    return (
        f"{point:.{digits}f} "
        f"[{item['ci95_low']:.{digits}f}, {item['ci95_high']:.{digits}f}]"
    )


def _format_design_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    if value is None:
        return "--"
    return str(value)


def _tex_escape(value: Any) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(character, character) for character in str(value))


def _generated_text(slice_data: Mapping[str, Any]) -> tuple[str, str]:
    figure = slice_data["figure_data"]
    arms = [item["id"] for item in figure["arms"]]
    conclusions = slice_data["conclusions"]
    if conclusions["objectives_selected_different_systems"]:
        selection_sentence = (
            f"The three objectives selected {conclusions['distinct_frozen_designs']} "
            "distinct frozen institutional designs under otherwise identical search conditions."
        )
    else:
        selection_sentence = (
            "All three objectives selected the same frozen institutional design under this budget."
        )
    if conclusions["best_system_changed_across_losses"]:
        reversal_sentence = (
            "The identity of the best frozen system changed across held-out scoring losses, "
            "a descriptive rank reversal between the frozen designs."
        )
    elif conclusions["rank_reversal_across_losses"]:
        reversal_sentence = (
            "The ordering below the top system changed across held-out scoring losses, "
            "while the best frozen system remained the same."
        )
    else:
        reversal_sentence = (
            "No rank-order reversal was observed across the three held-out losses."
        )
    if conclusions["all_pairwise_held_out_loss_intervals_include_zero"]:
        uncertainty_sentence = (
            f"All {conclusions['held_out_loss_pairwise_contrasts']} paired held-out "
            "loss contrasts have 95% intervals containing zero, so five seeds do not "
            "establish stable pairwise superiority."
        )
    else:
        uncertainty_sentence = (
            f"{conclusions['held_out_loss_pairwise_intervals_excluding_zero']} of "
            f"{conclusions['held_out_loss_pairwise_contrasts']} paired held-out loss "
            "contrasts have 95% intervals excluding zero."
        )
    duplicated_designs = [
        group
        for group in conclusions["arms_by_frozen_design"].values()
        if len(group) > 1
    ]
    duplicate_sentence = ""
    if duplicated_designs:
        duplicate_sentence = (
            "The topic-entropy and review-burden objectives selected the same design; "
            "their arm-labelled held-out trajectories are independent stochastic "
            "repetitions, not distinct institutional systems."
        )
    runtime_hours = slice_data["runtime"]["all_physical_wall_seconds_total"] / 3600
    missing_runtime_attempts = slice_data["runtime"]["attempts_missing_wall_seconds"]
    held_out_runs = slice_data["runtime"]["held_out_evaluation"]["logical_runs"]
    held_out_seed_count = len(
        slice_data["experimental_contract"]["controlled"]["held_out_seeds"]
    )

    markdown = [
        "# Metric-conditioned optimization results (generated)",
        "",
        "> Generated only after the sealed three-arm optimization and common held-out split passed the completion gate.",
        "",
        selection_sentence,
        reversal_sentence,
        uncertainty_sentence,
        duplicate_sentence,
        "The experiment changes the optimization LossSpec, not the simulator, design space, optimizer, budget, or seeds. Narrow proxy objectives are contrasts, not normative recommendations, and the report-only protocol selects no universal winner.",
        "",
        "## Frozen systems and own-objective generalization",
        "",
        "| Optimization objective | Design | Proposal | Development loss | Held-out own loss (95% CI) | Generalization gap |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    table_rows = []
    for arm in arms:
        winner = slice_data["winners"][arm]
        loss_id = winner["loss_spec"]["id"]
        held = slice_data["cross_objective_uncertainty"][arm][loss_id]
        gap = figure["generalization"][arm][
            "generalization_gap_held_out_minus_optimization"
        ]
        markdown.append(
            f"| {_arm_label(figure, arm)} | `{winner['design_id']}` | "
            f"{winner['proposal_index'] + 1} | {winner['optimization_loss']:.3f} | "
            f"{_format_ci(held)} | {gap:.3f} |"
        )
        table_rows.append((arm, winner, loss_id, held, gap))
    markdown.extend([
        "",
        "## Institutional parameters selected by each objective",
        "",
        "| Parameter | " + " | ".join(_arm_label(figure, arm) for arm in arms) + " |",
        "|---|" + "---:|" * len(arms),
    ])
    design_parameters = sorted({
        key
        for arm in arms
        for key in slice_data["winners"][arm]["design_flat"]
    })
    for parameter in design_parameters:
        markdown.append(
            "| " + parameter + " | "
            + " | ".join(
                _format_design_value(
                    slice_data["winners"][arm]["design_flat"].get(parameter, "--")
                )
                for arm in arms
            )
            + " |"
        )
    markdown.extend([
        "",
        "## Runtime and provenance",
        "",
        f"The slice covers {slice_data['runtime']['logical_optimization_runs']} logical optimization runs, "
        f"{slice_data['runtime']['physical_optimization_runs']} physically executed optimization runs, "
        f"{slice_data['runtime']['adopted_optimization_runs']} provenance-linked adopted logical runs, "
        f"{slice_data['runtime']['terminal_failed_optimization_runs']} terminal technical failures retained without numeric penalties, "
        f"and {held_out_runs} held-out runs. Recorded attempt runtime totals at least {runtime_hours:.2f} hours; "
        f"{missing_runtime_attempts} interrupted attempt(s) lack a recoverable wall-time value. "
        f"Source commit: `{slice_data['provenance']['source_commit']}`; winner-freeze SHA-256: "
        f"`{slice_data['provenance']['winner_freeze_sha256']}`.",
        "",
        "The full cross-objective matrix, paired effects, metric uncertainty, triggered gaming diagnostics, and source-file hashes are in `metric-conditioned-paper-slice.json`.",
        "",
    ])

    tex = [
        "% Generated by scripts.reports.metric_conditioned_paper_slice; do not edit.",
        r"\subsection{Completed loss-conditioned comparison}",
        " ".join(
            _tex_escape(sentence)
            for sentence in (
                selection_sentence,
                reversal_sentence,
                uncertainty_sentence,
                duplicate_sentence,
            )
            if sentence
        ),
        r"The experimental intervention is the optimization \code{LossSpec}; the simulator, design space, optimizer, budget, and seeds are held fixed. The proxy objectives are contrasts, not normative recommendations, and the report-only protocol selects no universal winner.",
        r"\begin{table}[t]",
        f"\\caption{{Frozen systems and own-objective generalization. Intervals are exact nonparametric 95\\% bootstrap percentile intervals for the complete LossSpec aggregate over the {held_out_seed_count} common held-out seeds.}}",
        r"\label{tab:metric-conditioned-heldout-winners}",
        r"\centering\small",
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Objective & Proposal & Development & Held-out [95\% CI] & Gap \\",
        r"\midrule",
    ]
    for arm, winner, _loss_id, held, gap in table_rows:
        tex.append(
            f"{_tex_escape(_arm_label(figure, arm))} & {winner['proposal_index'] + 1} & "
            f"{winner['optimization_loss']:.3f} & {_tex_escape(_format_ci(held))} & {gap:.3f} \\\\" 
        )
    tex.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
        r"\begin{table}[t]",
        r"\caption{Institutional parameters of the three frozen systems. Differences are consequences of changing the optimization objective under a shared search protocol.}",
        r"\label{tab:metric-conditioned-designs}",
        r"\centering\small",
        r"\resizebox{\linewidth}{!}{%",
        r"\begin{tabular}{l" + "l" * len(arms) + "}",
        r"\toprule",
        "Parameter & " + " & ".join(
            _tex_escape(_arm_label(figure, arm)) for arm in arms
        ) + r" \\",
        r"\midrule",
    ])
    for parameter in design_parameters:
        tex.append(
            _tex_escape(parameter)
            + " & "
            + " & ".join(
                _tex_escape(
                    _format_design_value(
                        slice_data["winners"][arm]["design_flat"].get(parameter, "--")
                    )
                )
                for arm in arms
            )
            + r" \\"
        )
    tex.extend([
        r"\bottomrule",
        r"\end{tabular}%",
        r"}",
        r"\end{table}",
        r"\begin{figure}[t]",
        r"\centering",
        r"\includegraphics[width=0.92\linewidth]{generated/metric-conditioned/figures/metric-conditioned-cross-evaluation.pdf}",
        r"\caption{Cross-evaluation of frozen systems. Annotations give the held-out LossSpec aggregate and its exact-bootstrap 95\% interval; color gives within-loss rank because loss units differ.}",
        r"\label{fig:metric-conditioned-cross-evaluation}",
        r"\end{figure}",
        r"\begin{figure}[t]",
        r"\centering",
        r"\includegraphics[width=\linewidth]{generated/metric-conditioned/figures/metric-conditioned-objective-trajectories.pdf}",
        r"\caption{Development trajectories in arm-specific units. Stars mark the simultaneously frozen winners.}",
        r"\label{fig:metric-conditioned-trajectories}",
        r"\end{figure}",
        r"\begin{figure}[t]",
        r"\centering",
        r"\includegraphics[width=\linewidth]{generated/metric-conditioned/figures/metric-conditioned-tradeoff-rank-generalization.pdf}",
        r"\caption{Held-out trade-off, rank reversal, proxy-gaming flags, and generalization diagnostics. Flags are diagnostics rather than validity failures or promotion vetoes; the panels characterize objective dependence rather than a universal optimum.}",
        r"\label{fig:metric-conditioned-diagnostics}",
        r"\end{figure}",
        r"\paragraph{Runtime and provenance.}",
        f"The slice contains {slice_data['runtime']['logical_optimization_runs']} logical optimization runs, "
        f"{slice_data['runtime']['physical_optimization_runs']} physical optimization runs, "
        f"{slice_data['runtime']['adopted_optimization_runs']} adopted logical runs, "
        f"{slice_data['runtime']['terminal_failed_optimization_runs']} terminal technical failures retained without numeric penalties, "
        f"and {held_out_runs} held-out runs "
        f"(at least {runtime_hours:.2f} recorded attempt-runtime hours; "
        f"{missing_runtime_attempts} interrupted attempt(s) lack wall time). Source commit: "
        f"\\code{{{_tex_escape(slice_data['provenance']['source_commit'])}}}; winner freeze: "
        f"\\code{{{_tex_escape(slice_data['provenance']['winner_freeze_sha256'])}}}.",
        "",
    ])
    return "\n".join(markdown), "\n".join(tex)


def write_outputs(
    slice_data: Mapping[str, Any],
    figure_data: Mapping[str, Any],
    output_dir: Path,
    *,
    formats: tuple[str, ...],
) -> list[Path]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        figures_dir = stage / "figures"
        generated = render(figure_data, figures_dir, formats=formats)
        json_path = stage / "metric-conditioned-paper-slice.json"
        json_path.write_text(
            json.dumps(slice_data, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        figure_path = stage / "metric-conditioned-figure-data.json"
        figure_path.write_text(
            json.dumps(figure_data, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        arms = [item["id"] for item in figure_data["arms"]]
        loss_rows = []
        for arm in arms:
            for loss_id, item in slice_data["cross_objective_uncertainty"][arm].items():
                loss_rows.append({"arm": arm, "loss_id": loss_id, **item})
        _write_csv(
            stage / "cross-objective-losses.csv",
            ["arm", "loss_id", "n", "estimate", "per_seed_mean", "sample_sd", "standard_error", "ci95_low", "ci95_high", "dispersion_weight", "bootstrap_resamples", "method"],
            loss_rows,
        )
        metric_rows = []
        for arm in arms:
            for metric_id, item in slice_data["held_out_metric_uncertainty"][arm].items():
                metric_rows.append({"arm": arm, "metric_id": metric_id, **item})
        _write_csv(
            stage / "held-out-metrics.csv",
            ["arm", "metric_id", "direction", "n", "mean", "sample_sd", "standard_error", "ci95_low", "ci95_high", "method"],
            metric_rows,
        )
        _write_csv(
            stage / "paired-effects.csv",
            ["kind", "measure_id", "direction", "left_arm", "right_arm", "n", "mean", "sample_sd", "standard_error", "ci95_low", "ci95_high", "method", "estimand", "seeds"],
            slice_data["paired_effects"],
        )
        design_fields = sorted({
            key
            for arm in arms
            for key in slice_data["winners"][arm]["design_flat"]
        })
        _write_csv(
            stage / "winner-designs.csv",
            ["arm", "loss_id", "design_id", "proposal_index", *design_fields],
            [
                {
                    "arm": arm,
                    "loss_id": slice_data["winners"][arm]["loss_spec"]["id"],
                    "design_id": slice_data["winners"][arm]["design_id"],
                    "proposal_index": slice_data["winners"][arm]["proposal_index"],
                    **slice_data["winners"][arm]["design_flat"],
                }
                for arm in arms
            ],
        )
        runtime_rows = [
            {"stage": arm, **value}
            for arm, value in slice_data["runtime"]["optimization_by_arm"].items()
        ] + [{"stage": "held-out-evaluation", **slice_data["runtime"]["held_out_evaluation"]}]
        _write_csv(
            stage / "runtime-summary.csv",
            ["stage", "logical_runs", "complete_logical_runs", "terminal_failed_logical_runs", "executed_physical_runs", "adopted_logical_runs", "physical_run_wall_seconds_total", "attempts", "attempts_missing_wall_seconds", "failed_attempts", "registry_sha256", "source_commits"],
            runtime_rows,
        )
        markdown, tex = _generated_text(slice_data)
        (stage / "metric-conditioned-results.generated.md").write_text(
            markdown, encoding="utf-8"
        )
        (stage / "metric-conditioned-results.generated.tex").write_text(
            tex, encoding="utf-8"
        )
        artifacts = sorted(path for path in stage.rglob("*") if path.is_file())
        manifest = {
            "schema": "scienceutopia.generated-artifact-manifest.v1",
            "source_slice_sha256": _file_sha(json_path),
            "artifacts": [
                {
                    "path": str(path.relative_to(stage)),
                    "sha256": _file_sha(path),
                    "bytes": path.stat().st_size,
                }
                for path in artifacts
            ],
        }
        (stage / "artifact-manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(stage, output_dir)
        return [output_dir / path.relative_to(stage) for path in artifacts] + [
            output_dir / "artifact-manifest.json"
        ]
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def _assignment(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("campaign root must be ARM=PATH")
    arm, path = value.split("=", 1)
    return arm, Path(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--study-root", required=True, type=Path)
    parser.add_argument("--campaign-root", action="append", required=True, type=_assignment)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--classification",
        choices=("experimental", "synthetic-test"),
        default="experimental",
    )
    parser.add_argument("--formats", default="pdf,png")
    args = parser.parse_args(argv)
    classification = SYNTHETIC if args.classification == "synthetic-test" else EXPERIMENTAL
    output = args.output_dir.resolve()
    if classification == SYNTHETIC and (
        output == PAPER_OUTPUT.resolve() or PAPER_OUTPUT.resolve() in output.parents
    ):
        raise ValueError("synthetic fixtures may not be published into the paper output")
    campaign_roots = dict(args.campaign_root)
    if len(campaign_roots) != len(args.campaign_root):
        raise ValueError("campaign roots contain duplicate arm assignments")
    slice_data, figure_data = build_slice(
        manifest_path=args.manifest,
        study_root=args.study_root,
        campaign_roots=campaign_roots,
        classification=classification,
    )
    formats = tuple(item.strip() for item in args.formats.split(",") if item.strip())
    for path in write_outputs(slice_data, figure_data, args.output_dir, formats=formats):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
