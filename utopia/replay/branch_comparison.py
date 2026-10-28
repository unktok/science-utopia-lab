"""Deterministic branch-comparison fixture for the NOCTILUCA game UI.

The two futures share canonical event objects through the completed review and
then contain explicit, branch-local intervention and outcome events.  This is a
renderer/evidence contract fixture, not a causal experiment or policy result.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .events import EventEnvelope, canonical_event_stream_hash
from .vertical_slice import vertical_slice_events, vertical_slice_presentation
from .viewer import build_viewer_payload_v2


BRANCH_MANIFEST_SCHEMA = "scienceutopia.replay-branch-manifest.v1"
SHARED_PREFIX_COUNT = 7


def _suffix(branch_id: str) -> list[dict[str, Any]]:
    if branch_id == "open-synthesis":
        return [
            {
                "event_type": "policy.changed",
                "actor_ids": ("researcher:sol",),
                "payload": {
                    "policy_id": "policy:open-synthesis",
                    "target_institution": "Peer Review Exchange",
                    "change": "Open synthesis and signed response window enabled",
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
        ]
    if branch_id == "sealed-panel":
        return [
            {
                "event_type": "policy.changed",
                "actor_ids": ("researcher:sol",),
                "payload": {
                    "policy_id": "policy:sealed-panel",
                    "target_institution": "Peer Review Exchange",
                    "change": "Sealed panel with an additional revision gate enabled",
                },
            },
            {
                "event_type": "paper.decided",
                "actor_ids": ("researcher:aya",),
                "artifact_ids": ("paper:arcology-signals",),
                "payload": {
                    "decision": "revise",
                    "score": 4,
                    "conference": "Peer Review Exchange",
                    "submission_round": 0,
                },
            },
            {
                "event_type": "resource.changed",
                "actor_ids": ("researcher:aya",),
                "payload": {
                    "category": "bridge_grant",
                    "delta": 5,
                    "requested_delta": 20,
                    "balance_before": 100,
                    "balance_after": 105,
                    "active_after": True,
                    "uncollected_cost": 15,
                    "source_institution": "Civic Funding Bureau",
                },
            },
            {
                "event_type": "citation.recorded",
                "actor_ids": ("researcher:sol", "researcher:aya"),
                "artifact_ids": ("paper:arcology-signals",),
                "payload": {"citation_count_delta": 1},
            },
        ]
    raise ValueError(f"Unknown branch id: {branch_id}")


def branch_events(branch_id: str) -> list[EventEnvelope]:
    shared = vertical_slice_events()[:SHARED_PREFIX_COUNT]
    suffix = _suffix(branch_id)
    reports = [
        {
            "event_type": "resource.balance_reported",
            "actor_ids": (actor_id,),
            "payload": {
                "opening_balance": 100,
                "closing_balance": (
                    120 if branch_id == "open-synthesis" else 105
                ) if actor_id == "researcher:aya" else 100,
                "opening_active": True,
                "closing_active": True,
                "residual": 0,
            },
        }
        for actor_id in (
            "researcher:aya", "researcher:mino", "researcher:sol", "researcher:iren"
        )
    ]
    specs = suffix + reports + [{"event_type": "year.completed", "payload": {"year": 1}}]
    phase_by_type = {
        "policy.changed": 4,
        "paper.decided": 5,
        "resource.changed": 5,
        "citation.recorded": 5,
        "resource.balance_reported": 6,
        "year.completed": 7,
    }
    events = list(shared)
    for sequence, spec in enumerate(specs, start=SHARED_PREFIX_COUNT):
        events.append(EventEnvelope.create(
            sequence=sequence,
            year=1,
            phase=phase_by_type[spec["event_type"]],
            event_type=spec["event_type"],
            actor_ids=spec.get("actor_ids", ()),
            artifact_ids=spec.get("artifact_ids", ()),
            payload=spec.get("payload", {}),
            provenance={
                "source": "synthetic.branch-comparison-contract-fixture",
                "branch": branch_id,
                "record": sequence,
                "empirical": False,
            },
        ))
    return events


def branch_payload(branch_id: str) -> dict[str, Any]:
    events = branch_events(branch_id)
    choreography, ambient = vertical_slice_presentation(events)
    choreography = deepcopy(choreography)
    intervention = events[SHARED_PREFIX_COUNT]
    resource = next(event for event in events if event.event_type == "resource.changed")
    for flow in choreography["flows"]:
        if flow["flow_type"] == "funding":
            flow["label"] = f"FUNDING // {int(resource.payload['delta']):+d}"
        elif flow["flow_type"] == "policy":
            flow["label"] = f"POLICY // {branch_id.replace('-', ' ')}"
    for action in choreography["actions"]:
        if action["action_type"] == "policy":
            action["label"] = str(intervention.payload["change"])
    return build_viewer_payload_v2(
        events,
        metadata={
            "title": f"NOCTILUCA // {branch_id}",
            "run_id": "synthetic-intervention-fork-v1",
            "branch": branch_id,
            "source_kind": "synthetic_branch_contract_fixture",
            "empirical": False,
            "disclosure": (
                "Hand-authored branch fixture for renderer validation. The branch "
                "outcomes are canonical fixture records, not simulated causal "
                "estimates or evidence for a science policy."
            ),
        },
        choreography=choreography,
        ambient=ambient,
    )


def branch_manifest(payloads: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    ordered_ids = ("open-synthesis", "sealed-panel")
    streams = [branch_events(branch_id) for branch_id in ordered_ids]
    shared_prefix = streams[0][:SHARED_PREFIX_COUNT]
    if any(stream[:SHARED_PREFIX_COUNT] != shared_prefix for stream in streams[1:]):
        raise ValueError("Branch streams do not share the declared canonical prefix")
    colors = {"open-synthesis": "#39f5c8", "sealed-panel": "#f653d8"}
    labels = {"open-synthesis": "OPEN SYNTHESIS", "sealed-panel": "SEALED PANEL"}
    for branch_id, stream in zip(ordered_ids, streams, strict=True):
        actual_hash = canonical_event_stream_hash(stream)
        if payloads[branch_id].get("stream_hash") != actual_hash:
            raise ValueError(f"{branch_id}: payload stream hash does not match events")
    return {
        "schema_version": BRANCH_MANIFEST_SCHEMA,
        "comparison_id": "synthetic-intervention-fork-v1",
        "source_kind": "synthetic_branch_contract_fixture",
        "empirical": False,
        "disclosure": (
            "Two hand-authored renderer-contract futures share one canonical "
            "prefix. Differences demonstrate evidence navigation, not policy "
            "effects, optimization results, or causal inference."
        ),
        "shared_origin": {
            "event_count": SHARED_PREFIX_COUNT,
            "stream_hash": canonical_event_stream_hash(shared_prefix),
            "last_event_id": shared_prefix[-1].event_id,
            "split_after_event_type": shared_prefix[-1].event_type,
        },
        "branches": [
            {
                "id": branch_id,
                "label": labels[branch_id],
                "color": colors[branch_id],
                "replay_url": f"/data/branch-{branch_id}.replay.json",
                "stream_hash": str(payloads[branch_id]["stream_hash"]),
                "intervention_event_id": streams[index][SHARED_PREFIX_COUNT].event_id,
            }
            for index, branch_id in enumerate(ordered_ids)
        ],
    }


__all__ = [
    "BRANCH_MANIFEST_SCHEMA",
    "SHARED_PREFIX_COUNT",
    "branch_events",
    "branch_manifest",
    "branch_payload",
]
