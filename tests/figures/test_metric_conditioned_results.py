import json
from pathlib import Path

import matplotlib.image as mpimg
import pytest

from scripts.figures.metric_conditioned_results import (
    ARM_ORDER,
    EXPERIMENTAL,
    REPORT_SCHEMA,
    SUMMARY_SCHEMA,
    SYNTHETIC,
    main,
    normalize_report,
    render,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/metric-conditioned-figure-data.synthetic-test.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _campaign_state(arm, losses):
    return {
        "suggestions": [
            {
                "suggestion": {
                    "proposal_index": index,
                    "phase": "initial" if index < 2 else "adaptive",
                    "suggestion_id": f"synthetic-{arm}-{index}",
                },
                "status": "observed_complete",
                "observation": {"loss": loss},
            }
            for index, loss in enumerate(losses)
        ]
    }


def _source_report():
    arms = ARM_ORDER
    loss_ids = ("loss-a", "loss-b", "loss-c")
    profiles = {}
    for index, arm in enumerate(arms):
        profiles[arm] = [
            {
                "id": "active-researcher-fraction",
                "slice": None,
                "direction": "maximize",
                "summary": {"mean": 0.8 - index * 0.1, "population_sd": 0.01},
                "complete": True,
            },
            {
                "id": "review-burden-per-active-researcher",
                "slice": None,
                "direction": "minimize",
                "summary": {"mean": 0.5 + index * 0.2, "population_sd": 0.02},
                "complete": True,
            },
        ]
    return {
        "schema": REPORT_SCHEMA,
        "study_id": "synthetic-metric-conditioned-study",
        "study_revision": "synthetic-test-only",
        "provenance": {"data_classification": SYNTHETIC},
        "loss_by_frozen_winner": {
            arm: {
                loss_id: {"loss": float(row + column) / 10}
                for column, loss_id in enumerate(loss_ids)
            }
            for row, arm in enumerate(arms)
        },
        "held_out_metric_profiles": profiles,
        "analyses": {
            "rank_reversal": {
                "columns": {
                    f"loss:{loss_id}": {
                        "ranks": {arm: float((index + shift) % 3 + 1) for index, arm in enumerate(arms)}
                    }
                    for shift, loss_id in enumerate(loss_ids)
                }
            },
            "paired_tradeoffs": [{"synthetic": True}],
            "gaming_flags": [{"signature": "synthetic-only", "triggered": False}],
            "generalization": {
                arm: {"generalization_gap_held_out_minus_optimization": 0.01 * (index + 1)}
                for index, arm in enumerate(arms)
            },
            "secondary_resolution": {
                "synthetic": {"label": "synthetic-test-only", "low_resolution": False}
            },
        },
    }


def test_normalize_report_preserves_analysis_and_builds_trajectories():
    report = _source_report()
    states = {
        arm: _campaign_state(arm, [0.5, 0.4, 0.45, 0.3, 0.35])
        for arm in ARM_ORDER
    }

    summary = normalize_report(report, states, classification=SYNTHETIC)

    assert summary["schema"] == SUMMARY_SCHEMA
    assert summary["provenance"]["data_classification"] == SYNTHETIC
    assert len(summary["provenance"]["source_report_sha256"]) == 64
    assert set(summary["provenance"]["source_campaign_state_sha256"]) == set(ARM_ORDER)
    assert all(
        len(value) == 64
        for value in summary["provenance"]["source_campaign_state_sha256"].values()
    )
    assert summary["optimization_trajectories"][ARM_ORDER[0]][-1]["incumbent_loss"] == 0.3
    assert summary["cross_evaluation"]["values"][ARM_ORDER[1]]["loss-c"] == 0.3
    assert summary["gaming_flags"] == report["analyses"]["gaming_flags"]
    assert summary["secondary_resolution"] == report["analyses"]["secondary_resolution"]


def test_normalize_requires_all_arm_trajectories():
    with pytest.raises(ValueError, match="missing optimization trajectories"):
        normalize_report(_source_report(), {}, classification=SYNTHETIC)


def test_synthetic_source_cannot_be_relabelled_experimental():
    with pytest.raises(ValueError, match="cannot be rendered as an experimental result"):
        normalize_report(_source_report(), {}, classification=EXPERIMENTAL)


def test_synthetic_fixture_renders_three_watermarked_pngs(tmp_path):
    summary = _load(FIXTURE)
    outputs = render(summary, tmp_path, formats=("png",))

    assert [path.name for path in outputs] == [
        "metric-conditioned-cross-evaluation.png",
        "metric-conditioned-objective-trajectories.png",
        "metric-conditioned-tradeoff-rank-generalization.png",
    ]
    assert all(path.stat().st_size > 10_000 for path in outputs)
    # The warning banner is a red-dominant region in the top portion of every image.
    for path in outputs:
        image = mpimg.imread(path)
        top = image[: max(1, image.shape[0] // 8), :, :3]
        assert ((top[:, :, 0] > 0.45) & (top[:, :, 0] > top[:, :, 1] * 1.4)).any()


def test_render_fails_closed_on_missing_result(tmp_path):
    summary = _load(FIXTURE)
    summary["cross_evaluation"]["values"][ARM_ORDER[0]][
        "participation-review-tradeoff-probe"
    ] = None

    with pytest.raises(ValueError, match="non-finite cross-evaluation loss"):
        render(summary, tmp_path, formats=("png",))


def test_cli_rejects_classification_mismatch_and_paper_destination(tmp_path):
    with pytest.raises(ValueError, match="does not match summary provenance"):
        main([
            "--input", str(FIXTURE),
            "--classification", "experimental",
            "--out-dir", str(tmp_path),
            "--formats", "png",
        ])

    with pytest.raises(ValueError, match="paper results directory"):
        main([
            "--input", str(FIXTURE),
            "--classification", "synthetic-test",
            "--out-dir", str(ROOT / "paper/figures/metric-conditioned"),
            "--formats", "png",
        ])


def test_paper_boundary_requires_complete_figure_set():
    boundary = (ROOT / "paper/metric_conditioned_results.tex").read_text(
        encoding="utf-8"
    )
    assert boundary.count("\\IfFileExists") == 3
    assert "metricconditionedresultstrue" in boundary
    assert "No synthetic fixture" in boundary
    assert "tests/fixtures" not in boundary
    main_tex = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
    assert "\\input{metric_conditioned_results}" in main_tex
