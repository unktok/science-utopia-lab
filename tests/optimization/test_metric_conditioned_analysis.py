import pytest

from utopia.optimization.metric_conditioned_analysis import build_analyses


SEEDS = [701, 709, 719, 727, 733]


def _profile(metric_id, direction, base, *, slice_id=None):
    values = [base - 0.02, base - 0.01, base, base + 0.01, base + 0.02]
    return {
        "id": metric_id,
        "slice": slice_id,
        "direction": direction,
        "seed_values": [
            {"seed": seed, "status": "measured", "value": value}
            for seed, value in zip(SEEDS, values)
        ],
        "summary": {"mean": base},
        "structured_summary": {},
        "complete": True,
    }


def _loss(base, own=False):
    return {
        "status": "complete",
        "loss": base,
        "is_own_loss": own,
        "held_out_seed_values": [
            {"seed": seed, "loss": base + offset}
            for seed, offset in zip(SEEDS, (-0.02, -0.01, 0, 0.01, 0.02))
        ],
    }


def test_full_metric_conditioned_analysis_structure_and_flags():
    profiles = {
        "arm-a": [
            _profile("active-researcher-fraction", "maximize", 0.9),
            _profile(
                "active-researcher-fraction", "maximize", 0.5,
                slice_id="low-resource-researchers",
            ),
            _profile("topic-entropy", "observe", 1.0),
            _profile("review-burden-per-active-researcher", "minimize", 1.0),
            _profile("review-coverage", "maximize", 0.9),
            _profile("submission-count", "observe", 10),
            _profile("accepted-paper-count", "observe", 3),
        ],
        "arm-b": [
            _profile("active-researcher-fraction", "maximize", 0.6),
            _profile(
                "active-researcher-fraction", "maximize", 0.7,
                slice_id="low-resource-researchers",
            ),
            _profile("topic-entropy", "observe", 1.5),
            _profile("review-burden-per-active-researcher", "minimize", 1.2),
            _profile("review-coverage", "maximize", 0.8),
            _profile("submission-count", "observe", 8),
            _profile("accepted-paper-count", "observe", 2),
        ],
        "arm-c": [
            _profile("active-researcher-fraction", "maximize", 0.7),
            _profile(
                "active-researcher-fraction", "maximize", 0.6,
                slice_id="low-resource-researchers",
            ),
            _profile("topic-entropy", "observe", 0.8),
            _profile("review-burden-per-active-researcher", "minimize", 0.5),
            _profile("review-coverage", "maximize", 0.4),
            _profile("submission-count", "observe", 5),
            _profile("accepted-paper-count", "observe", 1),
        ],
    }
    losses = {
        "arm-a": {"loss-a": _loss(0.3, True), "loss-b": _loss(0.8), "loss-c": _loss(0.7)},
        "arm-b": {"loss-a": _loss(0.6), "loss-b": _loss(0.2, True), "loss-c": _loss(0.9)},
        "arm-c": {"loss-a": _loss(0.5), "loss-b": _loss(0.7), "loss-c": _loss(0.1, True)},
    }
    freeze = {
        "winners": [
            {
                "campaign_id": arm,
                "loss_spec": {"id": loss_id},
                "optimization_observation": {"loss": optimization},
            }
            for arm, loss_id, optimization in (
                ("arm-a", "loss-a", 0.2),
                ("arm-b", "loss-b", 0.1),
                ("arm-c", "loss-c", 0.05),
            )
        ]
    }

    analysis = build_analyses(freeze=freeze, profiles=profiles, losses=losses)

    ranking = analysis["rank_reversal"]["columns"]
    assert ranking["active-researcher-fraction"]["raw_order"][0] == "arm-a"
    assert ranking["loss:loss-c"]["raw_order"][0] == "arm-c"
    assert analysis["rank_reversal"]["own_loss_check"]["arm-b"][
        "own_winner_remains_best"
    ] is True
    triggered = {
        item["signature"]
        for item in analysis["gaming_flags"]
        if item["triggered"]
    }
    assert "burden_without_coverage_or_activity" in triggered
    assert "entropy_without_participation_or_activity" in triggered
    assert "aggregate_participation_distributional_tradeoff" in triggered
    assert analysis["generalization"]["arm-a"][
        "generalization_gap_held_out_minus_optimization"
    ] == pytest.approx(0.1)
    assert analysis["paired_tradeoffs"]
    assert all(
        "low_resolution" in item
        for item in analysis["secondary_resolution"].values()
    )
