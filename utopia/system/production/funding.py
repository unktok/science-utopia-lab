"""Production compact-funding adapter for the generic mechanism boundary.

The ranking validation and expansion is delegated to the same production
function used by prospective funding experiments.  The adapter adds only the
graph port contract, allocation policy, canonical events, and checkpointable
balances; it does not reimplement or weaken the production ranking protocol.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from utopia.funding.compact import expand_compact_result
from utopia.system.production.governance import resolve_active_policy
from utopia.system.runtime import (
    GraphRuntimeError,
    MechanismContext,
    MechanismEvent,
    MechanismRegistry,
    MechanismResult,
    MechanismValue,
)


COMPACT_RANKED_ALLOCATION = "production.funding.compact-ranked-allocation-v1"
STATE_SCHEMA_VERSION = "scienceutopia.compact-funding-state.v2"
LEGACY_STATE_SCHEMA_VERSION = "scienceutopia.compact-funding-state.v1"


def register_compact_funding_mechanism(registry: MechanismRegistry) -> None:
    """Register the production compact-ranking adapter at version 1."""

    registry.register(COMPACT_RANKED_ALLOCATION, 1, compact_ranked_allocation)


def compact_ranked_allocation(context: MechanismContext) -> MechanismResult:
    """Validate ranked panels and allocate fixed awards to top applications.

    Required graph ports are intentionally explicit: ``panels`` is the input
    and ``allocations`` is the output.  Each panel payload contains the frozen
    application metadata and the already-elicited compact model result.  Model
    inference stays outside this deterministic adapter and can be supplied by
    any upstream mechanism implementation.
    """

    state = _restore_state(context.state)
    amount = _positive_number(context.mechanism.parameters.get("award_amount", 1.0))
    default_slots = _positive_int(context.mechanism.parameters.get("award_slots", 1))
    policy_slots = None
    active_policy = resolve_active_policy(
        context.inputs.get("policies", ()),
        target="funding",
        active=state["active_policy"],
        system_fingerprint=context.system_fingerprint,
    )
    state["active_policy"] = active_policy
    if active_policy is not None:
        directive = active_policy["directive"]
        amount = _positive_number(
            amount * directive.get("award_amount_multiplier", 1.0)
        )
        policy_slots = directive.get("award_slots")
    outputs: list[MechanismValue] = []
    events: list[MechanismEvent] = []

    for delivered in context.inputs.get("panels", ()):
        panel = delivered.payload
        panel_id = panel.get("panel_id")
        if not isinstance(panel_id, str) or not panel_id:
            raise GraphRuntimeError("compact funding panel_id must be a non-empty string")
        if panel_id in state["processed_panel_ids"]:
            raise GraphRuntimeError(f"compact funding panel {panel_id!r} was already processed")
        applications = panel.get("applications")
        compact_result = panel.get("compact_result")
        try:
            expanded = expand_compact_result(compact_result, applications)
        except ValueError as exc:
            raise GraphRuntimeError(f"invalid compact funding panel {panel_id!r}: {exc}") from exc
        slots = (
            policy_slots
            if policy_slots is not None
            else panel.get("award_slots", default_slots)
        )
        if isinstance(slots, bool) or not isinstance(slots, int) or slots < 1:
            raise GraphRuntimeError("compact funding award_slots must be a positive integer")
        ranked = expanded["ranked_applications"]
        if slots > len(ranked):
            raise GraphRuntimeError("compact funding award_slots exceeds panel size")

        for row in ranked[:slots]:
            recipient = row["applicant_id"]
            before = float(state["balances"].get(recipient, 0.0))
            after = before + amount
            state["balances"][recipient] = after
            allocation = {
                "panel_id": panel_id,
                "recipient_id": recipient,
                "application_id": row["application_id"],
                "rank": row["rank"],
                "amount": amount,
                "balance_before": before,
                "balance_after": after,
            }
            outputs.append(
                MechanismValue(
                    allocation,
                    actor_ids=(recipient,),
                    artifact_ids=(panel_id,),
                    lineage_event_ids=delivered.lineage_event_ids,
                )
            )
            events.append(
                MechanismEvent(
                    "funding.awarded",
                    payload=allocation,
                    provenance={
                        "ranking_protocol": "ordered_application_ids_v1",
                        "production_adapter": COMPACT_RANKED_ALLOCATION,
                        "government_policy_id": (
                            active_policy["policy_id"]
                            if active_policy is not None
                            else None
                        ),
                        "government_policy_version": (
                            active_policy["policy_version"]
                            if active_policy is not None
                            else None
                        ),
                    },
                )
            )
            state["total_awarded"] += amount
        state["processed_panel_ids"].append(panel_id)

    return MechanismResult(
        outputs={"allocations": tuple(outputs)},
        events=tuple(events),
        next_state=state,
    )


def _restore_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not raw:
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "processed_panel_ids": [],
            "balances": {},
            "total_awarded": 0.0,
            "active_policy": None,
        }
    if raw.get("schema_version") == LEGACY_STATE_SCHEMA_VERSION:
        raw = {**dict(raw), "schema_version": STATE_SCHEMA_VERSION, "active_policy": None}
    if set(raw) != {
        "schema_version",
        "processed_panel_ids",
        "balances",
        "total_awarded",
        "active_policy",
    } or raw.get("schema_version") != STATE_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported compact funding mechanism state")
    panels = raw["processed_panel_ids"]
    balances = raw["balances"]
    total = raw["total_awarded"]
    active_policy = raw["active_policy"]
    if (
        not isinstance(panels, list)
        or any(not isinstance(item, str) or not item for item in panels)
        or len(panels) != len(set(panels))
        or not isinstance(balances, Mapping)
    ):
        raise GraphRuntimeError("invalid compact funding mechanism state")
    normalized_balances: dict[str, float] = {}
    for recipient, balance in balances.items():
        if not isinstance(recipient, str) or not recipient:
            raise GraphRuntimeError("invalid compact funding balance recipient")
        normalized_balances[recipient] = _nonnegative_number(balance)
    normalized_total = _nonnegative_number(total)
    if not math.isclose(
        sum(normalized_balances.values()), normalized_total, rel_tol=0, abs_tol=1e-9
    ):
        raise GraphRuntimeError("compact funding state balances do not sum to total_awarded")
    normalized_policy = resolve_active_policy((), target="funding", active=active_policy)
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "processed_panel_ids": list(panels),
        "balances": normalized_balances,
        "total_awarded": normalized_total,
        "active_policy": normalized_policy,
    }


def _positive_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise GraphRuntimeError("compact funding award_slots must be a positive integer")
    return value


def _positive_number(value: Any) -> float:
    result = _nonnegative_number(value)
    if result <= 0:
        raise GraphRuntimeError("compact funding award_amount must be positive")
    return result


def _nonnegative_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GraphRuntimeError("compact funding amounts must be numbers")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise GraphRuntimeError("compact funding amounts must be finite and non-negative")
    return result
