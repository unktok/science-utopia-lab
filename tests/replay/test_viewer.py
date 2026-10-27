from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from utopia.replay import ArtifactBundle, build_viewer_payload, convert_artifacts


FIXTURE = Path(__file__).parent / "fixtures" / "one_year"


def events():
    return convert_artifacts(
        ArtifactBundle.discover(FIXTURE / "checkpoint_year_1.json")
    )


def test_viewer_payload_uses_authoritative_projection_at_every_cursor() -> None:
    payload = build_viewer_payload(events(), metadata={"title": "Fixture"})

    assert payload["schema_version"] == "scienceutopia.replay-view.v1"
    assert payload["metadata"] == {"title": "Fixture"}
    assert len(payload["frames"]) == len(payload["events"]) + 1
    assert payload["frames"][0]["state"]["agents"] == {}
    assert payload["frames"][-1]["state"]["agents"]["researcher-a"]["balance"] == 110
    assert payload["frames"][-1]["state"]["artifacts"]["paper-1"]["status"] == "accept"
    assert [frame["cursor"] for frame in payload["frames"]] == list(
        range(len(payload["frames"]))
    )
    assert [frame["event_id"] for frame in payload["frames"][1:]] == [
        event["event_id"] for event in payload["events"]
    ]


def test_export_cli_is_deterministic(tmp_path: Path) -> None:
    outputs = [tmp_path / "first.json", tmp_path / "second.json"]
    command = [
        sys.executable,
        "scripts/export_game_replay.py",
        str(FIXTURE / "checkpoint_year_1.json"),
        "--title",
        "One-year fixture",
        "--source-label",
        "tests/replay/fixtures/one_year",
    ]
    for output in outputs:
        subprocess.run(
            [*command, "--output", str(output)],
            check=True,
            capture_output=True,
            text=True,
        )

    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    payload = json.loads(outputs[0].read_text(encoding="utf-8"))
    assert payload["stream_hash"] == (
        "4829fd12af64eea68ff08417737160c87376e58dd2d3ccdafdf778bb8af0ed39"
    )
