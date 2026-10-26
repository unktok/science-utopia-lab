from __future__ import annotations

import json
from pathlib import Path

import pytest

from utopia.replay import (
    ArtifactBundle,
    ReplayError,
    canonical_event_stream_hash,
    convert_artifacts,
    replay,
    validate_references,
)


FIXTURE = Path(__file__).parent / "fixtures" / "one_year"


def bundle() -> ArtifactBundle:
    return ArtifactBundle.discover(FIXTURE / "checkpoint_year_1.json")


def test_conversion_and_event_hashes_are_deterministic(tmp_path: Path) -> None:
    first = convert_artifacts(bundle())
    copied = tmp_path / "copied"
    copied.mkdir()
    for source in FIXTURE.iterdir():
        (copied / source.name).write_bytes(source.read_bytes())
    second = convert_artifacts(
        ArtifactBundle.discover(copied / "checkpoint_year_1.json")
    )

    assert [event.to_dict() for event in first] == [
        event.to_dict() for event in second
    ]
    assert canonical_event_stream_hash(first) == canonical_event_stream_hash(second)
    assert canonical_event_stream_hash(first) == (
        "4829fd12af64eea68ff08417737160c87376e58dd2d3ccdafdf778bb8af0ed39"
    )
    assert len({event.event_id for event in first}) == len(first)


def test_all_actor_and_artifact_references_resolve() -> None:
    events = convert_artifacts(bundle())

    assert validate_references(events) == []
    assert [event.sequence for event in events] == list(range(len(events)))


def test_llm_free_replay_projects_world_and_reconciles_resources() -> None:
    events = convert_artifacts(bundle())

    state = replay(events)

    assert state.year == 1
    assert state.completed_years == [1]
    assert state.agents["researcher-a"]["balance"] == 110
    assert state.agents["researcher-b"]["balance"] == 90
    assert state.artifacts["paper-1"]["status"] == "accept"
    assert state.artifacts["paper-1"]["reviews"] == [{
        "year": 1,
        "reviewer_id": "researcher-b",
        "score": 4,
        "justification": "The artifact is sufficient for a replay fixture.",
    }]


def test_replay_rejects_a_broken_ledger(tmp_path: Path) -> None:
    copied = tmp_path / "broken"
    copied.mkdir()
    for source in FIXTURE.iterdir():
        (copied / source.name).write_bytes(source.read_bytes())
    ledger = copied / "resource_ledger.jsonl"
    rows = [
        json.loads(line)
        for line in ledger.read_text(encoding="utf-8").splitlines()
    ]
    rows[-1]["balance_after"] = 999
    ledger.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )

    events = convert_artifacts(
        ArtifactBundle.discover(copied / "checkpoint_year_1.json")
    )
    with pytest.raises(ReplayError, match="does not equal balance_after"):
        replay(events)
