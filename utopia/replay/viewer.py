"""Build a browser-safe replay artifact from canonical events.

The browser intentionally receives projected frames rather than reimplementing
ScienceUtopia's domain transitions in JavaScript.  This module is the boundary
between the authoritative replay projector and presentation-only clients.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from .events import EventEnvelope, canonical_event_stream_hash, validate_references
from .projector import replay


VIEW_SCHEMA_VERSION = "scienceutopia.replay-view.v1"


def build_viewer_payload(
    events: Iterable[EventEnvelope],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return events and authoritative projected state at every replay cursor."""

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
