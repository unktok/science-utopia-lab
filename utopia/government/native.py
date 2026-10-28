"""Native prospective adapter for production government policy mechanisms.

The adapter is separate from optimization loss and from the legacy simulator's
fixed topology.  It observes explicit annual mechanism summaries, invokes the
existing production government handler, and delivers versioned directives over
the exact delayed edges declared by a complete ``SystemSpec``.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence

from utopia.optimization.government_structural import ENGINEERING_POLICY_DIRECTIVES
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
from utopia.system.production.governance import (
    EVENT_RESPONSIVE_GOVERNMENT,
    POLICY_SCHEMA_VERSION,
    STATE_SCHEMA_VERSION,
    THRESHOLD_GOVERNMENT,
    event_responsive_government,
    parse_policy_decision,
    resolve_active_policy,
    threshold_government,
)
from utopia.system.runtime import (
    DeliveredValue,
    GraphRuntimeError,
    MechanismContext,
    MechanismResult,
)
from utopia.system.validation import validate_system_spec


NATIVE_GOVERNMENT_OVERLAY = "scienceutopia.native-government-overlay.v1"
NATIVE_GOVERNMENT_STATE = "scienceutopia.native-government-state.v1"
GOVERNMENT_MECHANISM_ID = "native.government.policy-maker"

OBSERVATION_EVENT_TYPE = "native.government.mechanism_observed"
DECISION_EVENT_TYPE = "native.government.policy_decided"
APPLICATION_EVENT_TYPE = "native.government.policy_applied"

OBSERVATION_CONTRACTS = {
    "evaluation": (
        "legacy.evaluation",
        "decisions",
        ChannelKind.DECISION,
        "evaluation-decision",
        4,
    ),
    "funding": (
        "legacy.funding",
        "allocations",
        ChannelKind.RESOURCE,
        "resource-allocation",
        5,
    ),
    "publication": (
        "legacy.publication",
        "publications",
        ChannelKind.ARTIFACT,
        "published-output",
        6,
    ),
}
POLICY_CONTRACTS = {
    "evaluation": (
        "evaluation_policies",
        "legacy.evaluation",
        "policies",
    ),
    "funding": (
        "funding_policies",
        "legacy.funding",
        "policies",
    ),
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class NativeGovernmentError(ValueError):
    """Native government config, graph, event, or checkpoint is invalid."""


@dataclass(frozen=True)
class NativeGovernmentConfig:
    implementation: str
    minimum_observations: int
    repeat_interval: int
    directives: Mapping[str, Mapping[str, Any]]
    observation_sources: tuple[str, ...]
    policy_latencies: tuple[tuple[str, int], ...]
    system_fingerprint: str
    mechanism_id: str = GOVERNMENT_MECHANISM_ID

    @property
    def mode(self) -> str:
        if self.implementation == EVENT_RESPONSIVE_GOVERNMENT:
            return "event-responsive"
        if self.implementation == THRESHOLD_GOVERNMENT:
            return "threshold"
        raise NativeGovernmentError("government implementation is unsupported")

    @property
    def latency_by_target(self) -> dict[str, int]:
        return dict(self.policy_latencies)

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.to_dict())

    def validate(self) -> None:
        _ = self.mode
        for name, value in (
            ("minimum_observations", self.minimum_observations),
            ("repeat_interval", self.repeat_interval),
        ):
            if type(value) is not int or value < 1:
                raise NativeGovernmentError(f"{name} must be positive")
        if (
            len(self.observation_sources) != len(set(self.observation_sources))
            or not set(self.observation_sources) <= set(OBSERVATION_CONTRACTS)
        ):
            raise NativeGovernmentError("government observation sources are invalid")
        targets = [target for target, _latency in self.policy_latencies]
        if len(targets) != len(set(targets)) or not set(targets) <= set(POLICY_CONTRACTS):
            raise NativeGovernmentError("government policy targets are invalid")
        if any(type(latency) is not int or latency not in {1, 2}
               for _target, latency in self.policy_latencies):
            raise NativeGovernmentError("government policy latency must be one or two")
        if not isinstance(self.mechanism_id, str) or not self.mechanism_id:
            raise NativeGovernmentError("government mechanism id must be non-empty")
        if not _SHA256.fullmatch(self.system_fingerprint):
            raise NativeGovernmentError("government SystemSpec fingerprint is invalid")
        if _json_value(self.directives) != ENGINEERING_POLICY_DIRECTIVES:
            raise NativeGovernmentError(
                "government directives differ from the catalog engineering fixture"
            )
        try:
            parse_policy_decision({
                "schema_version": POLICY_SCHEMA_VERSION,
                "policy_id": "validation-policy",
                "policy_version": 1,
                "issuer_id": self.mechanism_id,
                "system_fingerprint": self.system_fingerprint,
                "issued_period": 0,
                "observed_event_ids": ["validation-event"],
                "directives": _json_value(self.directives),
            })
        except GraphRuntimeError as error:
            raise NativeGovernmentError(str(error)) from error

    def to_dict(self) -> dict[str, Any]:
        return {
            "implementation": self.implementation,
            "minimum_observations": self.minimum_observations,
            "repeat_interval": self.repeat_interval,
            "directives": _json_value(self.directives),
            "observation_sources": list(self.observation_sources),
            "policy_latencies": [
                {"target": target, "latency": latency}
                for target, latency in self.policy_latencies
            ],
            "system_fingerprint": self.system_fingerprint,
            "mechanism_id": self.mechanism_id,
        }


def native_government_config_from_namespace(
    namespace: Any,
) -> NativeGovernmentConfig | None:
    """Build config from parsed CLI arguments; ``off`` means no mechanism."""

    mode = getattr(namespace, "government_policy_mode", "off")
    if mode == "off":
        return None
    implementation = {
        "event-responsive": EVENT_RESPONSIVE_GOVERNMENT,
        "threshold": THRESHOLD_GOVERNMENT,
    }.get(mode)
    if implementation is None:
        raise NativeGovernmentError("government policy mode is unsupported")
    try:
        directives = json.loads(getattr(namespace, "government_directives_json", ""))
    except (TypeError, json.JSONDecodeError) as error:
        raise NativeGovernmentError("government directives JSON is invalid") from error
    observations = _parse_csv(
        getattr(namespace, "government_observation_sources", ""),
        "government observation sources",
    )
    latencies = _parse_policy_edges(
        getattr(namespace, "government_policy_edges", "")
    )
    config = NativeGovernmentConfig(
        implementation=implementation,
        minimum_observations=getattr(namespace, "government_minimum_observations", None),
        repeat_interval=getattr(namespace, "government_repeat_interval", None),
        directives=directives,
        observation_sources=observations,
        policy_latencies=latencies,
        system_fingerprint=getattr(namespace, "government_system_fingerprint", None),
    )
    config.validate()
    return config


def native_government_system_spec(
    base: SystemSpec,
    *,
    implementation: str,
    observation_sources: Sequence[str] = ("evaluation", "funding", "publication"),
    policy_latencies: Mapping[str, int] | None = None,
    minimum_observations: int | None = None,
    repeat_interval: int | None = None,
) -> SystemSpec:
    """Add the exact catalog-derived government overlay to an executable spec."""

    if implementation == EVENT_RESPONSIVE_GOVERNMENT:
        minimum = 1 if minimum_observations is None else minimum_observations
        repeat = 1 if repeat_interval is None else repeat_interval
        mode = "event-responsive"
    elif implementation == THRESHOLD_GOVERNMENT:
        minimum = 10 if minimum_observations is None else minimum_observations
        repeat = 10 if repeat_interval is None else repeat_interval
        mode = "threshold"
    else:
        raise NativeGovernmentError("government implementation is unsupported")
    sources = tuple(observation_sources)
    latencies = dict(policy_latencies or {"evaluation": 1, "funding": 1})
    provisional = NativeGovernmentConfig(
        implementation=implementation,
        minimum_observations=minimum,
        repeat_interval=repeat,
        directives=ENGINEERING_POLICY_DIRECTIVES,
        observation_sources=sources,
        policy_latencies=tuple(sorted(latencies.items())),
        system_fingerprint="0" * 64,
    )
    provisional.validate()
    if "native_government" in base.metadata:
        raise NativeGovernmentError("SystemSpec already declares native government")
    if any(item.mechanism_id == GOVERNMENT_MECHANISM_ID for item in base.mechanisms):
        raise NativeGovernmentError("native government mechanism id already exists")
    if any(item.artifact_type_id == "government-policy" for item in base.artifact_types):
        raise NativeGovernmentError("government-policy artifact already exists")
    mechanisms = {item.mechanism_id: item for item in base.mechanisms}
    for mechanism_id in ("legacy.evaluation", "legacy.funding", "legacy.publication"):
        if mechanism_id not in mechanisms:
            raise NativeGovernmentError(f"native government requires {mechanism_id}")
    updated_mechanisms = []
    for mechanism in base.mechanisms:
        if mechanism.mechanism_id in {"legacy.evaluation", "legacy.funding"}:
            if any(port.port_id == "policies" for port in mechanism.inputs):
                raise NativeGovernmentError(
                    f"{mechanism.mechanism_id} already declares policies input"
                )
            mechanism = replace(
                mechanism,
                inputs=mechanism.inputs + (
                    PortSpec(
                        "policies",
                        ChannelKind.CONSTRAINT,
                        "government-policy",
                        required=False,
                    ),
                ),
            )
        updated_mechanisms.append(mechanism)
    government = MechanismSpec(
        GOVERNMENT_MECHANISM_ID,
        MechanismFamily.GOVERNANCE,
        implementation,
        inputs=tuple(
            PortSpec(
                OBSERVATION_CONTRACTS[source][1],
                OBSERVATION_CONTRACTS[source][2],
                OBSERVATION_CONTRACTS[source][3],
                required=False,
            )
            for source in OBSERVATION_CONTRACTS
        ),
        outputs=tuple(
            PortSpec(port, ChannelKind.CONSTRAINT, "government-policy", required=False)
            for port, _target, _input in POLICY_CONTRACTS.values()
        ),
        parameters={
            "directives": deepcopy(ENGINEERING_POLICY_DIRECTIVES),
            "minimum_observations": minimum,
            "repeat_interval": repeat,
        },
    )
    observation_edges = tuple(
        ConnectionSpec(
            OBSERVATION_CONTRACTS[source][0],
            OBSERVATION_CONTRACTS[source][1],
            GOVERNMENT_MECHANISM_ID,
            OBSERVATION_CONTRACTS[source][1],
            OBSERVATION_CONTRACTS[source][2],
        )
        for source in sources
    )
    policy_edges = tuple(
        ConnectionSpec(
            GOVERNMENT_MECHANISM_ID,
            POLICY_CONTRACTS[target][0],
            POLICY_CONTRACTS[target][1],
            POLICY_CONTRACTS[target][2],
            ChannelKind.CONSTRAINT,
            latency=latency,
        )
        for target, latency in sorted(latencies.items())
    )
    spec = replace(
        base,
        system_id=f"{base.system_id}-native-government-{mode}",
        artifact_types=base.artifact_types + (
            ArtifactTypeSpec("government-policy", "Versioned policy decision"),
        ),
        mechanisms=tuple(updated_mechanisms) + (government,),
        connections=base.connections + observation_edges + policy_edges,
        schedules=base.schedules + (ScheduleSpec(GOVERNMENT_MECHANISM_ID, 9),),
        global_invariants=base.global_invariants + (
            "native-government-policy-lineage",
            "native-government-monotonic-version",
            "native-government-fingerprint-bound",
        ),
        metadata={
            **base.metadata,
            "native_government": {
                "schema": NATIVE_GOVERNMENT_OVERLAY,
                "base_system_id": base.system_id,
                "implementation": implementation,
                "minimum_observations": minimum,
                "repeat_interval": repeat,
                "directives": deepcopy(ENGINEERING_POLICY_DIRECTIVES),
                "observation_sources": list(sources),
                "policy_latencies": [
                    {"target": target, "latency": latency}
                    for target, latency in sorted(latencies.items())
                ],
            },
        },
    )
    validate_system_spec(spec).require_valid()
    return spec


def native_government_system_spec_from_catalog_candidate(
    base: SystemSpec,
    candidate: Mapping[str, Any],
) -> SystemSpec:
    """Translate one canonical government structural candidate to native form.

    The structural candidate describes the government axes against its compact
    deterministic workload.  This adapter preserves those axes while replacing
    only that workload/base graph with the supplied executable simulator spec.
    """

    from utopia.optimization.government_structural import government_structural_space

    space = government_structural_space()
    catalog_spec = space.decode(candidate)
    selection = space.selection(candidate)
    option = selection.nodes["government"]
    if option is None:
        return replace(
            base,
            metadata={
                **base.metadata,
                "native_government_catalog_source": {
                    "space_id": space.grammar.space_id,
                    "candidate_fingerprint": catalog_spec.fingerprint,
                    "selection": selection.to_dict(),
                    "government_present": False,
                },
            },
        )
    government = next(
        item for item in catalog_spec.mechanisms if item.mechanism_id == "government"
    )
    observation_sources = tuple(
        source
        for source, slot in (
            ("evaluation", "observe-decisions"),
            ("funding", "observe-allocations"),
            ("publication", "observe-publications"),
        )
        if selection.edges[slot] is not None
    )
    policy_latencies = {
        target: next(
            edge.latency
            for edge in catalog_spec.connections
            if edge.source_mechanism == "government"
            and edge.target_mechanism == target
        )
        for target, slot in (
            ("evaluation", "policy-to-evaluation"),
            ("funding", "policy-to-funding"),
        )
        if selection.edges[slot] is not None
    }
    translated = native_government_system_spec(
        base,
        implementation=government.implementation,
        observation_sources=observation_sources,
        policy_latencies=policy_latencies,
        minimum_observations=government.parameters["minimum_observations"],
        repeat_interval=government.parameters["repeat_interval"],
    )
    return replace(
        translated,
        metadata={
            **translated.metadata,
            "native_government_catalog_source": {
                "space_id": space.grammar.space_id,
                "candidate_fingerprint": catalog_spec.fingerprint,
                "selection": selection.to_dict(),
                "government_present": True,
            },
        },
    )


def split_native_government_system_spec(
    spec: SystemSpec,
) -> tuple[SystemSpec, NativeGovernmentConfig | None]:
    """Validate and remove one exact government overlay for legacy compilation."""

    raw = spec.metadata.get("native_government")
    if raw is None:
        return spec, None
    required = {
        "schema", "base_system_id", "implementation", "minimum_observations",
        "repeat_interval", "directives", "observation_sources", "policy_latencies",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise NativeGovernmentError("native government metadata is invalid")
    if raw["schema"] != NATIVE_GOVERNMENT_OVERLAY:
        raise NativeGovernmentError("native government overlay schema is unsupported")
    latencies = _policy_latency_records(raw["policy_latencies"])
    sources = _string_sequence(raw["observation_sources"], "observation sources")
    base_metadata = dict(spec.metadata)
    base_metadata.pop("native_government")
    mechanisms = []
    found_government = False
    for mechanism in spec.mechanisms:
        if mechanism.mechanism_id == GOVERNMENT_MECHANISM_ID:
            found_government = True
            continue
        if mechanism.mechanism_id in {"legacy.evaluation", "legacy.funding"}:
            policy_ports = [port for port in mechanism.inputs if port.port_id == "policies"]
            if len(policy_ports) != 1:
                raise NativeGovernmentError(
                    f"{mechanism.mechanism_id} government policy port is invalid"
                )
            mechanism = replace(
                mechanism,
                inputs=tuple(port for port in mechanism.inputs if port.port_id != "policies"),
            )
        mechanisms.append(mechanism)
    if not found_government:
        raise NativeGovernmentError("native government node is missing")
    base = replace(
        spec,
        system_id=raw["base_system_id"],
        artifact_types=tuple(
            item for item in spec.artifact_types
            if item.artifact_type_id != "government-policy"
        ),
        mechanisms=tuple(mechanisms),
        connections=tuple(
            edge for edge in spec.connections
            if edge.source_mechanism != GOVERNMENT_MECHANISM_ID
            and edge.target_mechanism != GOVERNMENT_MECHANISM_ID
        ),
        schedules=tuple(
            item for item in spec.schedules
            if item.mechanism_id != GOVERNMENT_MECHANISM_ID
        ),
        global_invariants=tuple(
            item for item in spec.global_invariants
            if item not in {
                "native-government-policy-lineage",
                "native-government-monotonic-version",
                "native-government-fingerprint-bound",
            }
        ),
        metadata=base_metadata,
    )
    validate_system_spec(base).require_valid()
    expected = native_government_system_spec(
        base,
        implementation=raw["implementation"],
        observation_sources=sources,
        policy_latencies=dict(latencies),
        minimum_observations=raw["minimum_observations"],
        repeat_interval=raw["repeat_interval"],
    )
    if expected.to_dict() != spec.to_dict():
        raise NativeGovernmentError(
            "native government overlay differs from exact catalog contract"
        )
    config = NativeGovernmentConfig(
        implementation=raw["implementation"],
        minimum_observations=raw["minimum_observations"],
        repeat_interval=raw["repeat_interval"],
        directives=raw["directives"],
        observation_sources=sources,
        policy_latencies=latencies,
        system_fingerprint=spec.fingerprint,
    )
    config.validate()
    return base, config


class NativeGovernmentRuntime:
    """Checkpointable native adapter around the production government handler."""

    def __init__(
        self,
        config: NativeGovernmentConfig,
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

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self._state)

    def active_policy(self, target: str) -> Mapping[str, Any] | None:
        if target not in POLICY_CONTRACTS:
            raise NativeGovernmentError(f"unknown policy target {target!r}")
        value = self._state["active_policies"].get(target)
        return deepcopy(value) if value is not None else None

    @property
    def evaluation_acceptance_rate(self) -> float | None:
        active = self.active_policy("evaluation")
        return None if active is None else float(active["directive"]["acceptance_rate"])

    @property
    def funding_award_multiplier(self) -> float:
        active = self.active_policy("funding")
        if active is None:
            return 1.0
        return float(active["directive"].get("award_amount_multiplier", 1.0))

    def start_year(self, year: int) -> tuple[EventEnvelope, ...]:
        if type(year) is not int or year != self._state["last_completed_year"] + 1:
            raise NativeGovernmentError("government years must be contiguous")
        if self._state["last_started_year"] != self._state["last_completed_year"]:
            raise NativeGovernmentError("prior government year was not completed")
        before = len(self._state["events"])
        self._deliver_due(year)
        self._state["last_started_year"] = year
        return self.events[before:]

    def finish_year(
        self,
        year: int,
        observations: Mapping[str, Mapping[str, Any]],
    ) -> tuple[EventEnvelope, ...]:
        if (
            type(year) is not int
            or self._state["last_started_year"] != year
            or self._state["last_completed_year"] != year - 1
        ):
            raise NativeGovernmentError("government year was not started exactly once")
        if not isinstance(observations, Mapping):
            raise NativeGovernmentError("government observations must be a mapping")
        before = len(self._state["events"])
        delivered: dict[str, tuple[DeliveredValue, ...]] = {}
        for source in self.config.observation_sources:
            summary = observations.get(source)
            if not isinstance(summary, Mapping):
                raise NativeGovernmentError(
                    f"government observation {source!r} is missing"
                )
            _strict_json(summary, f"government {source} observation")
            event = self._append_event(
                year=year,
                phase=OBSERVATION_CONTRACTS[source][4],
                event_type=OBSERVATION_EVENT_TYPE,
                payload={
                    "source_family": source,
                    "summary": _json_value(summary),
                    "system_fingerprint": self.config.system_fingerprint,
                },
                provenance={
                    "namespace": "native.government",
                    "native_mechanism": OBSERVATION_CONTRACTS[source][0],
                },
            )
            port = OBSERVATION_CONTRACTS[source][1]
            delivered[port] = (
                DeliveredValue(
                    channel=OBSERVATION_CONTRACTS[source][2],
                    artifact_type=OBSERVATION_CONTRACTS[source][3],
                    payload=_json_value(summary),
                    actor_ids=(),
                    artifact_ids=(),
                    lineage_event_ids=(event.event_id,),
                    source_mechanism=OBSERVATION_CONTRACTS[source][0],
                    source_port=port,
                    emitted_period=year,
                    available_period=year,
                ),
            )
        result = self._invoke_production(year, delivered, self._state["production_state"])
        if result.next_state is None:
            raise NativeGovernmentError("production government returned no state")
        self._state["production_state"] = deepcopy(dict(result.next_state))
        self._record_decision(year, result)
        self._state["last_completed_year"] = year
        self._validate_state(self._state)
        return self.events[before:]

    def summary(self) -> dict[str, Any]:
        production = self._state["production_state"]
        return {
            "implementation": self.config.implementation,
            "system_fingerprint": self.config.system_fingerprint,
            "observed_values": production.get("observed_value_count", 0),
            "issued_policies": len(production.get("issued_policy_ids", ())),
            "active_targets": sorted(self._state["active_policies"]),
            "pending_deliveries": len(self._state["pending_deliveries"]),
            "checkpoint_fingerprint": self.checkpoint_fingerprint,
        }

    def _invoke_production(
        self,
        year: int,
        inputs: Mapping[str, tuple[DeliveredValue, ...]],
        state: Mapping[str, Any],
    ) -> MechanismResult:
        mechanism = MechanismSpec(
            self.config.mechanism_id,
            MechanismFamily.GOVERNANCE,
            self.config.implementation,
            inputs=tuple(
                PortSpec(
                    OBSERVATION_CONTRACTS[source][1],
                    OBSERVATION_CONTRACTS[source][2],
                    OBSERVATION_CONTRACTS[source][3],
                    required=False,
                )
                for source in OBSERVATION_CONTRACTS
            ),
            outputs=tuple(
                PortSpec(port, ChannelKind.CONSTRAINT, "government-policy", required=False)
                for port, _target, _input in POLICY_CONTRACTS.values()
            ),
            parameters={
                "directives": _json_value(self.config.directives),
                "minimum_observations": self.config.minimum_observations,
                "repeat_interval": self.config.repeat_interval,
            },
        )
        context = MechanismContext(
            system_id="native-prospective-simulator",
            system_fingerprint=self.config.system_fingerprint,
            mechanism=mechanism,
            period=year,
            phase=9,
            trigger="annual",
            inputs=inputs,
            initial_state={},
            state=state,
        )
        handler = (
            event_responsive_government
            if self.config.implementation == EVENT_RESPONSIVE_GOVERNMENT
            else threshold_government
        )
        try:
            return handler(context)
        except GraphRuntimeError as error:
            raise NativeGovernmentError(
                f"production government rejected native input/state: {error}"
            ) from error

    def _record_decision(self, year: int, result: MechanismResult) -> None:
        values = [
            value
            for port_values in result.outputs.values()
            for value in port_values
        ]
        if not values:
            if result.events:
                raise NativeGovernmentError("government emitted event without policy")
            return
        policies = [parse_policy_decision(value.payload) for value in values]
        if any(policy != policies[0] for policy in policies[1:]):
            raise NativeGovernmentError("government output ports disagree on policy")
        if len(result.events) != 1 or result.events[0].event_type != "government.policy_decided":
            raise NativeGovernmentError("production government decision event is invalid")
        policy = policies[0]
        decision = self._append_event(
            year=year,
            phase=9,
            event_type=DECISION_EVENT_TYPE,
            payload={"policy": policy},
            provenance={
                "namespace": "native.government",
                "native_mechanism": self.config.mechanism_id,
                "production_adapter": self.config.implementation,
                "source_event_ids": list(policy["observed_event_ids"]),
            },
        )
        output_by_target = {
            target: result.outputs.get(POLICY_CONTRACTS[target][0], ())
            for target in POLICY_CONTRACTS
        }
        for target, latency in self.config.policy_latencies:
            target_values = output_by_target[target]
            if len(target_values) != 1 or target_values[0].payload != policy:
                raise NativeGovernmentError(
                    f"production government output for {target} is invalid"
                )
            self._state["pending_deliveries"].append({
                "target": target,
                "due_year": year + latency,
                "latency": latency,
                "policy": policy,
                "decision_event_id": decision.event_id,
            })

    def _deliver_due(self, year: int) -> None:
        pending = []
        for delivery in self._state["pending_deliveries"]:
            if delivery["due_year"] > year:
                pending.append(delivery)
                continue
            target = delivery["target"]
            policy = parse_policy_decision(delivery["policy"])
            port, _mechanism, _input = POLICY_CONTRACTS[target]
            delivered = DeliveredValue(
                channel=ChannelKind.CONSTRAINT,
                artifact_type="government-policy",
                payload=policy,
                actor_ids=(),
                artifact_ids=(),
                lineage_event_ids=(delivery["decision_event_id"],),
                source_mechanism=self.config.mechanism_id,
                source_port=port,
                emitted_period=policy["issued_period"],
                available_period=year,
            )
            try:
                active = resolve_active_policy(
                    (delivered,),
                    target=target,
                    active=self._state["active_policies"].get(target),
                    system_fingerprint=self.config.system_fingerprint,
                )
            except GraphRuntimeError as error:
                raise NativeGovernmentError(str(error)) from error
            self._state["active_policies"][target] = active
            self._append_event(
                year=year,
                phase=0,
                event_type=APPLICATION_EVENT_TYPE,
                payload={
                    "policy_id": policy["policy_id"],
                    "policy_version": policy["policy_version"],
                    "target_family": target,
                    "affected_mechanism": POLICY_CONTRACTS[target][1],
                    "directive": deepcopy(policy["directives"][target]),
                    "issued_year": policy["issued_period"],
                    "applied_year": year,
                    "latency": delivery["latency"],
                    "system_fingerprint": self.config.system_fingerprint,
                },
                provenance={
                    "namespace": "native.government",
                    "native_mechanism": POLICY_CONTRACTS[target][1],
                    "source_event_ids": [delivery["decision_event_id"]],
                },
            )
        self._state["pending_deliveries"] = pending

    def _append_event(
        self,
        *,
        year: int,
        phase: int,
        event_type: str,
        payload: Mapping[str, Any],
        provenance: Mapping[str, Any],
    ) -> EventEnvelope:
        event = EventEnvelope.create(
            sequence=len(self._state["events"]),
            year=year,
            phase=phase,
            event_type=event_type,
            payload=payload,
            provenance=provenance,
        )
        self._state["events"].append(event.to_dict())
        return event

    def _restore(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        if not raw:
            return {
                "schema_version": NATIVE_GOVERNMENT_STATE,
                "config": self.config.to_dict(),
                "config_fingerprint": self.config.fingerprint,
                "last_started_year": 0,
                "last_completed_year": 0,
                "production_state": {},
                "active_policies": {},
                "pending_deliveries": [],
                "events": [],
            }
        restored = deepcopy(dict(raw))
        self._validate_state(restored)
        return restored

    def _validate_state(self, state: Mapping[str, Any]) -> None:
        required = {
            "schema_version", "config", "config_fingerprint", "last_started_year",
            "last_completed_year", "production_state", "active_policies",
            "pending_deliveries", "events",
        }
        if set(state) != required or state.get("schema_version") != NATIVE_GOVERNMENT_STATE:
            raise NativeGovernmentError("native government checkpoint schema changed")
        if state["config"] != self.config.to_dict():
            raise NativeGovernmentError("native government checkpoint config changed")
        if state["config_fingerprint"] != self.config.fingerprint:
            raise NativeGovernmentError("native government config fingerprint mismatch")
        completed = state["last_completed_year"]
        if (
            type(completed) is not int
            or completed < 0
            or state["last_started_year"] != completed
        ):
            raise NativeGovernmentError("native government year cursor is invalid")
        events = state["events"]
        if not isinstance(events, list):
            raise NativeGovernmentError("native government events must be a list")
        parsed_events = [_event_from_dict(item) for item in events]
        if [event.sequence for event in parsed_events] != list(range(len(parsed_events))):
            raise NativeGovernmentError("native government event sequence is not contiguous")
        validate_native_government_events(
            parsed_events, system_fingerprint=self.config.system_fingerprint
        )
        observation_events = [
            event for event in parsed_events if event.event_type == OBSERVATION_EVENT_TYPE
        ]
        decision_events = [
            event for event in parsed_events if event.event_type == DECISION_EVENT_TYPE
        ]
        application_events = [
            event for event in parsed_events if event.event_type == APPLICATION_EVENT_TYPE
        ]
        if any(
            event.payload["source_family"] not in self.config.observation_sources
            for event in observation_events
        ):
            raise NativeGovernmentError("event history contains an undeclared observation")
        if any(
            event.payload["policy"]["directives"]
            != _json_value(self.config.directives)
            for event in decision_events
        ):
            raise NativeGovernmentError("event history contains changed directives")
        production = state["production_state"]
        if not isinstance(production, Mapping):
            raise NativeGovernmentError("production government state must be a mapping")
        if production:
            if production.get("schema_version") != STATE_SCHEMA_VERSION:
                raise NativeGovernmentError("production government state schema changed")
            if production.get("observed_event_ids") != [
                event.event_id for event in observation_events
            ]:
                raise NativeGovernmentError(
                    "production government observations differ from event history"
                )
            decision_policy_ids = [
                event.payload["policy"]["policy_id"] for event in decision_events
            ]
            if production.get("issued_policy_ids") != decision_policy_ids:
                raise NativeGovernmentError(
                    "production government decisions differ from event history"
                )
            if production.get("observed_value_count") != len(observation_events):
                raise NativeGovernmentError(
                    "production government observation count differs from event history"
                )
            if production.get("next_policy_version") != len(decision_events) + 1:
                raise NativeGovernmentError(
                    "production government version cursor differs from event history"
                )
            expected_last_fingerprint = (
                _fingerprint(decision_events[-1].payload["policy"])
                if decision_events else None
            )
            if production.get("last_policy_fingerprint") != expected_last_fingerprint:
                raise NativeGovernmentError(
                    "production government policy fingerprint differs from history"
                )
            stable = self._invoke_production(max(completed, 1), {}, production)
            if stable.outputs or stable.events or stable.next_state != production:
                raise NativeGovernmentError(
                    "production government checkpoint is not a stable restored state"
                )
        elif observation_events or decision_events:
            raise NativeGovernmentError("production government state is missing")
        active = state["active_policies"]
        if not isinstance(active, Mapping) or not set(active) <= set(POLICY_CONTRACTS):
            raise NativeGovernmentError("active government policies are invalid")
        for target, value in active.items():
            try:
                if resolve_active_policy((), target=target, active=value) != value:
                    raise NativeGovernmentError("active government policy is not canonical")
            except GraphRuntimeError as error:
                raise NativeGovernmentError(str(error)) from error
            applied_for_target = [
                event for event in application_events
                if event.payload["target_family"] == target
            ]
            if not applied_for_target:
                raise NativeGovernmentError("active policy lacks an application event")
            latest = applied_for_target[-1].payload
            if (
                value["policy_id"] != latest["policy_id"]
                or value["policy_version"] != latest["policy_version"]
                or value["directive"] != latest["directive"]
            ):
                raise NativeGovernmentError(
                    "active policy differs from latest application event"
                )
        latencies = self.config.latency_by_target
        if any(
            event.payload["target_family"] not in latencies
            or event.payload["latency"]
            != latencies[event.payload["target_family"]]
            for event in application_events
        ):
            raise NativeGovernmentError("applied policy differs from declared edge latency")
        decisions_by_id = {event.event_id: event for event in decision_events}
        pending = state["pending_deliveries"]
        if not isinstance(pending, list):
            raise NativeGovernmentError("pending government deliveries must be a list")
        seen_pending: set[tuple[str, str]] = set()
        for delivery in pending:
            if not isinstance(delivery, Mapping) or set(delivery) != {
                "target", "due_year", "latency", "policy", "decision_event_id"
            }:
                raise NativeGovernmentError("pending government delivery is invalid")
            target = delivery["target"]
            policy = parse_policy_decision(delivery["policy"])
            decision = decisions_by_id.get(delivery["decision_event_id"])
            identity = (target, policy["policy_id"])
            if (
                target not in latencies
                or identity in seen_pending
                or delivery["latency"] != latencies[target]
                or delivery["due_year"] != policy["issued_period"] + latencies[target]
                or delivery["due_year"] <= completed
                or decision is None
                or decision.payload["policy"] != policy
            ):
                raise NativeGovernmentError("pending government lineage/latency is invalid")
            seen_pending.add(identity)
        _strict_json(state, "native government checkpoint")


def validate_native_government_events(
    events: Sequence[EventEnvelope],
    *,
    system_fingerprint: str,
) -> None:
    """Validate typed policy action -> affected mechanism causal lineage."""

    seen: set[str] = set()
    decisions: dict[str, EventEnvelope] = {}
    for event in events:
        if event.event_type not in {
            OBSERVATION_EVENT_TYPE, DECISION_EVENT_TYPE, APPLICATION_EVENT_TYPE
        }:
            raise NativeGovernmentError("event is outside native government namespace")
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
            raise NativeGovernmentError("native government event identity mismatch")
        if event.provenance.get("namespace") != "native.government":
            raise NativeGovernmentError("native government namespace is missing")
        if event.actor_ids or event.artifact_ids:
            raise NativeGovernmentError("native government control event has data ids")
        if event.event_type == OBSERVATION_EVENT_TYPE:
            source = event.payload.get("source_family")
            if (
                source not in OBSERVATION_CONTRACTS
                or event.payload.get("system_fingerprint") != system_fingerprint
                or not isinstance(event.payload.get("summary"), Mapping)
                or event.provenance.get("native_mechanism")
                != OBSERVATION_CONTRACTS[source][0]
            ):
                raise NativeGovernmentError("government observation event is invalid")
        elif event.event_type == DECISION_EVENT_TYPE:
            try:
                policy = parse_policy_decision(event.payload.get("policy"))
            except GraphRuntimeError as error:
                raise NativeGovernmentError(str(error)) from error
            sources = event.provenance.get("source_event_ids")
            if (
                policy["system_fingerprint"] != system_fingerprint
                or sources != policy["observed_event_ids"]
                or not set(sources) <= seen
                or event.year != policy["issued_period"]
                or event.provenance.get("native_mechanism") != policy["issuer_id"]
            ):
                raise NativeGovernmentError("government decision lineage is invalid")
            decisions[policy["policy_id"]] = event
        else:
            target = event.payload.get("target_family")
            policy_id = event.payload.get("policy_id")
            decision = decisions.get(policy_id)
            sources = event.provenance.get("source_event_ids")
            issued = event.payload.get("issued_year")
            applied = event.payload.get("applied_year")
            latency = event.payload.get("latency")
            if (
                target not in POLICY_CONTRACTS
                or decision is None
                or sources != [decision.event_id]
                or decision.event_id not in seen
                or event.payload.get("system_fingerprint") != system_fingerprint
                or event.payload.get("affected_mechanism") != POLICY_CONTRACTS[target][1]
                or event.provenance.get("native_mechanism") != POLICY_CONTRACTS[target][1]
                or type(issued) is not int
                or type(applied) is not int
                or type(latency) is not int
                or applied - issued != latency
                or event.year != applied
            ):
                raise NativeGovernmentError("government policy application lineage is invalid")
            policy = decision.payload["policy"]
            if (
                event.payload.get("policy_version") != policy["policy_version"]
                or event.payload.get("directive") != policy["directives"][target]
            ):
                raise NativeGovernmentError("government applied directive is inconsistent")
        seen.add(event.event_id)


def _event_from_dict(value: Mapping[str, Any]) -> EventEnvelope:
    required = {
        "schema_version", "event_id", "sequence", "year", "phase", "event_type",
        "actor_ids", "artifact_ids", "payload", "provenance",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise NativeGovernmentError("canonical government event fields are invalid")
    if (
        value["schema_version"] != SCHEMA_VERSION
        or not isinstance(value["event_id"], str)
        or type(value["sequence"]) is not int
        or type(value["year"]) is not int
        or type(value["phase"]) is not int
        or value["sequence"] < 0
        or value["year"] < 0
        or value["phase"] < 0
        or not isinstance(value["event_type"], str)
        or not isinstance(value["actor_ids"], list)
        or not isinstance(value["artifact_ids"], list)
        or not isinstance(value["payload"], Mapping)
        or not isinstance(value["provenance"], Mapping)
    ):
        raise NativeGovernmentError("canonical government event value types are invalid")
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


def _parse_csv(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, str):
        raise NativeGovernmentError(f"{label} must be comma-separated text")
    if not value:
        return ()
    result = tuple(value.split(","))
    if any(not item for item in result) or len(result) != len(set(result)):
        raise NativeGovernmentError(f"{label} contains empty or duplicate values")
    return result


def _parse_policy_edges(value: Any) -> tuple[tuple[str, int], ...]:
    records = _parse_csv(value, "government policy edges")
    parsed = []
    for record in records:
        target, separator, latency_text = record.partition(":")
        if not separator:
            raise NativeGovernmentError("government policy edge must be target:latency")
        try:
            latency = int(latency_text)
        except ValueError as error:
            raise NativeGovernmentError("government policy latency must be an integer") from error
        parsed.append((target, latency))
    return tuple(parsed)


def _policy_latency_records(value: Any) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, list):
        raise NativeGovernmentError("government policy latencies must be a list")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping) or set(item) != {"target", "latency"}:
            raise NativeGovernmentError(
                f"government policy latency record {index} is invalid"
            )
        result.append((item["target"], item["latency"]))
    return tuple(result)


def _string_sequence(value: Any, label: str) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item for item in value)
        or len(value) != len(set(value))
    ):
        raise NativeGovernmentError(f"government {label} must be unique strings")
    return tuple(value)


def _json_value(value: Any) -> Any:
    return json.loads(_canonical_json(value))


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _strict_json(value: Any, label: str) -> None:
    try:
        _canonical_json(value)
    except (TypeError, ValueError) as error:
        raise NativeGovernmentError(f"{label} is not strict JSON") from error
