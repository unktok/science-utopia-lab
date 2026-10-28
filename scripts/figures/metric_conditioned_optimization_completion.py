"""Render the development-only metric-conditioned completion figure."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from scripts.figures.visual_utils import nature_style
from utopia.optimization.metric_conditioned_completion import validate_completion_report


SYNTHETIC = "synthetic_test_fixture"
COLORS = ("#136F8A", "#B06A15", "#7B4A9E")


def _label(arm: str) -> str:
    if "participation" in arm:
        return "Participation–review"
    if "topic" in arm:
        return "Topic entropy proxy"
    if "burden" in arm:
        return "Review burden proxy"
    return arm


def _loss_label(loss_id: str) -> str:
    return loss_id.replace("-tradeoff-probe", " trade-off").replace(
        "-diversity-probe", " diversity"
    ).replace("-burden-probe", " burden")


def _warning(fig, report: Mapping[str, Any]) -> None:
    if report["data_classification"] == SYNTHETIC:
        text = "SYNTHETIC TEST FIXTURE - NOT AN EXPERIMENTAL RESULT"
        color = "white"
        face = "#A61B1B"
    else:
        text = "DEVELOPMENT SPLIT ONLY - HELD-OUT SEEDS VERIFIED UNUSED"
        color = "#17212B"
        face = "#F2D66D"
    fig.text(
        0.5, 0.995, text, ha="center", va="top", fontsize=7, color=color,
        fontweight="bold", bbox={"facecolor": face, "edgecolor": "none", "pad": 2.8},
    )


def render_completion_figure(
    report: Mapping[str, Any], out_dir: Path, formats=("pdf", "png")
) -> list[Path]:
    validate_completion_report(report)
    out_dir.mkdir(parents=True, exist_ok=True)
    nature_style()
    # Use the bundled font deterministically. Some macOS Helvetica variants are
    # present in font discovery but fail glyph loading in headless Agg renders.
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    arms = list(report["arms"])
    loss_ids = list(report["development_cross_objective"]["candidate_rankings"])
    fig = plt.figure(figsize=(8.0, 5.35))
    grid = fig.add_gridspec(2, 3, height_ratios=(1.15, 1), hspace=0.62, wspace=0.46)
    panel_axes = []

    for index, arm in enumerate(arms):
        ax = fig.add_subplot(grid[0, index])
        panel_axes.append(ax)
        arm_report = report["arms"][arm]
        own_loss = arm_report["loss_spec"]["id"]
        candidates = arm_report["candidates"]
        x = np.array([item["proposal_index"] + 1 for item in candidates])
        means = np.array([
            item["cross_objective_losses"][own_loss]["mean"] for item in candidates
        ])
        dispersions = np.array([
            item["cross_objective_losses"][own_loss]["population_sd"]
            for item in candidates
        ])
        aggregate = np.array([
            item["cross_objective_losses"][own_loss]["loss"] for item in candidates
        ])
        ax.errorbar(
            x, means, yerr=dispersions, fmt="o", color=COLORS[index],
            ecolor=COLORS[index], elinewidth=0.9, capsize=2, markersize=4,
            alpha=0.76, label="seed mean +/- pop. SD",
        )
        ax.plot(x, aggregate, color=COLORS[index], linewidth=1.15, label="selection loss")
        for candidate in candidates:
            modes = candidate["execution_provenance"]
            if modes.get("adopted", 0):
                ax.scatter(
                    candidate["proposal_index"] + 1,
                    candidate["cross_objective_losses"][own_loss]["mean"],
                    s=28, facecolors="none", edgecolors="#17212B", linewidths=0.8,
                    zorder=5,
                )
        winner_key = arm_report["frozen_winner_candidate_key"]
        winner = next(item for item in candidates if item["candidate_key"] == winner_key)
        ax.scatter(
            winner["proposal_index"] + 1,
            winner["cross_objective_losses"][own_loss]["loss"],
            marker="*", s=80, color="#17212B", edgecolor="white", linewidth=0.5,
            zorder=6, label="frozen winner",
        )
        ax.axvline(3.5, color="#8A96A3", linestyle=":", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xlabel("Candidate (1-3 initial; 4-5 adaptive)")
        ax.set_title(_label(arm), fontsize=7, pad=5)
        ax.grid(axis="y", color="#DDE2E6", linewidth=0.5)
        sns.despine(ax=ax)
        if index == 0:
            ax.set_ylabel("Development loss\n(arm-specific units)")
            ax.text(
                0.02, 0.02, "line: aggregate | bars: seed SD | *: frozen",
                transform=ax.transAxes, fontsize=4.5, color="#52616B",
            )

    matrix_ax = fig.add_subplot(grid[1, :2])
    panel_axes.append(matrix_ax)
    frozen = report["development_cross_objective"]["frozen_winner_matrix"]
    matrix = np.array([
        [frozen[arm][loss_id]["loss"] for loss_id in loss_ids] for arm in arms
    ])
    ranks = np.zeros_like(matrix)
    for column in range(len(loss_ids)):
        order = np.argsort(matrix[:, column], kind="stable")
        for rank, row in enumerate(order, start=1):
            ranks[row, column] = rank
    annotations = np.array([
        [
            f"{matrix[row, column]:.3f}\nrank {int(ranks[row, column])}"
            for column in range(len(loss_ids))
        ]
        for row in range(len(arms))
    ])
    sns.heatmap(
        ranks, annot=annotations, fmt="", cmap="mako_r", vmin=1, vmax=3,
        linewidths=0.5, linecolor="white", cbar_kws={"label": "Within-objective rank"},
        xticklabels=[_loss_label(item) for item in loss_ids],
        yticklabels=[_label(item) for item in arms], ax=matrix_ax,
    )
    reversals = report["development_cross_objective"]["winner_reversals"]
    matrix_ax.set_title(
        "Frozen development winners: cross-objective ranks"
        + (" (reversal observed)" if reversals else " (no reversal observed)"),
        pad=6,
    )
    matrix_ax.set_xlabel("Loss used for development cross-scoring")
    matrix_ax.set_ylabel("Objective that selected the system")
    matrix_ax.tick_params(axis="x", rotation=18)
    matrix_ax.tick_params(axis="y", rotation=0)

    provenance_ax = fig.add_subplot(grid[1, 2])
    panel_axes.append(provenance_ax)
    executed = [report["arms"][arm]["execution"]["executed_runs"] for arm in arms]
    adopted = [report["arms"][arm]["execution"]["adopted_runs"] for arm in arms]
    positions = np.arange(len(arms))
    provenance_ax.bar(positions, executed, color="#377D8C", width=0.62, label="executed")
    provenance_ax.bar(
        positions, adopted, bottom=executed, color="#D5A64A", width=0.62,
        label="adopted",
    )
    for position, total in zip(positions, np.array(executed) + np.array(adopted)):
        provenance_ax.text(position, total + 0.35, str(int(total)), ha="center", fontsize=6)
    provenance_ax.set_ylim(0, max(np.array(executed) + np.array(adopted)) + 3)
    provenance_ax.set_xticks(positions, ["Part.", "Topic", "Burden"])
    provenance_ax.set_ylabel("Logical development runs")
    provenance_ax.set_title(
        f"45 logical = {report['execution']['executed_runs']} executed + "
        f"{report['execution']['adopted_runs']} adopted",
        fontsize=6.8, pad=18,
    )
    provenance_ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, 1.035), ncol=2, frameon=False,
        fontsize=5.1, handlelength=1.0, columnspacing=0.8,
    )
    provenance_ax.grid(axis="y", color="#DDE2E6", linewidth=0.5)
    sns.despine(ax=provenance_ax)
    provenance_ax.text(
        0.5, -0.28, "Held-out registry/snapshot/report: absent",
        transform=provenance_ax.transAxes, ha="center", fontsize=5.7,
        color="#365466", fontweight="bold",
    )

    for ax, label in zip(panel_axes, "abcde"):
        ax.text(-0.17, 1.08, label, transform=ax.transAxes, fontsize=8, fontweight="bold")
    _warning(fig, report)
    winner_designs = {
        next(
            item["design_id"] for item in value["candidates"]
            if item["candidate_key"] == value["frozen_winner_candidate_key"]
        )
        for value in report["arms"].values()
    }
    outcome = (
        f"{len(winner_designs)} systems selected by 3 objectives"
        if len(winner_designs) > 1
        else "same system selected by all 3 objectives"
    )
    fig.suptitle(
        f"Metric-conditioned optimization completion: {outcome}",
        x=0.06, y=0.955, ha="left", fontsize=9, fontweight="bold",
    )
    outputs = []
    for extension in formats:
        path = out_dir / f"metric-conditioned-optimization-completion.{extension}"
        kwargs: dict[str, Any] = {"dpi": 300, "bbox_inches": "tight"}
        if extension == "pdf":
            kwargs["metadata"] = {
                "Creator": "Science Utopia Lab optimization completion pipeline",
                "CreationDate": None,
                "ModDate": None,
            }
        fig.savefig(path, **kwargs)
        outputs.append(path)
    plt.close(fig)
    return outputs
