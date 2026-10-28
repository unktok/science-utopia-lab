"""Orchestrate loss-conditioned campaigns and their sealed cross-evaluation.

The study-level controller enforces the experimental ordering that one
``ClosedLoopCampaign`` cannot enforce on its own:

1. optimize every arm on the common development split;
2. freeze exactly one winner per arm;
3. only then register the common held-out runs; and
4. evaluate every frozen winner under every declared loss and metric.

It never chooses a winner across objectives.  The output is a cross-evaluation
matrix for interpretation under the manifest's ``report_only`` policy.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator

from utopia.optimization.closed_loop import (
    ClosedLoopCampaign,
    _atomic_write_json,
    validate_campaign_spec,
)
from utopia.optimization.harness import (
    ROOT,
    RunRegistry,
    build_command,
    build_report,
    canonical_json,
    design_id,
    digest,
    execute_pending,
    run_id,
    utc_now,
)
from utopia.optimization.loss import evaluate_loss, load_loss_spec, loss_spec_sha256
from utopia.optimization.held_out_evaluator import (
    EVALUATOR_ID as HELD_OUT_EVALUATOR_ID,
    EVALUATOR_VERSION as HELD_OUT_EVALUATOR_VERSION,
    evaluate_common_suite,
)
from utopia.optimization.metric_conditioned_analysis import build_analyses


STUDY_SCHEMA = "scienceutopia.metric-conditioned-optimization-study.v1"
FREEZE_SCHEMA = "scienceutopia.metric-conditioned-winner-freeze.v1"
EVALUATION_SNAPSHOT_SCHEMA = (
    "scienceutopia.metric-conditioned-cross-evaluation-snapshot.v1"
)
REPORT_SCHEMA = "scienceutopia.metric-conditioned-cross-evaluation-report.v1"


def _repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def select_frozen_winner(records: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Return the lowest-loss valid record, breaking exact ties by proposal order."""
    complete = [
        record
        for record in records
        if record.get("status") == "observed_complete"
        and isinstance(record.get("observation"), Mapping)
        and isinstance(record["observation"].get("loss"), (int, float))
        and not isinstance(record["observation"].get("loss"), bool)
        and math.isfinite(float(record["observation"]["loss"]))
    ]
    if not complete:
        raise ValueError("campaign has no technically valid completed observation")
    return min(
        complete,
        key=lambda record: (
            float(record["observation"]["loss"]),
            int(record["suggestion"]["proposal_index"]),
        ),
    )


class MetricConditionedStudy:
    """Study-level seed firewall, winner seal, and held-out evaluator."""

    def __init__(self, manifest_path: str | Path):
        self.manifest_path = Path(manifest_path).resolve()
        self.manifest = _read_object(self.manifest_path)
        schema = _read_object(
            ROOT / "research/specs/metric-conditioned-optimization-study-v1.schema.json"
        )
        Draft202012Validator(schema).validate(self.manifest)
        if self.manifest.get("schema") != STUDY_SCHEMA:
            raise ValueError(f"unsupported study schema {self.manifest.get('schema')!r}")

        self.campaigns = [
            ClosedLoopCampaign(_repo_path(path))
            for path in self.manifest["campaigns"]
        ]
        if not self.campaigns:
            raise ValueError("study requires at least one campaign")
        self.losses = [campaign.loss_spec for campaign in self.campaigns]
        self.held_out_suite = _read_object(
            _repo_path(self.manifest["held_out_evaluator"]["spec"])
        )
        self._validate_contract()

        output_root = _repo_path(self.campaigns[0].spec["execution"]["output_root"])
        self.revision = digest(
            {
                "manifest": self.manifest,
                "campaign_revisions": [campaign.revision for campaign in self.campaigns],
                "held_out_metric_suite": self.held_out_suite,
            },
            length=12,
        )
        self.root = output_root / self.manifest["id"] / self.revision
        self.freeze_path = self.root / "winner-freeze.json"
        self.evaluation_root = self.root / "held-out-evaluation"
        self.evaluation_snapshot_path = self.evaluation_root / "snapshot.json"
        self.evaluation_registry_path = self.evaluation_root / "runs.sqlite3"
        self.evaluation_report_path = self.evaluation_root / "cross-evaluation.json"

    def _validate_contract(self) -> None:
        optimization = set(self.manifest["common_optimization_seeds"])
        held_out = set(self.manifest["common_held_out_evaluation_seeds"])
        forbidden = set(self.manifest["forbidden_legacy_held_out_seeds"])
        if optimization & held_out or forbidden & (optimization | held_out):
            raise ValueError("optimization, held-out, and forbidden seeds must be disjoint")

        reference = self.campaigns[0].spec
        parity_fields = (
            "study_template",
            "fidelity",
            "seed_sets",
            "optimizer",
            "budget",
            "execution",
        )
        for campaign in self.campaigns:
            validate_campaign_spec(campaign.spec)
            if set(campaign.spec["seed_sets"]["optimization"]) != optimization:
                raise ValueError(f"{campaign.spec['id']} optimization seeds differ")
            if set(campaign.spec["seed_sets"]["held_out_evaluation"]) != held_out:
                raise ValueError(f"{campaign.spec['id']} held-out seeds differ")
            for field in parity_fields:
                if canonical_json(campaign.spec[field]) != canonical_json(reference[field]):
                    raise ValueError(
                        f"campaigns differ outside LossSpec/identity at field {field!r}"
                    )
        if len({loss["id"] for loss in self.losses}) != len(self.losses):
            raise ValueError("each arm must use a distinct LossSpec")
        evaluator = self.manifest["held_out_evaluator"]
        if (
            evaluator["id"] != HELD_OUT_EVALUATOR_ID
            or evaluator["version"] != HELD_OUT_EVALUATOR_VERSION
        ):
            raise ValueError("held-out evaluator manifest does not match implementation")
        if self.held_out_suite.get("evaluator") != {
            "id": HELD_OUT_EVALUATOR_ID,
            "version": HELD_OUT_EVALUATOR_VERSION,
        }:
            raise ValueError("held-out metric suite does not match evaluator version")
        native_ids = [item.get("id") for item in self.held_out_suite.get("metrics", [])]
        declared_ids = [item.get("id") for item in self.manifest["held_out_metric_suite"]]
        if not native_ids or len(native_ids) != len(set(native_ids)):
            raise ValueError("held-out native metric ids must be present and unique")
        if not set(native_ids).issubset(declared_ids):
            raise ValueError("native held-out metrics are missing from the study manifest")

    def _arm_registries(self) -> list[Path]:
        output_root = _repo_path(self.campaigns[0].spec["execution"]["output_root"])
        paths: list[Path] = []
        for campaign in self.campaigns:
            arm_root = output_root / campaign.spec["id"]
            if arm_root.exists():
                paths.extend(sorted(arm_root.glob("*/runs.sqlite3")))
        return paths

    def audit(self) -> dict[str, Any]:
        """Audit every known study registry without consuming any seed."""
        optimization = set(self.manifest["common_optimization_seeds"])
        held_out = set(self.manifest["common_held_out_evaluation_seeds"])
        forbidden = set(self.manifest["forbidden_legacy_held_out_seeds"])
        violations: list[str] = []
        inspected: list[dict[str, Any]] = []
        for registry_path in self._arm_registries():
            registry = RunRegistry(registry_path)
            try:
                rows = registry.rows()
            finally:
                registry.close()
            seeds = {int(row["seed"]) for row in rows}
            bad = seeds & (held_out | forbidden)
            wrong_role = [
                row["run_id"]
                for row in rows
                if row["seed_role"] != "optimization" or row["seed"] not in optimization
            ]
            if bad:
                violations.append(f"{registry_path}: protected seeds present {sorted(bad)}")
            if wrong_role:
                violations.append(
                    f"{registry_path}: non-optimization rows {wrong_role[:3]}"
                )
            inspected.append({"path": str(registry_path), "runs": len(rows)})

        if self.evaluation_registry_path.exists():
            if not self.freeze_path.exists():
                violations.append("held-out evaluation registry exists before winner freeze")
            registry = RunRegistry(self.evaluation_registry_path)
            try:
                evaluation_rows = registry.rows()
            finally:
                registry.close()
            wrong_evaluation = [
                row["run_id"]
                for row in evaluation_rows
                if row["seed_role"] != "held_out_evaluation"
                or row["seed"] not in held_out
                or row["seed"] in forbidden
            ]
            if wrong_evaluation:
                violations.append(
                    "held-out registry contains non-reserved rows "
                    f"{wrong_evaluation[:3]}"
                )
        result = {
            "study_id": self.manifest["id"],
            "revision": self.revision,
            "seed_sets_pairwise_disjoint": True,
            "registries": inspected,
            "winner_freeze_exists": self.freeze_path.exists(),
            "violations": violations,
            "passed": not violations,
        }
        if violations:
            raise RuntimeError("study audit failed: " + "; ".join(violations))
        return result

    def initialize(self) -> dict[str, Any]:
        self.audit()
        return {
            campaign.spec["id"]: campaign.initialize()
            for campaign in self.campaigns
        }

    def suggest_initial(self) -> dict[str, Any]:
        """Register equal initial asks in every arm and assert byte identity."""
        records = {
            campaign.spec["id"]: campaign.suggest()
            for campaign in self.campaigns
        }
        proposals = [
            [canonical_json(item["source_candidate"]) for item in arm]
            for arm in records.values()
        ]
        if any(proposal != proposals[0] for proposal in proposals[1:]):
            raise RuntimeError("initial proposals differ across LossSpec arms")
        return {
            "arms": records,
            "identical_initial_proposals": True,
            "proposal_count": len(proposals[0]),
        }

    def adopt_initial(self, canonical_arm: str | None = None) -> dict[str, Any]:
        """Adopt completed byte-identical initial trajectories into other arms."""
        by_id = {campaign.spec["id"]: campaign for campaign in self.campaigns}
        canonical = by_id.get(canonical_arm) if canonical_arm else self.campaigns[0]
        if canonical is None:
            raise ValueError(f"unknown canonical arm {canonical_arm!r}")
        initial_count = canonical.spec["optimizer"]["initial_random"]
        states = {campaign.spec["id"]: campaign._load_state() for campaign in self.campaigns}
        for campaign in self.campaigns:
            records = states[campaign.spec["id"]]["suggestions"]
            if len(records) != initial_count:
                raise RuntimeError(
                    "initial adoption requires exactly the initial proposal batch in every arm"
                )
        canonical_records = sorted(
            states[canonical.spec["id"]]["suggestions"],
            key=lambda item: item["suggestion"]["proposal_index"],
        )
        canonical_candidates = [
            canonical_json(record["source_candidate"]) for record in canonical_records
        ]
        results: dict[str, list[dict[str, Any]]] = {}
        for target in self.campaigns:
            if target is canonical:
                continue
            target_records = sorted(
                states[target.spec["id"]]["suggestions"],
                key=lambda item: item["suggestion"]["proposal_index"],
            )
            target_candidates = [
                canonical_json(record["source_candidate"])
                for record in target_records
            ]
            if target_candidates != canonical_candidates:
                raise RuntimeError("initial proposals are not byte-identical across arms")
            target_registry = RunRegistry(target.paths.registry)
            try:
                adopted: list[dict[str, Any]] = []
                for source_record, target_record in zip(canonical_records, target_records):
                    if len(source_record["run_ids"]) != len(target_record["run_ids"]):
                        raise RuntimeError("initial proposal seed replication differs across arms")
                    for source_run, target_run in zip(
                        source_record["run_ids"], target_record["run_ids"]
                    ):
                        adopted.append(target_registry.adopt_artifact(
                            target_run,
                            source_registry_path=canonical.paths.registry,
                            source_run=source_run,
                        ))
                results[target.spec["id"]] = adopted
            finally:
                target_registry.close()
        return {
            "canonical_arm": canonical.spec["id"],
            "targets": results,
            "logical_runs_adopted": sum(
                int(item["adopted"]) for items in results.values() for item in items
            ),
            "logical_runs_idempotent": sum(
                int(item["idempotent"]) for items in results.values() for item in items
            ),
        }

    def freeze_winners(self) -> dict[str, Any]:
        """Seal all arm winners; refuse partial campaigns or mutable overwrite."""
        self.audit()
        winners: list[dict[str, Any]] = []
        for campaign in self.campaigns:
            state = campaign._load_state()
            records = state["suggestions"]
            expected = campaign.spec["budget"]["max_suggestions"]
            if len(records) != expected:
                raise RuntimeError(
                    f"{campaign.spec['id']} used {len(records)}/{expected} suggestions"
                )
            unresolved = [
                record["suggestion"]["suggestion_id"]
                for record in records
                if record["status"] not in {"observed_complete", "observed_invalid"}
            ]
            if unresolved:
                raise RuntimeError(
                    f"{campaign.spec['id']} has unresolved suggestions {unresolved}"
                )
            winner = select_frozen_winner(records)
            winners.append({
                "campaign_id": campaign.spec["id"],
                "campaign_revision": campaign.revision,
                "loss_spec": {
                    "id": campaign.loss_spec["id"],
                    "version": campaign.loss_spec["version"],
                    "sha256": loss_spec_sha256(campaign.loss_spec),
                },
                "suggestion_id": winner["suggestion"]["suggestion_id"],
                "proposal_index": winner["suggestion"]["proposal_index"],
                "design_id": winner["design_id"],
                "system_fingerprint": winner["system_fingerprint"],
                "source_candidate": winner["source_candidate"],
                "optimization_observation": winner["observation"],
            })

        freeze = {
            "schema": FREEZE_SCHEMA,
            "study_id": self.manifest["id"],
            "study_revision": self.revision,
            "source_commit": self.campaigns[0].source["commit"],
            "frozen_utc": utc_now(),
            "decision_policy": "report_only",
            "optimization_seeds": self.manifest["common_optimization_seeds"],
            "held_out_seeds_unconsumed_at_freeze": self.manifest[
                "common_held_out_evaluation_seeds"
            ],
            "winners": winners,
        }
        immutable = dict(freeze)
        immutable.pop("frozen_utc")
        freeze["freeze_sha256"] = digest(immutable, length=64)
        self.root.mkdir(parents=True, exist_ok=True)
        if self.freeze_path.exists():
            existing = _read_object(self.freeze_path)
            if existing.get("freeze_sha256") != freeze["freeze_sha256"]:
                raise RuntimeError("winner freeze already exists with different contents")
            return existing
        _atomic_write_json(self.freeze_path, freeze)
        return freeze

    def _validated_freeze(self) -> dict[str, Any]:
        if not self.freeze_path.exists():
            raise RuntimeError("freeze all arm winners before using held-out evidence")
        freeze = _read_object(self.freeze_path)
        expected = freeze.get("freeze_sha256")
        immutable = dict(freeze)
        immutable.pop("freeze_sha256", None)
        immutable.pop("frozen_utc", None)
        if not isinstance(expected, str) or digest(immutable, length=64) != expected:
            raise RuntimeError("winner freeze hash does not match its contents")
        if freeze.get("study_revision") != self.revision:
            raise RuntimeError("winner freeze belongs to another study revision")
        if len(freeze.get("winners", [])) != len(self.campaigns):
            raise RuntimeError("winner freeze does not contain one winner per arm")
        return freeze

    def plan_evaluation(self) -> dict[str, Any]:
        """Register 3 x 5 held-out jobs, but only after the winner seal exists."""
        self.audit()
        freeze = self._validated_freeze()
        campaign = self.campaigns[0]
        seeds = self.manifest["common_held_out_evaluation_seeds"]
        run_records: list[dict[str, Any]] = []
        self.evaluation_root.mkdir(parents=True, exist_ok=True)
        registry = RunRegistry(self.evaluation_registry_path)
        added = 0
        try:
            for winner in freeze["winners"]:
                candidate = winner["source_candidate"]
                for seed in seeds:
                    identity = run_id(
                        f"{self.manifest['id']}-{winner['campaign_id']}",
                        self.revision,
                        candidate,
                        campaign.spec["fidelity"],
                        "held-out-evaluation",
                        seed,
                    )
                    command = build_command(
                        campaign.study,
                        campaign.space,
                        candidate,
                        run=identity,
                        fidelity=campaign.spec["fidelity"],
                        seed=seed,
                        output_root=self.evaluation_root / "runs",
                    )
                    added += int(registry.add({
                        "run_id": identity,
                        "study_id": self.manifest["id"],
                        "study_revision": self.revision,
                        "design_id": design_id(candidate),
                        "design_json": canonical_json(candidate),
                        "sampler": "frozen_loss_conditioned_winner",
                        "fidelity": campaign.spec["fidelity"],
                        "seed_role": "held_out_evaluation",
                        "seed": seed,
                        "max_attempts": campaign.study["execution"]["max_attempts"],
                        "command_json": canonical_json(command),
                        "output_root": str(self.evaluation_root / "runs"),
                        "created_utc": utc_now(),
                    }))
                    run_records.append({
                        "run_id": identity,
                        "campaign_id": winner["campaign_id"],
                        "loss_spec_id": winner["loss_spec"]["id"],
                        "design_id": design_id(candidate),
                        "seed": seed,
                    })
            total = len(registry.rows())
        finally:
            registry.close()
        snapshot = {
            "schema": EVALUATION_SNAPSHOT_SCHEMA,
            "study_id": self.manifest["id"],
            "study_revision": self.revision,
            "winner_freeze_sha256": freeze["freeze_sha256"],
            "held_out_seeds": seeds,
            "metric_suite": self.manifest["held_out_metric_suite"],
            "held_out_evaluator": self.manifest["held_out_evaluator"],
            "held_out_metric_suite_spec": self.held_out_suite,
            "held_out_metric_suite_sha256": digest(
                self.held_out_suite, length=64
            ),
            "runs": run_records,
        }
        if self.evaluation_snapshot_path.exists():
            if canonical_json(_read_object(self.evaluation_snapshot_path)) != canonical_json(snapshot):
                raise RuntimeError("held-out evaluation snapshot changed")
        else:
            _atomic_write_json(self.evaluation_snapshot_path, snapshot)
        expected_total = len(freeze["winners"]) * len(seeds)
        if total != expected_total:
            raise RuntimeError(
                f"held-out registry has {total} rows; expected exactly {expected_total}"
            )
        return {"added_runs": added, "total_runs": total, "root": str(self.evaluation_root)}

    def execute_evaluation(
        self, *, limit: int | None = None, workers: int | None = None
    ) -> dict[str, int]:
        if not self.evaluation_snapshot_path.exists():
            raise RuntimeError("plan held-out evaluation before execution")
        registry = RunRegistry(self.evaluation_registry_path)
        try:
            return execute_pending(
                registry,
                limit=limit,
                workers=workers or self.campaigns[0].spec["execution"]["workers"],
                execution=self.campaigns[0].study["execution"],
            )
        finally:
            registry.close()

    @staticmethod
    def _summary(values: list[float]) -> dict[str, Any]:
        return {
            "n": len(values),
            "mean": statistics.fmean(values) if values else None,
            "median": statistics.median(values) if values else None,
            "population_sd": statistics.pstdev(values) if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }

    @classmethod
    def _flatten_numeric(cls, value: Any, prefix: str = "") -> dict[str, float]:
        flattened: dict[str, float] = {}
        if isinstance(value, Mapping):
            for key, item in value.items():
                if key in {"status", "reason"}:
                    continue
                path = f"{prefix}.{key}" if prefix else str(key)
                flattened.update(cls._flatten_numeric(item, path))
        elif (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        ):
            flattened[prefix] = float(value)
        return flattened

    @classmethod
    def _structured_summary(cls, values: list[dict[str, Any]]) -> dict[str, Any]:
        by_path: dict[str, list[float]] = defaultdict(list)
        for value in values:
            for path, number in cls._flatten_numeric(value).items():
                by_path[path].append(number)
        return {path: cls._summary(numbers) for path, numbers in sorted(by_path.items())}

    def report_evaluation(self) -> dict[str, Any]:
        """Build the loss-by-winner matrix and common held-out metric profiles."""
        if not self.evaluation_snapshot_path.exists():
            raise RuntimeError("held-out evaluation is not planned")
        snapshot = _read_object(self.evaluation_snapshot_path)
        freeze = self._validated_freeze()
        if snapshot.get("winner_freeze_sha256") != freeze["freeze_sha256"]:
            raise RuntimeError("evaluation snapshot does not match the winner freeze")
        registry = RunRegistry(self.evaluation_registry_path)
        try:
            rows = [dict(row) for row in registry.rows()]
            expected_runs = {item["run_id"] for item in snapshot["runs"]}
            if {row["run_id"] for row in rows} != expected_runs:
                raise RuntimeError("held-out registry rows differ from the sealed snapshot")
            if any(
                row["status"] != "complete"
                and not (
                    row["status"] == "failed"
                    and row["attempt"] >= row["max_attempts"]
                )
                for row in rows
            ):
                raise RuntimeError("held-out runs are not all terminal")
            raw = build_report(registry, self.campaigns[0].constitution)
        finally:
            registry.close()

        run_meta = {item["run_id"]: item for item in snapshot["runs"]}
        row_by_run = {row["run_id"]: row for row in rows}
        evaluations = {
            item["run_id"]: item for item in raw["objective_evaluations"]
        }
        grouped_runs: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in snapshot["runs"]:
            grouped_runs[item["campaign_id"]].append(item)

        loss_matrix: dict[str, dict[str, Any]] = {}
        metric_profiles: dict[str, list[dict[str, Any]]] = {}
        common_run_evaluations: dict[str, dict[str, Any]] = {}
        for winner in freeze["winners"]:
            arm = winner["campaign_id"]
            arm_runs = sorted(grouped_runs.get(arm, []), key=lambda item: item["seed"])
            # Placeholders make terminal failures explicit rejected inputs in
            # every recomputed loss instead of silently changing sample size.
            arm_evaluations = [
                evaluations.get(item["run_id"], {"run_id": item["run_id"], "metrics": {}})
                for item in arm_runs
            ]
            loss_matrix[arm] = {}
            for loss in self.losses:
                result = evaluate_loss(loss, arm_evaluations)
                per_run = {item["run_id"]: item["loss"] for item in result["per_run"]}
                result["held_out_seed_values"] = [
                    {
                        "seed": item["seed"],
                        "run_id": item["run_id"],
                        "loss": per_run.get(item["run_id"]),
                        "missing_reason": (
                            None if item["run_id"] in per_run
                            else next(
                                (
                                    rejected["reason"]
                                    for rejected in result["rejected_runs"]
                                    if rejected["run_id"] == item["run_id"]
                                ),
                                "loss input unavailable",
                            )
                        ),
                    }
                    for item in arm_runs
                ]
                result["is_own_loss"] = loss["id"] == winner["loss_spec"]["id"]
                loss_matrix[arm][loss["id"]] = result

            for run_item, evaluation in zip(arm_runs, arm_evaluations):
                run = run_item["run_id"]
                row = row_by_run[run]
                if run in evaluations and row["status"] == "complete":
                    common_run_evaluations[run] = evaluate_common_suite(
                        run_id=run,
                        output_root=row["output_root"],
                        candidate=winner["source_candidate"],
                        objective_evaluation=evaluation,
                    )
            profiles: list[dict[str, Any]] = []
            for declared in self.manifest["held_out_metric_suite"]:
                values: list[dict[str, Any]] = []
                for run_item, evaluation in zip(arm_runs, arm_evaluations):
                    run = run_item["run_id"]
                    seed = run_item["seed"]
                    metric_id = declared["id"]
                    slice_id = declared.get("slice")
                    value: Any = None
                    reason: str | None = None
                    status = "unknown"
                    metric_version = None
                    details = None
                    common = common_run_evaluations.get(run)
                    if common is None:
                        reason = "run failed or common held-out evaluation was unavailable"
                    elif metric_id in common.get("metrics", {}):
                        measured = common["metrics"][metric_id]
                        status = measured.get("status", "unknown")
                        metric_version = measured.get("metric_version")
                        details = measured.get("details")
                        if slice_id is None:
                            if status in {"measured", "partial"}:
                                value = measured.get("value")
                                reason = measured.get("reason")
                            else:
                                reason = measured.get("reason", "metric is unavailable")
                        else:
                            sliced = measured.get("slice_results", {}).get(slice_id)
                            if isinstance(sliced, dict) and sliced.get("status") == "measured":
                                value = sliced.get("value")
                                status = "measured"
                            else:
                                status = "unknown"
                                reason = (sliced or {}).get(
                                    "reason", measured.get("slice_reason", "slice is unavailable")
                                )
                    else:
                        reason = "declared metric has no executable evaluator in v1"
                    values.append({
                        "seed": seed,
                        "status": status,
                        "metric_version": metric_version,
                        "value": value,
                        "missing_reason": reason,
                        "details": details,
                    })
                numeric = [
                    float(item["value"])
                    for item in values
                    if isinstance(item["value"], (int, float))
                    and not isinstance(item["value"], bool)
                    and math.isfinite(float(item["value"]))
                ]
                structured_values = [
                    item["value"] for item in values if isinstance(item["value"], dict)
                ]
                profiles.append({
                    **declared,
                    "seed_values": values,
                    "summary": self._summary(numeric),
                    "structured_summary": self._structured_summary(structured_values),
                    "complete": len(numeric) == len(values) and all(
                        item["status"] == "measured" for item in values
                    ) if not structured_values else (
                        len(structured_values) == len(values)
                        and all(item["status"] == "measured" for item in values)
                    ),
                })
            metric_profiles[arm] = profiles

        report = {
            "schema": REPORT_SCHEMA,
            "study_id": self.manifest["id"],
            "study_revision": self.revision,
            "winner_freeze_sha256": freeze["freeze_sha256"],
            "decision_policy": "report_only",
            "loss_by_frozen_winner": loss_matrix,
            "held_out_metric_profiles": metric_profiles,
            "common_run_evaluations": common_run_evaluations,
            "analyses": build_analyses(
                freeze=freeze,
                profiles=metric_profiles,
                losses=loss_matrix,
            ),
            "raw_registry_report": raw,
            "note": (
                "Rows are frozen LossSpec-conditioned systems. Columns remain "
                "separate measurements; no universal winner is selected."
            ),
        }
        _atomic_write_json(self.evaluation_report_path, report)
        return report

    def status(self) -> dict[str, Any]:
        arms: dict[str, Any] = {}
        for campaign in self.campaigns:
            arms[campaign.spec["id"]] = (
                campaign.status() if campaign.paths.state.exists() else {"initialized": False}
            )
        evaluation_runs: dict[str, int] = {}
        if self.evaluation_registry_path.exists():
            registry = RunRegistry(self.evaluation_registry_path)
            try:
                for row in registry.rows():
                    evaluation_runs[row["status"]] = evaluation_runs.get(row["status"], 0) + 1
            finally:
                registry.close()
        return {
            "study_id": self.manifest["id"],
            "revision": self.revision,
            "arms": arms,
            "winners_frozen": self.freeze_path.exists(),
            "evaluation_runs": evaluation_runs,
            "evaluation_report_exists": self.evaluation_report_path.exists(),
        }


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, allow_nan=False))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in (
        "audit", "init", "suggest-initial", "freeze", "plan-evaluation",
        "report-evaluation", "status",
    ):
        commands.add_parser(command)
    adopt = commands.add_parser("adopt-initial")
    adopt.add_argument("--canonical-arm")
    run = commands.add_parser("run-evaluation")
    run.add_argument("--limit", type=int)
    run.add_argument("--workers", type=int)
    args = parser.parse_args(argv)
    study = MetricConditionedStudy(args.study)
    if args.command == "audit":
        result = study.audit()
    elif args.command == "init":
        result = study.initialize()
    elif args.command == "suggest-initial":
        result = study.suggest_initial()
    elif args.command == "adopt-initial":
        result = study.adopt_initial(args.canonical_arm)
    elif args.command == "freeze":
        result = study.freeze_winners()
    elif args.command == "plan-evaluation":
        result = study.plan_evaluation()
    elif args.command == "run-evaluation":
        result = study.execute_evaluation(limit=args.limit, workers=args.workers)
    elif args.command == "report-evaluation":
        result = study.report_evaluation()
    else:
        result = study.status()
    _print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
