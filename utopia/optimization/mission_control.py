"""Read-only, result-blind projection for the optimization mission-control UI.

The adapter deliberately exports orchestration facts, never objective values,
metrics, observations, or an inferred winner.  SQLite registries are copied to
memory through a read-only connection before they are queried.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any


SCHEMA_VERSION = "scienceutopia.optimization-mission-control.v1"
SOURCE_KIND = "read_only_metric_conditioned_registry_snapshot"
SYNTHETIC_SOURCE_KIND = "synthetic_optimization_mission_fixture"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _canonical(value: Any) -> str:
    return json.dumps(value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_registry(path: Path) -> tuple[list[dict[str, Any]], str]:
    source = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
    memory = sqlite3.connect(":memory:")
    try:
        source.backup(memory)
        memory.row_factory = sqlite3.Row
        rows = [dict(row) for row in memory.execute(
            """
            SELECT r.run_id, r.design_id, r.seed, r.seed_role, r.status,
                   r.attempt, r.max_attempts, r.started_utc, r.finished_utc,
                   r.wall_seconds,
                   CASE WHEN a.logical_run_id IS NOT NULL THEN 'adopted'
                        WHEN r.status = 'planned' AND r.attempt = 0 THEN 'unmaterialized'
                        ELSE 'physical' END AS execution_kind,
                   a.physical_run_id
            FROM runs r
            LEFT JOIN artifact_links a ON a.logical_run_id = r.run_id
            ORDER BY r.design_id, r.seed, r.run_id
            """
        )]
        schedulers = [dict(row) for row in memory.execute(
            """SELECT scheduler_id, started_utc, finished_utc, status,
                      worker_limit, recovered_runs
               FROM schedulers ORDER BY started_utc, scheduler_id"""
        )]
    finally:
        memory.close()
        source.close()
    projection = {"runs": rows, "schedulers": schedulers}
    return rows, _hash(projection)


def _candidate_status(runs: list[dict[str, Any]], record_status: str) -> str:
    statuses = {row["status"] for row in runs}
    if record_status == "observed_complete":
        return "complete"
    if record_status == "observed_invalid":
        return "failed"
    if "running" in statuses:
        return "running"
    if "failed" in statuses:
        return "failed"
    if runs and statuses == {"complete"}:
        return "complete"
    return "planned"


def _arm_label(loss_id: str) -> str:
    return {
        "participation-review-tradeoff-probe": "Participation × review",
        "topic-diversity-probe": "Topic diversity",
        "review-burden-probe": "Review burden",
    }.get(loss_id, loss_id.replace("-", " ").title())


def _resolve_arm_root(source_root: Path, campaign: dict[str, Any]) -> Path:
    output = Path(campaign["execution"]["output_root"])
    output = output if output.is_absolute() else source_root / output
    matches = sorted((output / campaign["id"]).glob("*/campaign-snapshot.json"))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one initialized revision for {campaign['id']}; found {len(matches)}")
    return matches[0].parent


def build_mission_control_snapshot(
    source_root: str | Path,
    study_spec: str | Path = "research/specs/metric-conditioned-optimization-study-v1-1.json",
    *,
    observed_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build a fail-closed progress snapshot from a pinned study worktree."""
    root = Path(source_root).resolve()
    manifest_path = Path(study_spec)
    manifest_path = manifest_path if manifest_path.is_absolute() else root / manifest_path
    manifest = _read(manifest_path)
    if manifest.get("schema") != "scienceutopia.metric-conditioned-optimization-study.v1":
        raise ValueError("unsupported optimization study schema")
    arm_payloads: list[dict[str, Any]] = []
    source_files: list[dict[str, str]] = [{"role": "study_spec", "path": str(manifest_path.relative_to(root)), "sha256": _file_hash(manifest_path)}]
    commits: set[str] = set()
    registry_hashes: list[str] = []
    logical_rows: list[dict[str, Any]] = []
    runtime: dict[str, Any] | None = None

    for campaign_ref in manifest["campaigns"]:
        campaign_path = root / campaign_ref
        campaign = _read(campaign_path)
        arm_root = _resolve_arm_root(root, campaign)
        snapshot_path = arm_root / "campaign-snapshot.json"
        state_path = arm_root / "campaign-state.json"
        registry_path = arm_root / "runs.sqlite3"
        before = state_path.stat()
        campaign_snapshot = _read(snapshot_path)
        state = _read(state_path)
        rows, registry_hash = _read_registry(registry_path)
        after = state_path.stat()
        if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
            raise RuntimeError(f"campaign state changed while snapshotting {campaign['id']}; retry")
        if state.get("campaign_id") != campaign["id"] or state.get("revision") != campaign_snapshot.get("revision"):
            raise ValueError(f"campaign state/snapshot mismatch for {campaign['id']}")
        if campaign_snapshot.get("source", {}).get("tree_dirty") is not False:
            raise ValueError(f"source was not clean for {campaign['id']}")
        commit = campaign_snapshot["source"]["commit"]
        commits.add(commit)
        loss = campaign_snapshot["loss_spec"]
        if campaign["loss_spec"] != campaign_snapshot["campaign"]["loss_spec"]:
            raise ValueError(f"loss reference mismatch for {campaign['id']}")
        if runtime is None:
            execution = campaign_snapshot["study_template"]["execution"]
            runtime = {
                "model": execution["model"],
                "backend": execution["api_backend"],
                "batch_size": execution["batch_size"],
                "max_attempts": execution["max_attempts"],
                "workers": campaign["execution"]["workers"],
                "fidelity": campaign["fidelity"],
            }
        by_design: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            if row["seed_role"] != "optimization" or row["seed"] not in manifest["common_optimization_seeds"]:
                raise ValueError(f"protected or unknown seed found in arm registry {campaign['id']}")
            by_design.setdefault(row["design_id"], []).append(row)
            logical_rows.append(row)
        candidates: list[dict[str, Any]] = []
        for record in state["suggestions"]:
            suggestion = record["suggestion"]
            design = record["design_id"]
            candidate_runs = by_design.pop(design, [])
            if {row["seed"] for row in candidate_runs} != set(manifest["common_optimization_seeds"]):
                raise ValueError(f"candidate seed grid is incomplete for {campaign['id']}:{design}")
            candidates.append({
                "proposal_index": suggestion["proposal_index"],
                "suggestion_id": suggestion["suggestion_id"],
                "design_id": design,
                "phase": suggestion["phase"],
                "status": _candidate_status(candidate_runs, record["status"]),
                "seeds": [{
                    "seed": row["seed"],
                    "status": row["status"],
                    "execution_kind": row["execution_kind"],
                    "attempt": row["attempt"],
                    "max_attempts": row["max_attempts"],
                    "started_utc": row["started_utc"],
                    "finished_utc": row["finished_utc"],
                    "wall_seconds": row["wall_seconds"],
                    "physical_run_id": row["physical_run_id"],
                } for row in sorted(candidate_runs, key=lambda item: item["seed"])],
            })
        if by_design:
            raise ValueError(f"registry contains designs absent from campaign state for {campaign['id']}")
        candidates.sort(key=lambda item: item["proposal_index"])
        arm_payloads.append({
            "campaign_id": campaign["id"],
            "revision": campaign_snapshot["revision"],
            "state_updated_utc": state["updated_utc"],
            "loss_spec": {
                "id": loss["id"],
                "version": loss["version"],
                "direction": loss["direction"],
                "label": _arm_label(loss["id"]),
                "interpretation": loss["interpretation"],
                "prohibited_claims": loss["prohibited_claims"],
            },
            "budget": {
                "used": len(candidates),
                "maximum": campaign["budget"]["max_suggestions"],
                "optimization_seeds": len(manifest["common_optimization_seeds"]),
            },
            "winner": {"status": "not_frozen", "design_id": None},
            "candidates": candidates,
            "registry_projection_sha256": registry_hash,
        })
        registry_hashes.append(registry_hash)
        for role, path in (("campaign_spec", campaign_path), ("campaign_snapshot", snapshot_path), ("campaign_state", state_path)):
            source_files.append({"role": role, "path": str(path.relative_to(root)), "sha256": _file_hash(path)})

    if len(commits) != 1:
        raise ValueError("campaign arms do not share one pinned source commit")
    first_campaign = _read(root / manifest["campaigns"][0])
    output = Path(first_campaign["execution"]["output_root"])
    output = output if output.is_absolute() else root / output
    study_roots = sorted((output / manifest["id"]).glob("*")) if (output / manifest["id"]).exists() else []
    freeze_files = [path / "winner-freeze.json" for path in study_roots if (path / "winner-freeze.json").exists()]
    heldout_registries = [path / "held-out-evaluation" / "runs.sqlite3" for path in study_roots if (path / "held-out-evaluation" / "runs.sqlite3").exists()]
    if freeze_files or heldout_registries:
        raise ValueError("mission-control v1 only accepts the pre-freeze, held-out-locked study phase")

    status_counts = {status: 0 for status in ("planned", "running", "complete", "failed")}
    execution_counts = {"physical_complete": 0, "physical_running": 0, "adopted_complete": 0}
    for row in logical_rows:
        status_counts[row["status"]] += 1
        if row["execution_kind"] == "adopted" and row["status"] == "complete":
            execution_counts["adopted_complete"] += 1
        elif row["execution_kind"] == "physical" and row["status"] == "complete":
            execution_counts["physical_complete"] += 1
        elif row["execution_kind"] == "physical" and row["status"] == "running":
            execution_counts["physical_running"] += 1
    candidate_capacity = sum(arm["budget"]["maximum"] for arm in arm_payloads)
    logical_capacity = candidate_capacity * len(manifest["common_optimization_seeds"])
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "truth_status": "verified_snapshot",
        "source_kind": SOURCE_KIND,
        "disclosure": "Read-only progress snapshot. It contains orchestration state, not objective values, unfinished results, or an inferred winner.",
        "observed_at_utc": observed_at_utc or datetime.now(timezone.utc).isoformat(),
        "study": {
            "id": manifest["id"],
            "version": manifest["version"],
            "goal": "Compare how three explicit LossSpecs condition the search for science-system designs; freeze one winner per arm before any held-out evaluation.",
            "decision_policy": manifest["decision_policy"],
            "arms": len(arm_payloads),
            "candidate_capacity": candidate_capacity,
            "logical_run_capacity": logical_capacity,
        },
        "workflow": [
            {"id": "development", "label": "Develop 3 LossSpec arms", "status": "running" if status_counts["running"] else "pending"},
            {"id": "freeze", "label": "Freeze one winner per arm", "status": "locked"},
            {"id": "held_out", "label": "Run common held-out seeds", "status": "locked"},
            {"id": "report", "label": "Cross-evaluate and report", "status": "locked"},
        ],
        "progress": {
            "logical_registered": len(logical_rows),
            "logical_capacity": logical_capacity,
            "status_counts": status_counts,
            "execution_counts": execution_counts,
        },
        "arms": arm_payloads,
        "winner_freeze": {"status": "not_frozen", "frozen_arms": 0, "required_arms": len(arm_payloads)},
        "held_out": {
            "status": "locked",
            "reason": "The held-out registry cannot exist until all three arm winners are immutably frozen.",
            "seeds": manifest["common_held_out_evaluation_seeds"],
            "registry_exists": False,
            "registered_runs": 0,
        },
        "runtime": runtime,
        "provenance": {
            "source_commit": next(iter(commits)),
            "source_tree_clean": True,
            "study_spec_sha256": _file_hash(manifest_path),
            "registry_projection_sha256": _hash(registry_hashes),
            "source_files": sorted(source_files, key=lambda item: (item["role"], item["path"])),
        },
    }
    payload["snapshot_hash"] = _hash(payload)
    return payload


def build_synthetic_mission_fixture(real_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Produce an unmistakable UI-test fixture without changing the real snapshot."""
    payload = copy.deepcopy(real_snapshot)
    payload["truth_status"] = "synthetic"
    payload["source_kind"] = SYNTHETIC_SOURCE_KIND
    payload["disclosure"] = "SYNTHETIC UI fixture. These states are invented for display testing and are not experiment evidence."
    payload["observed_at_utc"] = "2030-01-02T03:04:05+00:00"
    statuses = ("complete", "running", "failed")
    for arm_index, arm in enumerate(payload["arms"]):
        for candidate_index, candidate in enumerate(arm["candidates"]):
            candidate["status"] = statuses[(arm_index + candidate_index) % len(statuses)]
            for seed_index, seed in enumerate(candidate["seeds"]):
                seed["status"] = statuses[(arm_index + candidate_index + seed_index) % len(statuses)]
                seed["execution_kind"] = "adopted" if seed_index == 2 else "physical"
    synthetic_seeds = [
        seed
        for arm in payload["arms"]
        for candidate in arm["candidates"]
        for seed in candidate["seeds"]
    ]
    payload["progress"]["status_counts"] = {
        status: sum(seed["status"] == status for seed in synthetic_seeds)
        for status in ("planned", "running", "complete", "failed")
    }
    payload["progress"]["execution_counts"] = {
        "physical_complete": sum(
            seed["status"] == "complete" and seed["execution_kind"] == "physical"
            for seed in synthetic_seeds
        ),
        "physical_running": sum(
            seed["status"] == "running" and seed["execution_kind"] == "physical"
            for seed in synthetic_seeds
        ),
        "adopted_complete": sum(
            seed["status"] == "complete" and seed["execution_kind"] == "adopted"
            for seed in synthetic_seeds
        ),
    }
    payload["snapshot_hash"] = ""
    payload["snapshot_hash"] = _hash({key: value for key, value in payload.items() if key != "snapshot_hash"})
    return payload


def verify_snapshot_hash(payload: dict[str, Any]) -> bool:
    claimed = payload.get("snapshot_hash")
    unhashed = copy.deepcopy(payload)
    unhashed.pop("snapshot_hash", None)
    return isinstance(claimed, str) and claimed == _hash(unhashed)
