from __future__ import annotations

import json

import pytest

from utopia.optimization.blackbox import AdaptiveRandomSearch, evaluate_round
from utopia.optimization.government_structural import (
    government_engineering_loss,
    government_structural_space,
)
from utopia.optimization.production_structural import (
    execute_production_structural_candidate,
    observe_production_structural_suggestion,
    production_structural_registry,
)
from utopia.optimization.structural_space import StructuralSelection
from utopia.system import (
    ChannelKind,
    DeliveredValue,
    DeterministicGraphRunner,
    GraphCheckpoint,
    GraphRuntimeError,
)
from utopia.system.production.governance import (
    POLICY_SCHEMA_VERSION,
    parse_policy_decision,
    resolve_active_policy,
)


def _candidate(
    government: str | None,
    *,
    evaluation_latency: str | None = "one-period",
    funding_latency: str | None = "one-period",
) -> dict:
    enabled = government is not None
    space = government_structural_space()
    return space.build(
        StructuralSelection(
            {
                "workload": "deterministic-v1",
                "evaluation": "conference-rate",
                "funding": "compact-ranked",
                "publication": "paper-tracker",
                "government": government,
            },
            {
                "review-input": "instant",
                "funding-input": "instant",
                "publication-flow": "instant",
                "observe-decisions": "instant" if enabled else None,
                "observe-allocations": "instant" if enabled else None,
                "observe-publications": "instant" if enabled else None,
                "policy-to-evaluation": evaluation_latency if enabled else None,
                "policy-to-funding": funding_latency if enabled else None,
            },
        )
    ).to_dict()


def _policy(*, version: int = 1, issuer: str = "government") -> dict:
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "policy_id": f"policy-{version}",
        "policy_version": version,
        "issuer_id": issuer,
        "system_fingerprint": "a" * 64,
        "issued_period": version,
        "observed_event_ids": [f"event-{version}"],
        "directives": {
            "evaluation": {"acceptance_rate": 0.75},
            "funding": {"award_amount_multiplier": 1.5},
        },
    }


def _delivered(policy: dict) -> DeliveredValue:
    return DeliveredValue(
        channel=ChannelKind.CONSTRAINT,
        artifact_type="government-policy",
        payload=policy,
        actor_ids=(),
        artifact_ids=(),
        lineage_event_ids=("government-event",),
        source_mechanism=policy["issuer_id"],
        source_port="evaluation_policies",
        emitted_period=policy["issued_period"],
        available_period=policy["issued_period"] + 1,
    )


def test_policy_schema_and_consumer_resolution_fail_closed() -> None:
    valid = parse_policy_decision(_policy())
    active = resolve_active_policy(
        (_delivered(valid),),
        target="evaluation",
        active=None,
        system_fingerprint="a" * 64,
    )

    assert active == {
        "policy_id": "policy-1",
        "policy_version": 1,
        "issuer_id": "government",
        "directive": {"acceptance_rate": 0.75},
    }

    unknown = {**_policy(), "unversioned_extra": True}
    with pytest.raises(GraphRuntimeError, match="fields do not match"):
        parse_policy_decision(unknown)
    wrong_directive = _policy()
    wrong_directive["directives"]["evaluation"]["unknown"] = 1
    with pytest.raises(GraphRuntimeError, match="evaluation directive fields"):
        parse_policy_decision(wrong_directive)
    with pytest.raises(GraphRuntimeError, match="stale or replayed"):
        resolve_active_policy(
            (_delivered(_policy(version=1)),),
            target="evaluation",
            active=active,
            system_fingerprint="a" * 64,
        )
    wrong_system = _policy(version=2)
    wrong_system["system_fingerprint"] = "b" * 64
    with pytest.raises(GraphRuntimeError, match="different system"):
        resolve_active_policy(
            (_delivered(wrong_system),),
            target="evaluation",
            active=active,
            system_fingerprint="a" * 64,
        )
    with pytest.raises(GraphRuntimeError, match="multiple issuers"):
        resolve_active_policy(
            (
                _delivered(_policy(version=2)),
                _delivered(_policy(version=3, issuer="other-government")),
            ),
            target="evaluation",
            active=active,
            system_fingerprint="a" * 64,
        )


def test_government_observes_events_and_changes_two_downstream_families() -> None:
    space = government_structural_space()
    absent = execute_production_structural_candidate(space, _candidate(None))
    responsive = execute_production_structural_candidate(
        space, _candidate("event-responsive")
    )
    threshold = execute_production_structural_candidate(
        space, _candidate("cumulative-threshold")
    )

    assert absent.summary.accepted == 6
    assert absent.summary.total_awarded == 100.0
    assert absent.summary.government_policies == 0
    assert responsive.summary.accepted == 9
    assert responsive.summary.total_awarded == 175.0
    assert responsive.summary.government_policies == 4
    assert threshold.summary.accepted == 8
    assert threshold.summary.total_awarded == 150.0
    assert threshold.summary.government_policies == 2

    government_events = [
        event
        for event in responsive.result.events
        if event.event_type == "government.policy_decided"
    ]
    assert [event.payload["policy_version"] for event in government_events] == [
        1,
        2,
        3,
        4,
    ]
    assert all(event.provenance["input_event_ids"] for event in government_events)
    governed_evaluation = next(
        event
        for event in responsive.result.events
        if event.event_type == "evaluation.paper_decided" and event.year == 1
    )
    governed_funding = next(
        event
        for event in responsive.result.events
        if event.event_type == "funding.awarded" and event.year == 1
    )
    assert governed_evaluation.provenance["government_policy_version"] == 1
    assert governed_funding.provenance["government_policy_version"] == 1

    government_state = responsive.result.checkpoint.mechanism_states["government"]
    assert government_state["observed_value_count"] == 24
    assert government_state["next_policy_version"] == 5
    assert len(government_state["observed_event_ids"]) == 24
    assert responsive.result.checkpoint.mechanism_states["evaluation"][
        "active_policy"
    ]["policy_version"] == 3
    assert responsive.result.checkpoint.mechanism_states["funding"][
        "active_policy"
    ]["policy_version"] == 3


def test_government_checkpoint_resume_and_structural_identity() -> None:
    space = government_structural_space()
    candidate = _candidate("event-responsive")
    changed = _candidate("event-responsive", evaluation_latency="two-period")
    spec = space.decode(candidate)
    changed_spec = space.decode(changed)

    uninterrupted = DeterministicGraphRunner(
        spec, production_structural_registry()
    ).run(periods=4)
    first = DeterministicGraphRunner(spec, production_structural_registry()).run(
        periods=2
    )
    checkpoint = GraphCheckpoint.from_dict(
        json.loads(json.dumps(first.checkpoint.to_dict(), sort_keys=True))
    )
    resumed = DeterministicGraphRunner(spec, production_structural_registry()).run(
        periods=2, checkpoint=checkpoint
    )

    assert [event.to_dict() for event in (*first.events, *resumed.events)] == [
        event.to_dict() for event in uninterrupted.events
    ]
    assert resumed.checkpoint.to_dict() == uninterrupted.checkpoint.to_dict()
    assert changed_spec.fingerprint != spec.fingerprint
    with pytest.raises(GraphRuntimeError, match="fingerprint does not match"):
        DeterministicGraphRunner(
            changed_spec, production_structural_registry()
        ).run(periods=1, checkpoint=checkpoint)


def test_government_space_exposes_presence_implementation_edges_and_latency() -> None:
    space = government_structural_space()
    runs = [
        execute_production_structural_candidate(
            space, space.build(selection).to_dict(), periods=2
        )
        for selection in space.selections
    ]
    kinds = {
        mutation.kind
        for selection in space.selections
        for mutation, _neighbor in space.neighbors(space.build(selection).to_dict())
    }

    assert space.candidate_count == 145
    assert len({run.spec.fingerprint for run in runs}) == 145
    assert kinds == {"node-presence", "implementation", "edge-presence", "latency"}
    assert {selection.nodes["government"] for selection in space.selections} == {
        None,
        "event-responsive",
        "cumulative-threshold",
    }


def test_black_box_round_explores_government_structure() -> None:
    space = government_structural_space()
    optimizer = AdaptiveRandomSearch(space, seed=110, initial_random=5)
    suggestions, observations = evaluate_round(
        optimizer,
        lambda suggestion: observe_production_structural_suggestion(
            space,
            suggestion,
            loss_function=government_engineering_loss,
        ),
        count=5,
    )
    selections = [space.selection(suggestion.candidate) for suggestion in suggestions]

    assert {selection.nodes["government"] for selection in selections} == {
        None,
        "event-responsive",
        "cumulative-threshold",
    }
    assert {
        selection.edges["policy-to-evaluation"]
        for selection in selections
        if selection.edges["policy-to-evaluation"] is not None
    } == {"one-period", "two-period"}
    assert len({observation.loss for observation in observations}) > 1
    assert all(
        observation.metadata["system_fingerprint"]
        == space.candidate_fingerprint(observation.candidate)
        for observation in observations
    )
