"""Render the frozen development-stage metric-conditioned optimization result.

This figure intentionally stops at the winner freeze.  It reads the compact,
tracked optimization result and never reads or creates held-out artifacts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from scripts.figures.visual_utils import nature_style


SCHEMA = "scienceutopia.metric-conditioned-optimization-result.v1"
ARM_COLORS = ("#176B87", "#B26A1B", "#76529B")


def _arm_label(campaign_id: str) -> str:
    if "participation" in campaign_id:
        return "Participation + review"
    if "topic" in campaign_id:
        return "Topic diversity proxy"
    if "burden" in campaign_id:
        return "Review burden proxy"
    return campaign_id


def _validate(result: dict[str, Any]) -> None:
    if result.get("schema") != SCHEMA:
        raise ValueError("unexpected metric-conditioned result schema")
    budget = result.get("study", {}).get("budget", {})
    if budget != {
        "arms": 3,
        "suggestions_per_arm": 5,
        "optimization_seeds_per_suggestion": 3,
        "logical_runs": 45,
    }:
        raise ValueError("figure requires the frozen 3 x 5 x 3 study budget")
    arms = result.get("arms", [])
    if len(arms) != 3 or any(len(arm.get("suggestions", [])) != 5 for arm in arms):
        raise ValueError("figure requires three complete five-suggestion traces")
    firewall = result.get("seed_firewall", {})
    if firewall.get("held_out_consumed") is not False or firewall.get("held_out_rows") != 0:
        raise ValueError("refuse to render development-only figure after held-out use")


def render(result: dict[str, Any], output_prefix: Path) -> list[Path]:
    _validate(result)
    nature_style()
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
    fig, axes = plt.subplots(1, 3, figsize=(7.45, 2.95))

    for index, (ax, arm) in enumerate(zip(axes, result["arms"])):
        suggestions = arm["suggestions"]
        valid = [item for item in suggestions if item["loss"] is not None]
        invalid = [item for item in suggestions if item["loss"] is None]
        valid_x = np.array([item["proposal_index"] + 1 for item in valid])
        valid_y = np.array([item["loss"] for item in valid])

        ax.axvspan(0.5, 3.5, color="#EAF1F4", alpha=0.8, linewidth=0)
        ax.axvspan(3.5, 5.5, color="#F4F0E8", alpha=0.8, linewidth=0)
        ax.plot(valid_x, valid_y, color=ARM_COLORS[index], linewidth=1.25, alpha=0.9)
        ax.scatter(
            valid_x,
            valid_y,
            s=28,
            color=ARM_COLORS[index],
            edgecolor="white",
            linewidth=0.55,
            zorder=4,
        )

        invalid_x = [item["proposal_index"] + 1 for item in invalid]
        if invalid_x:
            ax.scatter(
                invalid_x,
                [0.08] * len(invalid_x),
                transform=ax.get_xaxis_transform(),
                marker="x",
                s=28,
                color="#B23A3A",
                linewidth=1.1,
                clip_on=False,
                zorder=5,
            )
            for x_value in invalid_x:
                ax.text(
                    x_value,
                    0.145,
                    "invalid",
                    transform=ax.get_xaxis_transform(),
                    rotation=90,
                    ha="center",
                    va="bottom",
                    fontsize=4.5,
                    color="#8B3030",
                )

        winner = min(
            (item for item in valid),
            key=lambda item: (item["loss"], item["proposal_index"]),
        )
        ax.scatter(
            winner["proposal_index"] + 1,
            winner["loss"],
            marker="*",
            s=105,
            color="#17212B",
            edgecolor="white",
            linewidth=0.7,
            zorder=6,
        )
        ax.annotate(
            f"winner C{winner['proposal_index'] + 1}",
            (winner["proposal_index"] + 1, winner["loss"]),
            xytext=(4, 8),
            textcoords="offset points",
            fontsize=5.3,
            color="#17212B",
        )
        ax.set_title(_arm_label(arm["campaign_id"]), fontsize=7.2, fontweight="bold")
        ax.set_xticks(range(1, 6))
        ax.set_xlim(0.5, 5.5)
        ax.set_xlabel("Candidate (C1-C3 initial; C4-C5 adaptive)", fontsize=5.7)
        ax.grid(axis="y", color="#D7DEE3", linewidth=0.45)
        sns.despine(ax=ax)
        if index == 0:
            ax.set_ylabel("Development loss (lower is better)", fontsize=6.2)
        ax.text(
            0.02,
            0.96,
            "initial",
            transform=ax.transAxes,
            va="top",
            fontsize=4.8,
            color="#52616B",
        )
        ax.text(
            0.70,
            0.96,
            "adaptive",
            transform=ax.transAxes,
            va="top",
            fontsize=4.8,
            color="#6A604D",
        )
        ax.text(-0.14, 1.08, chr(ord("a") + index), transform=ax.transAxes,
                fontsize=8, fontweight="bold")

    audit = result["runtime_audit"]
    fig.suptitle(
        "Metric-conditioned optimization: frozen development-stage outcomes",
        x=0.07,
        y=0.985,
        ha="left",
        fontsize=9.2,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.008,
        "DEVELOPMENT SPLIT ONLY - held-out seeds unused   |   "
        f"{audit['logical_complete']} valid + {audit['logical_failed']} technical failures   |   "
        f"{audit['physically_executed_rows']} executed + {audit['adopted_complete_rows']} provenance-adopted rows   |   "
        f"{audit['serial_wall_hours']:.2f} serial hours",
        ha="center",
        va="bottom",
        fontsize=5.6,
        color="#17212B",
        bbox={"facecolor": "#F2D66D", "edgecolor": "none", "pad": 3.0},
    )
    fig.subplots_adjust(left=0.075, right=0.985, top=0.80, bottom=0.25, wspace=0.38)

    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    outputs = []
    for suffix in ("pdf", "png"):
        path = output_prefix.with_suffix(f".{suffix}")
        kwargs: dict[str, Any] = {"dpi": 300, "bbox_inches": "tight"}
        if suffix == "pdf":
            kwargs["metadata"] = {
                "Creator": "Science Utopia Lab",
                "CreationDate": None,
                "ModDate": None,
            }
        fig.savefig(path, **kwargs)
        outputs.append(path)
    plt.close(fig)
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--result",
        type=Path,
        default=Path("research/results/metric-conditioned-optimization-v1-1.json"),
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=Path("paper/figures/metric-conditioned/optimization-stage"),
    )
    args = parser.parse_args(argv)
    result = json.loads(args.result.read_text(encoding="utf-8"))
    for path in render(result, args.output_prefix):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
