import pytest

from utopia.optimization.generative_system import seed_generative_system
from utopia.replay.program_lab import program_world_events, viewer_entry
from utopia.system.program_world import evaluate_program_system, initial_world, make_world_loss
from utopia.system.programs import digest


def test_projected_world_events_retain_system_world_and_program_identities():
    system = seed_generative_system()
    world = initial_world(811)
    outer = evaluate_program_system(system, [world], make_world_loss("production"), periods=2, record=True)
    entry = viewer_entry("Generated system", system, world, outer)
    events = entry["events"]
    assert [row["sequence"] for row in events] == list(range(len(events)))
    assert all(row["provenance"]["system_fingerprint"] == system.fingerprint for row in events)
    assert all(row["provenance"]["world_sha256"] == digest(world) for row in events)
    assert len([row for row in events if row["event_type"] == "agent.registered"]) == 6
    assert len([row for row in events if row["event_type"] == "world.period.completed"]) == 2
    assert entry["event_stream_sha256"] == digest(events)
    assert events == program_world_events(system, world, outer["runs"][0])


def test_viewer_rejects_a_different_world_instead_of_showing_its_agent_state():
    system = seed_generative_system()
    outer = evaluate_program_system(system, [initial_world(811)], make_world_loss("production"), record=True)
    with pytest.raises(ValueError, match="exact world"):
        viewer_entry("Wrong world", system, initial_world(821), outer)
