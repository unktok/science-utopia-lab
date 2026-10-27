"""Canonical, read-only replay support for saved ScienceUtopia artifacts."""

from .events import EventEnvelope, canonical_event_stream_hash, validate_references
from .projector import ReplayError, WorldState, replay
from .viewer import (
    DERIVATION_VERSION_V2,
    FLOW_TYPES,
    VIEW_SCHEMA_VERSION,
    VIEW_SCHEMA_VERSION_V2,
    build_viewer_payload,
    build_viewer_payload_v2,
)
from .vertical_slice import (
    vertical_slice_events,
    vertical_slice_metadata,
    vertical_slice_presentation,
)

__all__ = [
    "ArtifactBundle",
    "EventEnvelope",
    "ReplayError",
    "WorldState",
    "VIEW_SCHEMA_VERSION",
    "VIEW_SCHEMA_VERSION_V2",
    "DERIVATION_VERSION_V2",
    "FLOW_TYPES",
    "build_viewer_payload",
    "build_viewer_payload_v2",
    "canonical_event_stream_hash",
    "convert_artifacts",
    "replay",
    "validate_references",
    "vertical_slice_events",
    "vertical_slice_metadata",
    "vertical_slice_presentation",
]


def __getattr__(name: str):
    # Keep converter unloaded when it is itself executed as a module.
    if name in {"ArtifactBundle", "convert_artifacts"}:
        from .converter import ArtifactBundle, convert_artifacts

        return {
            "ArtifactBundle": ArtifactBundle,
            "convert_artifacts": convert_artifacts,
        }[name]
    raise AttributeError(name)
