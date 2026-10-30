import copy
from pathlib import Path
import sqlite3

import pytest

from utopia.optimization.held_out_progress import (
    build_held_out_progress,
    verify_progress_hash,
)


def _registry(path: Path, rows: list[tuple]) -> Path:
    database = sqlite3.connect(path)
    database.executescript(
        """
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY,
            study_id TEXT NOT NULL,
            study_revision TEXT NOT NULL,
            seed INTEGER NOT NULL,
            seed_role TEXT NOT NULL,
            status TEXT NOT NULL,
            attempt INTEGER NOT NULL,
            max_attempts INTEGER NOT NULL,
            started_utc TEXT,
            finished_utc TEXT,
            wall_seconds REAL,
            error TEXT
        );
        """
    )
    database.executemany(
        "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows
    )
    database.commit()
    database.close()
    return path


def _row(
    run: str,
    seed: int,
    status: str,
    *,
    attempt: int = 0,
    started: str | None = None,
    finished: str | None = None,
    wall: float | None = None,
    error: str | None = None,
) -> tuple:
    return (
        run,
        "study-v1",
        "revision-1",
        seed,
        "held_out_evaluation",
        status,
        attempt,
        2,
        started,
        finished,
        wall,
        error,
    )


def _keys(value) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in _keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in _keys(item)}
    return set()


def test_progress_is_result_blind_read_only_and_estimates_eta(tmp_path: Path) -> None:
    registry = _registry(
        tmp_path / "runs.sqlite3",
        [
            _row(
                "complete",
                701,
                "complete",
                attempt=1,
                started="2030-01-01T00:00:00+00:00",
                finished="2030-01-01T01:00:00+00:00",
                wall=3600,
            ),
            _row(
                "running",
                709,
                "running",
                attempt=1,
                started="2030-01-01T01:00:00+00:00",
            ),
            _row("planned", 719, "planned"),
        ],
    )
    before = registry.read_bytes()
    snapshot = build_held_out_progress(
        registry,
        expected_runs=3,
        observed_at_utc="2030-01-01T01:30:00+00:00",
    )

    assert registry.read_bytes() == before
    assert snapshot["progress"]["counts"] == {
        "planned": 1,
        "running": 1,
        "complete": 1,
        "failed": 0,
    }
    assert snapshot["progress"]["eta"]["remaining_seconds"] == 5400
    assert snapshot["health"]["stalled"] is False
    assert snapshot["gate"]["next_action"] == "continue-evaluation"
    assert verify_progress_hash(snapshot)
    keys = {key.lower() for key in _keys(snapshot)}
    assert not {"loss", "metric", "observation", "winner", "promotion"} & keys
    assert "promotion" in snapshot["disclosure"]


def test_planned_rows_without_active_run_fail_closed_as_stalled(tmp_path: Path) -> None:
    registry = _registry(
        tmp_path / "runs.sqlite3", [_row("planned", 701, "planned")]
    )
    snapshot = build_held_out_progress(
        registry,
        expected_runs=1,
        observed_at_utc="2030-01-01T00:00:00+00:00",
    )
    assert snapshot["health"]["stalled"] is True
    assert snapshot["gate"]["next_action"] == "investigate-stall"


def test_terminal_rows_open_report_gate_without_selecting_a_winner(tmp_path: Path) -> None:
    registry = _registry(
        tmp_path / "runs.sqlite3",
        [
            _row(
                "complete",
                701,
                "complete",
                attempt=1,
                started="2030-01-01T00:00:00+00:00",
                finished="2030-01-01T01:00:00+00:00",
                wall=3600,
            ),
            _row(
                "failed",
                709,
                "failed",
                attempt=2,
                started="2030-01-01T01:00:00+00:00",
                finished="2030-01-01T02:00:00+00:00",
                error="technical failure",
            ),
        ],
    )
    snapshot = build_held_out_progress(
        registry,
        expected_runs=2,
        observed_at_utc="2030-01-01T02:00:00+00:00",
    )
    assert snapshot["gate"] == {
        "ready_for_report": True,
        "next_action": "report-evaluation",
    }
    assert snapshot["progress"]["terminal_failures"] == 1
    assert "winner" not in str(snapshot).lower()


def test_stale_running_row_is_reported(tmp_path: Path) -> None:
    registry = _registry(
        tmp_path / "runs.sqlite3",
        [
            _row(
                "running",
                701,
                "running",
                attempt=1,
                started="2030-01-01T00:00:00+00:00",
            )
        ],
    )
    snapshot = build_held_out_progress(
        registry,
        expected_runs=1,
        observed_at_utc="2030-01-01T05:00:00+00:00",
        stale_after_hours=4,
    )
    assert snapshot["health"]["stale_run_ids"] == ["running"]
    assert snapshot["health"]["stalled"] is True


def test_hash_detects_mutation(tmp_path: Path) -> None:
    registry = _registry(
        tmp_path / "runs.sqlite3", [_row("planned", 701, "planned")]
    )
    snapshot = build_held_out_progress(
        registry,
        expected_runs=1,
        observed_at_utc="2030-01-01T00:00:00+00:00",
    )
    mutated = copy.deepcopy(snapshot)
    mutated["progress"]["counts"]["complete"] = 99
    assert verify_progress_hash(mutated) is False


@pytest.mark.parametrize("role", ["optimization", "confirmation"])
def test_non_held_out_registry_is_refused(tmp_path: Path, role: str) -> None:
    row = list(_row("planned", 701, "planned"))
    row[4] = role
    registry = _registry(tmp_path / "runs.sqlite3", [tuple(row)])
    with pytest.raises(ValueError, match="non-held-out"):
        build_held_out_progress(registry, expected_runs=1)
