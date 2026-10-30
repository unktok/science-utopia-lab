"""Joint structural black-box space for a multi-institution science system.

This is a deterministic development slice.  It composes existing production
evaluation, publication, funding, government, and communication adapters in
one ``SystemSpec`` search space.  It neither defines held-out metrics nor a
promotion policy, and its synthetic engineering LossSpec is not a science-
policy objective.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

from utopia.optimization.blackbox import Observation, Suggestion
from utopia.optimization.communication_structural import (
    KNOWLEDGE_SOURCE_FIXTURE,
    register_communication_structural_fixture,
)
from utopia.optimization.loss import (
    SCHEMA as LOSS_SPEC_SCHEMA,
    evaluate_loss,
    loss_spec_sha256,
    validate_loss_spec,
)
from utopia.optimization.production_structural import (
    STRUCTURAL_WORKLOAD_SOURCE,
    production_structural_registry,
)
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
    COMPACT_RANKED_ALLOCATION,
    CONFERENCE_ACCEPTANCE,
    EVENT_RESPONSIVE_GOVERNMENT,
    KNOWLEDGE_BROADCAST,
    KNOWLEDGE_DIGEST,
    KNOWLEDGE_RECEIVER,
    PAPER_TRACKER_PUBLICATION,
    THRESHOLD_GOVERNMENT,
)


WHOLE_SYSTEM_SPACE_ID = "whole-science-system-structural-v1"
ENGINEERING_POLICY_DIRECTIVES = {
    "evaluation": {"acceptance_rate": 1.0},
    "funding": {"award_amount_multiplier": 2.0},
}

# This ordinary LossSpec is deliberately bound to synthetic development
# signals.  It is exported so callers cannot silently substitute an implicit
# score while claiming to use this integration fixture.
WHOLE_SYSTEM_ENGINEERING_LOSS_SPEC: dict[str, Any] = {
    "schema": LOSS_SPEC_SCHEMA,
    "id": "whole-system-structural-engineering-v1",
    "version": "1.0.0",
    "status": "synthetic-development-only",
    "optimization_seed_role": "optimization",
    "direction": "minimize",
    "per_run": {
        "intercept": 0.0,
        "terms": [
            {"metric_id": "accepted", "slice_id": None, "coefficient": -1.0},
            {
                "metric_id": "publication_records",
                "slice_id": None,
                "coefficient": -0.5,
            },
            {
                "metric_id": "total_awarded",
                "slice_id": None,
                "coefficient": -0.01,
            },
            {
                "metric_id": "received_knowledge_items",
                "slice_id": None,
                "coefficient": -0.1,
            },
            {
                "metric_id": "blocked_invocations",
                "slice_id": None,
                "coefficient": 0.2,
            },
            {
                "metric_id": "mechanism_count",
                "slice_id": None,
                "coefficient": 0.01,
            },
        ],
    },
    "across_seeds": {
        "aggregation": "mean_plus_population_sd",
        "dispersion_weight": 0.0,
        "minimum_valid_runs": 1,
    },
}


@dataclass(frozen=True)
class WholeSystemStructuralSummary:
    accepted: int
    rejected: int
    publication_records: int
    funding_awards: int
    total_awarded: float
    government_policies: int
    emitted_messages: int
    received_knowledge_items: int
    blocked_invocations: int
    mechanism_count: int
    connection_count: int

    def to_dict(self) -> dict[str, int | float]:
        return {
            "accepted": self.accepted,
            "rejected": self.rejected,
            "publication_records": self.publication_records,
            "funding_awards": self.funding_awards,
            "total_awarded": self.total_awarded,
            "government_policies": self.government_policies,
            "emitted_messages": self.emitted_messages,
            "received_knowledge_items": self.received_knowledge_items,
            "blocked_invocations": self.blocked_invocations,
            "mechanism_count": self.mechanism_count,
            "connection_count": self.connection_count,
        }

    def development_evaluation(self, run_id: str) -> dict[str, Any]:
        """Return LossSpec inputs, explicitly not a held-out metric report."""

        values = self.to_dict()
        metric_ids = (
            "accepted",
            "publication_records",
            "total_awarded",
            "received_knowledge_items",
            "blocked_invocations",
            "mechanism_count",
        )
        return {
            "run_id": run_id,
            "measurement_role": "synthetic-optimization-development",
            "metrics": {
                metric_id: {"status": "measured", "value": values[metric_id]}
                for metric_id in metric_ids
            },
        }


@dataclass(frozen=True)
class WholeSystemStructuralRun:
    spec: SystemSpec
    result: GraphRunResult
    summary: WholeSystemStructuralSummary


def whole_system_structural_grammar() -> StructuralGrammar:
    """Compose five optional institutional families in one finite grammar."""

    workload = NodeSlot(
        "workload",
        (
            NodeOption(
                "deterministic-v1",
                MechanismSpec(
                    "workload",
                    MechanismFamily.CUSTOM,
                    STRUCTURAL_WORKLOAD_SOURCE,
                    outputs=(
                        PortSpec("review_batches", ChannelKind.ARTIFACT, "review-batch"),
                        PortSpec("funding_panels", ChannelKind.ARTIFACT, "funding-panel"),
                    ),
                ),
                ScheduleSpec("workload", 0),
            ),
        ),
    )
    knowledge_source = NodeSlot(
        "knowledge-source",
        (
            NodeOption(
                "deterministic-v1",
                MechanismSpec(
                    "knowledge-source",
                    MechanismFamily.RESEARCH,
                    KNOWLEDGE_SOURCE_FIXTURE,
                    outputs=(PortSpec("knowledge", ChannelKind.ARTIFACT, "knowledge-item"),),
                ),
                ScheduleSpec("knowledge-source", 0),
            ),
        ),
    )
    evaluation = NodeSlot(
        "evaluation",
        tuple(
            NodeOption(
                option_id,
                MechanismSpec(
                    "evaluation",
                    MechanismFamily.EVALUATION,
                    CONFERENCE_ACCEPTANCE,
                    inputs=(
                        PortSpec("review_batches", ChannelKind.ARTIFACT, "review-batch"),
                        PortSpec(
                            "policies",
                            ChannelKind.CONSTRAINT,
                            "government-policy",
                            required=False,
                        ),
                    ),
                    outputs=(PortSpec("decisions", ChannelKind.DECISION, "paper-decision"),),
                    parameters={
                        "acceptance_rate": 0.5,
                        "acceptance_mode": mode,
                        "tiebreak_seed": 2718,
                    },
                ),
                ScheduleSpec("evaluation", 1),
            )
            for option_id, mode in (
                ("conference-rate", "rate"),
                ("conference-fixed-slots", "fixed_slots"),
            )
        ),
        optional=True,
    )
    publication = NodeSlot(
        "publication",
        (
            NodeOption(
                "paper-tracker",
                MechanismSpec(
                    "publication",
                    MechanismFamily.PUBLICATION,
                    PAPER_TRACKER_PUBLICATION,
                    inputs=(PortSpec("decisions", ChannelKind.DECISION, "paper-decision"),),
                    outputs=(
                        PortSpec(
                            "records",
                            ChannelKind.ARTIFACT,
                            "publication-record",
                            required=False,
                        ),
                    ),
                ),
                ScheduleSpec("publication", 2),
            ),
        ),
        optional=True,
    )
    funding = NodeSlot(
        "funding",
        (
            NodeOption(
                "compact-ranked",
                MechanismSpec(
                    "funding",
                    MechanismFamily.FUNDING,
                    COMPACT_RANKED_ALLOCATION,
                    inputs=(
                        PortSpec("panels", ChannelKind.ARTIFACT, "funding-panel"),
                        PortSpec(
                            "policies",
                            ChannelKind.CONSTRAINT,
                            "government-policy",
                            required=False,
                        ),
                    ),
                    outputs=(
                        PortSpec("allocations", ChannelKind.RESOURCE, "resource-allocation"),
                    ),
                    parameters={"award_slots": 1, "award_amount": 25},
                ),
                ScheduleSpec("funding", 1),
            ),
        ),
        optional=True,
    )
    government = NodeSlot(
        "government",
        tuple(
            NodeOption(
                option_id,
                MechanismSpec(
                    "government",
                    MechanismFamily.GOVERNANCE,
                    implementation,
                    inputs=(
                        PortSpec(
                            "decisions",
                            ChannelKind.DECISION,
                            "paper-decision",
                            required=False,
                        ),
                    ),
                    outputs=(
                        PortSpec(
                            "evaluation_policies",
                            ChannelKind.CONSTRAINT,
                            "government-policy",
                            required=False,
                        ),
                        PortSpec(
                            "funding_policies",
                            ChannelKind.CONSTRAINT,
                            "government-policy",
                            required=False,
                        ),
                    ),
                    parameters={
                        "directives": ENGINEERING_POLICY_DIRECTIVES,
                        "minimum_observations": minimum,
                        "repeat_interval": repeat,
                    },
                ),
                ScheduleSpec("government", 3),
            )
            for option_id, implementation, minimum, repeat in (
                ("event-responsive", EVENT_RESPONSIVE_GOVERNMENT, 1, 1),
                ("cumulative-threshold", THRESHOLD_GOVERNMENT, 10, 10),
            )
        ),
        optional=True,
    )
    broker = NodeSlot(
        "communication",
        tuple(
            NodeOption(
                option_id,
                MechanismSpec(
                    "knowledge-broker",
                    MechanismFamily.COMMUNICATION,
                    implementation,
                    inputs=(PortSpec("knowledge", ChannelKind.ARTIFACT, "knowledge-item"),),
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
    research_receiver = NodeSlot(
        "research-receiver",
        (
            NodeOption(
                "strict-receiver",
                MechanismSpec(
                    "research-receiver",
                    MechanismFamily.RESEARCH,
                    KNOWLEDGE_RECEIVER,
                    inputs=(
                        PortSpec(
                            "messages",
                            ChannelKind.SIGNAL,
                            "knowledge-message",
                            required=False,
                        ),
                    ),
                    parameters={"receiver_role": "research-archive"},
                ),
                ScheduleSpec("research-receiver", 2),
            ),
        ),
    )

    return StructuralGrammar(
        space_id=WHOLE_SYSTEM_SPACE_ID,
        system_id="whole-science-system",
        version=1,
        node_slots=(
            workload,
            knowledge_source,
            evaluation,
            publication,
            funding,
            government,
            broker,
            research_receiver,
        ),
        edge_slots=(
            _edge(
                "review-input",
                "workload",
                "review_batches",
                "evaluation",
                "review_batches",
                ChannelKind.ARTIFACT,
            ),
            _edge(
                "publication-flow",
                "evaluation",
                "decisions",
                "publication",
                "decisions",
                ChannelKind.DECISION,
            ),
            _edge(
                "funding-input",
                "workload",
                "funding_panels",
                "funding",
                "panels",
                ChannelKind.ARTIFACT,
            ),
            _edge(
                "government-observation",
                "evaluation",
                "decisions",
                "government",
                "decisions",
                ChannelKind.DECISION,
            ),
            _edge(
                "government-policy",
                "government",
                "evaluation_policies",
                "evaluation",
                "policies",
                ChannelKind.CONSTRAINT,
                latencies=(("one-period", 1), ("two-period", 2)),
            ),
            _edge(
                "knowledge-input",
                "knowledge-source",
                "knowledge",
                "knowledge-broker",
                "knowledge",
                ChannelKind.ARTIFACT,
            ),
            _edge(
                "knowledge-delivery",
                "knowledge-broker",
                "messages",
                "research-receiver",
                "messages",
                ChannelKind.SIGNAL,
                latencies=(("instant", 0), ("one-period", 1)),
            ),
        ),
        artifact_types=tuple(
            ArtifactTypeSpec(name)
            for name in (
                "review-batch",
                "paper-decision",
                "publication-record",
                "funding-panel",
                "resource-allocation",
                "government-policy",
                "knowledge-item",
                "knowledge-message",
            )
        ),
        global_invariants=(
            "strict-json-events",
            "production-adapter-state",
            "causal-message-lineage",
            "monotonic-policy-version",
            "fingerprint-bound-checkpoints",
        ),
        metadata={
            "purpose": "whole-system-structural-black-box-integration",
            "workload": "deterministic-development-fixtures",
            "objective_binding": "external-loss-spec",
            "held_out_metrics": "not-defined",
            "promotion_policy": "not-defined",
            "scientific_preference": "not-defined",
        },
    )


def whole_system_structural_space() -> StructuralSystemSpace:
    return StructuralSystemSpace(whole_system_structural_grammar())


def whole_system_structural_registry() -> MechanismRegistry:
    registry = production_structural_registry()
    register_communication_structural_fixture(registry)
    return registry


def execute_whole_system_structural_candidate(
    space: StructuralSystemSpace,
    candidate: Mapping[str, Any],
    *,
    periods: int = 4,
    registry: MechanismRegistry | None = None,
) -> WholeSystemStructuralRun:
    spec = space.decode(candidate)
    result = DeterministicGraphRunner(
        spec,
        registry if registry is not None else whole_system_structural_registry(),
    ).run(periods=periods)
    decisions = [
        event for event in result.events if event.event_type == "evaluation.paper_decided"
    ]
    awards = [event for event in result.events if event.event_type == "funding.awarded"]
    received = [
        event
        for event in result.events
        if event.event_type == "communication.knowledge_received"
    ]
    summary = WholeSystemStructuralSummary(
        accepted=sum(event.payload["decision"] == "accept" for event in decisions),
        rejected=sum(event.payload["decision"] == "reject" for event in decisions),
        publication_records=sum(
            event.event_type == "publication.recorded" for event in result.events
        ),
        funding_awards=len(awards),
        total_awarded=sum(float(event.payload["amount"]) for event in awards),
        government_policies=sum(
            event.event_type == "government.policy_decided" for event in result.events
        ),
        emitted_messages=sum(
            event.event_type == "communication.message_emitted" for event in result.events
        ),
        received_knowledge_items=sum(
            len(event.payload["knowledge_ids"]) for event in received
        ),
        blocked_invocations=sum(record.status == "blocked" for record in result.trace),
        mechanism_count=len(spec.mechanisms),
        connection_count=len(spec.connections),
    )
    return WholeSystemStructuralRun(spec, result, summary)


def whole_system_engineering_loss(
    run: WholeSystemStructuralRun,
    *,
    loss_spec: Mapping[str, Any] = WHOLE_SYSTEM_ENGINEERING_LOSS_SPEC,
) -> float:
    """Evaluate the explicit synthetic LossSpec after a technically valid run."""

    validate_loss_spec(loss_spec)
    evaluation = run.summary.development_evaluation(
        "development-" + run.spec.fingerprint[:16]
    )
    result = evaluate_loss(loss_spec, (evaluation,))
    loss = result.get("loss")
    if result.get("status") != "complete" or isinstance(loss, bool) or not isinstance(
        loss, (int, float)
    ) or not math.isfinite(loss):
        raise ValueError("engineering LossSpec did not produce a finite scalar")
    return float(loss)


def observe_whole_system_structural_suggestion(
    space: StructuralSystemSpace,
    suggestion: Suggestion,
    *,
    periods: int = 4,
    loss_spec: Mapping[str, Any] = WHOLE_SYSTEM_ENGINEERING_LOSS_SPEC,
    registry: MechanismRegistry | None = None,
) -> Observation:
    """Execute, validate, then score; technical failures never get penalties."""

    run = execute_whole_system_structural_candidate(
        space, suggestion.candidate, periods=periods, registry=registry
    )
    loss = whole_system_engineering_loss(run, loss_spec=loss_spec)
    return Observation(
        observation_id="observation-" + suggestion.suggestion_id,
        suggestion_id=suggestion.suggestion_id,
        candidate=suggestion.candidate,
        status="complete",
        loss=loss,
        metadata={
            "technical_validity": "complete",
            "system_fingerprint": run.spec.fingerprint,
            "event_stream_hash": run.result.event_stream_hash,
            "checkpoint_fingerprint": run.result.checkpoint.fingerprint,
            "loss_spec": {
                "id": loss_spec["id"],
                "version": loss_spec["version"],
                "sha256": loss_spec_sha256(loss_spec),
            },
            "measurement_role": "synthetic-optimization-development",
            "summary": run.summary.to_dict(),
        },
    )


def _edge(
    slot_id: str,
    source_mechanism: str,
    source_port: str,
    target_mechanism: str,
    target_port: str,
    channel: ChannelKind,
    *,
    latencies: tuple[tuple[str, int], ...] = (("instant", 0),),
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
            for option_id, latency in latencies
        ),
    )
