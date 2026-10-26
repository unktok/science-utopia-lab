from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from utopia.optimization import harness
from utopia.optimization.harness import RunRegistry, execute_pending


FAKE_RUN = r"""
import json
import os
from pathlib import Path
import sys
import time

label = sys.argv[1]
result_root = Path(sys.argv[2])
delay = float(sys.argv[3])
returncode = int(sys.argv[4])
started = time.monotonic()
print(f"stdout:{label}", flush=True)
print(f"stderr:{label}", file=sys.stderr, flush=True)
time.sleep(delay)
finished = time.monotonic()
(result_root / f"{label}.json").write_text(json.dumps({
    "label": label,
    "started": started,
    "finished": finished,
    "scheduler": os.environ.get("UTOPIA_HARNESS_SCHEDULER_ID"),
    "slot": os.environ.get("UTOPIA_HARNESS_WORKER_SLOT"),
    "workers": os.environ.get("UTOPIA_HARNESS_WORKERS"),
}))
raise SystemExit(returncode)
"""


def warm_cache(tmp_path: Path) -> Path:
    root = tmp_path / "shared-cache"
    rag = root / "rag"
    rag.mkdir(parents=True)
    (rag / "documents-fixture.pkl").write_bytes(b"warm-documents")
    (rag / "embeddings-fixture.pt").write_bytes(b"warm-embeddings")
    keywords = root / "keywords"
    keywords.mkdir()
    (keywords / "seed.json").write_text("{}")
    return root


def add_run(
    registry: RunRegistry,
    tmp_path: Path,
    run_id: str,
    *,
    delay: float = 0.05,
    returncode: int = 0,
    max_attempts: int = 2,
    cache: Path | None = None,
) -> None:
    result_root = tmp_path / "fake-results"
    result_root.mkdir(exist_ok=True)
    command = [
        sys.executable,
        "-c",
        FAKE_RUN,
        run_id,
        str(result_root),
        str(delay),
        str(returncode),
    ]
    if cache is not None:
        command.extend([
            "--data-cache-dir", str(cache),
            "--api-backend", "ollama",
            "--vllm_url", "http://fixture-ollama/v1",
            "--model", "fixture-model",
        ])
    registry.add({
        "run_id": run_id,
        "study_id": "parallel-fixture",
        "study_revision": "revision",
        "design_id": f"design-{run_id}",
        "design_json": "{}",
        "sampler": "random",
        "fidelity": "smoke",
        "seed_role": "exploration",
        "seed": len(registry.rows()) + 1,
        "max_attempts": max_attempts,
        "command_json": json.dumps(command),
        "output_root": str(tmp_path / "outputs"),
        "created_utc": "fixture",
    })


def intervals(tmp_path: Path) -> list[dict]:
    return [
        json.loads(path.read_text())
        for path in sorted((tmp_path / "fake-results").glob("*.json"))
    ]


def maximum_overlap(rows: list[dict]) -> int:
    points = []
    for row in rows:
        points.append((row["started"], 1))
        points.append((row["finished"], -1))
    active = maximum = 0
    for _, delta in sorted(points, key=lambda item: (item[0], item[1])):
        active += delta
        maximum = max(maximum, active)
    return maximum


def test_workers_one_preserves_sequential_execution_and_combined_log(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(harness, "manifest_status", lambda row: ("complete", None))
    registry = RunRegistry(tmp_path / "registry.sqlite3")
    try:
        add_run(registry, tmp_path, "run-a", delay=0.08)
        add_run(registry, tmp_path, "run-b", delay=0.08)

        counts = execute_pending(registry, workers=1)

        rows = intervals(tmp_path)
        assert counts == {"complete": 2, "failed": 0}
        assert maximum_overlap(rows) == 1
        assert len(registry.attempt_rows()) == 2
        provenance = registry.attempt_scheduler_rows()
        assert {row["worker_limit"] for row in provenance} == {1}
        for row in provenance:
            assert row["stdout_path"] == row["stderr_path"]
            log = Path(row["stdout_path"]).read_text()
            assert "stdout:" in log
            assert "stderr:" in log
    finally:
        registry.close()


def test_workers_two_overlap_without_duplicate_claims_and_are_bounded(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(harness, "manifest_status", lambda row: ("complete", None))
    cache = warm_cache(tmp_path)
    registry = RunRegistry(tmp_path / "registry.sqlite3")
    try:
        for index in range(4):
            add_run(
                registry,
                tmp_path,
                f"run-{index}",
                delay=0.18,
                cache=cache,
            )

        counts = execute_pending(
            registry,
            workers=2,
            execution={
                "api_backend": "ollama",
                "endpoint": "http://fixture-ollama/v1",
                "model": "fixture-model",
                "data_cache_dir": str(cache),
            },
        )

        rows = intervals(tmp_path)
        assert counts == {"complete": 4, "failed": 0}
        assert len(rows) == 4
        assert {row["label"] for row in rows} == {
            "run-0", "run-1", "run-2", "run-3"
        }
        assert maximum_overlap(rows) == 2
        assert len(registry.attempt_rows()) == 4
        provenance = registry.attempt_scheduler_rows()
        assert len({row["run_id"] for row in provenance}) == 4
        assert len({row["run_output_root"] for row in provenance}) == 4
        assert len({row["cache_root"] for row in provenance}) == 4
        assert all(
            row["stdout_path"] != row["stderr_path"] for row in provenance
        )
        assert {row["workers"] for row in rows} == {"2"}
        shared_mutable = cache / "keywords" / "seed.json"
        assert all(
            (
                Path(row["cache_root"]) / "keywords" / "seed.json"
            ).stat().st_ino != shared_mutable.stat().st_ino
            for row in provenance
        )
    finally:
        registry.close()


def test_atomic_sqlite_claim_cannot_duplicate_an_attempt(tmp_path: Path) -> None:
    path = tmp_path / "registry.sqlite3"
    first = RunRegistry(path)
    second = RunRegistry(path)
    try:
        add_run(first, tmp_path, "only-once")

        claimed = first.claim("only-once")
        duplicate = second.claim("only-once")

        assert claimed is not None
        assert duplicate is None
        assert len(first.attempt_rows()) == 1
    finally:
        first.close()
        second.close()


def test_one_failure_does_not_stop_other_runs(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(harness, "manifest_status", lambda row: ("complete", None))
    cache = warm_cache(tmp_path)
    registry = RunRegistry(tmp_path / "registry.sqlite3")
    try:
        add_run(registry, tmp_path, "good-a", cache=cache)
        add_run(registry, tmp_path, "bad", returncode=7, cache=cache)
        add_run(registry, tmp_path, "good-b", cache=cache)

        counts = execute_pending(registry, workers=2)

        assert counts == {"complete": 2, "failed": 1}
        assert {row["run_id"]: row["status"] for row in registry.rows()} == {
            "bad": "failed",
            "good-a": "complete",
            "good-b": "complete",
        }
        assert {row["label"] for row in intervals(tmp_path)} == {
            "bad", "good-a", "good-b"
        }
    finally:
        registry.close()


def test_resume_recovers_running_attempt_and_uses_next_attempt(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(harness, "manifest_status", lambda row: ("complete", None))
    registry = RunRegistry(tmp_path / "registry.sqlite3")
    try:
        add_run(registry, tmp_path, "resume-me", max_attempts=2)
        stale = registry.start("resume-me")
        assert stale["attempt"] == 1

        counts = execute_pending(registry, workers=1)

        assert counts == {"complete": 1, "failed": 0}
        assert [
            (row["attempt"], row["status"])
            for row in registry.attempt_rows()
        ] == [(1, "failed"), (2, "complete")]
        assert registry.scheduler_rows()[-1]["recovered_runs"] == 1
    finally:
        registry.close()


def test_interrupt_terminates_active_child_and_records_failure(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(harness, "manifest_status", lambda row: ("complete", None))
    registry = RunRegistry(tmp_path / "registry.sqlite3")
    try:
        add_run(registry, tmp_path, "interrupt-me", delay=5)

        original_sleep = harness.time.sleep
        calls = 0

        def interrupt(seconds: float) -> None:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise KeyboardInterrupt()
            original_sleep(seconds)

        monkeypatch.setattr(harness.time, "sleep", interrupt)
        with pytest.raises(KeyboardInterrupt):
            execute_pending(registry, workers=1)

        assert registry.rows()[0]["status"] == "failed"
        assert registry.attempt_rows()[0]["status"] == "failed"
        assert registry.scheduler_rows()[0]["status"] == "interrupted"
        assert "scheduler interrupted" in registry.rows()[0]["error"]
    finally:
        registry.close()


def test_parallel_cold_cache_fails_before_claiming(tmp_path: Path) -> None:
    cold = tmp_path / "cold-cache"
    cold.mkdir()
    registry = RunRegistry(tmp_path / "registry.sqlite3")
    try:
        add_run(registry, tmp_path, "cold", cache=cold)

        with pytest.raises(ValueError, match="warm shared RAG cache"):
            execute_pending(registry, workers=2)

        assert registry.rows()[0]["status"] == "planned"
        assert registry.attempt_rows() == []
    finally:
        registry.close()
