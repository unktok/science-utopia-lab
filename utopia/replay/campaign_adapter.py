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
    review_events = [event for event in events if event.event_type == "review.completed"]
    decision_events = [event for event in events if event.event_type == "paper.decided"]
    grant_events = [event for event in events if event.event_type == "resource.changed" and event.payload.get("category") == "grant_income"]
    application_events: dict[str, list[EventEnvelope]] = {}
    for event in events:
        if event.event_type == "resource.changed" and event.payload.get("category") == "funding_application_cost":
            application_events.setdefault(event.actor_ids[0], []).append(event)
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

    workflow_specs = (
        ("workflow:submission-relay", "SUBMISSION RELAY", "workflow_submission", (168, 232),
            [event for event in events if event.event_type == "paper.submitted"]),
        ("workflow:review-exchange", "REVIEW EXCHANGE", "workflow_review", (334, 118),
            [event for event in events if event.event_type == "review.completed"]),
        ("workflow:publication-spine", "PUBLICATION SPINE", "workflow_publication", (432, 232),
            [event for event in events if event.event_type == "paper.decided"]),
        ("workflow:funding-ledger", "FUNDING LEDGER", "workflow_funding", (112, 232),
            [event for event in events if event.event_type == "resource.changed"
                and event.payload.get("category") in {"funding_application_cost", "grant_income"}]),
    )
    workflow_nodes: list[dict[str, Any]] = []
    for node_id, label, asset_key, node_position, source_events in workflow_specs:
        if not source_events:
            continue
        positions[node_id] = node_position
        workflow_nodes.append({
            "id": node_id, "label": label, "kind": "institutional-workflow-node",
            "entity_type": "workflow_node", "asset_key": asset_key,
            "x": node_position[0], "y": node_position[1],
            "truth_status": "derived",
            "derived_from_event_ids": [event.event_id for event in source_events],
            "derivation_version": DERIVATION_VERSION_V2,
            "logical_timestamp_ms": min(times[event.event_id] for event in source_events),
            "duration_ms": 48_000, "causal_parent_id": None,
        })

    workstations: list[dict[str, Any]] = []
    manuscript_station_by_event: dict[str, str] = {}
    review_station_by_event: dict[str, str] = {}
    decision_station_by_event: dict[str, str] = {}
    application_station_by_actor: dict[str, str] = {}
    award_station_by_actor: dict[str, str] = {}

    def add_workstation(
        station_id: str, label: str, asset_key: str,
        station_position: tuple[int, int], source_events: Sequence[EventEnvelope],
    ) -> None:
        positions[station_id] = station_position
        workstations.append({
            "id": station_id, "label": label, "kind": "institutional-workstation",
            "entity_type": "workstation", "asset_key": asset_key,
            "x": station_position[0], "y": station_position[1],
            "truth_status": "derived",
            "derived_from_event_ids": [event.event_id for event in source_events],
            "derivation_version": DERIVATION_VERSION_V2,
            "logical_timestamp_ms": min(times[event.event_id] for event in source_events),
            "duration_ms": 48_000, "causal_parent_id": None,
        })

    for index, event in enumerate(paper_events):
        station_id = f"workstation:manuscript:{index}"
        manuscript_station_by_event[event.event_id] = station_id
        add_workstation(station_id, f"MANUSCRIPT BENCH {index + 1}", "station_manuscript",
            (218 + index * 48, 220), [event])
    for index in range(2):
        source_events = review_events[index::2]
        if source_events:
            station_id = f"workstation:review:{index}"
            add_workstation(station_id, f"REVIEW BOOTH {index + 1}", "station_review",
                ((314, 152), (354, 152))[index], source_events)
            for event in source_events:
                review_station_by_event[event.event_id] = station_id
    application_points = ((72, 222), (100, 222), (128, 222), (156, 222))
    application_station_sources: list[list[EventEnvelope]] = [[] for _ in application_points]
    for index, (actor, source_events) in enumerate(sorted(application_events.items())):
        terminal_index = index % len(application_points)
        station_id = f"workstation:application:{terminal_index}"
        application_station_by_actor[actor] = station_id
        application_station_sources[terminal_index].extend(source_events)
    for index, source_events in enumerate(application_station_sources):
        if source_events:
            add_workstation(f"workstation:application:{index}", f"APPLICATION TERMINAL {index + 1}",
                "station_application", application_points[index], source_events)
    for index, event in enumerate(decision_events):
        station_id = f"workstation:decision:{index}"
        decision_station_by_event[event.event_id] = station_id
        add_workstation(station_id, f"DECISION CONSOLE {index + 1}", "station_decision",
            ((406, 232), (450, 232))[index % 2], [event])
    grants_by_actor: dict[str, list[EventEnvelope]] = {}
    for event in grant_events:
        grants_by_actor.setdefault(event.actor_ids[0], []).append(event)
    for index, (actor, source_events) in enumerate(sorted(grants_by_actor.items())):
        station_id = f"workstation:award:{index}"
        award_station_by_actor[actor] = station_id
        add_workstation(station_id, "GRANT INBOX", "station_award", positions[actor], source_events)

    flows: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    camera_cues: list[dict[str, Any]] = []
    epistemic_flows: list[dict[str, Any]] = []
    interior_activities: list[dict[str, Any]] = []

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

    def add_action_many(
        source_events: Sequence[EventEnvelope], suffix: str, action_type: str,
        start: tuple[int, int], end: tuple[int, int], path: list[tuple[int, int]],
        start_ms: int, duration_ms: int, label: str,
    ) -> None:
        first = source_events[0]
        actions.append({
            "id": f"action:{suffix}:{first.event_id[:12]}",
            "actor_entity_id": first.actor_ids[0], "action_type": action_type,
            "start": point(start), "end": point(end),
            "path": [point(item) for item in path],
            "truth_status": "derived",
            "derived_from_event_ids": [event.event_id for event in source_events],
            "derivation_version": DERIVATION_VERSION_V2,
            "logical_timestamp_ms": start_ms, "duration_ms": duration_ms,
            "causal_parent_id": first.event_id, "label": label,
            "kind": "researcher-action",
        })

    def add_interior_activity(
        source_events: Sequence[EventEnvelope], activity_type: str,
        workstation_id: str, start_ms: int, duration_ms: int, label: str,
    ) -> None:
        first = source_events[0]
        interior_activities.append({
            "id": f"interior:{activity_type}:{first.event_id[:12]}",
            "label": label, "kind": "institutional-interior-activity",
            "activity_type": activity_type, "event_type": first.event_type,
            "actor_entity_id": first.actor_ids[0], "workstation_id": workstation_id,
            "truth_status": "derived",
            "derived_from_event_ids": [event.event_id for event in source_events],
            "derivation_version": DERIVATION_VERSION_V2,
            "logical_timestamp_ms": start_ms, "duration_ms": duration_ms,
            "causal_parent_id": first.event_id,
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

    def add_epistemic_flow(
        flow_kind: str,
        source_events: Sequence[EventEnvelope],
        from_entity_id: str,
        to_entity_id: str,
        path: list[tuple[int, int]],
        label: str,
        packet_asset_key: str,
        *,
        duration_ms: int = 2_600,
    ) -> None:
        first = source_events[0]
        epistemic_flows.append({
            "id": f"epistemic:{flow_kind}:{first.event_id[:12]}",
            "label": label, "kind": "epistemic-flow",
            "flow_kind": flow_kind, "event_type": first.event_type,
            "from_entity_id": from_entity_id, "to_entity_id": to_entity_id,
            "path": [point(item) for item in path],
            "packet_asset_key": packet_asset_key,
            "truth_status": "derived",
            "derived_from_event_ids": [event.event_id for event in source_events],
            "derivation_version": DERIVATION_VERSION_V2,
            "logical_timestamp_ms": times[first.event_id],
            "duration_ms": duration_ms,
            "causal_parent_id": first.event_id,
        })

    review_index = 0
    for event in events:
        event_time = times[event.event_id]
        if event.event_type == "paper.submitted":
            actor, paper = event.actor_ids[0], event.artifact_ids[0]
            paper_point = positions[paper]
            work_point = (paper_point[0], paper_point[1] - 12)
            add_work_cycle(event, "write", work_point, "Write and submit paper")
            add_interior_activity([event], "write", manuscript_station_by_event[event.event_id],
                max(0, event_time - 800), 2_000, "Synthesize and write manuscript")
            flows.append({
                "id": f"flow:paper:{event.event_id[:12]}", "flow_type": "paper",
                "from_entity_id": actor, "to_entity_id": paper,
                **_trace(event, event_count=count, duration=2_200,
                    logical_timestamp_ms=event_time,
                    label="PAPER // author handoff", kind="paper-flow"),
                "causal_parent_id": event.event_id,
            })
            home = positions[actor]
            relay = positions["workflow:submission-relay"]
            add_epistemic_flow(
                "manuscript", [event], actor, paper,
                [home, (home[0], 210), (relay[0], 210), relay, (paper_point[0], relay[1]), paper_point],
                "MANUSCRIPT // author → submission → paper", "token_manuscript",
            )
        elif event.event_type == "review.completed":
            actor, paper = event.actor_ids[0], event.artifact_ids[0]
            booth = ((314, 152), (354, 152))[review_index % 2]
            review_index += 1
            add_work_cycle(event, "review", booth, "Complete peer review")
            add_interior_activity([event], "review", review_station_by_event[event.event_id],
                max(0, event_time - 800), 2_000, "Inspect and complete peer review")
            flows.append({
                "id": f"flow:review:{event.event_id[:12]}", "flow_type": "review",
                "from_entity_id": actor, "to_entity_id": paper,
                **_trace(event, event_count=count, duration=2_200,
                    logical_timestamp_ms=event_time,
                    label="REVIEW // reviewer handoff", kind="review-flow"),
                "causal_parent_id": event.event_id,
            })
            home = positions[actor]
            relay = positions["workflow:review-exchange"]
            paper_point = positions[paper]
            add_epistemic_flow(
                "review", [event], actor, paper,
                [home, (home[0], relay[1]), relay, (paper_point[0], relay[1]), paper_point],
                "REVIEW // reviewer → exchange → paper", "token_review_seal",
            )
        elif event.event_type == "paper.decided":
            paper = event.artifact_ids[0]
            paper_point = positions[paper]
            relay = positions["workflow:publication-spine"]
            station_id = decision_station_by_event[event.event_id]
            station_point = positions[station_id]
            add_work_cycle(event, "read", station_point, "Read publication decision")
            add_interior_activity([event], "read", station_id,
                max(0, event_time - 800), 2_000, "Read recorded publication decision")
            decision = str(event.payload.get("decision") or "recorded").upper()
            add_epistemic_flow(
                "decision", [event], paper, "workflow:publication-spine",
                [paper_point, (paper_point[0], 252), (relay[0], 252), relay],
                f"DECISION // {decision} → publication spine", "token_decision",
                duration_ms=2_200,
            )
        elif event.event_type == "resource.changed" and event.payload.get("category") == "grant_income":
            actor = event.actor_ids[0]
            agent = next(row for row in agent_events if row.actor_ids[0] == actor)
            institution = _institution_id(str(agent.payload.get("institution") or "Unassigned"))
            home = positions[actor]
            add_action(event, "receive", "receive", home, home, [home, home],
                max(0, event_time - 500), 1_800, "Receive grant income")
            add_interior_activity([event], "receive", award_station_by_actor[actor],
                max(0, event_time - 500), 1_800, "Receive grant ledger update")
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
            relay = positions["workflow:funding-ledger"]
            add_epistemic_flow(
                "award", [event], "workflow:funding-ledger", actor,
                [relay, (relay[0], 216), (home[0], 216), home],
                "AWARD // grant ledger → researcher", "token_grant",
                duration_ms=2_400,
            )

    funding_relay = positions.get("workflow:funding-ledger")
    if funding_relay:
        for actor, source_events in sorted(application_events.items()):
            home = positions[actor]
            first_time = times[source_events[0].event_id]
            last_time = times[source_events[-1].event_id]
            station_id = application_station_by_actor[actor]
            station_point = positions[station_id]
            work_duration = max(1_400, last_time - first_time + 1_000)
            via_home = (home[0], 202)
            via_station = (station_point[0], 202)
            add_action_many(source_events, "move-to-application", "move", home, station_point,
                [home, via_home, via_station, station_point], max(0, first_time - 1_200),
                800, "Move to application terminal")
            add_action_many(source_events, "apply", "apply", station_point, station_point,
                [station_point, station_point], max(0, first_time - 300), work_duration,
                "Prepare funding application")
            add_action_many(source_events, "return-from-application", "move", station_point, home,
                [station_point, via_station, via_home, home], first_time + work_duration + 100,
                800, "Return from application terminal")
            add_interior_activity(source_events, "apply", station_id,
                max(0, first_time - 300), work_duration, "Prepare funding application")
            camera_cues.append({
                "id": f"camera:application:{source_events[0].event_id[:12]}",
                "target_entity_id": actor, "zoom": 2,
                "truth_status": "derived",
                "derived_from_event_ids": [event.event_id for event in source_events],
                "derivation_version": DERIVATION_VERSION_V2,
                "logical_timestamp_ms": max(0, first_time - 1_200),
                "duration_ms": work_duration + 2_100,
                "causal_parent_id": source_events[0].event_id,
                "label": f"Follow {actor}", "kind": "camera-cue",
            })
            add_epistemic_flow(
                "application", source_events, actor, "workflow:funding-ledger",
                [home, (home[0], 216), (funding_relay[0], 216), funding_relay],
                f"APPLICATION // {len(source_events)} canonical fee event{'s' if len(source_events) != 1 else ''}",
                "token_application",
                duration_ms=max(1_800, last_time - first_time + 600),
            )

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
        "workflow_nodes": workflow_nodes, "epistemic_flows": epistemic_flows,
        "workstations": workstations, "interior_activities": interior_activities,
        "time_compression": {
            "kind": "deterministic-stage-compression",
            "canonical_event_count": len(events), "duration_ms": 48_000,
        },
    }, {"actors": [], "effects": [
        {
            "id": "ambient:interior-console-flicker", "label": "Cosmetic console flicker",
            "kind": "interior-console-flicker", "truth_status": "ambient",
            "derived_from_event_ids": [], "derivation_version": DERIVATION_VERSION_V2,
            "logical_timestamp_ms": 0, "duration_ms": 48_000, "causal_parent_id": None,
        },
        {
            "id": "ambient:break-room-vapor", "label": "Cosmetic break-room vapor",
            "kind": "break-room-vapor", "truth_status": "ambient",
            "derived_from_event_ids": [], "derivation_version": DERIVATION_VERSION_V2,
            "logical_timestamp_ms": 0, "duration_ms": 48_000, "causal_parent_id": None,
        },
    ]})


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
    metadata = _object(payload.get("metadata"), "portable metadata")
    verified_source = metadata.get("source_kind") == "verified_commit_pinned_campaign_run"
    if bool(metadata.get("empirical")) != verified_source:
        raise ValueError("portable verified/synthetic source boundary mismatch")
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
    choreography = _object(payload.get("choreography"), "portable choreography")
    epistemic_flows = choreography.get("epistemic_flows")
    if verified_source and (not isinstance(epistemic_flows, list) or not epistemic_flows):
        raise ValueError("verified campaign requires evidence-linked epistemic flows")
    event_by_id = {event.event_id: event for event in events}
    for index, flow_value in enumerate(epistemic_flows or []):
        flow = _object(flow_value, f"choreography.epistemic_flows[{index}]")
        source_ids = flow.get("derived_from_event_ids", [])
        if not isinstance(source_ids, list) or any(event_id not in event_by_id for event_id in source_ids):
            raise ValueError(f"epistemic flow has an unknown canonical source: {flow.get('id')}")
        sources = [event_by_id[event_id] for event_id in source_ids]
        kind = flow.get("flow_kind")
        if not sources:
            raise ValueError(f"epistemic flow has no canonical source: {flow.get('id')}")
        if flow.get("event_type") != sources[0].event_type or any(event.event_type != sources[0].event_type for event in sources):
            raise ValueError(f"epistemic flow event type mismatch: {flow.get('id')}")
        if kind == "manuscript":
            valid = len(sources) == 1 and sources[0].event_type == "paper.submitted" \
                and flow.get("from_entity_id") == sources[0].actor_ids[0] \
                and flow.get("to_entity_id") == sources[0].artifact_ids[0]
        elif kind == "review":
            valid = len(sources) == 1 and sources[0].event_type == "review.completed" \
                and flow.get("from_entity_id") == sources[0].actor_ids[0] \
                and flow.get("to_entity_id") == sources[0].artifact_ids[0]
        elif kind == "decision":
            valid = len(sources) == 1 and sources[0].event_type == "paper.decided" \
                and flow.get("from_entity_id") == sources[0].artifact_ids[0] \
                and flow.get("to_entity_id") == "workflow:publication-spine"
        elif kind == "application":
            valid = all(event.payload.get("category") == "funding_application_cost" for event in sources) \
                and len({event.actor_ids[0] for event in sources}) == 1 \
                and flow.get("from_entity_id") == sources[0].actor_ids[0] \
                and flow.get("to_entity_id") == "workflow:funding-ledger"
        elif kind == "award":
            valid = len(sources) == 1 and sources[0].payload.get("category") == "grant_income" \
                and flow.get("from_entity_id") == "workflow:funding-ledger" \
                and flow.get("to_entity_id") == sources[0].actor_ids[0]
        else:
            valid = False
        if not valid:
            raise ValueError(f"epistemic flow semantic mismatch: {flow.get('id')}")
    workstations = choreography.get("workstations")
    interior_activities = choreography.get("interior_activities")
    if verified_source and (
        not isinstance(workstations, list) or not workstations
        or not isinstance(interior_activities, list) or not interior_activities
    ):
        raise ValueError("verified campaign requires evidence-linked institutional interiors")
    workstation_ids = {
        str(_object(row, f"choreography.workstations[{index}]").get("id"))
        for index, row in enumerate(workstations or [])
    }
    for index, activity_value in enumerate(interior_activities or []):
        activity = _object(activity_value, f"choreography.interior_activities[{index}]")
        source_ids = activity.get("derived_from_event_ids", [])
        if not isinstance(source_ids, list) or not source_ids or any(event_id not in event_by_id for event_id in source_ids):
            raise ValueError(f"interior activity has an unknown canonical source: {activity.get('id')}")
        sources = [event_by_id[event_id] for event_id in source_ids]
        activity_type = activity.get("activity_type")
        same_actor = len({event.actor_ids[0] for event in sources}) == 1
        base_valid = activity.get("event_type") == sources[0].event_type \
            and all(event.event_type == sources[0].event_type for event in sources) \
            and same_actor and activity.get("actor_entity_id") == sources[0].actor_ids[0] \
            and activity.get("workstation_id") in workstation_ids
        if activity_type == "write":
            semantic_valid = len(sources) == 1 and sources[0].event_type == "paper.submitted"
        elif activity_type == "review":
            semantic_valid = len(sources) == 1 and sources[0].event_type == "review.completed"
        elif activity_type == "read":
            semantic_valid = len(sources) == 1 and sources[0].event_type == "paper.decided"
        elif activity_type == "apply":
            semantic_valid = all(event.payload.get("category") == "funding_application_cost" for event in sources)
        elif activity_type == "receive":
            semantic_valid = len(sources) == 1 and sources[0].payload.get("category") == "grant_income"
        else:
            semantic_valid = False
        if not base_valid or not semantic_valid:
            raise ValueError(f"interior activity semantic mismatch: {activity.get('id')}")
    serialized = json.dumps(payload, sort_keys=True)
    forbidden = ('"paper_tracker":', '"ecosystem_data":', '"memory_bank":', '"conference_system":')
    if any(token in serialized for token in forbidden):
        raise ValueError("portable bundle contains a raw simulator-state field")


__all__ = [
    "SOURCE_SCHEMA", "campaign_presentation", "cinematic_timestamps",
    "export_campaign_bundle", "validate_portable_bundle", "web_event_stream_hash",
]
