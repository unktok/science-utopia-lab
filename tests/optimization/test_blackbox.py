import json
from pathlib import Path

import pytest

from utopia.optimization.blackbox import (
    AdaptiveRandomSearch,
    LegacyParameterSpace,
    LegacySystemSpecSpace,
    Observation,
    evaluate_round,
)
from utopia.optimization.design_space import load_space


ROOT = Path(__file__).resolve().parents[2]
SPACE = load_space(ROOT / "research/specs/design-space-v2.json")


def _observation(suggestion, loss, *, status="complete"):
    return Observation(
        observation_id="o-" + suggestion.suggestion_id,
        suggestion_id=suggestion.suggestion_id,
        candidate=suggestion.candidate,
        status=status,
        loss=loss,
    )


def test_initial_ask_is_deterministic_and_valid():
    adapter = LegacyParameterSpace(SPACE)
    first = AdaptiveRandomSearch(adapter, seed=17).ask(4)
    second = AdaptiveRandomSearch(adapter, seed=17).ask(4)

    assert [item.to_dict() for item in first] == [item.to_dict() for item in second]
    assert len({json.dumps(item.candidate, sort_keys=True) for item in first}) == 4
    assert {item.phase for item in first} == {"initial"}
    for item in first:
        adapter.validate(item.candidate)


def test_tell_makes_next_proposal_depend_on_best_observation():
    adapter = LegacyParameterSpace(SPACE)
    optimizer = AdaptiveRandomSearch(adapter, seed=29, initial_random=2)
    initial = optimizer.ask(2)
    optimizer.tell([
        _observation(initial[0], 8.0),
        _observation(initial[1], 1.0),
    ])

    adaptive = optimizer.ask(1)[0]

    assert adaptive.phase == "adaptive"
    assert adaptive.based_on_observation_id == "o-" + initial[1].suggestion_id
    assert adaptive.candidate != initial[1].candidate


def test_invalid_observation_is_not_converted_into_a_penalty_or_incumbent():
    adapter = LegacyParameterSpace(SPACE)
    optimizer = AdaptiveRandomSearch(adapter, seed=31, initial_random=1)
    suggestion = optimizer.ask(1)[0]
    optimizer.tell([_observation(suggestion, None, status="invalid")])

    following = optimizer.ask(1)[0]

    assert following.phase == "initial"
    assert following.based_on_observation_id is None


def test_state_round_trip_preserves_pending_and_next_adaptive_suggestion():
    adapter = LegacyParameterSpace(SPACE)
    original = AdaptiveRandomSearch(adapter, seed=37, initial_random=2)
    initial = original.ask(2)
    original.tell([_observation(initial[0], 3.0), _observation(initial[1], 2.0)])
    pending = original.ask(1)[0]
    state = json.loads(json.dumps(original.state_dict()))

    restored = AdaptiveRandomSearch.from_state(adapter, state)

    assert restored.state_dict() == state
    restored.tell([_observation(pending, 1.5)])
    original.tell([_observation(pending, 1.5)])
    assert restored.ask(1)[0].to_dict() == original.ask(1)[0].to_dict()


def test_tell_rejects_unknown_or_changed_suggestion():
    adapter = LegacyParameterSpace(SPACE)
    optimizer = AdaptiveRandomSearch(adapter, seed=41)
    suggestion = optimizer.ask(1)[0]
    changed = dict(suggestion.candidate)
    changed["funding_budget_slots_frac"] = 0.5

    with pytest.raises(ValueError, match="does not match"):
        optimizer.tell([
            Observation(
                observation_id="changed",
                suggestion_id=suggestion.suggestion_id,
                candidate=changed,
                status="complete",
                loss=1.0,
            )
        ])


def test_tell_rejects_two_observations_for_one_pending_suggestion():
    adapter = LegacyParameterSpace(SPACE)
    optimizer = AdaptiveRandomSearch(adapter, seed=42)
    suggestion = optimizer.ask(1)[0]

    with pytest.raises(ValueError, match="duplicate suggestion id"):
        optimizer.tell([
            _observation(suggestion, 1.0),
            Observation(
                observation_id="another-observation",
                suggestion_id=suggestion.suggestion_id,
                candidate=suggestion.candidate,
                status="complete",
                loss=2.0,
            ),
        ])


def test_synchronous_round_closes_ask_evaluate_tell_loop():
    adapter = LegacyParameterSpace(SPACE)
    optimizer = AdaptiveRandomSearch(adapter, seed=43, initial_random=2)

    suggestions, observations = evaluate_round(
        optimizer,
        lambda item: _observation(
            item,
            1.0 - float(item.candidate["funding_budget_slots_frac"]),
        ),
        count=2,
    )

    assert len(suggestions) == len(observations) == 2
    assert optimizer.state_dict()["pending"] == []
    assert len(optimizer.state_dict()["observations"]) == 2


def test_optimizer_accepts_nested_whole_system_candidates_through_adapter():
    class NestedSystemSpace:
        def validate(self, candidate):
            if not isinstance(candidate.get("mechanisms"), list):
                raise ValueError("mechanisms required")

        def sample(self, *, seed, proposal_index):
            return {
                "mechanisms": [
                    {"family": "funding", "parameters": {"budget": proposal_index + 1}}
                ],
                "connections": [],
            }

        def mutate(self, incumbent, *, seed, proposal_index, scale):
            budget = incumbent["mechanisms"][0]["parameters"]["budget"]
            return {
                "mechanisms": [
                    {"family": "funding", "parameters": {"budget": budget + 1}}
                ],
                "connections": [],
            }

    optimizer = AdaptiveRandomSearch(NestedSystemSpace(), seed=47, initial_random=1)
    first = optimizer.ask(1)[0]
    optimizer.tell([_observation(first, 2.0)])

    second = optimizer.ask(1)[0]

    assert second.phase == "adaptive"
    assert second.candidate["mechanisms"][0]["parameters"]["budget"] == 2
    assert second.based_on_observation_id == "o-" + first.suggestion_id


def test_legacy_system_spec_adapter_proposes_nested_executable_designs():
    adapter = LegacySystemSpecSpace(SPACE)
    optimizer = AdaptiveRandomSearch(adapter, seed=49, initial_random=1)
    first = optimizer.ask(1)[0]
    adapter.validate(first.candidate)
    optimizer.tell([_observation(first, 2.0)])

    second = optimizer.ask(1)[0]
    adapter.validate(second.candidate)

    assert first.candidate["system_id"] == "legacy-fixed-topology"
    assert len(first.candidate["mechanisms"]) > 1
    assert second.phase == "adaptive"
    assert second.candidate != first.candidate


@pytest.mark.parametrize(
    "status,loss",
    [("complete", None), ("complete", float("nan")), ("failed", 1.0)],
)
def test_observation_enforces_loss_and_technical_status_separation(status, loss):
    with pytest.raises(ValueError):
        Observation(
            observation_id="bad",
            suggestion_id="suggestion",
            candidate={"system": "opaque"},
            status=status,
            loss=loss,
        )
