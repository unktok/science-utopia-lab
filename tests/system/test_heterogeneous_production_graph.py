from __future__ import annotations

from dataclasses import replace
import json

import pytest

from utopia.system import (
    ArtifactTypeSpec,
    ChannelKind,
    ConnectionSpec,
    DeterministicGraphRunner,
    GraphCheckpoint,
    GraphRuntimeError,
    MechanismFamily,
    MechanismRegistry,
    MechanismResult,
    MechanismSpec,
    MechanismValue,
    PortSpec,
    ScheduleSpec,
    SystemSpec,
)
from utopia.system.production import (
    COMPACT_RANKED_ALLOCATION,
    CONFERENCE_ACCEPTANCE,
    PAPER_TRACKER_PUBLICATION,
    register_production_mechanisms,
)


SYSTEM_INPUT_SOURCE = "test.heterogeneous-system-input-source-v1"


def _system() -> SystemSpec:
    return SystemSpec(
        "heterogeneous-production-system",
        1,
        artifact_types=(
            ArtifactTypeSpec("review-batch"),
            ArtifactTypeSpec("paper-decision"),
            ArtifactTypeSpec("publication-record"),
            ArtifactTypeSpec("funding-panel"),
            ArtifactTypeSpec("resource-allocation"),
        ),
        mechanisms=(
            MechanismSpec(
                "system-inputs",
                MechanismFamily.CUSTOM,
                SYSTEM_INPUT_SOURCE,
                outputs=(
                    PortSpec("review_batches", ChannelKind.ARTIFACT, "review-batch"),
                    PortSpec("funding_panels", ChannelKind.ARTIFACT, "funding-panel"),
                ),
            ),
            MechanismSpec(
                "conference-evaluation",
                MechanismFamily.EVALUATION,
                CONFERENCE_ACCEPTANCE,
                inputs=(
                    PortSpec("review_batches", ChannelKind.ARTIFACT, "review-batch"),
                ),
                outputs=(
                    PortSpec("decisions", ChannelKind.DECISION, "paper-decision"),
                ),
                parameters={
                    "acceptance_rate": 0.5,
                    "acceptance_mode": "fixed_slots",
                    "tiebreak_seed": 2718,
                },
            ),
            MechanismSpec(
                "publication-record",
                MechanismFamily.PUBLICATION,
                PAPER_TRACKER_PUBLICATION,
                inputs=(
                    PortSpec("decisions", ChannelKind.DECISION, "paper-decision"),
                ),
                outputs=(
                    PortSpec("records", ChannelKind.ARTIFACT, "publication-record"),
                ),
            ),
            MechanismSpec(
                "ranked-funding",
                MechanismFamily.FUNDING,
                COMPACT_RANKED_ALLOCATION,
                inputs=(
                    PortSpec("panels", ChannelKind.ARTIFACT, "funding-panel"),
                ),
                outputs=(
                    PortSpec(
                        "allocations", ChannelKind.RESOURCE, "resource-allocation"
                    ),
                ),
                parameters={"award_slots": 1, "award_amount": 25},
            ),
        ),
        connections=(
            ConnectionSpec(
                "system-inputs",
                "review_batches",
                "conference-evaluation",
                "review_batches",
                ChannelKind.ARTIFACT,
                latency=1,
            ),
            ConnectionSpec(
                "conference-evaluation",
                "decisions",
                "publication-record",
                "decisions",
                ChannelKind.DECISION,
                latency=1,
            ),
            ConnectionSpec(
                "system-inputs",
                "funding_panels",
                "ranked-funding",
                "panels",
                ChannelKind.ARTIFACT,
                latency=1,
            ),
        ),
        schedules=(
            ScheduleSpec("system-inputs", 0),
            ScheduleSpec("conference-evaluation", 1),
            ScheduleSpec("ranked-funding", 1),
            ScheduleSpec("publication-record", 2),
        ),
    )


def _paper(period: int, index: int) -> dict:
    return {
        "id": f"paper-{period}-{index}",
        "title": f"Paper {period}-{index}",
        "abstract": f"Deterministic abstract {period}-{index}",
        "author_id": f"researcher-{period}-{index}",
        "author_type": "researcher",
        "year": period + 1,
        "conference": "science-conf",
        "topics": ["science-of-science"],
        "tags": ["cs.CY"],
        "project_start_year": period,
        "project_end_year": period + 1,
        "maturity": 1,
        "type": "submission",
        "status": "pending",
    }


def _registry() -> MechanismRegistry:
    registry = MechanismRegistry()

    def inputs(context):
        period = context.period
        paper_count = 2 if period % 2 == 0 else 3
        papers = [_paper(period, index) for index in range(paper_count)]
        review_batch = {
            "batch_id": f"reviews-{period}",
            "conference_id": "science-conf",
            "conference_name": "Science Conference",
            "topics": ["science-of-science"],
            "papers": papers,
            "reviews": {
                paper["id"]: [
                    {
                        "reviewer_id": f"reviewer-{index}",
                        "overall_score": 5 - index,
                        "justification": "deterministic fixture",
                    }
                ]
                for index, paper in enumerate(papers)
            },
        }
        funding_panel = {
            "panel_id": f"funding-{period}",
            "applications": [
                {"applicant_id": f"researcher-{period}-0"},
                {"applicant_id": f"researcher-{period}-1"},
            ],
            "compact_result": {"ranked_application_ids": [1, 0]},
        }
        return MechanismResult(
            outputs={
                "review_batches": (
                    MechanismValue(
                        review_batch,
                        artifact_ids=(review_batch["batch_id"],),
                    ),
                ),
                "funding_panels": (
                    MechanismValue(
                        funding_panel,
                        artifact_ids=(funding_panel["panel_id"],),
                    ),
                ),
            }
        )

    registry.register(SYSTEM_INPUT_SOURCE, 1, inputs)
    register_production_mechanisms(registry)
    return registry


def test_three_production_families_compose_and_resume_deterministically() -> None:
    spec = _system()
    uninterrupted = DeterministicGraphRunner(spec, _registry()).run(periods=4)

    first = DeterministicGraphRunner(spec, _registry()).run(periods=2)
    serialized = json.loads(json.dumps(first.checkpoint.to_dict(), sort_keys=True))
    resumed = DeterministicGraphRunner(spec, _registry()).run(
        periods=2,
        checkpoint=GraphCheckpoint.from_dict(serialized),
    )

    assert [event.to_dict() for event in (*first.events, *resumed.events)] == [
        event.to_dict() for event in uninterrupted.events
    ]
    assert (*first.trace, *resumed.trace) == uninterrupted.trace
    assert resumed.checkpoint.to_dict() == uninterrupted.checkpoint.to_dict()

    states = resumed.checkpoint.mechanism_states
    assert set(states) == {
        "conference-evaluation",
        "publication-record",
        "ranked-funding",
    }
    evaluation = states["conference-evaluation"]
    assert evaluation["processed_batch_ids"] == [
        "reviews-0",
        "reviews-1",
        "reviews-2",
    ]
    assert evaluation["fixed_slots_by_conference"] == {"science-conf": 1}
    assert evaluation["decision_counts"] == {"accept": 3, "reject": 4}

    publication = states["publication-record"]
    assert publication["status_counts"] == {"accept": 2, "reject": 3}
    assert len(publication["papers"]) == 5
    assert all(len(paper["review_history"]) == 1 for paper in publication["papers"])

    funding = states["ranked-funding"]
    assert funding["processed_panel_ids"] == [
        "funding-0",
        "funding-1",
        "funding-2",
    ]
    assert funding["total_awarded"] == 75.0

    assert first.pending_deliveries == 4
    assert resumed.pending_deliveries == 4
    assert {mechanism.family for mechanism in spec.mechanisms} >= {
        MechanismFamily.EVALUATION,
        MechanismFamily.PUBLICATION,
        MechanismFamily.FUNDING,
    }


def test_fixed_slots_are_native_state_across_different_batch_sizes() -> None:
    result = DeterministicGraphRunner(_system(), _registry()).run(periods=3)
    decisions = [
        event.payload
        for event in result.events
        if event.event_type == "evaluation.paper_decided"
    ]

    by_batch: dict[str, list[dict]] = {}
    for decision in decisions:
        by_batch.setdefault(decision["batch_id"], []).append(decision)
    assert len(by_batch["reviews-0"]) == 2
    assert len(by_batch["reviews-1"]) == 3
    assert sum(item["decision"] == "accept" for item in by_batch["reviews-0"]) == 1
    assert sum(item["decision"] == "accept" for item in by_batch["reviews-1"]) == 1


def test_exchanging_one_mechanism_changes_whole_system_identity() -> None:
    spec = _system()
    checkpoint = DeterministicGraphRunner(spec, _registry()).run(periods=1).checkpoint
    alternative_id = "test.alternative-evaluation-v1"
    changed = replace(
        spec,
        mechanisms=tuple(
            replace(mechanism, implementation=alternative_id)
            if mechanism.mechanism_id == "conference-evaluation"
            else mechanism
            for mechanism in spec.mechanisms
        ),
    )
    registry = _registry()
    registry.register(alternative_id, 1, lambda _context: MechanismResult())

    assert changed.fingerprint != spec.fingerprint
    with pytest.raises(GraphRuntimeError, match="fingerprint does not match"):
        DeterministicGraphRunner(changed, registry).run(
            periods=1,
            checkpoint=checkpoint,
        )
