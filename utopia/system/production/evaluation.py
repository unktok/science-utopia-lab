"""Production conference-decision adapter for generic mechanism graphs."""

from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
import io
import math
from typing import Any, Mapping

from utopia.agents.conference import Conference, ConferenceStatus
from utopia.system.production.governance import resolve_active_policy
from utopia.system.runtime import (
    GraphRuntimeError,
    MechanismContext,
    MechanismEvent,
    MechanismRegistry,
    MechanismResult,
    MechanismValue,
)


CONFERENCE_ACCEPTANCE = "production.evaluation.conference-acceptance-v1"
STATE_SCHEMA_VERSION = "scienceutopia.conference-evaluation-state.v2"
LEGACY_STATE_SCHEMA_VERSION = "scienceutopia.conference-evaluation-state.v1"


def register_conference_evaluation_mechanism(registry: MechanismRegistry) -> None:
    registry.register(CONFERENCE_ACCEPTANCE, 1, conference_acceptance)


def conference_acceptance(context: MechanismContext) -> MechanismResult:
    """Run the production conference acceptance rule over typed review batches."""

    state = _restore_state(context.state)
    rate = _acceptance_rate(context.mechanism.parameters.get("acceptance_rate", 0.2))
    active_policy = resolve_active_policy(
        context.inputs.get("policies", ()),
        target="evaluation",
        active=state["active_policy"],
        system_fingerprint=context.system_fingerprint,
    )
    state["active_policy"] = active_policy
    if active_policy is not None:
        rate = active_policy["directive"]["acceptance_rate"]
    mode = context.mechanism.parameters.get("acceptance_mode", "rate")
    if mode not in {"rate", "fixed_slots"}:
        raise GraphRuntimeError("conference acceptance_mode must be rate or fixed_slots")
    seed = context.mechanism.parameters.get("tiebreak_seed")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise GraphRuntimeError("conference tiebreak_seed must be an integer or null")

    outputs: list[MechanismValue] = []
    events: list[MechanismEvent] = []
    for delivered in context.inputs.get("review_batches", ()):
        batch = delivered.payload
        batch_id = _nonempty_string(batch.get("batch_id"), "review batch_id")
        if batch_id in state["processed_batch_ids"]:
            raise GraphRuntimeError(f"review batch {batch_id!r} was already processed")
        conference_id = _nonempty_string(
            batch.get("conference_id"), "review conference_id"
        )
        papers = batch.get("papers")
        reviews = batch.get("reviews")
        if not isinstance(papers, list) or not papers:
            raise GraphRuntimeError("review batch papers must be a non-empty list")
        if not isinstance(reviews, Mapping):
            raise GraphRuntimeError("review batch reviews must be a mapping")
        normalized_papers = deepcopy(papers)
        paper_ids = [_paper_id(paper) for paper in normalized_papers]
        if len(paper_ids) != len(set(paper_ids)):
            raise GraphRuntimeError("review batch paper ids must be unique")
        if set(reviews) != set(paper_ids):
            raise GraphRuntimeError("review batch must have reviews for exactly every paper")

        conference = Conference(
            conference_id=conference_id,
            name=str(batch.get("conference_name", conference_id)),
            topics=list(batch.get("topics", [])),
            acceptance_rate=rate,
            year=context.period,
        )
        # Production simulation also assigns a scheduled rate immediately
        # before decisions; this overrides the global default-rate config.
        conference.acceptance_rate = rate
        conference.status = ConferenceStatus.UNDER_REVIEW
        conference.submitted_papers = normalized_papers
        conference.reviews = deepcopy(dict(reviews))
        prior_slots = state["fixed_slots_by_conference"].get(conference_id)
        conference.fixed_slots = prior_slots
        try:
            # The production class prints an operator summary and adds wall
            # clock fields. The adapter captures the print and excludes those
            # non-semantic timestamps from its typed deterministic boundary.
            with redirect_stdout(io.StringIO()):
                conference.make_acceptance_decisions(
                    tiebreak_seed=seed,
                    acceptance_mode=mode,
                )
        except (AssertionError, KeyError, TypeError, ValueError) as exc:
            raise GraphRuntimeError(
                f"production conference decision failed for {batch_id!r}: {exc}"
            ) from exc
        if mode == "fixed_slots":
            state["fixed_slots_by_conference"][conference_id] = conference.fixed_slots

        for decision in ("accept", "reject"):
            for paper in conference.decisions[decision]:
                paper_payload = {
                    key: deepcopy(value)
                    for key, value in paper.items()
                    if key != "decision_time"
                }
                payload = {
                    "batch_id": batch_id,
                    "conference_id": conference_id,
                    "paper_id": _paper_id(paper),
                    "decision": decision,
                    "final_score": float(paper["final_score"]),
                    "paper": paper_payload,
                }
                author_ids = _author_ids(paper.get("author_id"))
                outputs.append(
                    MechanismValue(
                        payload,
                        actor_ids=author_ids,
                        artifact_ids=(payload["paper_id"],),
                        lineage_event_ids=delivered.lineage_event_ids,
                    )
                )
                events.append(
                    MechanismEvent(
                        "evaluation.paper_decided",
                        payload={
                            key: payload[key]
                            for key in (
                                "batch_id",
                                "conference_id",
                                "paper_id",
                                "decision",
                                "final_score",
                            )
                        },
                        provenance={
                            "production_adapter": CONFERENCE_ACCEPTANCE,
                            "acceptance_mode": mode,
                            "acceptance_rate": rate,
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
                state["decision_counts"][decision] += 1
        state["processed_batch_ids"].append(batch_id)

    return MechanismResult(
        outputs={"decisions": tuple(outputs)},
        events=tuple(events),
        next_state=state,
    )


def _restore_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not raw:
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "processed_batch_ids": [],
            "fixed_slots_by_conference": {},
            "decision_counts": {"accept": 0, "reject": 0},
            "active_policy": None,
        }
    if raw.get("schema_version") == LEGACY_STATE_SCHEMA_VERSION:
        raw = {**dict(raw), "schema_version": STATE_SCHEMA_VERSION, "active_policy": None}
    required = {
        "schema_version",
        "processed_batch_ids",
        "fixed_slots_by_conference",
        "decision_counts",
        "active_policy",
    }
    if set(raw) != required or raw.get("schema_version") != STATE_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported conference evaluation mechanism state")
    batches = raw["processed_batch_ids"]
    slots = raw["fixed_slots_by_conference"]
    counts = raw["decision_counts"]
    active_policy = raw["active_policy"]
    if (
        not isinstance(batches, list)
        or any(not isinstance(item, str) or not item for item in batches)
        or len(batches) != len(set(batches))
        or not isinstance(slots, Mapping)
        or not isinstance(counts, Mapping)
        or set(counts) != {"accept", "reject"}
    ):
        raise GraphRuntimeError("invalid conference evaluation mechanism state")
    normalized_slots: dict[str, int] = {}
    for conference_id, value in slots.items():
        if not isinstance(conference_id, str) or not conference_id:
            raise GraphRuntimeError("invalid conference id in fixed-slot state")
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise GraphRuntimeError("invalid conference fixed-slot state")
        normalized_slots[conference_id] = value
    normalized_counts: dict[str, int] = {}
    for decision in ("accept", "reject"):
        value = counts[decision]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise GraphRuntimeError("invalid conference decision count state")
        normalized_counts[decision] = value
    normalized_policy = resolve_active_policy(
        (), target="evaluation", active=active_policy
    )
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "processed_batch_ids": list(batches),
        "fixed_slots_by_conference": normalized_slots,
        "decision_counts": normalized_counts,
        "active_policy": normalized_policy,
    }


def _acceptance_rate(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GraphRuntimeError("conference acceptance_rate must be numeric")
    rate = float(value)
    if not math.isfinite(rate) or not 0 <= rate <= 1:
        raise GraphRuntimeError("conference acceptance_rate must be between zero and one")
    return rate


def _paper_id(paper: Any) -> str:
    if not isinstance(paper, Mapping):
        raise GraphRuntimeError("review batch papers must be mappings")
    return _nonempty_string(paper.get("id", paper.get("paper_id")), "paper id")


def _author_ids(value: Any) -> tuple[str, ...]:
    values = value if isinstance(value, list) else [value]
    if any(not isinstance(item, str) or not item for item in values):
        raise GraphRuntimeError("paper author_id must be a string or list of strings")
    return tuple(values)


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise GraphRuntimeError(f"{label} must be a non-empty string")
    return value
