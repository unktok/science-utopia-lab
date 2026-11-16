"""Declared initial-consumer moves; SCRIPTED losses, not new native worlds."""
from copy import deepcopy

import pytest

from tests.optimization.test_native_topic_priority_space_v1 import reference
from tests.system.test_native_topic_priority_controls import actors, output, producer
from utopia.optimization.blackbox import Observation
from utopia.optimization.native_initial_choice_space_v1 import NativeInitialChoiceSpace
from utopia.optimization.native_parameter_space_v1 import NativeParameterOptimizer
from utopia.optimization.native_topic_priority_space_v1 import topic_priority_space
from utopia.system import SystemSpec
from utopia.system.native_topic_priority_controls import SOURCE


def choices(candidate):
    assigned = output(SOURCE, producer(SystemSpec.from_dict(candidate)).parameters, actors())[
        'outputs']['agenda'][0]['payload']['assignments']
    return [(a['direction']['topic'], a['direction']['years']) for a in assigned]


def test_literal_anchor_initial_samples_and_declared_groups():
    control = reference(); society = actors(); before = deepcopy(society)
    space = NativeInitialChoiceSpace(control, society); numeric = topic_priority_space(control)
    assert society == before and space.binding['anchor'] == numeric.binding['anchor']
    assert space.binding['design_space'] == numeric.binding['design_space']
    groups = space.binding['initial_choice_kernel']['groups']
    assert [len(g['topics']) for g in groups] == [2, 6, 2]
    assert [g['original_duration'] for g in groups] == [1, 2, 1]
    assert space.choice_steps(.2) == 1 and space.choice_steps(1.) == 3
    assert space.sample(seed=31, proposal_index=0) == numeric.sample(seed=31, proposal_index=0)


@pytest.mark.parametrize('group,alternative', [(0, 'neural_symbolic_ai'),
    *[(1, t) for t in ['mathematical_software', 'operating_systems', 'parallel_computing',
                      'performance_analysis', 'software_engineering']], (2, 'meta-learning')])
def test_each_declared_single_move_crosses_literal_initial_consumer_boundary(monkeypatch, group, alternative):
    space = NativeInitialChoiceSpace(reference(), actors()); anchor = space.binding['anchor']
    class RNG:
        def randrange(self, n): assert n == 3; return group
        def choice(self, values): assert alternative in values; return alternative
    monkeypatch.setattr(space, '_rng', lambda *a: RNG())
    candidate = space.mutate(anchor, seed=17, proposal_index=0, scale=.2)
    old, new = choices(anchor), choices(candidate)
    assert sum(a != b for a,b in zip(old,new)) == 1
    assert [years for _,years in old] == [years for _,years in new]
    assert new[group + 1][0] == alternative
    fixed = deepcopy(candidate)
    next(n for n in fixed['mechanisms'] if n['mechanism_id'] == 'developer-catalog-agenda')[
        'parameters']['topic_priorities'] = producer(SystemSpec.from_dict(anchor)).parameters['topic_priorities']
    assert fixed == anchor  # No new source/graph/schedule/world effect contract.


def test_real_ask_tell_state_replays_without_fabricated_warm_measurement():
    space = NativeInitialChoiceSpace(reference(), actors()); anchor = space.binding['anchor']
    optimizer = NativeParameterOptimizer(space, seed=13, initial_random=1, mutation_scale=.2)
    optimizer.warm_start(Observation('SCRIPTED-reference', 'SCRIPTED-parent', anchor, 'complete', 0.))
    initial, = optimizer.ask()
    optimizer.tell([Observation('SCRIPTED-initial', initial.suggestion_id, initial.candidate, 'complete', 1.)])
    suggestion, = optimizer.ask(); assert choices(suggestion.candidate) != choices(anchor)
    optimizer.tell([Observation('SCRIPTED-first', suggestion.suggestion_id, suggestion.candidate, 'complete', 2.)])
    restored = NativeParameterOptimizer.from_state(space, deepcopy(optimizer.state_dict()))
    assert optimizer.ask()[0].to_dict() == restored.ask()[0].to_dict()
    different = actors(); different[1]['is_active'] = False
    with pytest.raises(ValueError): NativeParameterOptimizer.from_state(NativeInitialChoiceSpace(reference(), different), restored.state_dict())


@pytest.mark.parametrize('value', [True, 0., -1., 1.1, float('nan'), float('inf'), '0.2'])
def test_invalid_scale_is_not_repaired(value):
    space = NativeInitialChoiceSpace(reference(), actors())
    with pytest.raises(ValueError): space.choice_steps(value)


def test_no_initial_choices_is_configuration_error_not_failed_candidate_refill():
    society = actors()
    for actor in society: actor['is_active'] = False
    with pytest.raises(ValueError, match='no nontrivial'): NativeInitialChoiceSpace(reference(), society)
