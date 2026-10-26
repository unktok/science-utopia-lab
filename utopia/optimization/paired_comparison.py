"""Audit and summarize a seed-paired institutional comparison."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sqlite3
import statistics
from typing import Any, Iterable, Mapping


DEFAULT_SEEDS = (101, 103, 107, 109, 113)
DEFAULT_SEED_ROLE = "exploration"
BOOTSTRAP_SEED = 20261025
BOOTSTRAP_RESAMPLES = 10_000
ALLOWED_DESIGN_CHANGE = "funding_budget_slots_frac"

METRICS = {
    "active_researcher_fraction": (
        "active-researcher-fraction", None, "higher"
    ),
    "low_resource_active_fraction": (
        "active-researcher-fraction", "low-resource-researchers", "higher"
    ),
    "review_burden": (
        "review-burden-per-active-researcher", None, "lower"
    ),
    "low_resource_review_burden": (
        "review-burden-per-active-researcher", "low-resource-researchers", "lower"
    ),
    "topic_entropy": ("topic-entropy", None, "portfolio"),
}

MANIFEST_INVARIANTS = (
    "git_commit",
    "git_dirty_files",
    "source_files_sha256",
    "python",
    "package_versions",
    "model_id",
    "dataset_identity",
    "ordered_documents_sha256",
    "retrieval_embedding",
    "metric_embedding",
    "resolved_config",
)

PATH_OR_ID_ARGS = {
    "checkpoint_dir",
    "docs_dir",
    "experiment_id",
    "log_dir",
    "output_dir",
    "run_id",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _quantile(sorted_values: list[float], probability: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = position - lower
    return sorted_values[lower] + fraction * (sorted_values[upper] - sorted_values[lower])


def bootstrap_mean_interval(
    values: Iterable[float], *, seed: int = BOOTSTRAP_SEED,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> dict[str, Any]:
    """Return the preregistered descriptive percentile interval for a paired mean."""
    sample = [float(value) for value in values]
    if not sample:
        raise ValueError("bootstrap requires at least one paired delta")
    if resamples < 1:
        raise ValueError("resamples must be positive")
    rng = random.Random(seed)
    means = sorted(
        statistics.fmean(rng.choice(sample) for _ in sample)
        for _ in range(resamples)
    )
    return {
        "method": "paired-percentile-bootstrap",
        "seed": seed,
        "resamples": resamples,
        "confidence_level": 0.95,
        "lower": _quantile(means, 0.025),
        "upper": _quantile(means, 0.975),
        "interpretation": "descriptive",
    }


def summarize_deltas(values: Iterable[float]) -> dict[str, Any]:
    deltas = [float(value) for value in values]
    if not deltas:
        raise ValueError("paired summary requires at least one delta")
    return {
        "n": len(deltas),
        "mean": statistics.fmean(deltas),
        "median": statistics.median(deltas),
        "sample_sd": statistics.stdev(deltas) if len(deltas) > 1 else None,
        "min": min(deltas),
        "max": max(deltas),
        "positive": sum(value > 0 for value in deltas),
        "zero": sum(value == 0 for value in deltas),
        "negative": sum(value < 0 for value in deltas),
        "mean_interval": bootstrap_mean_interval(deltas),
    }


def _registry_rows(root: Path) -> tuple[dict[int, dict[str, Any]], dict[str, int]]:
    with sqlite3.connect(root / "registry.sqlite3") as connection:
        connection.row_factory = sqlite3.Row
        rows = {
            int(row["seed"]): dict(row)
            for row in connection.execute(
                "SELECT run_id, seed, status, fidelity, seed_role, design_id, "
                "design_json, wall_seconds FROM runs"
            )
        }
        failures = {
            row["run_id"]: int(row["n"])
            for row in connection.execute(
                "SELECT run_id, COUNT(*) AS n FROM attempts "
                "WHERE status = 'failed' GROUP BY run_id"
            )
        }
    return rows, failures


def _campaign(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    report = _read_json(root / "registry-report.json")
    snapshot = _read_json(root / "study-snapshot.json")
    rows, failures = _registry_rows(root)
    completed = {int(item["seed"]): item for item in report["completed_runs"]}
    seed_by_run = {item["run_id"]: seed for seed, item in completed.items()}
    evaluations = {
        seed_by_run[item["run_id"]]: item for item in report["objective_evaluations"]
    }
    reliability = {
        seed_by_run[item["run_id"]]: item
        for item in report["funding_application_reliability"]
    }
    return {
        "root": root,
        "report": report,
        "snapshot": snapshot,
        "rows": rows,
        "failures": failures,
        "completed": completed,
        "evaluations": evaluations,
        "reliability": reliability,
    }


def _manifest(campaign: Mapping[str, Any], seed: int) -> dict[str, Any]:
    run_id = campaign["rows"][seed]["run_id"]
    return _read_json(campaign["root"] / "docs" / run_id / "run_manifest.json")


def _normalized_args(manifest: Mapping[str, Any], allowed_change: str) -> dict[str, Any]:
    return {
        key: value for key, value in manifest["args"].items()
        if key not in PATH_OR_ID_ARGS and key != allowed_change
    }


def _metric_value(evaluation: Mapping[str, Any], metric_key: str) -> float:
    metric_id, slice_id, _ = METRICS[metric_key]
    metric = evaluation["metrics"][metric_id]
    if metric.get("status") != "measured":
        raise ValueError(f"{metric_id} is not measured")
    if slice_id is None:
        value = metric.get("value")
    else:
        slice_result = metric.get("slice_results", {}).get(slice_id, {})
        if slice_result.get("status") != "measured":
            raise ValueError(f"{metric_id}/{slice_id} is not measured")
        value = slice_result.get("value")
    if type(value) not in {int, float}:
        raise ValueError(f"{metric_id} has no numeric value")
    return float(value)


def _funding_and_resource_shadows(root: Path, run_id: str) -> dict[str, float | int]:
    checkpoint = root / "checkpoints" / run_id
    counts = {
        "funding_targets": 0,
        "funding_applications": 0,
        "funding_awards": 0,
        "funding_allocations_applied": 0,
    }
    for path in sorted(checkpoint.glob("funding_application_trace_year_*.summary.json")):
        summary = _read_json(path)["counts"]
        counts["funding_targets"] += int(summary["targets"])
        counts["funding_applications"] += int(summary["submitted"])
        counts["funding_awards"] += int(summary["funded"])
        counts["funding_allocations_applied"] += int(summary["allocations_applied"])
    grant_income = 0.0
    with (checkpoint / "resource_balances.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            grant_income += float(json.loads(line)["grant_income"])
    return {**counts, "grant_income": grant_income}


def _run_shadows(campaign: Mapping[str, Any], seed: int) -> dict[str, float | int]:
    run = campaign["completed"][seed]
    registry = campaign["rows"][seed]
    return {
        "final_total_resources": float(run["total_resources"]),
        "papers": int(run["papers"]),
        "reviews": int(run["reviews"]),
        "acceptances": int(run["accepted"]),
        "wall_seconds": float(registry["wall_seconds"]),
        "failed_attempts": campaign["failures"].get(run["run_id"], 0),
        **_funding_and_resource_shadows(campaign["root"], run["run_id"]),
    }


def _validate_campaign(
    campaign: Mapping[str, Any], seeds: tuple[int, ...], seed_role: str,
) -> None:
    report = campaign["report"]
    study_seeds = campaign["snapshot"].get("study", {}).get("seed_sets", {}).get(
        seed_role
    )
    if study_seeds != list(seeds):
        raise ValueError(f"study snapshot {seed_role} seeds do not match the paired bundle")
    if report.get("report_errors"):
        raise ValueError(f"campaign report has errors: {report['report_errors']}")
    if report.get("status_counts") != {"complete": len(seeds)}:
        raise ValueError("campaign does not contain exactly the required completed runs")
    for collection in ("rows", "completed", "evaluations", "reliability"):
        if set(campaign[collection]) != set(seeds):
            raise ValueError(f"campaign {collection} seeds do not match the paired bundle")
    for seed in seeds:
        row = campaign["rows"][seed]
        evaluation = campaign["evaluations"][seed]
        if row["status"] != "complete" or row["seed_role"] != seed_role:
            raise ValueError(f"seed {seed} is not a completed {seed_role} run")
        if evaluation.get("measurement_gaps"):
            raise ValueError(f"seed {seed} has measurement gaps")
        integrity = evaluation["metrics"]["integrity-checks-pass"]
        if integrity.get("value") is not True:
            raise ValueError(f"seed {seed} failed integrity")
        if campaign["reliability"][seed].get("state") != "pass":
            raise ValueError(f"seed {seed} failed funding reliability")


def _layer_state(evaluation: Mapping[str, Any], layer: str) -> str:
    states = [item.get("state") for item in evaluation.get(layer, [])]
    if not states or any(state not in {"pass", "fail", "unknown"} for state in states):
        return "unknown"
    if "fail" in states:
        return "fail"
    if "unknown" in states:
        return "unknown"
    return "pass"


def _confirmation_policy(
    baseline: Mapping[str, Any], candidate: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    baseline_policy = baseline["snapshot"]["study"].get("paired_confirmation_policy")
    candidate_policy = candidate["snapshot"]["study"].get("paired_confirmation_policy")
    if baseline_policy != candidate_policy:
        raise ValueError("paired confirmation policy differs between campaigns")
    return baseline_policy


def build_paired_comparison(
    baseline_root: str | Path,
    candidate_root: str | Path,
    *,
    seeds: Iterable[int] = DEFAULT_SEEDS,
    allowed_change: str = ALLOWED_DESIGN_CHANGE,
    expected_baseline: float = 0.3,
    expected_candidate: float = 0.5,
    seed_role: str = DEFAULT_SEED_ROLE,
) -> dict[str, Any]:
    """Build an audited diagnostic report without overriding formal eligibility."""
    paired_seeds = tuple(int(seed) for seed in seeds)
    if len(paired_seeds) != len(set(paired_seeds)) or not paired_seeds:
        raise ValueError("paired seeds must be non-empty and unique")
    baseline = _campaign(baseline_root)
    candidate = _campaign(candidate_root)
    _validate_campaign(baseline, paired_seeds, seed_role)
    _validate_campaign(candidate, paired_seeds, seed_role)
    confirmation_policy = _confirmation_policy(baseline, candidate)
    outcome_distribution = (
        confirmation_policy is not None
        and confirmation_policy.get("capability_treatment") == "outcome_distribution"
    )

    audit_pairs = []
    pair_records = []
    for seed in paired_seeds:
        base_row = baseline["rows"][seed]
        candidate_row = candidate["rows"][seed]
        base_design = json.loads(base_row["design_json"])
        candidate_design = json.loads(candidate_row["design_json"])
        differing_design_keys = sorted(
            key for key in set(base_design) | set(candidate_design)
            if base_design.get(key) != candidate_design.get(key)
        )
        if differing_design_keys != [allowed_change]:
            raise ValueError(
                f"seed {seed} design differs outside {allowed_change}: {differing_design_keys}"
            )
        if (
            base_design.get(allowed_change) != expected_baseline
            or candidate_design.get(allowed_change) != expected_candidate
        ):
            raise ValueError(f"seed {seed} has an unexpected intervention value")
        if base_row["fidelity"] != candidate_row["fidelity"]:
            raise ValueError(f"seed {seed} fidelity mismatch")

        base_manifest = _manifest(baseline, seed)
        candidate_manifest = _manifest(candidate, seed)
        if base_manifest.get("run_seed") != seed or candidate_manifest.get("run_seed") != seed:
            raise ValueError(f"seed {seed} manifest seed mismatch")
        for key in MANIFEST_INVARIANTS:
            if base_manifest.get(key) != candidate_manifest.get(key):
                raise ValueError(f"seed {seed} manifest invariant differs: {key}")
        if base_manifest.get("git_dirty_files") or candidate_manifest.get("git_dirty_files"):
            raise ValueError(f"seed {seed} was produced from a dirty worktree")
        if _normalized_args(base_manifest, allowed_change) != _normalized_args(
            candidate_manifest, allowed_change
        ):
            raise ValueError(f"seed {seed} execution arguments differ outside intervention")

        base_eval = baseline["evaluations"][seed]
        candidate_eval = candidate["evaluations"][seed]
        for key in ("constitution", "evaluator"):
            if base_eval.get(key) != candidate_eval.get(key):
                raise ValueError(f"seed {seed} evaluation producer differs: {key}")

        metrics = {}
        for name, (_, _, direction) in METRICS.items():
            base_value = _metric_value(base_eval, name)
            candidate_value = _metric_value(candidate_eval, name)
            metrics[name] = {
                "preferred_direction": direction,
                "baseline": base_value,
                "candidate": candidate_value,
                "delta_candidate_minus_baseline": candidate_value - base_value,
            }
        shadows = {}
        base_shadows = _run_shadows(baseline, seed)
        candidate_shadows = _run_shadows(candidate, seed)
        for name in base_shadows:
            shadows[name] = {
                "baseline": base_shadows[name],
                "candidate": candidate_shadows[name],
                "delta_candidate_minus_baseline": candidate_shadows[name] - base_shadows[name],
            }
        pair_record = {
            "seed": seed,
            "baseline_run_id": base_row["run_id"],
            "candidate_run_id": candidate_row["run_id"],
            "baseline_eligibility": base_eval["comparison_eligibility"],
            "candidate_eligibility": candidate_eval["comparison_eligibility"],
            "metrics": metrics,
            "shadows": shadows,
        }
        if outcome_distribution:
            pair_record.update({
                "baseline_hard_constraint_state": _layer_state(
                    base_eval, "hard_constraints"
                ),
                "candidate_hard_constraint_state": _layer_state(
                    candidate_eval, "hard_constraints"
                ),
                "baseline_capability_state": _layer_state(base_eval, "capabilities"),
                "candidate_capability_state": _layer_state(candidate_eval, "capabilities"),
            })
        pair_records.append(pair_record)
        audit_pairs.append({
            "seed": seed,
            "fidelity": base_row["fidelity"],
            "source_commit": base_manifest["git_commit"],
            "ordered_documents_sha256": base_manifest["ordered_documents_sha256"],
            "invariants_match": True,
            "only_design_change": allowed_change,
        })

    metric_summaries = {
        name: {
            "preferred_direction": METRICS[name][2],
            **summarize_deltas(
                pair["metrics"][name]["delta_candidate_minus_baseline"]
                for pair in pair_records
            ),
        }
        for name in METRICS
    }
    shadow_names = pair_records[0]["shadows"]
    shadow_summaries = {
        name: summarize_deltas(
            pair["shadows"][name]["delta_candidate_minus_baseline"]
            for pair in pair_records
        )
        for name in shadow_names
    }
    legacy_inadmissible = [
        {"seed": pair["seed"], "design": design, "state": pair[f"{design}_eligibility"]}
        for pair in pair_records
        for design in ("baseline", "candidate")
        if pair[f"{design}_eligibility"] != "feasible"
    ]
    technical_inadmissible = []
    if outcome_distribution:
        technical_inadmissible = [
            {"seed": pair["seed"], "design": design,
             "state": pair[f"{design}_hard_constraint_state"]}
            for pair in pair_records
            for design in ("baseline", "candidate")
            if pair[f"{design}_hard_constraint_state"] != "pass"
        ]
    inadmissible = technical_inadmissible if outcome_distribution else legacy_inadmissible
    formal_complete = not inadmissible

    capability_summary = None
    candidate_decision = None
    if outcome_distribution:
        transitions = {key: 0 for key in ("pass_to_pass", "pass_to_fail", "fail_to_pass", "fail_to_fail", "unknown")}
        for pair in pair_records:
            before = pair["baseline_capability_state"]
            after = pair["candidate_capability_state"]
            key = f"{before}_to_{after}"
            if key in transitions:
                transitions[key] += 1
            else:
                transitions["unknown"] += 1
        capability_summary = {
            design: {
                state: sum(
                    pair[f"{design}_capability_state"] == state
                    for pair in pair_records
                )
                for state in ("pass", "fail", "unknown")
            }
            for design in ("baseline", "candidate")
        }
        capability_summary["paired_transitions"] = transitions

        gates = confirmation_policy.get("candidate_gates", {})
        failures = []
        if gates.get("require_zero_candidate_capability_failures", True):
            if capability_summary["candidate"]["fail"]:
                failures.append("candidate has one or more capability failures")
        if capability_summary["candidate"]["unknown"]:
            failures.append("candidate has unknown capability state")
        if gates.get("require_no_pass_to_fail_transition", True):
            if transitions["pass_to_fail"]:
                failures.append("candidate introduces a baseline-pass to candidate-fail transition")
        protected = metric_summaries["low_resource_active_fraction"]
        if gates.get("require_no_negative_protected_slice_pairs", True):
            if protected["negative"]:
                failures.append("candidate harms protected-slice participation in at least one pair")
        primary = metric_summaries["active_researcher_fraction"]
        if primary["mean"] < float(gates.get("minimum_primary_mean_delta", 0.0)):
            failures.append("candidate mean primary participation delta is below the frozen minimum")
        resource_delta = shadow_summaries["grant_income"]["mean"]
        if failures:
            disposition = "not_confirmed"
        elif resource_delta > 0:
            disposition = "confirmed_tradeoff"
        else:
            disposition = "eligible_for_non_dominance_review"
        candidate_decision = {
            "status": disposition,
            "passes_noncompensable_gates": not failures,
            "blocking_reasons": failures,
            "resource_input_mean_delta": resource_delta,
            "interpretation": (
                "Capability and protected-slice gates pass, but higher resource input "
                "requires a trade-off interpretation."
                if disposition == "confirmed_tradeoff" else None
            ),
        }
    report = {
        "schema": "scienceutopia.paired_system_comparison.v1",
        "comparison": {
            "baseline": {
                "study_id": baseline["snapshot"]["study"]["id"],
                "study_revision": baseline["snapshot"]["study_revision"],
                "design_id": baseline["rows"][paired_seeds[0]]["design_id"],
            },
            "candidate": {
                "study_id": candidate["snapshot"]["study"]["id"],
                "study_revision": candidate["snapshot"]["study_revision"],
                "design_id": candidate["rows"][paired_seeds[0]]["design_id"],
            },
            "pairing_key": f"{seed_role}_seed",
            "seeds": list(paired_seeds),
            "n_pairs": len(paired_seeds),
            "intervention": {
                "parameter": allowed_change,
                "baseline": expected_baseline,
                "candidate": expected_candidate,
            },
            "scalar_welfare_score": None,
        },
        "audit": {
            "technical_admissibility_pass": True,
            "pairs": audit_pairs,
        },
        "formal_comparison": {
            "status": "complete" if formal_complete else "incomplete",
            "authorized_for_ranking": formal_complete,
            "inadmissible_runs": inadmissible,
            "reason": None if formal_complete else (
                "At least one preregistered run is infeasible; paired effects remain diagnostic."
            ),
        },
        "paired_runs": pair_records,
        "paired_metric_summaries": metric_summaries,
        "paired_shadow_summaries": shadow_summaries,
        "interpretation_limits": [
            "The bootstrap interval is descriptive for five simulator seeds.",
            "No null-hypothesis significance claim is authorized.",
            "Higher resource input prevents a cost-free dominance claim.",
            "No real-world causal or optimal-science-policy claim is authorized.",
        ],
    }
    if outcome_distribution:
        report["schema"] = "scienceutopia.paired_system_comparison.v2"
        report["comparison"]["seed_role"] = seed_role
        report["formal_comparison"]["authorized_for_ranking"] = False
        report["formal_comparison"]["authorized_for_confirmatory_interpretation"] = (
            formal_complete
        )
        report["confirmation_policy"] = confirmation_policy
        report["capability_outcome_distribution"] = capability_summary
        report["candidate_confirmation_decision"] = candidate_decision
    return report


def render_markdown(report: Mapping[str, Any]) -> str:
    status = report["formal_comparison"]["status"]
    capability = report.get("capability_outcome_distribution")
    lines = [
        (
            "# Five-seed paired system comparison"
            if capability is not None else "# First five-seed paired system comparison"
        ),
        "",
        f"Formal comparison status: **{status}**.",
        "",
        "## Paired objective deltas",
        "",
        "All deltas are candidate minus baseline. Intervals are descriptive "
        "95% paired-bootstrap intervals.",
        "",
        "| Metric | Mean delta | Median | 95% interval | + / 0 / − |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, summary in report["paired_metric_summaries"].items():
        interval = summary["mean_interval"]
        lines.append(
            f"| `{name}` | {summary['mean']:.6g} | {summary['median']:.6g} | "
            f"[{interval['lower']:.6g}, {interval['upper']:.6g}] | "
            f"{summary['positive']} / {summary['zero']} / {summary['negative']} |"
        )
    lines.extend([
        "",
        "## Seed-level participation",
        "",
        "| Seed | Aggregate baseline → candidate | Low-resource baseline → candidate | "
        "Eligibility (B/C) |",
        "|---:|---:|---:|---:|",
    ])
    for pair in report["paired_runs"]:
        aggregate = pair["metrics"]["active_researcher_fraction"]
        protected = pair["metrics"]["low_resource_active_fraction"]
        lines.append(
            f"| {pair['seed']} | {aggregate['baseline']:.3g} → {aggregate['candidate']:.3g} | "
            f"{protected['baseline']:.3g} → {protected['candidate']:.3g} | "
            f"{pair['baseline_eligibility']} / {pair['candidate_eligibility']} |"
        )
    if capability is not None:
        decision = report["candidate_confirmation_decision"]
        transitions = capability["paired_transitions"]
        lines.extend([
            "",
            "## Confirmation capability outcome",
            "",
            f"- Baseline pass/fail/unknown: {capability['baseline']['pass']} / "
            f"{capability['baseline']['fail']} / {capability['baseline']['unknown']}",
            f"- Candidate pass/fail/unknown: {capability['candidate']['pass']} / "
            f"{capability['candidate']['fail']} / {capability['candidate']['unknown']}",
            f"- Paired pass→fail / fail→pass: {transitions['pass_to_fail']} / "
            f"{transitions['fail_to_pass']}",
            f"- Frozen decision: **{decision['status']}**",
        ])
        if decision["blocking_reasons"]:
            lines.extend(
                f"  - {reason}" for reason in decision["blocking_reasons"]
            )
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
    ])
    if status == "incomplete":
        lines.append(
            "The preregistered formal comparison is incomplete because at least one run is "
            "infeasible. It is retained rather than discarded or replaced; the five paired "
            "deltas are diagnostic evidence."
        )
        lines.append("")
    lines.extend(f"- {limit}" for limit in report["interpretation_limits"])
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", required=True)
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--json-output", required=True)
    parser.add_argument("--markdown-output")
    parser.add_argument(
        "--seed-role", choices=["exploration", "selection", "confirmation"],
        default=DEFAULT_SEED_ROLE,
    )
    args = parser.parse_args(argv)
    report = build_paired_comparison(
        args.baseline_root, args.candidate_root, seed_role=args.seed_role,
    )
    json_path = Path(args.json_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.markdown_output:
        markdown_path = Path(args.markdown_output)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
