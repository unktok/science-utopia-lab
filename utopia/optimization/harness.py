"""Plan, execute, resume, and summarize seed-replicated institutional designs."""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import random
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
    if type(sampler.get("count")) is not int or sampler["count"] < 1:
        raise ValueError("sampler.count must be a positive integer")
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
    stage = {"smoke": "smoke", "screen": "pilot", "confirm": "confirmatory"}[fidelity]
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
        now = utc_now()
        reason = "Harness process ended before recording completion; retry may resume checkpoint"
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
        self.connection.commit()
        return len(interrupted)

    def start(self, run: str) -> sqlite3.Row:
        self.connection.execute(
            """UPDATE runs SET status='running', attempt=attempt+1, started_utc=?,
               finished_utc=NULL, returncode=NULL, error=NULL WHERE run_id=?""",
            (utc_now(), run),
        )
        row = self.rows("run_id=?", (run,))[0]
        self.connection.execute(
            """INSERT INTO attempts (run_id, attempt, status, started_utc)
               VALUES (?, ?, 'running', ?)""",
            (run, row["attempt"], row["started_utc"]),
        )
        self.connection.commit()
        return row

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
    sample_count = count or sampler["count"]
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


def execute_pending(
    registry: RunRegistry, *, limit: int | None = None, selected_run_id: str | None = None
) -> dict[str, int]:
    registry.recover_interrupted()
    if selected_run_id is None:
        runnable = registry.rows("status IN ('planned','failed') AND attempt < max_attempts")
    else:
        runnable = registry.rows(
            "run_id=? AND status IN ('planned','failed') AND attempt < max_attempts",
            (selected_run_id,),
        )
        if not runnable:
            raise ValueError(f"Run is missing, complete, active, or out of attempts: {selected_run_id}")
    if limit is not None:
        runnable = runnable[:limit]
    counts = {"complete": 0, "failed": 0}
    for pending in runnable:
        row = registry.start(pending["run_id"])
        command = json.loads(row["command_json"])
        log_dir = Path(row["output_root"]) / "registry-logs" / row["run_id"]
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"attempt-{row['attempt']}.log"
        started = time.monotonic()
        with log_path.open("w", encoding="utf-8") as log:
            log.write("COMMAND " + canonical_json(command) + "\n")
            log.flush()
            result = subprocess.run(
                command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, text=True
            )
        elapsed = time.monotonic() - started
        status, manifest_error = manifest_status(row)
        complete = result.returncode == 0 and status == "complete"
        final_status = "complete" if complete else "failed"
        error = None if complete else (
            manifest_error or f"process returncode={result.returncode}, manifest status={status}"
        )
        registry.finish(
            row["run_id"], status=final_status, returncode=result.returncode,
            wall_seconds=elapsed, error=error,
        )
        counts[final_status] += 1
    return counts


def numeric_summary(values: Iterable[float]) -> dict[str, float | int | None]:
    finite = [float(value) for value in values if math.isfinite(float(value))]
    if not finite:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {"n": len(finite), "mean": statistics.fmean(finite),
            "median": statistics.median(finite), "min": min(finite), "max": max(finite)}


def build_report(
    registry: RunRegistry, constitution: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    rows = registry.rows()
    attempts = registry.attempt_rows()
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
                "generation_attempts", "semantic_invalid_attempts", "request_error_attempts",
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
    result = {
        "generated_utc": utc_now(),
        "total_runs": len(rows),
        "status_counts": by_status,
        "final_run_failure_rate": (
            by_status.get("failed", 0) / attempted_runs if attempted_runs else None
        ),
        "attempt_status_counts": attempt_status,
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
        "funding_application_distributions": {
            field: numeric_summary(item[field] for item in pipeline_diagnostics)
            for field in (
                "targets", "validated", "submitted", "declined_by_agent", "dropped", "evaluated",
                "decided", "funded", "allocations_recorded", "allocations_applied",
                "generation_attempts", "semantic_invalid_attempts", "request_error_attempts",
            )
        },
        "objective_evaluations": objective_evaluations,
        "design_objective_readiness": (
            summarize_evaluations(objective_evaluations, completed, constitution)
            if constitution is not None else []
        ),
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
    plan.add_argument("--fidelity", choices=["smoke", "screen", "confirm"], default="smoke")
    plan.add_argument("--seed-role", choices=["exploration", "selection", "confirmation"], default="exploration")
    plan.add_argument("--sampler", choices=["random", "sobol"])
    plan.add_argument("--count", type=int)
    run = commands.add_parser("run")
    run.add_argument("--limit", type=int)
    run.add_argument("--run-id", help="Execute one specific planned or retryable run")
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
                    registry, limit=args.limit, selected_run_id=args.run_id
                )
            elif args.command == "status":
                rows = registry.rows()
                result = {"study_revision": revision, "root": str(root), "runs": [dict(r) for r in rows]}
            else:
                constitution = load_metric_constitution(
                    _resolve_repo_path(study["metric_constitution"])
                )
                result = build_report(registry, constitution)
                report_path = root / "registry-report.json"
                report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
                result["report_path"] = str(report_path)
        finally:
            registry.close()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

