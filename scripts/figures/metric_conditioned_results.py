"""Reproducible paper graphics for the metric-conditioned optimization study.

The pipeline has an explicit two-stage boundary:

1. normalize a cross-evaluation report and arm campaign states into one compact
   ``scienceutopia.metric-conditioned-figure-data.v1`` JSON file;
2. render every figure from that JSON alone.

Synthetic fixtures are rejected unless ``--classification synthetic-test`` is
explicit, and every synthetic rendering carries an in-figure warning banner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from scripts.figures.visual_utils import GRID, INK, MUTED, nature_style


SUMMARY_SCHEMA = "scienceutopia.metric-conditioned-figure-data.v1"
REPORT_SCHEMA = "scienceutopia.metric-conditioned-cross-evaluation-report.v1"
SYNTHETIC = "synthetic_test_fixture"
EXPERIMENTAL = "experimental_result"
ARM_ORDER = (
    "metric-conditioned-participation-review-v1",
    "metric-conditioned-topic-diversity-v1",
    "metric-conditioned-review-burden-v1",
)
ROLE_ORDER = ("participation-review", "topic-diversity", "review-burden")
ROLE_LABELS = {
    ROLE_ORDER[0]: "Participation-review",
    ROLE_ORDER[1]: "Topic-entropy proxy",
    ROLE_ORDER[2]: "Review-burden proxy",
}
ROLE_COLORS = {
    ROLE_ORDER[0]: "#376795",
    ROLE_ORDER[1]: "#E8A33D",
    ROLE_ORDER[2]: "#E76254",
}
LOSS_LABELS = {
    "participation-review-tradeoff-probe": "Part.-review",
    "topic-diversity-probe": "Topic entropy",
    "review-burden-probe": "Review burden",
}
REPO_ROOT = Path(__file__).resolve().parents[2]
PAPER_RESULTS_DIR = REPO_ROOT / "paper/figures/metric-conditioned"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _classification(value: Mapping[str, Any]) -> str:
    return value.get("provenance", {}).get("data_classification", EXPERIMENTAL)


def _arm_role(arm: str) -> str | None:
    return next((role for role in ROLE_ORDER if role in arm), None)


def _arm_order(arms) -> list[str]:
    return sorted(
        set(arms),
        key=lambda arm: (
            ROLE_ORDER.index(_arm_role(arm)) if _arm_role(arm) else len(ROLE_ORDER),
            arm,
        ),
    )


def _loss_label(loss_id: str) -> str:
    return LOSS_LABELS.get(loss_id, loss_id.replace("-probe", "").replace("-", " "))


def _profile_map(report: Mapping[str, Any], arm: str) -> dict[str, Mapping[str, Any]]:
    result = {}
    for profile in report["held_out_metric_profiles"][arm]:
        key = profile["id"]
        if profile.get("slice"):
            key += "/" + profile["slice"]
        result[key] = profile
    return result


def _trajectory_from_state(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    trajectory = []
    incumbent = math.inf
    for record in sorted(
        state["suggestions"], key=lambda item: item["suggestion"]["proposal_index"]
    ):
        observation = record.get("observation") or {}
        loss = observation.get("loss")
        if isinstance(loss, (int, float)) and math.isfinite(float(loss)):
            incumbent = min(incumbent, float(loss))
        trajectory.append({
            "proposal_index": int(record["suggestion"]["proposal_index"]),
            "phase": record["suggestion"].get("phase", "unknown"),
            "status": record["status"],
            "loss": float(loss) if isinstance(loss, (int, float)) else None,
            "incumbent_loss": incumbent if math.isfinite(incumbent) else None,
            "suggestion_id": record["suggestion"]["suggestion_id"],
        })
    return trajectory


def normalize_report(
    report: Mapping[str, Any],
    campaign_states: Mapping[str, Mapping[str, Any]],
    *,
    classification: str,
) -> dict[str, Any]:
    if report.get("schema") != REPORT_SCHEMA:
        raise ValueError(f"expected {REPORT_SCHEMA}")
    source_class = _classification(report)
    if classification == SYNTHETIC and source_class != SYNTHETIC:
        raise ValueError("synthetic-test mode requires an explicitly synthetic source report")
    if classification == EXPERIMENTAL and source_class == SYNTHETIC:
        raise ValueError("synthetic fixture cannot be rendered as an experimental result")

    arms = _arm_order(report["loss_by_frozen_winner"])
    missing_states = set(arms) - set(campaign_states)
    embedded = report.get("optimization_trajectories", {})
    if missing_states - set(embedded):
        raise ValueError(f"missing optimization trajectories for {sorted(missing_states)}")
    trajectories = {
        arm: (
            _trajectory_from_state(campaign_states[arm])
            if arm in campaign_states else embedded[arm]
        )
        for arm in arms
    }

    loss_ids = sorted({
        loss_id
        for system_losses in report["loss_by_frozen_winner"].values()
        for loss_id in system_losses
    })
    cross_loss = {
        arm: {
            loss_id: report["loss_by_frozen_winner"][arm][loss_id].get("loss")
            for loss_id in loss_ids
        }
        for arm in arms
    }
    metrics = {}
    for arm in arms:
        profiles = _profile_map(report, arm)
        metrics[arm] = {
            key: {
                "mean": profile.get("summary", {}).get("mean"),
                "population_sd": profile.get("summary", {}).get("population_sd"),
                "direction": profile["direction"],
                "complete": profile.get("complete", False),
            }
            for key, profile in profiles.items()
            if isinstance(profile.get("summary", {}).get("mean"), (int, float))
        }

    analyses = report["analyses"]
    summary = {
        "schema": SUMMARY_SCHEMA,
        "provenance": {
            "data_classification": classification,
            "source_report_sha256": _sha(report),
            "source_campaign_state_sha256": {
                arm: _sha(campaign_states[arm]) if arm in campaign_states else None
                for arm in arms
            },
            "source_report_schema": report["schema"],
            "study_id": report["study_id"],
            "study_revision": report["study_revision"],
            "warning": (
                "SYNTHETIC TEST FIXTURE - NOT AN EXPERIMENTAL RESULT"
                if classification == SYNTHETIC else None
            ),
        },
        "arms": [
            {
                "id": arm,
                "label": ROLE_LABELS.get(_arm_role(arm), arm),
                "color": ROLE_COLORS.get(_arm_role(arm), "#666666"),
            }
            for arm in arms
        ],
        "optimization_trajectories": trajectories,
        "cross_evaluation": {"loss_ids": loss_ids, "values": cross_loss},
        "held_out_metrics": metrics,
        "rank_reversal": analyses["rank_reversal"],
        "paired_tradeoffs": analyses["paired_tradeoffs"],
        "gaming_flags": analyses["gaming_flags"],
        "generalization": analyses["generalization"],
        "secondary_resolution": analyses["secondary_resolution"],
    }
    return summary


def _warning(fig, summary: Mapping[str, Any]) -> None:
    if _classification(summary) == SYNTHETIC:
        fig.text(
            0.5, 0.995, "SYNTHETIC TEST FIXTURE - NOT AN EXPERIMENTAL RESULT",
            ha="center", va="top", fontsize=7, color="white", fontweight="bold",
            bbox={"facecolor": "#A61B1B", "edgecolor": "none", "pad": 2.5},
        )


def _save(fig, out_dir: Path, stem: str, formats: tuple[str, ...]) -> list[Path]:
    paths = []
    for extension in formats:
        path = out_dir / f"{stem}.{extension}"
        kwargs = {"dpi": 300, "bbox_inches": "tight"}
        if extension == "pdf":
            kwargs["metadata"] = {
                "Creator": "Science Utopia Lab metric-conditioned graphics pipeline",
                "CreationDate": None,
                "ModDate": None,
            }
        fig.savefig(path, **kwargs)
        paths.append(path)
    plt.close(fig)
    return paths


def plot_cross_evaluation(summary, out_dir, formats):
    arms = [item["id"] for item in summary["arms"]]
    labels = [item["label"] for item in summary["arms"]]
    loss_ids = summary["cross_evaluation"]["loss_ids"]
    matrix = np.array([
        [summary["cross_evaluation"]["values"][arm][loss] for loss in loss_ids]
        for arm in arms
    ], dtype=float)
    # Each loss has its own units and scale. Color therefore encodes only the
    # within-column rank while the annotations retain the measured loss.
    ranks = np.array([
        [
            summary["rank_reversal"]["columns"][f"loss:{loss}"]["ranks"][arm]
            for loss in loss_ids
        ]
        for arm in arms
    ], dtype=float)
    uncertainty = summary["cross_evaluation"].get("uncertainty")
    annotations: Any = matrix
    annotation_format = ".3f"
    if uncertainty:
        annotations = np.array([
            [
                (
                    f"{matrix[row, column]:.3f}\n"
                    f"[{uncertainty[arm][loss]['ci95_low']:.3f}, "
                    f"{uncertainty[arm][loss]['ci95_high']:.3f}]"
                )
                for column, loss in enumerate(loss_ids)
            ]
            for row, arm in enumerate(arms)
        ])
        annotation_format = ""
    fig, ax = plt.subplots(figsize=(5.6, 2.45))
    sns.heatmap(
        ranks, annot=annotations, fmt=annotation_format, cmap="mako_r", linewidths=0.5,
        vmin=1, vmax=len(arms),
        linecolor="white", xticklabels=[_loss_label(item) for item in loss_ids],
        yticklabels=labels, cbar_kws={"label": "Within-loss rank (1 = best)"}, ax=ax,
    )
    ax.set_xlabel("Loss used to score each frozen system")
    ax.set_ylabel("Optimization objective that produced the system")
    ax.set_title("Cross-evaluation exposes objective-conditioned systems", pad=7)
    ax.tick_params(axis="x", rotation=20)
    _warning(fig, summary)
    fig.tight_layout(rect=(0, 0, 1, 0.96 if _classification(summary) == SYNTHETIC else 1))
    return _save(fig, out_dir, "metric-conditioned-cross-evaluation", formats)


def plot_trajectories(summary, out_dir, formats):
    arms = summary["arms"]
    fig, axes = plt.subplots(1, len(arms), figsize=(7.2, 2.65), squeeze=False)
    for ax, arm in zip(axes[0], arms):
        rows = summary["optimization_trajectories"][arm["id"]]
        x = [item["proposal_index"] + 1 for item in rows if item["loss"] is not None]
        raw = [item["loss"] for item in rows if item["loss"] is not None]
        incumbent = [item["incumbent_loss"] for item in rows if item["loss"] is not None]
        ax.plot(
            x, raw, marker="o", linewidth=0.8, alpha=0.42,
            color=arm["color"], label="observed",
        )
        ax.step(
            x, incumbent, where="post", linewidth=1.8,
            color=arm["color"], label="incumbent",
        )
        winner = min(
            (item for item in rows if item["loss"] is not None),
            key=lambda item: (item["loss"], item["proposal_index"]),
        )
        ax.scatter(
            winner["proposal_index"] + 1,
            winner["loss"],
            marker="*",
            s=42,
            color=INK,
            edgecolor="white",
            linewidth=0.4,
            zorder=5,
            label="frozen winner",
        )
        boundary = next(
            (
                item["proposal_index"] + 0.5
                for item in rows
                if item["phase"] != "initial"
            ),
            None,
        )
        if boundary is not None:
            ax.axvline(boundary, color=MUTED, linestyle=":", linewidth=0.8)
        ax.set_xlabel("Proposal index")
        ax.set_title(arm["label"], pad=5)
        ax.set_xticks(x)
        ax.grid(axis="y", color=GRID, linewidth=0.5)
        sns.despine(ax=ax)
    axes[0][0].set_ylabel("Development loss (arm-specific units)")
    axes[0][-1].legend(frameon=False, loc="best")
    synthetic = _classification(summary) == SYNTHETIC
    fig.suptitle(
        "Each objective steers a separate optimization trajectory",
        x=0.07, y=0.86 if synthetic else 0.97,
        ha="left", fontsize=7.5, fontweight="bold",
    )
    _warning(fig, summary)
    fig.tight_layout(rect=(0, 0, 1, 0.77 if synthetic else 0.89))
    return _save(fig, out_dir, "metric-conditioned-objective-trajectories", formats)


def plot_tradeoff_rank_generalization(summary, out_dir, formats):
    fig, axes = plt.subplots(1, 4, figsize=(9.4, 2.35))
    arms = [item["id"] for item in summary["arms"]]
    for arm in summary["arms"]:
        metrics = summary["held_out_metrics"][arm["id"]]
        x = metrics["review-burden-per-active-researcher"]["mean"]
        y = metrics["active-researcher-fraction"]["mean"]
        axes[0].errorbar(
            x,
            y,
            xerr=metrics["review-burden-per-active-researcher"].get("population_sd"),
            yerr=metrics["active-researcher-fraction"].get("population_sd"),
            fmt="o",
            markersize=5.3,
            color=arm["color"],
            ecolor=arm["color"],
            elinewidth=0.8,
            capsize=1.8,
            markeredgecolor="white",
            markeredgewidth=0.5,
            zorder=3,
        )
        axes[0].annotate(arm["label"], (x, y), xytext=(4, 3), textcoords="offset points", fontsize=5.7)
    axes[0].set_xlabel("Review burden (lower is better)")
    axes[0].set_ylabel("Active-researcher fraction")
    axes[0].set_title("Held-out trade-off", pad=4)
    axes[0].grid(color=GRID, linewidth=0.5)

    loss_columns = [
        key for key in summary["rank_reversal"]["columns"] if key.startswith("loss:")
    ]
    rank_matrix = np.array([
        [summary["rank_reversal"]["columns"][column]["ranks"].get(arm, np.nan) for column in loss_columns]
        for arm in arms
    ])
    sns.heatmap(
        rank_matrix, annot=True, fmt=".1f", cmap="crest_r", vmin=1, vmax=len(arms),
        cbar=False, linewidths=0.4, linecolor="white", ax=axes[1],
        xticklabels=[_loss_label(column.removeprefix("loss:")) for column in loss_columns],
        yticklabels=[item["label"] for item in summary["arms"]],
    )
    axes[1].set_title("Rank reversal", pad=4)
    axes[1].set_xlabel("Held-out scoring loss")
    axes[1].tick_params(axis="x", rotation=25)

    triggered = {
        arm: sum(
            item.get("triggered") is True
            and item.get("signature")
            != "development_improvement_without_held_out_transfer"
            for item in summary["gaming_flags"]
            if item.get("system") == arm
        )
        for arm in arms
    }
    evaluated = {
        arm: sum(
            item.get("signature")
            != "development_improvement_without_held_out_transfer"
            for item in summary["gaming_flags"]
            if item.get("system") == arm
        )
        for arm in arms
    }
    axes[2].bar(
        range(len(arms)),
        [triggered[arm] for arm in arms],
        color=[item["color"] for item in summary["arms"]],
        width=0.65,
    )
    axes[2].set_xticks(
        range(len(arms)), ["Part.-review", "Topic", "Burden"], rotation=20
    )
    axes[2].set_ylabel("Triggered pairwise flags")
    axes[2].set_title("Gaming diagnostics", pad=4)
    axes[2].grid(axis="y", color=GRID, linewidth=0.5)
    for index, arm in enumerate(arms):
        axes[2].text(
            index,
            triggered[arm] + 0.04,
            f"{triggered[arm]}/{evaluated[arm]}",
            ha="center",
            va="bottom",
            fontsize=5.5,
        )

    gaps = [
        summary["generalization"][arm]["generalization_gap_held_out_minus_optimization"]
        for arm in arms
    ]
    axes[3].bar(
        range(len(arms)), gaps, color=[item["color"] for item in summary["arms"]], width=0.65
    )
    axes[3].axhline(0, color=MUTED, linewidth=0.7)
    axes[3].set_xticks(range(len(arms)), ["Part.-review", "Topic", "Burden"], rotation=20)
    axes[3].set_ylabel("Held-out - development loss")
    axes[3].set_title("Generalization gap", pad=4)
    axes[3].grid(axis="y", color=GRID, linewidth=0.5)
    for ax, letter in zip(axes, "abcd"):
        ax.text(-0.18, 1.08, letter, transform=ax.transAxes, fontsize=8, fontweight="bold", color=INK)
    sns.despine(ax=axes[0]); sns.despine(ax=axes[2]); sns.despine(ax=axes[3])
    _warning(fig, summary)
    fig.tight_layout(rect=(0, 0, 1, 0.94 if _classification(summary) == SYNTHETIC else 1))
    return _save(fig, out_dir, "metric-conditioned-tradeoff-rank-generalization", formats)


def _validate_summary(summary: Mapping[str, Any]) -> None:
    if summary.get("schema") != SUMMARY_SCHEMA:
        raise ValueError(f"expected {SUMMARY_SCHEMA}")
    if "data_classification" not in summary.get("provenance", {}):
        raise ValueError("figure data requires an explicit data classification")
    if _classification(summary) not in {SYNTHETIC, EXPERIMENTAL}:
        raise ValueError("unknown data classification")
    arms = [item["id"] for item in summary.get("arms", [])]
    if len(arms) != 3 or len(set(arms)) != 3:
        raise ValueError("metric-conditioned figure data requires exactly three arms")
    loss_ids = summary.get("cross_evaluation", {}).get("loss_ids", [])
    if len(loss_ids) != 3 or len(set(loss_ids)) != 3:
        raise ValueError("metric-conditioned figure data requires exactly three losses")
    for arm in arms:
        trajectory = summary.get("optimization_trajectories", {}).get(arm, [])
        if not any(isinstance(item.get("loss"), (int, float)) for item in trajectory):
            raise ValueError(f"missing development trajectory for {arm}")
        for loss_id in loss_ids:
            value = summary["cross_evaluation"]["values"][arm].get(loss_id)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f"non-finite cross-evaluation loss for {arm}/{loss_id}")
            rank = summary["rank_reversal"]["columns"][f"loss:{loss_id}"]["ranks"].get(arm)
            if not isinstance(rank, (int, float)) or not math.isfinite(float(rank)):
                raise ValueError(f"missing loss rank for {arm}/{loss_id}")
        for metric_id in (
            "active-researcher-fraction",
            "review-burden-per-active-researcher",
        ):
            metric = summary.get("held_out_metrics", {}).get(arm, {}).get(metric_id, {})
            if not metric.get("complete") or not isinstance(metric.get("mean"), (int, float)):
                raise ValueError(f"missing complete held-out metric for {arm}/{metric_id}")
        gap = summary.get("generalization", {}).get(arm, {}).get(
            "generalization_gap_held_out_minus_optimization"
        )
        if not isinstance(gap, (int, float)) or not math.isfinite(float(gap)):
            raise ValueError(f"missing generalization gap for {arm}")


def render(summary: Mapping[str, Any], out_dir: Path, formats=("pdf", "png")) -> list[Path]:
    _validate_summary(summary)
    out_dir.mkdir(parents=True, exist_ok=True)
    nature_style()
    paths = []
    paths.extend(plot_cross_evaluation(summary, out_dir, formats))
    paths.extend(plot_trajectories(summary, out_dir, formats))
    paths.extend(plot_tradeoff_rank_generalization(summary, out_dir, formats))
    return paths


def _is_paper_results_dir(path: Path) -> bool:
    resolved = path.resolve()
    expected = PAPER_RESULTS_DIR.resolve()
    return resolved == expected or expected in resolved.parents


def _assignment(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("campaign state must be ARM=PATH")
    arm, path = value.split("=", 1)
    return arm, Path(path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--campaign-state", action="append", default=[], type=_assignment)
    parser.add_argument("--classification", choices=("experimental", "synthetic-test"), default="experimental")
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--formats", default="pdf,png")
    args = parser.parse_args(argv)
    value = json.loads(args.input.read_text(encoding="utf-8"))
    requested = SYNTHETIC if args.classification == "synthetic-test" else EXPERIMENTAL
    if value.get("schema") == SUMMARY_SCHEMA:
        summary = value
        if _classification(summary) != requested:
            raise ValueError("requested classification does not match summary provenance")
    else:
        states = {
            arm: json.loads(path.read_text(encoding="utf-8"))
            for arm, path in args.campaign_state
        }
        summary = normalize_report(value, states, classification=requested)
    if requested == SYNTHETIC and _is_paper_results_dir(args.out_dir):
        raise ValueError(
            "synthetic fixtures may not be rendered into the paper results directory"
        )
    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    formats = tuple(item.strip() for item in args.formats.split(",") if item.strip())
    for path in render(summary, args.out_dir, formats=formats):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
