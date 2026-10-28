from __future__ import annotations

from dataclasses import replace
import json

import pytest

from utopia.system import (
    ArtifactTypeSpec,
    ChannelKind,
    ConnectionSpec,
    DeterministicGraphRunner,
    GraphCheckpoint,
    GraphRuntimeError,
    MechanismFamily,
    MechanismRegistry,
    MechanismResult,
    MechanismSpec,
    MechanismValue,
    PortSpec,
    ScheduleSpec,
    SystemSpec,
)
from utopia.system.production import (
    COMPACT_RANKED_ALLOCATION,
    register_compact_funding_mechanism,
)


PANEL_SOURCE = "test.scripted-funding-panel-source-v1"


def _system() -> SystemSpec:
    return SystemSpec(
        "production-funding-checkpoint",
        1,
        artifact_types=(
            ArtifactTypeSpec("funding-panel"),
            ArtifactTypeSpec("resource-allocation"),
        ),
        mechanisms=(
            MechanismSpec(
                "panel-source",
                MechanismFamily.CUSTOM,
                PANEL_SOURCE,
                outputs=(
                    PortSpec("panels", ChannelKind.ARTIFACT, "funding-panel"),
                ),
            ),
            MechanismSpec(
                "ranked-funding",
                MechanismFamily.FUNDING,
                COMPACT_RANKED_ALLOCATION,
                inputs=(
                    PortSpec("panels", ChannelKind.ARTIFACT, "funding-panel"),
                ),
                outputs=(
                    PortSpec(
                        "allocations",
                        ChannelKind.RESOURCE,
                        "resource-allocation",
                    ),
                ),
                parameters={"award_slots": 1, "award_amount": 25},
            ),
        ),
        connections=(
            ConnectionSpec(
                "panel-source",
                "panels",
                "ranked-funding",
                "panels",
                ChannelKind.ARTIFACT,
                latency=1,
            ),
        ),
        schedules=(
            ScheduleSpec("panel-source", 0),
            ScheduleSpec("ranked-funding", 1),
        ),
    )


def _registry() -> MechanismRegistry:
    registry = MechanismRegistry()

    def panel_source(context):
        period = context.period
        payload = {
            "panel_id": f"panel-{period}",
            "applications": [
                {"applicant_id": f"researcher-{period}-a"},
                {"applicant_id": f"researcher-{period}-b"},
            ],
            "compact_result": {"ranked_application_ids": [1, 0]},
        }
        return MechanismResult(
            outputs={
                "panels": (
                    MechanismValue(payload, artifact_ids=(payload["panel_id"],)),
                )
            }
        )

    registry.register(PANEL_SOURCE, 1, panel_source)
    register_compact_funding_mechanism(registry)
    return registry


def test_production_funding_adapter_resumes_identically_with_queued_input() -> None:
    spec = _system()
    uninterrupted = DeterministicGraphRunner(spec, _registry()).run(periods=4)

    first = DeterministicGraphRunner(spec, _registry()).run(periods=2)
    serialized = json.loads(json.dumps(first.checkpoint.to_dict(), sort_keys=True))
    restored = GraphCheckpoint.from_dict(serialized)
    resumed = DeterministicGraphRunner(spec, _registry()).run(
        periods=2, checkpoint=restored
    )

    combined_events = [event.to_dict() for event in (*first.events, *resumed.events)]
    assert combined_events == [event.to_dict() for event in uninterrupted.events]
    assert (*first.trace, *resumed.trace) == uninterrupted.trace
    assert resumed.checkpoint.to_dict() == uninterrupted.checkpoint.to_dict()
    assert GraphCheckpoint.from_dict(serialized).fingerprint == first.checkpoint.fingerprint

    # The pending panel emitted in period 1 survived the JSON checkpoint and
    # the production compact protocol selected application index 1 unchanged.
    assert first.pending_deliveries == 1
    resumed_awards = [event.payload for event in resumed.events]
    assert resumed_awards[0]["panel_id"] == "panel-1"
    assert resumed_awards[0]["recipient_id"] == "researcher-1-b"
    state = resumed.checkpoint.mechanism_states["ranked-funding"]
    assert state["processed_panel_ids"] == ["panel-0", "panel-1", "panel-2"]
    assert state["total_awarded"] == 75.0


def test_checkpoint_is_bound_to_exact_system_and_resume_position() -> None:
    spec = _system()
    checkpoint = DeterministicGraphRunner(spec, _registry()).run(periods=1).checkpoint

    changed = replace(spec, system_id="different-system")
    with pytest.raises(GraphRuntimeError, match="system_id does not match"):
        DeterministicGraphRunner(changed, _registry()).run(
            periods=1, checkpoint=checkpoint
        )
    with pytest.raises(GraphRuntimeError, match="start_period does not equal"):
        DeterministicGraphRunner(spec, _registry()).run(
            periods=1, start_period=10, checkpoint=checkpoint
        )


def test_production_compact_validation_rejects_non_permutation() -> None:
    registry = _registry()

    def invalid_panel(context):
        payload = {
            "panel_id": f"panel-{context.period}",
            "applications": [
                {"applicant_id": "researcher-a"},
                {"applicant_id": "researcher-b"},
            ],
            "compact_result": {"ranked_application_ids": [0, 0]},
        }
        return MechanismResult(
            outputs={"panels": (MechanismValue(payload),)}
        )

    registry.register(PANEL_SOURCE, 1, invalid_panel, replace=True)
    with pytest.raises(GraphRuntimeError, match="complete unique permutation"):
        DeterministicGraphRunner(_system(), registry).run(periods=2)
