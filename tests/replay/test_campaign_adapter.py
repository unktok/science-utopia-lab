from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from utopia.replay.campaign_adapter import export_campaign_bundle, validate_portable_bundle


FIXTURE = Path(__file__).parent / "fixtures" / "one_year"
COMMITTED = Path("game-ui-v2/public/data/completed-campaign.replay.json")
COMMIT = "0" * 40


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    project, campaign = tmp_path / "project", tmp_path / "campaign"
    run_id, suggestion_id, seed = "completed-run-s7", "suggestion-a", 7
    result = {
        "campaign": {"id": "completed-campaign", "revision": "abc123", "source_commit": COMMIT, "completed_utc": "2026-10-27T00:00:00Z"},
        "suggestions": [{"suggestion_id": suggestion_id, "status": "complete", "runs": [{"run_id": run_id, "seed": seed}]}],
    }
    result_path = project / "research/results/completed.json"
    _write(result_path, result)
    files: dict[str, dict[str, str]] = {}
    generated = {
        "run_manifest": ("runs/docs/run_manifest.json", {"status": "complete", "git_commit": COMMIT, "git_dirty_files": "", "args": {"run_id": run_id, "seed": seed}}),
        "integrity": ("runs/docs/integrity_checks.json", [{"year": 1, "passed": True, "failures": []}]),
    }
    for name, (relative, value) in generated.items():
        path = campaign / relative
        _write(path, value)
        files[name] = {"path": relative, "sha256": _sha(path)}
    for name, source_name in (("checkpoint", "checkpoint_year_1.json"), ("resource_ledger", "resource_ledger.jsonl"), ("resource_balances", "resource_balances.jsonl")):
        relative = f"runs/checkpoints/{source_name}"
        path = campaign / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURE / source_name, path)
        files[name] = {"path": relative, "sha256": _sha(path)}
    source = {
        "schema_version": "scienceutopia.game-campaign-source.v1",
        "status": "completed", "campaign_id": "completed-campaign", "campaign_revision": "abc123",
        "source_commit": COMMIT, "protocol_tag": "protocol/test", "claim_boundary": "Completed test artifact; no policy claim.",
        "campaign_result": {"path": "research/results/completed.json", "sha256": _sha(result_path)},
        "run": {"id": run_id, "suggestion_id": suggestion_id, "seed": seed, "status": "complete"},
        "files": files,
    }
    source_path = project / "source.json"
    _write(source_path, source)
    return source_path, campaign, project


def test_committed_bundle_is_real_campaign_projection_not_raw_state() -> None:
    payload = json.loads(COMMITTED.read_text(encoding="utf-8"))
    validate_portable_bundle(payload)
    assert payload["metadata"]["source_kind"] == "verified_commit_pinned_campaign_run"
    assert payload["metadata"]["source_commit"] == "0b733df425405f5e2eeb953cff2a7288f13f5af9"
    assert payload["metadata"]["campaign_revision"] == "9a10029807d5"
    assert len(payload["canonical"]["events"]) == 71
    assert len(payload["projection"]["frames"]) == 72
    assert len(payload["choreography"]["actions"]) == 20
    assert len(payload["choreography"]["chapters"]) == 9
    assert len(payload["choreography"]["workflow_nodes"]) == 4
    assert len(payload["choreography"]["epistemic_flows"]) == 20
    epistemic_kinds = [flow["flow_kind"] for flow in payload["choreography"]["epistemic_flows"]]
    assert {kind: epistemic_kinds.count(kind) for kind in set(epistemic_kinds)} == {
        "application": 10, "award": 2, "decision": 2, "manuscript": 2, "review": 4,
    }
    assert payload["choreography"]["time_compression"]["kind"] == "deterministic-stage-compression"
    action_types = [action["action_type"] for action in payload["choreography"]["actions"]]
    assert {kind: action_types.count(kind) for kind in set(action_types)} == {
        "move": 12, "receive": 2, "review": 4, "write": 2,
    }
    assert all(
        isinstance(point[axis], int)
        for action in payload["choreography"]["actions"]
        for point in action["path"]
        for axis in ("x", "y")
    )
    fact_times = [fact["logical_timestamp_ms"] for fact in payload["canonical"]["facts"]]
    assert fact_times == sorted(fact_times)
    assert [frame["logical_timestamp_ms"] for frame in payload["projection"]["frames"][1:]] == fact_times
    assert "paper_tracker" not in payload
    assert "ecosystem_data" not in payload


def test_verified_export_is_deterministic_and_projection_reconciles(tmp_path: Path) -> None:
    source, campaign, project = source_tree(tmp_path)
    first = export_campaign_bundle(source, campaign, project)
    second = export_campaign_bundle(source, campaign, project)
    assert first == second
    validate_portable_bundle(first)
    assert first["metadata"]["source_file_sha256"]["checkpoint"]


def test_export_rejects_a_tampered_source_file(tmp_path: Path) -> None:
    source, campaign, project = source_tree(tmp_path)
    checkpoint = campaign / "runs/checkpoints/checkpoint_year_1.json"
    checkpoint.write_text(checkpoint.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="checkpoint hash mismatch"):
        export_campaign_bundle(source, campaign, project)


def test_export_rejects_a_nonterminal_campaign(tmp_path: Path) -> None:
    source, campaign, project = source_tree(tmp_path)
    value = json.loads(source.read_text(encoding="utf-8"))
    value["status"] = "running"
    _write(source, value)
    with pytest.raises(ValueError, match="must both be complete"):
        export_campaign_bundle(source, campaign, project)


def test_portable_validation_rejects_projection_tampering() -> None:
    payload = json.loads(COMMITTED.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(payload)
    tampered["projection"]["frames"][-1]["state"]["completed_years"] = []
    with pytest.raises(ValueError, match="authoritative projection mismatch"):
        validate_portable_bundle(tampered)


def test_portable_validation_rejects_projection_timing_tampering() -> None:
    payload = json.loads(COMMITTED.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(payload)
    tampered["projection"]["frames"][1]["logical_timestamp_ms"] = 99
    with pytest.raises(ValueError, match="authoritative projection timestamp mismatch"):
        validate_portable_bundle(tampered)


def test_portable_validation_rejects_epistemic_semantic_tampering() -> None:
    payload = json.loads(COMMITTED.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(payload)
    tampered["choreography"]["epistemic_flows"][0]["flow_kind"] = "award"
    with pytest.raises(ValueError, match="epistemic flow semantic mismatch"):
        validate_portable_bundle(tampered)


def test_portable_validation_rejects_unknown_epistemic_source() -> None:
    payload = json.loads(COMMITTED.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(payload)
    tampered["choreography"]["epistemic_flows"][0]["derived_from_event_ids"] = ["missing"]
    with pytest.raises(ValueError, match="unknown canonical source"):
        validate_portable_bundle(tampered)
