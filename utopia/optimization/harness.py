"""Plan, execute, resume, and summarize seed-replicated institutional designs."""
from __future__ import annotations

import argparse
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping

from utopia.optimization.design_space import (
    candidate_to_cli,
    load_candidate,
    load_space,
    validate_candidate,
)
from utopia.optimization.metric_constitution import (
    constitution_sha256,
    load_metric_constitution,
)
from utopia.optimization.objective_evaluator import (
    evaluate_run,
    summarize_evaluations,
    write_evaluation,
)
from utopia.utils.paths import project_root


ROOT = project_root(__file__)


class SchedulerBusyError(RuntimeError):
    pass


class RunLease:
    """A lease inherited by a run subprocess so orphaned children stay visible."""

    def __init__(self, registry_path: Path, run_id: str):
        lease_id = hashlib.sha256(run_id.encode()).hexdigest()
        self.path = registry_path.with_name(
            registry_path.name + ".run-leases"
        ) / f"{lease_id}.lock"
        self.run_id = run_id
        self.stream = None

    def acquire(self) -> "RunLease":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self.stream.close()
            self.stream = None
            raise SchedulerBusyError(
                f"Run {self.run_id} still holds its execution lease at {self.path}"
            ) from error
        self.stream.seek(0)
        self.stream.truncate()
        self.stream.write(
            f"run_id={self.run_id} owner_pid={os.getpid()} acquired_utc={utc_now()}\n"
        )
        self.stream.flush()
        return self

    def fileno(self) -> int:
        if self.stream is None:
            raise RuntimeError("run lease is not acquired")
        return self.stream.fileno()

    def release(self) -> None:
        if self.stream is not None:
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
            self.stream.close()
            self.stream = None

    def relinquish_to_child(self) -> None:
        """Close only this descriptor after a child inherited the lease.

        Calling LOCK_UN here would also unlock the child's duplicated open file
        description. A plain close leaves the lease owned by the child until it
        exits, including when the scheduler subsequently crashes.
        """
        if self.stream is None:
            raise RuntimeError("run lease is not acquired")
        self.stream.close()
        self.stream = None

    def __enter__(self) -> "RunLease":
        return self.acquire()

    def __exit__(self, exc_type, exc, traceback):
        self.release()
        return False


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL,
    study_revision TEXT NOT NULL,
    design_id TEXT NOT NULL,
    design_json TEXT NOT NULL,
    sampler TEXT NOT NULL,
    fidelity TEXT NOT NULL,
    seed_role TEXT NOT NULL,
    seed INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('planned','running','complete','failed')),
    attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL,
    command_json TEXT NOT NULL,
    output_root TEXT NOT NULL,
    created_utc TEXT NOT NULL,
    started_utc TEXT,
    finished_utc TEXT,
    wall_seconds REAL,
    returncode INTEGER,
    error TEXT
);
CREATE INDEX IF NOT EXISTS runs_status_idx ON runs(status, attempt, max_attempts);
CREATE TABLE IF NOT EXISTS attempts (
    run_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('running','complete','failed')),
    started_utc TEXT NOT NULL,
    finished_utc TEXT,
    wall_seconds REAL,
    returncode INTEGER,
    error TEXT,
    PRIMARY KEY (run_id, attempt),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
CREATE TABLE IF NOT EXISTS schedulers (
    scheduler_id TEXT PRIMARY KEY,
    started_utc TEXT NOT NULL,
    finished_utc TEXT,
    status TEXT NOT NULL CHECK(status IN ('running','complete','interrupted')),
    worker_limit INTEGER NOT NULL,
    parent_pid INTEGER NOT NULL,
    recovered_runs INTEGER NOT NULL,
    error TEXT
);
CREATE TABLE IF NOT EXISTS attempt_schedulers (
    run_id TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    scheduler_id TEXT NOT NULL,
    worker_slot INTEGER NOT NULL,
    worker_limit INTEGER NOT NULL,
    subprocess_pid INTEGER,
    stdout_path TEXT NOT NULL,
    stderr_path TEXT NOT NULL,
    run_output_root TEXT NOT NULL,
    cache_root TEXT,
    effective_command_sha256 TEXT NOT NULL,
    PRIMARY KEY (run_id, attempt),
    FOREIGN KEY (run_id, attempt) REFERENCES attempts(run_id, attempt),
    FOREIGN KEY (scheduler_id) REFERENCES schedulers(scheduler_id)
);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any, length: int = 12) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()[:length]


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def validate_funding_reliability_policy(policy: Mapping[str, Any]) -> None:
    """Validate the versioned, non-objective funding pipeline gate."""
    for key in ("id", "version"):
        if not isinstance(policy.get(key), str) or not policy[key]:
            raise ValueError(f"funding_reliability_policy.{key} is required")
    if policy.get("failure_action") != "quarantine":
        raise ValueError("funding_reliability_policy.failure_action must be quarantine")
    minimum_targets = policy.get("minimum_targets")
    if type(minimum_targets) is not int or minimum_targets < 1:
        raise ValueError("funding_reliability_policy.minimum_targets must be positive")
    for key in (
        "maximum_semantic_invalid_attempt_rate",
        "maximum_sanitized_reference_attempt_rate",
        "maximum_request_error_attempt_rate",
        "maximum_terminal_drop_rate",
    ):
        value = policy.get(key)
        if type(value) not in {int, float} or not 0 <= value <= 1:
            raise ValueError(f"funding_reliability_policy.{key} must be between 0 and 1")


def validate_participation_measurement_policy(policy: Mapping[str, Any]) -> None:
    """Validate the pre-registered gate for an informative longitudinal fidelity."""
    for key in ("id", "version"):
        if not isinstance(policy.get(key), str) or not policy[key]:
            raise ValueError(f"participation_measurement_policy.{key} is required")
    if policy.get("failure_action") != "recalibrate_fidelity":
        raise ValueError(
            "participation_measurement_policy.failure_action must be recalibrate_fidelity"
        )
    for key in (
        "minimum_years",
        "minimum_initial_researchers",
        "minimum_protected_slice_support",
        "minimum_distinct_annual_active_counts",
    ):
        value = policy.get(key)
        if type(value) is not int or value < 1:
            raise ValueError(f"participation_measurement_policy.{key} must be positive")
    for prefix in ("aggregate", "protected_slice"):
        lower = policy.get(f"{prefix}_minimum_exclusive")
        upper = policy.get(f"{prefix}_maximum_exclusive")
        if (
            type(lower) not in {int, float}
            or type(upper) not in {int, float}
            or not 0 <= lower < upper <= 1
        ):
            raise ValueError(
                f"participation_measurement_policy {prefix} bounds must satisfy "
                "0 <= minimum < maximum <= 1"
            )


def load_study(path: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    study_path = Path(path).resolve()
    study = json.loads(study_path.read_text(encoding="utf-8"))
    if study.get("version") != 1 or not isinstance(study.get("id"), str):
        raise ValueError("Unsupported study specification")
    space = load_space(_resolve_repo_path(study["design_space"]))
    baseline = load_candidate(_resolve_repo_path(study["baseline_design"]))
    validate_candidate(space, baseline)
    constitution_path = study.get("metric_constitution")
    if not isinstance(constitution_path, str) or not constitution_path:
        raise ValueError("metric_constitution is required")
    constitution = load_metric_constitution(_resolve_repo_path(constitution_path))
    study["metric_constitution_sha256"] = constitution_sha256(constitution)
    sampler = study.get("sampler", {})
    if sampler.get("kind") not in {"random", "sobol"}:
        raise ValueError("sampler.kind must be random or sobol")
    if type(sampler.get("count")) is not int or sampler["count"] < 0:
        raise ValueError("sampler.count must be a nonnegative integer")
    if sampler["count"] == 0 and sampler.get("include_baseline") is not True:
        raise ValueError("sampler.count=0 requires include_baseline=true")
    if type(sampler.get("seed")) is not int:
        raise ValueError("sampler.seed must be an integer")
    for role in ("exploration", "selection", "confirmation"):
        seeds = study.get("seed_sets", {}).get(role)
        if not isinstance(seeds, list) or not seeds or any(type(seed) is not int for seed in seeds):
            raise ValueError(f"seed_sets.{role} must contain integers")
        if len(seeds) != len(set(seeds)):
            raise ValueError(f"seed_sets.{role} contains duplicates")
    all_seeds = [seed for seeds in study["seed_sets"].values() for seed in seeds]
    if len(all_seeds) != len(set(all_seeds)):
        raise ValueError("Seed roles must be disjoint")
    execution = study.get("execution", {})
    for key in ("model", "api_backend", "endpoint", "output_root", "data_cache_dir"):
        if not execution.get(key):
            raise ValueError(f"execution.{key} is required")
    if execution["api_backend"] not in {"vllm", "ollama"}:
        raise ValueError("Unsupported API backend")
    if type(execution.get("max_attempts")) is not int or execution["max_attempts"] < 1:
        raise ValueError("execution.max_attempts must be positive")
    reliability_policy = study.get("funding_reliability_policy")
    if reliability_policy is not None:
        if not isinstance(reliability_policy, dict):
            raise ValueError("funding_reliability_policy must be an object")
        validate_funding_reliability_policy(reliability_policy)
    participation_policy = study.get("participation_measurement_policy")
    if participation_policy is not None:
        if not isinstance(participation_policy, dict):
            raise ValueError("participation_measurement_policy must be an object")
        validate_participation_measurement_policy(participation_policy)
    return study, space, baseline


def study_revision(study: Mapping[str, Any], space: Mapping[str, Any]) -> str:
    return digest({"study": study, "space": space}, length=10)


def _unit_to_candidate(space: Mapping[str, Any], point: Iterable[float]) -> dict[str, Any]:
    candidate = {}
    for (name, rule), raw in zip(space["variables"].items(), point):
        unit = min(max(float(raw), 0.0), math.nextafter(1.0, 0.0))
        if rule["type"] == "float":
            value = rule["minimum"] + unit * (rule["maximum"] - rule["minimum"])
            candidate[name] = round(value, 8)
        elif rule["type"] == "integer":
            width = rule["maximum"] - rule["minimum"] + 1
            candidate[name] = rule["minimum"] + min(int(unit * width), width - 1)
        else:
            choices = rule["choices"]
            candidate[name] = choices[min(int(unit * len(choices)), len(choices) - 1)]
    validate_candidate(space, candidate)
    return candidate


def sample_designs(
    space: Mapping[str, Any], *, kind: str, count: int, seed: int
) -> list[dict[str, Any]]:
    if count < 0:
        raise ValueError("sample count must be nonnegative")
    if count == 0:
        return []
    dimensions = len(space["variables"])
    if kind == "random":
        rng = random.Random(seed)
        points = [[rng.random() for _ in range(dimensions)] for _ in range(count)]
    elif kind == "sobol":
        if count & (count - 1):
            raise ValueError("Sobol count must be a power of two")
        from scipy.stats import qmc

        points = qmc.Sobol(d=dimensions, scramble=True, seed=seed).random_base2(
            m=int(math.log2(count))
        )
    else:
        raise ValueError("kind must be random or sobol")
    return [_unit_to_candidate(space, point) for point in points]


def unique_designs(designs: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen, result = set(), []
    for design in designs:
        identity = canonical_json(design)
        if identity not in seen:
            seen.add(identity)
            result.append(dict(design))
    return result


def design_id(candidate: Mapping[str, Any]) -> str:
    return "d" + digest(candidate, length=12)


def run_id(
    study_id: str, revision: str, candidate: Mapping[str, Any], fidelity: str, role: str, seed: int
) -> str:
    safe_study = "".join(ch if ch.isalnum() or ch in "_.-" else "-" for ch in study_id)
    return f"opt-{safe_study}-{revision}-{fidelity}-{role}-{design_id(candidate)}-s{seed}"


def execution_root(study: Mapping[str, Any], revision: str) -> Path:
    base = _resolve_repo_path(study["execution"]["output_root"])
    return base / study["id"] / revision


def build_command(
    study: Mapping[str, Any], space: Mapping[str, Any], candidate: Mapping[str, Any],
    *, run: str, fidelity: str, seed: int, output_root: Path,
) -> list[str]:
    if fidelity not in space["fidelities"]:
        raise ValueError(f"Unknown fidelity {fidelity!r}")
    level = space["fidelities"][fidelity]
    stage = level.get("experiment_stage")
    if stage is None:
        stage = {"smoke": "smoke", "screen": "pilot", "confirm": "confirmatory"}.get(
            fidelity
        )
    if stage not in {"smoke", "pilot", "confirmatory"}:
        raise ValueError(
            f"Fidelity {fidelity!r} must define a valid experiment_stage"
        )
    execution = study["execution"]
    command = [
        sys.executable, "-B", "-m", "utopia",
        "--model", execution["model"],
        "--vllm_url", execution["endpoint"],
        "--api-backend", execution["api_backend"],
        "--batch_size", str(execution["batch_size"]),
        "--experiment_stage", stage,
        "--run-id", run,
        "--output-dir", str(output_root),
        "--data-cache-dir", str(_resolve_repo_path(execution["data_cache_dir"])),
        "--seed", str(seed),
        "--num_years", str(level["num_years"]),
        "--num_institutions", str(level["num_institutions"]),
        "--num_conferences", str(level["num_conferences"]),
    ]
    command.extend(candidate_to_cli(space, candidate, years=level["num_years"]))
    return command


class RunRegistry:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def add(self, record: Mapping[str, Any]) -> bool:
        before = self.connection.total_changes
        self.connection.execute(
            """INSERT OR IGNORE INTO runs
            (run_id, study_id, study_revision, design_id, design_json, sampler, fidelity,
             seed_role, seed, status, max_attempts, command_json, output_root, created_utc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'planned', ?, ?, ?, ?)""",
            tuple(record[key] for key in (
                "run_id", "study_id", "study_revision", "design_id", "design_json",
                "sampler", "fidelity", "seed_role", "seed", "max_attempts",
                "command_json", "output_root", "created_utc",
            )),
        )
        self.connection.commit()
        return self.connection.total_changes > before

    def rows(self, where: str = "1=1", parameters: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            f"SELECT * FROM runs WHERE {where} ORDER BY run_id", parameters
        ))

    def recover_interrupted(self) -> int:
        interrupted = self.rows("status='running'")
        # An abruptly terminated scheduler can leave its child simulation alive.
        # The child inherits this lease file descriptor, so acquire every affected
        # run lease before changing any registry state. If even one remains held,
        # leave all rows untouched and refuse to launch possible double writers.
        recovery_leases: list[RunLease] = []
        try:
            for row in interrupted:
                recovery_leases.append(
                    RunLease(self.path, row["run_id"]).acquire()
                )
        except BaseException:
            for lease in recovery_leases:
                lease.release()
            raise
        now = utc_now()
        reason = "Harness process ended before recording completion; retry may resume checkpoint"
        try:
            for row in interrupted:
                self.connection.execute(
                    """UPDATE runs SET status='failed', finished_utc=?, error=? WHERE run_id=?""",
                    (now, reason, row["run_id"]),
                )
                self.connection.execute(
                    """UPDATE attempts SET status='failed', finished_utc=?, error=?
                       WHERE run_id=? AND attempt=? AND status='running'""",
                    (now, reason, row["run_id"], row["attempt"]),
                )
            self.connection.execute(
                """UPDATE schedulers SET status='interrupted', finished_utc=?,
                   error=COALESCE(error, ?)
                   WHERE status='running'""",
                (now, reason),
            )
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise
        finally:
            for lease in recovery_leases:
                lease.release()
        return len(interrupted)

    def start(self, run: str) -> sqlite3.Row:
        row = self.claim(run)
        if row is None:
            raise ValueError(f"Run is not atomically claimable: {run}")
        return row

    def claim(self, run: str) -> sqlite3.Row | None:
        """Atomically transition one retryable run to a new running attempt."""
        started = utc_now()
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            cursor = self.connection.execute(
                """UPDATE runs SET status='running', attempt=attempt+1, started_utc=?,
                   finished_utc=NULL, returncode=NULL, error=NULL
                   WHERE run_id=? AND status IN ('planned','failed')
                   AND attempt < max_attempts""",
                (started, run),
            )
            if cursor.rowcount != 1:
                self.connection.rollback()
                return None
            row = self.connection.execute(
                "SELECT * FROM runs WHERE run_id=?", (run,)
            ).fetchone()
            self.connection.execute(
                """INSERT INTO attempts (run_id, attempt, status, started_utc)
                   VALUES (?, ?, 'running', ?)""",
                (run, row["attempt"], row["started_utc"]),
            )
            self.connection.commit()
            return row
        except BaseException:
            self.connection.rollback()
            raise

    def start_scheduler(
        self, scheduler_id: str, *, workers: int, recovered_runs: int
    ) -> None:
        self.connection.execute(
            """INSERT INTO schedulers
               (scheduler_id, started_utc, status, worker_limit, parent_pid,
                recovered_runs)
               VALUES (?, ?, 'running', ?, ?, ?)""",
            (scheduler_id, utc_now(), workers, os.getpid(), recovered_runs),
        )
        self.connection.commit()

    def finish_scheduler(
        self, scheduler_id: str, *, status: str, error: str | None = None
    ) -> None:
        if status not in {"complete", "interrupted"}:
            raise ValueError("scheduler status must be complete or interrupted")
        self.connection.execute(
            """UPDATE schedulers SET status=?, finished_utc=?, error=?
               WHERE scheduler_id=?""",
            (status, utc_now(), error, scheduler_id),
        )
        self.connection.commit()

    def attach_scheduler_attempt(
        self,
        row: Mapping[str, Any],
        *,
        scheduler_id: str,
        worker_slot: int,
        workers: int,
        stdout_path: Path,
        stderr_path: Path,
        run_output_root: Path,
        cache_root: Path | None,
        effective_command: list[str],
    ) -> None:
        self.connection.execute(
            """INSERT INTO attempt_schedulers
               (run_id, attempt, scheduler_id, worker_slot, worker_limit,
                stdout_path, stderr_path, run_output_root, cache_root,
                effective_command_sha256)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row["run_id"],
                row["attempt"],
                scheduler_id,
                worker_slot,
                workers,
                str(stdout_path),
                str(stderr_path),
                str(run_output_root),
                str(cache_root) if cache_root is not None else None,
                hashlib.sha256(canonical_json(effective_command).encode()).hexdigest(),
            ),
        )
        self.connection.commit()

    def set_subprocess_pid(self, run: str, attempt: int, pid: int) -> None:
        self.connection.execute(
            """UPDATE attempt_schedulers SET subprocess_pid=?
               WHERE run_id=? AND attempt=?""",
            (pid, run, attempt),
        )
        self.connection.commit()

    def finish(
        self, run: str, *, status: str, returncode: int, wall_seconds: float, error: str | None
    ) -> None:
        if status not in {"complete", "failed"}:
            raise ValueError("finish status must be complete or failed")
        self.connection.execute(
            """UPDATE runs SET status=?, finished_utc=?, returncode=?, wall_seconds=?, error=?
               WHERE run_id=?""",
            (status, utc_now(), returncode, wall_seconds, error, run),
        )
        row = self.rows("run_id=?", (run,))[0]
        self.connection.execute(
            """UPDATE attempts SET status=?, finished_utc=?, returncode=?, wall_seconds=?, error=?
               WHERE run_id=? AND attempt=?""",
            (status, row["finished_utc"], returncode, wall_seconds, error, run, row["attempt"]),
        )
        self.connection.commit()

    def attempt_rows(self) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            "SELECT * FROM attempts ORDER BY run_id, attempt"
        ))

    def scheduler_rows(self) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            "SELECT * FROM schedulers ORDER BY started_utc, scheduler_id"
        ))

    def attempt_scheduler_rows(self) -> list[sqlite3.Row]:
        return list(self.connection.execute(
            "SELECT * FROM attempt_schedulers ORDER BY run_id, attempt"
        ))


def plan_study(
    study: Mapping[str, Any], space: Mapping[str, Any], baseline: Mapping[str, Any],
    *, fidelity: str, seed_role: str, sampler_kind: str | None = None,
    count: int | None = None,
) -> dict[str, Any]:
    revision = study_revision(study, space)
    root = execution_root(study, revision)
    root.mkdir(parents=True, exist_ok=True)
    sampler = study["sampler"]
    kind = sampler_kind or sampler["kind"]
    sample_count = sampler["count"] if count is None else count
    if sample_count == 0 and sampler.get("include_baseline") is not True:
        raise ValueError("sample count 0 requires include_baseline=true")
    designs = sample_designs(space, kind=kind, count=sample_count, seed=sampler["seed"])
    if sampler.get("include_baseline"):
        designs.insert(0, dict(baseline))
    designs = unique_designs(designs)
    seeds = study["seed_sets"].get(seed_role)
    if not seeds:
        raise ValueError(f"Unknown or empty seed role {seed_role!r}")
    constitution = load_metric_constitution(_resolve_repo_path(study["metric_constitution"]))
    snapshot = {
        "study": study,
        "space": space,
        "metric_constitution": constitution,
        "study_revision": revision,
    }
    snapshot_path = root / "study-snapshot.json"
    encoded = json.dumps(snapshot, indent=2, sort_keys=True) + "\n"
    if snapshot_path.exists() and snapshot_path.read_text() != encoded:
        raise ValueError("Study snapshot changed within an immutable revision directory")
    snapshot_path.write_text(encoded)
    added = 0
    registry_path = root / "registry.sqlite3"
    registry = RunRegistry(registry_path)
    try:
        for candidate in designs:
            for seed in seeds:
                identity = run_id(study["id"], revision, candidate, fidelity, seed_role, seed)
                command = build_command(
                    study, space, candidate, run=identity, fidelity=fidelity,
                    seed=seed, output_root=root,
                )
                added += registry.add({
                    "run_id": identity,
                    "study_id": study["id"],
                    "study_revision": revision,
                    "design_id": design_id(candidate),
                    "design_json": canonical_json(candidate),
                    "sampler": kind,
                    "fidelity": fidelity,
                    "seed_role": seed_role,
                    "seed": seed,
                    "max_attempts": study["execution"]["max_attempts"],
                    "command_json": canonical_json(command),
                    "output_root": str(root),
                    "created_utc": utc_now(),
                })
        total = len(registry.rows())
    finally:
        registry.close()
    return {"study_revision": revision, "root": str(root), "designs": len(designs),
            "seeds": len(seeds), "added_runs": added, "total_runs": total}


def manifest_status(row: Mapping[str, Any]) -> tuple[str, str | None]:
    path = Path(row["output_root"]) / "docs" / row["run_id"] / "run_manifest.json"
    if not path.exists():
        return "missing", None
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        return "invalid", str(error)
    if manifest.get("status") == "complete":
        integrity_path = path.parent / "integrity_checks.json"
        if integrity_path.exists():
            try:
                checks = json.loads(integrity_path.read_text())
            except (OSError, json.JSONDecodeError) as error:
                return "invalid", f"invalid integrity report: {error}"
            if not isinstance(checks, list) or any(not isinstance(check, dict) for check in checks):
                return "invalid", "invalid integrity report: expected a list of objects"
            failed = [check for check in checks if check.get("passed") is not True]
            if failed:
                return "invalid", f"integrity checks failed for years: " + ",".join(
                    str(check.get("year", "unknown")) for check in failed
                )

        args = manifest.get("args")
        output_dir = args.get("output_dir") if isinstance(args, dict) else None
        if isinstance(output_dir, str):
            for summary_path in sorted(Path(output_dir).glob(
                    "funding_application_trace_year_*.summary.json")):
                try:
                    summary = json.loads(summary_path.read_text())
                except (OSError, json.JSONDecodeError) as error:
                    return "invalid", f"invalid funding application trace: {error}"
                if summary.get("passed") is not True:
                    return "invalid", f"funding application trace failed: {summary_path.name}"
        return "complete", None
    return str(manifest.get("status", "unknown")), manifest.get("wrapper_error")


class SchedulerFileLock:
    """Single parent scheduler lease for one registry on this host."""

    def __init__(self, registry_path: Path):
        self.path = registry_path.with_name(registry_path.name + ".scheduler.lock")
        self.stream = None

    def __enter__(self):
        self.stream = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self.stream.close()
            self.stream = None
            raise SchedulerBusyError(
                f"Another harness scheduler holds {self.path}"
            ) from error
        self.stream.seek(0)
        self.stream.truncate()
        self.stream.write(f"pid={os.getpid()} started_utc={utc_now()}\n")
        self.stream.flush()
        return self

    def __exit__(self, exc_type, exc, traceback):
        if self.stream is not None:
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
            self.stream.close()
        return False


def _command_option(command: list[str], option: str) -> str | None:
    try:
        index = command.index(option)
    except ValueError:
        return None
    if index + 1 >= len(command):
        raise ValueError(f"{option} is missing its value")
    return command[index + 1]


def _replace_command_option(command: list[str], option: str, value: Path) -> list[str]:
    result = list(command)
    try:
        index = result.index(option)
    except ValueError as error:
        raise ValueError(
            f"Parallel execution requires explicit {option} in every command"
        ) from error
    if index + 1 >= len(result):
        raise ValueError(f"{option} is missing its value")
    result[index + 1] = str(value)
    return result


def validate_warm_shared_cache(path: Path) -> dict[str, Any]:
    """Reject parallel cold starts that could race while constructing RAG."""
    rag = path / "rag"
    documents = sorted(
        item for item in rag.glob("documents-*.pkl")
        if item.is_file() and item.stat().st_size > 0
    )
    embeddings = sorted(
        item for item in rag.glob("embeddings-*.pt")
        if item.is_file() and item.stat().st_size > 0
    )
    if not documents or not embeddings:
        raise ValueError(
            "workers > 1 requires a warm shared RAG cache containing both "
            "rag/documents-*.pkl and rag/embeddings-*.pt; run once with "
            "--workers 1 to warm it safely"
        )
    return {
        "shared_cache": str(path),
        "document_caches": len(documents),
        "embedding_caches": len(embeddings),
    }


def _link_or_copy(source: str, destination: str) -> str:
    try:
        os.link(source, destination)
        return destination
    except OSError:
        return shutil.copy2(source, destination)


def seed_isolated_run_cache(shared: Path, target: Path) -> Path:
    """Seed a private mutable cache with a read-mostly RAG snapshot.

    RAG writers use atomic replacement, so hard-linked warm RAG files cannot
    be modified in place. Other cache families include in-place NPZ writers
    and must be copied normally to prevent cross-run corruption.
    """
    marker = target / ".scienceutopia-cache-seed-v1"
    if marker.exists():
        return target
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.mkdir()
    for source in shared.iterdir():
        destination = target / source.name
        if source.is_dir():
            shutil.copytree(
                source,
                destination,
                copy_function=(
                    _link_or_copy if source.name == "rag" else shutil.copy2
                ),
            )
        else:
            shutil.copy2(source, destination)
    marker.write_text(
        json.dumps({
            "source": str(shared),
            "seeded_utc": utc_now(),
            "rag_mode": "hardlink-with-copy-fallback",
            "mutable_cache_mode": "copy",
        }, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


@dataclass
class ActiveRun:
    row: Mapping[str, Any]
    process: subprocess.Popen
    started: float
    worker_slot: int
    streams: tuple[Any, ...]


def _close_streams(streams: Iterable[Any]) -> None:
    seen: set[int] = set()
    for stream in streams:
        if stream is not None and id(stream) not in seen:
            seen.add(id(stream))
            stream.close()


def _finalize_process(
    registry: RunRegistry,
    active: ActiveRun,
    *,
    forced_error: str | None = None,
) -> str:
    _close_streams(active.streams)
    elapsed = time.monotonic() - active.started
    returncode = active.process.returncode
    if returncode is None:
        returncode = -1
    status, manifest_error = manifest_status(active.row)
    complete = forced_error is None and returncode == 0 and status == "complete"
    final_status = "complete" if complete else "failed"
    error = None if complete else (
        forced_error
        or manifest_error
        or f"process returncode={returncode}, manifest status={status}"
    )
    registry.finish(
        active.row["run_id"],
        status=final_status,
        returncode=returncode,
        wall_seconds=elapsed,
        error=error,
    )
    return final_status


def execute_pending(
    registry: RunRegistry,
    *,
    limit: int | None = None,
    selected_run_id: str | None = None,
    workers: int = 1,
    execution: Mapping[str, Any] | None = None,
) -> dict[str, int]:
    if type(workers) is not int or workers < 1:
        raise ValueError("workers must be a positive integer")
    if workers > 1 and execution is not None:
        if execution.get("api_backend") != "ollama":
            raise ValueError(
                "bounded multi-run scheduling currently requires api_backend=ollama"
            )

    with SchedulerFileLock(registry.path):
        recovered = registry.recover_interrupted()
        if selected_run_id is None:
            runnable = registry.rows(
                "status IN ('planned','failed') AND attempt < max_attempts"
            )
        else:
            runnable = registry.rows(
                "run_id=? AND status IN ('planned','failed') AND attempt < max_attempts",
                (selected_run_id,),
            )
            if not runnable:
                raise ValueError(
                    "Run is missing, complete, active, or out of attempts: "
                    f"{selected_run_id}"
                )
        if limit is not None:
            runnable = runnable[:limit]

        shared_cache: Path | None = None
        if workers > 1 and runnable:
            if execution is not None:
                expected_endpoint = str(execution["endpoint"])
                expected_model = str(execution["model"])
                for pending in runnable:
                    command = json.loads(pending["command_json"])
                    if _command_option(command, "--api-backend") != "ollama":
                        raise ValueError(
                            "All parallel commands must use api_backend=ollama"
                        )
                    if _command_option(command, "--vllm_url") != expected_endpoint:
                        raise ValueError(
                            "All parallel commands must share the study Ollama endpoint"
                        )
                    if _command_option(command, "--model") != expected_model:
                        raise ValueError(
                            "All parallel commands must share the study Ollama model"
                        )
            if execution is not None:
                configured = _resolve_repo_path(execution["data_cache_dir"])
            else:
                configured_value = _command_option(
                    json.loads(runnable[0]["command_json"]),
                    "--data-cache-dir",
                )
                if configured_value is None:
                    raise ValueError(
                        "workers > 1 requires an explicit shared data cache"
                    )
                configured = Path(configured_value)
            shared_cache = configured.resolve()
            validate_warm_shared_cache(shared_cache)

        scheduler_id = "scheduler-" + digest({
            "registry": str(registry.path.resolve()),
            "pid": os.getpid(),
            "time_ns": time.time_ns(),
        })
        registry.start_scheduler(
            scheduler_id, workers=workers, recovered_runs=recovered
        )
        counts = {"complete": 0, "failed": 0}
        queue = list(runnable)
        active: dict[str, ActiveRun] = {}
        available_slots = set(range(workers))
        scheduler_finished = False

        try:
            while queue or active:
                while queue and available_slots:
                    pending = queue.pop(0)
                    slot = min(available_slots)
                    available_slots.remove(slot)
                    try:
                        lease = RunLease(
                            registry.path, pending["run_id"]
                        ).acquire()
                    except SchedulerBusyError:
                        available_slots.add(slot)
                        raise
                    row = registry.claim(pending["run_id"])
                    if row is None:
                        lease.release()
                        available_slots.add(slot)
                        continue
                    command = json.loads(row["command_json"])
                    cache_root = None
                    if workers > 1:
                        cache_root = (
                            Path(row["output_root"])
                            / "run-caches"
                            / row["run_id"]
                        )
                        seed_isolated_run_cache(shared_cache, cache_root)
                        command = _replace_command_option(
                            command, "--data-cache-dir", cache_root
                        )

                    log_dir = (
                        Path(row["output_root"])
                        / "registry-logs"
                        / row["run_id"]
                    )
                    log_dir.mkdir(parents=True, exist_ok=True)
                    log_path = log_dir / f"attempt-{row['attempt']}.log"
                    if workers == 1:
                        combined = log_path.open("w", encoding="utf-8")
                        combined.write(
                            "COMMAND " + canonical_json(command) + "\n"
                        )
                        combined.write(
                            f"SCHEDULER {scheduler_id} WORKER {slot}/1\n"
                        )
                        combined.flush()
                        stdout_path = stderr_path = log_path
                        stdout_stream = combined
                        stderr_stream = subprocess.STDOUT
                        streams = (combined,)
                    else:
                        stdout_path = (
                            log_dir / f"attempt-{row['attempt']}.stdout.log"
                        )
                        stderr_path = (
                            log_dir / f"attempt-{row['attempt']}.stderr.log"
                        )
                        log_path.write_text(
                            "COMMAND " + canonical_json(command) + "\n"
                            + f"SCHEDULER {scheduler_id} WORKER {slot}/{workers}\n"
                            + f"STDOUT {stdout_path}\nSTDERR {stderr_path}\n",
                            encoding="utf-8",
                        )
                        stdout_stream = stdout_path.open("w", encoding="utf-8")
                        stderr_stream = stderr_path.open("w", encoding="utf-8")
                        streams = (stdout_stream, stderr_stream)

                    run_output_root = (
                        Path(row["output_root"])
                        / "checkpoints"
                        / row["run_id"]
                    )
                    registry.attach_scheduler_attempt(
                        row,
                        scheduler_id=scheduler_id,
                        worker_slot=slot,
                        workers=workers,
                        stdout_path=stdout_path,
                        stderr_path=stderr_path,
                        run_output_root=run_output_root,
                        cache_root=cache_root,
                        effective_command=command,
                    )
                    environment = os.environ.copy()
                    environment.update({
                        "UTOPIA_HARNESS_SCHEDULER_ID": scheduler_id,
                        "UTOPIA_HARNESS_WORKER_SLOT": str(slot),
                        "UTOPIA_HARNESS_WORKERS": str(workers),
                    })
                    started = time.monotonic()
                    try:
                        process = subprocess.Popen(
                            command,
                            cwd=ROOT,
                            stdout=stdout_stream,
                            stderr=stderr_stream,
                            text=True,
                            env=environment,
                            pass_fds=(lease.fileno(),),
                        )
                    except Exception as error:
                        _close_streams(streams)
                        lease.release()
                        registry.finish(
                            row["run_id"],
                            status="failed",
                            returncode=127,
                            wall_seconds=time.monotonic() - started,
                            error=f"subprocess start failed: {error}",
                        )
                        counts["failed"] += 1
                        available_slots.add(slot)
                        continue
                    lease.relinquish_to_child()
                    registry.set_subprocess_pid(
                        row["run_id"], row["attempt"], process.pid
                    )
                    active[row["run_id"]] = ActiveRun(
                        row=row,
                        process=process,
                        started=started,
                        worker_slot=slot,
                        streams=streams,
                    )

                finished = []
                for run, item in active.items():
                    returncode = item.process.poll()
                    if returncode is not None:
                        finished.append(run)
                for run in finished:
                    item = active.pop(run)
                    final_status = _finalize_process(registry, item)
                    counts[final_status] += 1
                    available_slots.add(item.worker_slot)
                if active and not finished:
                    time.sleep(0.05)

            registry.finish_scheduler(scheduler_id, status="complete")
            scheduler_finished = True
            return counts
        except BaseException as error:
            for item in active.values():
                item.process.terminate()
            for item in active.values():
                try:
                    item.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    item.process.kill()
                    item.process.wait()
                final_status = _finalize_process(
                    registry,
                    item,
                    forced_error=f"scheduler interrupted: {type(error).__name__}",
                )
                counts[final_status] += 1
            registry.finish_scheduler(
                scheduler_id,
                status="interrupted",
                error=f"{type(error).__name__}: {error}",
            )
            scheduler_finished = True
            raise
        finally:
            if not scheduler_finished:
                registry.finish_scheduler(
                    scheduler_id,
                    status="interrupted",
                    error="scheduler exited without final status",
                )


def numeric_summary(values: Iterable[float]) -> dict[str, float | int | None]:
    finite = [float(value) for value in values if math.isfinite(float(value))]
    if not finite:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {"n": len(finite), "mean": statistics.fmean(finite),
            "median": statistics.median(finite), "min": min(finite), "max": max(finite)}


def evaluate_funding_reliability(
    diagnostic: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[str, Any]:
    """Apply an engineering gate without turning reliability into an objective."""
    validate_funding_reliability_policy(policy)
    targets = int(diagnostic.get("targets", 0))
    attempts = int(diagnostic.get("generation_attempts", 0))
    rates = {
        "semantic_invalid_attempt_rate": (
            int(diagnostic.get("semantic_invalid_attempts", 0)) / attempts
            if attempts else None
        ),
        "sanitized_reference_attempt_rate": (
            int(diagnostic.get("sanitized_reference_attempts", 0)) / attempts
            if attempts else None
        ),
        "request_error_attempt_rate": (
            int(diagnostic.get("request_error_attempts", 0)) / attempts
            if attempts else None
        ),
        "terminal_drop_rate": (
            int(diagnostic.get("dropped", 0)) / targets if targets else None
        ),
    }
    reasons = []
    if targets < int(policy["minimum_targets"]):
        state = "insufficient_evidence"
        reasons.append(
            f"requires at least {policy['minimum_targets']} funding application targets"
        )
    else:
        thresholds = {
            "semantic_invalid_attempt_rate": policy[
                "maximum_semantic_invalid_attempt_rate"
            ],
            "sanitized_reference_attempt_rate": policy[
                "maximum_sanitized_reference_attempt_rate"
            ],
            "request_error_attempt_rate": policy["maximum_request_error_attempt_rate"],
            "terminal_drop_rate": policy["maximum_terminal_drop_rate"],
        }
        for metric, threshold in thresholds.items():
            value = rates[metric]
            if value is None or value > threshold:
                reasons.append(f"{metric}={value!r} exceeds maximum {threshold}")
        state = "pass" if not reasons else "fail"
    return {
        "run_id": diagnostic.get("run_id"),
        "policy_id": policy["id"],
        "policy_version": policy["version"],
        "failure_action": policy["failure_action"],
        "state": state,
        "comparison_eligible": state == "pass",
        "disposition": "eligible" if state == "pass" else policy["failure_action"],
        "policy_sha256": hashlib.sha256(
            canonical_json(policy).encode("utf-8")
        ).hexdigest(),
        "rates": rates,
        "reasons": reasons,
    }


def apply_funding_reliability_to_readiness(
    objective_readiness: list[dict[str, Any]],
    completed: Iterable[Mapping[str, Any]],
    reliability_evaluations: Iterable[Mapping[str, Any]],
) -> None:
    """Quarantine unreliable runs from comparison without changing objectives."""
    reliability_by_run = {
        item["run_id"]: item for item in reliability_evaluations
    }
    runs_by_design: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in completed:
        runs_by_design[row["design_id"]].append(row)
    for readiness in objective_readiness:
        states = [
            reliability_by_run.get(row["run_id"], {"state": "insufficient_evidence"})[
                "state"
            ]
            for row in runs_by_design[readiness["design_id"]]
        ]
        readiness["funding_reliability_states"] = states
        if any(state != "pass" for state in states):
            readiness["authorized_for_ranking"] = False
            reason = "one or more runs did not pass the funding reliability gate"
            if reason not in readiness["blocking_reasons"]:
                readiness["blocking_reasons"].append(reason)


def evaluate_participation_measurement_suitability(
    evaluation: Mapping[str, Any] | None,
    docs: Path,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Test whether a completed longitudinal run escapes floor/ceiling saturation."""
    validate_participation_measurement_policy(policy)
    run = evaluation.get("run_id") if evaluation else docs.name
    reasons: list[str] = []
    evidence_errors: list[str] = []
    observations: dict[str, Any] = {}

    metric = (evaluation or {}).get("metrics", {}).get("active-researcher-fraction")
    if not isinstance(metric, dict) or metric.get("status") != "measured":
        evidence_errors.append("active-researcher-fraction is not measured")

    try:
        import pandas as pd

        agents = pd.read_parquet(docs / "agent_year.parquet")
        required = {"agent_id", "year", "is_active", "resource_band"}
        if agents.empty or not required.issubset(agents.columns):
            evidence_errors.append("agent-year longitudinal fields are missing")
        else:
            years = sorted(int(year) for year in agents["year"].unique())
            first_year, final_year = years[0], years[-1]
            initial = agents.loc[agents["year"] == first_year].copy()
            final = agents.loc[agents["year"] == final_year].copy()
            if initial["agent_id"].duplicated().any() or final["agent_id"].duplicated().any():
                evidence_errors.append("initial or final agent status is duplicated")
            initial_ids = set(initial["agent_id"])
            if not initial_ids or set(final["agent_id"]) != initial_ids:
                evidence_errors.append("final status is missing for initial researchers")
            band_counts = agents.groupby("agent_id")["resource_band"].nunique(dropna=False)
            if agents["resource_band"].isna().any() or (band_counts != 1).any():
                evidence_errors.append("protected resource-band membership is not stable")

            lower_ids = set(
                initial.loc[initial["resource_band"] == "lower-band", "agent_id"]
            )
            final_by_id = final.set_index("agent_id")
            aggregate_fraction = (
                float(final["is_active"].astype(bool).sum()) / len(initial_ids)
                if initial_ids else None
            )
            protected_fraction = (
                float(final_by_id.loc[list(lower_ids), "is_active"].astype(bool).sum())
                / len(lower_ids)
                if lower_ids and lower_ids <= set(final_by_id.index) else None
            )
            annual_counts = [
                {
                    "year": year,
                    "active": int(
                        agents.loc[agents["year"] == year, "is_active"].astype(bool).sum()
                    ),
                }
                for year in years
            ]
            observations = {
                "years_observed": len(years),
                "first_year": first_year,
                "final_year": final_year,
                "initial_researchers": len(initial_ids),
                "protected_slice_support": len(lower_ids),
                "aggregate_final_active_fraction": aggregate_fraction,
                "protected_slice_final_active_fraction": protected_fraction,
                "annual_active_counts": annual_counts,
                "distinct_annual_active_counts": len(
                    {row["active"] for row in annual_counts}
                ),
            }
    except (OSError, ValueError, KeyError, ImportError) as error:
        evidence_errors.append(f"longitudinal evidence is unreadable: {error}")

    if not evidence_errors:
        checks = (
            ("years_observed", "minimum_years"),
            ("initial_researchers", "minimum_initial_researchers"),
            ("protected_slice_support", "minimum_protected_slice_support"),
            (
                "distinct_annual_active_counts",
                "minimum_distinct_annual_active_counts",
            ),
        )
        for observation, threshold in checks:
            if observations[observation] < policy[threshold]:
                reasons.append(
                    f"{observation}={observations[observation]} is below "
                    f"{threshold}={policy[threshold]}"
                )
        for prefix, observation in (
            ("aggregate", "aggregate_final_active_fraction"),
            ("protected_slice", "protected_slice_final_active_fraction"),
        ):
            value = observations[observation]
            lower = policy[f"{prefix}_minimum_exclusive"]
            upper = policy[f"{prefix}_maximum_exclusive"]
            if value is None or not lower < value < upper:
                reasons.append(
                    f"{observation}={value!r} is not inside ({lower}, {upper})"
                )

    state = "insufficient_evidence" if evidence_errors else ("fail" if reasons else "pass")
    return {
        "run_id": run,
        "policy_id": policy["id"],
        "policy_version": policy["version"],
        "policy_sha256": hashlib.sha256(
            canonical_json(policy).encode("utf-8")
        ).hexdigest(),
        "state": state,
        "comparison_eligible": state == "pass",
        "disposition": "eligible" if state == "pass" else policy["failure_action"],
        "observations": observations,
        "reasons": evidence_errors + reasons,
    }


def apply_participation_suitability_to_readiness(
    objective_readiness: list[dict[str, Any]],
    completed: Iterable[Mapping[str, Any]],
    suitability_evaluations: Iterable[Mapping[str, Any]],
) -> None:
    """Block ranking when the study's primary participation signal is saturated."""
    suitability_by_run = {
        item["run_id"]: item for item in suitability_evaluations
    }
    runs_by_design: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in completed:
        runs_by_design[row["design_id"]].append(row)
    for readiness in objective_readiness:
        states = [
            suitability_by_run.get(
                row["run_id"], {"state": "insufficient_evidence"}
            )["state"]
            for row in runs_by_design[readiness["design_id"]]
        ]
        readiness["participation_measurement_states"] = states
        if any(state != "pass" for state in states):
            readiness["authorized_for_ranking"] = False
            reason = "one or more runs did not pass the participation measurement gate"
            if reason not in readiness["blocking_reasons"]:
                readiness["blocking_reasons"].append(reason)


def build_report(
    registry: RunRegistry, constitution: Mapping[str, Any] | None = None,
    funding_reliability_policy: Mapping[str, Any] | None = None,
    participation_measurement_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rows = registry.rows()
    attempts = registry.attempt_rows()
    schedulers = registry.scheduler_rows()
    attempt_schedulers = registry.attempt_scheduler_rows()
    by_status: dict[str, int] = {}
    for row in rows:
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
    completed = [row for row in rows if row["status"] == "complete"]
    activity, pipeline_diagnostics, objective_evaluations, report_errors = [], [], [], []
    for row in completed:
        trace_root = Path(row["output_root"]) / "checkpoints" / row["run_id"]
        trace_summaries = []
        for trace_path in sorted(trace_root.glob(
                "funding_application_trace_year_*.summary.json")):
            try:
                trace_summaries.append(json.loads(trace_path.read_text()))
            except (OSError, json.JSONDecodeError) as error:
                report_errors.append({
                    "run_id": row["run_id"],
                    "error": f"invalid funding trace summary {trace_path.name}: {error}",
                })
        if trace_summaries:
            count_fields = (
                "targets", "validated", "submitted", "declined_by_agent", "dropped", "evaluated",
                "decided", "funded", "allocations_recorded", "allocations_applied",
                "generation_attempts", "semantic_invalid_attempts",
                "sanitized_reference_attempts", "request_error_attempts",
            )
            pipeline_diagnostics.append({
                "run_id": row["run_id"],
                **{
                    field: sum(summary.get("counts", {}).get(field, 0)
                               for summary in trace_summaries)
                    for field in count_fields
                },
            })
        if constitution is not None:
            try:
                evaluation = evaluate_run(
                    run_id=row["run_id"], output_root=row["output_root"],
                    constitution=constitution,
                )
                write_evaluation(evaluation, row["output_root"])
                objective_evaluations.append(evaluation)
            except Exception as error:
                report_errors.append({
                    "run_id": row["run_id"], "error": f"objective evaluation failed: {error}"
                })
        try:
            from utopia.analysis.release import summarize_run

            result, _, _, _ = summarize_run(row["run_id"], row["output_root"])
            last = result["annual"][-1]
            activity.append({
                "run_id": row["run_id"], "design_id": row["design_id"], "seed": row["seed"],
                "papers": last["cumulative_unique_papers"],
                "accepted": last["cumulative_accepted_papers"],
                "reviews": result["total_reviews"],
                "active_researchers": last["active_researchers"],
                "total_resources": last["total_resources"],
            })
        except Exception as error:
            report_errors.append({"run_id": row["run_id"], "error": str(error)})
    fields = ("papers", "accepted", "reviews", "active_researchers", "total_resources")
    attempted_runs = by_status.get("complete", 0) + by_status.get("failed", 0)
    attempt_status: dict[str, int] = {}
    for attempt in attempts:
        attempt_status[attempt["status"]] = attempt_status.get(attempt["status"], 0) + 1
    finished_attempts = [attempt for attempt in attempts if attempt["status"] != "running"]
    reliability_evaluations = []
    if funding_reliability_policy is not None:
        diagnostic_by_run = {item["run_id"]: item for item in pipeline_diagnostics}
        reliability_evaluations = [
            evaluate_funding_reliability(
                diagnostic_by_run.get(row["run_id"], {"run_id": row["run_id"]}),
                funding_reliability_policy,
            )
            for row in completed
        ]
    objective_readiness = (
        summarize_evaluations(objective_evaluations, completed, constitution)
        if constitution is not None else []
    )
    if funding_reliability_policy is not None:
        apply_funding_reliability_to_readiness(
            objective_readiness, completed, reliability_evaluations
        )
    participation_suitability = []
    if participation_measurement_policy is not None:
        evaluations_by_run = {
            item["run_id"]: item for item in objective_evaluations
        }
        participation_suitability = [
            evaluate_participation_measurement_suitability(
                evaluations_by_run.get(row["run_id"]),
                Path(row["output_root"]) / "docs" / row["run_id"],
                participation_measurement_policy,
            )
            for row in completed
        ]
        apply_participation_suitability_to_readiness(
            objective_readiness, completed, participation_suitability
        )
    result = {
        "generated_utc": utc_now(),
        "total_runs": len(rows),
        "status_counts": by_status,
        "final_run_failure_rate": (
            by_status.get("failed", 0) / attempted_runs if attempted_runs else None
        ),
        "attempt_status_counts": attempt_status,
        "scheduler_runs": [dict(item) for item in schedulers],
        "attempt_scheduler_provenance": [
            dict(item) for item in attempt_schedulers
        ],
        "attempt_failure_rate": (
            attempt_status.get("failed", 0) / len(finished_attempts) if finished_attempts else None
        ),
        "attempt_wall_seconds": numeric_summary(
            attempt["wall_seconds"] for attempt in finished_attempts
            if attempt["wall_seconds"] is not None
        ),
        "completed_run_wall_seconds": numeric_summary(row["wall_seconds"] for row in completed),
        "activity_distributions": {
            field: numeric_summary(item[field] for item in activity) for field in fields
        },
        "completed_runs": activity,
        "funding_application_diagnostics": pipeline_diagnostics,
        "funding_application_reliability": reliability_evaluations,
        "funding_reliability_policy": (
            dict(funding_reliability_policy)
            if funding_reliability_policy is not None else None
        ),
        "participation_measurement_suitability": participation_suitability,
        "participation_measurement_policy": (
            dict(participation_measurement_policy)
            if participation_measurement_policy is not None else None
        ),
        "funding_application_distributions": {
            field: numeric_summary(item[field] for item in pipeline_diagnostics)
            for field in (
                "targets", "validated", "submitted", "declined_by_agent", "dropped", "evaluated",
                "decided", "funded", "allocations_recorded", "allocations_applied",
                "generation_attempts", "semantic_invalid_attempts",
                "sanitized_reference_attempts", "request_error_attempts",
            )
        },
        "objective_evaluations": objective_evaluations,
        "design_objective_readiness": objective_readiness,
        "report_errors": report_errors,
        "note": (
            "Activity and funding-pipeline fields are diagnostics. Only the versioned "
            "objective evaluations are governed by the Metric Constitution."
        ),
    }
    return result


def _context(study_path: Path):
    study, space, baseline = load_study(study_path)
    revision = study_revision(study, space)
    root = execution_root(study, revision)
    return study, space, baseline, revision, root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan")
    plan.add_argument("--fidelity", default="smoke")
    plan.add_argument("--seed-role", choices=["exploration", "selection", "confirmation"], default="exploration")
    plan.add_argument("--sampler", choices=["random", "sobol"])
    plan.add_argument("--count", type=int)
    run = commands.add_parser("run")
    run.add_argument("--limit", type=int)
    run.add_argument("--run-id", help="Execute one specific planned or retryable run")
    run.add_argument(
        "--workers",
        type=int,
        default=1,
        help=(
            "Maximum concurrent run subprocesses sharing one Ollama endpoint. "
            "Values above 1 require a warm shared RAG cache."
        ),
    )
    commands.add_parser("status")
    commands.add_parser("report")
    args = parser.parse_args(argv)
    study, space, baseline, revision, root = _context(args.study)
    if args.command == "plan":
        result = plan_study(
            study, space, baseline, fidelity=args.fidelity, seed_role=args.seed_role,
            sampler_kind=args.sampler, count=args.count,
        )
    else:
        registry_path = root / "registry.sqlite3"
        if not registry_path.exists():
            raise FileNotFoundError("Plan the study before using the registry")
        registry = RunRegistry(registry_path)
        try:
            if args.command == "run":
                result = execute_pending(
                    registry,
                    limit=args.limit,
                    selected_run_id=args.run_id,
                    workers=args.workers,
                    execution=study["execution"],
                )
            elif args.command == "status":
                rows = registry.rows()
                result = {
                    "study_revision": revision,
                    "root": str(root),
                    "runs": [dict(r) for r in rows],
                    "schedulers": [
                        dict(item) for item in registry.scheduler_rows()
                    ],
                    "attempt_schedulers": [
                        dict(item) for item in registry.attempt_scheduler_rows()
                    ],
                }
            else:
                constitution = load_metric_constitution(
                    _resolve_repo_path(study["metric_constitution"])
                )
                result = build_report(
                    registry,
                    constitution,
                    study.get("funding_reliability_policy"),
                    study.get("participation_measurement_policy"),
                )
                report_path = root / "registry-report.json"
                report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
                result["report_path"] = str(report_path)
        finally:
            registry.close()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

