from __future__ import annotations

from dataclasses import replace
import json

import pytest

from utopia.optimization.blackbox import AdaptiveRandomSearch, evaluate_round
from utopia.optimization.communication_structural import (
    communication_engineering_loss,
    communication_structural_registry,
    communication_structural_space,
    execute_communication_structural_candidate,
    observe_communication_structural_suggestion,
)
from utopia.optimization.structural_space import StructuralSelection
from utopia.system import (
    ChannelKind,
    DeliveredValue,
    DeterministicGraphRunner,
    GraphCheckpoint,
    GraphRuntimeError,
    MechanismContext,
    MechanismFamily,
    MechanismSpec,
)
from utopia.system.production import (
    KNOWLEDGE_ITEM_SCHEMA_VERSION,
    KNOWLEDGE_MESSAGE_SCHEMA_VERSION,
    parse_knowledge_item,
    parse_knowledge_message,
    validate_delivered_message,
)
from utopia.system.production.communication import knowledge_receiver


def _candidate(
    broker: str | None,
    *,
    source_latency: str | None = "instant",
    research_latency: str | None = "one-period",
    education_latency: str | None = "one-period",
) -> dict:
    enabled = broker is not None
    space = communication_structural_space()
    return space.build(
        StructuralSelection(
            {
                "source": "deterministic-research",
                "broker": broker,
                "research-consumer": "strict-receiver",
                "education-consumer": "strict-receiver",
            },
            {
                "source-to-broker": source_latency if enabled else None,
                "broker-to-research": research_latency if enabled else None,
                "broker-to-education": education_latency if enabled else None,
            },
        )
    ).to_dict()


def _item(index: int = 1) -> dict:
    return {
        "schema_version": KNOWLEDGE_ITEM_SCHEMA_VERSION,
        "knowledge_id": f"knowledge-{index}",
        "origin_mechanism": "knowledge-source",
        "created_period": 0,
        "topic": "methods",
        "summary": f"Knowledge item {index}",
        "evidence_artifact_ids": [f"evidence-{index}"],
    }


def _message(sequence: int = 1) -> dict:
    return {
        "schema_version": KNOWLEDGE_MESSAGE_SCHEMA_VERSION,
        "message_id": f"message-{sequence}",
        "message_sequence": sequence,
        "sender_id": "knowledge-broker",
        "system_fingerprint": "a" * 64,
        "emitted_period": 0,
        "transformation": "relay",
        "source_event_ids": ["source-event"],
        "knowledge_items": [_item(sequence)],
    }


def _delivered(message: dict) -> DeliveredValue:
    return DeliveredValue(
        channel=ChannelKind.SIGNAL,
        artifact_type="knowledge-message",
        payload=message,
        actor_ids=(),
        artifact_ids=tuple(
            item["knowledge_id"] for item in message["knowledge_items"]
        ),
        lineage_event_ids=("source-event", "message-event"),
        source_mechanism=message["sender_id"],
        source_port="messages",
        emitted_period=message["emitted_period"],
        available_period=message["emitted_period"] + 1,
    )


def test_message_schema_and_delivery_provenance_fail_closed() -> None:
    item = parse_knowledge_item(_item())
    message = parse_knowledge_message(_message())
    delivered = _delivered(message)

    assert item["knowledge_id"] == "knowledge-1"
    assert validate_delivered_message(
        delivered, system_fingerprint="a" * 64
    ) == message

    unknown = {**message, "unknown": True}
    with pytest.raises(GraphRuntimeError, match="fields do not match"):
        parse_knowledge_message(unknown)
    duplicated = _message()
    duplicated["knowledge_items"].append(_item())
    with pytest.raises(GraphRuntimeError, match="duplicate knowledge"):
        parse_knowledge_message(duplicated)
    malformed_item = {**_item(), "unversioned_extra": True}
    with pytest.raises(GraphRuntimeError, match="fields do not match"):
        parse_knowledge_item(malformed_item)
    with pytest.raises(GraphRuntimeError, match="different system"):
        validate_delivered_message(delivered, system_fingerprint="b" * 64)
    with pytest.raises(GraphRuntimeError, match="sender does not match"):
        validate_delivered_message(
            replace(delivered, source_mechanism="other-broker"),
            system_fingerprint="a" * 64,
        )
    with pytest.raises(GraphRuntimeError, match="period does not match"):
        validate_delivered_message(
            replace(delivered, emitted_period=1),
            system_fingerprint="a" * 64,
        )
    with pytest.raises(GraphRuntimeError, match="absent from lineage"):
        validate_delivered_message(
            replace(delivered, lineage_event_ids=("message-event",)),
            system_fingerprint="a" * 64,
        )
    with pytest.raises(GraphRuntimeError, match="artifacts do not match"):
        validate_delivered_message(
            replace(delivered, artifact_ids=("different-knowledge",)),
            system_fingerprint="a" * 64,
        )


def test_receiver_rejects_message_and_knowledge_replay() -> None:
    mechanism = MechanismSpec(
        "receiver",
        MechanismFamily.RESEARCH,
        "test.receiver",
        parameters={"receiver_role": "test"},
    )

    def invoke(message: dict, state: dict) -> object:
        return knowledge_receiver(
            MechanismContext(
                system_id="test-system",
                system_fingerprint="a" * 64,
                mechanism=mechanism,
                period=1,
                phase=2,
                trigger="annual",
                inputs={"messages": (_delivered(message),)},
                initial_state={},
                state=state,
            )
        )

    first = invoke(_message(), {})
    assert first.next_state is not None
    with pytest.raises(GraphRuntimeError, match="stale or replayed"):
        invoke(_message(), dict(first.next_state))

    repeated_knowledge = _message(sequence=2)
    repeated_knowledge["knowledge_items"] = [_item(index=1)]
    with pytest.raises(GraphRuntimeError, match="knowledge item was already received"):
        invoke(repeated_knowledge, dict(first.next_state))


def test_broadcast_and_digest_diffuse_to_two_independent_families() -> None:
    space = communication_structural_space()
    absent = execute_communication_structural_candidate(space, _candidate(None))
    broadcast = execute_communication_structural_candidate(
        space, _candidate("broadcast")
    )
    digest = execute_communication_structural_candidate(space, _candidate("digest"))

    assert absent.summary.to_dict() == {
        "emitted_messages": 0,
        "receipt_events": 0,
        "received_knowledge_items": 0,
        "blocked_invocations": 0,
        "mechanism_count": 3,
        "connection_count": 0,
    }
    assert broadcast.summary.emitted_messages == 8
    assert broadcast.summary.receipt_events == 12
    assert broadcast.summary.received_knowledge_items == 12
    assert digest.summary.emitted_messages == 2
    assert digest.summary.receipt_events == 2
    assert digest.summary.received_knowledge_items == 8

    broadcast_state = broadcast.result.checkpoint.mechanism_states[
        "knowledge-broker"
    ]
    digest_state = digest.result.checkpoint.mechanism_states["knowledge-broker"]
    assert broadcast_state["processed_knowledge_ids"] == [
        f"knowledge-{period}-{index}"
        for period in range(4)
        for index in range(2)
    ]
    assert len(broadcast_state["observed_event_ids"]) == 4
    assert broadcast_state["next_message_sequence"] == 9
    assert digest_state["next_message_sequence"] == 3
    assert digest_state["buffer"] == []

    receipt = next(
        event
        for event in broadcast.result.events
        if event.event_type == "communication.knowledge_received"
    )
    event_types = {
        event.event_id: event.event_type for event in broadcast.result.events
    }
    lineage_types = {
        event_types[event_id] for event_id in receipt.provenance["input_event_ids"]
    }
    assert lineage_types == {
        "research.knowledge_created",
        "communication.message_emitted",
    }
    assert {
        event.provenance["mechanism_family"]
        for event in broadcast.result.events
        if event.event_type == "communication.knowledge_received"
    } == {"research", "education"}


def test_digest_checkpoint_resume_and_latency_fingerprint() -> None:
    space = communication_structural_space()
    candidate = _candidate("digest")
    changed = _candidate("digest", education_latency="two-period")
    spec = space.decode(candidate)
    changed_spec = space.decode(changed)
    registry = communication_structural_registry()

    uninterrupted = DeterministicGraphRunner(spec, registry).run(periods=4)
    first = DeterministicGraphRunner(
        spec, communication_structural_registry()
    ).run(periods=2)
    checkpoint = GraphCheckpoint.from_dict(
        json.loads(json.dumps(first.checkpoint.to_dict(), sort_keys=True))
    )
    resumed = DeterministicGraphRunner(
        spec, communication_structural_registry()
    ).run(periods=2, checkpoint=checkpoint)

    assert [event.to_dict() for event in (*first.events, *resumed.events)] == [
        event.to_dict() for event in uninterrupted.events
    ]
    assert resumed.checkpoint.to_dict() == uninterrupted.checkpoint.to_dict()
    assert changed_spec.fingerprint != spec.fingerprint
    with pytest.raises(GraphRuntimeError, match="fingerprint does not match"):
        DeterministicGraphRunner(
            changed_spec, communication_structural_registry()
        ).run(periods=1, checkpoint=checkpoint)


def test_communication_space_executes_every_structure_and_mutation_axis() -> None:
    space = communication_structural_space()
    runs = [
        execute_communication_structural_candidate(
            space, space.build(selection).to_dict(), periods=3
        )
        for selection in space.selections
    ]
    kinds = {
        mutation.kind
        for selection in space.selections
        for mutation, _neighbor in space.neighbors(space.build(selection).to_dict())
    }

    assert space.candidate_count == 97
    assert len({run.spec.fingerprint for run in runs}) == 97
    assert kinds == {"node-presence", "implementation", "edge-presence", "latency"}
    assert {selection.nodes["broker"] for selection in space.selections} == {
        None,
        "broadcast",
        "digest",
    }


def test_black_box_boundary_explores_communication_structure() -> None:
    space = communication_structural_space()
    optimizer = AdaptiveRandomSearch(space, seed=13, initial_random=8)
    suggestions, observations = evaluate_round(
        optimizer,
        lambda suggestion: observe_communication_structural_suggestion(
            space,
            suggestion,
            loss_function=communication_engineering_loss,
        ),
        count=8,
    )
    selections = [space.selection(suggestion.candidate) for suggestion in suggestions]

    assert {selection.nodes["broker"] for selection in selections} == {
        None,
        "broadcast",
        "digest",
    }
    assert {
        selection.edges["source-to-broker"] for selection in selections
    } == {None, "instant", "one-period"}
    downstream_latencies = {
        selection.edges[slot]
        for selection in selections
        for slot in ("broker-to-research", "broker-to-education")
    }
    assert {None, "instant", "one-period", "two-period"} <= downstream_latencies
    assert len({observation.loss for observation in observations}) > 1
    assert all(
        observation.metadata["system_fingerprint"]
        == space.candidate_fingerprint(observation.candidate)
        for observation in observations
    )
