import hashlib
import json
from pathlib import Path

import pytest

from scripts.reports.generative_lab import assert_reproduction, load_run
from utopia.system import SystemSpec
from utopia.system.program_world import evaluate_program_system
from utopia.system.programs import digest

ROOT = Path(__file__).resolve().parents[2]


def test_published_view_recomputes_from_frozen_programs_and_worlds_offline():
    envelope = json.loads((ROOT / "game-ui-v2/public/data/generative-lab-v1.json").read_text())
    assert hashlib.sha256(envelope["payload_json"].encode()).hexdigest() == envelope["payload_sha256"]
    payload = json.loads(envelope["payload_json"])
    assert payload["source"]["dirty_development"] is False
    for arm in payload["arms"]:
        for result in arm["systems"]:
            spec = SystemSpec.from_dict(result["system_spec"])
            assert spec.fingerprint == result["system_fingerprint"]
            recomputed = evaluate_program_system(spec, payload["worlds"], arm["loss_spec"],
                                                periods=len(result["frames"]), record=True)
            assert recomputed["loss"] == pytest.approx(result["loss"], abs=1e-12)
            assert recomputed["runs"][0]["history"] == result["frames"]
            assert digest(result["events"]) == result["event_stream_sha256"]


def test_reproduction_verifier_does_not_ignore_a_changed_world():
    original = {"arms": {}, "worlds": [{"quality": [0.5]}]}
    repeated = {"arms": {}, "worlds": [{"quality": [0.6]}]}
    with pytest.raises(ValueError, match="worlds"):
        assert_reproduction(original, repeated)


def test_run_verifier_requires_both_hash_bound_artifacts(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({
        "schema": "scienceutopia.generative-lab-manifest.v1", "files": {},
    }))
    with pytest.raises(ValueError, match="exactly"):
        load_run(tmp_path)


def test_run_verifier_rejects_tampered_report_before_parsing_it(tmp_path):
    (tmp_path / "report.json").write_text("changed")
    (tmp_path / "manifest.json").write_text(json.dumps({
        "schema": "scienceutopia.generative-lab-manifest.v1",
        "files": {"report.json": "0" * 64, "viewer.json": "0" * 64},
    }))
    with pytest.raises(ValueError, match="hash mismatch"):
        load_run(tmp_path)
