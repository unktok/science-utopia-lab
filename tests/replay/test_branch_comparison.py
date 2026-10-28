from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from utopia.replay import (
    SHARED_PREFIX_COUNT,
    branch_events,
    branch_manifest,
    branch_payload,
    canonical_event_stream_hash,
)


def test_two_futures_share_exact_canonical_prefix_then_diverge() -> None:
    left = branch_events("open-synthesis")
    right = branch_events("sealed-panel")

    assert left[:SHARED_PREFIX_COUNT] == right[:SHARED_PREFIX_COUNT]
    assert left[SHARED_PREFIX_COUNT].event_type == "policy.changed"
    assert right[SHARED_PREFIX_COUNT].event_type == "policy.changed"
    assert left[SHARED_PREFIX_COUNT].event_id != right[SHARED_PREFIX_COUNT].event_id


def test_manifest_binds_origin_streams_and_interventions() -> None:
    payloads = {
        branch_id: branch_payload(branch_id)
        for branch_id in ("open-synthesis", "sealed-panel")
    }
    manifest = branch_manifest(payloads)

    prefix = branch_events("open-synthesis")[:SHARED_PREFIX_COUNT]
    assert manifest["shared_origin"]["stream_hash"] == canonical_event_stream_hash(prefix)
    assert manifest["empirical"] is False
    for branch in manifest["branches"]:
        assert branch["stream_hash"] == payloads[branch["id"]]["stream_hash"]
        ids = {
            event["event_id"]
            for event in payloads[branch["id"]]["canonical"]["events"]
        }
        assert branch["intervention_event_id"] in ids


def test_authoritative_projections_report_branch_local_outcomes() -> None:
    left = branch_payload("open-synthesis")["projection"]["frames"][-1]["state"]
    right = branch_payload("sealed-panel")["projection"]["frames"][-1]["state"]

    assert left["artifacts"]["paper:arcology-signals"]["status"] == "accept"
    assert right["artifacts"]["paper:arcology-signals"]["status"] == "revise"
    assert left["agents"]["researcher:aya"]["balance"] == 120
    assert right["agents"]["researcher:aya"]["balance"] == 105


def test_manifest_rejects_a_payload_not_bound_to_its_canonical_stream() -> None:
    payloads = {
        branch_id: branch_payload(branch_id)
        for branch_id in ("open-synthesis", "sealed-panel")
    }
    payloads["open-synthesis"]["stream_hash"] = "0" * 64

    with pytest.raises(ValueError, match="payload stream hash does not match events"):
        branch_manifest(payloads)


def test_branch_bundle_export_is_byte_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    for output in (first, second):
        subprocess.run(
            [
                sys.executable,
                "scripts/export_game_branch_comparison.py",
                "--output-directory",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    names = sorted(path.name for path in first.iterdir())
    assert names == sorted(path.name for path in second.iterdir())
    for name in names:
        assert (first / name).read_bytes() == (second / name).read_bytes()
    manifest = json.loads((first / "intervention-branches.manifest.json").read_text())
    assert "not policy effects" in manifest["disclosure"]
