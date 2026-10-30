"""Result-blind progress projection for a held-out run registry.

The projection reads orchestration state only.  It deliberately excludes
metric values, model outputs, optimizer observations, and policy decisions.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from statistics import mean, median
from typing import Any


SCHEMA = "scienceutopia.held-out-progress.v1"
STATUSES = ("planned", "running", "complete", "failed")


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def verify_progress_hash(snapshot: dict[str, Any]) -> bool:
    claimed = snapshot.get("snapshot_sha256")
    if not isinstance(claimed, str):
        return False
    unsigned = {key: value for key, value in snapshot.items() if key != "snapshot_sha256"}
    actual = hashlib.sha256(_canonical(unsigned).encode("utf-8")).hexdigest()
    return claimed == actual


def _read_rows(registry_path: Path) -> list[dict[str, Any]]:
    if not registry_path.is_file():
        raise FileNotFoundError(registry_path)
    source = sqlite3.connect(f"file:{registry_path}?mode=ro", uri=True, timeout=30)
    memory = sqlite3.connect(":memory:")
    memory.row_factory = sqlite3.Row
    try:
        source.backup(memory)
        columns = {
            row[1]
            for row in memory.execute("PRAGMA table_info(runs)")
        }
        required = {
            "run_id",
            "study_id",
            "study_revision",
            "seed",
            "seed_role",
            "status",
            "attempt",
            "max_attempts",
            "started_utc",
            "finished_utc",
            "wall_seconds",
            "error",
        }
        missing = required - columns
        if missing:
            raise ValueError(f"run registry lacks required columns: {sorted(missing)}")
        return [
            dict(row)
            for row in memory.execute(
                """SELECT run_id, study_id, study_revision, seed, seed_role,
                          status, attempt, max_attempts, started_utc,
                          finished_utc, wall_seconds, error
                   FROM runs ORDER BY run_id"""
            )
        ]
    finally:
        memory.close()
        source.close()


def build_held_out_progress(
    registry: str | Path,
    *,
    expected_runs: int | None = None,
    observed_at_utc: str | None = None,
    stale_after_hours: float = 4.0,
) -> dict[str, Any]:
    """Build a deterministic, result-blind progress snapshot."""
    if expected_runs is not None and expected_runs <= 0:
        raise ValueError("expected_runs must be positive")
    if stale_after_hours <= 0:
        raise ValueError("stale_after_hours must be positive")
    path = Path(registry).resolve()
    rows = _read_rows(path)
    if not rows:
        raise ValueError("held-out registry is empty")
    if expected_runs is not None and len(rows) != expected_runs:
        raise ValueError(
            f"held-out registry has {len(rows)} rows; expected {expected_runs}"
        )
    if {row["seed_role"] for row in rows} != {"held_out_evaluation"}:
        raise ValueError("registry contains a non-held-out seed role")
    studies = {(row["study_id"], row["study_revision"]) for row in rows}
    if len(studies) != 1:
        raise ValueError("registry mixes study identities")
    invalid_statuses = {row["status"] for row in rows} - set(STATUSES)
    if invalid_statuses:
        raise ValueError(f"registry contains invalid statuses: {sorted(invalid_statuses)}")

    observed = _parse_utc(observed_at_utc) if observed_at_utc else datetime.now(timezone.utc)
    counts = {status: 0 for status in STATUSES}
    for row in rows:
        counts[row["status"]] += 1

    completed_seconds = [
        float(row["wall_seconds"])
        for row in rows
        if row["status"] == "complete" and row["wall_seconds"] is not None
    ]
    if len(completed_seconds) != counts["complete"]:
        raise ValueError("a complete held-out row lacks wall time")
    duration = None
    if completed_seconds:
        duration = {
            "count": len(completed_seconds),
            "mean_seconds": mean(completed_seconds),
            "median_seconds": median(completed_seconds),
            "minimum_seconds": min(completed_seconds),
            "maximum_seconds": max(completed_seconds),
        }

    active_runs: list[dict[str, Any]] = []
    stale_runs: list[str] = []
    for row in rows:
        if row["status"] != "running":
            continue
        if not row["started_utc"]:
            raise ValueError("a running held-out row lacks started_utc")
        elapsed = max(0.0, (observed - _parse_utc(row["started_utc"])).total_seconds())
        active_runs.append(
            {
                "run_id": row["run_id"],
                "seed": row["seed"],
                "attempt": row["attempt"],
                "max_attempts": row["max_attempts"],
                "started_utc": row["started_utc"],
                "elapsed_seconds": elapsed,
            }
        )
        if elapsed > stale_after_hours * 3600:
            stale_runs.append(row["run_id"])

    retryable_failures = sum(
        row["status"] == "failed" and row["attempt"] < row["max_attempts"]
        for row in rows
    )
    terminal_failures = sum(
        row["status"] == "failed" and row["attempt"] >= row["max_attempts"]
        for row in rows
    )
    unfinished = counts["planned"] + counts["running"] + retryable_failures
    eta = None
    if duration and unfinished:
        typical = duration["median_seconds"]
        active_remaining = sum(
            max(0.0, typical - run["elapsed_seconds"])
            for run in active_runs
        )
        queued = counts["planned"] + retryable_failures
        eta_seconds = active_remaining + queued * typical
        eta = {
            "method": "completed_run_median",
            "remaining_seconds": eta_seconds,
            "estimated_completion_utc": (
                observed.timestamp() + eta_seconds
            ),
        }
        eta["estimated_completion_utc"] = datetime.fromtimestamp(
            eta["estimated_completion_utc"], tz=timezone.utc
        ).isoformat()

    stalled = bool(stale_runs) or (
        (counts["planned"] > 0 or retryable_failures > 0) and not active_runs
    )
    ready_for_report = (
        counts["planned"] == 0
        and counts["running"] == 0
        and retryable_failures == 0
        and counts["complete"] + terminal_failures == len(rows)
    )
    study_id, study_revision = next(iter(studies))
    failures = [
        {
            "run_id": row["run_id"],
            "seed": row["seed"],
            "attempt": row["attempt"],
            "max_attempts": row["max_attempts"],
            "terminal": row["attempt"] >= row["max_attempts"],
            "error": row["error"],
        }
        for row in rows
        if row["status"] == "failed"
    ]
    snapshot: dict[str, Any] = {
        "schema": SCHEMA,
        "truth_status": "verified_progress_snapshot",
        "disclosure": (
            "Read-only orchestration facts only; no loss, metric, model output, "
            "candidate update, or promotion decision is included."
        ),
        "observed_at_utc": observed.isoformat(),
        "study": {"id": study_id, "revision": study_revision},
        "registry": {
            "path": str(path),
            "registered_runs": len(rows),
            "expected_runs": expected_runs,
            "projection_sha256": hashlib.sha256(
                _canonical(rows).encode("utf-8")
            ).hexdigest(),
        },
        "progress": {
            "counts": counts,
            "completion_fraction": counts["complete"] / len(rows),
            "retryable_failures": retryable_failures,
            "terminal_failures": terminal_failures,
            "active_runs": active_runs,
            "duration_summary": duration,
            "eta": eta,
        },
        "health": {
            "stalled": stalled,
            "stale_after_hours": stale_after_hours,
            "stale_run_ids": stale_runs,
            "failures": failures,
        },
        "gate": {
            "ready_for_report": ready_for_report,
            "next_action": (
                "report-evaluation"
                if ready_for_report
                else "investigate-stall"
                if stalled
                else "continue-evaluation"
            ),
        },
    }
    snapshot["snapshot_sha256"] = hashlib.sha256(
        _canonical(snapshot).encode("utf-8")
    ).hexdigest()
    return snapshot
