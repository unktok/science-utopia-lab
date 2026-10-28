from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from utopia.optimization.design_space import load_candidate, load_space
from utopia.system import (
    COMPILER_ID,
    COMPILER_REVISION,
    MechanismFamily,
    MechanismSpec,
    ScheduleSpec,
    SealedSimulatorExperimentPlan,
    SimulatorFidelitySpec,
    SimulatorModelSpec,
    SimulatorPlanCompilationError,
    SimulatorPlanRequest,
    SimulatorPlanValidationError,
    compile_system_spec_experiment_plan,
    legacy_candidate_to_system_spec,
    validate_simulator_experiment_plan,
)


ROOT = Path(__file__).resolve().parents[2]
SPACE = ROOT / "research/specs/design-space-v1.json"
CANDIDATE = ROOT / "research/specs/example-design-v0.json"


def _spec():
    return legacy_candidate_to_system_spec(load_space(SPACE), load_candidate(CANDIDATE))


def _request(tmp_path: Path, **changes):
    request = SimulatorPlanRequest(
        campaign_id="synthetic-system-plan-v1",
        seed_role="synthetic-development",
        seeds=(1103, 1109),
        model=SimulatorModelSpec(
            model="qwen3:8b",
            api_backend="ollama",
            endpoint="http://127.0.0.1:11434/v1",
            batch_size=2,
            model_revision="synthetic-model-revision",
        ),
        fidelity=SimulatorFidelitySpec(
            fidelity_id="synthetic-two-year",
            experiment_stage="pilot",
            num_years=2,
            num_institutions=3,
            num_conferences=1,
        ),
        output_root=str(tmp_path / "planned-outputs"),
        data_cache_dir=str(tmp_path / "planned-cache"),
        compiler_source_commit="a" * 40,
        compiler_tree_dirty=False,
        source_locator="synthetic:test-fixture",
    )
    return replace(request, **changes)


def _reseal(value):
    payload = {key: item for key, item in value.items() if key != "seal"}
    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    value["seal"]["payload_sha256"] = hashlib.sha256(encoded).hexdigest()


def test_supported_system_compiles_to_sealed_dry_run_plan_without_writes(tmp_path):
    spec = _spec()
    request = _request(tmp_path)
    plan = compile_system_spec_experiment_plan(spec, request)

    assert plan.source_system_fingerprint == spec.fingerprint
    assert plan.plan_fingerprint == plan.to_dict()["seal"]["payload_sha256"]
    assert plan.to_dict()["compiler"] == {
        "id": COMPILER_ID,
        "revision": COMPILER_REVISION,
    }
    assert [run.seed for run in plan.runs] == [1103, 1109]
    assert all(run.run_id.startswith("synthetic-system-plan-v1-") for run in plan.runs)
    assert not (tmp_path / "planned-outputs").exists()
    assert not (tmp_path / "planned-cache").exists()

    mappings = {item.family: item for item in plan.mechanism_mappings}
    assert set(mappings) == {
        "population", "research", "evaluation", "publication", "communication", "funding"
    }
    assert mappings["communication"].execution_surface == "simulator-built-in"
    assert mappings["communication"].parameter_bindings == ()
    acceptance = next(
        item for item in mappings["evaluation"].parameter_bindings
        if item.parameter == "acceptance_rate"
    )
    assert acceptance.cli_flag == "--acceptance_rate_schedule"
    assert acceptance.encoding == "repeat-per-year"
    assert acceptance.value == [0.3, 0.3]


def test_plan_json_round_trip_revalidates_exact_compiler_output(tmp_path):
    original = compile_system_spec_experiment_plan(_spec(), _request(tmp_path))
    encoded = json.loads(original.canonical_json())
    restored = SealedSimulatorExperimentPlan.from_dict(encoded)

    validate_simulator_experiment_plan(restored, dry_run=True)
    assert restored == original
    assert restored.canonical_json() == original.canonical_json()


def test_unsupported_government_and_communication_fail_closed(tmp_path):
    spec = _spec()
    government = MechanismSpec(
        "candidate.government",
        MechanismFamily.GOVERNANCE,
        "production.governance.adaptive-policy-v1",
    )
    with_government = replace(
        spec,
        mechanisms=spec.mechanisms + (government,),
        schedules=spec.schedules + (ScheduleSpec(government.mechanism_id, 6),),
    )
    with pytest.raises(
        SimulatorPlanCompilationError,
        match="unsupported simulator mechanism.*governance",
    ):
        compile_system_spec_experiment_plan(with_government, _request(tmp_path))

    communication = next(
        item for item in spec.mechanisms if item.family == MechanismFamily.COMMUNICATION
    )
    new_communication = replace(
        communication,
        implementation="production.communication.digest-broker-v1",
    )
    changed = replace(
        spec,
        mechanisms=tuple(
            new_communication if item == communication else item
            for item in spec.mechanisms
        ),
    )
    with pytest.raises(
        SimulatorPlanCompilationError,
        match="unsupported simulator mechanism.*communication",
    ):
        compile_system_spec_experiment_plan(changed, _request(tmp_path))


def test_unknown_parameter_and_topology_mutation_are_not_silently_ignored(tmp_path):
    spec = _spec()
    evaluation = next(
        item for item in spec.mechanisms if item.family == MechanismFamily.EVALUATION
    )
    extended_evaluation = replace(
        evaluation,
        parameters={**evaluation.parameters, "government_override": True},
    )
    extended = replace(
        spec,
        mechanisms=tuple(
            extended_evaluation if item == evaluation else item
            for item in spec.mechanisms
        ),
    )
    with pytest.raises(SimulatorPlanCompilationError, match="parameters must map exactly"):
        compile_system_spec_experiment_plan(extended, _request(tmp_path))

    rewired = replace(
        spec,
        connections=tuple(
            replace(edge, latency=2)
            if edge.source_mechanism == "legacy.funding"
            else edge
            for edge in spec.connections
        ),
    )
    with pytest.raises(SimulatorPlanCompilationError, match="exact fixed-v1 graph"):
        compile_system_spec_experiment_plan(rewired, _request(tmp_path))


def test_seal_system_fingerprint_and_exact_mapping_are_fail_closed(tmp_path):
    plan = compile_system_spec_experiment_plan(_spec(), _request(tmp_path))

    bad_seal = json.loads(plan.canonical_json())
    bad_seal["campaign"]["seeds"][0] = 999
    parsed = SealedSimulatorExperimentPlan.from_dict(bad_seal)
    with pytest.raises(SimulatorPlanValidationError, match="seal does not match"):
        validate_simulator_experiment_plan(parsed)

    wrong_source = json.loads(plan.canonical_json())
    wrong_source["source_system"]["fingerprint"] = "0" * 64
    _reseal(wrong_source)
    parsed = SealedSimulatorExperimentPlan.from_dict(wrong_source)
    with pytest.raises(SimulatorPlanValidationError, match="fingerprint mismatch"):
        validate_simulator_experiment_plan(parsed)

    wrong_mapping = json.loads(plan.canonical_json())
    wrong_mapping["mechanism_mappings"][0]["execution_surface"] = "ignored"
    _reseal(wrong_mapping)
    parsed = SealedSimulatorExperimentPlan.from_dict(wrong_mapping)
    with pytest.raises(SimulatorPlanValidationError, match="exact compiler output"):
        validate_simulator_experiment_plan(parsed)


def test_request_provenance_model_seeds_and_fidelity_change_plan_identity(tmp_path):
    spec = _spec()
    request = _request(tmp_path)
    baseline = compile_system_spec_experiment_plan(spec, request)
    different_seeds = compile_system_spec_experiment_plan(
        spec, replace(request, seeds=(1117, 1123))
    )
    different_fidelity = compile_system_spec_experiment_plan(
        spec,
        replace(
            request,
            fidelity=replace(request.fidelity, fidelity_id="three-year", num_years=3),
        ),
    )
    different_model = compile_system_spec_experiment_plan(
        spec, replace(request, model=replace(request.model, model="Qwen/Qwen3-8B"))
    )
    assert len({
        baseline.plan_fingerprint,
        different_seeds.plan_fingerprint,
        different_fidelity.plan_fingerprint,
        different_model.plan_fingerprint,
    }) == 4

    with pytest.raises(SimulatorPlanCompilationError, match="clean compiler tree"):
        compile_system_spec_experiment_plan(
            spec, replace(request, compiler_tree_dirty=True)
        )
