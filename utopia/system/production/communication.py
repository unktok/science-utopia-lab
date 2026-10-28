"""Stateful communication mechanisms with strict knowledge-message provenance."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any, Mapping

from utopia.system.model import ChannelKind
from utopia.system.runtime import (
    DeliveredValue,
    GraphRuntimeError,
    MechanismContext,
    MechanismEvent,
    MechanismRegistry,
    MechanismResult,
    MechanismValue,
)


KNOWLEDGE_BROADCAST = "production.communication.knowledge-broadcast-v1"
KNOWLEDGE_DIGEST = "production.communication.knowledge-digest-v1"
KNOWLEDGE_RECEIVER = "production.communication.knowledge-receiver-v1"
KNOWLEDGE_ITEM_SCHEMA_VERSION = "scienceutopia.knowledge-item.v1"
KNOWLEDGE_MESSAGE_SCHEMA_VERSION = "scienceutopia.knowledge-message.v1"
DIFFUSION_STATE_SCHEMA_VERSION = "scienceutopia.knowledge-diffusion-state.v1"
RECEIVER_STATE_SCHEMA_VERSION = "scienceutopia.knowledge-receiver-state.v1"


def register_communication_mechanisms(registry: MechanismRegistry) -> None:
    registry.register(KNOWLEDGE_BROADCAST, 1, knowledge_broadcast)
    registry.register(KNOWLEDGE_DIGEST, 1, knowledge_digest)
    registry.register(KNOWLEDGE_RECEIVER, 1, knowledge_receiver)


def knowledge_broadcast(context: MechanismContext) -> MechanismResult:
    """Relay each new typed knowledge item in its own versioned message."""

    return _diffuse_knowledge(context, mode="relay")


def knowledge_digest(context: MechanismContext) -> MechanismResult:
    """Buffer new knowledge and emit deterministic multi-item digests."""

    return _diffuse_knowledge(context, mode="digest")


def knowledge_receiver(context: MechanismContext) -> MechanismResult:
    """Consume knowledge messages while enforcing causal delivery provenance."""

    state = _restore_receiver_state(context.state)
    receiver_role = _nonempty_string(
        context.mechanism.parameters.get("receiver_role"), "receiver_role"
    )
    events: list[MechanismEvent] = []
    for delivered in context.inputs.get("messages", ()):
        message = validate_delivered_message(
            delivered,
            system_fingerprint=context.system_fingerprint,
        )
        sender = message["sender_id"]
        sequence = message["message_sequence"]
        previous = state["last_sequence_by_sender"].get(sender, 0)
        if sequence <= previous:
            raise GraphRuntimeError("knowledge message sequence is stale or replayed")
        if message["message_id"] in state["received_message_ids"]:
            raise GraphRuntimeError("knowledge message id was already received")
        knowledge_ids = [
            item["knowledge_id"] for item in message["knowledge_items"]
        ]
        seen_knowledge = set(state["received_knowledge_ids"])
        if any(knowledge_id in seen_knowledge for knowledge_id in knowledge_ids):
            raise GraphRuntimeError("knowledge item was already received")

        state["received_message_ids"].append(message["message_id"])
        state["received_knowledge_ids"].extend(knowledge_ids)
        state["last_sequence_by_sender"][sender] = sequence
        state["knowledge_by_id"].update(
            {
                item["knowledge_id"]: deepcopy(item)
                for item in message["knowledge_items"]
            }
        )
        events.append(
            MechanismEvent(
                "communication.knowledge_received",
                artifact_ids=tuple(knowledge_ids),
                payload={
                    "message_id": message["message_id"],
                    "message_sequence": sequence,
                    "sender_id": sender,
                    "receiver_role": receiver_role,
                    "transformation": message["transformation"],
                    "knowledge_ids": knowledge_ids,
                },
                provenance={
                    "production_adapter": KNOWLEDGE_RECEIVER,
                    "message_schema": KNOWLEDGE_MESSAGE_SCHEMA_VERSION,
                },
            )
        )
    return MechanismResult(events=tuple(events), next_state=state)


def parse_knowledge_item(value: Mapping[str, Any]) -> dict[str, Any]:
    """Parse one exact knowledge-item v1 payload."""

    if not isinstance(value, Mapping):
        raise GraphRuntimeError("knowledge item must be a mapping")
    required = {
        "schema_version",
        "knowledge_id",
        "origin_mechanism",
        "created_period",
        "topic",
        "summary",
        "evidence_artifact_ids",
    }
    if set(value) != required:
        raise GraphRuntimeError("knowledge item fields do not match v1 schema")
    if value.get("schema_version") != KNOWLEDGE_ITEM_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported knowledge item schema")
    for key in ("knowledge_id", "origin_mechanism", "topic", "summary"):
        _nonempty_string(value[key], f"knowledge item {key}")
    _nonnegative_int(value["created_period"], "knowledge item created_period")
    evidence_ids = value["evidence_artifact_ids"]
    if (
        not isinstance(evidence_ids, list)
        or any(not isinstance(item, str) or not item for item in evidence_ids)
        or len(evidence_ids) != len(set(evidence_ids))
    ):
        raise GraphRuntimeError(
            "knowledge item evidence_artifact_ids must be unique strings"
        )
    result = deepcopy(dict(value))
    _strict_json(result, "knowledge item")
    return result


def parse_knowledge_message(value: Mapping[str, Any]) -> dict[str, Any]:
    """Parse one exact, versioned knowledge-message v1 envelope."""

    if not isinstance(value, Mapping):
        raise GraphRuntimeError("knowledge message must be a mapping")
    required = {
        "schema_version",
        "message_id",
        "message_sequence",
        "sender_id",
        "system_fingerprint",
        "emitted_period",
        "transformation",
        "source_event_ids",
        "knowledge_items",
    }
    if set(value) != required:
        raise GraphRuntimeError("knowledge message fields do not match v1 schema")
    if value.get("schema_version") != KNOWLEDGE_MESSAGE_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported knowledge message schema")
    for key in ("message_id", "sender_id", "system_fingerprint"):
        _nonempty_string(value[key], f"knowledge message {key}")
    fingerprint = value["system_fingerprint"]
    if len(fingerprint) != 64 or any(
        character not in "0123456789abcdef" for character in fingerprint
    ):
        raise GraphRuntimeError("knowledge message system_fingerprint is not sha256")
    _positive_int(value["message_sequence"], "knowledge message sequence")
    _nonnegative_int(value["emitted_period"], "knowledge message emitted_period")
    if value["transformation"] not in {"relay", "digest"}:
        raise GraphRuntimeError("knowledge message transformation is unsupported")
    source_event_ids = value["source_event_ids"]
    if (
        not isinstance(source_event_ids, list)
        or not source_event_ids
        or any(not isinstance(item, str) or not item for item in source_event_ids)
        or len(source_event_ids) != len(set(source_event_ids))
    ):
        raise GraphRuntimeError(
            "knowledge message source_event_ids must be unique non-empty strings"
        )
    raw_items = value["knowledge_items"]
    if not isinstance(raw_items, list) or not raw_items:
        raise GraphRuntimeError("knowledge message must contain knowledge_items")
    knowledge_items = [parse_knowledge_item(item) for item in raw_items]
    knowledge_ids = [item["knowledge_id"] for item in knowledge_items]
    if len(knowledge_ids) != len(set(knowledge_ids)):
        raise GraphRuntimeError("knowledge message contains duplicate knowledge ids")
    result = deepcopy(dict(value))
    result["knowledge_items"] = knowledge_items
    _strict_json(result, "knowledge message")
    return result


def validate_delivered_message(
    delivered: DeliveredValue,
    *,
    system_fingerprint: str,
) -> dict[str, Any]:
    """Validate envelope fields against the runner-owned delivery provenance."""

    message = parse_knowledge_message(delivered.payload)
    if (
        delivered.channel != ChannelKind.SIGNAL
        or delivered.artifact_type != "knowledge-message"
    ):
        raise GraphRuntimeError("knowledge message delivery type is invalid")
    if message["system_fingerprint"] != system_fingerprint:
        raise GraphRuntimeError("knowledge message belongs to a different system")
    if message["sender_id"] != delivered.source_mechanism:
        raise GraphRuntimeError("knowledge message sender does not match delivery source")
    if message["emitted_period"] != delivered.emitted_period:
        raise GraphRuntimeError("knowledge message period does not match delivery")
    lineage = set(delivered.lineage_event_ids)
    if not set(message["source_event_ids"]) <= lineage:
        raise GraphRuntimeError("knowledge message source events are absent from lineage")
    knowledge_ids = tuple(
        item["knowledge_id"] for item in message["knowledge_items"]
    )
    if knowledge_ids != delivered.artifact_ids:
        raise GraphRuntimeError("knowledge message artifacts do not match its payload")
    return message


def _diffuse_knowledge(
    context: MechanismContext,
    *,
    mode: str,
) -> MechanismResult:
    state = _restore_diffusion_state(context.state, context.mechanism.parameters, mode)
    new_entries: list[dict[str, Any]] = []
    prior_knowledge_ids = set(state["processed_knowledge_ids"])
    prior_event_ids = set(state["observed_event_ids"])
    new_knowledge_ids: set[str] = set()
    new_event_ids: list[str] = []
    for delivered in context.inputs.get("knowledge", ()):
        item = parse_knowledge_item(delivered.payload)
        if item["origin_mechanism"] != delivered.source_mechanism:
            raise GraphRuntimeError("knowledge origin does not match delivery source")
        if item["created_period"] != delivered.emitted_period:
            raise GraphRuntimeError("knowledge creation period does not match delivery")
        if delivered.artifact_ids != (item["knowledge_id"],):
            raise GraphRuntimeError("knowledge delivery artifacts do not match its payload")
        if not delivered.lineage_event_ids:
            raise GraphRuntimeError("knowledge input requires canonical event lineage")
        if (
            item["knowledge_id"] in prior_knowledge_ids
            or item["knowledge_id"] in new_knowledge_ids
        ):
            raise GraphRuntimeError("knowledge item was already processed")
        if any(event_id in prior_event_ids for event_id in delivered.lineage_event_ids):
            raise GraphRuntimeError("knowledge input reuses an observed system event")
        new_entries.append(
            {
                "item": item,
                "source_event_ids": list(dict.fromkeys(delivered.lineage_event_ids)),
            }
        )
        new_knowledge_ids.add(item["knowledge_id"])
        new_event_ids.extend(delivered.lineage_event_ids)

    state["processed_knowledge_ids"].extend(
        entry["item"]["knowledge_id"] for entry in new_entries
    )
    state["observed_event_ids"].extend(
        event_id
        for event_id in dict.fromkeys(new_event_ids)
        if event_id not in prior_event_ids
    )

    messages: list[dict[str, Any]] = []
    if mode == "relay":
        messages.extend(
            _build_message(
                context,
                state,
                [entry],
                sequence=state["next_message_sequence"] + offset,
            )
            for offset, entry in enumerate(new_entries)
        )
    else:
        state["buffer"].extend(new_entries)
        if len(state["buffer"]) >= state["digest_size"]:
            messages.append(
                _build_message(
                    context,
                    state,
                    state["buffer"],
                    sequence=state["next_message_sequence"],
                )
            )
            state["buffer"] = []

    outputs: list[MechanismValue] = []
    events: list[MechanismEvent] = []
    for message in messages:
        knowledge_ids = tuple(
            item["knowledge_id"] for item in message["knowledge_items"]
        )
        outputs.append(
            MechanismValue(
                message,
                artifact_ids=knowledge_ids,
                lineage_event_ids=tuple(message["source_event_ids"]),
            )
        )
        events.append(
            MechanismEvent(
                "communication.message_emitted",
                artifact_ids=knowledge_ids,
                payload={
                    "message_id": message["message_id"],
                    "message_sequence": message["message_sequence"],
                    "transformation": mode,
                    "knowledge_ids": list(knowledge_ids),
                },
                provenance={
                    "production_adapter": context.mechanism.implementation,
                    "message_schema": KNOWLEDGE_MESSAGE_SCHEMA_VERSION,
                },
            )
        )
        state["emitted_message_ids"].append(message["message_id"])
        state["next_message_sequence"] += 1
        state["last_message_fingerprint"] = _fingerprint(message)
    return MechanismResult(
        outputs={"messages": tuple(outputs)} if outputs else {},
        events=tuple(events),
        next_state=state,
    )


def _build_message(
    context: MechanismContext,
    state: Mapping[str, Any],
    entries: list[Mapping[str, Any]],
    *,
    sequence: int,
) -> dict[str, Any]:
    items = [deepcopy(entry["item"]) for entry in entries]
    source_event_ids = list(
        dict.fromkeys(
            event_id
            for entry in entries
            for event_id in entry["source_event_ids"]
        )
    )
    body = {
        "schema_version": KNOWLEDGE_MESSAGE_SCHEMA_VERSION,
        "message_id": "pending",
        "message_sequence": sequence,
        "sender_id": context.mechanism.mechanism_id,
        "system_fingerprint": context.system_fingerprint,
        "emitted_period": context.period,
        "transformation": state["mode"],
        "source_event_ids": source_event_ids,
        "knowledge_items": items,
    }
    digest = _fingerprint(
        {key: value for key, value in body.items() if key != "message_id"}
    )
    body["message_id"] = (
        f"{context.mechanism.mechanism_id}"
        f"-m{sequence}-{digest[:12]}"
    )
    return parse_knowledge_message(body)


def _restore_diffusion_state(
    raw: Mapping[str, Any],
    parameters: Mapping[str, Any],
    mode: str,
) -> dict[str, Any]:
    digest_size = _positive_int(parameters.get("digest_size", 2), "digest_size")
    if not raw:
        return {
            "schema_version": DIFFUSION_STATE_SCHEMA_VERSION,
            "mode": mode,
            "digest_size": digest_size,
            "processed_knowledge_ids": [],
            "observed_event_ids": [],
            "emitted_message_ids": [],
            "next_message_sequence": 1,
            "buffer": [],
            "last_message_fingerprint": None,
        }
    required = {
        "schema_version",
        "mode",
        "digest_size",
        "processed_knowledge_ids",
        "observed_event_ids",
        "emitted_message_ids",
        "next_message_sequence",
        "buffer",
        "last_message_fingerprint",
    }
    if set(raw) != required or raw.get("schema_version") != DIFFUSION_STATE_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported knowledge diffusion state")
    if raw["mode"] != mode or raw["digest_size"] != digest_size:
        raise GraphRuntimeError("knowledge diffusion state configuration changed")
    processed = _unique_string_list(raw["processed_knowledge_ids"], "processed ids")
    observed = _unique_string_list(raw["observed_event_ids"], "observed events")
    emitted = _unique_string_list(raw["emitted_message_ids"], "emitted message ids")
    sequence = _positive_int(raw["next_message_sequence"], "next message sequence")
    if sequence != len(emitted) + 1:
        raise GraphRuntimeError("knowledge diffusion sequence cursor is inconsistent")
    raw_buffer = raw["buffer"]
    if not isinstance(raw_buffer, list):
        raise GraphRuntimeError("knowledge diffusion buffer must be a list")
    buffer: list[dict[str, Any]] = []
    for entry in raw_buffer:
        if not isinstance(entry, Mapping) or set(entry) != {"item", "source_event_ids"}:
            raise GraphRuntimeError("knowledge diffusion buffer entry is invalid")
        buffer.append(
            {
                "item": parse_knowledge_item(entry["item"]),
                "source_event_ids": _unique_string_list(
                    entry["source_event_ids"], "buffer source events", nonempty=True
                ),
            }
        )
    buffered_ids = [entry["item"]["knowledge_id"] for entry in buffer]
    if len(buffered_ids) != len(set(buffered_ids)) or not set(buffered_ids) <= set(processed):
        raise GraphRuntimeError("knowledge diffusion buffer ids are inconsistent")
    buffered_events = {
        event_id for entry in buffer for event_id in entry["source_event_ids"]
    }
    if not buffered_events <= set(observed):
        raise GraphRuntimeError("knowledge diffusion buffer events are inconsistent")
    if mode == "relay" and buffer:
        raise GraphRuntimeError("relay diffusion state cannot contain a buffer")
    fingerprint = raw["last_message_fingerprint"]
    if fingerprint is not None and not _is_sha256(fingerprint):
        raise GraphRuntimeError("knowledge diffusion fingerprint is invalid")
    if bool(emitted) != (fingerprint is not None):
        raise GraphRuntimeError("knowledge diffusion fingerprint cursor is inconsistent")
    return {
        "schema_version": DIFFUSION_STATE_SCHEMA_VERSION,
        "mode": mode,
        "digest_size": digest_size,
        "processed_knowledge_ids": processed,
        "observed_event_ids": observed,
        "emitted_message_ids": emitted,
        "next_message_sequence": sequence,
        "buffer": buffer,
        "last_message_fingerprint": fingerprint,
    }


def _restore_receiver_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not raw:
        return {
            "schema_version": RECEIVER_STATE_SCHEMA_VERSION,
            "received_message_ids": [],
            "received_knowledge_ids": [],
            "last_sequence_by_sender": {},
            "knowledge_by_id": {},
        }
    required = {
        "schema_version",
        "received_message_ids",
        "received_knowledge_ids",
        "last_sequence_by_sender",
        "knowledge_by_id",
    }
    if set(raw) != required or raw.get("schema_version") != RECEIVER_STATE_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported knowledge receiver state")
    message_ids = _unique_string_list(raw["received_message_ids"], "received messages")
    knowledge_ids = _unique_string_list(
        raw["received_knowledge_ids"], "received knowledge"
    )
    cursors = raw["last_sequence_by_sender"]
    if not isinstance(cursors, Mapping) or any(
        not isinstance(sender, str)
        or not sender
        or isinstance(sequence, bool)
        or not isinstance(sequence, int)
        or sequence < 1
        for sender, sequence in cursors.items()
    ):
        raise GraphRuntimeError("knowledge receiver sender cursors are invalid")
    raw_knowledge = raw["knowledge_by_id"]
    if not isinstance(raw_knowledge, Mapping):
        raise GraphRuntimeError("knowledge receiver archive must be a mapping")
    knowledge_by_id = {
        key: parse_knowledge_item(item) for key, item in raw_knowledge.items()
    }
    if any(key != item["knowledge_id"] for key, item in knowledge_by_id.items()):
        raise GraphRuntimeError("knowledge receiver archive key is inconsistent")
    if set(knowledge_ids) != set(knowledge_by_id):
        raise GraphRuntimeError("knowledge receiver archive ids are inconsistent")
    return {
        "schema_version": RECEIVER_STATE_SCHEMA_VERSION,
        "received_message_ids": message_ids,
        "received_knowledge_ids": knowledge_ids,
        "last_sequence_by_sender": dict(cursors),
        "knowledge_by_id": knowledge_by_id,
    }


def _unique_string_list(
    value: Any,
    label: str,
    *,
    nonempty: bool = False,
) -> list[str]:
    if (
        not isinstance(value, list)
        or (nonempty and not value)
        or any(not isinstance(item, str) or not item for item in value)
        or len(value) != len(set(value))
    ):
        raise GraphRuntimeError(f"knowledge diffusion {label} must be unique strings")
    return list(value)


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise GraphRuntimeError(f"{label} must be a non-empty string")
    return value


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise GraphRuntimeError(f"{label} must be a positive integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GraphRuntimeError(f"{label} must be a non-negative integer")
    return value


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _strict_json(value: Any, label: str) -> None:
    try:
        json.dumps(value, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise GraphRuntimeError(f"{label} is not strict JSON: {exc}") from exc
