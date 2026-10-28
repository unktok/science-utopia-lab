from __future__ import annotations

from dataclasses import replace
import json
import math

import pytest

from utopia.optimization.blackbox import (
    AdaptiveRandomSearch,
    Observation,
    evaluate_round,
)
from utopia.optimization.structural_space import (
    StructuralGrammar,
    StructuralSelection,
    StructuralSystemSpace,
    toy_structural_grammar,
)
from utopia.system import (
    DeterministicGraphRunner,
    MechanismFamily,
    SystemSpec,
    validate_system_spec,
)
from utopia.system.examples import register_example_mechanisms
from utopia.system.runtime import MechanismRegistry


def _space() -> StructuralSystemSpace:
    return StructuralSystemSpace(toy_structural_grammar())


def _registry() -> MechanismRegistry:
    registry = MechanismRegistry()
    register_example_mechanisms(registry)
    return registry


def _candidate(
    space: StructuralSystemSpace,
    *,
    publication: str = "direct",
    funding: str | None = None,
    research: str | None = None,
    edge: str | None = None,
) -> dict:
    return space.build(
        StructuralSelection(
            {
                "publication": publication,
                "funding": funding,
                "research": research,
            },
            {"resource-flow": edge},
        )
    ).to_dict()


def _toy_loss(space: StructuralSystemSpace, candidate: dict) -> tuple[float, object]:
    spec = space.decode(candidate)
    result = DeterministicGraphRunner(spec, _registry()).run(periods=2)
    resources = sum(
        float(event.payload["delta"])
        for event in result.events
        if event.event_type == "resource.changed"
    )
    research = sum(
        event.event_type == "mechanism.decision" for event in result.events
    )
    complexity = len(spec.mechanisms) + len(spec.connections)
    loss = complexity - 0.05 * resources - 2.0 * research
    assert math.isfinite(loss)
    return loss, result


def test_finite_grammar_contains_node_implementation_and_topology_freedom():
    space = _space()

    assert space.candidate_count == 39
    node_values = {
        slot: {selection.nodes[slot] for selection in space.selections}
        for slot in ("publication", "funding", "research")
    }
    edge_values = {
        selection.edges["resource-flow"] for selection in space.selections
    }
    assert node_values == {
        "publication": {"direct", "curated", "community-governed"},
        "funding": {None, "fixed", "matching"},
        "research": {None, "resource-triggered", "autonomous"},
    }
    assert edge_values == {None, "instant", "delayed"}
    publication_slot = toy_structural_grammar().node_slots[0]
    assert {option.mechanism.family for option in publication_slot.options} == {
        MechanismFamily.PUBLICATION,
        MechanismFamily.GOVERNANCE,
    }


def test_every_candidate_is_valid_executable_and_has_bound_provenance():
    space = _space()
    fingerprints = set()
    for selection in space.selections:
        spec = space.build(selection)
        assert validate_system_spec(spec).valid
        result = DeterministicGraphRunner(spec, _registry()).run(periods=2)
        fingerprints.add(spec.fingerprint)
        assert result.system_fingerprint == spec.fingerprint
        assert all(
            event.provenance["system_fingerprint"] == spec.fingerprint
            for event in result.events
        )

    assert len(fingerprints) == space.candidate_count


def test_round_trip_fingerprint_and_canonical_rebuild_reject_tampering():
    space = _space()
    candidate = _candidate(
        space,
        publication="curated",
        funding="matching",
        research="resource-triggered",
        edge="delayed",
    )
    spec = space.decode(candidate)
    round_trip = SystemSpec.from_dict(json.loads(spec.canonical_json()))

    assert round_trip == spec
    assert round_trip.fingerprint == spec.fingerprint
    assert space.candidate_fingerprint(candidate) == spec.fingerprint

    tampered = json.loads(json.dumps(candidate))
    tampered["mechanisms"][0]["parameters"]["title"] = "unbound change"
    with pytest.raises(ValueError, match="canonical structural selection"):
        space.validate(tampered)


def test_illegal_edges_are_excluded_and_rejected():
    space = _space()
    illegal = StructuralSelection(
        {"publication": "direct", "funding": None, "research": None},
        {"resource-flow": "instant"},
    )

    with pytest.raises(ValueError, match="does not produce a valid graph"):
        space.build(illegal)

    autonomous_edge = StructuralSelection(
        {
            "publication": "direct",
            "funding": "fixed",
            "research": "autonomous",
        },
        {"resource-flow": "instant"},
    )
    with pytest.raises(ValueError, match="does not produce a valid graph"):
        space.build(autonomous_edge)


def test_one_step_neighbors_cover_all_structural_mutation_kinds():
    space = _space()
    kinds = set()
    for selection in space.selections:
        candidate = space.build(selection).to_dict()
        for mutation, neighbor in space.neighbors(candidate):
            kinds.add(mutation.kind)
            space.validate(neighbor)
            changed = space.selection(neighbor)
            node_diffs = sum(
                selection.nodes[key] != changed.nodes[key]
                for key in selection.nodes
            )
            edge_diffs = sum(
                selection.edges[key] != changed.edges[key]
                for key in selection.edges
            )
            assert node_diffs + edge_diffs == 1

    assert kinds == {
        "node-presence",
        "family",
        "implementation",
        "edge-presence",
        "latency",
    }


def test_sampling_and_mutation_are_deterministic_and_canonical():
    first = _space()
    second = _space()
    sampled_first = [
        first.sample(seed=71, proposal_index=index) for index in range(8)
    ]
    sampled_second = [
        second.sample(seed=71, proposal_index=index) for index in range(8)
    ]
    assert sampled_first == sampled_second

    incumbent = _candidate(
        first,
        funding="fixed",
        research="resource-triggered",
        edge=None,
    )
    changed, mutation = first.mutate_with_record(
        incumbent, seed=73, proposal_index=4, scale=0.2
    )
    repeated, repeated_mutation = second.mutate_with_record(
        incumbent, seed=73, proposal_index=4, scale=0.2
    )
    assert changed == repeated
    assert mutation == repeated_mutation
    assert first.candidate_fingerprint(changed) != first.candidate_fingerprint(
        incumbent
    )


def test_structural_space_closes_real_ask_execute_loss_tell_loop():
    space = _space()
    optimizer = AdaptiveRandomSearch(space, seed=79, initial_random=2)

    def evaluate(suggestion):
        loss, result = _toy_loss(space, suggestion.candidate)
        return Observation(
            observation_id="o-" + suggestion.suggestion_id,
            suggestion_id=suggestion.suggestion_id,
            candidate=suggestion.candidate,
            status="complete",
            loss=loss,
            metadata={
                "system_fingerprint": result.system_fingerprint,
                "event_stream_hash": result.event_stream_hash,
            },
        )

    initial, observations = evaluate_round(optimizer, evaluate, count=2)
    best = min(observations, key=lambda item: (item.loss, item.observation_id))
    adaptive = optimizer.ask(1)[0]

    assert adaptive.phase == "adaptive"
    assert adaptive.based_on_observation_id == best.observation_id
    assert adaptive.candidate != best.candidate
    adaptive_observation = evaluate(adaptive)
    optimizer.tell([adaptive_observation])
    assert adaptive_observation.metadata["system_fingerprint"] == (
        space.candidate_fingerprint(adaptive.candidate)
    )
    assert len(initial) == 2
    assert optimizer.state_dict()["pending"] == []

    state = json.loads(json.dumps(optimizer.state_dict()))
    restored = AdaptiveRandomSearch.from_state(_space(), state)
    assert restored.state_dict() == state


def test_grammar_rejects_duplicate_slots_before_candidate_generation():
    grammar = toy_structural_grammar()
    duplicated = replace(
        grammar,
        node_slots=(grammar.node_slots[0], grammar.node_slots[0]),
    )
    with pytest.raises(ValueError, match="node slot ids must be unique"):
        StructuralSystemSpace(duplicated)


def test_selection_encoding_is_strict():
    with pytest.raises(ValueError, match="exactly nodes and edges"):
        StructuralSelection.from_dict({"nodes": {}, "edges": {}, "extra": {}})

    grammar = StructuralGrammar(
        space_id="empty",
        system_id="empty",
        version=1,
        node_slots=(),
    )
    empty = StructuralSystemSpace(grammar)
    assert empty.candidate_count == 1
    empty.validate(empty.sample(seed=1, proposal_index=0))
