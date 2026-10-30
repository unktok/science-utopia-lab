from __future__ import annotations

import json

import pytest

from utopia.optimization.blackbox import AdaptiveRandomSearch, evaluate_round
from utopia.optimization.loss import loss_spec_sha256
from utopia.optimization.structural_space import StructuralSelection
from utopia.optimization.whole_system_structural import (
    WHOLE_SYSTEM_ENGINEERING_LOSS_SPEC,
    execute_whole_system_structural_candidate,
    observe_whole_system_structural_suggestion,
    whole_system_engineering_loss,
    whole_system_structural_registry,
    whole_system_structural_space,
)
from utopia.system import (
    DeterministicGraphRunner,
    GraphCheckpoint,
    GraphRuntimeError,
    MechanismRegistry,
    validate_system_spec,
)


@pytest.fixture(scope="module")
def space():
    return whole_system_structural_space()


def _candidate(
    space,
    *,
    evaluation: str | None = None,
    publication: str | None = None,
    funding: str | None = None,
    government: str | None = None,
    communication: str | None = None,
    government_policy: str | None = None,
    knowledge_delivery: str | None = None,
) -> dict:
    return space.build(
        StructuralSelection(
            {
                "workload": "deterministic-v1",
                "knowledge-source": "deterministic-v1",
                "evaluation": evaluation,
                "publication": publication,
                "funding": funding,
                "government": government,
                "communication": communication,
                "research-receiver": "strict-receiver",
            },
            {
                "review-input": "instant" if evaluation else None,
                "publication-flow": "instant" if publication else None,
                "funding-input": "instant" if funding else None,
                "government-observation": "instant" if government and evaluation else None,
                "government-policy": government_policy,
                "knowledge-input": "instant" if communication else None,
                "knowledge-delivery": knowledge_delivery,
            },
        )
    ).to_dict()


def _full_candidate(space) -> dict:
    return _candidate(
        space,
        evaluation="conference-rate",
        publication="paper-tracker",
        funding="compact-ranked",
        government="event-responsive",
        communication="broadcast",
        government_policy="one-period",
        knowledge_delivery="instant",
    )


def test_joint_space_exposes_mechanism_absence_implementation_and_edges(space) -> None:
    assert space.candidate_count == 770
    assert len(
        {space.build(selection).fingerprint for selection in space.selections}
    ) == 770
    assert {selection.nodes["evaluation"] for selection in space.selections} == {
        None,
        "conference-rate",
        "conference-fixed-slots",
    }
    assert {selection.nodes["publication"] for selection in space.selections} == {
        None,
        "paper-tracker",
    }
    assert {selection.nodes["funding"] for selection in space.selections} == {
        None,
        "compact-ranked",
    }
    assert {selection.nodes["government"] for selection in space.selections} == {
        None,
        "event-responsive",
        "cumulative-threshold",
    }
    assert {selection.nodes["communication"] for selection in space.selections} == {
        None,
        "broadcast",
        "digest",
    }
    assert {selection.edges["government-policy"] for selection in space.selections} == {
        None,
        "one-period",
        "two-period",
    }
    assert {selection.edges["knowledge-delivery"] for selection in space.selections} == {
        None,
        "instant",
        "one-period",
    }
    assert all(validate_system_spec(space.build(selection)).valid for selection in space.selections)


def test_representative_systems_execute_and_keep_claim_boundaries(space) -> None:
    bare = execute_whole_system_structural_candidate(space, _candidate(space))
    full = execute_whole_system_structural_candidate(space, _full_candidate(space))
    alternative = execute_whole_system_structural_candidate(
        space,
        _candidate(
            space,
            evaluation="conference-fixed-slots",
            publication="paper-tracker",
            funding="compact-ranked",
            government="cumulative-threshold",
            communication="digest",
            government_policy="two-period",
            knowledge_delivery="one-period",
        ),
    )

    assert bare.summary.to_dict() == {
        "accepted": 0,
        "rejected": 0,
        "publication_records": 0,
        "funding_awards": 0,
        "total_awarded": 0,
        "government_policies": 0,
        "emitted_messages": 0,
        "received_knowledge_items": 0,
        "blocked_invocations": 0,
        "mechanism_count": 3,
        "connection_count": 0,
    }
    assert full.summary.accepted == 9
    assert full.summary.publication_records == 10
    assert full.summary.total_awarded == 100.0
    assert full.summary.government_policies == 4
    assert full.summary.received_knowledge_items == 8
    assert alternative.summary.accepted == 4
    assert alternative.summary.government_policies == 1
    assert alternative.summary.emitted_messages == 2
    assert alternative.summary.received_knowledge_items == 4
    assert whole_system_engineering_loss(full) != whole_system_engineering_loss(
        alternative
    )
    assert full.spec.metadata["objective_binding"] == "external-loss-spec"
    assert full.spec.metadata["held_out_metrics"] == "not-defined"
    assert full.spec.metadata["promotion_policy"] == "not-defined"


def test_checkpoint_resume_is_exact_for_joint_graph(space) -> None:
    spec = space.decode(_full_candidate(space))
    uninterrupted = DeterministicGraphRunner(
        spec, whole_system_structural_registry()
    ).run(periods=4)
    first = DeterministicGraphRunner(
        spec, whole_system_structural_registry()
    ).run(periods=2)
    checkpoint = GraphCheckpoint.from_dict(
        json.loads(json.dumps(first.checkpoint.to_dict(), sort_keys=True))
    )
    resumed = DeterministicGraphRunner(
        spec, whole_system_structural_registry()
    ).run(periods=2, checkpoint=checkpoint)

    assert [event.to_dict() for event in (*first.events, *resumed.events)] == [
        event.to_dict() for event in uninterrupted.events
    ]
    assert resumed.checkpoint.to_dict() == uninterrupted.checkpoint.to_dict()


def test_neighbors_cover_joint_structural_axes(space) -> None:
    candidates = (_candidate(space), _full_candidate(space))
    kinds = {
        mutation.kind
        for candidate in candidates
        for mutation, _neighbor in space.neighbors(candidate)
    }
    assert kinds == {
        "node-presence",
        "configuration",
        "implementation",
        "edge-presence",
        "latency",
    }


def test_black_box_round_uses_explicit_loss_spec_after_valid_execution(space) -> None:
    optimizer = AdaptiveRandomSearch(space, seed=211, initial_random=5)
    suggestions, observations = evaluate_round(
        optimizer,
        lambda suggestion: observe_whole_system_structural_suggestion(
            space, suggestion, periods=3
        ),
        count=5,
    )

    assert len(suggestions) == len(observations) == 5
    assert len({observation.loss for observation in observations}) > 1
    assert all(observation.status == "complete" for observation in observations)
    assert all(
        observation.metadata["loss_spec"]["sha256"]
        == loss_spec_sha256(WHOLE_SYSTEM_ENGINEERING_LOSS_SPEC)
        for observation in observations
    )
    assert all(
        observation.metadata["technical_validity"] == "complete"
        for observation in observations
    )
    assert all(
        observation.metadata["measurement_role"]
        == "synthetic-optimization-development"
        for observation in observations
    )


def test_technical_failure_is_not_converted_to_a_loss(space) -> None:
    optimizer = AdaptiveRandomSearch(space, seed=7, initial_random=1)
    suggestion = optimizer.ask(1)[0]

    with pytest.raises(GraphRuntimeError, match="registered"):
        observe_whole_system_structural_suggestion(
            space,
            suggestion,
            registry=MechanismRegistry(),
        )
    assert optimizer.state_dict()["observations"] == []
