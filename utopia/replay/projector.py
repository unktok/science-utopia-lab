"""Pure state projection for canonical ScienceUtopia events."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Iterable

from .events import EventEnvelope, validate_references


class ReplayError(ValueError):
    pass


def _same_number(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is right
    return math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)


@dataclass
class WorldState:
    year: int = 0
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    completed_years: list[int] = field(default_factory=list)
    applied_event_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "agents": self.agents,
            "artifacts": self.artifacts,
            "completed_years": self.completed_years,
            "applied_event_ids": self.applied_event_ids,
        }


def replay(events: Iterable[EventEnvelope]) -> WorldState:
    """Replay a canonical stream without simulator or model dependencies."""

    ordered = list(events)
    reference_errors = validate_references(ordered)
    if reference_errors:
        raise ReplayError("; ".join(reference_errors))

    state = WorldState()
    for event in ordered:
        state.year = max(state.year, event.year)
        state.applied_event_ids.append(event.event_id)

        if event.event_type == "agent.registered":
            actor_id = event.actor_ids[0]
            state.agents[actor_id] = {
                "agent_type": event.payload.get("agent_type"),
                "institution": event.payload.get("institution"),
                "balance": event.payload.get("initial_balance"),
                "active": event.payload.get("initial_active", True),
            }
        elif event.event_type == "artifact.created":
            if len(event.artifact_ids) != 1 or event.artifact_ids[0] in state.artifacts:
                raise ReplayError("generic artifact creation requires one new identity")
            state.artifacts[event.artifact_ids[0]] = {
                "artifact_type": event.payload.get("artifact_type"),
                "content": dict(event.payload.get("content", {})),
                "history": [{"year": event.year, "event": "created"}],
            }
        elif event.event_type == "artifact.updated":
            if len(event.artifact_ids) != 1:
                raise ReplayError("generic artifact update requires one identity")
            artifact = state.artifacts[event.artifact_ids[0]]
            if artifact.get("artifact_type") != event.payload.get("artifact_type"):
                raise ReplayError("generic artifact update changes its type")
            artifact["content"] = dict(event.payload.get("content", {}))
            artifact["history"].append({"year": event.year, "event": "updated"})
        elif event.event_type == "paper.submitted":
            paper_id = event.artifact_ids[0]
            paper = state.artifacts.setdefault(
                paper_id, {"reviews": [], "history": []}
            )
            paper.update({
                "title": event.payload.get("title"),
                "author_id": event.actor_ids[0],
                "conference": event.payload.get("conference"),
                "topics": event.payload.get("topics", []),
                "status": "submitted",
            })
            paper["history"].append({"year": event.year, "event": "submitted"})
        elif event.event_type == "review.completed":
            paper = state.artifacts[event.artifact_ids[0]]
            paper["reviews"].append({
                "year": event.year,
                "reviewer_id": event.actor_ids[0],
                "score": event.payload.get("score"),
                "justification": event.payload.get("justification"),
            })
        elif event.event_type == "paper.decided":
            paper = state.artifacts[event.artifact_ids[0]]
            paper["status"] = event.payload.get("decision")
            paper["history"].append({
                "year": event.year,
                "event": "decided",
                "decision": event.payload.get("decision"),
            })
        elif event.event_type == "resource.changed":
            actor_id = event.actor_ids[0]
            agent = state.agents[actor_id]
            before = event.payload.get("balance_before")
            if not _same_number(agent.get("balance"), before):
                raise ReplayError(
                    f"{actor_id} year {event.year}: current balance "
                    f"{agent.get('balance')} does not match ledger balance_before {before}"
                )
            expected_after = float(before) + float(event.payload.get("delta", 0))
            after = event.payload.get("balance_after")
            if not _same_number(expected_after, after):
                raise ReplayError(
                    f"{actor_id} year {event.year}: {before} + "
                    f"{event.payload.get('delta')} does not equal balance_after {after}"
                )
            agent["balance"] = after
            agent["active"] = event.payload.get(
                "active_after", agent.get("active")
            )
        elif event.event_type == "resource.balance_reported":
            actor_id = event.actor_ids[0]
            agent = state.agents[actor_id]
            if not _same_number(
                agent.get("balance"), event.payload.get("closing_balance")
            ):
                raise ReplayError(
                    f"{actor_id} year {event.year}: replayed balance "
                    f"{agent.get('balance')} does not match reported closing balance "
                    f"{event.payload.get('closing_balance')}"
                )
            if not _same_number(event.payload.get("residual", 0), 0):
                raise ReplayError(
                    f"{actor_id} year {event.year}: non-zero resource residual "
                    f"{event.payload.get('residual')}"
                )
            agent["active"] = event.payload.get(
                "closing_active", agent.get("active")
            )
        elif event.event_type == "year.completed":
            state.completed_years.append(event.year)

    return state
