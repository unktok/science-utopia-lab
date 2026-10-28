"""Stateful government policy mechanisms and fail-closed policy contracts."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from typing import Any, Mapping

from utopia.system.runtime import (
    DeliveredValue,
    GraphRuntimeError,
    MechanismContext,
    MechanismEvent,
    MechanismRegistry,
    MechanismResult,
    MechanismValue,
)


EVENT_RESPONSIVE_GOVERNMENT = "production.governance.event-responsive-policy-v1"
THRESHOLD_GOVERNMENT = "production.governance.threshold-policy-v1"
POLICY_SCHEMA_VERSION = "scienceutopia.government-policy.v1"
STATE_SCHEMA_VERSION = "scienceutopia.government-state.v1"

_TARGET_PORTS = {
    "evaluation": "evaluation_policies",
    "funding": "funding_policies",
    "publication": "publication_policies",
}


def register_government_mechanisms(registry: MechanismRegistry) -> None:
    registry.register(
        EVENT_RESPONSIVE_GOVERNMENT, 1, event_responsive_government
    )
    registry.register(THRESHOLD_GOVERNMENT, 1, threshold_government)


def event_responsive_government(context: MechanismContext) -> MechanismResult:
    """Issue configured fixture directives whenever new system events arrive."""

    return _government_policy(context, mode="event-responsive")


def threshold_government(context: MechanismContext) -> MechanismResult:
    """Issue configured fixture directives after observation-count thresholds."""

    return _government_policy(context, mode="threshold")


def parse_policy_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and clone one exact v1 government policy envelope."""

    if not isinstance(value, Mapping):
        raise GraphRuntimeError("government policy must be a mapping")
    required = {
        "schema_version",
        "policy_id",
        "policy_version",
        "issuer_id",
        "system_fingerprint",
        "issued_period",
        "observed_event_ids",
        "directives",
    }
    if set(value) != required:
        raise GraphRuntimeError("government policy fields do not match v1 schema")
    if value.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported government policy schema")
    for key in ("policy_id", "issuer_id", "system_fingerprint"):
        if not isinstance(value[key], str) or not value[key]:
            raise GraphRuntimeError(f"government policy {key} must be non-empty")
    fingerprint = value["system_fingerprint"]
    if len(fingerprint) != 64 or any(
        character not in "0123456789abcdef" for character in fingerprint
    ):
        raise GraphRuntimeError("government policy system_fingerprint is not sha256")
    for key in ("policy_version", "issued_period"):
        if (
            isinstance(value[key], bool)
            or not isinstance(value[key], int)
            or value[key] < 0
        ):
            raise GraphRuntimeError(
                f"government policy {key} must be a non-negative integer"
            )
    if value["policy_version"] < 1:
        raise GraphRuntimeError("government policy_version must be positive")
    event_ids = value["observed_event_ids"]
    if (
        not isinstance(event_ids, list)
        or not event_ids
        or any(not isinstance(item, str) or not item for item in event_ids)
        or len(event_ids) != len(set(event_ids))
    ):
        raise GraphRuntimeError(
            "government policy observed_event_ids must be unique non-empty strings"
        )
    directives = value["directives"]
    if (
        not isinstance(directives, Mapping)
        or not directives
        or not set(directives) <= set(_TARGET_PORTS)
    ):
        raise GraphRuntimeError("government policy directives have unknown targets")
    normalized: dict[str, dict[str, Any]] = {}
    for target, directive in directives.items():
        normalized[target] = _parse_directive(target, directive)
    result = deepcopy(dict(value))
    result["directives"] = normalized
    _strict_json(result, "government policy")
    return result


def resolve_active_policy(
    values: tuple[DeliveredValue, ...],
    *,
    target: str,
    active: Mapping[str, Any] | None,
    system_fingerprint: str | None = None,
) -> dict[str, Any] | None:
    """Resolve delivered policies monotonically or fail on ambiguity/staleness."""

    current = _parse_active_policy(active, target) if active is not None else None
    if not values:
        return current
    parsed = [parse_policy_decision(value.payload) for value in values]
    for delivered, policy in zip(values, parsed):
        if target not in policy["directives"]:
            raise GraphRuntimeError(
                f"government policy delivered to {target} lacks its directive"
            )
        if (
            system_fingerprint is not None
            and policy["system_fingerprint"] != system_fingerprint
        ):
            raise GraphRuntimeError("government policy belongs to a different system")
        if policy["issuer_id"] != delivered.source_mechanism:
            raise GraphRuntimeError("government policy issuer does not match delivery source")
        if policy["issued_period"] != delivered.emitted_period:
            raise GraphRuntimeError("government policy period does not match delivery")
    issuers = {policy["issuer_id"] for policy in parsed}
    if current is not None:
        issuers.add(current["issuer_id"])
    if len(issuers) != 1:
        raise GraphRuntimeError("government policy has ambiguous multiple issuers")
    versions = [policy["policy_version"] for policy in parsed]
    if len(versions) != len(set(versions)):
        raise GraphRuntimeError("government policy versions are duplicated")
    if current is not None and min(versions) <= current["policy_version"]:
        raise GraphRuntimeError("government policy version is stale or replayed")
    selected = max(parsed, key=lambda policy: policy["policy_version"])
    return {
        "policy_id": selected["policy_id"],
        "policy_version": selected["policy_version"],
        "issuer_id": selected["issuer_id"],
        "directive": deepcopy(selected["directives"][target]),
    }


def _government_policy(
    context: MechanismContext,
    *,
    mode: str,
) -> MechanismResult:
    state = _restore_state(context.state, context.mechanism.parameters, mode)
    observed_values = tuple(
        value
        for port_id in ("decisions", "allocations", "publications")
        for value in context.inputs.get(port_id, ())
    )
    if not observed_values:
        return MechanismResult(next_state=state)
    new_event_ids = _observation_event_ids(observed_values, state)
    counts = {
        port_id: len(context.inputs.get(port_id, ()))
        for port_id in ("decisions", "allocations", "publications")
    }
    state["observed_value_count"] += len(observed_values)
    state["observed_event_ids"].extend(new_event_ids)
    state["last_observation_counts"] = counts

    should_issue = mode == "event-responsive"
    if mode == "threshold" and state["observed_value_count"] >= state["next_threshold"]:
        should_issue = True
        state["next_threshold"] += state["repeat_interval"]
    if not should_issue:
        return MechanismResult(next_state=state)

    policy = _build_policy(context, state, new_event_ids)
    outputs = {
        _TARGET_PORTS[target]: (MechanismValue(policy),)
        for target in policy["directives"]
    }
    state["issued_policy_ids"].append(policy["policy_id"])
    state["next_policy_version"] += 1
    state["last_policy_fingerprint"] = _fingerprint(policy)
    return MechanismResult(
        outputs=outputs,
        events=(
            MechanismEvent(
                "government.policy_decided",
                payload={
                    "policy_id": policy["policy_id"],
                    "policy_version": policy["policy_version"],
                    "observed_value_count": state["observed_value_count"],
                    "directives": deepcopy(policy["directives"]),
                },
                provenance={
                    "production_adapter": context.mechanism.implementation,
                    "policy_schema": POLICY_SCHEMA_VERSION,
                    "decision_mode": mode,
                },
            ),
        ),
        next_state=state,
    )


def _build_policy(
    context: MechanismContext,
    state: Mapping[str, Any],
    event_ids: tuple[str, ...],
) -> dict[str, Any]:
    directives = context.mechanism.parameters.get("directives")
    body = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "policy_id": "pending",
        "policy_version": state["next_policy_version"],
        "issuer_id": context.mechanism.mechanism_id,
        "system_fingerprint": context.system_fingerprint,
        "issued_period": context.period,
        "observed_event_ids": list(event_ids),
        "directives": deepcopy(directives),
    }
    digest = _fingerprint({key: value for key, value in body.items() if key != "policy_id"})
    body["policy_id"] = (
        f"{context.mechanism.mechanism_id}"
        f"-v{state['next_policy_version']}-{digest[:12]}"
    )
    return parse_policy_decision(body)


def _restore_state(
    raw: Mapping[str, Any],
    parameters: Mapping[str, Any],
    mode: str,
) -> dict[str, Any]:
    minimum = _positive_int(parameters.get("minimum_observations", 1), "minimum_observations")
    repeat = _positive_int(parameters.get("repeat_interval", minimum), "repeat_interval")
    if not raw:
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "mode": mode,
            "observed_value_count": 0,
            "observed_event_ids": [],
            "issued_policy_ids": [],
            "next_policy_version": 1,
            "next_threshold": minimum,
            "repeat_interval": repeat,
            "last_observation_counts": {
                "decisions": 0,
                "allocations": 0,
                "publications": 0,
            },
            "last_policy_fingerprint": None,
        }
    required = {
        "schema_version",
        "mode",
        "observed_value_count",
        "observed_event_ids",
        "issued_policy_ids",
        "next_policy_version",
        "next_threshold",
        "repeat_interval",
        "last_observation_counts",
        "last_policy_fingerprint",
    }
    if set(raw) != required or raw.get("schema_version") != STATE_SCHEMA_VERSION:
        raise GraphRuntimeError("unsupported government mechanism state")
    if raw["mode"] != mode:
        raise GraphRuntimeError("government state mode does not match implementation")
    for key in (
        "observed_value_count",
        "next_policy_version",
        "next_threshold",
        "repeat_interval",
    ):
        if isinstance(raw[key], bool) or not isinstance(raw[key], int) or raw[key] < 0:
            raise GraphRuntimeError(f"invalid government state {key}")
    if raw["next_policy_version"] < 1 or raw["next_threshold"] < 1 or raw["repeat_interval"] < 1:
        raise GraphRuntimeError("invalid positive government state cursor")
    event_ids = raw["observed_event_ids"]
    policy_ids = raw["issued_policy_ids"]
    if (
        not isinstance(event_ids, list)
        or any(not isinstance(item, str) or not item for item in event_ids)
        or len(event_ids) != len(set(event_ids))
        or not isinstance(policy_ids, list)
        or any(not isinstance(item, str) or not item for item in policy_ids)
        or len(policy_ids) != len(set(policy_ids))
    ):
        raise GraphRuntimeError("invalid government state ids")
    counts = raw["last_observation_counts"]
    if not isinstance(counts, Mapping) or set(counts) != {
        "decisions",
        "allocations",
        "publications",
    }:
        raise GraphRuntimeError("invalid government observation counts")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in counts.values()
    ):
        raise GraphRuntimeError("invalid government observation count value")
    fingerprint = raw["last_policy_fingerprint"]
    if fingerprint is not None and (not isinstance(fingerprint, str) or len(fingerprint) != 64):
        raise GraphRuntimeError("invalid government policy fingerprint")
    if raw["repeat_interval"] != repeat:
        raise GraphRuntimeError("government repeat_interval changed across checkpoint")
    return deepcopy(dict(raw))


def _observation_event_ids(
    values: tuple[DeliveredValue, ...],
    state: Mapping[str, Any],
) -> tuple[str, ...]:
    event_ids = tuple(
        dict.fromkeys(
            event_id
            for value in values
            for event_id in value.lineage_event_ids
        )
    )
    if not event_ids:
        raise GraphRuntimeError("government observations require canonical event lineage")
    prior = set(state["observed_event_ids"])
    if any(event_id in prior for event_id in event_ids):
        raise GraphRuntimeError("government observed an already-consumed system event")
    return event_ids


def _parse_active_policy(
    value: Mapping[str, Any],
    target: str,
) -> dict[str, Any]:
    required = {"policy_id", "policy_version", "issuer_id", "directive"}
    if not isinstance(value, Mapping) or set(value) != required:
        raise GraphRuntimeError("active government policy state is invalid")
    for key in ("policy_id", "issuer_id"):
        if not isinstance(value[key], str) or not value[key]:
            raise GraphRuntimeError("active government policy identity is invalid")
    version = value["policy_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise GraphRuntimeError("active government policy version is invalid")
    return {
        "policy_id": value["policy_id"],
        "policy_version": version,
        "issuer_id": value["issuer_id"],
        "directive": _parse_directive(target, value["directive"]),
    }


def _parse_directive(target: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not value:
        raise GraphRuntimeError(f"government {target} directive must be non-empty")
    if target == "evaluation":
        if set(value) != {"acceptance_rate"}:
            raise GraphRuntimeError("government evaluation directive fields are invalid")
        rate = _finite_number(value["acceptance_rate"], "evaluation acceptance_rate")
        if not 0 <= rate <= 1:
            raise GraphRuntimeError("government evaluation acceptance_rate is out of range")
        return {"acceptance_rate": rate}
    if target == "funding":
        allowed = {"award_amount_multiplier", "award_slots"}
        if not set(value) <= allowed or not value:
            raise GraphRuntimeError("government funding directive fields are invalid")
        result: dict[str, Any] = {}
        if "award_amount_multiplier" in value:
            multiplier = _finite_number(
                value["award_amount_multiplier"], "funding award_amount_multiplier"
            )
            if multiplier <= 0:
                raise GraphRuntimeError("government funding multiplier must be positive")
            result["award_amount_multiplier"] = multiplier
        if "award_slots" in value:
            result["award_slots"] = _positive_int(value["award_slots"], "award_slots")
        return result
    if target == "publication":
        if set(value) != {"recording_enabled"} or type(value["recording_enabled"]) is not bool:
            raise GraphRuntimeError("government publication directive fields are invalid")
        return {"recording_enabled": value["recording_enabled"]}
    raise GraphRuntimeError(f"unknown government directive target {target!r}")


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise GraphRuntimeError(f"government {label} must be a positive integer")
    return value


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GraphRuntimeError(f"government {label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise GraphRuntimeError(f"government {label} must be finite")
    return result


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _strict_json(value: Any, label: str) -> None:
    try:
        json.dumps(value, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise GraphRuntimeError(f"{label} is not strict JSON: {exc}") from exc
