"""Report-only semantic instrumentation for epistemic shadow diagnostics.

This vertical slice validates typed claim, evidence, verification, replication,
and correction events.  It deliberately has no LossSpec adapter and no
candidate-ranking API: outputs are shadow diagnostics only.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Iterable, Mapping


BUNDLE_SCHEMA = "scienceutopia.semantic-instrumentation-bundle.v1"
REPORT_SCHEMA = "scienceutopia.semantic-instrumentation-shadow-report.v1"
GROUND_TRUTH_SCHEMA = "scienceutopia.semantic-ground-truth.v1"
EVENT_SCHEMAS = {
    "claim": "scienceutopia.semantic-claim-event.v1",
    "evidence": "scienceutopia.semantic-evidence-event.v1",
    "verification": "scienceutopia.semantic-verification-event.v1",
    "replication": "scienceutopia.semantic-replication-event.v1",
    "correction": "scienceutopia.semantic-correction-event.v1",
}
EVENT_TYPES = {
    "claim.created": "claim",
    "claim.revised": "claim",
    "claim.withdrawn": "claim",
    "evidence.attached": "evidence",
    "evidence.invalidated": "evidence",
    "verification.completed": "verification",
    "replication.attempted": "replication",
    "replication.resolved": "replication",
    "correction.issued": "correction",
    "correction.propagated": "correction",
}
CLASSIFICATIONS = {
    "synthetic_ground_truth",
    "synthetic_gaming_counterexample",
    "experimental_shadow",
}
MISSING_REASONS = {
    "not_observed",
    "measurement_failed",
    "redacted",
    "not_applicable",
    "unknown",
}
LINEAGE_FIELDS = ("method", "data", "model", "evaluator", "organization")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _fields(value: Mapping[str, Any], expected: set[str], context: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{context} fields do not match the v1 contract")


def _string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} must be a non-empty string")
    return value


def _integer(value: Any, context: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{context} must be an integer >= {minimum}")
    return value


def _probability(value: Any, context: str) -> float:
    if type(value) not in {int, float} or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{context} must be a finite probability")
    return float(value)


def _measurement(
    value: Any,
    context: str,
    *,
    kind: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be an observed/missing measurement")
    status = value.get("status")
    if status == "missing":
        _fields(value, {"status", "reason", "detail"}, context)
        if value["reason"] not in MISSING_REASONS:
            raise ValueError(f"{context} has an unsupported missingness reason")
        _string(value["detail"], f"{context}.detail")
        return deepcopy(dict(value))
    if status != "observed":
        raise ValueError(f"{context}.status must be observed or missing")
    _fields(value, {"status", "value"}, context)
    observed = value["value"]
    if kind == "probability":
        observed = _probability(observed, f"{context}.value")
    elif kind == "string":
        observed = _string(observed, f"{context}.value")
    elif kind == "reference":
        observed = _claim_ref(observed, f"{context}.value")
    else:
        raise AssertionError(f"unknown measurement kind {kind}")
    return {"status": "observed", "value": observed}


def _claim_ref(value: Any, context: str) -> str:
    value = _string(value, context)
    if "@" not in value:
        raise ValueError(f"{context} must have claim-id@version form")
    claim_id, version = value.rsplit("@", 1)
    _string(claim_id, f"{context} claim id")
    try:
        parsed = int(version)
    except ValueError as error:
        raise ValueError(f"{context} version must be an integer") from error
    if parsed < 1 or str(parsed) != version:
        raise ValueError(f"{context} version must be a positive canonical integer")
    return value


def _lineage(value: Any, context: str) -> dict[str, Any]:
    _fields(value, set(LINEAGE_FIELDS), context)
    return {
        field: _measurement(value[field], f"{context}.{field}", kind="string")
        for field in LINEAGE_FIELDS
    }


def _references(value: Any, context: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    result = [_claim_ref(item, f"{context} item") for item in value]
    if len(result) != len(set(result)):
        raise ValueError(f"{context} must not contain duplicates")
    return result


def _string_list(value: Any, context: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{context} must be {'a non-empty ' if nonempty else 'a '}list")
    result = [_string(item, f"{context} item") for item in value]
    if len(result) != len(set(result)):
        raise ValueError(f"{context} must not contain duplicates")
    return result


def _parse_claim_payload(event_type: str, payload: Any) -> dict[str, Any]:
    if event_type == "claim.withdrawn":
        _fields(payload, {"claim_ref", "reason"}, event_type)
        return {
            "claim_ref": _claim_ref(payload["claim_ref"], "claim.withdrawn claim_ref"),
            "reason": _string(payload["reason"], "claim.withdrawn reason"),
        }
    required = {
        "claim_id",
        "claim_version",
        "parent_version",
        "truth_target_id",
        "asserted_value",
        "claim_type",
        "scope",
        "prior_probability",
        "dependencies",
    }
    _fields(payload, required, event_type)
    version = _integer(payload["claim_version"], f"{event_type} claim_version", minimum=1)
    parent = payload["parent_version"]
    if parent is not None:
        parent = _integer(parent, f"{event_type} parent_version", minimum=1)
    if type(payload["asserted_value"]) is not bool:
        raise ValueError(f"{event_type} asserted_value must be boolean")
    return {
        "claim_id": _string(payload["claim_id"], f"{event_type} claim_id"),
        "claim_version": version,
        "parent_version": parent,
        "truth_target_id": _measurement(
            payload["truth_target_id"], f"{event_type}.truth_target_id", kind="string"
        ),
        "asserted_value": payload["asserted_value"],
        "claim_type": _string(payload["claim_type"], f"{event_type} claim_type"),
        "scope": _string(payload["scope"], f"{event_type} scope"),
        "prior_probability": _measurement(
            payload["prior_probability"],
            f"{event_type}.prior_probability",
            kind="probability",
        ),
        "dependencies": _references(payload["dependencies"], f"{event_type} dependencies"),
    }


def _parse_evidence_payload(event_type: str, payload: Any) -> dict[str, Any]:
    if event_type == "evidence.invalidated":
        _fields(payload, {"evidence_id", "reason", "invalidating_event_ids"}, event_type)
        return {
            "evidence_id": _string(payload["evidence_id"], f"{event_type} evidence_id"),
            "reason": _string(payload["reason"], f"{event_type} reason"),
            "invalidating_event_ids": _string_list(
                payload["invalidating_event_ids"],
                f"{event_type} invalidating_event_ids",
                nonempty=True,
            ),
        }
    _fields(payload, {"evidence_id", "claim_ref", "result", "strength", "lineage"}, event_type)
    if payload["result"] not in {"supports", "challenges", "null"}:
        raise ValueError("evidence.attached result is unsupported")
    strength = payload["strength"]
    parsed_strength = _measurement(strength, "evidence.attached.strength", kind="probability")
    return {
        "evidence_id": _string(payload["evidence_id"], "evidence.attached evidence_id"),
        "claim_ref": _claim_ref(payload["claim_ref"], "evidence.attached claim_ref"),
        "result": payload["result"],
        "strength": parsed_strength,
        "lineage": _lineage(payload["lineage"], "evidence.attached.lineage"),
    }


def _parse_verification_payload(payload: Any) -> dict[str, Any]:
    required = {
        "verification_id",
        "claim_ref",
        "evidence_ids",
        "outcome",
        "posterior_probability",
        "independence_claimed",
        "lineage",
    }
    _fields(payload, required, "verification.completed")
    if payload["outcome"] not in {"supports", "challenges", "inconclusive"}:
        raise ValueError("verification outcome is unsupported")
    if type(payload["independence_claimed"]) is not bool:
        raise ValueError("verification independence_claimed must be boolean")
    return {
        "verification_id": _string(payload["verification_id"], "verification id"),
        "claim_ref": _claim_ref(payload["claim_ref"], "verification claim_ref"),
        "evidence_ids": _string_list(
            payload["evidence_ids"], "verification evidence_ids", nonempty=True
        ),
        "outcome": payload["outcome"],
        "posterior_probability": _measurement(
            payload["posterior_probability"],
            "verification.posterior_probability",
            kind="probability",
        ),
        "independence_claimed": payload["independence_claimed"],
        "lineage": _lineage(payload["lineage"], "verification.lineage"),
    }


def _parse_replication_payload(event_type: str, payload: Any) -> dict[str, Any]:
    if event_type == "replication.attempted":
        _fields(payload, {"replication_id", "claim_ref", "preregistered", "lineage"}, event_type)
        if type(payload["preregistered"]) is not bool:
            raise ValueError("replication preregistered must be boolean")
        return {
            "replication_id": _string(payload["replication_id"], "replication id"),
            "claim_ref": _claim_ref(payload["claim_ref"], "replication claim_ref"),
            "preregistered": payload["preregistered"],
            "lineage": _lineage(payload["lineage"], "replication.attempted.lineage"),
        }
    required = {
        "replication_id",
        "outcome",
        "posterior_probability",
        "independence_claimed",
        "lineage",
    }
    _fields(payload, required, event_type)
    if payload["outcome"] not in {
        "supports", "challenges", "inconclusive", "technical_failure",
    }:
        raise ValueError("replication outcome is unsupported")
    if type(payload["independence_claimed"]) is not bool:
        raise ValueError("replication independence_claimed must be boolean")
    return {
        "replication_id": _string(payload["replication_id"], "replication id"),
        "outcome": payload["outcome"],
        "posterior_probability": _measurement(
            payload["posterior_probability"],
            "replication.posterior_probability",
            kind="probability",
        ),
        "independence_claimed": payload["independence_claimed"],
        "lineage": _lineage(payload["lineage"], "replication.resolved.lineage"),
    }


def _parse_correction_payload(event_type: str, payload: Any) -> dict[str, Any]:
    if event_type == "correction.issued":
        required = {
            "correction_id",
            "target_claim_ref",
            "disposition",
            "invalidating_event_ids",
            "replacement_claim_ref",
        }
        _fields(payload, required, event_type)
        if payload["disposition"] not in {"revised", "withdrawn", "scope_narrowed"}:
            raise ValueError("correction disposition is unsupported")
        return {
            "correction_id": _string(payload["correction_id"], "correction id"),
            "target_claim_ref": _claim_ref(payload["target_claim_ref"], "correction target"),
            "disposition": payload["disposition"],
            "invalidating_event_ids": _string_list(
                payload["invalidating_event_ids"],
                "correction invalidating_event_ids",
                nonempty=True,
            ),
            "replacement_claim_ref": _measurement(
                payload["replacement_claim_ref"],
                "correction replacement_claim_ref",
                kind="reference",
            ),
        }
    required = {
        "correction_id",
        "dependent_claim_ref",
        "status",
        "replacement_dependency_ref",
    }
    _fields(payload, required, event_type)
    if payload["status"] not in {"updated", "withdrawn", "acknowledged"}:
        raise ValueError("correction propagation status is unsupported")
    return {
        "correction_id": _string(payload["correction_id"], "correction id"),
        "dependent_claim_ref": _claim_ref(payload["dependent_claim_ref"], "dependent claim"),
        "status": payload["status"],
        "replacement_dependency_ref": _measurement(
            payload["replacement_dependency_ref"],
            "correction replacement_dependency_ref",
            kind="reference",
        ),
    }


def _parse_event(value: Any, expected_sequence: int) -> dict[str, Any]:
    required = {
        "schema",
        "event_id",
        "sequence",
        "step",
        "event_type",
        "actor_id",
        "institution_id",
        "provenance",
        "payload",
    }
    _fields(value, required, "semantic event")
    event_type = value["event_type"]
    family = EVENT_TYPES.get(event_type)
    if family is None or value["schema"] != EVENT_SCHEMAS[family]:
        raise ValueError(f"unsupported semantic event contract for {event_type!r}")
    sequence = _integer(value["sequence"], "event sequence")
    if sequence != expected_sequence:
        raise ValueError(f"event sequence {sequence}, expected {expected_sequence}")
    provenance = value["provenance"]
    _fields(provenance, {"run_id", "producer", "source_event_ids"}, "event provenance")
    parsed_provenance = {
        "run_id": _string(provenance["run_id"], "event provenance run_id"),
        "producer": _string(provenance["producer"], "event provenance producer"),
        "source_event_ids": _string_list(
            provenance["source_event_ids"], "event provenance source_event_ids"
        ),
    }
    if family == "claim":
        payload = _parse_claim_payload(event_type, value["payload"])
    elif family == "evidence":
        payload = _parse_evidence_payload(event_type, value["payload"])
    elif family == "verification":
        payload = _parse_verification_payload(value["payload"])
    elif family == "replication":
        payload = _parse_replication_payload(event_type, value["payload"])
    else:
        payload = _parse_correction_payload(event_type, value["payload"])
    return {
        "schema": value["schema"],
        "event_id": _string(value["event_id"], "event_id"),
        "sequence": sequence,
        "step": _integer(value["step"], "event step"),
        "event_type": event_type,
        "actor_id": _string(value["actor_id"], "event actor_id"),
        "institution_id": _string(value["institution_id"], "event institution_id"),
        "provenance": parsed_provenance,
        "payload": payload,
    }


def _parse_ground_truth(value: Any, classification: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("ground_truth must be observed or missing")
    if value.get("status") == "missing":
        _fields(value, {"status", "reason", "detail"}, "ground_truth")
        if classification != "experimental_shadow":
            raise ValueError("synthetic fixtures require observed ground truth")
        if value["reason"] not in MISSING_REASONS:
            raise ValueError("ground_truth missingness reason is unsupported")
        _string(value["detail"], "ground_truth detail")
        return deepcopy(dict(value))
    required = {"status", "schema", "universe_id", "targets"}
    _fields(value, required, "ground_truth")
    if value.get("status") != "observed" or value.get("schema") != GROUND_TRUTH_SCHEMA:
        raise ValueError("ground_truth contract is unsupported")
    if classification == "experimental_shadow":
        raise ValueError("experimental shadow bundles may not embed synthetic ground truth")
    targets = value["targets"]
    if not isinstance(targets, list) or not targets:
        raise ValueError("ground_truth targets must be a non-empty list")
    parsed_targets = []
    for item in targets:
        _fields(item, {"truth_target_id", "truth", "difficulty", "importance"}, "truth target")
        if type(item["truth"]) is not bool:
            raise ValueError("truth target truth must be boolean")
        if item["difficulty"] not in {"easy", "medium", "hard"}:
            raise ValueError("truth target difficulty is unsupported")
        importance = item["importance"]
        if type(importance) not in {int, float} or not math.isfinite(importance) or importance <= 0:
            raise ValueError("truth target importance must be finite and positive")
        parsed_targets.append({
            "truth_target_id": _string(item["truth_target_id"], "truth target id"),
            "truth": item["truth"],
            "difficulty": item["difficulty"],
            "importance": float(importance),
        })
    ids = [item["truth_target_id"] for item in parsed_targets]
    if len(ids) != len(set(ids)):
        raise ValueError("ground_truth target ids must be unique")
    return {
        "status": "observed",
        "schema": GROUND_TRUTH_SCHEMA,
        "universe_id": _string(value["universe_id"], "ground_truth universe_id"),
        "targets": parsed_targets,
    }


def validate_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Validate exact event contracts plus temporal and semantic lineage."""

    required = {
        "schema",
        "bundle_id",
        "classification",
        "instrumentation_use",
        "run_id",
        "events",
        "ground_truth",
    }
    _fields(bundle, required, "semantic instrumentation bundle")
    if bundle.get("schema") != BUNDLE_SCHEMA:
        raise ValueError("semantic instrumentation bundle schema is unsupported")
    classification = bundle.get("classification")
    if classification not in CLASSIFICATIONS:
        raise ValueError("semantic instrumentation classification is unsupported")
    if bundle.get("instrumentation_use") != "report_only":
        raise ValueError("semantic instrumentation is report_only and cannot rank candidates")
    run_id = _string(bundle.get("run_id"), "bundle run_id")
    raw_events = bundle.get("events")
    if not isinstance(raw_events, list) or not raw_events:
        raise ValueError("semantic instrumentation events must be a non-empty list")
    events = [_parse_event(value, index) for index, value in enumerate(raw_events)]
    ground_truth = _parse_ground_truth(bundle.get("ground_truth"), classification)

    event_ids: set[str] = set()
    event_by_id: dict[str, dict[str, Any]] = {}
    claims: dict[str, dict[str, Any]] = {}
    latest: dict[str, int] = {}
    withdrawn: set[str] = set()
    evidence: dict[str, dict[str, Any]] = {}
    invalidated_evidence: set[str] = set()
    verifications: set[str] = set()
    replications: dict[str, dict[str, Any]] = {}
    corrections: dict[str, dict[str, Any]] = {}
    propagations: set[tuple[str, str]] = set()

    truth_ids = {
        item["truth_target_id"] for item in ground_truth.get("targets", [])
    }
    previous_step = -1
    for event in events:
        event_id = event["event_id"]
        if event_id in event_ids:
            raise ValueError(f"duplicate semantic event id {event_id}")
        if event["provenance"]["run_id"] != run_id:
            raise ValueError(f"event {event_id} belongs to another run")
        if event["step"] < previous_step:
            raise ValueError(f"event {event_id} moves semantic time backwards")
        previous_step = event["step"]
        unknown_sources = set(event["provenance"]["source_event_ids"]) - event_ids
        if unknown_sources:
            raise ValueError(f"event {event_id} has forward or unknown source events")
        event_ids.add(event_id)
        event_by_id[event_id] = event
        payload = event["payload"]
        event_type = event["event_type"]

        if event_type in {"claim.created", "claim.revised"}:
            claim_id = payload["claim_id"]
            version = payload["claim_version"]
            reference = f"{claim_id}@{version}"
            if reference in claims:
                raise ValueError(f"duplicate claim version {reference}")
            if event_type == "claim.created":
                if version != 1 or payload["parent_version"] is not None or claim_id in latest:
                    raise ValueError("claim.created must introduce version 1 without a parent")
            else:
                previous = latest.get(claim_id)
                if (
                    previous is None
                    or claim_id in withdrawn
                    or version != previous + 1
                    or payload["parent_version"] != previous
                ):
                    raise ValueError(f"claim revision is not contiguous for {reference}")
                parent_ref = f"{claim_id}@{previous}"
                if (
                    claims[parent_ref]["event_id"]
                    not in event["provenance"]["source_event_ids"]
                ):
                    raise ValueError("claim revision does not cite its parent event")
                parent_target = claims[parent_ref]["payload"]["truth_target_id"]
                revised_target = payload["truth_target_id"]
                if (
                    parent_target["status"] == "observed"
                    and revised_target["status"] == "observed"
                    and parent_target["value"] != revised_target["value"]
                ):
                    raise ValueError("claim revision cannot change its truth target")
            missing_dependencies = set(payload["dependencies"]) - set(claims)
            if missing_dependencies:
                raise ValueError(f"claim {reference} has unknown dependencies")
            dependency_sources = {
                claims[item]["event_id"] for item in payload["dependencies"]
            }
            if not dependency_sources <= set(event["provenance"]["source_event_ids"]):
                raise ValueError(f"claim {reference} provenance omits dependency events")
            target = payload["truth_target_id"]
            if target["status"] == "observed" and truth_ids and target["value"] not in truth_ids:
                raise ValueError(f"claim {reference} has an unknown truth target")
            claims[reference] = event
            latest[claim_id] = version
        elif event_type == "claim.withdrawn":
            reference = payload["claim_ref"]
            claim_id, version = reference.rsplit("@", 1)
            if reference not in claims or latest.get(claim_id) != int(version):
                raise ValueError("only the current claim version may be withdrawn")
            if claim_id in withdrawn:
                raise ValueError("claim is already withdrawn")
            if (
                claims[reference]["event_id"]
                not in event["provenance"]["source_event_ids"]
            ):
                raise ValueError("claim withdrawal does not cite the withdrawn claim event")
            withdrawn.add(claim_id)
        elif event_type == "evidence.attached":
            if payload["claim_ref"] not in claims:
                raise ValueError("evidence references an unknown claim")
            if payload["evidence_id"] in evidence:
                raise ValueError("evidence id is duplicated")
            if (
                claims[payload["claim_ref"]]["event_id"]
                not in event["provenance"]["source_event_ids"]
            ):
                raise ValueError("evidence does not cite its claim event")
            evidence[payload["evidence_id"]] = event
        elif event_type == "evidence.invalidated":
            evidence_id = payload["evidence_id"]
            if evidence_id not in evidence or evidence_id in invalidated_evidence:
                raise ValueError("evidence invalidation target is unknown or already invalidated")
            if not set(payload["invalidating_event_ids"]) <= event_ids - {event_id}:
                raise ValueError("evidence invalidation references a non-prior event")
            required_sources = {
                evidence[evidence_id]["event_id"], *payload["invalidating_event_ids"]
            }
            if not required_sources <= set(event["provenance"]["source_event_ids"]):
                raise ValueError("evidence invalidation provenance is incomplete")
            invalidated_evidence.add(evidence_id)
        elif event_type == "verification.completed":
            if payload["verification_id"] in verifications:
                raise ValueError("verification id is duplicated")
            if payload["claim_ref"] not in claims:
                raise ValueError("verification references an unknown claim")
            if any(item not in evidence for item in payload["evidence_ids"]):
                raise ValueError("verification references unknown evidence")
            if any(item in invalidated_evidence for item in payload["evidence_ids"]):
                raise ValueError("verification references already invalidated evidence")
            if any(
                evidence[item]["payload"]["claim_ref"] != payload["claim_ref"]
                for item in payload["evidence_ids"]
            ):
                raise ValueError("verification evidence belongs to another claim")
            required_sources = {
                evidence[item]["event_id"] for item in payload["evidence_ids"]
            }
            if not required_sources <= set(event["provenance"]["source_event_ids"]):
                raise ValueError("verification provenance omits evidence events")
            verifications.add(payload["verification_id"])
        elif event_type == "replication.attempted":
            replication_id = payload["replication_id"]
            if replication_id in replications or payload["claim_ref"] not in claims:
                raise ValueError("replication attempt is duplicate or has an unknown claim")
            if (
                claims[payload["claim_ref"]]["event_id"]
                not in event["provenance"]["source_event_ids"]
            ):
                raise ValueError("replication attempt does not cite its claim event")
            replications[replication_id] = {"attempt": event, "resolution": None}
        elif event_type == "replication.resolved":
            replication_id = payload["replication_id"]
            record = replications.get(replication_id)
            if record is None or record["resolution"] is not None:
                raise ValueError("replication resolution lacks one unresolved attempt")
            attempt_id = record["attempt"]["event_id"]
            if attempt_id not in event["provenance"]["source_event_ids"]:
                raise ValueError("replication resolution does not cite its attempt event")
            if _canonical_json(record["attempt"]["payload"]["lineage"]) != _canonical_json(
                payload["lineage"]
            ):
                raise ValueError("replication resolution lineage differs from its attempt")
            record["resolution"] = event
        elif event_type == "correction.issued":
            correction_id = payload["correction_id"]
            if correction_id in corrections or payload["target_claim_ref"] not in claims:
                raise ValueError("correction is duplicate or targets an unknown claim")
            invalidating = [event_by_id.get(item) for item in payload["invalidating_event_ids"]]
            if any(item is None for item in invalidating) or not any(
                item["event_type"] in {"verification.completed", "replication.resolved"}
                and item["payload"]["outcome"] == "challenges"
                for item in invalidating
            ):
                raise ValueError("correction requires a prior challenging semantic event")
            if not set(payload["invalidating_event_ids"]) <= set(
                event["provenance"]["source_event_ids"]
            ):
                raise ValueError("correction provenance omits invalidating events")
            replacement = payload["replacement_claim_ref"]
            if replacement["status"] == "observed" and replacement["value"] not in claims:
                raise ValueError("correction replacement claim is unknown")
            corrections[correction_id] = event
        else:
            correction_id = payload["correction_id"]
            dependent = payload["dependent_claim_ref"]
            correction = corrections.get(correction_id)
            if correction is None or dependent not in claims:
                raise ValueError("correction propagation has an unknown correction or dependent")
            if correction["event_id"] not in event["provenance"]["source_event_ids"]:
                raise ValueError("correction propagation does not cite the correction event")
            target = correction["payload"]["target_claim_ref"]
            if target not in claims[dependent]["payload"]["dependencies"]:
                raise ValueError("propagated correction is not in the dependent claim lineage")
            key = (correction_id, dependent)
            if key in propagations:
                raise ValueError("correction propagation is duplicated")
            replacement = payload["replacement_dependency_ref"]
            if replacement["status"] == "observed" and replacement["value"] not in claims:
                raise ValueError("replacement dependency is unknown")
            propagations.add(key)

    if ground_truth["status"] == "observed":
        observed_targets = {
            event["payload"]["truth_target_id"]["value"]
            for event in claims.values()
            if event["payload"]["truth_target_id"]["status"] == "observed"
        }
        if not observed_targets <= truth_ids:
            raise ValueError("claim targets fall outside the synthetic truth universe")

    return {
        "schema": BUNDLE_SCHEMA,
        "bundle_id": _string(bundle["bundle_id"], "bundle_id"),
        "classification": classification,
        "instrumentation_use": "report_only",
        "run_id": run_id,
        "events": events,
        "ground_truth": ground_truth,
    }


def _lineage_values(lineage: Mapping[str, Any]) -> dict[str, str] | None:
    if any(lineage[field]["status"] != "observed" for field in LINEAGE_FIELDS):
        return None
    return {field: lineage[field]["value"] for field in LINEAGE_FIELDS}


def _independence(
    lineage: Mapping[str, Any],
    baselines: Iterable[Mapping[str, Any]],
) -> tuple[str, list[str]]:
    candidate = _lineage_values(lineage)
    baseline_values = [_lineage_values(item) for item in baselines]
    if candidate is None or not baseline_values or any(item is None for item in baseline_values):
        return "unknown", []
    overlaps = sorted({
        field
        for baseline in baseline_values
        for field in LINEAGE_FIELDS
        if candidate[field] == baseline[field]
    })
    return ("correlated", overlaps) if overlaps else ("independent", [])


def _binary_entropy(probability: float) -> float:
    if probability in {0.0, 1.0}:
        return 0.0
    return -probability * math.log2(probability) - (1 - probability) * math.log2(1 - probability)


def _numeric_summary(values: Iterable[float]) -> dict[str, Any]:
    values = list(values)
    return {
        "count": len(values),
        "mean": statistics.fmean(values) if values else None,
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
        "values": values,
    }


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def _walk_missing(value: Any, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(value, Mapping):
        if value.get("status") == "missing" and set(value) == {"status", "reason", "detail"}:
            yield path, value["reason"]
            return
        for key, item in value.items():
            yield from _walk_missing(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_missing(item, f"{path}[{index}]")


def build_shadow_report(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Build non-ranking epistemic and robustness diagnostics."""

    bundle = validate_bundle(bundle)
    events = bundle["events"]
    event_counts = Counter(event["event_type"] for event in events)
    claim_events = [
        event for event in events
        if event["event_type"] in {"claim.created", "claim.revised"}
    ]
    created = [event for event in events if event["event_type"] == "claim.created"]
    claim_by_ref = {
        f"{event['payload']['claim_id']}@{event['payload']['claim_version']}": event
        for event in claim_events
    }
    evidence = {
        event["payload"]["evidence_id"]: event
        for event in events if event["event_type"] == "evidence.attached"
    }
    evidence_by_claim: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in evidence.values():
        evidence_by_claim[event["payload"]["claim_ref"]].append(event)
    verifications = [event for event in events if event["event_type"] == "verification.completed"]
    replication_attempts = {
        event["payload"]["replication_id"]: event
        for event in events if event["event_type"] == "replication.attempted"
    }
    replication_resolutions = {
        event["payload"]["replication_id"]: event
        for event in events if event["event_type"] == "replication.resolved"
    }
    corrections = {
        event["payload"]["correction_id"]: event
        for event in events if event["event_type"] == "correction.issued"
    }
    propagations = [event for event in events if event["event_type"] == "correction.propagated"]

    independence_records = []
    entropy_reductions = []
    brier_improvements = []
    truth = {
        item["truth_target_id"]: item
        for item in bundle["ground_truth"].get("targets", [])
    }
    truth_alignment: list[bool] = []

    def record_result(
        event: Mapping[str, Any],
        claim_ref: str,
        baseline_lineages: list[Mapping[str, Any]],
    ) -> None:
        payload = event["payload"]
        status, overlaps = _independence(payload["lineage"], baseline_lineages)
        independence_records.append({
            "event_id": event["event_id"],
            "event_type": event["event_type"],
            "claim_ref": claim_ref,
            "outcome": payload["outcome"],
            "independence_claimed": payload["independence_claimed"],
            "independence_status": status,
            "overlapping_dimensions": overlaps,
        })
        claim = claim_by_ref[claim_ref]["payload"]
        prior = claim["prior_probability"]
        posterior = payload["posterior_probability"]
        if (
            status == "independent"
            and payload["outcome"] in {"supports", "challenges"}
            and prior["status"] == "observed"
            and posterior["status"] == "observed"
        ):
            entropy_reductions.append(
                _binary_entropy(prior["value"]) - _binary_entropy(posterior["value"])
            )
            target = claim["truth_target_id"]
            if target["status"] == "observed" and target["value"] in truth:
                correct = claim["asserted_value"] == truth[target["value"]]["truth"]
                y = 1.0 if correct else 0.0
                brier_improvements.append(
                    (prior["value"] - y) ** 2 - (posterior["value"] - y) ** 2
                )
                expected = "supports" if correct else "challenges"
                if payload["outcome"] != "technical_failure":
                    truth_alignment.append(payload["outcome"] == expected)

    for event in verifications:
        claim_ref = event["payload"]["claim_ref"]
        baselines = [
            evidence[item]["payload"]["lineage"]
            for item in event["payload"]["evidence_ids"]
        ]
        record_result(event, claim_ref, baselines)
    for replication_id, event in replication_resolutions.items():
        attempt = replication_attempts[replication_id]
        claim_ref = attempt["payload"]["claim_ref"]
        baselines = [
            item["payload"]["lineage"]
            for item in evidence_by_claim.get(claim_ref, [])
        ]
        record_result(event, claim_ref, baselines)

    independent_results = [
        item
        for item in independence_records
        if item["independence_status"] == "independent"
        and item["outcome"] in {"supports", "challenges"}
    ]
    correlated_claims = [
        item for item in independence_records
        if item["independence_claimed"] and item["independence_status"] != "independent"
    ]

    created_refs = [
        f"{event['payload']['claim_id']}@{event['payload']['claim_version']}" for event in created
    ]
    claim_ids_with_evidence = {
        reference.split("@", 1)[0] for reference in evidence_by_claim
    }
    claim_ids_with_verification = {
        event["payload"]["claim_ref"].split("@", 1)[0] for event in verifications
    }
    claim_ids_with_replication = {
        event["payload"]["claim_ref"].split("@", 1)[0]
        for event in replication_attempts.values()
    }
    claim_ids = {reference.split("@", 1)[0] for reference in created_refs}

    issued_targets = {
        event["payload"]["target_claim_ref"] for event in corrections.values()
    }
    challenge_events = [
        event for event in verifications + list(replication_resolutions.values())
        if event["payload"]["outcome"] == "challenges"
    ]
    challenged_refs = set()
    challenge_by_id = {}
    for event in challenge_events:
        if event["event_type"] == "verification.completed":
            reference = event["payload"]["claim_ref"]
        else:
            reference = replication_attempts[
                event["payload"]["replication_id"]
            ]["payload"]["claim_ref"]
        challenged_refs.add(reference)
        challenge_by_id[event["event_id"]] = event

    expected_propagations = set()
    for correction_id, correction in corrections.items():
        target = correction["payload"]["target_claim_ref"]
        for reference, claim in claim_by_ref.items():
            if target in claim["payload"]["dependencies"]:
                expected_propagations.add((correction_id, reference))
    observed_propagations = {
        (event["payload"]["correction_id"], event["payload"]["dependent_claim_ref"])
        for event in propagations
    }
    correction_latencies = []
    for correction in corrections.values():
        invalidating_steps = [
            challenge_by_id[item]["step"]
            for item in correction["payload"]["invalidating_event_ids"]
            if item in challenge_by_id
        ]
        if invalidating_steps:
            correction_latencies.append(correction["step"] - min(invalidating_steps))

    target_claim_counts = Counter(
        event["payload"]["truth_target_id"]["value"]
        for event in created
        if event["payload"]["truth_target_id"]["status"] == "observed"
    )
    split_targets = sorted(
        target for target, count in target_claim_counts.items() if count > 1
    )
    split_evaluable = all(
        event["payload"]["truth_target_id"]["status"] == "observed"
        for event in created
    )
    truth_targets = list(truth.values())
    hard_targets = {
        item["truth_target_id"]
        for item in truth_targets
        if item["difficulty"] == "hard"
    }
    claimed_targets = set(target_claim_counts)
    hard_coverage = _ratio(len(hard_targets & claimed_targets), len(hard_targets))
    easy_selection_evaluable = (
        bundle["ground_truth"]["status"] == "observed" and bool(hard_targets)
    )

    missing = list(_walk_missing(bundle))
    missing_reasons = Counter(reason for _, reason in missing)
    missing_fields = Counter(path.rsplit(".", 1)[-1] for path, _ in missing)
    lineage_events = [
        event for event in events
        if event["event_type"] in {
            "evidence.attached", "verification.completed",
            "replication.attempted", "replication.resolved",
        }
    ]
    complete_lineages = sum(
        _lineage_values(event["payload"]["lineage"]) is not None
        for event in lineage_events
    )

    gaming_flags = [
        {
            "id": "declared-independence-with-correlated-or-missing-lineage",
            "status": "evaluated",
            "triggered": bool(correlated_claims),
            "event_ids": [item["event_id"] for item in correlated_claims],
            "interpretation": (
                "Self-declared independence is never accepted without complete, "
                "non-overlapping lineage."
            ),
        },
        {
            "id": "claim-splitting-on-one-truth-target",
            "status": "evaluated" if split_evaluable else "not_evaluable",
            "triggered": bool(split_targets) if split_evaluable else None,
            "truth_target_ids": split_targets,
            "interpretation": (
                "Multiple claim ids for one synthetic target can inflate "
                "count-based progress proxies."
            ),
        },
        {
            "id": "easy-target-selection",
            "status": "evaluated" if easy_selection_evaluable else "not_evaluable",
            "triggered": (
                hard_coverage["value"] < 0.5 if easy_selection_evaluable else None
            ),
            "hard_target_coverage": hard_coverage,
            "interpretation": (
                "Avoiding hard targets can inflate verification yield; difficulty "
                "remains a separate diagnostic."
            ),
        },
    ]

    return {
        "schema": REPORT_SCHEMA,
        "bundle_id": bundle["bundle_id"],
        "run_id": bundle["run_id"],
        "data_classification": bundle["classification"],
        "source_bundle_sha256": _sha256(bundle),
        "authorization": {
            "mode": "report_only",
            "optimization_input": False,
            "candidate_selection": False,
            "promotion_veto": False,
            "allowed_uses": ["shadow_diagnostic", "synthetic_contract_validation"],
        },
        "contract_coverage": {
            "events": len(events),
            "event_type_counts": dict(sorted(event_counts.items())),
            "claim_ids": len(claim_ids),
            "claim_versions": len(claim_events),
            "evidence_items": len(evidence),
            "verifications": len(verifications),
            "replication_attempts": len(replication_attempts),
            "replication_resolutions": len(replication_resolutions),
            "corrections_issued": len(corrections),
            "corrections_propagated": len(propagations),
        },
        "lineage_and_missingness": {
            "lineage_events": len(lineage_events),
            "complete_lineages": complete_lineages,
            "incomplete_lineages": len(lineage_events) - complete_lineages,
            "missing_measurements": len(missing),
            "missing_reasons": dict(sorted(missing_reasons.items())),
            "missing_fields": dict(sorted(missing_fields.items())),
            "independence_assessments": independence_records,
        },
        "epistemic_progress_shadow": {
            "claim_evidence_coverage": _ratio(
                len(claim_ids_with_evidence), len(claim_ids)
            ),
            "verification_coverage": _ratio(
                len(claim_ids_with_verification), len(claim_ids)
            ),
            "independent_result_coverage": _ratio(
                len(independent_results), len(independence_records)
            ),
            "truth_target_coverage": _ratio(
                len(claimed_targets & set(truth)), len(truth_targets)
            ),
            "verification_weighted_entropy_reduction": _numeric_summary(
                entropy_reductions
            ),
            "synthetic_truth_brier_improvement": _numeric_summary(brier_improvements),
            "interpretation": (
                "Entropy reduction is a shadow proxy. Synthetic-truth Brier "
                "improvement is retained separately; "
                "neither is an optimization objective."
            ),
        },
        "robustness_shadow": {
            "replication_attempt_coverage": _ratio(
                len(claim_ids_with_replication), len(claim_ids)
            ),
            "replication_resolution_coverage": _ratio(
                len(replication_resolutions), len(replication_attempts)
            ),
            "truth_aligned_independent_results": _ratio(
                sum(truth_alignment), len(truth_alignment)
            ),
            "correction_issuance_coverage": _ratio(
                len(issued_targets & challenged_refs), len(challenged_refs)
            ),
            "correction_propagation_coverage": _ratio(
                len(observed_propagations & expected_propagations),
                len(expected_propagations),
            ),
            "stale_dependent_claim_refs": sorted(
                {
                    reference
                    for _, reference in expected_propagations - observed_propagations
                }
            ),
            "correction_latency_steps": _numeric_summary(correction_latencies),
            "interpretation": (
                "Coverage, truth alignment, correction, and propagation remain separate; "
                "they are not collapsed into a robustness score."
            ),
        },
        "gaming_counterdiagnostics": gaming_flags,
        "ground_truth_boundary": {
            "status": bundle["ground_truth"]["status"],
            "schema": bundle["ground_truth"].get("schema"),
            "target_count": len(truth_targets),
            "synthetic_only": bundle["ground_truth"]["status"] == "observed",
        },
        "interpretation_guard": (
            "These are report-only shadow diagnostics from versioned semantic events. "
            "They are not a LossSpec, held-out metric, candidate ranking, promotion rule, "
            "or claim about real scientific progress."
        ),
    }


def load_bundle(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("semantic instrumentation bundle must be a JSON object")
    return validate_bundle(value)


__all__ = [
    "BUNDLE_SCHEMA",
    "EVENT_SCHEMAS",
    "GROUND_TRUTH_SCHEMA",
    "REPORT_SCHEMA",
    "build_shadow_report",
    "load_bundle",
    "validate_bundle",
]
