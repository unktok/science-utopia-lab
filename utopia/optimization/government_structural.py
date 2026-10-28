"""Structural black-box space for stateful government control-plane nodes."""

from __future__ import annotations

from utopia.optimization.production_structural import (
    STRUCTURAL_WORKLOAD_SOURCE,
    ProductionStructuralRun,
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
    MechanismFamily,
    MechanismSpec,
    PortSpec,
    ScheduleSpec,
)
from utopia.system.production import (
    COMPACT_RANKED_ALLOCATION,
    CONFERENCE_ACCEPTANCE,
    EVENT_RESPONSIVE_GOVERNMENT,
    PAPER_TRACKER_PUBLICATION,
    THRESHOLD_GOVERNMENT,
)


ENGINEERING_POLICY_DIRECTIVES = {
    "evaluation": {"acceptance_rate": 1.0},
    "funding": {"award_amount_multiplier": 2.0},
}


def government_structural_grammar() -> StructuralGrammar:
    """Finite grammar varying government presence, implementation, and latency."""

    artifact_types = tuple(
        ArtifactTypeSpec(name)
        for name in (
            "review-batch",
            "paper-decision",
            "publication-record",
            "funding-panel",
            "resource-allocation",
            "government-policy",
        )
    )
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
                        PortSpec(
                            "review_batches", ChannelKind.ARTIFACT, "review-batch"
                        ),
                        PortSpec(
                            "funding_panels", ChannelKind.ARTIFACT, "funding-panel"
                        ),
                    ),
                ),
                ScheduleSpec("workload", 0),
            ),
        ),
    )
    evaluation = NodeSlot(
        "evaluation",
        (
            NodeOption(
                "conference-rate",
                MechanismSpec(
                    "evaluation",
                    MechanismFamily.EVALUATION,
                    CONFERENCE_ACCEPTANCE,
                    inputs=(
                        PortSpec(
                            "review_batches", ChannelKind.ARTIFACT, "review-batch"
                        ),
                        PortSpec(
                            "policies",
                            ChannelKind.CONSTRAINT,
                            "government-policy",
                            required=False,
                        ),
                    ),
                    outputs=(
                        PortSpec(
                            "decisions", ChannelKind.DECISION, "paper-decision"
                        ),
                    ),
                    parameters={
                        "acceptance_rate": 0.5,
                        "acceptance_mode": "rate",
                        "tiebreak_seed": 2718,
                    },
                ),
                ScheduleSpec("evaluation", 1),
            ),
        ),
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
                        PortSpec(
                            "allocations",
                            ChannelKind.RESOURCE,
                            "resource-allocation",
                        ),
                    ),
                    parameters={"award_slots": 1, "award_amount": 25},
                ),
                ScheduleSpec("funding", 1),
            ),
        ),
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
                    inputs=(
                        PortSpec("decisions", ChannelKind.DECISION, "paper-decision"),
                    ),
                    outputs=(
                        PortSpec(
                            "records", ChannelKind.ARTIFACT, "publication-record"
                        ),
                    ),
                ),
                ScheduleSpec("publication", 2),
            ),
        ),
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
                        PortSpec(
                            "allocations",
                            ChannelKind.RESOURCE,
                            "resource-allocation",
                            required=False,
                        ),
                        PortSpec(
                            "publications",
                            ChannelKind.ARTIFACT,
                            "publication-record",
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
                        PortSpec(
                            "publication_policies",
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
                (
                    "event-responsive",
                    EVENT_RESPONSIVE_GOVERNMENT,
                    1,
                    1,
                ),
                (
                    "cumulative-threshold",
                    THRESHOLD_GOVERNMENT,
                    10,
                    10,
                ),
            )
        ),
        optional=True,
    )

    base_edges = (
        EdgeSlot(
            "review-input",
            (
                EdgeOption(
                    "instant",
                    ConnectionSpec(
                        "workload",
                        "review_batches",
                        "evaluation",
                        "review_batches",
                        ChannelKind.ARTIFACT,
                        latency=0,
                    ),
                ),
            ),
            optional=False,
        ),
        EdgeSlot(
            "funding-input",
            (
                EdgeOption(
                    "instant",
                    ConnectionSpec(
                        "workload",
                        "funding_panels",
                        "funding",
                        "panels",
                        ChannelKind.ARTIFACT,
                        latency=0,
                    ),
                ),
            ),
            optional=False,
        ),
        EdgeSlot(
            "publication-flow",
            (
                EdgeOption(
                    "instant",
                    ConnectionSpec(
                        "evaluation",
                        "decisions",
                        "publication",
                        "decisions",
                        ChannelKind.DECISION,
                        latency=0,
                    ),
                ),
            ),
            optional=False,
        ),
    )
    observation_edges = (
        _single_edge(
            "observe-decisions",
            "evaluation",
            "decisions",
            "government",
            "decisions",
            ChannelKind.DECISION,
        ),
        _single_edge(
            "observe-allocations",
            "funding",
            "allocations",
            "government",
            "allocations",
            ChannelKind.RESOURCE,
        ),
        _single_edge(
            "observe-publications",
            "publication",
            "records",
            "government",
            "publications",
            ChannelKind.ARTIFACT,
        ),
    )
    policy_edges = (
        _latency_edge(
            "policy-to-evaluation",
            "government",
            "evaluation_policies",
            "evaluation",
            "policies",
        ),
        _latency_edge(
            "policy-to-funding",
            "government",
            "funding_policies",
            "funding",
            "policies",
        ),
    )
    return StructuralGrammar(
        space_id="stateful-government-science-system-v1",
        system_id="stateful-government-science-system",
        version=1,
        node_slots=(workload, evaluation, funding, publication, government),
        edge_slots=(*base_edges, *observation_edges, *policy_edges),
        artifact_types=artifact_types,
        global_invariants=(
            "strict-government-policy-v1",
            "monotonic-policy-version",
            "fingerprint-bound-checkpoints",
        ),
        metadata={
            "purpose": "stateful-government-engineering-fixture",
            "scientific_preference": "not-defined",
            "policy_directives": "arbitrary-integration-test-values",
        },
    )


def government_structural_space() -> StructuralSystemSpace:
    return StructuralSystemSpace(government_structural_grammar())


def government_engineering_loss(run: ProductionStructuralRun) -> float:
    """Control-plane coverage target, not a scientific outcome preference."""

    return float(
        abs(run.summary.government_policies - 2)
        + 0.1 * run.summary.blocked_invocations
        + 0.001 * run.summary.connection_count
    )


def _single_edge(
    slot_id: str,
    source_mechanism: str,
    source_port: str,
    target_mechanism: str,
    target_port: str,
    channel: ChannelKind,
) -> EdgeSlot:
    return EdgeSlot(
        slot_id,
        (
            EdgeOption(
                "instant",
                ConnectionSpec(
                    source_mechanism,
                    source_port,
                    target_mechanism,
                    target_port,
                    channel,
                    latency=0,
                ),
            ),
        ),
    )


def _latency_edge(
    slot_id: str,
    source_mechanism: str,
    source_port: str,
    target_mechanism: str,
    target_port: str,
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
                    ChannelKind.CONSTRAINT,
                    latency=latency,
                ),
            )
            for option_id, latency in (("one-period", 1), ("two-period", 2))
        ),
    )
