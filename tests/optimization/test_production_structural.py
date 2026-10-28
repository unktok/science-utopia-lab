from __future__ import annotations

import json

import pytest

from utopia.optimization.blackbox import AdaptiveRandomSearch, evaluate_round
from utopia.optimization.production_structural import (
    engineering_demonstration_loss,
    execute_production_structural_candidate,
    observe_production_structural_suggestion,
    production_structural_registry,
    production_structural_space,
)
from utopia.optimization.structural_space import StructuralSelection
from utopia.system import DeterministicGraphRunner, GraphCheckpoint, GraphRuntimeError


def _candidate(
    *,
    policy: str = "evaluation-rate",
    review_latency: str = "instant",
    funding: bool = True,
    funding_latency: str | None = "instant",
    publication: bool = True,
    publication_latency: str | None = "instant",
) -> dict:
    space = production_structural_space()
    return space.build(
        StructuralSelection(
            {
                "workload": "deterministic-v1",
                "evaluation-policy": policy,
                "funding": "compact-funding" if funding else None,
                "publication": "paper-tracker" if publication else None,
            },
            {
                "review-input": review_latency,
                "funding-input": funding_latency if funding else None,
                "publication-flow": publication_latency if publication else None,
            },
        )
    ).to_dict()


def test_production_grammar_covers_legal_structural_mutations() -> None:
    space = production_structural_space()
    runs = [
        execute_production_structural_candidate(
            space, space.build(selection).to_dict(), periods=2
        )
        for selection in space.selections
    ]
    kinds = {
        mutation.kind
        for selection in space.selections
        for mutation, _candidate_value in space.neighbors(
            space.build(selection).to_dict()
        )
    }

    assert space.candidate_count == 64
    assert len({run.spec.fingerprint for run in runs}) == space.candidate_count
    assert kinds == {"node-presence", "family", "edge-presence", "latency"}
    assert {
        selection.nodes["evaluation-policy"] for selection in space.selections
    } == {"evaluation-rate", "governed-fixed-slots"}
    assert {selection.nodes["funding"] for selection in space.selections} == {
        None,
        "compact-funding",
    }
    assert {selection.nodes["publication"] for selection in space.selections} == {
        None,
        "paper-tracker",
    }


def test_structure_changes_production_results_loss_and_fingerprint() -> None:
    space = production_structural_space()
    full_rate = _candidate()
    governed_without_downstream = _candidate(
        policy="governed-fixed-slots",
        review_latency="delayed",
        funding=False,
        funding_latency=None,
        publication=False,
        publication_latency=None,
    )
    delayed_publication = _candidate(publication_latency="delayed")

    rate_run = execute_production_structural_candidate(space, full_rate)
    governed_run = execute_production_structural_candidate(
        space, governed_without_downstream
    )
    delayed_run = execute_production_structural_candidate(space, delayed_publication)

    assert len(
        {
            rate_run.spec.fingerprint,
            governed_run.spec.fingerprint,
            delayed_run.spec.fingerprint,
        }
    ) == 3
    assert rate_run.summary.accepted == 6
    assert governed_run.summary.accepted == 3
    assert rate_run.summary.funding_awards == 4
    assert governed_run.summary.funding_awards == 0
    assert rate_run.summary.publication_records == 10
    assert delayed_run.summary.publication_records == 7
    assert len(
        {
            engineering_demonstration_loss(rate_run),
            engineering_demonstration_loss(governed_run),
            engineering_demonstration_loss(delayed_run),
        }
    ) == 3


def test_production_candidates_share_ask_execute_loss_tell_boundary() -> None:
    space = production_structural_space()
    optimizer = AdaptiveRandomSearch(space, seed=1, initial_random=5)

    suggestions, observations = evaluate_round(
        optimizer,
        lambda suggestion: observe_production_structural_suggestion(
            space, suggestion
        ),
        count=5,
    )
    selections = [space.selection(suggestion.candidate) for suggestion in suggestions]

    assert {selection.nodes["evaluation-policy"] for selection in selections} == {
        "evaluation-rate",
        "governed-fixed-slots",
    }
    assert {selection.nodes["funding"] for selection in selections} == {
        None,
        "compact-funding",
    }
    assert {selection.nodes["publication"] for selection in selections} == {
        None,
        "paper-tracker",
    }
    assert len({observation.loss for observation in observations}) > 1
    for observation in observations:
        assert observation.metadata["system_fingerprint"] == (
            space.candidate_fingerprint(observation.candidate)
        )
        assert observation.metadata["summary"]["mechanism_count"] >= 2

    adaptive = optimizer.ask(1)[0]
    assert adaptive.phase == "adaptive"
    adaptive_observation = observe_production_structural_suggestion(space, adaptive)
    optimizer.tell([adaptive_observation])
    assert optimizer.state_dict()["pending"] == []


def test_checkpoint_resumes_same_structure_and_rejects_changed_structure() -> None:
    space = production_structural_space()
    candidate = _candidate(publication_latency="delayed")
    changed = _candidate(policy="governed-fixed-slots", publication_latency="delayed")
    spec = space.decode(candidate)
    changed_spec = space.decode(changed)

    uninterrupted = DeterministicGraphRunner(
        spec, production_structural_registry()
    ).run(periods=4)
    first = DeterministicGraphRunner(spec, production_structural_registry()).run(
        periods=2
    )
    restored = GraphCheckpoint.from_dict(
        json.loads(json.dumps(first.checkpoint.to_dict(), sort_keys=True))
    )
    resumed = DeterministicGraphRunner(spec, production_structural_registry()).run(
        periods=2, checkpoint=restored
    )

    assert [event.to_dict() for event in (*first.events, *resumed.events)] == [
        event.to_dict() for event in uninterrupted.events
    ]
    assert resumed.checkpoint.to_dict() == uninterrupted.checkpoint.to_dict()
    assert changed_spec.fingerprint != spec.fingerprint
    with pytest.raises(GraphRuntimeError, match="fingerprint does not match"):
        DeterministicGraphRunner(
            changed_spec, production_structural_registry()
        ).run(periods=1, checkpoint=restored)
