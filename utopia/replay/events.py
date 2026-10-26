"""Versioned canonical events shared by replay, analysis, and future UIs.

The envelope deliberately excludes filesystem paths from its identity. A saved
run copied to another machine must produce exactly the same event ids and stream
hash. Sequence is also excluded from the event id: it describes this projection
of the source records, rather than the identity of the source fact.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "scienceutopia.event.v1"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EventEnvelope:
    """A deterministic event with typed references and source provenance."""

    event_id: str
    sequence: int
    year: int
    phase: int
    event_type: str
    actor_ids: tuple[str, ...]
    artifact_ids: tuple[str, ...]
    payload: Mapping[str, Any]
    provenance: Mapping[str, Any]
    schema_version: str = SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        year: int,
        phase: int,
        event_type: str,
        actor_ids: Sequence[str] = (),
        artifact_ids: Sequence[str] = (),
        payload: Mapping[str, Any] | None = None,
        provenance: Mapping[str, Any] | None = None,
    ) -> "EventEnvelope":
        body = {
            "schema_version": SCHEMA_VERSION,
            "year": int(year),
            "phase": int(phase),
            "event_type": str(event_type),
            "actor_ids": list(actor_ids),
            "artifact_ids": list(artifact_ids),
            "payload": dict(payload or {}),
            "provenance": dict(provenance or {}),
        }
        return cls(
            event_id=_hash(body),
            sequence=int(sequence),
            year=body["year"],
            phase=body["phase"],
            event_type=body["event_type"],
            actor_ids=tuple(body["actor_ids"]),
            artifact_ids=tuple(body["artifact_ids"]),
            payload=body["payload"],
            provenance=body["provenance"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "sequence": self.sequence,
            "year": self.year,
            "phase": self.phase,
            "event_type": self.event_type,
            "actor_ids": list(self.actor_ids),
            "artifact_ids": list(self.artifact_ids),
            "payload": dict(self.payload),
            "provenance": dict(self.provenance),
        }


def canonical_event_stream_hash(events: Iterable[EventEnvelope]) -> str:
    """Hash a complete ordered stream, including its canonical sequence."""

    return _hash([event.to_dict() for event in events])


def validate_references(events: Iterable[EventEnvelope]) -> list[str]:
    """Return actor/artifact reference errors in canonical replay order."""

    actors: set[str] = set()
    artifacts: set[str] = set()
    errors: list[str] = []
    expected_sequence = 0

    for event in events:
        if event.sequence != expected_sequence:
            errors.append(
                f"event {event.event_id}: sequence {event.sequence}, expected {expected_sequence}"
            )
        expected_sequence += 1

        declared_actors = set(event.actor_ids) if event.event_type == "agent.registered" else set()
        declared_artifacts = (
            set(event.artifact_ids) if event.event_type == "paper.submitted" else set()
        )
        for actor_id in event.actor_ids:
            if actor_id not in actors and actor_id not in declared_actors:
                errors.append(f"event {event.event_id}: unknown actor {actor_id}")
        for artifact_id in event.artifact_ids:
            if artifact_id not in artifacts and artifact_id not in declared_artifacts:
                errors.append(f"event {event.event_id}: unknown artifact {artifact_id}")
        actors.update(declared_actors)
        artifacts.update(declared_artifacts)

    return errors
