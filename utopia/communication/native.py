"""Native prospective execution of production knowledge brokers.

This module is independent of the simulator's citation generation.  It
observes accepted outputs at the completed-year boundary, emits typed
knowledge messages, and delivers them to one explicit receiver after a
SystemSpec-defined latency.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence

from utopia.replay.events import EventEnvelope, SCHEMA_VERSION
from utopia.system.model import (
    ArtifactTypeSpec,
    ChannelKind,
    ConnectionSpec,
    MechanismFamily,
    MechanismSpec,
    PortSpec,
    ScheduleSpec,
    SystemSpec,
)
from utopia.system.production.communication import (
    KNOWLEDGE_BROADCAST,
    KNOWLEDGE_DIGEST,
    KNOWLEDGE_ITEM_SCHEMA_VERSION,
    KNOWLEDGE_MESSAGE_SCHEMA_VERSION,
    knowledge_broadcast,
    knowledge_digest,
    parse_knowledge_item,
    parse_knowledge_message,
)
from utopia.system.runtime import (
    DeliveredValue,
    GraphRuntimeError,
    MechanismContext,
    MechanismResult,
    MechanismValue,
)
from utopia.system.validation import validate_system_spec


NATIVE_COMMUNICATION_OVERLAY = "scienceutopia.native-communication-overlay.v1"
NATIVE_COMMUNICATION_SOURCE = "native.communication.accepted-output-source-v1"
NATIVE_COMMUNICATION_RECEIVER = "native.communication.researcher-receiver-v1"
NATIVE_COMMUNICATION_STATE = "scienceutopia.native-communication-state.v1"

SOURCE_MECHANISM_ID = "native.communication.accepted-output-source"
BROKER_MECHANISM_ID = "native.communication.knowledge-broker"
RECEIVER_MECHANISM_ID = "native.communication.researcher-receiver"

SOURCE_EVENT_TYPE = "native.communication.source_observed"
MESSAGE_EVENT_TYPE = "native.communication.message_emitted"
RECEIVER_EVENT_TYPE = "native.communication.message_received"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class NativeCommunicationError(ValueError):
    """Native communication configuration or checkpoint is invalid."""


@dataclass(frozen=True)
class NativeCommunicationConfig:
    mode: str
    digest_size: int
    latency: int
    receiver_role: str
    system_fingerprint: str
    source_mechanism_id: str = SOURCE_MECHANISM_ID
    broker_mechanism_id: str = BROKER_MECHANISM_ID
    receiver_mechanism_id: str = RECEIVER_MECHANISM_ID

    def validate(self) -> None:
        if self.mode not in {"broadcast", "digest"}:
            raise NativeCommunicationError("mode must be broadcast or digest")
        if type(self.digest_size) is not int or self.digest_size < 1:
            raise NativeCommunicationError("digest_size must be positive")
        if type(self.latency) is not int or self.latency < 0:
            raise NativeCommunicationError("latency must be nonnegative")
        if not isinstance(self.receiver_role, str) or not self.receiver_role:
            raise NativeCommunicationError("receiver_role must be non-empty")
        if not _SHA256.fullmatch(self.system_fingerprint):
            raise NativeCommunicationError("system_fingerprint must be lowercase SHA-256")
        for name in (
            "source_mechanism_id", "broker_mechanism_id", "receiver_mechanism_id"
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise NativeCommunicationError(f"{name} must be non-empty")

    @property
    def implementation(self) -> str:
        return KNOWLEDGE_BROADCAST if self.mode == "broadcast" else KNOWLEDGE_DIGEST

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "digest_size": self.digest_size,
            "latency": self.latency,
            "receiver_role": self.receiver_role,
            "system_fingerprint": self.system_fingerprint,
            "source_mechanism_id": self.source_mechanism_id,
            "broker_mechanism_id": self.broker_mechanism_id,
            "receiver_mechanism_id": self.receiver_mechanism_id,
        }


def native_config_from_namespace(namespace: Any) -> NativeCommunicationConfig | None:
    """Build the native config from parsed simulator arguments; off means absent."""

    mode = getattr(namespace, "communication_broker_mode", "off")
    if mode == "off":
        return None
    config = NativeCommunicationConfig(
        mode=mode,
        digest_size=getattr(namespace, "communication_digest_size", None),
        latency=getattr(namespace, "communication_latency", None),
        receiver_role=getattr(namespace, "communication_receiver_role", None),
        system_fingerprint=getattr(namespace, "communication_system_fingerprint", None),
    )
    config.validate()
    return config


def native_communication_system_spec(
    base: SystemSpec,
    *,
    mode: str,
    digest_size: int = 2,
    latency: int = 0,
    receiver_role: str = "research-community",
) -> SystemSpec:
    """Add one exact native source/broker/receiver overlay to a legacy spec."""

    if mode not in {"broadcast", "digest"}:
        raise NativeCommunicationError("mode must be broadcast or digest")
    if type(digest_size) is not int or digest_size < 1:
        raise NativeCommunicationError("digest_size must be positive")
    if type(latency) is not int or latency < 0:
        raise NativeCommunicationError("latency must be nonnegative")
    if not receiver_role:
        raise NativeCommunicationError("receiver_role must be non-empty")
    if "native_communication" in base.metadata:
        raise NativeCommunicationError("SystemSpec already declares native communication")
    if any(
        item.mechanism_id in {
            SOURCE_MECHANISM_ID, BROKER_MECHANISM_ID, RECEIVER_MECHANISM_ID
        }
        for item in base.mechanisms
    ):
        raise NativeCommunicationError("native communication mechanism id already exists")
    artifact_ids = {item.artifact_type_id for item in base.artifact_types}
    if artifact_ids & {"knowledge-item", "knowledge-message"}:
        raise NativeCommunicationError("native communication artifact id already exists")

    source = MechanismSpec(
        SOURCE_MECHANISM_ID,
        MechanismFamily.COMMUNICATION,
        NATIVE_COMMUNICATION_SOURCE,
        inputs=(PortSpec("publications", ChannelKind.ARTIFACT, "published-output"),),
        outputs=(PortSpec("knowledge", ChannelKind.ARTIFACT, "knowledge-item"),),
    )
    implementation = KNOWLEDGE_BROADCAST if mode == "broadcast" else KNOWLEDGE_DIGEST
    broker = MechanismSpec(
        BROKER_MECHANISM_ID,
        MechanismFamily.COMMUNICATION,
        implementation,
        inputs=(PortSpec("knowledge", ChannelKind.ARTIFACT, "knowledge-item"),),
        outputs=(PortSpec("messages", ChannelKind.SIGNAL, "knowledge-message"),),
        parameters={
            "mode": mode,
            "digest_size": digest_size,
            "delivery_latency": latency,
        },
    )
    receiver = MechanismSpec(
        RECEIVER_MECHANISM_ID,
        MechanismFamily.RESEARCH,
        NATIVE_COMMUNICATION_RECEIVER,
        inputs=(PortSpec("messages", ChannelKind.SIGNAL, "knowledge-message"),),
        parameters={"receiver_role": receiver_role},
    )
    spec = replace(
        base,
        system_id=f"{base.system_id}-native-communication-{mode}",
        artifact_types=base.artifact_types + (
            ArtifactTypeSpec("knowledge-item", "Typed accepted-output observation"),
            ArtifactTypeSpec("knowledge-message", "Versioned broker message"),
        ),
        mechanisms=base.mechanisms + (source, broker, receiver),
        connections=base.connections + (
            ConnectionSpec(
                "legacy.publication", "publications",
                SOURCE_MECHANISM_ID, "publications", ChannelKind.ARTIFACT,
            ),
            ConnectionSpec(
                SOURCE_MECHANISM_ID, "knowledge",
                BROKER_MECHANISM_ID, "knowledge", ChannelKind.ARTIFACT,
            ),
            ConnectionSpec(
                BROKER_MECHANISM_ID, "messages",
                RECEIVER_MECHANISM_ID, "messages", ChannelKind.SIGNAL,
                latency=latency,
            ),
        ),
        schedules=base.schedules + (
            ScheduleSpec(SOURCE_MECHANISM_ID, 6),
            ScheduleSpec(BROKER_MECHANISM_ID, 7),
            ScheduleSpec(RECEIVER_MECHANISM_ID, 8),
        ),
        global_invariants=base.global_invariants + (
            "native-communication-lineage",
            "native-communication-fingerprint-bound",
        ),
        metadata={
            **base.metadata,
            "native_communication": {
                "schema": NATIVE_COMMUNICATION_OVERLAY,
                "base_system_id": base.system_id,
                "mode": mode,
                "digest_size": digest_size,
                "latency": latency,
                "receiver_role": receiver_role,
            },
        },
    )
    validate_system_spec(spec).require_valid()
    return spec


def split_native_communication_system_spec(
    spec: SystemSpec,
) -> tuple[SystemSpec, NativeCommunicationConfig | None]:
    """Validate and remove the exact native overlay for legacy compilation."""

    raw = spec.metadata.get("native_communication")
    if raw is None:
        return spec, None
    if not isinstance(raw, Mapping) or set(raw) != {
        "schema", "base_system_id", "mode", "digest_size", "latency", "receiver_role"
    }:
        raise NativeCommunicationError("native communication metadata is invalid")
    if raw["schema"] != NATIVE_COMMUNICATION_OVERLAY:
        raise NativeCommunicationError("native communication overlay schema is unsupported")
    mechanism_ids = {
        SOURCE_MECHANISM_ID, BROKER_MECHANISM_ID, RECEIVER_MECHANISM_ID
    }
    mechanisms = {item.mechanism_id: item for item in spec.mechanisms}
    if not mechanism_ids <= set(mechanisms):
        raise NativeCommunicationError("native communication overlay nodes are incomplete")
    source = mechanisms[SOURCE_MECHANISM_ID]
    broker = mechanisms[BROKER_MECHANISM_ID]
    receiver = mechanisms[RECEIVER_MECHANISM_ID]
    mode = raw["mode"]
    expected_implementation = (
        KNOWLEDGE_BROADCAST if mode == "broadcast" else KNOWLEDGE_DIGEST
        if mode == "digest" else None
    )
    if (
        source.family != MechanismFamily.COMMUNICATION
        or source.implementation != NATIVE_COMMUNICATION_SOURCE
        or source.parameters
        or broker.family != MechanismFamily.COMMUNICATION
        or broker.implementation != expected_implementation
        or dict(broker.parameters) != {
            "mode": mode,
            "digest_size": raw["digest_size"],
            "delivery_latency": raw["latency"],
        }
        or receiver.family != MechanismFamily.RESEARCH
        or receiver.implementation != NATIVE_COMMUNICATION_RECEIVER
        or dict(receiver.parameters) != {"receiver_role": raw["receiver_role"]}
    ):
        raise NativeCommunicationError("native communication node contract changed")
    expected_edges = {
        (
            "legacy.publication", "publications", SOURCE_MECHANISM_ID,
            "publications", ChannelKind.ARTIFACT, 0,
        ),
        (
            SOURCE_MECHANISM_ID, "knowledge", BROKER_MECHANISM_ID,
            "knowledge", ChannelKind.ARTIFACT, 0,
        ),
        (
            BROKER_MECHANISM_ID, "messages", RECEIVER_MECHANISM_ID,
            "messages", ChannelKind.SIGNAL, raw["latency"],
        ),
    }
    overlay_edges = {
        (
            edge.source_mechanism, edge.source_port, edge.target_mechanism,
            edge.target_port, edge.channel, edge.latency,
        )
        for edge in spec.connections
        if edge.source_mechanism in mechanism_ids or edge.target_mechanism in mechanism_ids
    }
    if overlay_edges != expected_edges:
        raise NativeCommunicationError("native communication edges or latency changed")
    expected_schedules = {
        (SOURCE_MECHANISM_ID, 6, "annual"),
        (BROKER_MECHANISM_ID, 7, "annual"),
        (RECEIVER_MECHANISM_ID, 8, "annual"),
    }
    schedules = {
        (item.mechanism_id, item.phase, item.trigger)
        for item in spec.schedules if item.mechanism_id in mechanism_ids
    }
    if schedules != expected_schedules:
        raise NativeCommunicationError("native communication schedule changed")
    added_artifacts = {"knowledge-item", "knowledge-message"}
    present_added = {
        item.artifact_type_id for item in spec.artifact_types
        if item.artifact_type_id in added_artifacts
    }
    if present_added != added_artifacts:
        raise NativeCommunicationError("native communication artifact types are incomplete")

    base_metadata = dict(spec.metadata)
    base_metadata.pop("native_communication")
    base_invariants = tuple(
        item for item in spec.global_invariants
        if item not in {
            "native-communication-lineage",
            "native-communication-fingerprint-bound",
        }
    )
    base = replace(
        spec,
        system_id=raw["base_system_id"],
        artifact_types=tuple(
            item for item in spec.artifact_types
            if item.artifact_type_id not in added_artifacts
        ),
        mechanisms=tuple(
            item for item in spec.mechanisms if item.mechanism_id not in mechanism_ids
        ),
        connections=tuple(
            edge for edge in spec.connections
            if edge.source_mechanism not in mechanism_ids
            and edge.target_mechanism not in mechanism_ids
        ),
        schedules=tuple(
            item for item in spec.schedules if item.mechanism_id not in mechanism_ids
        ),
        global_invariants=base_invariants,
        metadata=base_metadata,
    )
    validate_system_spec(base).require_valid()
    expected = native_communication_system_spec(
        base,
        mode=mode,
        digest_size=raw["digest_size"],
        latency=raw["latency"],
        receiver_role=raw["receiver_role"],
    )
    if expected.to_dict() != spec.to_dict():
        raise NativeCommunicationError(
            "native communication overlay differs from the exact executable contract"
        )
    config = NativeCommunicationConfig(
        mode=mode,
        digest_size=raw["digest_size"],
        latency=raw["latency"],
        receiver_role=raw["receiver_role"],
        system_fingerprint=spec.fingerprint,
    )
    config.validate()
    return base, config


class NativeCommunicationBroker:
    """Deterministic native state machine with canonical causal events."""

    def __init__(
        self,
        config: NativeCommunicationConfig,
        state: Mapping[str, Any] | None = None,
    ) -> None:
        config.validate()
        self.config = config
        self._state = self._restore(state or {})

    @property
    def events(self) -> tuple[EventEnvelope, ...]:
        return tuple(_event_from_dict(item) for item in self._state["events"])

    @property
    def checkpoint_fingerprint(self) -> str:
        return _fingerprint(self.to_dict())

    def step(self, year: int, accepted_outputs: Iterable[Any]) -> tuple[EventEnvelope, ...]:
        if type(year) is not int or year != self._state["last_completed_year"] + 1:
            raise NativeCommunicationError("communication years must be contiguous")
        before = len(self._state["events"])
        self._deliver_due(year)
        new_entries = []
        for paper in sorted(accepted_outputs, key=lambda item: str(_paper_value(item, "id"))):
            entry = self._observe_output(year, paper)
            if entry is not None:
                new_entries.append(entry)
        self._run_production_broker(year, new_entries)
        self._deliver_due(year)
        self._state["last_completed_year"] = year
        self._validate_state(self._state)
        return self.events[before:]

    def summary(self) -> dict[str, Any]:
        return {
            "mode": self.config.mode,
            "system_fingerprint": self.config.system_fingerprint,
            "processed_outputs": len(self._state["processed_output_ids"]),
            "emitted_messages": len(self._state["emitted_message_ids"]),
            "received_messages": len(self._state["received_message_ids"]),
            "buffered_items": len(
                self._state["production_broker_state"].get("buffer", ())
            ),
            "pending_deliveries": len(self._state["pending_deliveries"]),
            "checkpoint_fingerprint": self.checkpoint_fingerprint,
        }

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self._state)

    def _observe_output(self, year: int, paper: Any) -> dict[str, Any] | None:
        paper_id = _nonempty_string(_paper_value(paper, "id"), "paper id")
        if paper_id in self._state["processed_output_ids"]:
            return None
        status = _paper_value(paper, "status")
        if status != "accept":
            raise NativeCommunicationError("native communication accepts only accepted outputs")
        paper_year = _paper_value(paper, "year")
        if type(paper_year) is not int or paper_year != year:
            raise NativeCommunicationError("accepted output year differs from broker year")
        title = _nonempty_string(_paper_value(paper, "title"), "paper title")
        topics = _paper_value(paper, "topics")
        if not isinstance(topics, list) or any(not isinstance(item, str) for item in topics):
            raise NativeCommunicationError("paper topics must be a string list")
        authors = _paper_value(paper, "author_id")
        author_ids = authors if isinstance(authors, list) else [authors]
        if not author_ids or any(not isinstance(item, str) or not item for item in author_ids):
            raise NativeCommunicationError("paper authors must be non-empty ids")
        knowledge_id = (
            "native-knowledge-"
            + _fingerprint({
                "system_fingerprint": self.config.system_fingerprint,
                "paper_id": paper_id,
                "year": year,
            })[:20]
        )
        item = parse_knowledge_item({
            "schema_version": KNOWLEDGE_ITEM_SCHEMA_VERSION,
            "knowledge_id": knowledge_id,
            "origin_mechanism": self.config.source_mechanism_id,
            "created_period": year,
            "topic": topics[0] if topics else "unspecified",
            "summary": title,
            "evidence_artifact_ids": [paper_id],
        })
        event = self._append_event(
            year=year,
            phase=6,
            event_type=SOURCE_EVENT_TYPE,
            actor_ids=author_ids,
            artifact_ids=(paper_id,),
            payload={
                "knowledge_item": item,
                "source_output_id": paper_id,
                "system_fingerprint": self.config.system_fingerprint,
            },
            provenance={
                "native_mechanism": self.config.source_mechanism_id,
                "namespace": "native.communication",
            },
        )
        self._state["processed_output_ids"].append(paper_id)
        self._state["source_event_ids"].append(event.event_id)
        return {"item": item, "source_event_id": event.event_id}

    def _run_production_broker(
        self,
        year: int,
        entries: Sequence[Mapping[str, Any]],
    ) -> None:
        inputs = tuple(
            DeliveredValue(
                channel=ChannelKind.ARTIFACT,
                artifact_type="knowledge-item",
                payload=entry["item"],
                actor_ids=(),
                artifact_ids=(entry["item"]["knowledge_id"],),
                lineage_event_ids=(entry["source_event_id"],),
                source_mechanism=self.config.source_mechanism_id,
                source_port="knowledge",
                emitted_period=year,
                available_period=year,
            )
            for entry in entries
        )
        result = self._invoke_production_broker(
            year, inputs, self._state["production_broker_state"]
        )
        if result.next_state is None:
            raise NativeCommunicationError("production broker did not return state")
        if set(result.outputs) - {"messages"}:
            raise NativeCommunicationError("production broker returned an unknown port")
        self._state["production_broker_state"] = deepcopy(dict(result.next_state))
        for value in result.outputs.get("messages", ()):
            self._queue_production_message(year, value)

    def _invoke_production_broker(
        self,
        year: int,
        inputs: Sequence[DeliveredValue],
        state: Mapping[str, Any],
    ) -> MechanismResult:
        mechanism = MechanismSpec(
            self.config.broker_mechanism_id,
            MechanismFamily.COMMUNICATION,
            self.config.implementation,
            inputs=(PortSpec("knowledge", ChannelKind.ARTIFACT, "knowledge-item"),),
            outputs=(PortSpec("messages", ChannelKind.SIGNAL, "knowledge-message"),),
            parameters={
                "mode": self.config.mode,
                "digest_size": self.config.digest_size,
                "delivery_latency": self.config.latency,
            },
        )
        context = MechanismContext(
            system_id="native-prospective-simulator",
            system_fingerprint=self.config.system_fingerprint,
            mechanism=mechanism,
            period=year,
            phase=7,
            trigger="annual",
            inputs={"knowledge": tuple(inputs)} if inputs else {},
            initial_state={},
            state=state,
        )
        handler = (
            knowledge_broadcast
            if self.config.mode == "broadcast"
            else knowledge_digest
        )
        try:
            return handler(context)
        except GraphRuntimeError as error:
            raise NativeCommunicationError(
                f"production broker rejected native input/state: {error}"
            ) from error

    def _queue_production_message(self, year: int, value: MechanismValue) -> None:
        message = parse_knowledge_message(value.payload)
        if tuple(message["source_event_ids"]) != value.lineage_event_ids:
            raise NativeCommunicationError("production message lineage is inconsistent")
        sequence = self._state["next_message_sequence"]
        if message["message_sequence"] != sequence:
            raise NativeCommunicationError("production message sequence is inconsistent")
        source_event_ids = list(message["source_event_ids"])
        items = message["knowledge_items"]
        artifact_ids = tuple(
            evidence_id
            for item in items for evidence_id in item["evidence_artifact_ids"]
        )
        event = self._append_event(
            year=year,
            phase=7,
            event_type=MESSAGE_EVENT_TYPE,
            artifact_ids=artifact_ids,
            payload={"message": message},
            provenance={
                "native_mechanism": self.config.broker_mechanism_id,
                "implementation": self.config.implementation,
                "production_adapter": self.config.implementation,
                "source_event_ids": source_event_ids,
                "namespace": "native.communication",
            },
        )
        self._state["emitted_message_ids"].append(message["message_id"])
        self._state["next_message_sequence"] += 1
        self._state["pending_deliveries"].append({
            "due_year": year + self.config.latency,
            "message": message,
            "message_event_id": event.event_id,
            "artifact_ids": list(artifact_ids),
        })

    def _deliver_due(self, year: int) -> None:
        pending = []
        for delivery in self._state["pending_deliveries"]:
            if delivery["due_year"] > year:
                pending.append(delivery)
                continue
            message = parse_knowledge_message(delivery["message"])
            if message["message_id"] in self._state["received_message_ids"]:
                raise NativeCommunicationError("message delivery was replayed")
            self._append_event(
                year=year,
                phase=8,
                event_type=RECEIVER_EVENT_TYPE,
                artifact_ids=tuple(delivery["artifact_ids"]),
                payload={
                    "message_id": message["message_id"],
                    "message_sequence": message["message_sequence"],
                    "sender_id": message["sender_id"],
                    "receiver_id": self.config.receiver_mechanism_id,
                    "receiver_role": self.config.receiver_role,
                    "emitted_year": message["emitted_period"],
                    "received_year": year,
                    "latency": self.config.latency,
                    "knowledge_ids": [
                        item["knowledge_id"] for item in message["knowledge_items"]
                    ],
                    "system_fingerprint": self.config.system_fingerprint,
                },
                provenance={
                    "native_mechanism": self.config.receiver_mechanism_id,
                    "source_event_ids": [delivery["message_event_id"]],
                    "namespace": "native.communication",
                },
            )
            self._state["received_message_ids"].append(message["message_id"])
        self._state["pending_deliveries"] = pending

    def _append_event(
        self,
        *,
        year: int,
        phase: int,
        event_type: str,
        actor_ids: Sequence[str] = (),
        artifact_ids: Sequence[str] = (),
        payload: Mapping[str, Any],
        provenance: Mapping[str, Any],
    ) -> EventEnvelope:
        event = EventEnvelope.create(
            sequence=len(self._state["events"]),
            year=year,
            phase=phase,
            event_type=event_type,
            actor_ids=actor_ids,
            artifact_ids=artifact_ids,
            payload=payload,
            provenance=provenance,
        )
        self._state["events"].append(event.to_dict())
        return event

    def _restore(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        if not raw:
            return {
                "schema_version": NATIVE_COMMUNICATION_STATE,
                "config": self.config.to_dict(),
                "config_fingerprint": self.config.fingerprint,
                "last_completed_year": 0,
                "processed_output_ids": [],
                "source_event_ids": [],
                "emitted_message_ids": [],
                "received_message_ids": [],
                "next_message_sequence": 1,
                "production_broker_state": {},
                "pending_deliveries": [],
                "events": [],
            }
        restored = deepcopy(dict(raw))
        self._validate_state(restored)
        return restored

    def _validate_state(self, state: Mapping[str, Any]) -> None:
        required = {
            "schema_version", "config", "config_fingerprint", "last_completed_year",
            "processed_output_ids", "source_event_ids", "emitted_message_ids",
            "received_message_ids", "next_message_sequence", "production_broker_state",
            "pending_deliveries", "events",
        }
        if set(state) != required or state.get("schema_version") != NATIVE_COMMUNICATION_STATE:
            raise NativeCommunicationError("native communication checkpoint schema changed")
        if state["config"] != self.config.to_dict():
            raise NativeCommunicationError("native communication checkpoint config changed")
        if state["config_fingerprint"] != self.config.fingerprint:
            raise NativeCommunicationError("native communication config fingerprint mismatch")
        year = state["last_completed_year"]
        if type(year) is not int or year < 0:
            raise NativeCommunicationError("last_completed_year is invalid")
        processed = _unique_strings(state["processed_output_ids"], "processed outputs")
        source_ids = _unique_strings(state["source_event_ids"], "source events")
        emitted = _unique_strings(state["emitted_message_ids"], "emitted messages")
        received = _unique_strings(state["received_message_ids"], "received messages")
        if not set(received) <= set(emitted):
            raise NativeCommunicationError("received messages were not emitted")
        if state["next_message_sequence"] != len(emitted) + 1:
            raise NativeCommunicationError("message sequence cursor is inconsistent")
        events = state["events"]
        if not isinstance(events, list):
            raise NativeCommunicationError("native communication events must be a list")
        parsed_events = [_event_from_dict(item) for item in events]
        if [item.sequence for item in parsed_events] != list(range(len(parsed_events))):
            raise NativeCommunicationError("native communication event sequence is not contiguous")
        validate_native_communication_events(
            parsed_events, system_fingerprint=self.config.system_fingerprint
        )
        source_events = [
            item for item in parsed_events if item.event_type == SOURCE_EVENT_TYPE
        ]
        message_events = [
            item for item in parsed_events if item.event_type == MESSAGE_EVENT_TYPE
        ]
        receiver_events = [
            item for item in parsed_events if item.event_type == RECEIVER_EVENT_TYPE
        ]
        if source_ids != [item.event_id for item in source_events]:
            raise NativeCommunicationError("source event cursor differs from event history")
        if processed != [item.payload.get("source_output_id") for item in source_events]:
            raise NativeCommunicationError("processed output cursor differs from event history")
        emitted_from_events = [
            item.payload["message"]["message_id"] for item in message_events
        ]
        if emitted != emitted_from_events:
            raise NativeCommunicationError("emitted message cursor differs from event history")
        received_from_events = [item.payload.get("message_id") for item in receiver_events]
        if received != received_from_events:
            raise NativeCommunicationError("received message cursor differs from event history")
        if len(processed) != len(source_ids):
            raise NativeCommunicationError("processed output/source event counts differ")
        production_state = state["production_broker_state"]
        if not isinstance(production_state, Mapping):
            raise NativeCommunicationError("production broker state must be a mapping")
        if production_state:
            processed_knowledge = [
                item.payload["knowledge_item"]["knowledge_id"] for item in source_events
            ]
            if production_state.get("processed_knowledge_ids") != processed_knowledge:
                raise NativeCommunicationError(
                    "production broker processed cursor differs from source history"
                )
            if production_state.get("observed_event_ids") != source_ids:
                raise NativeCommunicationError(
                    "production broker lineage differs from source history"
                )
            if production_state.get("emitted_message_ids") != emitted:
                raise NativeCommunicationError(
                    "production broker emitted cursor differs from event history"
                )
            if production_state.get("next_message_sequence") != state[
                "next_message_sequence"
            ]:
                raise NativeCommunicationError(
                    "production and native message cursors differ"
                )
            validated_production = self._invoke_production_broker(
                max(year, 1), (), production_state
            )
            if (
                validated_production.outputs
                or validated_production.events
                or validated_production.next_state != production_state
            ):
                raise NativeCommunicationError(
                    "production broker checkpoint is not a stable restored state"
                )
        elif processed or emitted:
            raise NativeCommunicationError("production broker state is missing")
        pending = state["pending_deliveries"]
        if not isinstance(pending, list):
            raise NativeCommunicationError("pending deliveries must be a list")
        message_events_by_id = {
            item.payload["message"]["message_id"]: item for item in message_events
        }
        pending_ids = []
        for delivery in pending:
            if not isinstance(delivery, Mapping) or set(delivery) != {
                "due_year", "message", "message_event_id", "artifact_ids"
            }:
                raise NativeCommunicationError("pending delivery is invalid")
            if type(delivery["due_year"]) is not int or delivery["due_year"] <= year:
                raise NativeCommunicationError("pending delivery due year is stale")
            message = parse_knowledge_message(delivery["message"])
            pending_ids.append(message["message_id"])
            message_event = message_events_by_id.get(message["message_id"])
            if (
                message_event is None
                or delivery["message_event_id"] != message_event.event_id
                or message != message_event.payload["message"]
            ):
                raise NativeCommunicationError("pending message event is inconsistent")
            expected_artifact_ids = [
                artifact_id
                for item in message["knowledge_items"]
                for artifact_id in item["evidence_artifact_ids"]
            ]
            if delivery["artifact_ids"] != expected_artifact_ids:
                raise NativeCommunicationError("pending artifact ids are inconsistent")
            if delivery["due_year"] != message["emitted_period"] + self.config.latency:
                raise NativeCommunicationError("pending delivery latency is inconsistent")
        if len(pending_ids) != len(set(pending_ids)) or not set(pending_ids) <= set(emitted):
            raise NativeCommunicationError("pending message identities are inconsistent")
        _strict_json(state, "native communication checkpoint")


def validate_native_communication_events(
    events: Sequence[EventEnvelope],
    *,
    system_fingerprint: str,
) -> None:
    """Validate native namespace, source/message/receiver causal lineage."""

    seen: set[str] = set()
    messages: dict[str, EventEnvelope] = {}
    for event in events:
        if event.event_type not in {
            SOURCE_EVENT_TYPE, MESSAGE_EVENT_TYPE, RECEIVER_EVENT_TYPE
        }:
            raise NativeCommunicationError("event is outside native communication namespace")
        recreated = EventEnvelope.create(
            sequence=event.sequence,
            year=event.year,
            phase=event.phase,
            event_type=event.event_type,
            actor_ids=event.actor_ids,
            artifact_ids=event.artifact_ids,
            payload=event.payload,
            provenance=event.provenance,
        )
        if recreated.event_id != event.event_id or event.schema_version != SCHEMA_VERSION:
            raise NativeCommunicationError("native communication event identity mismatch")
        if event.provenance.get("namespace") != "native.communication":
            raise NativeCommunicationError("native communication namespace is missing")
        if event.event_type == SOURCE_EVENT_TYPE:
            if event.payload.get("system_fingerprint") != system_fingerprint:
                raise NativeCommunicationError("source event system fingerprint mismatch")
            item = parse_knowledge_item(event.payload.get("knowledge_item"))
            source_output_id = event.payload.get("source_output_id")
            if (
                not isinstance(source_output_id, str)
                or event.artifact_ids != (source_output_id,)
                or item["evidence_artifact_ids"] != [source_output_id]
                or item["created_period"] != event.year
                or event.provenance.get("native_mechanism")
                != item["origin_mechanism"]
            ):
                raise NativeCommunicationError("source event payload lineage is invalid")
        elif event.event_type == MESSAGE_EVENT_TYPE:
            message = parse_knowledge_message(event.payload.get("message"))
            if message["system_fingerprint"] != system_fingerprint:
                raise NativeCommunicationError("message system fingerprint mismatch")
            sources = event.provenance.get("source_event_ids")
            if sources != message["source_event_ids"] or not set(sources) <= seen:
                raise NativeCommunicationError("message source lineage is invalid")
            evidence_ids = tuple(
                artifact_id
                for item in message["knowledge_items"]
                for artifact_id in item["evidence_artifact_ids"]
            )
            expected_implementation = (
                KNOWLEDGE_BROADCAST
                if message["transformation"] == "relay"
                else KNOWLEDGE_DIGEST
            )
            if (
                event.artifact_ids != evidence_ids
                or message["emitted_period"] != event.year
                or event.provenance.get("native_mechanism") != message["sender_id"]
                or event.provenance.get("production_adapter")
                != expected_implementation
            ):
                raise NativeCommunicationError("message event payload lineage is invalid")
            messages[message["message_id"]] = event
        else:
            if event.payload.get("system_fingerprint") != system_fingerprint:
                raise NativeCommunicationError("receiver system fingerprint mismatch")
            sources = event.provenance.get("source_event_ids")
            if not isinstance(sources, list) or len(sources) != 1 or sources[0] not in seen:
                raise NativeCommunicationError("receiver source lineage is invalid")
            message = messages.get(event.payload.get("message_id"))
            if message is None or message.event_id != sources[0]:
                raise NativeCommunicationError("receiver did not cite its message event")
            emitted_year = event.payload.get("emitted_year")
            received_year = event.payload.get("received_year")
            latency = event.payload.get("latency")
            if any(type(value) is not int for value in (emitted_year, received_year, latency)):
                raise NativeCommunicationError("receiver latency fields are invalid")
            observed_latency = received_year - emitted_year
            if (
                observed_latency != latency
                or received_year != event.year
                or event.artifact_ids != message.artifact_ids
                or event.provenance.get("native_mechanism")
                != event.payload.get("receiver_id")
            ):
                raise NativeCommunicationError("receiver latency does not reconcile")
        seen.add(event.event_id)


def _event_from_dict(value: Mapping[str, Any]) -> EventEnvelope:
    if not isinstance(value, Mapping) or set(value) != {
        "schema_version", "event_id", "sequence", "year", "phase", "event_type",
        "actor_ids", "artifact_ids", "payload", "provenance",
    }:
        raise NativeCommunicationError("canonical native event fields are invalid")
    if (
        value["schema_version"] != SCHEMA_VERSION
        or not isinstance(value["event_id"], str)
        or type(value["sequence"]) is not int
        or value["sequence"] < 0
        or type(value["year"]) is not int
        or value["year"] < 0
        or type(value["phase"]) is not int
        or value["phase"] < 0
        or not isinstance(value["event_type"], str)
        or not isinstance(value["actor_ids"], list)
        or not isinstance(value["artifact_ids"], list)
        or any(not isinstance(item, str) or not item for item in value["actor_ids"])
        or any(not isinstance(item, str) or not item for item in value["artifact_ids"])
        or not isinstance(value["payload"], Mapping)
        or not isinstance(value["provenance"], Mapping)
    ):
        raise NativeCommunicationError("canonical native event value types are invalid")
    return EventEnvelope(
        event_id=value["event_id"],
        sequence=value["sequence"],
        year=value["year"],
        phase=value["phase"],
        event_type=value["event_type"],
        actor_ids=tuple(value["actor_ids"]),
        artifact_ids=tuple(value["artifact_ids"]),
        payload=deepcopy(value["payload"]),
        provenance=deepcopy(value["provenance"]),
        schema_version=value["schema_version"],
    )


def _paper_value(paper: Any, name: str) -> Any:
    if isinstance(paper, Mapping):
        if name not in paper:
            raise NativeCommunicationError(f"accepted output is missing {name}")
        return paper[name]
    if not hasattr(paper, name):
        raise NativeCommunicationError(f"accepted output is missing {name}")
    return getattr(paper, name)


def _unique_strings(value: Any, name: str) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item for item in value)
        or len(value) != len(set(value))
    ):
        raise NativeCommunicationError(f"{name} must be unique strings")
    return list(value)


def _nonempty_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise NativeCommunicationError(f"{name} must be non-empty")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _strict_json(value: Any, name: str) -> None:
    try:
        _canonical_json(value)
    except (TypeError, ValueError) as error:
        raise NativeCommunicationError(f"{name} is not strict JSON") from error
