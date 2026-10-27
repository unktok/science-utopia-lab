"""Structural validation for a whole-system mechanism graph."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Iterable

from .model import ChannelKind, MechanismFamily, SystemSpec


_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def valid(self) -> bool:
        return not self.errors

    def require_valid(self) -> None:
        if self.errors:
            raise SystemSpecValidationError(self)


class SystemSpecValidationError(ValueError):
    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        details = "; ".join(
            f"{issue.path}: {issue.message}" for issue in report.errors
        )
        super().__init__(f"Invalid SystemSpec: {details}")


def validate_system_spec(spec: SystemSpec) -> ValidationReport:
    """Validate graph references, port types, schedules, and JSON stability.

    This establishes technical conformance only.  It does not establish that a
    system is scientifically useful, ethically acceptable, or policy-ready.
    """

    issues: list[ValidationIssue] = []

    def error(code: str, path: str, message: str) -> None:
        issues.append(ValidationIssue(code, path, message))

    def warning(code: str, path: str, message: str) -> None:
        issues.append(ValidationIssue(code, path, message, "warning"))

    _check_id(spec.system_id, "system_id", error)
    if isinstance(spec.version, bool) or not isinstance(spec.version, int) or spec.version < 1:
        error("invalid_version", "version", "must be a positive integer")

    _check_unique(
        ((item.agent_type_id, f"agent_types[{index}].agent_type_id")
         for index, item in enumerate(spec.agent_types)),
        "duplicate_agent_type",
        error,
    )
    for index, item in enumerate(spec.agent_types):
        _check_id(item.agent_type_id, f"agent_types[{index}].agent_type_id", error)

    artifact_ids = {item.artifact_type_id for item in spec.artifact_types}
    _check_unique(
        ((item.artifact_type_id, f"artifact_types[{index}].artifact_type_id")
         for index, item in enumerate(spec.artifact_types)),
        "duplicate_artifact_type",
        error,
    )
    for index, item in enumerate(spec.artifact_types):
        _check_id(item.artifact_type_id, f"artifact_types[{index}].artifact_type_id", error)

    mechanisms = {item.mechanism_id: item for item in spec.mechanisms}
    _check_unique(
        ((item.mechanism_id, f"mechanisms[{index}].mechanism_id")
         for index, item in enumerate(spec.mechanisms)),
        "duplicate_mechanism",
        error,
    )
    for index, mechanism in enumerate(spec.mechanisms):
        base = f"mechanisms[{index}]"
        _check_id(mechanism.mechanism_id, f"{base}.mechanism_id", error)
        if not isinstance(mechanism.family, MechanismFamily):
            error("invalid_family", f"{base}.family", "must be a known mechanism family")
        if not isinstance(mechanism.implementation, str) or not mechanism.implementation.strip():
            error("empty_implementation", f"{base}.implementation", "must not be empty")
        if (
            isinstance(mechanism.version, bool)
            or not isinstance(mechanism.version, int)
            or mechanism.version < 1
        ):
            error("invalid_version", f"{base}.version", "must be a positive integer")
        ports = [
            *((port.port_id, f"{base}.inputs[{port_index}]")
              for port_index, port in enumerate(mechanism.inputs)),
            *((port.port_id, f"{base}.outputs[{port_index}]")
              for port_index, port in enumerate(mechanism.outputs)),
        ]
        _check_unique(ports, "duplicate_port", error)
        for port_id, path in ports:
            _check_id(port_id, f"{path}.port_id", error)
        for direction, port_set in (("inputs", mechanism.inputs), ("outputs", mechanism.outputs)):
            for port_index, port in enumerate(port_set):
                if not isinstance(port.channel, ChannelKind):
                    error(
                        "invalid_channel",
                        f"{base}.{direction}[{port_index}].channel",
                        "must be a known channel kind",
                    )
                if port.artifact_type is not None and port.artifact_type not in artifact_ids:
                    error(
                        "unknown_artifact_type",
                        f"{base}.{direction}[{port_index}].artifact_type",
                        f"references {port.artifact_type!r}",
                    )

    seen_connections: set[tuple[str, str, str, str]] = set()
    connected_inputs: set[tuple[str, str]] = set()
    for index, connection in enumerate(spec.connections):
        path = f"connections[{index}]"
        key = (
            connection.source_mechanism,
            connection.source_port,
            connection.target_mechanism,
            connection.target_port,
        )
        if key in seen_connections:
            error("duplicate_connection", path, "duplicates an existing graph edge")
        seen_connections.add(key)
        if (
            isinstance(connection.latency, bool)
            or not isinstance(connection.latency, int)
            or connection.latency < 0
        ):
            error("invalid_latency", f"{path}.latency", "must be a non-negative integer")
        if not isinstance(connection.channel, ChannelKind):
            error("invalid_channel", f"{path}.channel", "must be a known channel kind")

        source = mechanisms.get(connection.source_mechanism)
        target = mechanisms.get(connection.target_mechanism)
        if source is None:
            error("unknown_source", f"{path}.source_mechanism", "mechanism does not exist")
        if target is None:
            error("unknown_target", f"{path}.target_mechanism", "mechanism does not exist")
        source_port = _port(source.outputs, connection.source_port) if source else None
        target_port = _port(target.inputs, connection.target_port) if target else None
        if source is not None and source_port is None:
            error("unknown_source_port", f"{path}.source_port", "output port does not exist")
        if target is not None and target_port is None:
            error("unknown_target_port", f"{path}.target_port", "input port does not exist")
        if source_port is not None and source_port.channel != connection.channel:
            error("source_channel_mismatch", f"{path}.channel", "does not match source port")
        if target_port is not None and target_port.channel != connection.channel:
            error("target_channel_mismatch", f"{path}.channel", "does not match target port")
        if (
            source_port is not None
            and target_port is not None
            and source_port.artifact_type is not None
            and target_port.artifact_type is not None
            and source_port.artifact_type != target_port.artifact_type
        ):
            error("artifact_type_mismatch", path, "source and target artifact types differ")
        if target_port is not None:
            connected_inputs.add((connection.target_mechanism, connection.target_port))

    for mechanism in spec.mechanisms:
        for port in mechanism.inputs:
            if port.required and (mechanism.mechanism_id, port.port_id) not in connected_inputs:
                error(
                    "unconnected_required_input",
                    f"mechanisms.{mechanism.mechanism_id}.inputs.{port.port_id}",
                    "required input has no incoming connection",
                )

    scheduled: set[str] = set()
    for index, schedule in enumerate(spec.schedules):
        path = f"schedules[{index}]"
        if schedule.mechanism_id not in mechanisms:
            error("unknown_scheduled_mechanism", f"{path}.mechanism_id", "mechanism does not exist")
        if schedule.mechanism_id in scheduled:
            error("duplicate_schedule", path, "mechanism is scheduled more than once")
        scheduled.add(schedule.mechanism_id)
        if (
            isinstance(schedule.phase, bool)
            or not isinstance(schedule.phase, int)
            or schedule.phase < 0
        ):
            error("invalid_phase", f"{path}.phase", "must be a non-negative integer")
        if not isinstance(schedule.trigger, str) or not schedule.trigger.strip():
            error("empty_trigger", f"{path}.trigger", "must not be empty")
    for mechanism_id in mechanisms.keys() - scheduled:
        warning(
            "unscheduled_mechanism",
            f"mechanisms.{mechanism_id}",
            "has no schedule; this is valid only for externally triggered or passive mechanisms",
        )

    if len(spec.global_invariants) != len(set(spec.global_invariants)):
        error("duplicate_invariant", "global_invariants", "contains duplicate invariant ids")
    for index, invariant in enumerate(spec.global_invariants):
        if not isinstance(invariant, str) or not invariant.strip():
            error("invalid_invariant", f"global_invariants[{index}]", "must be a non-empty string")

    try:
        json.dumps(spec.to_dict(), allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        error("non_json_value", "$", f"spec is not strict-JSON serializable: {exc}")

    return ValidationReport(tuple(issues))


def _check_id(value: object, path: str, add_error) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        add_error("invalid_id", path, "must be a lowercase dotted/dashed identifier")


def _check_unique(
    items: Iterable[tuple[str, str]], code: str, add_error
) -> None:
    seen: set[str] = set()
    for value, path in items:
        if value in seen:
            add_error(code, path, f"duplicate id {value!r}")
        seen.add(value)


def _port(ports, port_id: str):
    return next((port for port in ports if port.port_id == port_id), None)
