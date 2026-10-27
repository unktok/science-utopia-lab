"""Typed, serializable model of a complete science-system mechanism graph."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Mapping


class MechanismFamily(str, Enum):
    """Non-exclusive families used to describe, not prescribe, a system."""

    POPULATION = "population"
    RESEARCH = "research"
    EVALUATION = "evaluation"
    PUBLICATION = "publication"
    FUNDING = "funding"
    GOVERNANCE = "governance"
    COMMUNICATION = "communication"
    COLLABORATION = "collaboration"
    EMPLOYMENT = "employment"
    EDUCATION = "education"
    CUSTOM = "custom"


class ChannelKind(str, Enum):
    ARTIFACT = "artifact"
    SCORE = "score"
    DECISION = "decision"
    FEEDBACK = "feedback"
    RESOURCE = "resource"
    SIGNAL = "signal"
    CONSTRAINT = "constraint"


@dataclass(frozen=True)
class AgentTypeSpec:
    agent_type_id: str
    roles: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class ArtifactTypeSpec:
    artifact_type_id: str
    description: str = ""


@dataclass(frozen=True)
class PortSpec:
    port_id: str
    channel: ChannelKind
    artifact_type: str | None = None
    required: bool = True


@dataclass(frozen=True)
class MechanismSpec:
    mechanism_id: str
    family: MechanismFamily
    implementation: str
    version: int = 1
    inputs: tuple[PortSpec, ...] = ()
    outputs: tuple[PortSpec, ...] = ()
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConnectionSpec:
    source_mechanism: str
    source_port: str
    target_mechanism: str
    target_port: str
    channel: ChannelKind
    latency: int = 0


@dataclass(frozen=True)
class ScheduleSpec:
    mechanism_id: str
    phase: int
    trigger: str = "annual"


@dataclass(frozen=True)
class SystemSpec:
    """The complete design object passed across optimization boundaries.

    No mechanism family is mandatory.  An empty graph and a graph without an
    evaluation, publication, funding, or governance mechanism are all valid
    structural possibilities.  A concrete compiler may impose a narrower
    executable subset.
    """

    system_id: str
    version: int
    agent_types: tuple[AgentTypeSpec, ...] = ()
    artifact_types: tuple[ArtifactTypeSpec, ...] = ()
    mechanisms: tuple[MechanismSpec, ...] = ()
    connections: tuple[ConnectionSpec, ...] = ()
    schedules: tuple[ScheduleSpec, ...] = ()
    initial_state: Mapping[str, Any] = field(default_factory=dict)
    global_invariants: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a strict-JSON-ready representation with stable enum values."""

        return _enum_values(asdict(self))

    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SystemSpec":
        """Parse the canonical dictionary representation.

        Graph semantics are deliberately checked by ``validate_system_spec``;
        this method only performs the typed conversion.
        """

        return cls(
            system_id=value["system_id"],
            version=value["version"],
            agent_types=tuple(
                AgentTypeSpec(
                    agent_type_id=item["agent_type_id"],
                    roles=tuple(item.get("roles", ())),
                    description=item.get("description", ""),
                )
                for item in value.get("agent_types", ())
            ),
            artifact_types=tuple(
                ArtifactTypeSpec(**item) for item in value.get("artifact_types", ())
            ),
            mechanisms=tuple(_mechanism_from_dict(item) for item in value.get("mechanisms", ())),
            connections=tuple(
                ConnectionSpec(
                    **{
                        **item,
                        "channel": ChannelKind(item["channel"]),
                    }
                )
                for item in value.get("connections", ())
            ),
            schedules=tuple(ScheduleSpec(**item) for item in value.get("schedules", ())),
            initial_state=value.get("initial_state", {}),
            global_invariants=tuple(value.get("global_invariants", ())),
            metadata=value.get("metadata", {}),
        )


def _enum_values(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _enum_values(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_enum_values(item) for item in value]
    return value


def _port_from_dict(value: Mapping[str, Any]) -> PortSpec:
    return PortSpec(
        port_id=value["port_id"],
        channel=ChannelKind(value["channel"]),
        artifact_type=value.get("artifact_type"),
        required=value.get("required", True),
    )


def _mechanism_from_dict(value: Mapping[str, Any]) -> MechanismSpec:
    return MechanismSpec(
        mechanism_id=value["mechanism_id"],
        family=MechanismFamily(value["family"]),
        implementation=value["implementation"],
        version=value.get("version", 1),
        inputs=tuple(_port_from_dict(item) for item in value.get("inputs", ())),
        outputs=tuple(_port_from_dict(item) for item in value.get("outputs", ())),
        parameters=value.get("parameters", {}),
    )
