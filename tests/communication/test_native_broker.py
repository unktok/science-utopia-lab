from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from utopia.arguments import parse_arguments
from utopia.communication.native import (
    BROKER_MECHANISM_ID,
    MESSAGE_EVENT_TYPE,
    RECEIVER_EVENT_TYPE,
    SOURCE_EVENT_TYPE,
    NativeCommunicationBroker,
    NativeCommunicationConfig,
    NativeCommunicationError,
    native_communication_system_spec,
    native_config_from_namespace,
    validate_native_communication_events,
)
from utopia.optimization.design_space import load_candidate, load_space
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
from utopia.system.production import KNOWLEDGE_BROADCAST, KNOWLEDGE_DIGEST
from utopia.system.production.communication import DIFFUSION_STATE_SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[2]


def _base_spec():
    return legacy_candidate_to_system_spec(
        load_space(ROOT / "research/specs/design-space-v1.json"),
        load_candidate(ROOT / "research/specs/example-design-v0.json"),
    )


def _request(tmp_path: Path):
    return SimulatorPlanRequest(
        campaign_id="synthetic-native-communication-v1",
        seed_role="synthetic-development",
        seeds=(1201,),
        model=SimulatorModelSpec(
            model="qwen3:8b",
            api_backend="ollama",
            endpoint="http://127.0.0.1:11434/v1",
            batch_size=2,
        ),
        fidelity=SimulatorFidelitySpec(
            fidelity_id="synthetic-two-year",
            experiment_stage="smoke",
            num_years=2,
            num_institutions=2,
            num_conferences=1,
        ),
        output_root=str(tmp_path / "outputs"),
        data_cache_dir=str(tmp_path / "cache"),
        compiler_source_commit="b" * 40,
        compiler_tree_dirty=False,
        source_locator="synthetic:native-communication-fixture",
    )


def _paper(paper_id: str, year: int, author: str = "researcher-1"):
    return {
        "id": paper_id,
        "title": f"Synthetic output {paper_id}",
        "abstract": "Deterministic engineering fixture.",
        "author_id": author,
        "author_type": "university",
        "year": year,
        "conference": "SyntheticConf",
        "status": "accept",
        "topics": ["systems"],
        "tags": [],
        "project_start_year": year,
        "project_end_year": year,
        "maturity": 1,
        "review_history": [{
            "conference": "SyntheticConf",
            "year": year,
            "score": 4,
            "reviews": [],
            "decision": "accept",
        }],
    }


def test_default_off_has_no_native_config_or_plan_arguments(tmp_path):
    parsed = parse_arguments(
        ["--experiment_name", "exploration_vs_exploitation"],
        create_dirs=False,
    )
    assert native_config_from_namespace(parsed) is None

    plan = compile_system_spec_experiment_plan(_base_spec(), _request(tmp_path))
    argv = plan.runs[0].simulator_argv
    assert "--communication-broker-mode" not in argv
    assert "--communication-system-fingerprint" not in argv
    assert not (tmp_path / "outputs").exists()
    assert not (tmp_path / "cache").exists()


@pytest.mark.parametrize(
    ("mode", "implementation"),
    (("broadcast", KNOWLEDGE_BROADCAST), ("digest", KNOWLEDGE_DIGEST)),
)
def test_system_spec_compiles_through_sealed_plan_to_native_config(
    tmp_path, mode, implementation
):
    spec = native_communication_system_spec(
        _base_spec(), mode=mode, digest_size=3, latency=2
    )
    plan = compile_system_spec_experiment_plan(spec, _request(tmp_path))
    validate_simulator_experiment_plan(plan)

    run = plan.runs[0]
    parsed = parse_arguments(list(run.simulator_argv), create_dirs=False)
    config = native_config_from_namespace(parsed)
    assert config is not None
    assert config.mode == mode
    assert config.digest_size == 3
    assert config.latency == 2
    assert config.system_fingerprint == spec.fingerprint
    mapping = next(
        item for item in plan.mechanism_mappings
        if item.mechanism_id == BROKER_MECHANISM_ID
    )
    assert mapping.implementation == implementation
    assert {
        item.cli_flag: item.value for item in mapping.parameter_bindings
    } == {
        "--communication-broker-mode": mode,
        "--communication-digest-size": 3,
        "--communication-latency": 2,
    }


def test_native_broadcast_preserves_source_receiver_lineage_and_latency(tmp_path):
    spec = native_communication_system_spec(
        _base_spec(), mode="broadcast", latency=1
    )
    plan = compile_system_spec_experiment_plan(spec, _request(tmp_path))
    args = parse_arguments(list(plan.runs[0].simulator_argv), create_dirs=False)
    broker = NativeCommunicationBroker(native_config_from_namespace(args))

    first = broker.step(1, [_paper("paper-1", 1)])
    second = broker.step(2, [])
    assert [event.event_type for event in first] == [
        SOURCE_EVENT_TYPE, MESSAGE_EVENT_TYPE
    ]
    assert [event.event_type for event in second] == [RECEIVER_EVENT_TYPE]
    source, message, receipt = broker.events
    assert message.provenance["source_event_ids"] == [source.event_id]
    assert message.provenance["production_adapter"] == KNOWLEDGE_BROADCAST
    assert receipt.provenance["source_event_ids"] == [message.event_id]
    assert receipt.payload["emitted_year"] == 1
    assert receipt.payload["received_year"] == 2
    assert receipt.payload["latency"] == 1
    assert all(
        event.event_type.startswith("native.communication.") for event in broker.events
    )
    assert all("citation" not in event.event_type for event in broker.events)
    validate_native_communication_events(
        broker.events, system_fingerprint=spec.fingerprint
    )
    assert broker.to_dict()["production_broker_state"]["schema_version"] == (
        DIFFUSION_STATE_SCHEMA_VERSION
    )


def test_digest_checkpoint_round_trip_resume_is_deterministic(tmp_path):
    spec = native_communication_system_spec(
        _base_spec(), mode="digest", digest_size=2, latency=1
    )
    plan = compile_system_spec_experiment_plan(spec, _request(tmp_path))
    args = parse_arguments(list(plan.runs[0].simulator_argv), create_dirs=False)
    config = native_config_from_namespace(args)

    continuous = NativeCommunicationBroker(config)
    continuous.step(1, [_paper("paper-1", 1)])
    continuous.step(2, [_paper("paper-2", 2)])
    continuous.step(3, [])

    split = NativeCommunicationBroker(config)
    split.step(1, [_paper("paper-1", 1)])
    encoded = json.loads(json.dumps(split.to_dict(), sort_keys=True))
    resumed = NativeCommunicationBroker(config, encoded)
    resumed.step(2, [_paper("paper-2", 2)])
    resumed.step(3, [])

    assert resumed.to_dict() == continuous.to_dict()
    assert resumed.checkpoint_fingerprint == continuous.checkpoint_fingerprint
    assert [event.to_dict() for event in resumed.events] == [
        event.to_dict() for event in continuous.events
    ]
    assert resumed.summary()["emitted_messages"] == 1
    assert resumed.summary()["received_messages"] == 1


def test_simulation_year_hook_executes_sealed_system_spec_only_when_enabled(tmp_path):
    spec = native_communication_system_spec(
        _base_spec(), mode="broadcast", latency=0
    )
    plan = compile_system_spec_experiment_plan(spec, _request(tmp_path))
    args = parse_arguments(list(plan.runs[0].simulator_argv), create_dirs=False)
    config = native_config_from_namespace(args)
    simulation = Simulation.__new__(Simulation)
    simulation.native_communication = NativeCommunicationBroker(config)
    simulation.paper_tracker = SimpleNamespace(
        accepted_papers_by_year={1: {"paper-1": SimpleNamespace(**_paper("paper-1", 1))}}
    )
    year_results = {}
    events = Simulation._run_native_communication(simulation, 1, year_results)
    assert [event.event_type for event in events] == [
        SOURCE_EVENT_TYPE, MESSAGE_EVENT_TYPE, RECEIVER_EVENT_TYPE
    ]
    assert simulation.native_communication.config.system_fingerprint == spec.fingerprint
    assert year_results["native_communication"]["received_messages"] == 1

    simulation.native_communication = None
    untouched = {}
    assert Simulation._run_native_communication(simulation, 2, untouched) == ()
    assert untouched == {}


def test_checkpoint_and_structural_mismatches_fail_closed(tmp_path):
    spec = native_communication_system_spec(
        _base_spec(), mode="broadcast", latency=1
    )
    plan = compile_system_spec_experiment_plan(spec, _request(tmp_path))
    args = parse_arguments(list(plan.runs[0].simulator_argv), create_dirs=False)
    config = native_config_from_namespace(args)
    broker = NativeCommunicationBroker(config)
    broker.step(1, [_paper("paper-1", 1)])

    changed = replace(config, system_fingerprint="d" * 64)
    with pytest.raises(NativeCommunicationError, match="checkpoint config changed"):
        NativeCommunicationBroker(changed, broker.to_dict())

    corrupted = json.loads(json.dumps(broker.to_dict()))
    corrupted["pending_deliveries"][0]["message_event_id"] = (
        corrupted["source_event_ids"][0]
    )
    with pytest.raises(NativeCommunicationError, match="pending message event"):
        NativeCommunicationBroker(config, corrupted)

    receiver_edge = spec.connections[-1]
    mutated = replace(
        spec,
        connections=spec.connections[:-1] + (replace(receiver_edge, latency=2),),
    )
    with pytest.raises(
        SimulatorPlanCompilationError, match="edges or latency changed"
    ):
        compile_system_spec_experiment_plan(mutated, _request(tmp_path))


def test_checkpoint_converter_emits_typed_native_canonical_events(tmp_path):
    config = NativeCommunicationConfig(
        mode="broadcast",
        digest_size=2,
        latency=1,
        receiver_role="research-community",
        system_fingerprint="e" * 64,
    )
    broker = NativeCommunicationBroker(config)
    paper = _paper("paper-1", 1)
    broker.step(1, [paper])
    broker.step(2, [])
    checkpoint = {
        "ecosystem_data": {
            "agents": [{
                "id": "researcher-1",
                "type": "university",
                "university_name": "Synthetic University",
                "resources": 100,
                "is_active": True,
            }]
        },
        "paper_tracker": {"papers": [paper]},
        "yearly_results": [{"year": 1}, {"year": 2}],
        "native_communication": broker.to_dict(),
    }
    path = tmp_path / "checkpoint.json"
    path.write_text(json.dumps(checkpoint), encoding="utf-8")
    converted = convert_artifacts(ArtifactBundle(path))
    native = [
        event for event in converted
        if event.event_type.startswith("native.communication.")
    ]

    assert [event.event_id for event in native] == [
        event.event_id for event in broker.events
    ]
    by_id = {event.event_id: event for event in converted}
    for event in native:
        for source_id in event.provenance.get("source_event_ids", []):
            assert source_id in by_id
            assert by_id[source_id].sequence < event.sequence
    assert native[-1].payload["receiver_role"] == "research-community"
