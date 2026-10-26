"""Application and reconciliation of declared evaluation resource effects."""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from .base import LedgerEntry, ResourceEffect


def apply_resource_effects(
    opening_balances: Mapping[str, float],
    effects: Sequence[ResourceEffect],
) -> tuple[tuple[LedgerEntry, ...], dict[str, float]]:
    balances = {
        actor_id: float(balance)
        for actor_id, balance in opening_balances.items()
    }
    entries: list[LedgerEntry] = []
    for effect in effects:
        if effect.actor_id not in balances:
            raise ValueError(
                f"Missing opening balance for resource actor {effect.actor_id}"
            )
        before = balances[effect.actor_id]
        after = before + float(effect.delta)
        entries.append(LedgerEntry(
            effect_id=effect.effect_id,
            decision_id=effect.decision_id,
            actor_id=effect.actor_id,
            category=effect.category,
            delta=float(effect.delta),
            balance_before=before,
            balance_after=after,
        ))
        balances[effect.actor_id] = after
    return tuple(entries), balances


def reconcile_resource_effects(
    effects: Sequence[ResourceEffect],
    ledger: Sequence[LedgerEntry],
) -> list[str]:
    """Return all mismatches between declared effects and ledger rows."""

    errors: list[str] = []
    effect_by_id: dict[str, ResourceEffect] = {}
    for effect in effects:
        if effect.effect_id in effect_by_id:
            errors.append(f"duplicate effect {effect.effect_id}")
        effect_by_id[effect.effect_id] = effect

    seen: set[str] = set()
    last_balance: dict[str, float] = {}
    for entry in ledger:
        effect = effect_by_id.get(entry.effect_id)
        if effect is None:
            errors.append(f"ledger has undeclared effect {entry.effect_id}")
            continue
        if entry.effect_id in seen:
            errors.append(f"ledger repeats effect {entry.effect_id}")
        seen.add(entry.effect_id)
        if (
            entry.decision_id != effect.decision_id
            or entry.actor_id != effect.actor_id
            or entry.category != effect.category
            or not math.isclose(entry.delta, effect.delta)
        ):
            errors.append(f"ledger metadata differs for effect {entry.effect_id}")
        if not math.isclose(
            entry.balance_before + entry.delta, entry.balance_after
        ):
            errors.append(f"ledger arithmetic fails for effect {entry.effect_id}")
        if (
            entry.actor_id in last_balance
            and not math.isclose(
                entry.balance_before, last_balance[entry.actor_id]
            )
        ):
            errors.append(f"ledger chain breaks for actor {entry.actor_id}")
        last_balance[entry.actor_id] = entry.balance_after

    for effect_id in sorted(set(effect_by_id) - seen):
        errors.append(f"declared effect missing from ledger {effect_id}")
    return errors
