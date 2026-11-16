"""Actual source/ask-tell contracts; SCRIPTED losses are not native results."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from utopia.optimization.blackbox import Observation
from utopia.optimization.native_institution_workflow_domain_v6 import require_institution_workflow_candidate
from utopia.optimization.native_parameter_space_v1 import NativeParameterOptimizer
from utopia.optimization.native_topic_priority_space_v1 import SCOPE, topic_priority_space
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.native_topic_priority_controls import SOURCE
from tests.system.test_native_topic_priority_controls import actors, output, producer

ROOT = Path(__file__).resolve().parents[2]


def reference():
    return SystemSpec.from_dict(json.loads((ROOT /
        'research/data/native-terminal-cost-pilot-v1/systems/strong-related-reference.json').read_text()))


def test_zero_anchor_and_samples_execute_the_actual_existing_priority_consumer():
    ref = reference(); before = ref.to_dict(); space = topic_priority_space(ref)
    bound = space.binding
    assert bound['design_space']['world_law_scope'] == SCOPE
    assert all(v == 0. for v in producer(SystemSpec.from_dict(bound['anchor'])).parameters['topic_priorities'].values())
    assert output(SOURCE, producer(SystemSpec.from_dict(bound['anchor'])).parameters, actors()) == output(
        producer(ref).parameters['code_artifact']['source'], producer(ref).parameters, actors())
    choices = set()
    for index in range(12):
        candidate = space.sample(seed=11, proposal_index=index)
        spec = SystemSpec.from_dict(candidate)
        require_institution_workflow_candidate(ref, spec)
        assert spec.connections == ref.connections and spec.schedules == ref.schedules
        node = producer(spec)
        assert node.parameters['code_artifact']['source'] == SOURCE
        result = output(SOURCE, node.parameters, actors())
        choices.add(tuple(a['direction']['topic'] for a in result['outputs']['agenda'][0]['payload']['assignments']))
    assert len(choices) > 1  # Component actuation diversity, not new native-world scores.
    assert ref.to_dict() == before and space.binding == bound


def test_real_ask_tell_state_carries_objective_feedback_and_replays_without_world_calls():
    space = topic_priority_space(reference())
    a = NativeParameterOptimizer(space, seed=17, initial_random=1)
    b = NativeParameterOptimizer(space, seed=17, initial_random=1)
    first_a, first_b = a.ask()[0], b.ask()[0]
    assert first_a.to_dict() == first_b.to_dict()
    # Opposite declared SCRIPTED preferences; neither is a scientific metric.
    a.tell([Observation('SCRIPTED-a0', first_a.suggestion_id, first_a.candidate, 'complete', -1.)])
    b.tell([Observation('SCRIPTED-b0', first_b.suggestion_id, first_b.candidate, 'complete', 1.)])
    second_a, second_b = a.ask()[0], b.ask()[0]
    assert second_a.candidate == second_b.candidate  # Same sole parent so far.
    a.tell([Observation('SCRIPTED-a1', second_a.suggestion_id, second_a.candidate, 'complete', -2.)])
    b.tell([Observation('SCRIPTED-b1', second_b.suggestion_id, second_b.candidate, 'complete', 2.)])
    saved = deepcopy(a.state_dict()); before = deepcopy(saved)
    restored = NativeParameterOptimizer.from_state(space, saved)
    third_a, third_restored, third_b = a.ask()[0], restored.ask()[0], b.ask()[0]
    assert third_a.to_dict() == third_restored.to_dict() and a.state_dict() != b.state_dict()
    assert third_a.based_on_observation_id == 'SCRIPTED-a1'
    assert third_b.based_on_observation_id == 'SCRIPTED-b0'
    assert third_a.candidate != third_b.candidate and saved == before


@pytest.mark.parametrize('edit', ['source', 'wire', 'unknown-weight', 'duration'])
def test_restricted_family_cannot_silently_become_free_program_search(edit):
    space = topic_priority_space(reference()); candidate = deepcopy(space.binding['anchor'])
    node = next(n for n in candidate['mechanisms'] if n['mechanism_id'] == 'developer-catalog-agenda')
    if edit == 'source': node['parameters']['code_artifact']['source'] += '\n# altered\n'
    elif edit == 'wire': candidate['connections'].pop()
    elif edit == 'unknown-weight': node['parameters']['topic_priorities']['not_a_topic'] = 1.
    else: node['parameters']['catalog']['directions'][0]['years'] = 999
    with pytest.raises(ValueError): space.validate(candidate)


def test_literal_new_anchor_does_not_inherit_a_different_measured_reference():
    ref = reference(); space = topic_priority_space(ref)
    assert digest(ref.to_dict()) != digest(space.binding['anchor'])
    opt = NativeParameterOptimizer(space, seed=17)
    with pytest.raises(ValueError):
        opt.warm_start(Observation('SCRIPTED-not-the-anchor', 'SCRIPTED-ref', ref.to_dict(), 'complete', 0.))
    assert opt.state_dict()['optimizer']['observations'] == []


def test_uniform_control_is_the_same_existing_sampler_with_no_adaptive_steps_inside_budget():
    space = topic_priority_space(reference()); budget = 4
    opt = NativeParameterOptimizer(space, seed=19, initial_random=budget)
    for index in range(budget):
        s, = opt.ask()
        assert s.phase == 'initial' and s.based_on_observation_id is None
        opt.tell([Observation('SCRIPTED-uniform-' + str(index), s.suggestion_id,
                              s.candidate, 'failed', None)])
    observations = opt.state_dict()['optimizer']['observations']
    assert len(observations) == budget and all(r['loss'] is None for r in observations)
