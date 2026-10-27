from dataclasses import replace
import json
from pathlib import Path

import jsonschema
import pytest

from utopia.optimization.design_space import candidate_to_cli, load_candidate, load_space
from utopia.system import (
    ArtifactTypeSpec,
    ChannelKind,
    ConnectionSpec,
    LegacyCompilationError,
    MechanismFamily,
    MechanismSpec,
    PortSpec,
    ScheduleSpec,
    SystemSpec,
    compile_legacy_system,
    legacy_candidate_to_system_spec,
    validate_system_spec,
)


ROOT = Path(__file__).resolve().parents[2]
SPACE = ROOT / "research/specs/design-space-v0.json"
EXAMPLE = ROOT / "research/specs/example-design-v0.json"
SYSTEM_SCHEMA = ROOT / "research/specs/system-spec-v1.schema.json"


def test_empty_system_and_system_without_evaluation_are_valid():
    assert validate_system_spec(SystemSpec("empty-system", 1)).valid

    publication_only = SystemSpec(
        "publication-only",
        1,
        mechanisms=(
            MechanismSpec(
                "open-repository",
                MechanismFamily.PUBLICATION,
                "example.open-repository-v1",
            ),
        ),
        schedules=(ScheduleSpec("open-repository", 0, "continuous"),),
    )
    report = validate_system_spec(publication_only)
    assert report.valid
    assert not report.warnings


def test_validator_checks_typed_edges_required_inputs_and_references():
    spec = SystemSpec(
        "broken-system",
        1,
        artifact_types=(
            ArtifactTypeSpec("paper"),
            ArtifactTypeSpec("decision"),
        ),
        mechanisms=(
            MechanismSpec(
                "producer",
                MechanismFamily.RESEARCH,
                "example.producer-v1",
                outputs=(PortSpec("paper", ChannelKind.ARTIFACT, "paper"),),
            ),
            MechanismSpec(
                "consumer",
                MechanismFamily.PUBLICATION,
                "example.consumer-v1",
                inputs=(PortSpec("decision", ChannelKind.DECISION, "decision"),),
            ),
        ),
        connections=(
            ConnectionSpec(
                "producer",
                "paper",
                "consumer",
                "decision",
                ChannelKind.ARTIFACT,
            ),
        ),
    )
    report = validate_system_spec(spec)
    assert not report.valid
    assert {issue.code for issue in report.errors} >= {
        "target_channel_mismatch",
        "artifact_type_mismatch",
    }

    disconnected = replace(spec, connections=())
    assert "unconnected_required_input" in {
        issue.code for issue in validate_system_spec(disconnected).errors
    }


def test_round_trip_and_fingerprint_cover_the_whole_graph():
    space, candidate = load_space(SPACE), load_candidate(EXAMPLE)
    spec = legacy_candidate_to_system_spec(space, candidate)
    parsed = SystemSpec.from_dict(json.loads(spec.canonical_json()))

    assert parsed == spec
    assert parsed.fingerprint == spec.fingerprint

    funding = next(item for item in spec.mechanisms if item.family == MechanismFamily.FUNDING)
    changed_funding = replace(
        funding,
        parameters={**funding.parameters, "budget_slots_fraction": 0.5},
    )
    changed = replace(
        spec,
        mechanisms=tuple(
            changed_funding if item.mechanism_id == funding.mechanism_id else item
            for item in spec.mechanisms
        ),
    )
    assert changed.fingerprint != spec.fingerprint


def test_legacy_spec_conforms_to_public_json_schema():
    space, candidate = load_space(SPACE), load_candidate(EXAMPLE)
    spec = legacy_candidate_to_system_spec(space, candidate)
    schema = json.loads(SYSTEM_SCHEMA.read_text(encoding="utf-8"))

    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(spec.to_dict())


def test_legacy_candidate_compiles_to_the_existing_cli_contract():
    space, candidate = load_space(SPACE), load_candidate(EXAMPLE)
    spec = legacy_candidate_to_system_spec(space, candidate)
    plan = compile_legacy_system(spec, years=3)

    assert list(plan.cli_args) == candidate_to_cli(space, candidate, years=3)
    assert plan.system_fingerprint == spec.fingerprint
    assert {mechanism.family for mechanism in spec.mechanisms} >= {
        MechanismFamily.RESEARCH,
        MechanismFamily.EVALUATION,
        MechanismFamily.PUBLICATION,
        MechanismFamily.FUNDING,
        MechanismFamily.COMMUNICATION,
    }
    assert MechanismFamily.GOVERNANCE not in {
        mechanism.family for mechanism in spec.mechanisms
    }


def test_legacy_compiler_rejects_general_or_mutated_topology():
    with pytest.raises(LegacyCompilationError, match="not bound"):
        compile_legacy_system(SystemSpec("general-system", 1), years=1)

    space, candidate = load_space(SPACE), load_candidate(EXAMPLE)
    spec = legacy_candidate_to_system_spec(space, candidate)
    extended = replace(
        spec,
        mechanisms=spec.mechanisms
        + (
            MechanismSpec(
                "new-governance",
                MechanismFamily.GOVERNANCE,
                "example.governance-v1",
            ),
        ),
        schedules=spec.schedules + (ScheduleSpec("new-governance", 6),),
    )
    with pytest.raises(LegacyCompilationError, match="exact fixed-v1 topology"):
        compile_legacy_system(extended, years=1)

    rewired = replace(
        spec,
        connections=tuple(
            replace(item, latency=2)
            if item.source_mechanism == "legacy.funding"
            else item
            for item in spec.connections
        ),
    )
    with pytest.raises(LegacyCompilationError, match="exact fixed-v1 graph"):
        compile_legacy_system(rewired, years=1)


def test_parameters_must_be_strict_json():
    spec = SystemSpec(
        "not-json",
        1,
        mechanisms=(
            MechanismSpec(
                "custom",
                MechanismFamily.CUSTOM,
                "example.custom-v1",
                parameters={"bad": float("nan")},
            ),
        ),
    )
    report = validate_system_spec(spec)
    assert "non_json_value" in {issue.code for issue in report.errors}
