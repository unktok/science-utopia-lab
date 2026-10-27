from __future__ import annotations

from dataclasses import replace

import pytest

from utopia.replay import replay, validate_references
from utopia.system import (
    ArtifactTypeSpec,
    ChannelKind,
    ConnectionSpec,
    DeterministicGraphRunner,
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
from utopia.system.examples import (
    DIRECT_PUBLICATION,
    FIXED_GRANT,
    RESOURCE_RESEARCH,
    register_example_mechanisms,
)


def publication_only_spec() -> SystemSpec:
    return SystemSpec(
        "publication-only-runtime",
        1,
        mechanisms=(
            MechanismSpec(
                "direct-publication",
                MechanismFamily.PUBLICATION,
                DIRECT_PUBLICATION,
                parameters={
                    "author_id": "researcher-open",
                    "artifact_id": "paper-open",
                    "title": "Open dissemination without an evaluation node",
                    "topics": ["open-science"],
                },
            ),
        ),
        schedules=(ScheduleSpec("direct-publication", 0),),
    )


def funding_to_research_spec(*, latency: int = 1) -> SystemSpec:
    return SystemSpec(
        "funding-to-research-runtime",
        1,
        artifact_types=(ArtifactTypeSpec("resource-allocation"),),
        mechanisms=(
            MechanismSpec(
                "grant-program",
                MechanismFamily.FUNDING,
                FIXED_GRANT,
                outputs=(
                    PortSpec(
                        "allocations",
                        ChannelKind.RESOURCE,
                        "resource-allocation",
                    ),
                ),
                parameters={
                    "recipient_id": "researcher-funded",
                    "amount": 10,
                    "initial_balance": 0,
                    "start_period": 0,
                },
            ),
            MechanismSpec(
                "research-program",
                MechanismFamily.RESEARCH,
                RESOURCE_RESEARCH,
                inputs=(
                    PortSpec(
                        "resources",
                        ChannelKind.RESOURCE,
                        "resource-allocation",
                    ),
                ),
            ),
        ),
        connections=(
            ConnectionSpec(
                "grant-program",
                "allocations",
                "research-program",
                "resources",
                ChannelKind.RESOURCE,
                latency=latency,
            ),
        ),
        schedules=(
            ScheduleSpec("grant-program", 0),
            ScheduleSpec("research-program", 1),
        ),
    )


def example_registry() -> MechanismRegistry:
    registry = MechanismRegistry()
    register_example_mechanisms(registry)
    return registry


def test_publication_only_graph_is_replayable_and_deterministic() -> None:
    spec = publication_only_spec()
    first = DeterministicGraphRunner(spec, example_registry()).run(periods=1)
    second = DeterministicGraphRunner(spec, example_registry()).run(periods=1)

    assert [event.to_dict() for event in first.events] == [
        event.to_dict() for event in second.events
    ]
    assert first.event_stream_hash == second.event_stream_hash
    assert [event.event_type for event in first.events] == [
        "agent.registered",
        "paper.submitted",
        "paper.decided",
    ]
    assert validate_references(first.events) == []
    state = replay(first.events)
    assert state.artifacts["paper-open"]["status"] == "published"

    decision = first.events[-1]
    assert decision.provenance["mechanism_id"] == "direct-publication"
    assert decision.provenance["mechanism_family"] == "publication"
    assert decision.provenance["system_fingerprint"] == spec.fingerprint
    assert decision.provenance["decision_rule"] == "publish-on-submission"
    assert decision.provenance["evaluation_mechanism"] is None
    assert MechanismFamily.EVALUATION not in {
        mechanism.family for mechanism in spec.mechanisms
    }


def test_latency_blocks_then_delivers_resource_with_causal_provenance() -> None:
    spec = funding_to_research_spec(latency=1)
    result = DeterministicGraphRunner(spec, example_registry()).run(periods=2)

    assert [
        (item.period, item.mechanism_id, item.status)
        for item in result.trace
    ] == [
        (0, "grant-program", "executed"),
        (0, "research-program", "blocked"),
        (1, "grant-program", "executed"),
        (1, "research-program", "executed"),
    ]
    blocked = result.trace[1]
    assert blocked.missing_required_inputs == ("resources",)
    assert result.trace[-1].input_counts == {"resources": 1}
    assert result.pending_deliveries == 1

    first_grant_events = result.trace[0].event_ids
    decision = next(
        event for event in result.events if event.event_type == "mechanism.decision"
    )
    assert decision.payload == {
        "decision": "start-research",
        "resource_amount": 10.0,
        "allocation_count": 1,
    }
    assert decision.provenance["input_event_ids"] == list(first_grant_events)
    assert decision.provenance["implementation"] == RESOURCE_RESEARCH
    assert validate_references(result.events) == []
    assert replay(result.events).agents["researcher-funded"]["balance"] == 20.0


def test_zero_latency_reaches_a_later_phase_in_the_same_period() -> None:
    spec = funding_to_research_spec(latency=0)
    result = DeterministicGraphRunner(spec, example_registry()).run(periods=1)

    assert [item.status for item in result.trace] == ["executed", "executed"]
    assert result.trace[-1].input_counts == {"resources": 1}
    decision = result.events[-1]
    assert decision.event_type == "mechanism.decision"
    assert decision.year == 0
    assert decision.phase == 1


def test_registry_can_replace_behavior_and_graph_can_remove_the_node() -> None:
    spec = publication_only_spec()
    registry = example_registry()

    def alternative(_context):
        return MechanismResult()

    registry.register(DIRECT_PUBLICATION, 1, alternative, replace=True)
    replaced = DeterministicGraphRunner(spec, registry).run(periods=1)
    assert replaced.events == ()

    registry.unregister(DIRECT_PUBLICATION, 1)
    with pytest.raises(GraphRuntimeError, match="no implementation registered"):
        DeterministicGraphRunner(spec, registry)

    removed = replace(spec, mechanisms=(), schedules=())
    result = DeterministicGraphRunner(removed, registry).run(periods=1)
    assert result.events == ()
    assert result.trace == ()


def test_runner_rejects_outputs_that_violate_the_declared_contract() -> None:
    spec = funding_to_research_spec(latency=1)
    registry = example_registry()

    def wrong_port(_context):
        return MechanismResult(
            outputs={"unknown": (MechanismValue({"amount": 1}),)}
        )

    registry.register(FIXED_GRANT, 1, wrong_port, replace=True)
    with pytest.raises(GraphRuntimeError, match="undeclared output ports"):
        DeterministicGraphRunner(spec, registry).run(periods=1)


def test_trigger_selects_only_matching_schedules() -> None:
    spec = replace(
        publication_only_spec(),
        schedules=(ScheduleSpec("direct-publication", 0, "continuous"),),
    )
    runner = DeterministicGraphRunner(spec, example_registry())

    assert runner.run(periods=1, trigger="annual").events == ()
    assert len(runner.run(periods=1, trigger="continuous").events) == 3


def test_handler_mutation_cannot_change_the_system_spec() -> None:
    spec = SystemSpec(
        "mutation-isolation",
        1,
        mechanisms=(
            MechanismSpec(
                "custom",
                MechanismFamily.CUSTOM,
                "example.mutation-attempt-v1",
                parameters={"nested": {"value": 1}},
            ),
        ),
        schedules=(ScheduleSpec("custom", 0),),
        initial_state={"nested": {"value": 2}},
    )
    original_fingerprint = spec.fingerprint
    registry = MechanismRegistry()

    def mutation_attempt(context):
        context.mechanism.parameters["nested"]["value"] = 100
        context.initial_state["nested"]["value"] = 200
        return MechanismResult()

    registry.register("example.mutation-attempt-v1", 1, mutation_attempt)
    runner = DeterministicGraphRunner(spec, registry)
    runner.run(periods=2)

    assert spec.mechanisms[0].parameters == {"nested": {"value": 1}}
    assert spec.initial_state == {"nested": {"value": 2}}
    assert spec.fingerprint == original_fingerprint
