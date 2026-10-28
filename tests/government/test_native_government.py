from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from utopia.arguments import parse_arguments
from utopia.communication.native import native_communication_system_spec
from utopia.config import SIMULATION_CONFIG
from utopia.government.native import (
    APPLICATION_EVENT_TYPE,
    DECISION_EVENT_TYPE,
    GOVERNMENT_MECHANISM_ID,
    OBSERVATION_EVENT_TYPE,
    NativeGovernmentConfig,
    NativeGovernmentError,
    NativeGovernmentRuntime,
    native_government_config_from_namespace,
    native_government_system_spec,
    native_government_system_spec_from_catalog_candidate,
    validate_native_government_events,
)
from utopia.optimization.design_space import load_candidate, load_space
from utopia.optimization.government_structural import (
    ENGINEERING_POLICY_DIRECTIVES,
    government_structural_space,
)
from utopia.optimization.structural_space import StructuralSelection
from utopia.replay import ArtifactBundle, convert_artifacts
from utopia.simulation import Simulation
from utopia.system import (
    SimulatorFidelitySpec,
    SimulatorModelSpec,
    SimulatorPlanCompilationError,
    SimulatorPlanRequest,
    compile_system_spec_experiment_plan,
    legacy_candidate_to_system_spec,
    validate_simulator_experiment_plan,
)
from utopia.system.production.governance import (
    EVENT_RESPONSIVE_GOVERNMENT,
    STATE_SCHEMA_VERSION,
    THRESHOLD_GOVERNMENT,
)


ROOT = Path(__file__).resolve().parents[2]


def _base_spec():
    return legacy_candidate_to_system_spec(
        load_space(ROOT / "research/specs/design-space-v1.json"),
        load_candidate(ROOT / "research/specs/example-design-v0.json"),
    )


def _request(tmp_path: Path):
    return SimulatorPlanRequest(
        campaign_id="synthetic-native-government-v1",
        seed_role="synthetic-development",
        seeds=(1201,),
        model=SimulatorModelSpec(
            model="qwen3:8b",
            api_backend="ollama",
            endpoint="http://127.0.0.1:11434/v1",
            batch_size=2,
        ),
        fidelity=SimulatorFidelitySpec(
            fidelity_id="synthetic-four-year",
            experiment_stage="smoke",
            num_years=4,
            num_institutions=2,
            num_conferences=1,
        ),
        output_root=str(tmp_path / "outputs"),
        data_cache_dir=str(tmp_path / "cache"),
        compiler_source_commit="b" * 40,
        compiler_tree_dirty=False,
        source_locator="synthetic:native-government-fixture",
    )


def _spec(
    implementation=EVENT_RESPONSIVE_GOVERNMENT,
    *,
    evaluation_latency=1,
    funding_latency=2,
):
    return native_government_system_spec(
        _base_spec(),
        implementation=implementation,
        policy_latencies={
            "evaluation": evaluation_latency,
            "funding": funding_latency,
        },
    )


def _config(spec, implementation=EVENT_RESPONSIVE_GOVERNMENT):
    threshold = implementation == THRESHOLD_GOVERNMENT
    return NativeGovernmentConfig(
        implementation=implementation,
        minimum_observations=10 if threshold else 1,
        repeat_interval=10 if threshold else 1,
        directives=ENGINEERING_POLICY_DIRECTIVES,
        observation_sources=("evaluation", "funding", "publication"),
        policy_latencies=(("evaluation", 1), ("funding", 2)),
        system_fingerprint=spec.fingerprint,
    )


def _observations(year):
    return {
        "evaluation": {"accepted": year, "rejected": 2},
        "funding": {"awards": 1, "applications": 3},
        "publication": {
            "published_count": year,
            "published_output_ids": [f"paper-{year}"],
        },
    }


def _run_year(runtime, year):
    start = runtime.start_year(year)
    finish = runtime.finish_year(year, _observations(year))
    return (*start, *finish)


def test_default_off_preserves_base_plan_and_parser(tmp_path):
    parsed = parse_arguments(
        ["--experiment_name", "exploration_vs_exploitation"],
        create_dirs=False,
    )
    assert native_government_config_from_namespace(parsed) is None

    plan = compile_system_spec_experiment_plan(_base_spec(), _request(tmp_path))
    argv = plan.runs[0].simulator_argv
    assert "--government-policy-mode" not in argv
    assert "--government-system-fingerprint" not in argv
    assert not (tmp_path / "outputs").exists()
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize(
    ("implementation", "mode", "minimum"),
    (
        (EVENT_RESPONSIVE_GOVERNMENT, "event-responsive", 1),
        (THRESHOLD_GOVERNMENT, "threshold", 10),
    ),
)
def test_catalog_system_spec_compiles_to_sealed_native_config(
    tmp_path, implementation, mode, minimum
):
    spec = _spec(implementation)
    plan = compile_system_spec_experiment_plan(spec, _request(tmp_path))
    validate_simulator_experiment_plan(plan)
    parsed = parse_arguments(list(plan.runs[0].simulator_argv), create_dirs=False)
    config = native_government_config_from_namespace(parsed)

    assert config.implementation == implementation
    assert config.mode == mode
    assert config.minimum_observations == minimum
    assert config.system_fingerprint == spec.fingerprint
    assert config.latency_by_target == {"evaluation": 1, "funding": 2}
    mapping = next(
        item for item in plan.mechanism_mappings
        if item.mechanism_id == GOVERNMENT_MECHANISM_ID
    )
    assert mapping.implementation == implementation
    assert mapping.execution_surface == "cli"


@pytest.mark.parametrize("government_outer", (False, True))
def test_government_and_communication_overlays_compile_in_either_order(
    tmp_path, government_outer
):
    base = _base_spec()
    if government_outer:
        inner = native_communication_system_spec(base, mode="digest", latency=1)
        spec = native_government_system_spec(
            inner,
            implementation=EVENT_RESPONSIVE_GOVERNMENT,
            policy_latencies={"evaluation": 1, "funding": 2},
        )
    else:
        inner = native_government_system_spec(
            base,
            implementation=EVENT_RESPONSIVE_GOVERNMENT,
            policy_latencies={"evaluation": 1, "funding": 2},
        )
        spec = native_communication_system_spec(inner, mode="digest", latency=1)

    plan = compile_system_spec_experiment_plan(spec, _request(tmp_path))
    argv = plan.runs[0].simulator_argv
    assert "--communication-broker-mode" in argv
    assert "--government-policy-mode" in argv
    assert "--government-system-fingerprint" in argv


def test_policy_action_reaches_two_mechanisms_with_typed_lineage_and_latency():
    spec = _spec()
    runtime = NativeGovernmentRuntime(_config(spec))

    first = _run_year(runtime, 1)
    start_two = runtime.start_year(2)
    runtime.finish_year(2, _observations(2))
    start_three = runtime.start_year(3)
    runtime.finish_year(3, _observations(3))

    assert [event.event_type for event in first] == [
        OBSERVATION_EVENT_TYPE,
        OBSERVATION_EVENT_TYPE,
        OBSERVATION_EVENT_TYPE,
        DECISION_EVENT_TYPE,
    ]
    assert [event.payload["target_family"] for event in start_two] == ["evaluation"]
    assert {event.payload["target_family"] for event in start_three} == {
        "evaluation",
        "funding",
    }
    decision = next(event for event in first if event.event_type == DECISION_EVENT_TYPE)
    evaluation = start_two[0]
    assert evaluation.provenance["source_event_ids"] == [decision.event_id]
    assert evaluation.payload["affected_mechanism"] == "legacy.evaluation"
    assert evaluation.payload["latency"] == 1
    funding = next(
        event for event in start_three
        if event.payload["target_family"] == "funding"
    )
    assert funding.payload["latency"] == 2
    assert runtime.evaluation_acceptance_rate == 1.0
    assert runtime.funding_award_multiplier == 2.0
    validate_native_government_events(
        runtime.events, system_fingerprint=spec.fingerprint
    )
    assert runtime.to_dict()["production_state"]["schema_version"] == (
        STATE_SCHEMA_VERSION
    )


def test_catalog_candidate_translates_presence_implementation_edges_and_latency(tmp_path):
    space = government_structural_space()
    selection = StructuralSelection(
        {
            "workload": "deterministic-v1",
            "evaluation": "conference-rate",
            "funding": "compact-ranked",
            "publication": "paper-tracker",
            "government": "cumulative-threshold",
        },
        {
            "review-input": "instant",
            "funding-input": "instant",
            "publication-flow": "instant",
            "observe-decisions": "instant",
            "observe-allocations": None,
            "observe-publications": "instant",
            "policy-to-evaluation": "two-period",
            "policy-to-funding": "one-period",
        },
    )
    catalog = space.build(selection)
    translated = native_government_system_spec_from_catalog_candidate(
        _base_spec(), catalog.to_dict()
    )
    plan = compile_system_spec_experiment_plan(translated, _request(tmp_path))
    args = parse_arguments(list(plan.runs[0].simulator_argv), create_dirs=False)
    config = native_government_config_from_namespace(args)

    assert config.implementation == THRESHOLD_GOVERNMENT
    assert config.observation_sources == ("evaluation", "publication")
    assert config.latency_by_target == {"evaluation": 2, "funding": 1}
    source = translated.metadata["native_government_catalog_source"]
    assert source["space_id"] == "stateful-government-science-system-v1"
    assert source["candidate_fingerprint"] == catalog.fingerprint
    assert source["selection"] == selection.to_dict()

    absent_selection = StructuralSelection(
        {**selection.nodes, "government": None},
        {
            **selection.edges,
            "observe-decisions": None,
            "observe-publications": None,
            "policy-to-evaluation": None,
            "policy-to-funding": None,
        },
    )
    absent_catalog = space.build(absent_selection)
    absent = native_government_system_spec_from_catalog_candidate(
        _base_spec(), absent_catalog.to_dict()
    )
    absent_plan = compile_system_spec_experiment_plan(absent, _request(tmp_path))
    assert "--government-policy-mode" not in absent_plan.runs[0].simulator_argv
    assert not absent.metadata["native_government_catalog_source"][
        "government_present"
    ]


def test_threshold_implementation_accumulates_real_production_state():
    spec = _spec(THRESHOLD_GOVERNMENT)
    runtime = NativeGovernmentRuntime(_config(spec, THRESHOLD_GOVERNMENT))

    for year in range(1, 5):
        _run_year(runtime, year)

    decisions = [
        event for event in runtime.events if event.event_type == DECISION_EVENT_TYPE
    ]
    assert len(decisions) == 1
    assert decisions[0].payload["policy"]["policy_version"] == 1
    assert runtime.summary()["observed_values"] == 12
    assert runtime.summary()["issued_policies"] == 1


def test_checkpoint_roundtrip_resume_is_deterministic():
    spec = _spec()
    config = _config(spec)
    continuous = NativeGovernmentRuntime(config)
    for year in range(1, 5):
        _run_year(continuous, year)

    split = NativeGovernmentRuntime(config)
    for year in range(1, 3):
        _run_year(split, year)
    encoded = json.loads(json.dumps(split.to_dict(), sort_keys=True))
    resumed = NativeGovernmentRuntime(config, encoded)
    for year in range(3, 5):
        _run_year(resumed, year)

    assert resumed.to_dict() == continuous.to_dict()
    assert resumed.checkpoint_fingerprint == continuous.checkpoint_fingerprint
    assert [event.to_dict() for event in resumed.events] == [
        event.to_dict() for event in continuous.events
    ]


def test_checkpoint_and_structural_tampering_fail_closed(tmp_path):
    spec = _spec()
    config = _config(spec)
    runtime = NativeGovernmentRuntime(config)
    _run_year(runtime, 1)
    corrupted = json.loads(json.dumps(runtime.to_dict()))
    corrupted["pending_deliveries"][0]["decision_event_id"] = "not-an-event"
    with pytest.raises(NativeGovernmentError, match="lineage/latency"):
        NativeGovernmentRuntime(config, corrupted)

    evaluation_edge = next(
        edge for edge in spec.connections
        if edge.source_mechanism == GOVERNMENT_MECHANISM_ID
        and edge.target_mechanism == "legacy.evaluation"
    )
    mutated = replace(
        spec,
        connections=tuple(
            replace(edge, latency=2) if edge == evaluation_edge else edge
            for edge in spec.connections
        ),
    )
    with pytest.raises(
        SimulatorPlanCompilationError, match="exact catalog contract"
    ):
        compile_system_spec_experiment_plan(mutated, _request(tmp_path))


def test_simulator_hooks_apply_sealed_evaluation_and_funding_policy(tmp_path):
    spec = _spec(evaluation_latency=1, funding_latency=1)
    plan = compile_system_spec_experiment_plan(spec, _request(tmp_path))
    args = parse_arguments(list(plan.runs[0].simulator_argv), create_dirs=False)
    runtime = NativeGovernmentRuntime(native_government_config_from_namespace(args))
    simulation = Simulation.__new__(Simulation)
    simulation.native_government = runtime
    simulation.paper_tracker = SimpleNamespace(accepted_papers_by_year={1: {}})
    simulation.conference_system = SimpleNamespace(
        conferences=[SimpleNamespace(acceptance_rate=0.2)]
    )

    year_one = {
        "decisions": {"total_accepted": 1, "total_rejected": 2},
        "ecosystem_metrics": {
            "funding_success_by_type": {"university": 1, "total_applications": 3}
        },
    }
    assert Simulation._start_native_government_year(simulation, 1, year_one) == ()
    Simulation._finish_native_government_year(simulation, 1, year_one)
    year_two = {}
    applied = Simulation._start_native_government_year(simulation, 2, year_two)
    rate = Simulation._apply_native_government_evaluation_policy(simulation, year_two)

    assert len(applied) == 2
    assert rate == 1.0
    assert simulation.conference_system.conferences[0].acceptance_rate == 1.0
    assert runtime.funding_award_multiplier == 2.0
    assert runtime.config.system_fingerprint == spec.fingerprint

    researcher = SimpleNamespace(funding_success_history={})
    credits = []
    simulation.weighted_funding_assignment = False
    simulation.funding_allocation_mode = "fixed"
    simulation.ecosystem = SimpleNamespace(
        get_agent_by_id=lambda _agent_id: researcher
    )
    simulation.funding_tracker = SimpleNamespace(
        record_funding_allocation=lambda *args: None
    )
    simulation._funding_application_traces = {}
    simulation._account_resources = (
        lambda _agent, amount, **_kwargs: credits.append(amount) or True
    )
    dataframe = MagicMock()
    dataframe.set_index.return_value = dataframe
    allocated = Simulation._allocate_university_funding(
        simulation,
        2,
        {"program-1": [{"applicant_id": "researcher-1"}]},
        dataframe,
    )
    assert allocated == SIMULATION_CONFIG["funding"]["academic_base_budget"] * 2
    assert credits == [allocated]


def test_checkpoint_converter_merges_native_policy_lineage(tmp_path):
    spec = _spec(evaluation_latency=1, funding_latency=1)
    config = replace(
        _config(spec),
        policy_latencies=(("evaluation", 1), ("funding", 1)),
    )
    runtime = NativeGovernmentRuntime(config)
    _run_year(runtime, 1)
    runtime.start_year(2)
    runtime.finish_year(2, _observations(2))
    checkpoint = {
        "ecosystem_data": {"agents": []},
        "paper_tracker": {"papers": []},
        "yearly_results": [{"year": 1}, {"year": 2}],
        "native_government": runtime.to_dict(),
    }
    path = tmp_path / "checkpoint.json"
    path.write_text(json.dumps(checkpoint), encoding="utf-8")
    converted = convert_artifacts(ArtifactBundle(path))
    native = [
        event for event in converted
        if event.event_type.startswith("native.government.")
    ]

    assert [event.event_id for event in native] == [
        event.event_id for event in runtime.events
    ]
    by_id = {event.event_id: event for event in converted}
    applied = [event for event in native if event.event_type == APPLICATION_EVENT_TYPE]
    assert {event.payload["target_family"] for event in applied} == {
        "evaluation",
        "funding",
    }
    for event in native:
        for source_id in event.provenance.get("source_event_ids", []):
            assert source_id in by_id
            assert by_id[source_id].sequence < event.sequence
