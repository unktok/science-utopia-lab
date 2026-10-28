"""Build browser-safe replay artifacts from canonical events.

The browser intentionally receives projected frames rather than reimplementing
ScienceUtopia's domain transitions in JavaScript. This module is the boundary
between the authoritative replay projector and presentation-only clients.

Replay-view v1 remains unchanged. Replay-view v2 makes the epistemic boundary
visible in the data: canonical facts, authoritative projections, deterministic
visual choreography, and non-scientific ambience are separate sections.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import re
from typing import Any, Iterable, Mapping, Sequence

from .events import EventEnvelope, canonical_event_stream_hash, validate_references
from .projector import replay


VIEW_SCHEMA_VERSION = "scienceutopia.replay-view.v1"
VIEW_SCHEMA_VERSION_V2 = "scienceutopia.replay-view.v2"
DERIVATION_VERSION_V2 = "scienceutopia.game-choreography.v2.0.0"
TRUTH_STATUSES = frozenset({"canonical", "derived", "ambient"})
FLOW_TYPES = ("data", "paper", "review", "funding", "citation", "policy")


def build_viewer_payload(
    events: Iterable[EventEnvelope],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the stable v1 events-and-frames payload.

    This function intentionally continues to emit exactly the v1 contract.
    New clients should opt in to :func:`build_viewer_payload_v2`.
    """

    ordered = list(events)
    errors = validate_references(ordered)
    if errors:
        raise ValueError("Invalid canonical event references: " + "; ".join(errors))

    frames = [{
        "cursor": 0,
        "event_id": None,
        "state": replay([]).to_dict(),
    }]
    for cursor in range(1, len(ordered) + 1):
        frames.append({
            "cursor": cursor,
            "event_id": ordered[cursor - 1].event_id,
            "state": replay(ordered[:cursor]).to_dict(),
        })

    return {
        "schema_version": VIEW_SCHEMA_VERSION,
        "event_schema_version": (
            ordered[0].schema_version if ordered else "scienceutopia.event.v1"
        ),
        "stream_hash": canonical_event_stream_hash(ordered),
        "metadata": dict(metadata or {}),
        "events": [event.to_dict() for event in ordered],
        "frames": frames,
    }


def _trace(
    truth_status: str,
    *,
    event_ids: Sequence[str] = (),
    logical_timestamp_ms: int = 0,
    duration_ms: int = 0,
    causal_parent_id: str | None = None,
) -> dict[str, Any]:
    if truth_status not in TRUTH_STATUSES:
        raise ValueError(f"Unsupported truth status: {truth_status}")
    if truth_status == "ambient" and event_ids:
        raise ValueError("Ambient records cannot cite canonical events")
    if truth_status == "derived" and not event_ids:
        raise ValueError("Derived records must cite at least one canonical event")
    return {
        "truth_status": truth_status,
        "derived_from_event_ids": list(event_ids),
        "derivation_version": DERIVATION_VERSION_V2,
        "logical_timestamp_ms": int(logical_timestamp_ms),
        "duration_ms": int(duration_ms),
        "causal_parent_id": causal_parent_id,
    }


def _institution_id(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "unnamed"
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()[:8]
    return f"institution:{slug}:{digest}"


def _entity_catalog(events: Sequence[EventEnvelope]) -> dict[str, list[dict[str, Any]]]:
    researchers: list[dict[str, Any]] = []
    institutions_by_label: dict[str, list[str]] = defaultdict(list)
    artifacts: list[dict[str, Any]] = []

    for event in events:
        if event.event_type == "agent.registered":
            institution = str(event.payload.get("institution") or "Unassigned")
            institutions_by_label[institution].append(event.event_id)
            researchers.append({
                "id": event.actor_ids[0],
                "kind": "researcher",
                "label": str(event.payload.get("display_name") or event.actor_ids[0]),
                "institution_id": _institution_id(institution),
                **_trace("canonical", event_ids=(event.event_id,)),
            })
        elif event.event_type == "paper.submitted":
            artifacts.append({
                "id": event.artifact_ids[0],
                "kind": "paper",
                "label": str(event.payload.get("title") or event.artifact_ids[0]),
                "author_id": event.actor_ids[0],
                **_trace("canonical", event_ids=(event.event_id,)),
            })

    institutions = [
        {
            "id": _institution_id(label),
            "kind": "institution",
            "label": label,
            # Institution nodes normalize strings on canonical agent records;
            # they are not independently simulated entities.
            **_trace("derived", event_ids=tuple(event_ids)),
        }
        for label, event_ids in sorted(institutions_by_label.items())
    ]
    return {
        "researchers": sorted(researchers, key=lambda row: row["id"]),
        "institutions": institutions,
        "artifacts": sorted(artifacts, key=lambda row: row["id"]),
    }


def _logical_time(event: EventEnvelope, event_count: int) -> int:
    """Map canonical order to a stable 48-second presentation timeline."""

    if event_count <= 1:
        return 0
    return round(event.sequence * 48_000 / (event_count - 1))


def build_viewer_payload_v2(
    events: Iterable[EventEnvelope],
    *,
    metadata: Mapping[str, Any] | None = None,
    choreography: Mapping[str, Any] | None = None,
    ambient: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a truth-status-aware replay-view v2 document.

    ``choreography`` and ``ambient`` are explicit inputs because neither may be
    smuggled into canonical state. The function validates every reference and
    rejects a derived visual record without canonical evidence.
    """

    ordered = list(events)
    errors = validate_references(ordered)
    if errors:
        raise ValueError("Invalid canonical event references: " + "; ".join(errors))

    event_ids = {event.event_id for event in ordered}
    entities = _entity_catalog(ordered)
    facts = [
        {
            "event_id": event.event_id,
            **_trace(
                "canonical",
                event_ids=(event.event_id,),
                logical_timestamp_ms=_logical_time(event, len(ordered)),
            ),
        }
        for event in ordered
    ]

    frames: list[dict[str, Any]] = []
    for cursor in range(len(ordered) + 1):
        prefix = ordered[:cursor]
        source_ids = tuple(event.event_id for event in prefix)
        frames.append({
            "cursor": cursor,
            "event_id": prefix[-1].event_id if prefix else None,
            "state": replay(prefix).to_dict(),
            **(
                _trace(
                    "derived",
                    event_ids=source_ids,
                    logical_timestamp_ms=(
                        _logical_time(prefix[-1], len(ordered)) if prefix else 0
                    ),
                    causal_parent_id=(prefix[-2].event_id if len(prefix) > 1 else None),
                )
                if prefix
                else _trace("canonical")
            ),
        })

    choreography_value = {
        "duration_ms": 48_000,
        "placements": [],
        "flows": [],
        "actions": [],
        "camera_cues": [],
        **dict(choreography or {}),
    }
    ambient_value = {
        "actors": [],
        "effects": [],
        **dict(ambient or {}),
    }
    _validate_v2_visual_records(
        choreography=choreography_value,
        ambient=ambient_value,
        event_ids=event_ids,
        entities=entities,
    )

    metadata_value = {
        "source_kind": "saved_simulation_artifact",
        "empirical": True,
        "disclosure": (
            "Canonical facts come from the exported event stream. Derived visuals "
            "are deterministic projections. Ambient records make no scientific claim."
        ),
        "truth_legend": {
            "canonical": "Direct source fact in the canonical event stream.",
            "derived": "Deterministic projection with source event IDs.",
            "ambient": "Presentation only; not a simulated scientific fact.",
        },
        **dict(metadata or {}),
    }

    return {
        "schema_version": VIEW_SCHEMA_VERSION_V2,
        "event_schema_version": (
            ordered[0].schema_version if ordered else "scienceutopia.event.v1"
        ),
        "stream_hash": canonical_event_stream_hash(ordered),
        "stream_hash_algorithm": "scienceutopia.python-canonical-json-sha256.v1",
        "derivation_version": DERIVATION_VERSION_V2,
        "metadata": metadata_value,
        "canonical": {
            "events": [event.to_dict() for event in ordered],
            "facts": facts,
            "entities": entities,
        },
        "projection": {"frames": frames},
        "choreography": choreography_value,
        "ambient": ambient_value,
    }


def _validate_v2_visual_records(
    *,
    choreography: Mapping[str, Any],
    ambient: Mapping[str, Any],
    event_ids: set[str],
    entities: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    entity_ids = {
        str(entity["id"])
        for group in entities.values()
        for entity in group
    }
    researcher_ids = {
        str(entity["id"])
        for entity in entities.get("researchers", ())
    }
    visual_ids: set[str] = set()
    for group_name in ("placements", "flows", "actions", "camera_cues"):
        for record in choreography.get(group_name, []):
            _validate_trace_record(record, event_ids=event_ids, expected="derived")
            record_id = str(record["id"])
            if record_id in visual_ids:
                raise ValueError(f"Duplicate visual record id: {record_id}")
            visual_ids.add(record_id)
            if group_name == "placements" and record.get("entity_id") not in entity_ids:
                raise ValueError(f"Unknown placement entity: {record.get('entity_id')}")
            if group_name == "flows":
                if record.get("flow_type") not in FLOW_TYPES:
                    raise ValueError(f"Unsupported flow type: {record.get('flow_type')}")
                for endpoint in ("from_entity_id", "to_entity_id"):
                    if record.get(endpoint) not in entity_ids:
                        raise ValueError(f"Unknown flow endpoint: {record.get(endpoint)}")
            if group_name == "actions":
                if record.get("actor_entity_id") not in researcher_ids:
                    raise ValueError(
                        f"Unknown action actor: {record.get('actor_entity_id')}"
                    )
                if record.get("action_type") not in {
                    "move", "experiment", "write", "review", "revise",
                    "allocate", "receive", "read", "cite", "policy",
                }:
                    raise ValueError(
                        f"Unsupported action type: {record.get('action_type')}"
                    )
                for point_name in ("start", "end"):
                    point = record.get(point_name)
                    if not isinstance(point, Mapping) or not all(
                        isinstance(point.get(axis), (int, float))
                        and not isinstance(point.get(axis), bool)
                        for axis in ("x", "y")
                    ):
                        raise ValueError(
                            f"Invalid action {point_name}: {record.get('id')}"
                        )
    for group_name in ("actors", "effects"):
        for record in ambient.get(group_name, []):
            _validate_trace_record(record, event_ids=event_ids, expected="ambient")


def _validate_trace_record(
    record: Mapping[str, Any], *, event_ids: set[str], expected: str
) -> None:
    required = {
        "id",
        "truth_status",
        "derived_from_event_ids",
        "derivation_version",
        "logical_timestamp_ms",
        "duration_ms",
        "causal_parent_id",
    }
    missing = sorted(required - set(record))
    if missing:
        raise ValueError(f"Visual record missing fields {missing}: {record.get('id')}")
    if record["truth_status"] != expected:
        raise ValueError(
            f"{record['id']}: expected truth_status={expected}, got {record['truth_status']}"
        )
    references = set(record["derived_from_event_ids"])
    if expected == "derived" and not references:
        raise ValueError(f"{record['id']}: derived record has no source events")
    if expected == "ambient" and references:
        raise ValueError(f"{record['id']}: ambient record cites canonical events")
    unknown = references - event_ids
    if unknown:
        raise ValueError(f"{record['id']}: unknown source events {sorted(unknown)}")
    if int(record["logical_timestamp_ms"]) < 0 or int(record["duration_ms"]) < 0:
        raise ValueError(f"{record['id']}: negative logical time or duration")
