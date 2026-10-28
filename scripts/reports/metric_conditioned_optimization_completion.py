"""Build the atomic development-only metric-conditioned completion package."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

from scripts.figures.metric_conditioned_optimization_completion import (
    SYNTHETIC,
    render_completion_figure,
)
from utopia.optimization.metric_conditioned_completion import (
    build_optimization_completion_report,
    canonical_report_sha256,
    validate_completion_report,
)


PAPER_RESULTS_DIR = Path("paper/generated/metric-conditioned")


def _assignment(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("campaign root must be ARM=PATH")
    arm, path = value.split("=", 1)
    if not arm or not path:
        raise argparse.ArgumentTypeError("campaign root must be ARM=PATH")
    return arm, Path(path)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _write_candidates(path: Path, report: Mapping[str, Any]) -> None:
    fields = [
        "arm", "proposal_index", "phase", "candidate_key", "design_id",
        "system_fingerprint", "own_loss_id", "selection_loss", "seed_mean",
        "population_sd", "ci95_low", "ci95_high", "executed_runs",
        "adopted_runs", "frozen_winner",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for arm, arm_report in report["arms"].items():
            own = arm_report["loss_spec"]["id"]
            for candidate in arm_report["candidates"]:
                result = candidate["cross_objective_losses"][own]
                writer.writerow({
                    "arm": arm,
                    "proposal_index": candidate["proposal_index"],
                    "phase": candidate["phase"],
                    "candidate_key": candidate["candidate_key"],
                    "design_id": candidate["design_id"],
                    "system_fingerprint": candidate["system_fingerprint"],
                    "own_loss_id": own,
                    "selection_loss": result["loss"],
                    "seed_mean": result["mean"],
                    "population_sd": result["population_sd"],
                    "ci95_low": result["uncertainty"]["ci95_low"],
                    "ci95_high": result["uncertainty"]["ci95_high"],
                    "executed_runs": candidate["execution_provenance"].get("executed", 0),
                    "adopted_runs": candidate["execution_provenance"].get("adopted", 0),
                    "frozen_winner": (
                        candidate["candidate_key"]
                        == arm_report["frozen_winner_candidate_key"]
                    ),
                })


def _write_cross_objective(path: Path, report: Mapping[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "selected_by_arm", "winner_candidate_key", "winner_design_id",
            "scoring_loss", "loss", "seed_mean", "population_sd",
            "ci95_low", "ci95_high", "rank_among_frozen_winners",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        frozen = report["development_cross_objective"]["frozen_winner_matrix"]
        arms = list(report["arms"])
        for loss_id in report["development_cross_objective"]["candidate_rankings"]:
            ordered = sorted(arms, key=lambda arm: (frozen[arm][loss_id]["loss"], arm))
            ranks = {arm: index + 1 for index, arm in enumerate(ordered)}
            for arm in arms:
                arm_report = report["arms"][arm]
                key = arm_report["frozen_winner_candidate_key"]
                candidate = next(
                    item for item in arm_report["candidates"]
                    if item["candidate_key"] == key
                )
                result = frozen[arm][loss_id]
                writer.writerow({
                    "selected_by_arm": arm,
                    "winner_candidate_key": key,
                    "winner_design_id": candidate["design_id"],
                    "scoring_loss": loss_id,
                    "loss": result["loss"],
                    "seed_mean": result["mean"],
                    "population_sd": result["population_sd"],
                    "ci95_low": result["uncertainty"]["ci95_low"],
                    "ci95_high": result["uncertainty"]["ci95_high"],
                    "rank_among_frozen_winners": ranks[arm],
                })


def _write_winners(path: Path, report: Mapping[str, Any]) -> None:
    parameter_names = sorted({
        name
        for arm_report in report["arms"].values()
        for item in arm_report["candidates"]
        if item["candidate_key"] == arm_report["frozen_winner_candidate_key"]
        for name in item["source_candidate"]
    })
    fields = ["arm", "loss_spec", "candidate_key", "design_id", *parameter_names]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for arm, arm_report in report["arms"].items():
            key = arm_report["frozen_winner_candidate_key"]
            candidate = next(
                item for item in arm_report["candidates"] if item["candidate_key"] == key
            )
            writer.writerow({
                "arm": arm,
                "loss_spec": arm_report["loss_spec"]["id"],
                "candidate_key": key,
                "design_id": candidate["design_id"],
                **candidate["source_candidate"],
            })


def _write_markdown(path: Path, report: Mapping[str, Any]) -> None:
    cross = report["development_cross_objective"]
    lines = [
        "# Metric-conditioned optimization completion",
        "",
        "> **Development split only. Held-out seeds were verified unused.**",
        "",
        f"Study: `{report['study_id']}` at revision `{report['study_revision']}`.",
        "",
        "The three LossSpecs were optimized under the same 5-candidate × 3-seed "
        "budget. This report describes which institutional system each objective "
        "selected; it does not select a universal science-policy winner.",
        "",
        "## Frozen systems",
        "",
        "| Objective arm | LossSpec | Candidate | Design | Selection loss | Seed SD |",
        "|---|---|---:|---|---:|---:|",
    ]
    for arm, arm_report in report["arms"].items():
        key = arm_report["frozen_winner_candidate_key"]
        candidate = next(item for item in arm_report["candidates"] if item["candidate_key"] == key)
        own = arm_report["loss_spec"]["id"]
        value = candidate["cross_objective_losses"][own]
        lines.append(
            f"| `{arm}` | `{own}` | {candidate['proposal_index'] + 1} | "
            f"`{candidate['design_id']}` | {value['loss']:.6g} | "
            f"{value['population_sd']:.6g} |"
        )
    lines.extend([
        "",
        "## Objective-conditioned ranking",
        "",
        "| Scoring objective | Best of all 15 observed candidates | Design |",
        "|---|---|---|",
    ])
    for loss_id, ranking in cross["candidate_rankings"].items():
        lines.append(
            f"| `{loss_id}` | `{ranking['best_candidate_key']}` | "
            f"`{ranking['best_design_id']}` |"
        )
    lines.extend([
        "",
        f"Pairwise objective comparisons with a different top candidate: "
        f"**{len(cross['winner_reversals'])} / "
        f"{len(cross['pairwise_rank_association'])}**.",
        "",
        "## Execution and evidence boundary",
        "",
        f"- Logical development runs: {report['execution']['logical_runs']}.",
        f"- Physically executed logical runs: {report['execution']['executed_runs']}.",
        f"- Provenance-adopted logical runs: {report['execution']['adopted_runs']}.",
        f"- Physical attempt wall-seconds: "
        f"{report['execution']['physical_attempt_wall_seconds']:.3f}.",
        "- Held-out registry, snapshot, and cross-evaluation report were absent.",
        "- Seeds listed as held-out were absent from every arm registry.",
        "",
        "Seed intervals are exact percentile intervals over all 3^3 resamples of "
        "the three development-seed losses. They are descriptive development-world "
        "uncertainty, not held-out generalization intervals.",
        "",
        report["interpretation_guard"],
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def _manifest(root: Path, report_sha: str) -> dict[str, Any]:
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        content = path.read_bytes()
        files.append({
            "path": str(path.relative_to(root)),
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })
    return {
        "schema": "scienceutopia.metric-conditioned-optimization-completion-artifacts.v1",
        "source_report_sha256": report_sha,
        "files": files,
    }


def write_package(
    report: Mapping[str, Any], output_dir: Path, formats=("pdf", "png")
) -> list[Path]:
    validate_completion_report(report)
    if output_dir.exists():
        raise FileExistsError(f"refuse to overwrite existing output directory: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        report_path = temporary / "metric-conditioned-optimization-completion.json"
        _write_json(report_path, report)
        _write_candidates(temporary / "development-candidates.csv", report)
        _write_cross_objective(temporary / "development-cross-objective.csv", report)
        _write_winners(temporary / "frozen-winner-systems.csv", report)
        _write_markdown(temporary / "metric-conditioned-optimization-completion.md", report)
        figure_dir = temporary / "figures"
        render_completion_figure(report, figure_dir, formats=formats)
        _write_json(
            temporary / "artifact-manifest.json",
            _manifest(temporary, canonical_report_sha256(report)),
        )
        os.replace(temporary, output_dir)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return sorted(path for path in output_dir.rglob("*") if path.is_file())


def _inside_paper(path: Path) -> bool:
    resolved = path.resolve()
    paper = PAPER_RESULTS_DIR.resolve()
    return resolved == paper or paper in resolved.parents


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--study-root", required=True, type=Path)
    parser.add_argument("--campaign-root", action="append", required=True, type=_assignment)
    parser.add_argument(
        "--classification", choices=("experimental", "synthetic-test"),
        default="experimental",
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--formats", default="pdf,png")
    args = parser.parse_args(argv)
    classification = SYNTHETIC if args.classification == "synthetic-test" else "experimental"
    if classification == SYNTHETIC and _inside_paper(args.output_dir):
        raise ValueError("synthetic fixtures may not be written into the paper results directory")
    roots = dict(args.campaign_root)
    if len(roots) != len(args.campaign_root):
        raise ValueError("duplicate campaign-root assignment")
    report = build_optimization_completion_report(
        manifest_path=args.manifest,
        study_root=args.study_root,
        campaign_roots=roots,
        classification=classification,
    )
    formats = tuple(item.strip() for item in args.formats.split(",") if item.strip())
    for path in write_package(report, args.output_dir, formats=formats):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
