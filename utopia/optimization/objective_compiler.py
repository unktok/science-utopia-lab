"""Prospective ObjectiveSpec constitution and LossSpec compiler v1.

The compiler is a fail-closed translation boundary.  Normative choices remain
in a versioned ObjectiveSpec; measurement claims remain in a separately
validated metric-card registry; the emitted objects are ordinary scalar
LossSpecs for a future campaign.  Nothing in this module discovers policy
weights or promotes a metric by itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from utopia.optimization.loss import loss_spec_sha256, validate_loss_spec


OBJECTIVE_SCHEMA = "scienceutopia.objective-spec.v1"
REGISTRY_SCHEMA = "scienceutopia.validated-metric-card-registry.v1"
COMPILATION_SCHEMA = "scienceutopia.objective-compilation.v1"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def canonical_sha256(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def metric_card_sha256(card: Mapping[str, Any]) -> str:
    return canonical_sha256(card)


def load_objective_spec(
    path: str | Path, schema_path: str | Path | None = None
) -> dict[str, Any]:
    source = Path(path)
    value = json.loads(source.read_text(encoding="utf-8"))
    if schema_path is None:
        schema_path = _project_root(source) / "research/specs/objective-spec-v1.schema.json"
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validate_objective_spec(value, schema)
    return value


def load_validated_metric_registry(
    path: str | Path, schema_path: str | Path | None = None
) -> dict[str, Any]:
    source = Path(path)
    value = json.loads(source.read_text(encoding="utf-8"))
    if schema_path is None:
        schema_path = _project_root(source) / "research/specs/validated-metric-card-registry-v1.schema.json"
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validate_metric_registry(value, schema)
    return value


def _project_root(path: Path) -> Path:
    for parent in (path.resolve().parent, *path.resolve().parents):
        if (parent / "research/specs").is_dir() and (parent / "utopia").is_dir():
            return parent
    return Path.cwd()


def validate_objective_spec(spec: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    errors = _schema_errors(spec, schema)
    if errors:
        raise ValueError("Invalid ObjectiveSpec: " + "; ".join(sorted(errors)))
    if spec.get("schema") != OBJECTIVE_SCHEMA:
        errors.append(f"schema must be {OBJECTIVE_SCHEMA!r}")
    if spec.get("governance", {}).get("universal_objective_claim") != "none":
        errors.append("ObjectiveSpec cannot claim a universal objective")

    stakeholders = _unique_ids(spec.get("stakeholders", []), "stakeholder", errors)
    constructs = _unique_ids(spec.get("constructs", []), "construct", errors)
    phases = _unique_ids(spec.get("phases", []), "phase", errors)
    components = _unique_ids(spec.get("components", []), "component", errors)
    _unique_ids(spec.get("tradeoffs", []), "tradeoff", errors)

    for construct in spec.get("constructs", []):
        _check_refs(construct["stakeholder_refs"], stakeholders, f"construct {construct['id']!r}", errors)

    ordered_phases = spec.get("phases", [])
    for index, phase in enumerate(ordered_phases):
        if index == 0 and phase["start_step"] != 0:
            errors.append("first phase must start at step 0")
        end = phase["end_step"]
        if end is not None and end <= phase["start_step"]:
            errors.append(f"phase {phase['id']!r} end_step must exceed start_step")
        if index < len(ordered_phases) - 1:
            if end is None or ordered_phases[index + 1]["start_step"] != end:
                errors.append(f"phase {phase['id']!r} does not join the next phase")
        elif end is not None:
            errors.append("final phase must have an open end_step")

    metric_inputs: set[tuple[str, str]] = set()
    for component in spec.get("components", []):
        prefix = f"component {component['id']!r}"
        _check_refs([component["construct_ref"]], constructs, prefix, errors)
        _check_refs(component["stakeholder_refs"], stakeholders, prefix, errors)
        weights = component["weights"]
        weight_phases = [item["phase_ref"] for item in weights]
        if set(weight_phases) != phases or len(weight_phases) != len(phases):
            errors.append(f"{prefix} must define exactly one weight for every phase")
        card_ref = component["metric_card_ref"]
        identity = (card_ref["id"], card_ref["sha256"])
        if identity in metric_inputs:
            errors.append(f"{prefix} duplicates a metric-card reference")
        metric_inputs.add(identity)

    positive_by_phase = {phase_id: 0 for phase_id in phases}
    for component in spec.get("components", []):
        for weight in component["weights"]:
            if weight["value"] > 0 and weight["phase_ref"] in positive_by_phase:
                positive_by_phase[weight["phase_ref"]] += 1
    for phase_id, count in positive_by_phase.items():
        if count < 2:
            errors.append(f"phase {phase_id!r} must retain at least two positive tradeoff components")

    traded_components: set[str] = set()
    for tradeoff in spec.get("tradeoffs", []):
        _check_refs(tradeoff["component_refs"], components, f"tradeoff {tradeoff['id']!r}", errors)
        traded_components.update(tradeoff["component_refs"])
    missing_tradeoffs = components - traded_components
    if missing_tradeoffs:
        errors.append(f"components lack an explicit tradeoff declaration: {sorted(missing_tradeoffs)!r}")

    if spec.get("hard_constraints") != []:
        errors.append("v1 requires hard_constraints to be empty; tradeoffs cannot be hidden vetoes")
    core_scopes = {"construct-validity", "adversarial-validity", "measurement-reliability"}
    declared_scopes = set(spec.get("measurement_evidence_policy", {}).get("required_scopes", []))
    if not core_scopes <= declared_scopes:
        errors.append(f"measurement evidence policy lacks core scopes: {sorted(core_scopes - declared_scopes)!r}")
    if errors:
        raise ValueError("Invalid ObjectiveSpec: " + "; ".join(sorted(errors)))


def validate_metric_registry(registry: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    errors = _schema_errors(registry, schema)
    if errors:
        raise ValueError("Invalid metric-card registry: " + "; ".join(sorted(errors)))
    if registry.get("schema") != REGISTRY_SCHEMA:
        errors.append(f"schema must be {REGISTRY_SCHEMA!r}")
    if registry.get("active_campaign_effect") != "none":
        errors.append("active_campaign_effect must be none")
    cards = _unique_ids(registry.get("cards", []), "metric card", errors)
    evidence = _unique_ids(registry.get("evidence", []), "evidence", errors)
    evidence_by_id = {item["id"]: item for item in registry.get("evidence", [])}
    for card in registry.get("cards", []):
        prefix = f"metric card {card['id']!r}"
        _check_refs(card["evidence_refs"], evidence, prefix, errors)
        _check_refs(card["goodhart_test_refs"], evidence, prefix, errors)
        norm_ref = card["normalization"]["evidence_ref"]
        _check_refs([norm_ref], evidence, prefix, errors)
        if norm_ref not in card["evidence_refs"]:
            errors.append(f"{prefix} normalization evidence is absent from evidence_refs")
        for ref in card["goodhart_test_refs"]:
            if ref in evidence_by_id and evidence_by_id[ref]["scope"] != "adversarial-validity":
                errors.append(f"{prefix} Goodhart evidence {ref!r} is not adversarial-validity")
        if card["status"] == "validated-for-optimization" and not card["goodhart_test_refs"]:
            errors.append(f"{prefix} lacks adversarial evidence")
    if not cards:
        errors.append("registry contains no metric cards")
    if errors:
        raise ValueError("Invalid metric-card registry: " + "; ".join(sorted(errors)))


def compile_objective(
    objective: Mapping[str, Any],
    registry: Mapping[str, Any],
    *,
    objective_schema: Mapping[str, Any],
    registry_schema: Mapping[str, Any],
    evidence_root: str | Path,
) -> dict[str, Any]:
    """Compile an ObjectiveSpec into one ordinary LossSpec per weight phase."""

    validate_objective_spec(objective, objective_schema)
    validate_metric_registry(registry, registry_schema)
    verify_evidence_artifacts(registry, evidence_root)
    cards = {item["id"]: item for item in registry["cards"]}
    evidence = {item["id"]: item for item in registry["evidence"]}
    required_scopes = set(objective["measurement_evidence_policy"]["required_scopes"])
    components: list[dict[str, Any]] = []
    metric_identities: set[tuple[str, str | None]] = set()

    for component in objective["components"]:
        ref = component["metric_card_ref"]
        card = cards.get(ref["id"])
        if card is None:
            raise ValueError(f"metric card {ref['id']!r} is absent from the registry")
        if card["version"] != ref["version"]:
            raise ValueError(f"metric card {ref['id']!r} version mismatch")
        actual_hash = metric_card_sha256(card)
        if actual_hash != ref["sha256"]:
            raise ValueError(f"metric card {ref['id']!r} hash mismatch")
        if card["status"] != objective["measurement_evidence_policy"]["minimum_status"]:
            raise ValueError(f"metric card {ref['id']!r} is not validated for optimization")
        if card["construct_id"] != component["construct_ref"]:
            raise ValueError(f"metric card {ref['id']!r} construct mismatch")

        referenced = [evidence[item] for item in card["evidence_refs"]]
        scopes = {item["scope"] for item in referenced}
        missing_scopes = required_scopes - scopes
        if missing_scopes:
            raise ValueError(f"metric card {ref['id']!r} lacks evidence scopes {sorted(missing_scopes)!r}")
        if not all(item["independent_review"] for item in referenced):
            raise ValueError(f"metric card {ref['id']!r} lacks independent evidence review")
        if not set(objective["distribution"]["groups"]) <= set(card["distribution_support"]):
            raise ValueError(f"metric card {ref['id']!r} lacks declared distribution support")
        if not set(objective["time_horizon"]["outcome_windows"]) <= set(card["time_support"]):
            raise ValueError(f"metric card {ref['id']!r} lacks declared time support")
        metric_identity = (card["metric_id"], card["slice_id"])
        if metric_identity in metric_identities:
            raise ValueError(f"duplicate compiled metric input {metric_identity!r}")
        metric_identities.add(metric_identity)
        components.append({"objective_component": component, "metric_card": card, "metric_card_sha256": actual_hash})

    audit_refs = set(objective["goodhart_audit"]["adversarial_evidence_refs"])
    missing_audits = audit_refs - set(evidence)
    if missing_audits:
        raise ValueError(f"ObjectiveSpec Goodhart evidence is absent: {sorted(missing_audits)!r}")
    if any(evidence[ref]["scope"] != "adversarial-validity" for ref in audit_refs):
        raise ValueError("ObjectiveSpec Goodhart evidence must be adversarial-validity")

    compiled_phases = []
    for phase in objective["phases"]:
        terms = []
        intercept = 0.0
        component_receipts = []
        for item in components:
            component = item["objective_component"]
            card = item["metric_card"]
            weight = next(entry["value"] for entry in component["weights"] if entry["phase_ref"] == phase["id"])
            sign = -1.0 if card["preferred_direction"] == "maximize" else 1.0
            normalization = card["normalization"]
            coefficient = sign * float(weight) * float(normalization["multiplier"])
            intercept += sign * float(weight) * float(normalization["offset"])
            terms.append({"metric_id": card["metric_id"], "slice_id": card["slice_id"], "coefficient": coefficient})
            component_receipts.append({
                "component_id": component["id"],
                "construct_id": component["construct_ref"],
                "metric_card": {"id": card["id"], "version": card["version"], "sha256": item["metric_card_sha256"]},
                "metric_id": card["metric_id"],
                "slice_id": card["slice_id"],
                "preferred_direction": card["preferred_direction"],
                "weight": weight,
                "compiled_coefficient": coefficient,
                "measurement_evidence_refs": card["evidence_refs"],
                "goodhart_test_refs": card["goodhart_test_refs"],
                "normalization_evidence_ref": normalization["evidence_ref"],
                "limitations": card["limitations"],
            })
        loss_spec = {
            "schema": "scienceutopia.loss-spec.v1",
            "id": f"{objective['id']}--{phase['id']}",
            "version": objective["version"],
            "status": "research",
            "direction": "minimize",
            "optimization_seed_role": "optimization",
            "per_run": {"intercept": intercept, "terms": terms},
            "across_seeds": {
                "aggregation": objective["uncertainty"]["risk_aggregation"],
                "dispersion_weight": objective["uncertainty"]["dispersion_weight"],
                "minimum_valid_runs": objective["uncertainty"]["minimum_valid_runs"],
            },
            "interpretation": f"Prospective phase {phase['id']} compilation of ObjectiveSpec {objective['id']} v{objective['version']}; weights are declared policy tradeoffs, not discovered scientific truth or hidden vetoes.",
            "prohibited_claims": sorted(set(objective["prohibited_claims"] + ["universal science-policy optimum", "validated real-world welfare weights"])),
        }
        validate_loss_spec(loss_spec)
        compiled_phases.append({
            "phase": phase,
            "loss_spec": loss_spec,
            "loss_spec_sha256": loss_spec_sha256(loss_spec),
            "component_receipts": component_receipts,
        })

    return {
        "schema": COMPILATION_SCHEMA,
        "status": (
            "synthetic-test-only"
            if registry["status"] == "prospective-synthetic-test-only"
            else "prospective-future-campaign"
        ),
        "objective_spec": {"id": objective["id"], "version": objective["version"], "sha256": canonical_sha256(objective)},
        "metric_registry": {"id": registry["id"], "version": registry["version"], "sha256": canonical_sha256(registry)},
        "constitution_summary": {
            "governance": objective["governance"],
            "stakeholder_ids": [item["id"] for item in objective["stakeholders"]],
            "construct_ids": [item["id"] for item in objective["constructs"]],
            "time_horizon": objective["time_horizon"],
            "distribution": objective["distribution"],
            "uncertainty": objective["uncertainty"],
        },
        "hard_constraints": [],
        "tradeoffs": objective["tradeoffs"],
        "goodhart_audit": objective["goodhart_audit"],
        "measurement_evidence_policy": objective["measurement_evidence_policy"],
        "compiled_phases": compiled_phases,
        "warnings": [
            "Compilation proves schema and evidence-contract compatibility, not real-world construct validity.",
            "Weights, schedules, stakeholders, distribution, and horizons remain explicit normative choices.",
            "Shadow monitors are diagnostics and do not become implicit hard constraints.",
        ],
    }


def verify_evidence_artifacts(
    registry: Mapping[str, Any], evidence_root: str | Path
) -> None:
    """Verify evidence bytes while preventing paths from escaping the project root."""

    root = Path(evidence_root).resolve()
    errors: list[str] = []
    for item in registry["evidence"]:
        artifact = (root / item["artifact"]).resolve()
        try:
            artifact.relative_to(root)
        except ValueError:
            errors.append(f"evidence {item['id']!r} escapes the evidence root")
            continue
        if not artifact.is_file():
            errors.append(f"evidence {item['id']!r} artifact is missing")
            continue
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            errors.append(f"evidence {item['id']!r} artifact hash mismatch")
    if errors:
        raise ValueError("Invalid measurement evidence: " + "; ".join(sorted(set(errors))))


def _schema_errors(value: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    return [f"schema: {error.message}" for error in Draft202012Validator(schema).iter_errors(value)]


def _unique_ids(items: list[Mapping[str, Any]], label: str, errors: list[str]) -> set[str]:
    seen: set[str] = set()
    for item in items:
        item_id = item["id"]
        if item_id in seen:
            errors.append(f"duplicate {label} id {item_id!r}")
        seen.add(item_id)
    return seen


def _check_refs(refs: list[str], targets: set[str], prefix: str, errors: list[str]) -> None:
    missing = sorted(set(refs) - targets)
    if missing:
        errors.append(f"{prefix} has unresolved references {missing!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile prospective ObjectiveSpec v1")
    parser.add_argument("objective", type=Path)
    parser.add_argument("registry", type=Path)
    parser.add_argument("--objective-schema", type=Path, required=True)
    parser.add_argument("--registry-schema", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    objective_schema = json.loads(args.objective_schema.read_text(encoding="utf-8"))
    registry_schema = json.loads(args.registry_schema.read_text(encoding="utf-8"))
    objective = load_objective_spec(args.objective, args.objective_schema)
    registry = load_validated_metric_registry(args.registry, args.registry_schema)
    result = compile_objective(
        objective,
        registry,
        objective_schema=objective_schema,
        registry_schema=registry_schema,
        evidence_root=args.evidence_root,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
