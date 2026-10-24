"""Structural and referential validation for Metric Constitution v1."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from utopia.utils.paths import project_root


ROOT = project_root(__file__)
DEFAULT_SCHEMA = ROOT / "research/specs/metric-constitution-v1.schema.json"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def constitution_sha256(constitution: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(constitution).encode()).hexdigest()


def _ids(records: Iterable[Mapping[str, Any]], label: str, errors: list[str]) -> set[str]:
    values = [record["id"] for record in records]
    duplicates = sorted(value for value in set(values) if values.count(value) > 1)
    if duplicates:
        errors.append(f"duplicate {label} IDs: {', '.join(duplicates)}")
    return set(values)


def _refs(values, allowed, location, errors):
    missing = sorted(set(values) - set(allowed))
    if missing:
        errors.append(f"{location} references unknown IDs: {', '.join(missing)}")


def validate_references(document: Mapping[str, Any]) -> None:
    """Validate ID uniqueness and cross-references not expressible in JSON Schema."""
    errors: list[str] = []
    governance = document["layers"]["evaluator_governance"]
    stakeholder_ids = _ids(document["stakeholders"], "stakeholder", errors)
    slice_ids = _ids(document["stakeholder_slices"], "stakeholder slice", errors)
    horizon_ids = _ids(document["time_horizons"], "time horizon", errors)
    metric_ids = _ids(document["metric_registry"], "metric", errors)
    constraint_ids = _ids(document["layers"]["hard_constraints"], "constraint", errors)
    capability_ids = _ids(document["layers"]["capability_preservation"], "capability", errors)
    _ids(document["layers"]["commitments"], "commitment", errors)
    evaluator_ids = _ids(governance["evaluators"], "evaluator", errors)
    _ids(governance["decision_policies"], "decision policy", errors)
    _ids(governance["goodhart_audits"], "Goodhart audit", errors)

    lineage = document["lineage"]
    _refs(lineage["proposed_by"], stakeholder_ids, "lineage.proposed_by", errors)
    _refs(lineage["approved_by"], stakeholder_ids, "lineage.approved_by", errors)
    for record in document["stakeholder_slices"]:
        _refs(record["stakeholder_ids"], stakeholder_ids,
              f"stakeholder_slices.{record['id']}.stakeholder_ids", errors)
    for metric in document["metric_registry"]:
        prefix = f"metric_registry.{metric['id']}"
        _refs([metric["evaluator_ref"]], evaluator_ids, prefix + ".evaluator_ref", errors)
        _refs(metric["time_horizon_refs"], horizon_ids, prefix + ".time_horizon_refs", errors)
        _refs(metric["stakeholder_slice_refs"], slice_ids,
              prefix + ".stakeholder_slice_refs", errors)
        _refs(metric["shadow_metric_refs"], metric_ids, prefix + ".shadow_metric_refs", errors)
        _refs(metric["owner_stakeholder_ids"], stakeholder_ids,
              prefix + ".owner_stakeholder_ids", errors)

    for constraint in document["layers"]["hard_constraints"]:
        prefix = f"layers.hard_constraints.{constraint['id']}"
        _refs(constraint["protected_stakeholder_ids"], stakeholder_ids,
              prefix + ".protected_stakeholder_ids", errors)
        _refs(constraint["protected_slice_refs"], slice_ids,
              prefix + ".protected_slice_refs", errors)
        _refs(constraint["metric_refs"], metric_ids, prefix + ".metric_refs", errors)
    for capability in document["layers"]["capability_preservation"]:
        prefix = f"layers.capability_preservation.{capability['id']}"
        _refs(capability["protected_stakeholder_ids"], stakeholder_ids,
              prefix + ".protected_stakeholder_ids", errors)
        _refs(capability["metric_refs"], metric_ids, prefix + ".metric_refs", errors)
        _refs(capability["time_horizon_refs"], horizon_ids,
              prefix + ".time_horizon_refs", errors)
    for commitment in document["layers"]["commitments"]:
        prefix = f"layers.commitments.{commitment['id']}"
        for field in ("owner_stakeholder_ids", "beneficiary_stakeholder_ids",
                      "burden_bearer_stakeholder_ids"):
            _refs(commitment[field], stakeholder_ids, prefix + "." + field, errors)
        _refs(commitment["hard_constraint_refs"], constraint_ids,
              prefix + ".hard_constraint_refs", errors)
        _refs(commitment["capability_refs"], capability_ids,
              prefix + ".capability_refs", errors)
        _ids(commitment["objectives"],
             f"objective in commitment {commitment['id']}", errors)
        for objective in commitment["objectives"]:
            objective_prefix = prefix + f".objectives.{objective['id']}"
            _refs(objective["metric_refs"], metric_ids,
                  objective_prefix + ".metric_refs", errors)
            _refs(objective["time_horizon_refs"], horizon_ids,
                  objective_prefix + ".time_horizon_refs", errors)
            _refs(objective["stakeholder_slice_refs"], slice_ids,
                  objective_prefix + ".stakeholder_slice_refs", errors)

    for policy in governance["decision_policies"]:
        _refs(policy["evaluator_refs"], evaluator_ids,
              f"decision_policies.{policy['id']}.evaluator_refs", errors)
    change = governance["change_control"]
    for field in ("proposer_stakeholder_ids", "approver_stakeholder_ids",
                  "auditor_stakeholder_ids"):
        _refs(change[field], stakeholder_ids, "change_control." + field, errors)
    for audit in governance["goodhart_audits"]:
        _refs(audit["metric_refs"], metric_ids,
              f"goodhart_audits.{audit['id']}.metric_refs", errors)
        _refs(audit["responsible_stakeholder_ids"], stakeholder_ids,
              f"goodhart_audits.{audit['id']}.responsible_stakeholder_ids", errors)

    if errors:
        raise ValueError("Metric constitution reference errors:\n- " + "\n- ".join(errors))


def load_metric_constitution(path: str | Path, schema_path: str | Path = DEFAULT_SCHEMA):
    document_path = Path(path)
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    document = json.loads(document_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        messages = [
            f"{'.'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
            for error in errors
        ]
        raise ValueError("Metric constitution schema errors:\n- " + "\n- ".join(messages))
    validate_references(document)
    return document
