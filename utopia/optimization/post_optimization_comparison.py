"""Winner-only cross-objective comparison on sealed development evidence.

This module consumes the output of ``metric_conditioned_completion``.  It
does not open campaign registries, simulator outputs, or held-out artifacts.
The three caller-supplied winner fingerprints must match the simultaneous
freeze before any comparison is returned.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re
import statistics
from typing import Any, Mapping

from utopia.optimization.metric_conditioned_completion import (
    canonical_report_sha256,
    validate_completion_report,
)


REPORT_SCHEMA = "scienceutopia.metric-conditioned-post-optimization-comparison.v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _finite(value: Any, context: str) -> float:
    if type(value) not in {int, float} or not math.isfinite(value):
        raise ValueError(f"{context} must be finite")
    return float(value)


def _average_ranks(values: Mapping[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    ranks: dict[str, float] = {}
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        rank = ((index + 1) + end) / 2
        for arm, _ in ordered[index:end]:
            ranks[arm] = rank
        index = end
    return ranks


def _dominates(left: Mapping[str, float], right: Mapping[str, float]) -> bool:
    keys = set(left)
    if keys != set(right) or not keys:
        raise ValueError("Pareto vectors must have the same non-empty objective set")
    return all(left[key] <= right[key] for key in keys) and any(
        left[key] < right[key] for key in keys
    )


def _winner_candidate(arm: str, arm_report: Mapping[str, Any]) -> dict[str, Any]:
    key = arm_report.get("frozen_winner_candidate_key")
    matches = [
        candidate for candidate in arm_report.get("candidates", [])
        if candidate.get("candidate_key") == key
    ]
    if len(matches) != 1:
        raise ValueError(f"{arm} frozen winner candidate is missing or ambiguous")
    return deepcopy(matches[0])


def _validated_cell(
    value: Mapping[str, Any],
    *,
    arm: str,
    loss_id: str,
) -> dict[str, Any]:
    expected = {"loss", "mean", "population_sd", "seed_values", "uncertainty"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{arm}/{loss_id} cell fields differ from the completion contract")
    loss = _finite(value["loss"], f"{arm}/{loss_id} aggregate loss")
    mean = _finite(value["mean"], f"{arm}/{loss_id} seed mean")
    population_sd = _finite(
        value["population_sd"], f"{arm}/{loss_id} population sd"
    )
    if population_sd < 0:
        raise ValueError(f"{arm}/{loss_id} population sd must be non-negative")
    seed_values = value["seed_values"]
    if not isinstance(seed_values, list) or len(seed_values) != 3:
        raise ValueError(f"{arm}/{loss_id} must contain three development seeds")
    parsed_seeds = []
    for seed in seed_values:
        if not isinstance(seed, Mapping) or set(seed) != {
            "seed", "run_id", "loss", "execution_mode"
        }:
            raise ValueError(f"{arm}/{loss_id} seed record fields are invalid")
        if type(seed["seed"]) is not int:
            raise ValueError(f"{arm}/{loss_id} seed must be an integer")
        if seed["execution_mode"] not in {"executed", "adopted"}:
            raise ValueError(f"{arm}/{loss_id} execution mode is invalid")
        parsed_seeds.append({
            "seed": seed["seed"],
            "run_id": str(seed["run_id"]),
            "loss": _finite(seed["loss"], f"{arm}/{loss_id} seed loss"),
            "execution_mode": seed["execution_mode"],
        })
    if len({item["seed"] for item in parsed_seeds}) != 3:
        raise ValueError(f"{arm}/{loss_id} development seeds are not unique")
    losses = [item["loss"] for item in parsed_seeds]
    if not math.isclose(mean, statistics.fmean(losses), rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError(f"{arm}/{loss_id} seed mean does not recompute")
    if not math.isclose(
        population_sd, statistics.pstdev(losses), rel_tol=1e-12, abs_tol=1e-12
    ):
        raise ValueError(f"{arm}/{loss_id} seed dispersion does not recompute")
    uncertainty = value["uncertainty"]
    expected_uncertainty = {"method", "resamples", "ci95_low", "ci95_high"}
    if not isinstance(uncertainty, Mapping) or set(uncertainty) != expected_uncertainty:
        raise ValueError(f"{arm}/{loss_id} uncertainty contract is invalid")
    if (
        uncertainty["method"] != "exact_seed_bootstrap_percentile"
        or uncertainty["resamples"] != 27
    ):
        raise ValueError(f"{arm}/{loss_id} uncertainty method is invalid")
    ci_low = _finite(uncertainty["ci95_low"], f"{arm}/{loss_id} CI low")
    ci_high = _finite(uncertainty["ci95_high"], f"{arm}/{loss_id} CI high")
    if ci_low > ci_high:
        raise ValueError(f"{arm}/{loss_id} uncertainty interval is reversed")
    return {
        "loss": loss,
        "mean": mean,
        "population_sd": population_sd,
        "seed_min": min(losses),
        "seed_max": max(losses),
        "seed_values": sorted(parsed_seeds, key=lambda item: item["seed"]),
        "uncertainty": {
            "method": uncertainty["method"],
            "resamples": uncertainty["resamples"],
            "ci95_low": ci_low,
            "ci95_high": ci_high,
        },
    }


def build_post_optimization_comparison(
    completion_report: Mapping[str, Any],
    winner_fingerprints: Mapping[str, str],
) -> dict[str, Any]:
    """Build a 3×3 winner comparison without accessing held-out evidence."""

    validate_completion_report(completion_report)
    boundary = completion_report["evidence_boundary"]
    if boundary.get("split") != "development_only" or boundary.get(
        "held_out_consumed"
    ) is not False:
        raise ValueError("comparison requires a sealed development-only completion report")
    arms = sorted(completion_report["arms"])
    if set(winner_fingerprints) != set(arms):
        raise ValueError("winner fingerprint arm set differs from the completion report")
    for arm, fingerprint in winner_fingerprints.items():
        if not isinstance(fingerprint, str) or _SHA256.fullmatch(fingerprint) is None:
            raise ValueError(f"{arm} winner fingerprint must be a lowercase sha256")

    frozen_records = {
        item["campaign_id"]: item for item in completion_report["frozen_winners"]
    }
    if set(frozen_records) != set(arms):
        raise ValueError("completion winner freeze arm set is invalid")
    source_matrix = completion_report["development_cross_objective"][
        "frozen_winner_matrix"
    ]
    loss_ids = sorted(
        completion_report["development_cross_objective"]["candidate_rankings"]
    )
    if len(loss_ids) != 3:
        raise ValueError("comparison requires exactly three LossSpecs")

    winner_rows: dict[str, Any] = {}
    common_seeds: set[int] | None = None
    for arm in arms:
        arm_report = completion_report["arms"][arm]
        candidate = _winner_candidate(arm, arm_report)
        fingerprint = winner_fingerprints[arm]
        if (
            candidate.get("system_fingerprint") != fingerprint
            or frozen_records[arm].get("system_fingerprint") != fingerprint
        ):
            raise ValueError(f"{arm} supplied fingerprint differs from the frozen winner")
        if set(candidate.get("cross_objective_losses", {})) != set(loss_ids):
            raise ValueError(f"{arm} winner lacks all three LossSpec evaluations")
        evaluations = {}
        for loss_id in loss_ids:
            if candidate["cross_objective_losses"][loss_id] != source_matrix[arm][loss_id]:
                raise ValueError(f"{arm}/{loss_id} frozen matrix differs from candidate evidence")
            cell = _validated_cell(
                candidate["cross_objective_losses"][loss_id], arm=arm, loss_id=loss_id
            )
            cell_seeds = {item["seed"] for item in cell["seed_values"]}
            if common_seeds is None:
                common_seeds = cell_seeds
            elif cell_seeds != common_seeds:
                raise ValueError("winner comparison does not use one common development seed set")
            evaluations[loss_id] = cell
        selection_loss_id = arm_report["loss_spec"]["id"]
        if selection_loss_id not in evaluations:
            raise ValueError(f"{arm} selection LossSpec is absent from the matrix")
        winner_rows[arm] = {
            "selected_by_arm": arm,
            "winner_candidate_key": candidate["candidate_key"],
            "design_id": candidate["design_id"],
            "system_fingerprint": fingerprint,
            "selection_loss_id": selection_loss_id,
            "execution_provenance": deepcopy(candidate["execution_provenance"]),
            "evaluations": evaluations,
        }

    ranks_by_loss = {}
    top_fingerprints = set()
    top_system_sets = set()
    for loss_id in loss_ids:
        values = {
            arm: winner_rows[arm]["evaluations"][loss_id]["loss"] for arm in arms
        }
        ranks = _average_ranks(values)
        order = sorted(arms, key=lambda arm: (values[arm], arm))
        best_value = values[order[0]]
        top_arms = [arm for arm in order if values[arm] == best_value]
        top_systems = sorted({winner_rows[arm]["system_fingerprint"] for arm in top_arms})
        top_fingerprints.update(top_systems)
        top_system_sets.add(tuple(top_systems))
        ranks_by_loss[loss_id] = {
            "direction": "minimize",
            "values": values,
            "ranks": ranks,
            "order": order,
            "top_arms": top_arms,
            "top_system_fingerprints": top_systems,
        }
        for arm in arms:
            winner_rows[arm]["evaluations"][loss_id]["rank_among_winners"] = ranks[arm]

    vectors = {
        arm: {
            loss_id: winner_rows[arm]["evaluations"][loss_id]["loss"]
            for loss_id in loss_ids
        }
        for arm in arms
    }
    dominance = []
    dominated = set()
    tradeoffs = []
    for index, left in enumerate(arms):
        for right in arms[index + 1:]:
            left_dominates = _dominates(vectors[left], vectors[right])
            right_dominates = _dominates(vectors[right], vectors[left])
            if left_dominates:
                dominated.add(right)
            if right_dominates:
                dominated.add(left)
            if left_dominates or right_dominates:
                dominance.append({
                    "dominator": left if left_dominates else right,
                    "dominated": right if left_dominates else left,
                })
            objective_deltas = []
            better = set()
            for loss_id in loss_ids:
                delta = vectors[left][loss_id] - vectors[right][loss_id]
                winner = left if delta < 0 else right if delta > 0 else "tie"
                if winner != "tie":
                    better.add(winner)
                objective_deltas.append({
                    "loss_id": loss_id,
                    "left_loss": vectors[left][loss_id],
                    "right_loss": vectors[right][loss_id],
                    "left_minus_right": delta,
                    "better": winner,
                })
            relation = (
                "left_dominates" if left_dominates else
                "right_dominates" if right_dominates else
                "trade_off" if len(better) == 2 else
                "all_tied"
            )
            tradeoffs.append({
                "left_arm": left,
                "right_arm": right,
                "relation": relation,
                "objective_deltas": objective_deltas,
            })

    execution = deepcopy(completion_report["execution"])
    attempt_counts = execution.get("attempt_status_counts", {})
    non_complete_attempts = sum(
        count for status, count in attempt_counts.items() if status != "complete"
    )
    arm_execution = {
        arm: deepcopy(completion_report["arms"][arm]["execution"]) for arm in arms
    }
    source_provenance = completion_report["provenance"]
    return {
        "schema": REPORT_SCHEMA,
        "study_id": completion_report["study_id"],
        "study_revision": completion_report["study_revision"],
        "data_classification": completion_report["data_classification"],
        "authorization": {
            "stage": "optimization_complete_before_held_out",
            "source_split": "development_only",
            "held_out_artifacts_read": False,
            "held_out_runs_created": False,
            "held_out_seeds_consumed": False,
            "candidate_selection": False,
            "optimization_update": False,
            "universal_winner_selection": False,
        },
        "input": {
            "completion_report_schema": completion_report["schema"],
            "completion_report_sha256": canonical_report_sha256(completion_report),
            "winner_fingerprints": dict(sorted(winner_fingerprints.items())),
        },
        "contract": {
            "arms": 3,
            "loss_specs": 3,
            "development_seeds_per_cell": 3,
            "matrix_cells": 9,
            "loss_direction": "minimize",
        },
        "winner_matrix": winner_rows,
        "objective_rankings": ranks_by_loss,
        "rank_reversal": {
            "observed": len(top_system_sets) > 1,
            "distinct_top_system_fingerprints": sorted(top_fingerprints),
        },
        "pareto": {
            "front_arms": [arm for arm in arms if arm not in dominated],
            "front_system_fingerprints": sorted({
                winner_rows[arm]["system_fingerprint"]
                for arm in arms if arm not in dominated
            }),
            "dominance_relations": dominance,
        },
        "tradeoffs": tradeoffs,
        "execution": {
            "global": execution,
            "by_arm": arm_execution,
            "non_complete_physical_attempts": non_complete_attempts,
            "logical_run_failures": 0,
        },
        "provenance": {
            "source_commit": source_provenance["source_commit"],
            "winner_freeze_sha256": source_provenance["winner_freeze_sha256"],
            "manifest_sha256": source_provenance["manifest_sha256"],
            "controlled_search_contract_sha256": deepcopy(
                source_provenance["controlled_search_contract_sha256"]
            ),
            "campaign_files": deepcopy(source_provenance["campaign_files"]),
        },
        "interpretation_guard": (
            "Development-seed cross-objective comparison only. Pareto status is "
            "conditional on the three declared LossSpecs and three frozen systems; "
            "it is not held-out generalization or a universal science-policy ranking."
        ),
    }


def validate_post_optimization_comparison(report: Mapping[str, Any]) -> None:
    if report.get("schema") != REPORT_SCHEMA:
        raise ValueError(f"expected {REPORT_SCHEMA}")
    authorization = report.get("authorization", {})
    expected_false = (
        "held_out_artifacts_read",
        "held_out_runs_created",
        "held_out_seeds_consumed",
        "candidate_selection",
        "optimization_update",
        "universal_winner_selection",
    )
    if authorization.get("source_split") != "development_only" or any(
        authorization.get(field) is not False for field in expected_false
    ):
        raise ValueError("post-optimization comparison crossed its authorization boundary")
    if report.get("contract") != {
        "arms": 3,
        "loss_specs": 3,
        "development_seeds_per_cell": 3,
        "matrix_cells": 9,
        "loss_direction": "minimize",
    }:
        raise ValueError("post-optimization comparison contract is incomplete")
    matrix = report.get("winner_matrix", {})
    rankings = report.get("objective_rankings", {})
    if len(matrix) != 3 or len(rankings) != 3:
        raise ValueError("post-optimization comparison must be a 3 by 3 matrix")
    if any(len(row.get("evaluations", {})) != 3 for row in matrix.values()):
        raise ValueError("post-optimization comparison must be a 3 by 3 matrix")
    if len(report.get("tradeoffs", [])) != 3:
        raise ValueError("post-optimization comparison needs all three arm pairs")
    if not report.get("pareto", {}).get("front_arms"):
        raise ValueError("post-optimization comparison has an empty Pareto front")
