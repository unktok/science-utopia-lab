"""Deterministic, explicitly synthetic replay fixture for Game UI v2.

This is a contract fixture, not the output of a scientific experiment. Its
purpose is to exercise all six visual flow grammars while preserving the same
canonical -> projection -> choreography -> ambience boundary as real exports.
"""

from __future__ import annotations

from typing import Any

from .events import EventEnvelope
from .viewer import _institution_id, _trace


def vertical_slice_events() -> list[EventEnvelope]:
    specs: list[dict[str, Any]] = [
        {
            "event_type": "agent.registered",
            "actor_ids": ("researcher:aya",),
            "payload": {
                "display_name": "Dr. Aya Kuroda",
                "agent_type": "academic_researcher",
                "institution": "Noctiluca Knowledge Lab",
                "initial_balance": 100,
                "initial_active": True,
            },
        },
        {
            "event_type": "agent.registered",
            "actor_ids": ("researcher:mino",),
            "payload": {
                "display_name": "Dr. Mino Vale",
                "agent_type": "review_researcher",
                "institution": "Peer Review Exchange",
                "initial_balance": 100,
                "initial_active": True,
            },
        },
        {
            "event_type": "agent.registered",
            "actor_ids": ("researcher:sol",),
            "payload": {
                "display_name": "Dr. Sol Okafor",
                "agent_type": "policy_researcher",
                "institution": "Civic Funding Bureau",
                "initial_balance": 100,
                "initial_active": True,
            },
        },
        {
            "event_type": "agent.registered",
            "actor_ids": ("researcher:iren",),
            "payload": {
                "display_name": "Dr. Iren Moss",
                "agent_type": "editor_researcher",
                "institution": "Noctiluca Publication Spine",
                "initial_balance": 100,
                "initial_active": True,
            },
        },
        {
            "event_type": "research.data_shared",
            "actor_ids": ("researcher:aya", "researcher:mino"),
            "payload": {
                "dataset_id": "dataset:noctiluca-17",
                "summary": "A synthetic dataset handoff for renderer validation.",
            },
        },
        {
            "event_type": "paper.submitted",
            "actor_ids": ("researcher:aya",),
            "artifact_ids": ("paper:arcology-signals",),
            "payload": {
                "title": "Signals Across the Arcology",
                "conference": "Peer Review Exchange",
                "topics": ["science-of-science", "institution-design"],
                "submission_round": 0,
            },
        },
        {
            "event_type": "review.completed",
            "actor_ids": ("researcher:mino",),
            "artifact_ids": ("paper:arcology-signals",),
            "payload": {
                "conference": "Peer Review Exchange",
                "score": 4,
                "justification": "Synthetic review used to validate replay choreography.",
                "submission_round": 0,
            },
        },
        {
            "event_type": "paper.decided",
            "actor_ids": ("researcher:aya",),
            "artifact_ids": ("paper:arcology-signals",),
            "payload": {
                "decision": "accept",
                "score": 4,
                "conference": "Peer Review Exchange",
                "submission_round": 0,
            },
        },
        {
            "event_type": "resource.changed",
            "actor_ids": ("researcher:aya",),
            "payload": {
                "category": "grant_income",
                "delta": 20,
                "requested_delta": 20,
                "balance_before": 100,
                "balance_after": 120,
                "active_after": True,
                "uncollected_cost": 0,
                "source_institution": "Civic Funding Bureau",
            },
        },
        {
            "event_type": "citation.recorded",
            "actor_ids": ("researcher:sol", "researcher:aya"),
            "artifact_ids": ("paper:arcology-signals",),
            "payload": {"citation_count_delta": 1},
        },
        {
            "event_type": "policy.changed",
            "actor_ids": ("researcher:sol",),
            "payload": {
                "policy_id": "policy:open-review-window",
                "target_institution": "Peer Review Exchange",
                "change": "Synthetic open-review window enabled",
            },
        },
        {
            "event_type": "resource.balance_reported",
            "actor_ids": ("researcher:aya",),
            "payload": {
                "opening_balance": 100,
                "closing_balance": 120,
                "opening_active": True,
                "closing_active": True,
                "residual": 0,
            },
        },
        {
            "event_type": "resource.balance_reported",
            "actor_ids": ("researcher:mino",),
            "payload": {
                "opening_balance": 100,
                "closing_balance": 100,
                "opening_active": True,
                "closing_active": True,
                "residual": 0,
            },
        },
        {
            "event_type": "resource.balance_reported",
            "actor_ids": ("researcher:sol",),
            "payload": {
                "opening_balance": 100,
                "closing_balance": 100,
                "opening_active": True,
                "closing_active": True,
                "residual": 0,
            },
        },
        {
            "event_type": "resource.balance_reported",
            "actor_ids": ("researcher:iren",),
            "payload": {
                "opening_balance": 100,
                "closing_balance": 100,
                "opening_active": True,
                "closing_active": True,
                "residual": 0,
            },
        },
        {
            "event_type": "year.completed",
            "payload": {"year": 1},
        },
    ]
    phase_by_type = {
        "agent.registered": 0,
        "research.data_shared": 1,
        "paper.submitted": 2,
        "review.completed": 3,
        "paper.decided": 4,
        "resource.changed": 5,
        "citation.recorded": 5,
        "policy.changed": 5,
        "resource.balance_reported": 6,
        "year.completed": 7,
    }
    return [
        EventEnvelope.create(
            sequence=sequence,
            year=0 if spec["event_type"] == "agent.registered" else 1,
            phase=phase_by_type[spec["event_type"]],
            event_type=spec["event_type"],
            actor_ids=spec.get("actor_ids", ()),
            artifact_ids=spec.get("artifact_ids", ()),
            payload=spec.get("payload", {}),
            provenance={
                "source": "synthetic.vertical-slice-contract-fixture",
                "record": sequence,
                "empirical": False,
            },
        )
        for sequence, spec in enumerate(specs)
    ]


def vertical_slice_presentation(
    events: list[EventEnvelope],
) -> tuple[dict[str, Any], dict[str, Any]]:
    by_type = {event.event_type: event for event in events}
    registration = {
        event.actor_ids[0]: event
        for event in events
        if event.event_type == "agent.registered"
    }
    lab = _institution_id("Noctiluca Knowledge Lab")
    exchange = _institution_id("Peer Review Exchange")
    bureau = _institution_id("Civic Funding Bureau")
    publication = _institution_id("Noctiluca Publication Spine")

    placements = [
        _placement(lab, 122, 126, registration["researcher:aya"].event_id),
        _placement(exchange, 334, 112, registration["researcher:mino"].event_id),
        _placement(bureau, 252, 222, registration["researcher:sol"].event_id),
        _placement(
            publication, 420, 238, registration["researcher:iren"].event_id
        ),
        _placement(
            "researcher:aya", 144, 164, registration["researcher:aya"].event_id
        ),
        _placement(
            "researcher:mino", 350, 154, registration["researcher:mino"].event_id
        ),
        _placement(
            "researcher:sol", 266, 242, registration["researcher:sol"].event_id
        ),
        _placement(
            "researcher:iren", 426, 252, registration["researcher:iren"].event_id
        ),
        _placement(
            "paper:arcology-signals",
            238,
            132,
            by_type["paper.submitted"].event_id,
        ),
    ]

    flow_specs = [
        (
            "data", lab, exchange, "research.data_shared", 13_700,
            "#20e3ff", "DATA // shared",
        ),
        (
            "paper", lab, exchange, "paper.submitted", 17_100,
            "#ffcf5a", "PAPER // submitted",
        ),
        (
            "review", exchange, lab, "review.completed", 20_500,
            "#ff4fd8", "REVIEW // returned",
        ),
        (
            "paper", exchange, publication, "paper.decided", 24_000,
            "#ffcf5a", "PAPER // published",
        ),
        (
            "funding", bureau, lab, "resource.changed", 27_400,
            "#80ff72", "FUNDING // +20",
        ),
        (
            "citation", publication, lab, "citation.recorded", 30_800,
            "#a98cff", "CITATION // +1",
        ),
        (
            "policy", bureau, exchange, "policy.changed", 34_200,
            "#ff7657", "POLICY // changed",
        ),
    ]
    flows: list[dict[str, Any]] = []
    for index, spec in enumerate(flow_specs):
        flow_type, source, target, event_type, at, color, label = spec
        flow_id = f"flow:{index + 1}:{flow_type}"
        source_event = by_type[event_type]
        flows.append({
            "id": flow_id,
            "kind": "flow",
            "flow_type": flow_type,
            "from_entity_id": source,
            "to_entity_id": target,
            "artifact_id": (
                "paper:arcology-signals"
                if flow_type in {"paper", "review", "citation"}
                else None
            ),
            "color": color,
            "label": label,
            **_trace(
                "derived",
                event_ids=(source_event.event_id,),
                logical_timestamp_ms=at,
                duration_ms=4_200,
                causal_parent_id=(flows[-1]["id"] if flows else None),
            ),
        })

    action_specs = [
        (
            "aya-to-instrument", "researcher:aya", "move",
            (144, 164), (112, 130), 9_600, 1_400,
            (registration["researcher:aya"].event_id,),
            "Aya crosses the laboratory floor",
        ),
        (
            "aya-experiment", "researcher:aya", "experiment",
            (112, 130), (112, 130), 11_000, 3_200,
            (by_type["research.data_shared"].event_id,),
            "Aya operates the sample instrument",
        ),
        (
            "aya-to-terminal", "researcher:aya", "move",
            (112, 130), (142, 130), 14_200, 800,
            (by_type["paper.submitted"].event_id,),
            "Aya moves to the writing terminal",
        ),
        (
            "aya-write", "researcher:aya", "write",
            (142, 130), (142, 130), 15_000, 2_600,
            (by_type["paper.submitted"].event_id,),
            "Aya prepares the submitted paper",
        ),
        (
            "mino-to-review-cell", "researcher:mino", "move",
            (350, 154), (331, 116), 17_000, 900,
            (by_type["paper.submitted"].event_id,),
            "Mino enters an anonymous review cell",
        ),
        (
            "mino-review", "researcher:mino", "review",
            (331, 116), (331, 116), 17_900, 3_100,
            (by_type["review.completed"].event_id,),
            "Mino reviews the submitted paper",
        ),
        (
            "aya-to-revision-bench", "researcher:aya", "move",
            (142, 130), (116, 132), 20_500, 700,
            (by_type["review.completed"].event_id,),
            "Aya returns to the revision bench",
        ),
        (
            "aya-revise", "researcher:aya", "revise",
            (116, 132), (116, 132), 21_200, 3_300,
            (
                by_type["review.completed"].event_id,
                by_type["paper.decided"].event_id,
            ),
            "Aya works through the completed review",
        ),
        (
            "iren-to-publication-console", "researcher:iren", "move",
            (426, 252), (409, 211), 22_600, 1_000,
            (by_type["paper.decided"].event_id,),
            "Iren enters the publication repository",
        ),
        (
            "iren-publish", "researcher:iren", "publish",
            (409, 211), (409, 211), 23_600, 4_600,
            (by_type["paper.decided"].event_id,),
            "Iren deposits the accepted paper",
        ),
        (
            "sol-to-ledger", "researcher:sol", "move",
            (266, 242), (248, 214), 24_700, 1_000,
            (by_type["resource.changed"].event_id,),
            "Sol enters the allocation ledger",
        ),
        (
            "sol-allocate", "researcher:sol", "allocate",
            (248, 214), (248, 214), 25_700, 4_200,
            (by_type["resource.changed"].event_id,),
            "Sol authorizes the grant allocation",
        ),
        (
            "aya-receive-funding", "researcher:aya", "receive",
            (116, 132), (116, 132), 27_400, 3_500,
            (by_type["resource.changed"].event_id,),
            "Aya receives a capacity increase",
        ),
        (
            "sol-cite", "researcher:sol", "cite",
            (248, 214), (248, 214), 30_500, 3_600,
            (by_type["citation.recorded"].event_id,),
            "Sol records a citation link",
        ),
        (
            "aya-read-citation", "researcher:aya", "read",
            (116, 132), (116, 132), 30_800, 3_500,
            (by_type["citation.recorded"].event_id,),
            "Aya inspects the new citation",
        ),
        (
            "sol-policy", "researcher:sol", "policy",
            (248, 214), (248, 214), 34_000, 5_300,
            (by_type["policy.changed"].event_id,),
            "Sol transmits the policy change",
        ),
        (
            "mino-policy", "researcher:mino", "policy",
            (331, 116), (331, 116), 34_200, 4_000,
            (by_type["policy.changed"].event_id,),
            "Mino receives the open-review policy",
        ),
    ]
    actions: list[dict[str, Any]] = []
    previous_action_by_actor: dict[str, str] = {}
    for (
        action_id, actor_id, action_type, start, end, at, duration,
        source_event_ids, label,
    ) in action_specs:
        actions.append({
            "id": f"action:{action_id}",
            "kind": "actor_action",
            "actor_entity_id": actor_id,
            "action_type": action_type,
            "start": {"x": start[0], "y": start[1]},
            "end": {"x": end[0], "y": end[1]},
            "label": label,
            **_trace(
                "derived",
                event_ids=source_event_ids,
                logical_timestamp_ms=at,
                duration_ms=duration,
                causal_parent_id=previous_action_by_actor.get(actor_id),
            ),
        })
        previous_action_by_actor[actor_id] = f"action:{action_id}"

    camera_cues = [
        {
            "id": "camera:establish",
            "kind": "camera",
            "target_entity_id": lab,
            "zoom": 1.0,
            **_trace(
                "derived",
                event_ids=(registration["researcher:aya"].event_id,),
                logical_timestamp_ms=0,
                duration_ms=3_000,
            ),
        },
        {
            "id": "camera:exchange",
            "kind": "camera",
            "target_entity_id": exchange,
            "zoom": 1.2,
            **_trace(
                "derived",
                event_ids=(by_type["review.completed"].event_id,),
                logical_timestamp_ms=16_000,
                duration_ms=8_000,
                causal_parent_id="flow:2:paper",
            ),
        },
        {
            "id": "camera:system",
            "kind": "camera",
            "target_entity_id": publication,
            "zoom": 0.9,
            **_trace(
                "derived",
                event_ids=(by_type["paper.decided"].event_id,),
                logical_timestamp_ms=22_000,
                duration_ms=8_000,
                causal_parent_id="flow:3:review",
            ),
        },
        {
            "id": "camera:civic-system",
            "kind": "camera",
            "target_entity_id": bureau,
            "zoom": 0.9,
            **_trace(
                "derived",
                event_ids=(by_type["policy.changed"].event_id,),
                logical_timestamp_ms=30_000,
                duration_ms=12_000,
                causal_parent_id="flow:6:citation",
            ),
        },
    ]
    choreography = {
        "duration_ms": 48_000,
        "coordinate_space": {"width": 480, "height": 270, "unit": "logical_pixel"},
        "placements": placements,
        "flows": flows,
        "actions": actions,
        "camera_cues": camera_cues,
    }

    ambient = {
        "actors": [
            {
                "id": "ambient:courier-drone-1",
                "kind": "courier_drone",
                "path": [[40, 54], [222, 36], [448, 72]],
                "label": "decorative traffic — not a simulated agent",
                **_trace(
                    "ambient",
                    logical_timestamp_ms=0,
                    duration_ms=48_000,
                ),
            }
        ],
        "effects": [
            {
                "id": "ambient:rain-field",
                "kind": "rain",
                "seed": 261001257,
                "label": "atmosphere only",
                **_trace(
                    "ambient",
                    logical_timestamp_ms=0,
                    duration_ms=48_000,
                ),
            }
        ],
    }
    return choreography, ambient


def _placement(entity_id: str, x: int, y: int, event_id: str) -> dict[str, Any]:
    return {
        "id": f"placement:{entity_id}",
        "kind": "placement",
        "entity_id": entity_id,
        "x": x,
        "y": y,
        **_trace("derived", event_ids=(event_id,)),
    }


def vertical_slice_metadata() -> dict[str, Any]:
    return {
        "title": "NOCTILUCA // Replay Contract Vertical Slice",
        "source_label": "synthetic replay-view v2 contract fixture",
        "source_kind": "synthetic_contract_fixture",
        "empirical": False,
        "disclosure": (
            "Hand-authored deterministic four-researcher fixture for renderer "
            "validation. It is not "
            "an experimental run or evidence about a real ScienceUtopia system. All "
            "six semantic flow types cite synthetic canonical fixture events; ambient "
            "activity is isolated and makes no scientific claim."
        ),
    }


__all__ = [
    "vertical_slice_events",
    "vertical_slice_metadata",
    "vertical_slice_presentation",
]
