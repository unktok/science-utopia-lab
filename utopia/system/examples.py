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
FIXED_GRANT = "example.funding.fixed-grant-v1"
RESOURCE_RESEARCH = "example.research.resource-triggered-v1"


def register_example_mechanisms(registry: MechanismRegistry) -> None:
    """Register examples without giving the graph runner family knowledge."""

    registry.register(DIRECT_PUBLICATION, 1, direct_publication)
    registry.register(FIXED_GRANT, 1, fixed_grant)
    registry.register(RESOURCE_RESEARCH, 1, resource_triggered_research)


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
