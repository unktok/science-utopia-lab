from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from utopia.replay import (
    ArtifactBundle,
    FLOW_TYPES,
    build_viewer_payload_v2,
    convert_artifacts,
    vertical_slice_events,
    vertical_slice_metadata,
    vertical_slice_presentation,
)


SAVED_FIXTURE = Path(__file__).parent / "fixtures" / "one_year"


def payload() -> dict:
    events = vertical_slice_events()
    choreography, ambient = vertical_slice_presentation(events)
    return build_viewer_payload_v2(
        events,
        metadata=vertical_slice_metadata(),
        choreography=choreography,
        ambient=ambient,
    )


def test_vertical_slice_has_three_researchers_three_institutions_and_six_flows() -> None:
    value = payload()

    assert value["schema_version"] == "scienceutopia.replay-view.v2"
    assert value["stream_hash_algorithm"] == (
        "scienceutopia.python-canonical-json-sha256.v1"
    )
    assert value["metadata"]["source_kind"] == "synthetic_contract_fixture"
    assert value["metadata"]["empirical"] is False
    assert len(value["canonical"]["entities"]["researchers"]) == 3
    assert len(value["canonical"]["entities"]["institutions"]) == 3
    flows = value["choreography"]["flows"]
    assert len(flows) == 6
    assert tuple(flow["flow_type"] for flow in flows) == FLOW_TYPES
    actions = value["choreography"]["actions"]
    assert len(actions) == 15
    assert {action["actor_entity_id"] for action in actions} == {
        "researcher:aya", "researcher:mino", "researcher:sol",
    }


def test_all_derived_visuals_trace_to_canonical_events_and_ambient_never_does() -> None:
    value = payload()
    event_ids = {event["event_id"] for event in value["canonical"]["events"]}

    for group in ("placements", "flows", "actions", "camera_cues"):
        for record in value["choreography"][group]:
            assert record["truth_status"] == "derived"
            assert record["derived_from_event_ids"]
            assert set(record["derived_from_event_ids"]) <= event_ids
            assert record["derivation_version"] == value["derivation_version"]
            assert record["logical_timestamp_ms"] >= 0
            assert record["duration_ms"] >= 0
            assert "causal_parent_id" in record

    for group in ("actors", "effects"):
        for record in value["ambient"][group]:
            assert record["truth_status"] == "ambient"
            assert record["derived_from_event_ids"] == []


def test_projection_is_authoritative_and_reconciles_fixture_resources() -> None:
    final = payload()["projection"]["frames"][-1]["state"]

    assert final["agents"]["researcher:aya"]["balance"] == 120
    assert final["agents"]["researcher:mino"]["balance"] == 100
    assert final["agents"]["researcher:sol"]["balance"] == 100
    assert final["artifacts"]["paper:arcology-signals"]["status"] == "accept"
    assert final["completed_years"] == [1]


def test_v2_rejects_a_derived_flow_without_canonical_evidence() -> None:
    events = vertical_slice_events()
    choreography, ambient = vertical_slice_presentation(events)
    choreography["flows"][0]["derived_from_event_ids"] = []

    with pytest.raises(ValueError, match="derived record has no source events"):
        build_viewer_payload_v2(
            events,
            choreography=choreography,
            ambient=ambient,
        )


def test_v2_rejects_an_action_for_a_non_researcher() -> None:
    events = vertical_slice_events()
    choreography, ambient = vertical_slice_presentation(events)
    choreography["actions"][0]["actor_entity_id"] = choreography["placements"][0][
        "entity_id"
    ]

    with pytest.raises(ValueError, match="Unknown action actor"):
        build_viewer_payload_v2(
            events,
            choreography=choreography,
            ambient=ambient,
        )


def test_real_saved_export_does_not_invent_missing_visual_flows() -> None:
    events = convert_artifacts(
        ArtifactBundle.discover(SAVED_FIXTURE / "checkpoint_year_1.json")
    )

    value = build_viewer_payload_v2(events)

    assert value["metadata"]["source_kind"] == "saved_simulation_artifact"
    assert value["metadata"]["empirical"] is True
    assert value["choreography"]["flows"] == []
    assert value["choreography"]["actions"] == []
    assert value["ambient"]["actors"] == []


def test_vertical_slice_cli_is_deterministic_and_self_disclosing(tmp_path: Path) -> None:
    outputs = [tmp_path / "first.json", tmp_path / "second.json"]
    for output in outputs:
        subprocess.run(
            [
                sys.executable,
                "scripts/export_game_replay.py",
                "--vertical-slice-fixture",
                "--output",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    value = json.loads(outputs[0].read_text(encoding="utf-8"))
    assert value["metadata"]["empirical"] is False
    assert "not an experimental run" in value["metadata"]["disclosure"]
