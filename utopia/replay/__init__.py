"""Canonical, read-only replay support for saved ScienceUtopia artifacts."""

from .events import EventEnvelope, canonical_event_stream_hash, validate_references
from .projector import ReplayError, WorldState, replay

__all__ = [
    "ArtifactBundle",
    "EventEnvelope",
    "ReplayError",
    "WorldState",
    "canonical_event_stream_hash",
    "convert_artifacts",
    "replay",
    "validate_references",
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
