"""Canonical evidence projection for the generative miniature lab."""
from __future__ import annotations

from typing import Any, Mapping

from utopia.replay.events import EventEnvelope, validate_references
from utopia.system import SystemSpec
from utopia.system.programs import digest


def program_world_events(
    system: SystemSpec, world: Mapping[str, Any], run: Mapping[str, Any],
) -> list[dict[str, Any]]:
    actors = [f"researcher-{index}" for index in range(world["population"])]
    events: list[EventEnvelope] = []

    def emit(kind: str, year: int, phase: int, payload: Mapping[str, Any],
             *, actor_ids=(), mechanism_id: str | None = None):
        events.append(EventEnvelope.create(
            sequence=len(events), year=year, phase=phase, event_type=kind,
            actor_ids=actor_ids, payload=payload,
            provenance={"system_fingerprint": system.fingerprint,
                        "world_sha256": digest(world),
                        "mechanism_id": mechanism_id,
                        "backend": "discrete-numeric-program-world-v1"},
        ))

    for index, actor in enumerate(actors):
        emit("agent.registered", 0, 0, {
            key: world[key][index] for key in ("quality", "novelty", "resources", "knowledge")
        }, actor_ids=(actor,))
    nodes = {node.mechanism_id: node for node in system.mechanisms}
    for frame in run["history"]:
        for phase, name in enumerate(frame["execution_order"]):
            emit("mechanism.program.executed", frame["period"], phase + 1, {
                "values": frame["mechanisms"][name],
                "input_signal": frame["signals"][name],
                "program_sha256": digest(nodes[name].parameters["program"]),
            }, actor_ids=actors, mechanism_id=name)
        emit("world.period.completed", frame["period"], len(nodes) + 1, {
            "world": frame["world"], "production": frame["production"],
            "allocation": frame["allocation"],
        }, actor_ids=actors)
    errors = validate_references(events)
    if errors:
        raise ValueError("invalid lab event references: " + "; ".join(errors))
    return [event.to_dict() for event in events]


def viewer_entry(
    label: str, system: SystemSpec, world: Mapping[str, Any], outer: Mapping[str, Any],
) -> dict[str, Any]:
    run = next((row for row in outer["runs"] if row["world_sha256"] == digest(world)), None)
    if run is None or not run["history"]:
        raise ValueError("viewer requires recorded history for its exact world")
    events = program_world_events(system, world, run)
    return {
        "label": label, "system_spec": system.to_dict(),
        "system_fingerprint": system.fingerprint, "world_sha256": digest(world),
        "loss": outer["loss"], "loss_spec_sha256": outer["loss_spec_sha256"],
        "metrics": run["metrics"], "frames": run["history"],
        "events": events, "event_stream_sha256": digest(events),
        "world_source": world["source"],
    }
