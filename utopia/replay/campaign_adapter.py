"""Fail-closed export of a commit-pinned campaign run to replay-view v2.

Raw simulator state is accepted only on this Python boundary. The browser gets
canonical events, authoritative projector frames, deterministic presentation
records, and source hashes; it never receives the checkpoint document.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import struct
from typing import Any, Mapping, Sequence

from .converter import ArtifactBundle, convert_artifacts
from .events import EventEnvelope, canonical_event_stream_hash
from .projector import replay
from .viewer import DERIVATION_VERSION_V2, build_viewer_payload_v2


SOURCE_SCHEMA = "scienceutopia.game-campaign-source.v1"
PORTABLE_SCHEMA = "scienceutopia.replay-view.v2"
SHA256 = re.compile(r"[0-9a-f]{64}")
GIT_COMMIT = re.compile(r"[0-9a-f]{40}")


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _web_json_value(value: Any) -> Any:
    """Encode JSON numbers by browser-visible IEEE-754 bits."""

    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        number = float(value)
        if isinstance(value, int) and abs(value) > 2**53 - 1:
            raise ValueError("web stream contains an integer outside JavaScript's safe range")
        if not (-float("inf") < number < float("inf")):
            raise ValueError("web stream contains a non-finite number")
        return {"$number_f64": struct.pack(">d", number).hex()}
    if isinstance(value, list):
        return [_web_json_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _web_json_value(item) for key, item in value.items()}
    return value


def web_event_stream_hash(event_rows: Sequence[Mapping[str, Any]]) -> str:
    text = json.dumps(
        _web_json_value(list(event_rows)), ensure_ascii=False, allow_nan=False,
        separators=(",", ":"), sort_keys=True,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _checked_file(root: Path, spec: Any, label: str) -> Path:
    row = _object(spec, label)
    relative = Path(str(row.get("path", "")))
    expected = str(row.get("sha256", ""))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{label}.path must stay below the declared root")
    if SHA256.fullmatch(expected) is None:
        raise ValueError(f"{label}.sha256 must be a lowercase SHA-256")
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"{label}.path escapes the declared root") from error
    if not path.is_file():
        raise ValueError(f"{label} is missing: {relative}")
    actual = _sha256(path)
    if actual != expected:
        raise ValueError(f"{label} hash mismatch: expected {expected}, got {actual}")
    return path


def _trace(
    event: EventEnvelope,
    *,
    event_count: int,
    duration: int,
    label: str,
    kind: str,
    logical_timestamp_ms: int | None = None,
) -> dict[str, Any]:
    return {
        "truth_status": "derived",
        "derived_from_event_ids": [event.event_id],
        "derivation_version": DERIVATION_VERSION_V2,
        "logical_timestamp_ms": (
            _logical_time(event.sequence, event_count)
            if logical_timestamp_ms is None else logical_timestamp_ms
        ),
        "duration_ms": duration,
        "causal_parent_id": None,
        "label": label,
        "kind": kind,
    }


def _logical_time(sequence: int, count: int) -> int:
    return round(sequence * 48_000 / max(1, count - 1))


STAGE_WINDOWS = {
    "register": (0, 3_000),
    "submit": (6_000, 9_000),
    "produce": (10_500, 14_000),
    "review": (17_000, 26_000),
    "decide": (29_000, 32_000),
    "apply": (34_000, 39_000),
    "fund": (41_000, 43_000),
    "report": (45_000, 47_000),
    "complete": (48_000, 48_000),
}


def _cinematic_stage(event: EventEnvelope) -> str:
    if event.event_type == "agent.registered":
        return "register"
    if event.event_type == "paper.submitted":
        return "submit"
    if event.event_type == "review.completed":
        return "review"
    if event.event_type == "paper.decided":
        return "decide"
    if event.event_type == "resource.balance_reported":
        return "report"
    if event.event_type == "year.completed":
        return "complete"
    if event.event_type == "resource.changed":
        category = event.payload.get("category")
        if category in {"grant_income", "industry_income"}:
            return "fund"
        if category == "funding_application_cost":
            return "apply"
        return "produce"
    raise ValueError(f"No cinematic stage for canonical event {event.event_type}")


def cinematic_timestamps(events: Sequence[EventEnvelope]) -> dict[str, int]:
    """Compress dense accounting runs while preserving canonical event order."""

    groups: dict[str, list[EventEnvelope]] = {name: [] for name in STAGE_WINDOWS}
    for event in events:
        groups[_cinematic_stage(event)].append(event)
    result: dict[str, int] = {}
    for stage, rows in groups.items():
        start, end = STAGE_WINDOWS[stage]
        for index, event in enumerate(rows):
            result[event.event_id] = (
                start if len(rows) <= 1
                else start + round(index * (end - start) / (len(rows) - 1))
            )
    values = [result[event.event_id] for event in events]
    if values != sorted(values):
        raise ValueError("Cinematic stages changed canonical event order")
    return result


def _institution_id(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "unnamed"
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()[:8]
    return f"institution:{slug}:{digest}"


def campaign_presentation(events: Sequence[EventEnvelope]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive cinematic paths without inventing scientific state transitions."""

    times = cinematic_timestamps(events)
    count = len(events)
    agent_events = [event for event in events if event.event_type == "agent.registered"]
    institutions: dict[str, list[EventEnvelope]] = {}
    for event in agent_events:
        institutions.setdefault(
            str(event.payload.get("institution") or "Unassigned"), []
        ).append(event)
    labels = sorted(institutions)
    institution_positions = {
        label: (90 + round(index * 300 / max(1, len(labels) - 1)), 104)
        for index, label in enumerate(labels)
    }
    placements: list[dict[str, Any]] = []
    positions: dict[str, tuple[int, int]] = {}
    for label, source_events in sorted(institutions.items()):
        x, y = institution_positions[label]
        institution_id = _institution_id(label)
        positions[institution_id] = (x, y)
        placements.append({
            "id": f"placement:{institution_id}", "entity_id": institution_id,
            "x": x, "y": y,
            "asset_key": "institution_funding" if label == "Unassigned" else "institution_lab",
            "truth_status": "derived",
            "derived_from_event_ids": [event.event_id for event in source_events],
            "derivation_version": DERIVATION_VERSION_V2,
            "logical_timestamp_ms": 0, "duration_ms": 48_000,
            "causal_parent_id": None, "label": label,
            "kind": "institution-placement",
        })
        for index, event in enumerate(sorted(source_events, key=lambda item: item.actor_ids[0])):
            column, row = index % 3, index // 3
            point = (x - 44 + column * 44, y + 48 + row * 42)
            positions[event.actor_ids[0]] = point
            placements.append({
                "id": f"placement:{event.actor_ids[0]}", "entity_id": event.actor_ids[0],
                "x": point[0], "y": point[1],
                "asset_key": ("researcher_pi" if index == 0 else "researcher_reviewer" if index % 3 == 1 else "researcher_early"),
                **_trace(event, event_count=count, duration=48_000,
                    logical_timestamp_ms=times[event.event_id],
                    label=event.actor_ids[0], kind="researcher-placement"),
            })

    paper_events = [event for event in events if event.event_type == "paper.submitted"]
    for index, event in enumerate(paper_events):
        paper_id = event.artifact_ids[0]
        point = (218 + index * 48, 232)
        positions[paper_id] = point
        placements.append({
            "id": f"placement:{paper_id}", "entity_id": paper_id,
            "x": point[0], "y": point[1], "asset_key": "flow_paper",
            **_trace(event, event_count=count, duration=48_000,
                logical_timestamp_ms=times[event.event_id],
                label=str(event.payload.get("title") or paper_id),
                kind="paper-placement"),
        })

    flows: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    camera_cues: list[dict[str, Any]] = []

    def point(value: tuple[int, int]) -> dict[str, int]:
        return {"x": value[0], "y": value[1]}

    def add_action(
        event: EventEnvelope, suffix: str, action_type: str,
        start: tuple[int, int], end: tuple[int, int], path: list[tuple[int, int]],
        start_ms: int, duration_ms: int, label: str,
    ) -> None:
        actions.append({
            "id": f"action:{suffix}:{event.event_id[:12]}",
            "actor_entity_id": event.actor_ids[0], "action_type": action_type,
            "start": point(start), "end": point(end),
            "path": [point(item) for item in path],
            **_trace(event, event_count=count, duration=duration_ms,
                logical_timestamp_ms=start_ms, label=label,
                kind="researcher-action"),
            "causal_parent_id": event.event_id,
        })

    def add_work_cycle(
        event: EventEnvelope, action_type: str,
        work_point: tuple[int, int], label: str,
    ) -> None:
        actor = event.actor_ids[0]
        home = positions[actor]
        event_time = times[event.event_id]
        via = (home[0], 185)
        approach = (work_point[0], 185)
        add_action(event, f"move-to-{action_type}", "move", home, work_point,
            [home, via, approach, work_point], max(0, event_time - 2_400),
            1_400, f"Move to {action_type} station")
        add_action(event, action_type, action_type, work_point, work_point,
            [work_point, work_point], max(0, event_time - 800), 2_000, label)
        add_action(event, f"return-from-{action_type}", "move", work_point, home,
            [work_point, approach, via, home], event_time + 1_400, 1_500,
            f"Return from {action_type} station")
        camera_cues.append({
            "id": f"camera:{event.event_id[:12]}", "target_entity_id": actor,
            "zoom": 2, **_trace(event, event_count=count, duration=5_300,
                logical_timestamp_ms=max(0, event_time - 2_400),
                label=f"Follow {actor}", kind="camera-cue"),
            "causal_parent_id": event.event_id,
        })

    review_index = 0
    for event in events:
        event_time = times[event.event_id]
        if event.event_type == "paper.submitted":
            actor, paper = event.actor_ids[0], event.artifact_ids[0]
            paper_point = positions[paper]
            work_point = (paper_point[0], paper_point[1] - 12)
            add_work_cycle(event, "write", work_point, "Write and submit paper")
            flows.append({
                "id": f"flow:paper:{event.event_id[:12]}", "flow_type": "paper",
                "from_entity_id": actor, "to_entity_id": paper,
                **_trace(event, event_count=count, duration=2_200,
                    logical_timestamp_ms=event_time,
                    label="PAPER // author handoff", kind="paper-flow"),
                "causal_parent_id": event.event_id,
            })
        elif event.event_type == "review.completed":
            actor, paper = event.actor_ids[0], event.artifact_ids[0]
            booth = ((314, 152), (354, 152))[review_index % 2]
            review_index += 1
            add_work_cycle(event, "review", booth, "Complete peer review")
            flows.append({
                "id": f"flow:review:{event.event_id[:12]}", "flow_type": "review",
                "from_entity_id": actor, "to_entity_id": paper,
                **_trace(event, event_count=count, duration=2_200,
                    logical_timestamp_ms=event_time,
                    label="REVIEW // reviewer handoff", kind="review-flow"),
                "causal_parent_id": event.event_id,
            })
        elif event.event_type == "resource.changed" and event.payload.get("category") == "grant_income":
            actor = event.actor_ids[0]
            agent = next(row for row in agent_events if row.actor_ids[0] == actor)
            institution = _institution_id(str(agent.payload.get("institution") or "Unassigned"))
            home = positions[actor]
            add_action(event, "receive", "receive", home, home, [home, home],
                max(0, event_time - 500), 1_800, "Receive grant income")
            camera_cues.append({
                "id": f"camera:{event.event_id[:12]}", "target_entity_id": actor,
                "zoom": 2, **_trace(event, event_count=count, duration=2_300,
                    logical_timestamp_ms=max(0, event_time - 500),
                    label=f"Follow {actor}", kind="camera-cue"),
                "causal_parent_id": event.event_id,
            })
            flows.append({
                "id": f"flow:funding:{event.event_id[:12]}", "flow_type": "funding",
                "from_entity_id": institution, "to_entity_id": actor,
                **_trace(event, event_count=count, duration=2_200,
                    logical_timestamp_ms=event_time,
                    label="FUNDING // grant handoff", kind="funding-flow"),
                "causal_parent_id": event.event_id,
            })

    chapter_labels = {
        "register": "ASSEMBLE", "submit": "SUBMIT", "produce": "PRODUCE",
        "review": "REVIEW", "decide": "DECIDE", "apply": "APPLY",
        "fund": "FUND", "report": "REPORT", "complete": "CLOSE",
    }
    chapters = []
    for stage, (start, end) in STAGE_WINDOWS.items():
        sources = [event for event in events if _cinematic_stage(event) == stage]
        if not sources:
            continue
        chapters.append({
            "id": f"chapter:{stage}", "label": chapter_labels[stage],
            "kind": "cinematic-chapter", "truth_status": "derived",
            "derived_from_event_ids": [event.event_id for event in sources],
            "derivation_version": DERIVATION_VERSION_V2,
            "logical_timestamp_ms": start, "end_ms": end,
            "duration_ms": end - start, "causal_parent_id": None,
        })
    return ({
        "duration_ms": 48_000, "placements": placements, "flows": flows,
        "actions": actions, "camera_cues": camera_cues, "chapters": chapters,
        "time_compression": {
            "kind": "deterministic-stage-compression",
            "canonical_event_count": len(events), "duration_ms": 48_000,
        },
    }, {"actors": [], "effects": []})


def export_campaign_bundle(source_manifest: Path, campaign_root: Path, project_root: Path) -> dict[str, Any]:
    """Verify campaign provenance and return a browser-portable replay bundle."""

    source = _object(_read_json(source_manifest), "source manifest")
    if source.get("schema_version") != SOURCE_SCHEMA:
        raise ValueError("unsupported campaign source schema")
    if source.get("status") != "completed" or _object(source.get("run"), "run").get("status") != "complete":
        raise ValueError("campaign source and selected run must both be complete")
    commit = str(source.get("source_commit", ""))
    if GIT_COMMIT.fullmatch(commit) is None:
        raise ValueError("source_commit must be a full lowercase Git commit")

    campaign_result = _checked_file(project_root, source.get("campaign_result"), "campaign_result")
    result = _object(_read_json(campaign_result), "campaign result")
    campaign = _object(result.get("campaign"), "campaign result campaign")
    if campaign.get("id") != source.get("campaign_id") or campaign.get("revision") != source.get("campaign_revision"):
        raise ValueError("campaign identity does not match the completed result")
    if campaign.get("source_commit") != commit or not campaign.get("completed_utc"):
        raise ValueError("campaign result is not completed at the declared source commit")

    run = _object(source.get("run"), "run")
    suggestion = next((row for row in result.get("suggestions", []) if row.get("suggestion_id") == run.get("suggestion_id")), None)
    if not suggestion or suggestion.get("status") != "complete":
        raise ValueError("selected suggestion is not complete in the campaign result")
    run_result = next((row for row in suggestion.get("runs", []) if row.get("run_id") == run.get("id") and row.get("seed") == run.get("seed")), None)
    if not run_result:
        raise ValueError("selected run is not bound to the completed suggestion")

    files = _object(source.get("files"), "files")
    paths = {name: _checked_file(campaign_root, files.get(name), f"files.{name}") for name in (
        "run_manifest", "integrity", "checkpoint", "resource_ledger", "resource_balances"
    )}
    run_manifest = _object(_read_json(paths["run_manifest"]), "run manifest")
    if run_manifest.get("status") != "complete" or run_manifest.get("git_commit") != commit:
        raise ValueError("native run manifest is not complete at the declared commit")
    if run_manifest.get("git_dirty_files") not in ("", []):
        raise ValueError("native run manifest records a dirty source tree")
    args = _object(run_manifest.get("args"), "run manifest args")
    if args.get("run_id") != run.get("id") or args.get("seed") != run.get("seed"):
        raise ValueError("native run manifest identity does not match the selected run")
    integrity = _read_json(paths["integrity"])
    if not isinstance(integrity, list) or not integrity or any(not row.get("passed") or row.get("failures") for row in integrity):
        raise ValueError("native integrity report did not pass cleanly")

    events = convert_artifacts(ArtifactBundle(
        checkpoint=paths["checkpoint"],
        resource_ledger=paths["resource_ledger"],
        resource_balances=paths["resource_balances"],
    ))
    choreography, ambient = campaign_presentation(events)
    payload = build_viewer_payload_v2(events, metadata={
        "run_id": run["id"],
        "branch": f"completed campaign // seed {run['seed']}",
        "source_kind": "verified_commit_pinned_campaign_run",
        "empirical": True,
        "phase": "engineering demo · completed",
        "year": 1,
        "campaign_id": source["campaign_id"],
        "campaign_revision": source["campaign_revision"],
        "source_commit": commit,
        "source_manifest_schema": SOURCE_SCHEMA,
        "source_file_sha256": {name: _object(files[name], name)["sha256"] for name in sorted(files)},
        "claim_boundary": source["claim_boundary"],
        "disclosure": source["claim_boundary"] + " Canonical events and projector frames were produced by the verified Python adapter; raw simulator state is not included.",
    }, choreography=choreography, ambient=ambient,
        logical_timestamps_ms=cinematic_timestamps(events))
    payload["web_stream_hash"] = web_event_stream_hash(payload["canonical"]["events"])
    payload["web_stream_hash_algorithm"] = "scienceutopia.web-f64-json-sha256.v1"
    validate_portable_bundle(payload)
    return payload


def validate_portable_bundle(payload: Mapping[str, Any]) -> None:
    """Fail closed if a portable bundle diverges from canonical Python replay."""

    if payload.get("schema_version") != PORTABLE_SCHEMA:
        raise ValueError("unsupported portable replay schema")
    canonical = _object(payload.get("canonical"), "portable canonical")
    raw_events = canonical.get("events")
    if not isinstance(raw_events, list):
        raise ValueError("portable canonical.events must be a list")
    events: list[EventEnvelope] = []
    for index, row_value in enumerate(raw_events):
        row = _object(row_value, f"canonical.events[{index}]")
        recreated = EventEnvelope.create(
            sequence=row["sequence"], year=row["year"], phase=row["phase"],
            event_type=row["event_type"], actor_ids=row["actor_ids"],
            artifact_ids=row["artifact_ids"], payload=row["payload"], provenance=row["provenance"],
        )
        if recreated.event_id != row.get("event_id"):
            raise ValueError(f"canonical event identity mismatch at index {index}")
        events.append(recreated)
    if canonical_event_stream_hash(events) != payload.get("stream_hash"):
        raise ValueError("portable canonical stream hash mismatch")
    if web_event_stream_hash(raw_events) != payload.get("web_stream_hash"):
        raise ValueError("portable web stream hash mismatch")
    frames = _object(payload.get("projection"), "projection").get("frames")
    facts = canonical.get("facts")
    if not isinstance(facts, list) or len(facts) != len(events):
        raise ValueError("portable canonical fact count mismatch")
    if not isinstance(frames, list) or len(frames) != len(events) + 1:
        raise ValueError("portable projection frame count mismatch")
    for cursor, frame_value in enumerate(frames):
        frame = _object(frame_value, f"projection.frames[{cursor}]")
        if frame.get("cursor") != cursor or frame.get("state") != replay(events[:cursor]).to_dict():
            raise ValueError(f"authoritative projection mismatch at cursor {cursor}")
        expected_timestamp = 0 if cursor == 0 else _object(facts[cursor - 1], f"canonical.facts[{cursor - 1}]").get("logical_timestamp_ms")
        if frame.get("logical_timestamp_ms") != expected_timestamp:
            raise ValueError(f"authoritative projection timestamp mismatch at cursor {cursor}")
    serialized = json.dumps(payload, sort_keys=True)
    forbidden = ('"paper_tracker":', '"ecosystem_data":', '"memory_bank":', '"conference_system":')
    if any(token in serialized for token in forbidden):
        raise ValueError("portable bundle contains a raw simulator-state field")


__all__ = [
    "SOURCE_SCHEMA", "campaign_presentation", "cinematic_timestamps",
    "export_campaign_bundle", "validate_portable_bundle", "web_event_stream_hash",
]
