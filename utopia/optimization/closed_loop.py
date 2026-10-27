"""Persistent result-dependent black-box optimization campaigns.

The controller keeps optimization loss, technical execution validity, held-out
evaluation, and optional promotion policy as separate concepts.  It persists an
optimizer suggestion before registering any simulator jobs, so a process crash
cannot silently lose the ask/tell state that generated those jobs.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import subprocess
from typing import Any, Mapping, Sequence

from utopia.optimization.blackbox import (
    AdaptiveRandomSearch,
    LegacySystemSpecSpace,
    Observation,
    Suggestion,
)
from utopia.optimization.design_space import validate_candidate
from utopia.optimization.harness import (
    ROOT,
    RunRegistry,
    build_command,
    build_report,
    canonical_json,
    design_id,
    digest,
    execute_pending,
    load_study,
    run_id,
    utc_now,
)
from utopia.optimization.loss import evaluate_loss, load_loss_spec, loss_spec_sha256
from utopia.optimization.metric_constitution import load_metric_constitution
from utopia.system import SystemSpec, validate_system_spec


CAMPAIGN_SCHEMA = "scienceutopia.closed-loop-campaign.v1"
STATE_SCHEMA = "scienceutopia.closed-loop-state.v1"
SNAPSHOT_SCHEMA = "scienceutopia.closed-loop-snapshot.v1"


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _read_object(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _source_provenance() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return {
        "commit": commit,
        "tree_dirty": bool(status),
        "dirty_paths": status,
    }


def validate_campaign_spec(spec: Mapping[str, Any]) -> None:
    errors: list[str] = []
    if spec.get("schema") != CAMPAIGN_SCHEMA:
        errors.append(f"schema must be {CAMPAIGN_SCHEMA!r}")
    for name in ("id", "version", "status", "study_template", "loss_spec", "fidelity"):
        if not isinstance(spec.get(name), str) or not spec[name]:
            errors.append(f"{name} must be a non-empty string")

    seed_sets = spec.get("seed_sets")
    if not isinstance(seed_sets, dict):
        errors.append("seed_sets must be an object")
    else:
        parsed: dict[str, list[int]] = {}
        for role in ("optimization", "held_out_evaluation"):
            seeds = seed_sets.get(role)
            if (
                not isinstance(seeds, list)
                or not seeds
                or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds)
                or len(set(seeds)) != len(seeds)
            ):
                errors.append(f"seed_sets.{role} must contain unique integers")
            else:
                parsed[role] = seeds
        if set(parsed.get("optimization", [])) & set(
            parsed.get("held_out_evaluation", [])
        ):
            errors.append("optimization and held-out seed sets must be disjoint")

    optimizer = spec.get("optimizer")
    if not isinstance(optimizer, dict):
        errors.append("optimizer must be an object")
    else:
        if optimizer.get("kind") != "adaptive_random_search":
            errors.append("optimizer.kind must be 'adaptive_random_search'")
        if isinstance(optimizer.get("seed"), bool) or not isinstance(
            optimizer.get("seed"), int
        ):
            errors.append("optimizer.seed must be an integer")
        initial = optimizer.get("initial_random")
        if isinstance(initial, bool) or not isinstance(initial, int) or initial < 1:
            errors.append("optimizer.initial_random must be positive")
        scale = optimizer.get("mutation_scale")
        if (
            isinstance(scale, bool)
            or not isinstance(scale, (int, float))
            or not math.isfinite(scale)
            or not 0 < scale <= 1
        ):
            errors.append("optimizer.mutation_scale must be in (0, 1]")

    budget = spec.get("budget")
    if not isinstance(budget, dict):
        errors.append("budget must be an object")
    else:
        for name in ("max_suggestions", "initial_batch", "adaptive_batch"):
            value = budget.get(name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                errors.append(f"budget.{name} must be positive")
        if (
            isinstance(optimizer, dict)
            and isinstance(optimizer.get("initial_random"), int)
            and isinstance(budget.get("initial_batch"), int)
            and budget["initial_batch"] != optimizer["initial_random"]
        ):
            errors.append(
                "budget.initial_batch must equal optimizer.initial_random for the "
                "synchronous first campaign"
            )
        if (
            isinstance(budget.get("max_suggestions"), int)
            and isinstance(budget.get("initial_batch"), int)
            and budget["max_suggestions"] < budget["initial_batch"]
        ):
            errors.append("budget.max_suggestions cannot be smaller than initial_batch")

    execution = spec.get("execution")
    if not isinstance(execution, dict):
        errors.append("execution must be an object")
    else:
        workers = execution.get("workers")
        if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
            errors.append("execution.workers must be positive")
        if not isinstance(execution.get("output_root"), str) or not execution["output_root"]:
            errors.append("execution.output_root must be a non-empty string")
        if not isinstance(execution.get("require_clean_worktree"), bool):
            errors.append("execution.require_clean_worktree must be boolean")
    if errors:
        raise ValueError("Invalid campaign specification: " + "; ".join(errors))


@dataclass(frozen=True)
class CampaignPaths:
    root: Path
    state: Path
    snapshot: Path
    registry: Path
    reports: Path
    runs: Path


class ClosedLoopCampaign:
    """One commit-pinnable, resumable synchronous ask/run/observe/tell campaign."""

    def __init__(self, campaign_path: str | Path):
        self.campaign_path = Path(campaign_path).resolve()
        self.spec = _read_object(self.campaign_path)
        validate_campaign_spec(self.spec)
        self.study, self.space, self.baseline = load_study(
            _repo_path(self.spec["study_template"])
        )
        self.loss_spec = load_loss_spec(_repo_path(self.spec["loss_spec"]))
        if self.loss_spec["optimization_seed_role"] != "optimization":
            raise ValueError(
                "LossSpec optimization_seed_role must be 'optimization' for a "
                "closed-loop campaign"
            )
        if self.spec["fidelity"] not in self.space["fidelities"]:
            raise ValueError(f"unknown campaign fidelity {self.spec['fidelity']!r}")
        if (
            len(self.spec["seed_sets"]["optimization"])
            < self.loss_spec["across_seeds"]["minimum_valid_runs"]
        ):
            raise ValueError(
                "optimization seed set is smaller than LossSpec minimum_valid_runs"
            )
        self.constitution = load_metric_constitution(
            _repo_path(self.study["metric_constitution"])
        )
        self.source = _source_provenance()
        self.revision = digest(
            {
                "campaign": self.spec,
                "study": self.study,
                "space": self.space,
                "loss_spec": self.loss_spec,
                "source_commit": self.source["commit"],
            },
            length=12,
        )
        output_root = _repo_path(self.spec["execution"]["output_root"])
        root = output_root / self.spec["id"] / self.revision
        self.paths = CampaignPaths(
            root=root,
            state=root / "campaign-state.json",
            snapshot=root / "campaign-snapshot.json",
            registry=root / "runs.sqlite3",
            reports=root / "reports",
            runs=root / "runs",
        )
        self.search_space = LegacySystemSpecSpace(self.space)

    def _new_optimizer(self) -> AdaptiveRandomSearch:
        config = self.spec["optimizer"]
        return AdaptiveRandomSearch(
            self.search_space,
            seed=config["seed"],
            initial_random=config["initial_random"],
            mutation_scale=config["mutation_scale"],
        )

    def _load_state(self) -> dict[str, Any]:
        if not self.paths.state.exists():
            raise FileNotFoundError(
                f"campaign is not initialized: {self.paths.state}"
            )
        state = _read_object(self.paths.state)
        if state.get("schema") != STATE_SCHEMA or state.get("revision") != self.revision:
            raise ValueError("campaign state schema or revision does not match")
        return state

    def _save_state(self, state: dict[str, Any]) -> None:
        state["updated_utc"] = utc_now()
        _atomic_write_json(self.paths.state, state)

    def initialize(self) -> dict[str, Any]:
        """Create immutable inputs and initial optimizer state, idempotently."""
        if (
            self.spec["execution"]["require_clean_worktree"]
            and self.source["tree_dirty"]
        ):
            raise RuntimeError(
                "campaign requires a clean worktree; dirty paths: "
                + ", ".join(self.source["dirty_paths"])
            )
        self.paths.root.mkdir(parents=True, exist_ok=True)
        if self.paths.state.exists():
            return self.status()
        snapshot_inputs = {
            "schema": SNAPSHOT_SCHEMA,
            "campaign_path": str(self.campaign_path),
            "revision": self.revision,
            "campaign": self.spec,
            "study_template": self.study,
            "design_space": self.space,
            "loss_spec": self.loss_spec,
            "loss_spec_sha256": loss_spec_sha256(self.loss_spec),
            "source": self.source,
        }
        if self.paths.snapshot.exists():
            existing = _read_object(self.paths.snapshot)
            existing_inputs = dict(existing)
            existing_inputs.pop("created_utc", None)
            if canonical_json(existing_inputs) != canonical_json(snapshot_inputs):
                raise ValueError("existing campaign snapshot does not match inputs")
        else:
            snapshot = {**snapshot_inputs, "created_utc": utc_now()}
            _atomic_write_json(self.paths.snapshot, snapshot)
        registry = RunRegistry(self.paths.registry)
        registry.close()
        now = utc_now()
        state = {
            "schema": STATE_SCHEMA,
            "campaign_id": self.spec["id"],
            "revision": self.revision,
            "created_utc": now,
            "updated_utc": now,
            "optimizer_state": self._new_optimizer().state_dict(),
            "suggestions": [],
        }
        self._save_state(state)
        return self.status()

    def _optimizer(self, state: Mapping[str, Any]) -> AdaptiveRandomSearch:
        return AdaptiveRandomSearch.from_state(
            self.search_space, state["optimizer_state"]
        )

    @staticmethod
    def _source_candidate(suggestion: Suggestion) -> dict[str, Any]:
        spec = SystemSpec.from_dict(suggestion.candidate)
        validate_system_spec(spec).require_valid()
        source = spec.metadata.get("source_candidate")
        if not isinstance(source, dict):
            raise ValueError("suggested SystemSpec has no source_candidate")
        return json.loads(canonical_json(source))

    def _suggestion_record(self, suggestion: Suggestion) -> dict[str, Any]:
        source = self._source_candidate(suggestion)
        validate_candidate(self.space, source)
        spec = SystemSpec.from_dict(suggestion.candidate)
        run_ids = [
            run_id(
                self.spec["id"],
                self.revision,
                source,
                self.spec["fidelity"],
                "optimization",
                seed,
            )
            for seed in self.spec["seed_sets"]["optimization"]
        ]
        return {
            "suggestion": suggestion.to_dict(),
            "source_candidate": source,
            "design_id": design_id(source),
            "system_fingerprint": spec.fingerprint,
            "run_ids": run_ids,
            "status": "pending_plan",
            "created_utc": utc_now(),
            "observed_utc": None,
            "observation": None,
            "loss_report": None,
        }

    def _plan_pending(self, state: dict[str, Any]) -> int:
        registry = RunRegistry(self.paths.registry)
        planned = 0
        try:
            for record in state["suggestions"]:
                if record["status"] != "pending_plan":
                    continue
                source = record["source_candidate"]
                for seed, planned_run_id in zip(
                    self.spec["seed_sets"]["optimization"], record["run_ids"]
                ):
                    command = build_command(
                        self.study,
                        self.space,
                        source,
                        run=planned_run_id,
                        fidelity=self.spec["fidelity"],
                        seed=seed,
                        output_root=self.paths.runs,
                    )
                    added = registry.add({
                        "run_id": planned_run_id,
                        "study_id": self.spec["id"],
                        "study_revision": self.revision,
                        "design_id": record["design_id"],
                        "design_json": canonical_json(source),
                        "sampler": "adaptive_random_search",
                        "fidelity": self.spec["fidelity"],
                        "seed_role": "optimization",
                        "seed": seed,
                        "max_attempts": self.study["execution"]["max_attempts"],
                        "command_json": canonical_json(command),
                        "output_root": str(self.paths.runs),
                        "created_utc": record["created_utc"],
                    })
                    planned += int(added)
                record["status"] = "planned"
            self._save_state(state)
        finally:
            registry.close()
        return planned

    def suggest(self, count: int | None = None) -> list[dict[str, Any]]:
        """Persist new asks, then idempotently register their seed-replicated runs."""
        state = self._load_state()
        self._plan_pending(state)
        optimizer = self._optimizer(state)
        total = len(state["suggestions"])
        remaining = self.spec["budget"]["max_suggestions"] - total
        if remaining <= 0:
            return []
        unresolved = [
            record for record in state["suggestions"]
            if record["status"] not in {"observed_complete", "observed_invalid"}
        ]
        if unresolved and total >= self.spec["optimizer"]["initial_random"]:
            raise RuntimeError(
                "resolve pending suggestions before asking for an adaptive candidate"
            )
        if count is None:
            count = (
                self.spec["budget"]["initial_batch"]
                if total == 0
                else self.spec["budget"]["adaptive_batch"]
            )
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError("suggestion count must be positive")
        count = min(count, remaining)
        initial_limit = self.spec["optimizer"]["initial_random"]
        if total < initial_limit and total + count > initial_limit:
            raise ValueError("one ask batch cannot cross the initial/adaptive boundary")
        suggestions = optimizer.ask(count)
        records = [self._suggestion_record(item) for item in suggestions]
        state["suggestions"].extend(records)
        state["optimizer_state"] = optimizer.state_dict()
        # This is the crash-safety boundary: asks exist durably before jobs do.
        self._save_state(state)
        self._plan_pending(state)
        return records

    def execute(self, *, limit: int | None = None, workers: int | None = None) -> dict[str, int]:
        state = self._load_state()
        self._plan_pending(state)
        registry = RunRegistry(self.paths.registry)
        try:
            return execute_pending(
                registry,
                limit=limit,
                workers=(
                    workers
                    if workers is not None
                    else self.spec["execution"]["workers"]
                ),
                execution=self.study["execution"],
            )
        finally:
            registry.close()

    @staticmethod
    def _terminal(row: Mapping[str, Any]) -> bool:
        return row["status"] == "complete" or (
            row["status"] == "failed" and row["attempt"] >= row["max_attempts"]
        )

    def observe_ready(self) -> list[dict[str, Any]]:
        """Turn terminal seed groups into loss observations and call ``tell``."""
        state = self._load_state()
        self._plan_pending(state)
        registry = RunRegistry(self.paths.registry)
        try:
            rows = {row["run_id"]: row for row in registry.rows()}
            report = build_report(registry, self.constitution)
        finally:
            registry.close()
        self.paths.reports.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(self.paths.reports / "registry-report.json", report)
        evaluations = {
            item["run_id"]: item for item in report.get("objective_evaluations", [])
        }
        optimizer = self._optimizer(state)
        observations: list[Observation] = []
        records: list[dict[str, Any]] = []
        for record in sorted(
            state["suggestions"],
            key=lambda item: item["suggestion"]["proposal_index"],
        ):
            if record["status"] != "planned":
                continue
            run_rows = [rows.get(run) for run in record["run_ids"]]
            if any(row is None for row in run_rows) or not all(
                self._terminal(row) for row in run_rows if row is not None
            ):
                continue
            selected = [
                evaluations[run] for run in record["run_ids"] if run in evaluations
            ]
            loss_result = evaluate_loss(self.loss_spec, selected)
            loss_path = self.paths.reports / (
                record["suggestion"]["suggestion_id"] + ".loss.json"
            )
            _atomic_write_json(loss_path, loss_result)
            status = "complete" if loss_result["status"] == "complete" else "invalid"
            observation_id = "o" + digest({
                "suggestion_id": record["suggestion"]["suggestion_id"],
                "loss_result": loss_result,
            }, length=16)
            observation = Observation(
                observation_id=observation_id,
                suggestion_id=record["suggestion"]["suggestion_id"],
                candidate=record["suggestion"]["candidate"],
                status=status,
                loss=loss_result["loss"] if status == "complete" else None,
                metadata={
                    "design_id": record["design_id"],
                    "run_ids": record["run_ids"],
                    "loss_report": str(loss_path),
                    "loss_spec_sha256": loss_spec_sha256(self.loss_spec),
                },
            )
            observations.append(observation)
            records.append(record)
        if observations:
            optimizer.tell(observations)
            for record, observation in zip(records, observations):
                record["status"] = (
                    "observed_complete"
                    if observation.status == "complete"
                    else "observed_invalid"
                )
                record["observed_utc"] = utc_now()
                record["observation"] = observation.to_dict()
                record["loss_report"] = observation.metadata["loss_report"]
            state["optimizer_state"] = optimizer.state_dict()
            self._save_state(state)
        return [item.to_dict() for item in observations]

    def status(self) -> dict[str, Any]:
        state = self._load_state()
        registry = RunRegistry(self.paths.registry)
        try:
            rows = registry.rows()
        finally:
            registry.close()
        suggestion_counts: dict[str, int] = {}
        for record in state["suggestions"]:
            suggestion_counts[record["status"]] = (
                suggestion_counts.get(record["status"], 0) + 1
            )
        run_counts: dict[str, int] = {}
        for row in rows:
            run_counts[row["status"]] = run_counts.get(row["status"], 0) + 1
        complete = [
            record["observation"]
            for record in state["suggestions"]
            if record["status"] == "observed_complete"
        ]
        incumbent = min(
            complete,
            key=lambda item: (item["loss"], item["observation_id"]),
            default=None,
        )
        return {
            "schema": "scienceutopia.closed-loop-status.v1",
            "campaign_id": self.spec["id"],
            "revision": self.revision,
            "source_commit": self.source["commit"],
            "root": str(self.paths.root),
            "suggestions": suggestion_counts,
            "runs": run_counts,
            "budget": {
                "used": len(state["suggestions"]),
                "maximum": self.spec["budget"]["max_suggestions"],
            },
            "incumbent": incumbent,
            "held_out_evaluation_seeds_consumed": False,
        }


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True, help="campaign JSON specification")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init")
    suggest_parser = subparsers.add_parser("suggest")
    suggest_parser.add_argument("--count", type=int)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--limit", type=int)
    run_parser.add_argument("--workers", type=int)
    subparsers.add_parser("observe")
    subparsers.add_parser("status")
    args = parser.parse_args(argv)
    campaign = ClosedLoopCampaign(args.campaign)
    if args.command == "init":
        campaign.initialize()
        result = campaign.status()
    elif args.command == "suggest":
        result = campaign.suggest(args.count)
    elif args.command == "run":
        result = campaign.execute(limit=args.limit, workers=args.workers)
    elif args.command == "observe":
        result = campaign.observe_ready()
    else:
        result = campaign.status()
    _print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
