"""Warm reference is explicit state, not an own or synthetic world response."""
import pytest

from tests.optimization.test_native_parameter_space_v1 import space
from utopia.optimization.blackbox import Observation
from utopia.optimization.native_parameter_space_v1 import NativeParameterOptimizer


def reference(s):
    return Observation('developer-reference-original', 'reference-original', s.binding['anchor'],
        'complete', -10., {'SCRIPTED': 'scalar interface fixture, no science claim'})


def test_reference_is_literal_seen_anchor_and_a_real_lower_own_loss_guides_the_next_ask():
    s = space(); o = NativeParameterOptimizer(s, seed=51, initial_random=1); r = reference(s)
    o.warm_start(r)
    assert o.state_dict()['optimizer']['observations'] == [r.to_dict()]
    assert not o.state_dict()['optimizer']['pending'] and o.state_dict()['optimizer']['proposal_index'] == 0
    first = o.ask()[0]
    assert first.candidate != r.candidate and first.phase == 'initial'
    o.tell([Observation('own-lower', first.suggestion_id, first.candidate, 'complete', -20.)])
    restored = NativeParameterOptimizer.from_state(s, o.state_dict())
    second = o.ask()[0]
    assert second.phase == 'adaptive' and second.based_on_observation_id == 'own-lower'
    assert restored.ask()[0] == second
    with pytest.raises(ValueError, match='before the first'): o.warm_start(r)


def test_invalid_failed_or_nonaliteral_reference_is_not_repaired():
    s = space(); o = NativeParameterOptimizer(s, seed=51)
    with pytest.raises(ValueError, match='complete'):
        o.warm_start(Observation('failed', 'ref', s.binding['anchor'], 'failed'))
    other = s.candidate({'coordinate-0': 10})
    with pytest.raises(ValueError, match='literal numeric-space anchor'):
        o.warm_start(Observation('other', 'ref', other, 'complete', -10.))
    assert o.state_dict()['optimizer']['observations'] == []
