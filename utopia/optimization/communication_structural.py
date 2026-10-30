"""Structural black-box space for communication and knowledge diffusion."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Callable, Mapping

from utopia.optimization.blackbox import Observation, Suggestion
from utopia.optimization.structural_space import (
    EdgeOption,
    EdgeSlot,
    NodeOption,
    NodeSlot,
    StructuralGrammar,
    StructuralSystemSpace,
)
from utopia.system import (
    ArtifactTypeSpec,
    ChannelKind,
    ConnectionSpec,
    DeterministicGraphRunner,
    GraphRunResult,
    MechanismFamily,
    MechanismRegistry,
    MechanismSpec,
    PortSpec,
    ScheduleSpec,
    SystemSpec,
)
from utopia.system.production import (
    KNOWLEDGE_BROADCAST,
    KNOWLEDGE_DIGEST,
    KNOWLEDGE_ITEM_SCHEMA_VERSION,
    KNOWLEDGE_RECEIVER,
    register_communication_mechanisms,
)
from utopia.system.runtime import (
    MechanismEvent,
    MechanismResult,
    MechanismValue,
)


KNOWLEDGE_SOURCE_FIXTURE = "experiment.research.knowledge-source-v1"


@dataclass(frozen=True)
class CommunicationStructuralSummary:
    emitted_messages: int
    receipt_events: int
    received_knowledge_items: int
    blocked_invocations: int
    mechanism_count: int
    connection_count: int

    def to_dict(self) -> dict[str, int]:
        return {
            "emitted_messages": self.emitted_messages,
            "receipt_events": self.receipt_events,
            "received_knowledge_items": self.received_knowledge_items,
            "blocked_invocations": self.blocked_invocations,
            "mechanism_count": self.mechanism_count,
            "connection_count": self.connection_count,
        }


@dataclass(frozen=True)
class CommunicationStructuralRun:
    spec: SystemSpec
    result: GraphRunResult
    summary: CommunicationStructuralSummary


CommunicationLoss = Callable[[CommunicationStructuralRun], float]


def communication_structural_grammar() -> StructuralGrammar:
    """Finite grammar for optional one-to-many knowledge diffusion."""

    source = NodeSlot(
        "source",
        (
            NodeOption(
                "deterministic-research",
                MechanismSpec(
                    "knowledge-source",
                    MechanismFamily.RESEARCH,
                    KNOWLEDGE_SOURCE_FIXTURE,
                    outputs=(
                        PortSpec(
                            "knowledge",
                            ChannelKind.ARTIFACT,
                            "knowledge-item",
                        ),
                    ),
                ),
                ScheduleSpec("knowledge-source", 0),
            ),
        ),
    )
    broker = NodeSlot(
        "broker",
        tuple(
            NodeOption(
                option_id,
                MechanismSpec(
                    "knowledge-broker",
                    MechanismFamily.COMMUNICATION,
                    implementation,
                    inputs=(
                        PortSpec(
                            "knowledge",
                            ChannelKind.ARTIFACT,
                            "knowledge-item",
                            required=False,
                        ),
                    ),
                    outputs=(
                        PortSpec(
                            "messages",
                            ChannelKind.SIGNAL,
                            "knowledge-message",
                            required=False,
                        ),
                    ),
                    parameters={"digest_size": 3},
                ),
                ScheduleSpec("knowledge-broker", 1),
            )
            for option_id, implementation in (
                ("broadcast", KNOWLEDGE_BROADCAST),
                ("digest", KNOWLEDGE_DIGEST),
            )
        ),
        optional=True,
    )
    research_consumer = _consumer_slot(
        "research-consumer",
        "research-consumer",
        MechanismFamily.RESEARCH,
        "research-archive",
    )
    education_consumer = _consumer_slot(
        "education-consumer",
        "education-consumer",
        MechanismFamily.EDUCATION,
        "education-curriculum",
    )
    return StructuralGrammar(
        space_id="communication-knowledge-diffusion-v1",
        system_id="communication-knowledge-diffusion",
        version=1,
        node_slots=(source, broker, research_consumer, education_consumer),
        edge_slots=(
            _latency_edge(
                "source-to-broker",
                "knowledge-source",
                "knowledge",
                "knowledge-broker",
                "knowledge",
                ChannelKind.ARTIFACT,
                (("instant", 0), ("one-period", 1)),
            ),
            _latency_edge(
                "broker-to-research",
                "knowledge-broker",
                "messages",
                "research-consumer",
                "messages",
                ChannelKind.SIGNAL,
                (("instant", 0), ("one-period", 1), ("two-period", 2)),
            ),
            _latency_edge(
                "broker-to-education",
                "knowledge-broker",
                "messages",
                "education-consumer",
                "messages",
                ChannelKind.SIGNAL,
                (("instant", 0), ("one-period", 1), ("two-period", 2)),
            ),
        ),
        artifact_types=(
            ArtifactTypeSpec("knowledge-item"),
            ArtifactTypeSpec("knowledge-message"),
        ),
        global_invariants=(
            "strict-knowledge-message-v1",
            "causal-message-lineage",
            "monotonic-sender-sequence",
            "fingerprint-bound-checkpoints",
        ),
        metadata={
            "purpose": "communication-diffusion-engineering-fixture",
            "scientific_preference": "not-defined",
            "scope": "general-science-system-mechanism",
        },
    )


def communication_structural_space() -> StructuralSystemSpace:
    return StructuralSystemSpace(communication_structural_grammar())


def communication_structural_registry() -> MechanismRegistry:
    registry = MechanismRegistry()
    register_communication_structural_fixture(registry)
    register_communication_mechanisms(registry)
    return registry


def register_communication_structural_fixture(registry: MechanismRegistry) -> None:
    """Register only the deterministic development source used by this track.

    Keeping fixture registration separate from the production communication
    adapters lets a larger graph reuse the exact same synthetic source without
    copying its behavior or treating it as a production mechanism.
    """

    registry.register(KNOWLEDGE_SOURCE_FIXTURE, 1, _knowledge_source_fixture)


def execute_communication_structural_candidate(
    space: StructuralSystemSpace,
    candidate: Mapping[str, Any],
    *,
    periods: int = 4,
) -> CommunicationStructuralRun:
    spec = space.decode(candidate)
    result = DeterministicGraphRunner(
        spec, communication_structural_registry()
    ).run(periods=periods)
    message_events = tuple(
        event
        for event in result.events
        if event.event_type == "communication.message_emitted"
    )
    receipt_events = tuple(
        event
        for event in result.events
        if event.event_type == "communication.knowledge_received"
    )
    summary = CommunicationStructuralSummary(
        emitted_messages=len(message_events),
        receipt_events=len(receipt_events),
        received_knowledge_items=sum(
            len(event.payload["knowledge_ids"]) for event in receipt_events
        ),
        blocked_invocations=sum(record.status == "blocked" for record in result.trace),
        mechanism_count=len(spec.mechanisms),
        connection_count=len(spec.connections),
    )
    return CommunicationStructuralRun(spec, result, summary)


def communication_engineering_loss(run: CommunicationStructuralRun) -> float:
    """Technical coverage target; it is not an epistemic-quality objective."""

    summary = run.summary
    value = (
        abs(summary.emitted_messages - 2)
        + abs(summary.receipt_events - 2)
        + 0.1 * summary.blocked_invocations
        + 0.001 * summary.connection_count
    )
    if not math.isfinite(value):
        raise ValueError("communication engineering loss must be finite")
    return float(value)


def observe_communication_structural_suggestion(
    space: StructuralSystemSpace,
    suggestion: Suggestion,
    *,
    periods: int = 4,
    loss_function: CommunicationLoss = communication_engineering_loss,
) -> Observation:
    run = execute_communication_structural_candidate(
        space, suggestion.candidate, periods=periods
    )
    loss = loss_function(run)
    if isinstance(loss, bool) or not isinstance(loss, (int, float)) or not math.isfinite(loss):
        raise ValueError("loss_function must return a finite scalar")
    return Observation(
        observation_id="observation-" + suggestion.suggestion_id,
        suggestion_id=suggestion.suggestion_id,
        candidate=suggestion.candidate,
        status="complete",
        loss=float(loss),
        metadata={
            "system_fingerprint": run.spec.fingerprint,
            "event_stream_hash": run.result.event_stream_hash,
            "checkpoint_fingerprint": run.result.checkpoint.fingerprint,
            "summary": run.summary.to_dict(),
        },
    )


def _consumer_slot(
    slot_id: str,
    mechanism_id: str,
    family: MechanismFamily,
    receiver_role: str,
) -> NodeSlot:
    return NodeSlot(
        slot_id,
        (
            NodeOption(
                "strict-receiver",
                MechanismSpec(
                    mechanism_id,
                    family,
                    KNOWLEDGE_RECEIVER,
                    inputs=(
                        PortSpec(
                            "messages",
                            ChannelKind.SIGNAL,
                            "knowledge-message",
                            required=False,
                        ),
                    ),
                    parameters={"receiver_role": receiver_role},
                ),
                ScheduleSpec(mechanism_id, 2),
            ),
        ),
    )


def _latency_edge(
    slot_id: str,
    source_mechanism: str,
    source_port: str,
    target_mechanism: str,
    target_port: str,
    channel: ChannelKind,
    choices: tuple[tuple[str, int], ...],
) -> EdgeSlot:
    return EdgeSlot(
        slot_id,
        tuple(
            EdgeOption(
                option_id,
                ConnectionSpec(
                    source_mechanism,
                    source_port,
                    target_mechanism,
                    target_port,
                    channel,
                    latency=latency,
                ),
            )
            for option_id, latency in choices
        ),
    )


def _knowledge_source_fixture(context) -> MechanismResult:
    period = context.period
    items = tuple(
        {
            "schema_version": KNOWLEDGE_ITEM_SCHEMA_VERSION,
            "knowledge_id": f"knowledge-{period}-{index}",
            "origin_mechanism": context.mechanism.mechanism_id,
            "created_period": period,
            "topic": ("methods", "institutions")[(period + index) % 2],
            "summary": f"Deterministic knowledge item {period}-{index}",
            "evidence_artifact_ids": [f"evidence-{period}-{index}"],
        }
        for index in range(2)
    )
    return MechanismResult(
        outputs={
            "knowledge": tuple(
                MechanismValue(item, artifact_ids=(item["knowledge_id"],))
                for item in items
            )
        },
        events=(
            MechanismEvent(
                "research.knowledge_created",
                artifact_ids=tuple(item["knowledge_id"] for item in items),
                payload={
                    "knowledge_ids": [item["knowledge_id"] for item in items],
                    "fixture": "deterministic-engineering-only",
                },
                provenance={"production_adapter": KNOWLEDGE_SOURCE_FIXTURE},
            ),
        ),
    )
