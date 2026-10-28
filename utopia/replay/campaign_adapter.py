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


def _trace(event: EventEnvelope, *, event_count: int, duration: int, label: str, kind: str) -> dict[str, Any]:
    return {
        "truth_status": "derived",
        "derived_from_event_ids": [event.event_id],
        "derivation_version": DERIVATION_VERSION_V2,
        "logical_timestamp_ms": _logical_time(event.sequence, event_count),
        "duration_ms": duration,
        "causal_parent_id": None,
        "label": label,
        "kind": kind,
    }


def _logical_time(sequence: int, count: int) -> int:
    return round(sequence * 48_000 / max(1, count - 1))


def _institution_id(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "unnamed"
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()[:8]
    return f"institution:{slug}:{digest}"


def campaign_presentation(events: Sequence[EventEnvelope]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive only spatial records that cite their canonical source event."""

    agent_events = [event for event in events if event.event_type == "agent.registered"]
    institutions: dict[str, list[EventEnvelope]] = {}
    for event in agent_events:
        institutions.setdefault(str(event.payload.get("institution") or "Unassigned"), []).append(event)
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
            "id": f"placement:{institution_id}",
            "entity_id": institution_id,
            "x": x,
            "y": y,
            "asset_key": "institution_funding" if label == "Unassigned" else "institution_lab",
            "truth_status": "derived",
            "derived_from_event_ids": [event.event_id for event in source_events],
            "derivation_version": DERIVATION_VERSION_V2,
            "logical_timestamp_ms": 0,
            "duration_ms": 48_000,
            "causal_parent_id": None,
            "label": label,
            "kind": "institution-placement",
        })
        for index, event in enumerate(sorted(source_events, key=lambda item: item.actor_ids[0])):
            column, row = index % 3, index // 3
            point = (x - 44 + column * 44, y + 48 + row * 42)
            positions[event.actor_ids[0]] = point
            placements.append({
                "id": f"placement:{event.actor_ids[0]}",
                "entity_id": event.actor_ids[0],
                "x": point[0],
                "y": point[1],
                "asset_key": ("researcher_pi" if index == 0 else "researcher_reviewer" if index % 3 == 1 else "researcher_early"),
                **_trace(event, event_count=len(events), duration=48_000, label=event.actor_ids[0], kind="researcher-placement"),
            })

    paper_events = [event for event in events if event.event_type == "paper.submitted"]
    for index, event in enumerate(paper_events):
        paper_id = event.artifact_ids[0]
        point = (218 + index * 48, 232)
        positions[paper_id] = point
        placements.append({
            "id": f"placement:{paper_id}", "entity_id": paper_id,
            "x": point[0], "y": point[1], "asset_key": "flow_paper",
            **_trace(event, event_count=len(events), duration=48_000, label=str(event.payload.get("title") or paper_id), kind="paper-placement"),
        })

    flows: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    for event in events:
        if event.event_type == "paper.submitted":
            actor, paper = event.actor_ids[0], event.artifact_ids[0]
            flows.append({
                "id": f"flow:paper:{event.event_id[:12]}", "flow_type": "paper",
                "from_entity_id": actor, "to_entity_id": paper,
                **_trace(event, event_count=len(events), duration=2_800, label="PAPER // submitted", kind="paper-flow"),
            })
            actions.append({
                "id": f"action:write:{event.event_id[:12]}", "actor_entity_id": actor,
                "action_type": "write", "start": dict(zip(("x", "y"), positions[actor])),
                "end": dict(zip(("x", "y"), positions[paper])),
                **_trace(event, event_count=len(events), duration=2_800, label="Write and submit paper", kind="researcher-action"),
            })
        elif event.event_type == "review.completed":
            actor, paper = event.actor_ids[0], event.artifact_ids[0]
            flows.append({
                "id": f"flow:review:{event.event_id[:12]}", "flow_type": "review",
                "from_entity_id": actor, "to_entity_id": paper,
                **_trace(event, event_count=len(events), duration=2_400, label="REVIEW // completed", kind="review-flow"),
            })
            actions.append({
                "id": f"action:review:{event.event_id[:12]}", "actor_entity_id": actor,
                "action_type": "review", "start": dict(zip(("x", "y"), positions[actor])),
                "end": dict(zip(("x", "y"), positions[paper])),
                **_trace(event, event_count=len(events), duration=2_400, label="Complete peer review", kind="researcher-action"),
            })
        elif event.event_type == "resource.changed" and event.payload.get("category") == "grant_income":
            actor = event.actor_ids[0]
            agent = next(row for row in agent_events if row.actor_ids[0] == actor)
            institution = _institution_id(str(agent.payload.get("institution") or "Unassigned"))
            flows.append({
                "id": f"flow:funding:{event.event_id[:12]}", "flow_type": "funding",
                "from_entity_id": institution, "to_entity_id": actor,
                **_trace(event, event_count=len(events), duration=2_600, label="FUNDING // grant income", kind="funding-flow"),
            })
            actions.append({
                "id": f"action:receive:{event.event_id[:12]}", "actor_entity_id": actor,
                "action_type": "receive", "start": dict(zip(("x", "y"), positions[institution])),
                "end": dict(zip(("x", "y"), positions[actor])),
                **_trace(event, event_count=len(events), duration=2_600, label="Receive grant income", kind="researcher-action"),
            })
    return ({
        "duration_ms": 48_000,
        "placements": placements,
        "flows": flows,
        "actions": actions,
        "camera_cues": [],
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
    }, choreography=choreography, ambient=ambient)
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
    if not isinstance(frames, list) or len(frames) != len(events) + 1:
        raise ValueError("portable projection frame count mismatch")
    for cursor, frame_value in enumerate(frames):
        frame = _object(frame_value, f"projection.frames[{cursor}]")
        if frame.get("cursor") != cursor or frame.get("state") != replay(events[:cursor]).to_dict():
            raise ValueError(f"authoritative projection mismatch at cursor {cursor}")
    serialized = json.dumps(payload, sort_keys=True)
    forbidden = ('"paper_tracker":', '"ecosystem_data":', '"memory_bank":', '"conference_system":')
    if any(token in serialized for token in forbidden):
        raise ValueError("portable bundle contains a raw simulator-state field")


__all__ = [
    "SOURCE_SCHEMA", "campaign_presentation", "export_campaign_bundle",
    "validate_portable_bundle", "web_event_stream_hash",
]
