"""Production paper-tracker adapter for generic mechanism graphs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from utopia.data.paper_tracker import PaperTracker
from utopia.system.runtime import (
    GraphRuntimeError,
    MechanismContext,
    MechanismEvent,
    MechanismRegistry,
    MechanismResult,
    MechanismValue,
)


PAPER_TRACKER_PUBLICATION = "production.publication.paper-tracker-v1"
STATE_SCHEMA_VERSION = "scienceutopia.paper-tracker-publication-state.v1"


def register_paper_tracker_publication_mechanism(
    registry: MechanismRegistry,
) -> None:
    registry.register(PAPER_TRACKER_PUBLICATION, 1, paper_tracker_publication)


def paper_tracker_publication(context: MechanismContext) -> MechanismResult:
    """Persist typed paper decisions through the production ``PaperTracker``."""

    state = _restore_state(context.state)
    tracker = PaperTracker.from_dict(
        {"output_dir": ".", "papers": deepcopy(state["papers"])}
    )
    outputs: list[MechanismValue] = []
    events: list[MechanismEvent] = []

    for delivered in context.inputs.get("decisions", ()):
        decision = delivered.payload
        batch_id = _nonempty_string(decision.get("batch_id"), "decision batch_id")
        paper_id = _nonempty_string(decision.get("paper_id"), "decision paper_id")
        decision_id = f"{batch_id}:{paper_id}"
        if decision_id in state["processed_decision_ids"]:
            raise GraphRuntimeError(f"paper decision {decision_id!r} was already recorded")
        status = decision.get("decision")
        if status not in {"accept", "reject"}:
            raise GraphRuntimeError("paper decision must be accept or reject")
        paper = decision.get("paper")
        if not isinstance(paper, Mapping):
            raise GraphRuntimeError("paper decision must contain paper metadata")
        pending = deepcopy(dict(paper))
        pending.update({"id": paper_id, "type": "submission", "status": "pending"})
        final = deepcopy(pending)
        final.update(
            {
                "status": status,
                "final_score": decision.get("final_score"),
                "reviews": deepcopy(paper.get("reviews", [])),
            }
        )
        try:
            tracker.add_or_update_paper(pending)
            archived = tracker.add_or_update_paper(final)
        except (AssertionError, KeyError, TypeError, ValueError) as exc:
            raise GraphRuntimeError(
                f"production paper tracker failed for {decision_id!r}: {exc}"
            ) from exc

        record = {
            "decision_id": decision_id,
            "batch_id": batch_id,
            "paper_id": paper_id,
            "status": archived.status,
            "year": archived.year,
            "conference": archived.conference,
            "author_ids": archived.all_author_ids,
            "review_rounds": len(archived.review_history),
        }
        outputs.append(
            MechanismValue(
                record,
                actor_ids=tuple(archived.all_author_ids),
                artifact_ids=(paper_id,),
                lineage_event_ids=delivered.lineage_event_ids,
            )
        )
        events.append(
            MechanismEvent(
                "publication.recorded",
                payload=record,
                provenance={"production_adapter": PAPER_TRACKER_PUBLICATION},
            )
        )
        state["processed_decision_ids"].append(decision_id)
        state["status_counts"][status] += 1

    state["papers"] = tracker.to_dict()["papers"]
    return MechanismResult(
        outputs={"records": tuple(outputs)},
        events=tuple(events),
        next_state=state,
    )


def _restore_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not raw:
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "processed_decision_ids": [],
            "status_counts": {"accept": 0, "reject": 0},
            "papers": [],
        }
    required = {
        "schema_version",
        "processed_decision_ids",
        "status_counts",
        "papers",
    }
    if set(raw) != required or raw.get("schema_version") != STATE_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported paper tracker publication state")
    decisions = raw["processed_decision_ids"]
    counts = raw["status_counts"]
    papers = raw["papers"]
    if (
        not isinstance(decisions, list)
        or any(not isinstance(item, str) or not item for item in decisions)
        or len(decisions) != len(set(decisions))
        or not isinstance(counts, Mapping)
        or set(counts) != {"accept", "reject"}
        or not isinstance(papers, list)
        or any(not isinstance(paper, Mapping) for paper in papers)
    ):
        raise GraphRuntimeError("invalid paper tracker publication state")
    normalized_counts: dict[str, int] = {}
    for status in ("accept", "reject"):
        value = counts[status]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise GraphRuntimeError("invalid publication status count state")
        normalized_counts[status] = value
    paper_ids = [paper.get("id") for paper in papers]
    if any(not isinstance(item, str) or not item for item in paper_ids):
        raise GraphRuntimeError("publication state contains invalid paper ids")
    if len(paper_ids) != len(set(paper_ids)):
        raise GraphRuntimeError("publication state contains duplicate paper ids")
    if len(decisions) != len(papers) or sum(normalized_counts.values()) != len(papers):
        raise GraphRuntimeError("publication state counts do not match archived papers")
    actual_counts = {
        status: sum(paper.get("status") == status for paper in papers)
        for status in ("accept", "reject")
    }
    if actual_counts != normalized_counts:
        raise GraphRuntimeError("publication status counts do not match paper statuses")
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "processed_decision_ids": list(decisions),
        "status_counts": normalized_counts,
        "papers": deepcopy(papers),
    }


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise GraphRuntimeError(f"{label} must be a non-empty string")
    return value
