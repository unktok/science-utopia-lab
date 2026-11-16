"""SCRIPTED scalar feedback and real trusted priority consumer, not world gains."""
from copy import deepcopy

import pytest

from scripts.reports.native_priority_kernel_geometry_v1 import inspect_first_update, priority_order
from tests.optimization.test_native_topic_priority_space_v1 import reference
from tests.system.test_native_topic_priority_controls import actors, output, producer
from utopia.optimization.blackbox import Observation
from utopia.optimization.native_parameter_space_v1 import NativeParameterOptimizer
from utopia.optimization.native_topic_priority_space_v1 import topic_priority_space
from utopia.system import SystemSpec
from utopia.system.native_topic_priority_controls import SOURCE


def prepared(*, initial_random=1, own_loss=1., reference_loss=0., own_id='observation-own'):
    space = topic_priority_space(reference())
    opt = NativeParameterOptimizer(space, seed=19, initial_random=initial_random)
    opt.warm_start(Observation('developer-reference', 'SCRIPTED-ref', space.binding['anchor'],
                               'complete', reference_loss))
    first, = opt.ask()
    opt.tell([Observation(own_id, first.suggestion_id, first.candidate, 'complete', own_loss)])
    return space, opt


@pytest.mark.parametrize('own_loss', [1., 0.])
def test_worse_or_tied_first_own_keeps_zero_reference_and_exact_next_ask(own_loss):
    space, opt = prepared(own_loss=own_loss)
    state = deepcopy(opt.state_dict()); preserved = deepcopy(state)
    expected, = opt.ask()
    report = inspect_first_update(state, actual_started={
        'suggestion': expected.to_dict(), 'optimizer_after_ask': opt.state_dict()})
    assert state == preserved
    assert report['actual_ask_receipt_supplied_and_matched']
    assert report['parent_observation_id'] == 'developer-reference'
    assert report['all_parent_priorities_zero'] and report['common_zero_centered_unclipped_intervals']
    assert report['effective_mutation_scale'] == .2 and report['coordinate_radius'] == .4
    assert report['scale_observed_at_original_local_sampler_call']
    assert report['coordinate_count'] == 53
    assert set(tuple(v) for v in report['mutation_intervals'].values()) == {(-.4, .4)}
    assert report['expected_suggestion_id'] == expected.suggestion_id


def test_better_own_uses_nonzero_parent_and_does_not_claim_centered_kernel():
    _, opt = prepared(own_loss=-1.)
    report = inspect_first_update(opt.state_dict())
    assert report['parent_observation_id'] == 'observation-own'
    assert not report['all_parent_priorities_zero']
    assert not report['common_zero_centered_unclipped_intervals']
    assert not report['actual_ask_receipt_supplied_and_matched']


def test_observation_id_tie_rule_can_select_an_own_nonzero_parent():
    _, opt = prepared(own_loss=0., own_id='a-own')
    report = inspect_first_update(opt.state_dict())
    assert report['parent_observation_id'] == 'a-own'
    assert not report['all_parent_priorities_zero']


def test_uniform_second_sample_is_not_reinterpreted_as_parent_based_update():
    _, opt = prepared(initial_random=2)
    report = inspect_first_update(opt.state_dict())
    assert report['phase'] == 'initial' and report['parent_observation_id'] is None
    assert report['mutation_intervals'] is None and report['coordinate_radius'] is None
    assert not report['scale_observed_at_original_local_sampler_call']


@pytest.mark.parametrize('change', ['suggestion', 'post-ask', 'missing'])
def test_changed_or_missing_actual_ask_is_rejected_not_repaired(change):
    _, opt = prepared(); state = opt.state_dict(); s, = opt.ask()
    actual = {'suggestion': s.to_dict(), 'optimizer_after_ask': opt.state_dict()}
    if change == 'suggestion': actual['suggestion']['based_on_observation_id'] = 'fabricated'
    elif change == 'post-ask': actual['optimizer_after_ask']['optimizer']['proposal_index'] += 1
    else: actual.pop('suggestion')
    with pytest.raises(ValueError, match='actual recorded'):
        inspect_first_update(state, actual_started=actual)


def test_pending_state_is_not_treated_as_a_completed_first_observation():
    _, opt = prepared(); opt.ask()
    with pytest.raises(ValueError, match='first completed'):
        inspect_first_update(opt.state_dict())


@pytest.mark.parametrize('values', [{}, [], {'a': True}, {'a': float('nan')}, {1: .2}])
def test_malformed_priorities_are_not_silently_converted(values):
    with pytest.raises(ValueError, match='finite literal'):
        priority_order(values)


def test_exact_ties_use_lexical_order_and_negative_scaling_is_not_an_invariance():
    assert priority_order({'c': 0., 'a': 0., 'b': 1.}) == ['b', 'a', 'c']
    assert priority_order({'a': -1., 'b': 1.}) != priority_order({'a': 1., 'b': -1.})


@pytest.mark.parametrize('scale', [2. ** -12, .25, 1.])
def test_zero_centered_coupled_draw_keeps_order_and_actual_trusted_consumer_output(scale):
    space = topic_priority_space(reference()); sampled = space.sample(seed=17, proposal_index=1)
    params = producer(SystemSpec.from_dict(sampled)).parameters
    original = deepcopy(params); transformed = deepcopy(params)
    transformed['topic_priorities'] = {t: scale * v for t, v in params['topic_priorities'].items()}
    # Dyadic scaling here preserves these literal finite-float comparisons.
    # This is a coupled known draw, not matching sample/mutate RNG streams.
    assert priority_order(original['topic_priorities']) == priority_order(transformed['topic_priorities'])
    assert output(SOURCE, original, actors()) == output(SOURCE, transformed, actors())
    assert original == params


@pytest.mark.parametrize('artificial,neural,expected', [
    (0., 0., 'artificial_intelligence'),
    (-1e-6, 1e-6, 'neural_symbolic_ai'),
    (-.9, .9, 'neural_symbolic_ai'),
    (1e-6, -1e-6, 'artificial_intelligence')])
def test_small_coordinate_distance_is_not_policy_locality_on_actual_initial_actor(
        artificial, neural, expected):
    space = topic_priority_space(reference())
    params = deepcopy(producer(SystemSpec.from_dict(space.binding['anchor'])).parameters)
    params['topic_priorities'].update(artificial_intelligence=artificial, neural_symbolic_ai=neural)
    # Exact trusted native comparator and retained five-founder input, not an
    # invented response world or a scientific counterfactual outcome.
    result = output(SOURCE, params, actors())
    assignment = next(a for a in result['outputs']['agenda'][0]['payload']['assignments']
                      if a['actor_id'] == 'institution_0001_researcher_0')
    assert assignment['direction']['topic'] == expected
    assert assignment['direction']['years'] == 1
