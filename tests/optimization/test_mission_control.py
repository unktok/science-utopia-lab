import copy
import hashlib
import json
from pathlib import Path
import sqlite3

from utopia.optimization.mission_control import (
    SCHEMA_VERSION,
    build_mission_control_snapshot,
    build_synthetic_mission_fixture,
    verify_snapshot_hash,
)


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "game-ui-v2/public/data/optimization-mission.snapshot.json"


def _snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def test_committed_snapshot_is_result_blind_and_held_out_locked() -> None:
    payload = _snapshot()
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["truth_status"] == "verified_snapshot"
    assert verify_snapshot_hash(payload)
    assert payload["progress"]["logical_registered"] == 27
    assert payload["progress"]["logical_capacity"] == 45
    assert payload["winner_freeze"] == {
        "status": "not_frozen", "frozen_arms": 0, "required_arms": 3,
    }
    assert payload["held_out"]["status"] == "locked"
    assert payload["held_out"]["registry_exists"] is False
    assert payload["held_out"]["registered_runs"] == 0
    assert all(arm["winner"]["design_id"] is None for arm in payload["arms"])
    assert all(
        seed["seed"] not in payload["held_out"]["seeds"]
        for arm in payload["arms"]
        for candidate in arm["candidates"]
        for seed in candidate["seeds"]
    )
    serialized = json.dumps(payload)
    assert '"observation"' not in serialized
    assert '"objective"' not in serialized


def test_snapshot_hash_detects_mutation() -> None:
    payload = _snapshot()
    payload["progress"]["status_counts"]["complete"] = 999
    assert not verify_snapshot_hash(payload)


def test_synthetic_fixture_stays_visibly_separate() -> None:
    source = _snapshot()
    synthetic = build_synthetic_mission_fixture(source)
    assert synthetic["truth_status"] == "synthetic"
    assert synthetic["source_kind"] == "synthetic_optimization_mission_fixture"
    assert "SYNTHETIC" in synthetic["disclosure"]
    assert verify_snapshot_hash(synthetic)
    assert source["truth_status"] == "verified_snapshot"
    assert source["arms"] != synthetic["arms"]


def test_hash_excludes_only_the_claimed_hash_field() -> None:
    payload = _snapshot()
    cloned = copy.deepcopy(payload)
    cloned["snapshot_hash"] = "0" * 64
    assert not verify_snapshot_hash(cloned)


def test_adapter_reads_three_registries_without_mutating_them(tmp_path: Path) -> None:
    specs = tmp_path / "research/specs"
    specs.mkdir(parents=True)
    campaign_refs = []
    for arm_index in range(3):
        campaign_id = f"arm-{arm_index}"
        campaign_ref = f"research/specs/{campaign_id}.json"
        campaign_refs.append(campaign_ref)
        campaign = {
            "id": campaign_id,
            "loss_spec": f"loss-{arm_index}.json",
            "fidelity": "tiny",
            "seed_sets": {"optimization": [11], "held_out_evaluation": [91]},
            "budget": {"max_suggestions": 1},
            "execution": {"output_root": "out", "workers": 1},
        }
        (tmp_path / campaign_ref).write_text(json.dumps(campaign), encoding="utf-8")
        revision = f"revision-{arm_index}"
        arm_root = tmp_path / "out" / campaign_id / revision
        arm_root.mkdir(parents=True)
        snapshot = {
            "revision": revision,
            "source": {"commit": "a" * 40, "tree_dirty": False},
            "campaign": campaign,
            "loss_spec": {
                "id": f"loss-{arm_index}", "version": "1", "direction": "minimize",
                "interpretation": "test-only conditioning signal", "prohibited_claims": ["winner"],
            },
            "study_template": {"execution": {"model": "fixture", "api_backend": "none", "batch_size": 1, "max_attempts": 2}},
        }
        (arm_root / "campaign-snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
        state = {
            "campaign_id": campaign_id, "revision": revision,
            "updated_utc": "2030-01-01T00:00:00+00:00",
            "suggestions": [{
                "design_id": "design-0", "status": "planned",
                "suggestion": {"proposal_index": 0, "suggestion_id": "suggestion-0", "phase": "initial"},
            }],
        }
        (arm_root / "campaign-state.json").write_text(json.dumps(state), encoding="utf-8")
        database = sqlite3.connect(arm_root / "runs.sqlite3")
        database.executescript("""
            CREATE TABLE runs(run_id TEXT, design_id TEXT, seed INTEGER, seed_role TEXT, status TEXT,
                attempt INTEGER, max_attempts INTEGER, started_utc TEXT, finished_utc TEXT, wall_seconds REAL);
            CREATE TABLE artifact_links(logical_run_id TEXT, physical_run_id TEXT);
            CREATE TABLE schedulers(scheduler_id TEXT, started_utc TEXT, finished_utc TEXT, status TEXT,
                worker_limit INTEGER, recovered_runs INTEGER);
            INSERT INTO runs VALUES('run-0','design-0',11,'optimization','planned',0,2,NULL,NULL,NULL);
        """)
        database.commit()
        database.close()
    manifest = {
        "schema": "scienceutopia.metric-conditioned-optimization-study.v1",
        "id": "fixture-study", "version": "1", "campaigns": campaign_refs,
        "common_optimization_seeds": [11], "common_held_out_evaluation_seeds": [91],
        "decision_policy": "report_only",
    }
    manifest_path = specs / "study.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    registries = sorted(tmp_path.glob("out/*/*/runs.sqlite3"))
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in registries}

    payload = build_mission_control_snapshot(tmp_path, manifest_path, observed_at_utc="2030-01-01T00:00:00+00:00")

    assert payload["progress"]["logical_registered"] == 3
    assert payload["progress"]["status_counts"]["planned"] == 3
    assert all(arm["candidates"][0]["seeds"][0]["execution_kind"] == "unmaterialized" for arm in payload["arms"])
    assert verify_snapshot_hash(payload)
    assert before == {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in registries}
