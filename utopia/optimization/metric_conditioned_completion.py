"""Fail-closed development-split analysis for a completed metric study.

This module runs after all optimization arms are complete and their winners are
simultaneously frozen, but before held-out evaluation is planned.  It only
reads campaign artifacts.  The report cross-scores all development candidates
under every declared LossSpec and never treats those scores as held-out
evidence.
"""
from __future__ import annotations

from collections import Counter
from itertools import product
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import statistics
from typing import Any, Mapping, Sequence

from utopia.optimization.harness import canonical_json, digest
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256, validate_loss_spec
from utopia.optimization.metric_conditioned_study import FREEZE_SCHEMA, STUDY_SCHEMA


REPORT_SCHEMA = "scienceutopia.metric-conditioned-optimization-completion.v1"
CLASSIFICATIONS = {"experimental", "synthetic_test_fixture"}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _resolve(value: str | Path, root: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _read_registry(path: Path) -> dict[str, Any]:
    """Read a registry through SQLite read-only mode and prove bytes did not change."""

    before = _sha_file(path)
    uri = f"file:{path.resolve()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = [dict(row) for row in connection.execute("SELECT * FROM runs ORDER BY run_id")]
        attempts = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM attempts ORDER BY run_id, attempt"
            )
        ]
        links = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM artifact_links ORDER BY logical_run_id"
            )
        ]
    finally:
        connection.close()
    after = _sha_file(path)
    if before != after:
        raise RuntimeError(f"read-only analysis changed registry bytes: {path}")
    run_ids = {item["run_id"] for item in rows}
    orphan_links = sorted(
        item["logical_run_id"] for item in links
        if item["logical_run_id"] not in run_ids
    )
    if orphan_links:
        raise ValueError(f"registry contains orphan artifact links: {orphan_links}")
    link_by_run = {item["logical_run_id"]: item for item in links}
    attempts_by_run: dict[str, list[dict[str, Any]]] = {}
    for attempt in attempts:
        attempts_by_run.setdefault(attempt["run_id"], []).append(attempt)
    run_provenance = {}
    for row in rows:
        link = link_by_run.get(row["run_id"])
        run_attempts = attempts_by_run.get(row["run_id"], [])
        if link:
            if run_attempts:
                raise ValueError(
                    f"adopted logical run unexpectedly has execution attempts: {row['run_id']}"
                )
            for field in (
                "physical_run_id",
                "execution_identity_sha256",
                "bundle_receipt_sha256",
                "source_attempt_provenance_sha256",
            ):
                if not link.get(field):
                    raise ValueError(
                        f"adopted logical run lacks {field}: {row['run_id']}"
                    )
        elif row.get("status") == "complete" and not any(
            attempt.get("status") == "complete" for attempt in run_attempts
        ):
            raise ValueError(
                f"executed complete logical run lacks a complete attempt: {row['run_id']}"
            )
        run_provenance[row["run_id"]] = {
            "mode": "adopted" if link else "executed",
            "physical_run_id": link["physical_run_id"] if link else row["run_id"],
            "execution_identity_sha256": (
                link["execution_identity_sha256"] if link else None
            ),
            "bundle_receipt_sha256": link["bundle_receipt_sha256"] if link else None,
            "source_attempt_provenance_sha256": (
                link["source_attempt_provenance_sha256"] if link else None
            ),
        }
    return {
        "sha256": before,
        "rows": rows,
        "attempts": attempts,
        "artifact_links": links,
        "run_provenance": run_provenance,
    }


def _bootstrap_interval(values: Sequence[float], dispersion_weight: float) -> dict[str, Any]:
    if not values:
        raise ValueError("cannot bootstrap an empty seed vector")
    samples = []
    for indexes in product(range(len(values)), repeat=len(values)):
        resample = [values[index] for index in indexes]
        samples.append(
            statistics.fmean(resample)
            + dispersion_weight * statistics.pstdev(resample)
        )
    samples.sort()

    def percentile(probability: float) -> float:
        position = probability * (len(samples) - 1)
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return samples[lower]
        weight = position - lower
        return samples[lower] * (1 - weight) + samples[upper] * weight

    return {
        "method": "exact_seed_bootstrap_percentile",
        "resamples": len(samples),
        "ci95_low": percentile(0.025),
        "ci95_high": percentile(0.975),
    }


def _average_ranks(values: Mapping[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    ranks: dict[str, float] = {}
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][1] == ordered[index][1]:
            end += 1
        rank = ((index + 1) + end) / 2
        for name, _ in ordered[index:end]:
            ranks[name] = rank
        index = end
    return ranks


def _kendall_tau_b(left: Mapping[str, float], right: Mapping[str, float]) -> float | None:
    names = sorted(set(left) & set(right))
    concordant = discordant = left_ties = right_ties = 0
    for index, first in enumerate(names):
        for second in names[index + 1:]:
            a = left[first] - left[second]
            b = right[first] - right[second]
            if a == 0 and b == 0:
                continue
            if a == 0:
                left_ties += 1
            elif b == 0:
                right_ties += 1
            elif a * b > 0:
                concordant += 1
            else:
                discordant += 1
    denominator = math.sqrt(
        (concordant + discordant + left_ties)
        * (concordant + discordant + right_ties)
    )
    return (concordant - discordant) / denominator if denominator else None


def _validated_freeze(path: Path) -> dict[str, Any]:
    freeze = _read_json(path)
    if freeze.get("schema") != FREEZE_SCHEMA:
        raise ValueError("winner freeze schema is invalid")
    expected = freeze.get("freeze_sha256")
    immutable = dict(freeze)
    immutable.pop("freeze_sha256", None)
    immutable.pop("frozen_utc", None)
    if not isinstance(expected, str) or digest(immutable, length=64) != expected:
        raise ValueError("winner freeze hash does not match its contents")
    return freeze


def _campaign_ids(manifest: Mapping[str, Any], repo_root: Path) -> list[str]:
    ids = []
    for value in manifest["campaigns"]:
        spec = _read_json(_resolve(value, repo_root))
        ids.append(spec["id"])
    return ids


def build_optimization_completion_report(
    *,
    manifest_path: str | Path,
    study_root: str | Path,
    campaign_roots: Mapping[str, str | Path],
    classification: str,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Validate and analyze a sealed 3×5×3 optimization without held-out access."""

    if classification not in CLASSIFICATIONS:
        raise ValueError(f"unknown data classification {classification!r}")
    manifest_path = Path(manifest_path).resolve()
    repo_root = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
    study_root = Path(study_root).resolve()
    manifest = _read_json(manifest_path)
    if manifest.get("schema") != STUDY_SCHEMA:
        raise ValueError("study manifest schema is invalid")
    if manifest.get("decision_policy") != "report_only":
        raise ValueError("completion analysis requires report_only decision policy")
    arm_ids = _campaign_ids(manifest, repo_root)
    if len(arm_ids) != 3 or len(set(arm_ids)) != 3:
        raise ValueError("completion analysis requires exactly three arms")
    if set(campaign_roots) != set(arm_ids):
        raise ValueError("campaign root arm set differs from the study manifest")
    optimization_seeds = list(manifest["common_optimization_seeds"])
    held_out_seeds = list(manifest["common_held_out_evaluation_seeds"])
    if len(optimization_seeds) != 3 or len(set(optimization_seeds)) != 3:
        raise ValueError("completion analysis requires exactly three development seeds")
    if set(optimization_seeds) & set(held_out_seeds):
        raise ValueError("development and held-out seeds overlap")

    freeze_path = study_root / "winner-freeze.json"
    freeze = _validated_freeze(freeze_path)
    if freeze.get("study_id") != manifest["id"] or len(freeze.get("winners", [])) != 3:
        raise ValueError("winner freeze does not match the three-arm study")
    if (
        freeze.get("decision_policy") != "report_only"
        or freeze.get("optimization_seeds") != optimization_seeds
    ):
        raise ValueError("winner freeze does not preserve the development contract")
    if set(freeze.get("held_out_seeds_unconsumed_at_freeze", [])) != set(held_out_seeds):
        raise ValueError("winner freeze does not seal the declared held-out seeds as unconsumed")

    held_out_paths = [
        study_root / "held-out-evaluation" / "runs.sqlite3",
        study_root / "held-out-evaluation" / "snapshot.json",
        study_root / "held-out-evaluation" / "cross-evaluation.json",
    ]
    existing_held_out = [str(path) for path in held_out_paths if path.exists()]
    if existing_held_out:
        raise ValueError(
            "held-out evidence is already planned or consumed; development-only "
            f"completion report refused: {existing_held_out}"
        )

    winners = {item["campaign_id"]: item for item in freeze["winners"]}
    if set(winners) != set(arm_ids):
        raise ValueError("winner freeze arm set differs from manifest")

    losses: dict[str, dict[str, Any]] = {}
    snapshots: dict[str, dict[str, Any]] = {}
    states: dict[str, dict[str, Any]] = {}
    registry_data: dict[str, dict[str, Any]] = {}
    evaluations: dict[str, dict[str, Any]] = {}
    file_hashes: dict[str, dict[str, str]] = {}
    source_commits: set[str] = set()

    for arm in arm_ids:
        root = Path(campaign_roots[arm]).resolve()
        snapshot_path = root / "campaign-snapshot.json"
        state_path = root / "campaign-state.json"
        registry_path = root / "runs.sqlite3"
        report_path = root / "reports" / "registry-report.json"
        snapshot = _read_json(snapshot_path)
        state = _read_json(state_path)
        report = _read_json(report_path)
        registry = _read_registry(registry_path)
        if len(registry["rows"]) != 15:
            raise ValueError(
                f"{arm} registry has {len(registry['rows'])} logical runs, expected 15"
            )
        snapshots[arm] = snapshot
        states[arm] = state
        registry_data[arm] = registry
        file_hashes[arm] = {
            "snapshot_sha256": _sha_file(snapshot_path),
            "state_sha256": _sha_file(state_path),
            "registry_sha256": registry["sha256"],
            "registry_report_sha256": _sha_file(report_path),
        }
        if snapshot.get("campaign", {}).get("id") != arm:
            raise ValueError(f"{arm} snapshot campaign identity is invalid")
        campaign = snapshot["campaign"]
        if campaign.get("budget", {}).get("max_suggestions") != 5:
            raise ValueError(f"{arm} snapshot does not preserve the five-candidate budget")
        if (
            campaign.get("seed_sets", {}).get("optimization") != optimization_seeds
            or campaign.get("seed_sets", {}).get("held_out_evaluation") != held_out_seeds
        ):
            raise ValueError(f"{arm} snapshot seed sets differ from the study manifest")
        if state.get("campaign_id") != arm:
            raise ValueError(f"{arm} state campaign identity is invalid")
        if state.get("revision") != winners[arm].get("campaign_revision"):
            raise ValueError(f"{arm} state revision differs from winner freeze")
        source = snapshot.get("source", {})
        if source.get("tree_dirty") is not False or source.get("dirty_paths"):
            raise ValueError(f"{arm} snapshot source is not clean")
        source_commits.add(source.get("commit"))
        loss = snapshot.get("loss_spec")
        if not isinstance(loss, dict):
            raise ValueError(f"{arm} snapshot has no LossSpec")
        validate_loss_spec(loss)
        if winners[arm].get("loss_spec", {}).get("sha256") != loss_spec_sha256(loss):
            raise ValueError(f"{arm} winner LossSpec hash differs from snapshot")
        losses[loss["id"]] = loss
        if report.get("report_errors"):
            raise ValueError(f"{arm} registry report contains errors")
        objective_evaluations = report.get("objective_evaluations", [])
        evaluations[arm] = {item["run_id"]: item for item in objective_evaluations}
        if len(objective_evaluations) != 15 or len(evaluations[arm]) != 15:
            raise ValueError(f"{arm} registry report lacks 15 unique evaluations")
        if (
            report.get("total_runs") != 15
            or report.get("status_counts") != {"complete": 15}
            or report.get("artifact_provenance_counts") != {
                "executed": sum(
                    1 for value in registry["run_provenance"].values()
                    if value["mode"] == "executed"
                ),
                "adopted": len(registry["artifact_links"]),
            }
            or report.get("artifact_links") != registry["artifact_links"]
        ):
            raise ValueError(f"{arm} registry report provenance is stale or incomplete")
    if len(source_commits) != 1 or None in source_commits:
        raise ValueError("campaign snapshots do not share one pinned source commit")
    if len(losses) != 3:
        raise ValueError("campaign snapshots do not contain three distinct LossSpecs")
    if freeze.get("source_commit") not in source_commits:
        raise ValueError("winner freeze source commit differs from campaign snapshots")
    parity_fields = (
        "study_template", "fidelity", "seed_sets", "optimizer", "budget", "execution",
    )
    reference_campaign = snapshots[arm_ids[0]]["campaign"]
    missing_parity = [field for field in parity_fields if field not in reference_campaign]
    if missing_parity:
        raise ValueError(f"campaign snapshot lacks controlled fields {missing_parity}")
    for arm in arm_ids[1:]:
        campaign = snapshots[arm]["campaign"]
        for field in parity_fields:
            if canonical_json(campaign.get(field)) != canonical_json(
                reference_campaign.get(field)
            ):
                raise ValueError(
                    f"campaign snapshots differ outside LossSpec/identity at {field!r}"
                )

    arm_reports: dict[str, Any] = {}
    all_candidates: dict[str, dict[str, Any]] = {}
    total_modes: Counter[str] = Counter()
    total_attempts: Counter[str] = Counter()
    total_wall_seconds = 0.0

    for arm in arm_ids:
        state = states[arm]
        registry = registry_data[arm]
        rows = {item["run_id"]: item for item in registry["rows"]}
        if len(rows) != 15:
            raise ValueError(f"{arm} registry has {len(rows)} logical runs, expected 15")
        if any(item["status"] != "complete" for item in rows.values()):
            raise ValueError(f"{arm} has non-complete development runs")
        if any(
            item["seed_role"] != "optimization"
            or item["seed"] not in optimization_seeds
            or item["seed"] in held_out_seeds
            for item in rows.values()
        ):
            raise ValueError(f"{arm} registry violates the development seed firewall")
        suggestions = sorted(
            state.get("suggestions", []),
            key=lambda item: item["suggestion"]["proposal_index"],
        )
        if len(suggestions) != 5 or [
            item["suggestion"]["proposal_index"] for item in suggestions
        ] != list(range(5)):
            raise ValueError(f"{arm} must contain proposal indexes 0..4")
        candidates = []
        for record in suggestions:
            if record.get("status") != "observed_complete":
                raise ValueError(f"{arm} contains a non-complete suggestion")
            run_ids = record.get("run_ids", [])
            if len(run_ids) != 3 or len(set(run_ids)) != 3:
                raise ValueError(f"{arm} candidate does not contain three logical runs")
            run_rows = [rows.get(run_id) for run_id in run_ids]
            if any(row is None for row in run_rows):
                raise ValueError(f"{arm} candidate references a missing registry row")
            if {row["seed"] for row in run_rows} != set(optimization_seeds):
                raise ValueError(f"{arm} candidate does not cover all development seeds")
            selected = [evaluations[arm].get(run_id) for run_id in run_ids]
            if any(item is None for item in selected):
                raise ValueError(f"{arm} candidate lacks objective evaluation evidence")
            cross_losses = {}
            for loss_id, loss in sorted(losses.items()):
                result = evaluate_loss(loss, selected)
                if result["status"] != "complete" or result["valid_runs"] != 3:
                    raise ValueError(f"{arm} candidate is incomplete under {loss_id}")
                by_run = {item["run_id"]: item for item in result["per_run"]}
                seed_values = []
                for row in sorted(run_rows, key=lambda item: item["seed"]):
                    provenance = registry["run_provenance"][row["run_id"]]
                    seed_values.append({
                        "seed": row["seed"],
                        "run_id": row["run_id"],
                        "loss": by_run[row["run_id"]]["loss"],
                        "execution_mode": provenance["mode"],
                    })
                values = [item["loss"] for item in seed_values]
                cross_losses[loss_id] = {
                    "loss": result["loss"],
                    "mean": result["mean"],
                    "population_sd": result["population_sd"],
                    "seed_values": seed_values,
                    "uncertainty": _bootstrap_interval(
                        values, float(loss["across_seeds"]["dispersion_weight"])
                    ),
                }
            own_loss_id = snapshots[arm]["loss_spec"]["id"]
            observed = record.get("observation", {}).get("loss")
            if not isinstance(observed, (int, float)) or not math.isclose(
                float(observed), float(cross_losses[own_loss_id]["loss"]),
                rel_tol=1e-12, abs_tol=1e-12,
            ):
                raise ValueError(f"{arm} recorded observation does not recompute")
            modes = Counter(
                registry["run_provenance"][row["run_id"]]["mode"]
                for row in run_rows
            )
            total_modes.update(modes)
            candidate_key = f"{arm}/p{record['suggestion']['proposal_index']}"
            candidate = {
                "candidate_key": candidate_key,
                "proposal_index": record["suggestion"]["proposal_index"],
                "phase": record["suggestion"].get("phase"),
                "suggestion_id": record["suggestion"]["suggestion_id"],
                "design_id": record["design_id"],
                "system_fingerprint": record["system_fingerprint"],
                "source_candidate": record["source_candidate"],
                "run_ids": run_ids,
                "execution_provenance": dict(sorted(modes.items())),
                "cross_objective_losses": cross_losses,
            }
            candidates.append(candidate)
            all_candidates[candidate_key] = candidate
        winner = winners[arm]
        selected = min(
            candidates,
            key=lambda item: (
                item["cross_objective_losses"][snapshots[arm]["loss_spec"]["id"]]["loss"],
                item["proposal_index"],
            ),
        )
        if (
            winner["suggestion_id"] != selected["suggestion_id"]
            or winner["design_id"] != selected["design_id"]
            or winner["system_fingerprint"] != selected["system_fingerprint"]
            or not math.isclose(
                float(winner.get("optimization_observation", {}).get("loss", math.nan)),
                float(
                    selected["cross_objective_losses"][
                        snapshots[arm]["loss_spec"]["id"]
                    ]["loss"]
                ),
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
        ):
            raise ValueError(f"{arm} winner freeze differs from recomputed optimum")
        attempt_counts = Counter(item["status"] for item in registry["attempts"])
        total_attempts.update(attempt_counts)
        wall_seconds = sum(
            float(item["wall_seconds"])
            for item in registry["attempts"]
            if item.get("wall_seconds") is not None
        )
        total_wall_seconds += wall_seconds
        arm_reports[arm] = {
            "loss_spec": {
                "id": snapshots[arm]["loss_spec"]["id"],
                "version": snapshots[arm]["loss_spec"]["version"],
                "sha256": loss_spec_sha256(snapshots[arm]["loss_spec"]),
            },
            "campaign_revision": state["revision"],
            "candidates": candidates,
            "frozen_winner_candidate_key": selected["candidate_key"],
            "execution": {
                "logical_runs": len(rows),
                "executed_runs": sum(
                    1 for item in registry["run_provenance"].values()
                    if item["mode"] == "executed"
                ),
                "adopted_runs": len(registry["artifact_links"]),
                "attempt_status_counts": dict(sorted(attempt_counts.items())),
                "physical_attempt_wall_seconds": wall_seconds,
                "artifact_links": registry["artifact_links"],
            },
        }

    if len(all_candidates) != 15 or sum(total_modes.values()) != 45:
        raise ValueError("completion report does not contain 3 arms × 5 candidates × 3 seeds")

    rankings = {}
    for loss_id in sorted(losses):
        values = {
            key: candidate["cross_objective_losses"][loss_id]["loss"]
            for key, candidate in all_candidates.items()
        }
        ranks = _average_ranks(values)
        order = sorted(values, key=lambda key: (values[key], key))
        rankings[loss_id] = {
            "values": values,
            "ranks": ranks,
            "order": order,
            "best_candidate_key": order[0],
            "best_design_id": all_candidates[order[0]]["design_id"],
        }
    pairwise = []
    reversals = []
    loss_ids = sorted(losses)
    for index, left in enumerate(loss_ids):
        for right in loss_ids[index + 1:]:
            left_best = rankings[left]["best_candidate_key"]
            right_best = rankings[right]["best_candidate_key"]
            row = {
                "left": left,
                "right": right,
                "kendall_tau_b": _kendall_tau_b(
                    rankings[left]["ranks"], rankings[right]["ranks"]
                ),
                "left_best_candidate_key": left_best,
                "right_best_candidate_key": right_best,
                "winner_changes": left_best != right_best,
            }
            pairwise.append(row)
            if row["winner_changes"]:
                reversals.append(row)

    frozen_cross = {}
    for arm in arm_ids:
        key = arm_reports[arm]["frozen_winner_candidate_key"]
        frozen_cross[arm] = {
            loss_id: all_candidates[key]["cross_objective_losses"][loss_id]
            for loss_id in loss_ids
        }

    return {
        "schema": REPORT_SCHEMA,
        "study_id": manifest["id"],
        "study_revision": freeze["study_revision"],
        "data_classification": classification,
        "evidence_boundary": {
            "split": "development_only",
            "held_out_consumed": False,
            "held_out_seeds": held_out_seeds,
            "verified_absent_paths": [str(path) for path in held_out_paths],
            "interpretation": (
                "All rankings and uncertainty use development seeds. This report "
                "does not estimate held-out generalization or select a universal policy."
            ),
        },
        "contract": {
            "arms": 3,
            "candidates_per_arm": 5,
            "development_seeds_per_candidate": 3,
            "logical_runs": 45,
            "distinct_losses": 3,
            "decision_policy": "report_only",
        },
        "provenance": {
            "source_commit": next(iter(source_commits)),
            "controlled_search_contract_sha256": {
                field: digest(reference_campaign.get(field), length=64)
                for field in parity_fields
            },
            "manifest_path": str(manifest_path),
            "manifest_sha256": _sha_file(manifest_path),
            "winner_freeze_path": str(freeze_path),
            "winner_freeze_sha256": freeze["freeze_sha256"],
            "campaign_files": file_hashes,
        },
        "execution": {
            "logical_runs": 45,
            "executed_runs": total_modes["executed"],
            "adopted_runs": total_modes["adopted"],
            "attempt_status_counts": dict(sorted(total_attempts.items())),
            "physical_attempt_wall_seconds": total_wall_seconds,
        },
        "arms": arm_reports,
        "frozen_winners": freeze["winners"],
        "development_cross_objective": {
            "candidate_rankings": rankings,
            "frozen_winner_matrix": frozen_cross,
            "pairwise_rank_association": pairwise,
            "winner_reversals": reversals,
        },
        "interpretation_guard": (
            "The topic-entropy and review-burden objectives are contrastive proxies, "
            "not normative recommendations. Different winners demonstrate objective "
            "dependence; no universal winner is selected."
        ),
    }


def validate_completion_report(report: Mapping[str, Any]) -> None:
    if report.get("schema") != REPORT_SCHEMA:
        raise ValueError(f"expected {REPORT_SCHEMA}")
    contract = report.get("contract", {})
    expected = {
        "arms": 3,
        "candidates_per_arm": 5,
        "development_seeds_per_candidate": 3,
        "logical_runs": 45,
        "distinct_losses": 3,
        "decision_policy": "report_only",
    }
    if contract != expected:
        raise ValueError("completion report contract is incomplete")
    boundary = report.get("evidence_boundary", {})
    if (
        boundary.get("split") != "development_only"
        or boundary.get("held_out_consumed") is not False
        or len(boundary.get("held_out_seeds", [])) != 5
        or len(boundary.get("verified_absent_paths", [])) != 3
    ):
        raise ValueError("completion report must be development-only")
    execution = report.get("execution", {})
    if (
        execution.get("logical_runs") != 45
        or execution.get("executed_runs", 0) + execution.get("adopted_runs", 0) != 45
    ):
        raise ValueError("completion report must contain 45 logical runs")
    if len(report.get("arms", {})) != 3:
        raise ValueError("completion report must contain three arms")
    for arm, value in report["arms"].items():
        if len(value.get("candidates", [])) != 5:
            raise ValueError(f"{arm} does not contain five candidates")
        if not value.get("frozen_winner_candidate_key"):
            raise ValueError(f"{arm} has no frozen winner")
        arm_execution = value.get("execution", {})
        if (
            arm_execution.get("logical_runs") != 15
            or arm_execution.get("executed_runs", 0)
            + arm_execution.get("adopted_runs", 0) != 15
        ):
            raise ValueError(f"{arm} does not contain 15 provenanced logical runs")
        for candidate in value["candidates"]:
            if len(candidate.get("run_ids", [])) != 3:
                raise ValueError(f"{arm} candidate does not contain three seed runs")
            if len(candidate.get("cross_objective_losses", {})) != 3:
                raise ValueError(f"{arm} candidate lacks three-way cross-scoring")
    cross = report.get("development_cross_objective", {})
    if len(cross.get("candidate_rankings", {})) != 3:
        raise ValueError("completion report does not contain three objective rankings")
    for loss_id, ranking in cross["candidate_rankings"].items():
        if len(ranking.get("values", {})) != 15:
            raise ValueError(f"{loss_id} ranking does not contain 15 candidates")
    if len(cross.get("frozen_winner_matrix", {})) != 3:
        raise ValueError("completion report frozen-winner matrix is not 3 by 3")
    if any(
        len(row) != 3 for row in cross["frozen_winner_matrix"].values()
    ):
        raise ValueError("completion report frozen-winner matrix is not 3 by 3")


def canonical_report_sha256(report: Mapping[str, Any]) -> str:
    return _sha_bytes(canonical_json(report).encode("utf-8"))
