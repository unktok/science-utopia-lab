"""Generate the development-only frozen-winner cross-objective package."""
from __future__ import annotations

import argparse
import csv
from html import escape
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

from utopia.optimization.post_optimization_comparison import (
    build_post_optimization_comparison,
    validate_post_optimization_comparison,
)


PAPER_RESULTS_DIR = Path("paper/generated/metric-conditioned")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _assignment(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("winner fingerprint must be ARM=SHA256")
    arm, fingerprint = value.split("=", 1)
    if not arm or not fingerprint:
        raise argparse.ArgumentTypeError("winner fingerprint must be ARM=SHA256")
    return arm, fingerprint


def _write_matrix(path: Path, report: Mapping[str, Any]) -> None:
    fields = [
        "selected_by_arm", "system_fingerprint", "selection_loss_id", "scoring_loss_id",
        "aggregate_loss", "seed_mean", "population_sd", "seed_min", "seed_max",
        "ci95_low", "ci95_high", "rank_among_winners", "pareto_front",
    ]
    front = set(report["pareto"]["front_arms"])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for arm, winner in report["winner_matrix"].items():
            for loss_id, cell in winner["evaluations"].items():
                writer.writerow({
                    "selected_by_arm": arm,
                    "system_fingerprint": winner["system_fingerprint"],
                    "selection_loss_id": winner["selection_loss_id"],
                    "scoring_loss_id": loss_id,
                    "aggregate_loss": cell["loss"],
                    "seed_mean": cell["mean"],
                    "population_sd": cell["population_sd"],
                    "seed_min": cell["seed_min"],
                    "seed_max": cell["seed_max"],
                    "ci95_low": cell["uncertainty"]["ci95_low"],
                    "ci95_high": cell["uncertainty"]["ci95_high"],
                    "rank_among_winners": cell["rank_among_winners"],
                    "pareto_front": arm in front,
                })


def _write_tradeoffs(path: Path, report: Mapping[str, Any]) -> None:
    fields = [
        "left_arm", "right_arm", "relation", "scoring_loss_id", "left_loss",
        "right_loss", "left_minus_right", "better",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for pair in report["tradeoffs"]:
            for delta in pair["objective_deltas"]:
                writer.writerow({
                    "left_arm": pair["left_arm"],
                    "right_arm": pair["right_arm"],
                    "relation": pair["relation"],
                    "scoring_loss_id": delta["loss_id"],
                    "left_loss": delta["left_loss"],
                    "right_loss": delta["right_loss"],
                    "left_minus_right": delta["left_minus_right"],
                    "better": delta["better"],
                })


def _write_uncertainty(path: Path, report: Mapping[str, Any]) -> None:
    fields = [
        "arm", "scoring_loss_id", "seed", "run_id", "seed_loss", "execution_mode",
        "population_sd", "ci95_low", "ci95_high",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for arm, winner in report["winner_matrix"].items():
            for loss_id, cell in winner["evaluations"].items():
                for seed in cell["seed_values"]:
                    writer.writerow({
                        "arm": arm,
                        "scoring_loss_id": loss_id,
                        "seed": seed["seed"],
                        "run_id": seed["run_id"],
                        "seed_loss": seed["loss"],
                        "execution_mode": seed["execution_mode"],
                        "population_sd": cell["population_sd"],
                        "ci95_low": cell["uncertainty"]["ci95_low"],
                        "ci95_high": cell["uncertainty"]["ci95_high"],
                    })


def _write_runtime_provenance(path: Path, report: Mapping[str, Any]) -> None:
    fields = [
        "scope", "logical_runs", "executed_runs", "adopted_runs",
        "physical_attempt_wall_seconds", "attempt_status_counts",
        "non_complete_physical_attempts", "source_commit", "winner_freeze_sha256",
    ]
    rows = [("global", report["execution"]["global"])] + list(
        report["execution"]["by_arm"].items()
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for scope, summary in rows:
            writer.writerow({
                "scope": scope,
                "logical_runs": summary["logical_runs"],
                "executed_runs": summary["executed_runs"],
                "adopted_runs": summary["adopted_runs"],
                "physical_attempt_wall_seconds": summary["physical_attempt_wall_seconds"],
                "attempt_status_counts": json.dumps(
                    summary["attempt_status_counts"], sort_keys=True, separators=(",", ":")
                ),
                "non_complete_physical_attempts": (
                    report["execution"]["non_complete_physical_attempts"]
                    if scope == "global" else
                    sum(
                        count for status, count in summary["attempt_status_counts"].items()
                        if status != "complete"
                    )
                ),
                "source_commit": report["provenance"]["source_commit"],
                "winner_freeze_sha256": report["provenance"]["winner_freeze_sha256"],
            })


def _short(value: str, length: int = 20) -> str:
    return value if len(value) <= length else value[: length - 1] + "…"


def _write_svg(path: Path, report: Mapping[str, Any]) -> None:
    arms = list(report["winner_matrix"])
    losses = list(report["objective_rankings"])
    colors = ("#21D4C2", "#FF4FD8", "#FFD166")
    width, height = 1280, 780
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="1280" height="780" fill="#07101D"/>',
        '<style>text{font-family:Inter,Arial,sans-serif;fill:#EAF4FF}.title{font-size:25px;font-weight:700}.sub{font-size:13px;fill:#8FA8BF}.label{font-size:12px}.small{font-size:10px;fill:#AFC4D6}.value{font-size:13px;font-weight:700}.panel{fill:#0D1A2A;stroke:#25445C;stroke-width:1}</style>',
        '<text x="52" y="52" class="title">Frozen winners × optimization objectives</text>',
        '<text x="52" y="78" class="sub">Development evidence only · held-out artifacts untouched · lower loss is better</text>',
        '<rect x="930" y="32" width="300" height="48" rx="8" fill="#3B1731" stroke="#FF4FD8"/>',
        '<text x="1080" y="60" text-anchor="middle" class="label">PRE-HELD-OUT / NO GENERALIZATION CLAIM</text>',
        '<rect x="42" y="104" width="610" height="408" rx="12" class="panel"/>',
        '<text x="64" y="136" class="label">A · Cross-objective matrix (color = within-objective rank)</text>',
    ]
    x0, y0, cell_w, cell_h = 270, 170, 112, 90
    for col, loss_id in enumerate(losses):
        parts.append(
            f'<text x="{x0 + col * cell_w + cell_w / 2}" y="158" text-anchor="middle" class="small">{escape(_short(loss_id, 16))}</text>'
        )
    rank_colors = {1.0: "#176C65", 2.0: "#54446C", 3.0: "#6B3D4B"}
    for row, arm in enumerate(arms):
        parts.append(
            f'<text x="252" y="{y0 + row * cell_h + 38}" text-anchor="end" class="label">{escape(_short(arm, 26))}</text>'
        )
        for col, loss_id in enumerate(losses):
            cell = report["winner_matrix"][arm]["evaluations"][loss_id]
            rank = cell["rank_among_winners"]
            fill = rank_colors.get(rank, "#3F5365")
            x, y = x0 + col * cell_w, y0 + row * cell_h
            parts.extend([
                f'<rect x="{x + 4}" y="{y}" width="{cell_w - 8}" height="{cell_h - 10}" rx="8" fill="{fill}"/>',
                f'<text x="{x + cell_w / 2}" y="{y + 32}" text-anchor="middle" class="value">{cell["loss"]:.4g}</text>',
                f'<text x="{x + cell_w / 2}" y="{y + 55}" text-anchor="middle" class="small">rank {rank:g} · sd {cell["population_sd"]:.3g}</text>',
            ])
    parts.extend([
        '<rect x="674" y="104" width="564" height="408" rx="12" class="panel"/>',
        '<text x="696" y="136" class="label">B · Relative regret profiles (0 = best, 1 = worst per objective)</text>',
    ])
    axis_x = [730, 950, 1170]
    for x, loss_id in zip(axis_x, losses):
        parts.extend([
            f'<line x1="{x}" y1="180" x2="{x}" y2="430" stroke="#38546A"/>',
            f'<text x="{x}" y="160" text-anchor="middle" class="small">{escape(_short(loss_id, 18))}</text>',
            f'<text x="{x}" y="450" text-anchor="middle" class="small">worse</text>',
        ])
    for index, arm in enumerate(arms):
        points = []
        for x, loss_id in zip(axis_x, losses):
            values = report["objective_rankings"][loss_id]["values"]
            low, high = min(values.values()), max(values.values())
            normalized = 0.0 if high == low else (values[arm] - low) / (high - low)
            points.append((x, 190 + normalized * 220))
        encoded = " ".join(f"{x},{y}" for x, y in points)
        parts.append(
            f'<polyline points="{encoded}" fill="none" stroke="{colors[index]}" stroke-width="4" opacity="0.9"/>'
        )
        for x, y in points:
            parts.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{colors[index]}"/>')
        parts.append(
            f'<text x="{700 + index * 178}" y="486" class="small" fill="{colors[index]}">● {escape(_short(arm, 20))}</text>'
        )
    parts.extend([
        '<rect x="42" y="534" width="1196" height="188" rx="12" class="panel"/>',
        '<text x="64" y="568" class="label">C · Pareto, runtime, failures, and provenance</text>',
    ])
    front = report["pareto"]["front_arms"]
    reversal = "observed" if report["rank_reversal"]["observed"] else "not observed"
    global_execution = report["execution"]["global"]
    lines = [
        f"Pareto front: {', '.join(_short(item, 28) for item in front)}",
        f"Cross-objective top-system reversal: {reversal}",
        f"Logical development runs: {global_execution['logical_runs']} = {global_execution['executed_runs']} executed + {global_execution['adopted_runs']} adopted",
        f"Physical attempt wall time: {global_execution['physical_attempt_wall_seconds'] / 3600:.2f} h · non-complete attempts retained: {report['execution']['non_complete_physical_attempts']}",
        f"Source commit: {report['provenance']['source_commit']} · freeze: {report['provenance']['winner_freeze_sha256'][:16]}…",
    ]
    for index, line in enumerate(lines):
        parts.append(f'<text x="72" y="{602 + index * 25}" class="label">{escape(line)}</text>')
    if report["data_classification"] == "synthetic_test_fixture":
        parts.append(
            '<text x="640" y="405" text-anchor="middle" transform="rotate(-20 640 405)" font-size="56" fill="#FF4FD8" opacity="0.13">SYNTHETIC TEST ONLY</text>'
        )
    parts.append("</svg>\n")
    path.write_text("".join(parts), encoding="utf-8")


def _tex_escape(value: str) -> str:
    result = value
    for source, replacement in (
        ("\\", r"\textbackslash{}"), ("_", r"\_"), ("%", r"\%"),
        ("&", r"\&"), ("#", r"\#"), ("$", r"\$"),
    ):
        result = result.replace(source, replacement)
    return result


def _write_latex(path: Path, report: Mapping[str, Any]) -> None:
    arms = list(report["winner_matrix"])
    losses = list(report["objective_rankings"])
    front = set(report["pareto"]["front_arms"])
    lines = [
        r"% Generated development-only table; held-out evidence was not accessed.",
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\begin{tabular}{l" + "r" * len(losses) + "}",
        r"\toprule",
        "Selected by & " + " & ".join(_tex_escape(item) for item in losses) + r" \\",
        r"\midrule",
    ]
    for arm in arms:
        marker = r"$^{\dagger}$" if arm in front else ""
        cells = []
        for loss_id in losses:
            cell = report["winner_matrix"][arm]["evaluations"][loss_id]
            cells.append(
                f"{cell['loss']:.3f} [{cell['uncertainty']['ci95_low']:.3f}, "
                f"{cell['uncertainty']['ci95_high']:.3f}]"
            )
        lines.append(_tex_escape(arm) + marker + " & " + " & ".join(cells) + r" \\")
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\caption{Frozen systems re-scored under all three optimization losses on the common development seeds. Brackets are exact seed-bootstrap 95\% intervals; $\dagger$ marks the conditional Pareto front. These are not held-out estimates.}",
        r"\label{tab:metric-conditioned-post-optimization}",
        r"\end{table}",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_markdown(path: Path, report: Mapping[str, Any]) -> None:
    classification = report["data_classification"]
    lines = [
        "# Metric-conditioned post-optimization comparison",
        "",
        f"> Data classification: `{classification}`.",
        "> Development evidence only. No held-out artifact was read or created.",
        "",
        f"- Study revision: `{report['study_revision']}`",
        f"- Conditional Pareto front: {', '.join(report['pareto']['front_arms'])}",
        f"- Top-system rank reversal across LossSpecs: {report['rank_reversal']['observed']}",
        f"- Physical attempt wall time: {report['execution']['global']['physical_attempt_wall_seconds'] / 3600:.2f} h",
        f"- Non-complete physical attempts retained: {report['execution']['non_complete_physical_attempts']}",
        "",
        report["interpretation_guard"],
        "",
    ]
    if classification == "synthetic_test_fixture":
        lines.insert(2, "> **SYNTHETIC TEST ONLY — NOT AN EXPERIMENTAL RESULT.**")
    path.write_text("\n".join(lines), encoding="utf-8")


def _manifest(root: Path, source_sha256: str) -> dict[str, Any]:
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        payload = path.read_bytes()
        files.append({
            "path": str(path.relative_to(root)),
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    return {
        "schema": "scienceutopia.metric-conditioned-post-optimization-artifacts.v1",
        "source_completion_report_sha256": source_sha256,
        "files": files,
    }


def write_package(report: Mapping[str, Any], output_dir: Path) -> list[Path]:
    validate_post_optimization_comparison(report)
    if output_dir.exists():
        raise FileExistsError(f"refuse to overwrite existing output directory: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        _write_json(temporary / "post-optimization-comparison.json", report)
        _write_matrix(temporary / "cross-objective-matrix.csv", report)
        _write_tradeoffs(temporary / "pareto-tradeoffs.csv", report)
        _write_uncertainty(temporary / "seed-uncertainty.csv", report)
        _write_runtime_provenance(temporary / "runtime-provenance.csv", report)
        _write_latex(temporary / "post-optimization-comparison.tex", report)
        _write_markdown(temporary / "post-optimization-comparison.md", report)
        figure_dir = temporary / "figures"
        figure_dir.mkdir()
        _write_svg(figure_dir / "post-optimization-comparison.svg", report)
        _write_json(
            temporary / "artifact-manifest.json",
            _manifest(temporary, report["input"]["completion_report_sha256"]),
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
    parser.add_argument("--completion-report", required=True, type=Path)
    parser.add_argument(
        "--winner-fingerprint", action="append", required=True, type=_assignment
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    assignments = dict(args.winner_fingerprint)
    if len(assignments) != len(args.winner_fingerprint):
        raise ValueError("duplicate winner-fingerprint assignment")
    completion = _read_json(args.completion_report)
    if (
        completion.get("data_classification") == "synthetic_test_fixture"
        and _inside_paper(args.output_dir)
    ):
        raise ValueError("synthetic fixtures may not be written into paper results")
    report = build_post_optimization_comparison(completion, assignments)
    write_package(report, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
