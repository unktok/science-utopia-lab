from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import shutil

import pytest

from utopia.system import (
    DeterministicGraphRunner,
    GraphCheckpoint,
    GraphRuntimeError,
    MechanismRegistry,
)
from utopia.system.production import (
    load_verified_simulator_campaign,
    parse_simulator_event_batch,
    register_simulator_workload_bridge,
    simulator_bridge_system_spec,
    validate_delivered_event_batch,
)


FIXTURE = Path(__file__).parents[1] / "replay" / "fixtures" / "one_year"
COMMIT = "0" * 40


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    project = tmp_path / "project"
    campaign = tmp_path / "campaign"
    run_id = "completed-run-s7"
    suggestion_id = "suggestion-a"
    seed = 7
    result = {
        "campaign": {
            "id": "completed-campaign",
            "revision": "abc123",
            "source_commit": COMMIT,
            "completed_utc": "2026-10-27T00:00:00Z",
        },
        "suggestions": [
            {
                "suggestion_id": suggestion_id,
                "status": "complete",
                "runs": [{"run_id": run_id, "seed": seed}],
            }
        ],
    }
    result_path = project / "research/results/completed.json"
    _write(result_path, result)
    files: dict[str, dict[str, str]] = {}
    generated = {
        "run_manifest": (
            "runs/docs/run_manifest.json",
            {
                "status": "complete",
                "git_commit": COMMIT,
                "git_dirty_files": "",
                "args": {"run_id": run_id, "seed": seed},
            },
        ),
        "integrity": (
            "runs/docs/integrity_checks.json",
            [{"year": 1, "passed": True, "failures": []}],
        ),
    }
    for name, (relative, value) in generated.items():
        path = campaign / relative
        _write(path, value)
        files[name] = {"path": relative, "sha256": _sha(path)}
    for name, source_name in (
        ("checkpoint", "checkpoint_year_1.json"),
        ("resource_ledger", "resource_ledger.jsonl"),
        ("resource_balances", "resource_balances.jsonl"),
    ):
        relative = f"runs/checkpoints/{source_name}"
        path = campaign / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURE / source_name, path)
        files[name] = {"path": relative, "sha256": _sha(path)}
    source = {
        "schema_version": "scienceutopia.game-campaign-source.v1",
        "status": "completed",
        "campaign_id": "completed-campaign",
        "campaign_revision": "abc123",
        "source_commit": COMMIT,
        "protocol_tag": "protocol/test",
        "claim_boundary": "Completed test artifact; no policy claim.",
        "campaign_result": {
            "path": "research/results/completed.json",
            "sha256": _sha(result_path),
        },
        "run": {
            "id": run_id,
            "suggestion_id": suggestion_id,
            "seed": seed,
            "status": "complete",
        },
        "files": files,
    }
    source_path = project / "source.json"
    _write(source_path, source)
    return source_path, campaign, project


def _bundle(tmp_path: Path):
    source, campaign, project = _source_tree(tmp_path)
    return load_verified_simulator_campaign(source, campaign, project)


def _registry(bundle) -> MechanismRegistry:
    registry = MechanismRegistry()
    register_simulator_workload_bridge(registry, bundle)
    return registry


def test_loader_binds_verified_checkpoint_campaign_and_stream(tmp_path: Path) -> None:
    source, campaign, project = _source_tree(tmp_path)
    bundle = load_verified_simulator_campaign(source, campaign, project)

    assert bundle.campaign_id == "completed-campaign"
    assert bundle.campaign_revision == "abc123"
    assert bundle.run_id == "completed-run-s7"
    assert bundle.source_commit == COMMIT
    assert bundle.seed == 7
    assert len(bundle.events) > 10
    assert [event.sequence for event in bundle.events] == list(range(len(bundle.events)))
    assert len(bundle.fingerprint) == 64
    assert bundle.identity_dict()["source_file_sha256"]["checkpoint"]

    changed_source = project / "changed-source.json"
    value = json.loads(source.read_text(encoding="utf-8"))
    value["claim_boundary"] = "Same run, changed source manifest identity."
    _write(changed_source, value)
    changed = load_verified_simulator_campaign(changed_source, campaign, project)
    assert changed.event_stream_hash == bundle.event_stream_hash
    assert changed.fingerprint != bundle.fingerprint

    checkpoint = campaign / value["files"]["checkpoint"]["path"]
    checkpoint.write_text(
        checkpoint.read_text(encoding="utf-8") + " ", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="checkpoint hash mismatch"):
        load_verified_simulator_campaign(source, campaign, project)


def test_bridge_fans_real_events_into_five_mechanism_families(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    batch_size = 4
    spec = simulator_bridge_system_spec(bundle, batch_size=batch_size)
    periods = math.ceil(len(bundle.events) / batch_size) + 2
    run = DeterministicGraphRunner(spec, _registry(bundle)).run(periods=periods)

    batch_count = math.ceil(len(bundle.events) / batch_size)
    bridge_events = [
        event
        for event in run.events
        if event.event_type == "simulator.workload_batch_emitted"
    ]
    receiver_events = [
        event
        for event in run.events
        if event.event_type == "simulator.workload_batch_received"
    ]
    assert len(bridge_events) == batch_count
    assert len(receiver_events) == batch_count * 5
    assert run.pending_deliveries == 0
    assert {
        event.provenance["mechanism_family"] for event in receiver_events
    } == {"evaluation", "publication", "funding", "governance", "communication"}

    graph_event_by_id = {event.event_id: event for event in run.events}
    assert all(
        {
            graph_event_by_id[event_id].event_type
            for event_id in event.provenance["input_event_ids"]
        }
        == {"simulator.workload_batch_emitted"}
        for event in receiver_events
    )
    assert {
        event_id
        for event in bridge_events
        for event_id in event.payload["source_event_ids"]
    } == {event.event_id for event in bundle.events}

    for family in (
        "evaluation",
        "publication",
        "funding",
        "governance",
        "communication",
    ):
        state = run.checkpoint.mechanism_states[f"{family}-simulator-consumer"]
        assert state["next_source_index"] == len(bundle.events)
        assert len(state["received_batch_ids"]) == batch_count
        assert sum(state["event_type_counts"].values()) == len(bundle.events)


def test_bridge_checkpoint_resume_is_deterministic_and_system_bound(
    tmp_path: Path,
) -> None:
    bundle = _bundle(tmp_path)
    batch_size = 4
    spec = simulator_bridge_system_spec(bundle, batch_size=batch_size)
    periods = math.ceil(len(bundle.events) / batch_size) + 2
    uninterrupted = DeterministicGraphRunner(spec, _registry(bundle)).run(
        periods=periods
    )
    first = DeterministicGraphRunner(spec, _registry(bundle)).run(periods=2)
    checkpoint = GraphCheckpoint.from_dict(
        json.loads(json.dumps(first.checkpoint.to_dict(), sort_keys=True))
    )
    resumed = DeterministicGraphRunner(spec, _registry(bundle)).run(
        periods=periods - 2,
        checkpoint=checkpoint,
    )

    assert [event.to_dict() for event in (*first.events, *resumed.events)] == [
        event.to_dict() for event in uninterrupted.events
    ]
    assert resumed.checkpoint.to_dict() == uninterrupted.checkpoint.to_dict()

    changed = simulator_bridge_system_spec(
        bundle,
        batch_size=batch_size,
        latencies={
            "evaluation": 0,
            "publication": 1,
            "funding": 1,
            "governance": 1,
            "communication": 0,
        },
    )
    assert changed.fingerprint != spec.fingerprint
    with pytest.raises(GraphRuntimeError, match="fingerprint does not match"):
        DeterministicGraphRunner(changed, _registry(bundle)).run(
            periods=1,
            checkpoint=checkpoint,
        )


def test_bridge_and_batch_contracts_fail_closed(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    spec = simulator_bridge_system_spec(
        bundle,
        batch_size=4,
        latencies={family: 2 for family in (
            "evaluation",
            "publication",
            "funding",
            "governance",
            "communication",
        )},
    )
    first = DeterministicGraphRunner(spec, _registry(bundle)).run(periods=1)
    delivered = first.checkpoint.queued_deliveries[0].value
    batch = parse_simulator_event_batch(delivered.payload)

    assert validate_delivered_event_batch(
        delivered,
        system_fingerprint=spec.fingerprint,
        campaign_fingerprint=bundle.fingerprint,
        event_stream_hash=bundle.event_stream_hash,
        source_bridge_id="simulator-bridge",
    ) == batch

    unknown = {**batch, "unknown": True}
    with pytest.raises(GraphRuntimeError, match="fields do not match"):
        parse_simulator_event_batch(unknown)
    tampered_event = copy.deepcopy(batch)
    tampered_event["source_events"][0]["payload"]["tampered"] = True
    with pytest.raises(GraphRuntimeError, match="identity mismatch"):
        parse_simulator_event_batch(tampered_event)
    with pytest.raises(GraphRuntimeError, match="different target system"):
        validate_delivered_event_batch(
            delivered,
            system_fingerprint="b" * 64,
            campaign_fingerprint=bundle.fingerprint,
            event_stream_hash=bundle.event_stream_hash,
            source_bridge_id="simulator-bridge",
        )
    with pytest.raises(GraphRuntimeError, match="different campaign"):
        validate_delivered_event_batch(
            delivered,
            system_fingerprint=spec.fingerprint,
            campaign_fingerprint="b" * 64,
            event_stream_hash=bundle.event_stream_hash,
            source_bridge_id="simulator-bridge",
        )
    with pytest.raises(GraphRuntimeError, match="graph-local event lineage"):
        validate_delivered_event_batch(
            replace(delivered, lineage_event_ids=()),
            system_fingerprint=spec.fingerprint,
            campaign_fingerprint=bundle.fingerprint,
            event_stream_hash=bundle.event_stream_hash,
            source_bridge_id="simulator-bridge",
        )

    bad_bridge = replace(
        spec.mechanisms[0],
        parameters={
            **dict(spec.mechanisms[0].parameters),
            "campaign_fingerprint": "b" * 64,
        },
    )
    mismatched_spec = replace(spec, mechanisms=(bad_bridge, *spec.mechanisms[1:]))
    with pytest.raises(GraphRuntimeError, match="campaign fingerprint mismatch"):
        DeterministicGraphRunner(mismatched_spec, _registry(bundle)).run(periods=1)
