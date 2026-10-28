"""Small, LLM-free mechanism implementations for runtime examples and tests."""

from __future__ import annotations

from .runtime import (
    MechanismContext,
    MechanismEvent,
    MechanismRegistry,
    MechanismResult,
    MechanismValue,
)


DIRECT_PUBLICATION = "example.publication.direct-v1"
CURATED_PUBLICATION = "example.publication.curated-v1"
COMMUNITY_PUBLICATION = "example.governance.community-publication-v1"
FIXED_GRANT = "example.funding.fixed-grant-v1"
MATCHING_GRANT = "example.funding.matching-grant-v1"
RESOURCE_RESEARCH = "example.research.resource-triggered-v1"
AUTONOMOUS_RESEARCH = "example.research.autonomous-v1"


def register_example_mechanisms(registry: MechanismRegistry) -> None:
    """Register examples without giving the graph runner family knowledge."""

    registry.register(DIRECT_PUBLICATION, 1, direct_publication)
    registry.register(CURATED_PUBLICATION, 1, curated_publication)
    registry.register(COMMUNITY_PUBLICATION, 1, community_publication)
    registry.register(FIXED_GRANT, 1, fixed_grant)
    registry.register(MATCHING_GRANT, 1, matching_grant)
    registry.register(RESOURCE_RESEARCH, 1, resource_triggered_research)
    registry.register(AUTONOMOUS_RESEARCH, 1, autonomous_research)


def direct_publication(context: MechanismContext) -> MechanismResult:
    """Publish a configured artifact directly, without an evaluation node."""

    parameters = context.mechanism.parameters
    author_id = str(parameters.get("author_id", "researcher-direct"))
    artifact_id = str(parameters.get("artifact_id", "paper-direct"))
    title = str(parameters.get("title", "Directly shared research output"))
    return MechanismResult(
        events=(
            MechanismEvent(
                "agent.registered",
                actor_ids=(author_id,),
                payload={
                    "agent_type": "researcher",
                    "institution": parameters.get("institution", "independent"),
                    "initial_balance": 0,
                    "initial_active": True,
                },
            ),
            MechanismEvent(
                "paper.submitted",
                actor_ids=(author_id,),
                artifact_ids=(artifact_id,),
                payload={
                    "title": title,
                    "conference": None,
                    "topics": list(parameters.get("topics", ())),
                },
            ),
            MechanismEvent(
                "paper.decided",
                actor_ids=(author_id,),
                artifact_ids=(artifact_id,),
                payload={"decision": "published", "route": "direct-publication"},
                provenance={
                    "decision_rule": "publish-on-submission",
                    "evaluation_mechanism": None,
                },
            ),
        )
    )


def curated_publication(context: MechanismContext) -> MechanismResult:
    """Publish through a distinct toy curation implementation."""

    parameters = context.mechanism.parameters
    author_id = str(parameters.get("author_id", "researcher-curated"))
    artifact_id = str(parameters.get("artifact_id", "paper-curated"))
    return MechanismResult(
        events=(
            MechanismEvent(
                "agent.registered",
                actor_ids=(author_id,),
                payload={
                    "agent_type": "researcher",
                    "institution": parameters.get("institution", "curated-lab"),
                    "initial_balance": 0,
                    "initial_active": True,
                },
            ),
            MechanismEvent(
                "paper.submitted",
                actor_ids=(author_id,),
                artifact_ids=(artifact_id,),
                payload={
                    "title": parameters.get("title", "Curated research output"),
                    "conference": "toy-curation-board",
                    "topics": list(parameters.get("topics", ("curated",))),
                },
            ),
            MechanismEvent(
                "paper.decided",
                actor_ids=(author_id,),
                artifact_ids=(artifact_id,),
                payload={"decision": "published", "route": "curated-publication"},
                provenance={
                    "decision_rule": "toy-curation",
                    "evaluation_mechanism": None,
                },
            ),
        )
    )


def community_publication(context: MechanismContext) -> MechanismResult:
    """Publish through the same port contract under a governance family."""

    result = curated_publication(context)
    decision = result.events[-1]
    governed_decision = MechanismEvent(
        decision.event_type,
        actor_ids=decision.actor_ids,
        artifact_ids=decision.artifact_ids,
        payload={**dict(decision.payload), "route": "community-governed"},
        provenance={
            **dict(decision.provenance),
            "decision_rule": "community-governed-publication",
        },
    )
    return MechanismResult(events=(*result.events[:-1], governed_decision))


def fixed_grant(context: MechanismContext) -> MechanismResult:
    """Allocate the same configured amount each period."""

    parameters = context.mechanism.parameters
    recipient_id = str(parameters.get("recipient_id", "researcher-funded"))
    amount = float(parameters.get("amount", 10.0))
    initial_balance = float(parameters.get("initial_balance", 0.0))
    elapsed = context.period - int(parameters.get("start_period", 0))
    before = initial_balance + max(elapsed, 0) * amount
    after = before + amount
    events = []
    if elapsed == 0:
        events.append(
            MechanismEvent(
                "agent.registered",
                actor_ids=(recipient_id,),
                payload={
                    "agent_type": "researcher",
                    "institution": parameters.get("institution", "example-lab"),
                    "initial_balance": initial_balance,
                    "initial_active": True,
                },
            )
        )
    events.append(
        MechanismEvent(
            "resource.changed",
            actor_ids=(recipient_id,),
            payload={
                "balance_before": before,
                "delta": amount,
                "balance_after": after,
                "active_after": True,
                "reason": "fixed-grant",
            },
            provenance={"allocation_rule": "fixed-amount"},
        )
    )
    return MechanismResult(
        outputs={
            "allocations": (
                MechanismValue(
                    {"amount": amount, "recipient_id": recipient_id},
                    actor_ids=(recipient_id,),
                ),
            )
        },
        events=tuple(events),
    )


def matching_grant(context: MechanismContext) -> MechanismResult:
    """Toy alternative that matches a configured base contribution."""

    parameters = context.mechanism.parameters
    recipient_id = str(parameters.get("recipient_id", "researcher-funded"))
    base = float(parameters.get("base_amount", 6.0))
    ratio = float(parameters.get("match_ratio", 0.5))
    amount = base * (1.0 + ratio)
    initial_balance = float(parameters.get("initial_balance", 0.0))
    elapsed = context.period - int(parameters.get("start_period", 0))
    before = initial_balance + max(elapsed, 0) * amount
    after = before + amount
    events = []
    if elapsed == 0:
        events.append(
            MechanismEvent(
                "agent.registered",
                actor_ids=(recipient_id,),
                payload={
                    "agent_type": "researcher",
                    "institution": parameters.get("institution", "matching-lab"),
                    "initial_balance": initial_balance,
                    "initial_active": True,
                },
            )
        )
    events.append(
        MechanismEvent(
            "resource.changed",
            actor_ids=(recipient_id,),
            payload={
                "balance_before": before,
                "delta": amount,
                "balance_after": after,
                "active_after": True,
                "reason": "matching-grant",
            },
            provenance={"allocation_rule": "toy-matching"},
        )
    )
    return MechanismResult(
        outputs={
            "allocations": (
                MechanismValue(
                    {"amount": amount, "recipient_id": recipient_id},
                    actor_ids=(recipient_id,),
                ),
            )
        },
        events=tuple(events),
    )


def resource_triggered_research(context: MechanismContext) -> MechanismResult:
    """Start one project for each delivered resource allocation."""

    allocations = context.inputs["resources"]
    total = sum(float(value.payload["amount"]) for value in allocations)
    actor_ids = tuple(
        dict.fromkeys(
            actor_id for value in allocations for actor_id in value.actor_ids
        )
    )
    return MechanismResult(
        events=(
            MechanismEvent(
                "mechanism.decision",
                actor_ids=actor_ids,
                payload={
                    "decision": "start-research",
                    "resource_amount": total,
                    "allocation_count": len(allocations),
                },
                provenance={"decision_rule": "start-when-resourced"},
            ),
        )
    )


def autonomous_research(context: MechanismContext) -> MechanismResult:
    """Toy implementation that can act without a resource input edge."""

    actor_id = str(
        context.mechanism.parameters.get("actor_id", "researcher-autonomous")
    )
    return MechanismResult(
        events=(
            MechanismEvent(
                "mechanism.decision",
                actor_ids=(actor_id,),
                payload={
                    "decision": "start-autonomous-research",
                    "resource_amount": 0.0,
                    "allocation_count": 0,
                },
                provenance={"decision_rule": "autonomous-start"},
            ),
        )
    )
