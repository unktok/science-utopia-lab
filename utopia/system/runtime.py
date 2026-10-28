"""Deterministic runtime for arbitrary :class:`~utopia.system.SystemSpec` graphs.

The runtime knows about ports, schedules, and delivery latency, but it does not
know about peer review, publication, funding, or any other mechanism family.
Concrete behavior enters only through :class:`MechanismRegistry`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
from typing import Any, Iterable, Mapping, Protocol, Sequence

from utopia.replay.events import (
    EventEnvelope,
    canonical_event_stream_hash,
)

from .model import ChannelKind, MechanismSpec, PortSpec, SystemSpec
from .validation import validate_system_spec


class GraphRuntimeError(ValueError):
    """Raised when a structurally valid graph cannot execute as specified."""


@dataclass(frozen=True)
class MechanismValue:
    """One value emitted by a mechanism output port.

    The port declaration supplies the channel and artifact type.  Actor,
    artifact, and lineage ids are carried with the value so a downstream
    decision can retain causal provenance.
    """

    payload: Mapping[str, Any]
    actor_ids: tuple[str, ...] = ()
    artifact_ids: tuple[str, ...] = ()
    lineage_event_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class DeliveredValue:
    """Typed value presented to a mechanism input port."""

    channel: ChannelKind
    artifact_type: str | None
    payload: Mapping[str, Any]
    actor_ids: tuple[str, ...]
    artifact_ids: tuple[str, ...]
    lineage_event_ids: tuple[str, ...]
    source_mechanism: str
    source_port: str
    emitted_period: int
    available_period: int


@dataclass(frozen=True)
class MechanismEvent:
    """Event request emitted by a mechanism implementation.

    The runner turns this into the shared canonical ``EventEnvelope`` and adds
    execution and causal provenance.  Implementations cannot replace those
    reserved provenance fields.
    """

    event_type: str
    actor_ids: tuple[str, ...] = ()
    artifact_ids: tuple[str, ...] = ()
    payload: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MechanismResult:
    """Outputs, event requests, and an optional state transition.

    ``next_state=None`` preserves the mechanism's current state.  Returning an
    explicit mapping, including ``{}``, replaces it after output validation.
    """

    outputs: Mapping[str, Sequence[MechanismValue]] = field(default_factory=dict)
    events: tuple[MechanismEvent, ...] = ()
    next_state: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class MechanismContext:
    """Read-only invocation context passed to a registered implementation."""

    system_id: str
    system_fingerprint: str
    mechanism: MechanismSpec
    period: int
    phase: int
    trigger: str
    inputs: Mapping[str, tuple[DeliveredValue, ...]]
    initial_state: Mapping[str, Any]
    state: Mapping[str, Any]


class MechanismImplementation(Protocol):
    def __call__(self, context: MechanismContext) -> MechanismResult: ...


ImplementationKey = tuple[str, int]


class MechanismRegistry:
    """Explicit mapping from spec implementation ids to executable behavior."""

    def __init__(self) -> None:
        self._implementations: dict[ImplementationKey, MechanismImplementation] = {}

    def register(
        self,
        implementation: str,
        version: int,
        handler: MechanismImplementation,
        *,
        replace: bool = False,
    ) -> None:
        key = _implementation_key(implementation, version)
        if not callable(handler):
            raise TypeError("mechanism handler must be callable")
        if key in self._implementations and not replace:
            raise GraphRuntimeError(
                f"implementation {implementation!r} v{version} is already registered"
            )
        self._implementations[key] = handler

    def unregister(self, implementation: str, version: int) -> None:
        key = _implementation_key(implementation, version)
        if key not in self._implementations:
            raise GraphRuntimeError(
                f"implementation {implementation!r} v{version} is not registered"
            )
        del self._implementations[key]

    def resolve(self, mechanism: MechanismSpec) -> MechanismImplementation:
        key = (mechanism.implementation, mechanism.version)
        try:
            return self._implementations[key]
        except KeyError as exc:
            raise GraphRuntimeError(
                f"no implementation registered for {mechanism.implementation!r} "
                f"v{mechanism.version} (mechanism {mechanism.mechanism_id!r})"
            ) from exc

    @property
    def registered(self) -> tuple[ImplementationKey, ...]:
        return tuple(sorted(self._implementations))


@dataclass(frozen=True)
class ExecutionRecord:
    period: int
    phase: int
    mechanism_id: str
    status: str
    input_counts: Mapping[str, int]
    output_counts: Mapping[str, int]
    event_ids: tuple[str, ...]
    missing_required_inputs: tuple[str, ...] = ()


@dataclass(frozen=True)
class GraphRunResult:
    system_id: str
    system_fingerprint: str
    start_period: int
    periods: int
    trigger: str
    events: tuple[EventEnvelope, ...]
    trace: tuple[ExecutionRecord, ...]
    pending_deliveries: int
    checkpoint: "GraphCheckpoint"

    @property
    def event_stream_hash(self) -> str:
        return canonical_event_stream_hash(self.events)


@dataclass(frozen=True)
class _QueuedDelivery:
    order: int
    target_mechanism: str
    target_port: str
    value: DeliveredValue


CHECKPOINT_SCHEMA_VERSION = "scienceutopia.graph-checkpoint.v1"


@dataclass(frozen=True)
class GraphCheckpoint:
    """Strict-JSON snapshot sufficient for deterministic graph continuation."""

    system_id: str
    system_fingerprint: str
    trigger: str
    next_period: int
    next_event_sequence: int
    next_delivery_order: int
    mechanism_states: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    queued_deliveries: tuple[_QueuedDelivery, ...] = ()
    schema_version: str = CHECKPOINT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "system_id": self.system_id,
            "system_fingerprint": self.system_fingerprint,
            "trigger": self.trigger,
            "next_period": self.next_period,
            "next_event_sequence": self.next_event_sequence,
            "next_delivery_order": self.next_delivery_order,
            "mechanism_states": _strict_json_clone(self.mechanism_states),
            "queued_deliveries": [
                _queued_delivery_to_dict(item) for item in self.queued_deliveries
            ],
        }
        _require_strict_json(value, "graph checkpoint")
        return value

    @property
    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GraphCheckpoint":
        if not isinstance(value, Mapping):
            raise GraphRuntimeError("graph checkpoint must be a mapping")
        if value.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
            raise GraphRuntimeError("unsupported graph checkpoint schema")
        required = {
            "schema_version",
            "system_id",
            "system_fingerprint",
            "trigger",
            "next_period",
            "next_event_sequence",
            "next_delivery_order",
            "mechanism_states",
            "queued_deliveries",
        }
        if set(value) != required:
            raise GraphRuntimeError("graph checkpoint fields do not match v1 schema")
        for key in ("system_id", "system_fingerprint", "trigger"):
            if not isinstance(value[key], str) or not value[key]:
                raise GraphRuntimeError(f"checkpoint {key} must be a non-empty string")
        for key in ("next_period", "next_event_sequence", "next_delivery_order"):
            if (
                isinstance(value[key], bool)
                or not isinstance(value[key], int)
                or value[key] < 0
            ):
                raise GraphRuntimeError(f"checkpoint {key} must be a non-negative integer")
        states = value["mechanism_states"]
        if not isinstance(states, Mapping) or any(
            not isinstance(key, str) or not isinstance(state, Mapping)
            for key, state in states.items()
        ):
            raise GraphRuntimeError("checkpoint mechanism_states must map ids to mappings")
        deliveries = value["queued_deliveries"]
        if not isinstance(deliveries, list):
            raise GraphRuntimeError("checkpoint queued_deliveries must be a list")
        _require_strict_json(value, "graph checkpoint")
        result = cls(
            system_id=value["system_id"],
            system_fingerprint=value["system_fingerprint"],
            trigger=value["trigger"],
            next_period=value["next_period"],
            next_event_sequence=value["next_event_sequence"],
            next_delivery_order=value["next_delivery_order"],
            mechanism_states=_strict_json_clone(states),
            queued_deliveries=tuple(
                _queued_delivery_from_dict(item) for item in deliveries
            ),
        )
        orders = [item.order for item in result.queued_deliveries]
        if len(orders) != len(set(orders)) or any(
            order >= result.next_delivery_order for order in orders
        ):
            raise GraphRuntimeError("checkpoint delivery orders are inconsistent")
        return result


class DeterministicGraphRunner:
    """Execute a validated ``SystemSpec`` without family-specific branches."""

    def __init__(self, spec: SystemSpec, registry: MechanismRegistry) -> None:
        validate_system_spec(spec).require_valid()
        self.spec = spec
        self.registry = registry
        self._mechanisms = {
            mechanism.mechanism_id: mechanism for mechanism in spec.mechanisms
        }
        # Resolve every node up front.  An unscheduled/passive mechanism remains
        # part of the executable design and must not silently hide a typo.
        self._handlers = {
            mechanism.mechanism_id: registry.resolve(mechanism)
            for mechanism in spec.mechanisms
        }
        self._connections = _connections_by_source(spec)

    def run(
        self,
        *,
        periods: int,
        start_period: int | None = None,
        trigger: str = "annual",
        checkpoint: GraphCheckpoint | Mapping[str, Any] | None = None,
    ) -> GraphRunResult:
        if isinstance(periods, bool) or not isinstance(periods, int) or periods < 1:
            raise GraphRuntimeError("periods must be a positive integer")
        if start_period is not None and (
            isinstance(start_period, bool) or not isinstance(start_period, int)
        ):
            raise GraphRuntimeError("start_period must be an integer or None")
        if not isinstance(trigger, str) or not trigger.strip():
            raise GraphRuntimeError("trigger must be a non-empty string")

        schedules = sorted(
            (item for item in self.spec.schedules if item.trigger == trigger),
            key=lambda item: (item.phase, item.mechanism_id),
        )
        if checkpoint is None:
            effective_start = 0 if start_period is None else start_period
            queue = []
            delivery_order = 0
            event_sequence = 0
            mechanism_states = _initial_mechanism_states(self.spec)
        else:
            restored = (
                checkpoint
                if isinstance(checkpoint, GraphCheckpoint)
                else GraphCheckpoint.from_dict(checkpoint)
            )
            _validate_checkpoint(restored, self.spec, trigger)
            if start_period is not None and start_period != restored.next_period:
                raise GraphRuntimeError(
                    "start_period does not equal checkpoint next_period"
                )
            effective_start = restored.next_period
            queue = list(restored.queued_deliveries)
            delivery_order = restored.next_delivery_order
            event_sequence = restored.next_event_sequence
            mechanism_states = _strict_json_clone(restored.mechanism_states)
        events: list[EventEnvelope] = []
        trace: list[ExecutionRecord] = []

        for period in range(effective_start, effective_start + periods):
            for schedule in schedules:
                mechanism = self._mechanisms[schedule.mechanism_id]
                inputs, selected_orders = _select_inputs(queue, mechanism, period)
                missing = tuple(
                    port.port_id
                    for port in mechanism.inputs
                    if port.required and not inputs[port.port_id]
                )
                input_counts = {
                    port.port_id: len(inputs[port.port_id])
                    for port in mechanism.inputs
                }
                if missing:
                    trace.append(
                        ExecutionRecord(
                            period,
                            schedule.phase,
                            mechanism.mechanism_id,
                            "blocked",
                            input_counts,
                            {},
                            (),
                            missing,
                        )
                    )
                    continue

                context = MechanismContext(
                    system_id=self.spec.system_id,
                    system_fingerprint=self.spec.fingerprint,
                    mechanism=replace(
                        mechanism,
                        parameters=_strict_json_clone(mechanism.parameters),
                    ),
                    period=period,
                    phase=schedule.phase,
                    trigger=trigger,
                    inputs=inputs,
                    initial_state=_strict_json_clone(self.spec.initial_state),
                    state=_strict_json_clone(
                        mechanism_states.get(mechanism.mechanism_id, {})
                    ),
                )
                result = self._handlers[mechanism.mechanism_id](context)
                if not isinstance(result, MechanismResult):
                    raise GraphRuntimeError(
                        f"{mechanism.mechanism_id!r} returned "
                        f"{type(result).__name__}, expected MechanismResult"
                    )
                normalized_outputs = _validate_result(mechanism, result)
                if result.next_state is not None:
                    if not isinstance(result.next_state, Mapping):
                        raise GraphRuntimeError(
                            f"{mechanism.mechanism_id!r} next_state must be a mapping"
                        )
                    _require_strict_json(result.next_state, "mechanism next_state")

                input_lineage = _stable_unique(
                    event_id
                    for port in mechanism.inputs
                    for value in inputs[port.port_id]
                    for event_id in value.lineage_event_ids
                )
                invocation_events: list[EventEnvelope] = []
                for request in result.events:
                    provenance = {
                        **dict(request.provenance),
                        "system_id": self.spec.system_id,
                        "system_fingerprint": self.spec.fingerprint,
                        "mechanism_id": mechanism.mechanism_id,
                        "mechanism_family": mechanism.family.value,
                        "implementation": mechanism.implementation,
                        "implementation_version": mechanism.version,
                        "period": period,
                        "trigger": trigger,
                        "input_event_ids": list(input_lineage),
                    }
                    envelope = EventEnvelope.create(
                        sequence=event_sequence + len(events),
                        year=period,
                        phase=schedule.phase,
                        event_type=request.event_type,
                        actor_ids=request.actor_ids,
                        artifact_ids=request.artifact_ids,
                        payload=_strict_json_clone(request.payload),
                        provenance=_strict_json_clone(provenance),
                    )
                    events.append(envelope)
                    invocation_events.append(envelope)

                emitted_event_ids = tuple(
                    event.event_id for event in invocation_events
                )
                for port_id, values in normalized_outputs.items():
                    source_port = _port(mechanism.outputs, port_id)
                    assert source_port is not None
                    for connection in self._connections.get(
                        (mechanism.mechanism_id, port_id), ()
                    ):
                        for value in values:
                            lineage = _stable_unique(
                                (*value.lineage_event_ids, *emitted_event_ids)
                            )
                            delivered = DeliveredValue(
                                channel=source_port.channel,
                                artifact_type=source_port.artifact_type,
                                payload=_strict_json_clone(value.payload),
                                actor_ids=value.actor_ids,
                                artifact_ids=value.artifact_ids,
                                lineage_event_ids=lineage,
                                source_mechanism=mechanism.mechanism_id,
                                source_port=port_id,
                                emitted_period=period,
                                available_period=period + connection.latency,
                            )
                            queue.append(
                                _QueuedDelivery(
                                    delivery_order,
                                    connection.target_mechanism,
                                    connection.target_port,
                                    delivered,
                                )
                            )
                            delivery_order += 1

                # Consume only after successful execution and output validation.
                queue = [item for item in queue if item.order not in selected_orders]
                if result.next_state is not None:
                    mechanism_states[mechanism.mechanism_id] = _strict_json_clone(
                        result.next_state
                    )
                trace.append(
                    ExecutionRecord(
                        period,
                        schedule.phase,
                        mechanism.mechanism_id,
                        "executed",
                        input_counts,
                        {
                            port_id: len(values)
                            for port_id, values in normalized_outputs.items()
                        },
                        emitted_event_ids,
                    )
                )

        next_checkpoint = GraphCheckpoint(
            system_id=self.spec.system_id,
            system_fingerprint=self.spec.fingerprint,
            trigger=trigger,
            next_period=effective_start + periods,
            next_event_sequence=event_sequence + len(events),
            next_delivery_order=delivery_order,
            mechanism_states=_strict_json_clone(mechanism_states),
            queued_deliveries=tuple(sorted(queue, key=lambda item: item.order)),
        )
        return GraphRunResult(
            system_id=self.spec.system_id,
            system_fingerprint=self.spec.fingerprint,
            start_period=effective_start,
            periods=periods,
            trigger=trigger,
            events=tuple(events),
            trace=tuple(trace),
            pending_deliveries=len(queue),
            checkpoint=next_checkpoint,
        )


def _implementation_key(implementation: str, version: int) -> ImplementationKey:
    if not isinstance(implementation, str) or not implementation.strip():
        raise GraphRuntimeError("implementation id must be a non-empty string")
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise GraphRuntimeError("implementation version must be a positive integer")
    return implementation, version


def _initial_mechanism_states(spec: SystemSpec) -> dict[str, Mapping[str, Any]]:
    raw = spec.initial_state.get("mechanism_states", {})
    if not isinstance(raw, Mapping):
        raise GraphRuntimeError("initial_state.mechanism_states must be a mapping")
    known = {mechanism.mechanism_id for mechanism in spec.mechanisms}
    unknown = set(raw) - known
    if unknown:
        raise GraphRuntimeError(
            f"initial mechanism state refers to unknown mechanisms {sorted(unknown)!r}"
        )
    if any(
        not isinstance(key, str) or not isinstance(state, Mapping)
        for key, state in raw.items()
    ):
        raise GraphRuntimeError("initial mechanism states must map ids to mappings")
    _require_strict_json(raw, "initial mechanism states")
    return _strict_json_clone(raw)


def _validate_checkpoint(
    checkpoint: GraphCheckpoint,
    spec: SystemSpec,
    trigger: str,
) -> None:
    if checkpoint.schema_version != CHECKPOINT_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported graph checkpoint schema")
    if checkpoint.system_id != spec.system_id:
        raise GraphRuntimeError("checkpoint system_id does not match SystemSpec")
    if checkpoint.system_fingerprint != spec.fingerprint:
        raise GraphRuntimeError("checkpoint fingerprint does not match SystemSpec")
    if checkpoint.trigger != trigger:
        raise GraphRuntimeError("checkpoint trigger does not match requested trigger")
    known = {mechanism.mechanism_id for mechanism in spec.mechanisms}
    if set(checkpoint.mechanism_states) - known:
        raise GraphRuntimeError("checkpoint has state for an unknown mechanism")
    for item in checkpoint.queued_deliveries:
        mechanism = next(
            (
                candidate
                for candidate in spec.mechanisms
                if candidate.mechanism_id == item.target_mechanism
            ),
            None,
        )
        if mechanism is None or _port(mechanism.inputs, item.target_port) is None:
            raise GraphRuntimeError("checkpoint delivery target is absent from SystemSpec")
    # Reparse the canonical representation to enforce all scalar and queue
    # invariants even when a caller constructed the dataclass directly.
    GraphCheckpoint.from_dict(checkpoint.to_dict())


def _queued_delivery_to_dict(item: _QueuedDelivery) -> dict[str, Any]:
    value = item.value
    return {
        "order": item.order,
        "target_mechanism": item.target_mechanism,
        "target_port": item.target_port,
        "value": {
            "channel": value.channel.value,
            "artifact_type": value.artifact_type,
            "payload": _strict_json_clone(value.payload),
            "actor_ids": list(value.actor_ids),
            "artifact_ids": list(value.artifact_ids),
            "lineage_event_ids": list(value.lineage_event_ids),
            "source_mechanism": value.source_mechanism,
            "source_port": value.source_port,
            "emitted_period": value.emitted_period,
            "available_period": value.available_period,
        },
    }


def _queued_delivery_from_dict(value: Mapping[str, Any]) -> _QueuedDelivery:
    if not isinstance(value, Mapping) or set(value) != {
        "order",
        "target_mechanism",
        "target_port",
        "value",
    }:
        raise GraphRuntimeError("checkpoint delivery fields do not match v1 schema")
    order = value["order"]
    if isinstance(order, bool) or not isinstance(order, int) or order < 0:
        raise GraphRuntimeError("checkpoint delivery order must be non-negative")
    for key in ("target_mechanism", "target_port"):
        if not isinstance(value[key], str) or not value[key]:
            raise GraphRuntimeError(f"checkpoint delivery {key} is invalid")
    raw = value["value"]
    fields = {
        "channel",
        "artifact_type",
        "payload",
        "actor_ids",
        "artifact_ids",
        "lineage_event_ids",
        "source_mechanism",
        "source_port",
        "emitted_period",
        "available_period",
    }
    if not isinstance(raw, Mapping) or set(raw) != fields:
        raise GraphRuntimeError("checkpoint delivered value fields do not match v1 schema")
    try:
        channel = ChannelKind(raw["channel"])
    except (TypeError, ValueError) as exc:
        raise GraphRuntimeError("checkpoint delivery channel is invalid") from exc
    if not isinstance(raw["payload"], Mapping):
        raise GraphRuntimeError("checkpoint delivery payload must be a mapping")
    for key in ("actor_ids", "artifact_ids", "lineage_event_ids"):
        if not isinstance(raw[key], list):
            raise GraphRuntimeError(f"checkpoint delivery {key} must be a list")
        _require_string_ids(raw[key], key)
    for key in ("source_mechanism", "source_port"):
        if not isinstance(raw[key], str) or not raw[key]:
            raise GraphRuntimeError(f"checkpoint delivery {key} is invalid")
    for key in ("emitted_period", "available_period"):
        if isinstance(raw[key], bool) or not isinstance(raw[key], int):
            raise GraphRuntimeError(f"checkpoint delivery {key} must be an integer")
    artifact_type = raw["artifact_type"]
    if artifact_type is not None and not isinstance(artifact_type, str):
        raise GraphRuntimeError("checkpoint delivery artifact_type is invalid")
    return _QueuedDelivery(
        order=order,
        target_mechanism=value["target_mechanism"],
        target_port=value["target_port"],
        value=DeliveredValue(
            channel=channel,
            artifact_type=artifact_type,
            payload=_strict_json_clone(raw["payload"]),
            actor_ids=tuple(raw["actor_ids"]),
            artifact_ids=tuple(raw["artifact_ids"]),
            lineage_event_ids=tuple(raw["lineage_event_ids"]),
            source_mechanism=raw["source_mechanism"],
            source_port=raw["source_port"],
            emitted_period=raw["emitted_period"],
            available_period=raw["available_period"],
        ),
    )


def _connections_by_source(spec: SystemSpec) -> dict[tuple[str, str], tuple[Any, ...]]:
    grouped: dict[tuple[str, str], list[Any]] = {}
    for connection in spec.connections:
        grouped.setdefault(
            (connection.source_mechanism, connection.source_port), []
        ).append(connection)
    return {
        key: tuple(
            sorted(
                values,
                key=lambda item: (
                    item.target_mechanism,
                    item.target_port,
                    item.latency,
                ),
            )
        )
        for key, values in grouped.items()
    }


def _select_inputs(
    queue: Sequence[_QueuedDelivery],
    mechanism: MechanismSpec,
    period: int,
) -> tuple[dict[str, tuple[DeliveredValue, ...]], set[int]]:
    selected_orders: set[int] = set()
    inputs: dict[str, tuple[DeliveredValue, ...]] = {}
    for port in mechanism.inputs:
        selected = sorted(
            (
                item
                for item in queue
                if item.target_mechanism == mechanism.mechanism_id
                and item.target_port == port.port_id
                and item.value.available_period <= period
            ),
            key=lambda item: item.order,
        )
        for item in selected:
            if item.value.channel != port.channel:
                raise GraphRuntimeError(
                    f"delivery to {mechanism.mechanism_id}.{port.port_id} has "
                    f"channel {item.value.channel.value!r}, expected {port.channel.value!r}"
                )
            if item.value.artifact_type != port.artifact_type:
                raise GraphRuntimeError(
                    f"delivery to {mechanism.mechanism_id}.{port.port_id} has "
                    f"artifact type {item.value.artifact_type!r}, expected "
                    f"{port.artifact_type!r}"
                )
            selected_orders.add(item.order)
        inputs[port.port_id] = tuple(item.value for item in selected)
    return inputs, selected_orders


def _validate_result(
    mechanism: MechanismSpec,
    result: MechanismResult,
) -> dict[str, tuple[MechanismValue, ...]]:
    declared = {port.port_id: port for port in mechanism.outputs}
    unknown = set(result.outputs) - set(declared)
    if unknown:
        raise GraphRuntimeError(
            f"{mechanism.mechanism_id!r} emitted undeclared output ports "
            f"{sorted(unknown)!r}"
        )
    normalized: dict[str, tuple[MechanismValue, ...]] = {}
    for port in mechanism.outputs:
        raw_values = tuple(result.outputs.get(port.port_id, ()))
        if port.required and not raw_values:
            raise GraphRuntimeError(
                f"{mechanism.mechanism_id!r} did not emit required output "
                f"{port.port_id!r}"
            )
        for value in raw_values:
            if not isinstance(value, MechanismValue):
                raise GraphRuntimeError(
                    f"{mechanism.mechanism_id}.{port.port_id} emitted "
                    f"{type(value).__name__}, expected MechanismValue"
                )
            _require_strict_json(value.payload, f"output {port.port_id!r}")
            _require_string_ids(value.actor_ids, "actor_ids")
            _require_string_ids(value.artifact_ids, "artifact_ids")
            _require_string_ids(value.lineage_event_ids, "lineage_event_ids")
        normalized[port.port_id] = raw_values
    for event in result.events:
        if not isinstance(event, MechanismEvent):
            raise GraphRuntimeError(
                f"{mechanism.mechanism_id!r} emitted a non-MechanismEvent"
            )
        if not isinstance(event.event_type, str) or not event.event_type.strip():
            raise GraphRuntimeError("event_type must be a non-empty string")
        _require_string_ids(event.actor_ids, "actor_ids")
        _require_string_ids(event.artifact_ids, "artifact_ids")
        _require_strict_json(event.payload, "event payload")
        _require_strict_json(event.provenance, "event provenance")
    return normalized


def _require_strict_json(value: Any, label: str) -> None:
    try:
        json.dumps(value, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise GraphRuntimeError(f"{label} is not strict JSON: {exc}") from exc


def _require_string_ids(values: Sequence[str], label: str) -> None:
    if any(not isinstance(value, str) or not value for value in values):
        raise GraphRuntimeError(f"{label} must contain only non-empty strings")


def _strict_json_clone(value: Any) -> Any:
    return json.loads(
        json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )


def _stable_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _port(ports: Sequence[PortSpec], port_id: str) -> PortSpec | None:
    return next((port for port in ports if port.port_id == port_id), None)
