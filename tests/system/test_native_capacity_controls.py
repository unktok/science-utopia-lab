"""Literal reference policies in real isolated Python, not scientist outcomes."""
from copy import deepcopy

import pytest

from utopia.system.code_mechanisms import DockerCodeExecutor
from utopia.system.native_capacity_controls import capacity_allocation_control
from utopia.system.native_kernel import legacy_world_system
from utopia.system.native_liquidity_controls import liquidity_control

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


def test_existing_authority_wires_and_native_stages_are_not_extended():
    base = legacy_world_system(); original = liquidity_control(base, IMAGE)
    for rule in ('reserve-proximity', 'completion-priority'):
        spec = capacity_allocation_control(base, IMAGE, rule=rule)
        assert spec.connections == original.connections and spec.schedules == original.schedules
        assert spec.artifact_types == original.artifact_types and spec.initial_state == base.initial_state
        assert all(n in spec.mechanisms for n in base.mechanisms)
        changed = [(a,b) for a,b in zip(spec.mechanisms, original.mechanisms) if a != b]
        assert len(changed) == 1 and changed[0][0].mechanism_id == 'developer-liquidity-director'


@pytest.mark.parametrize('rule,reserve', [('other',21), ('reserve-proximity',True),
    ('reserve-proximity',0), ('reserve-proximity',21.0)])
def test_bad_explicit_controls_are_rejected(rule, reserve):
    with pytest.raises(ValueError):
        capacity_allocation_control(legacy_world_system(), IMAGE, rule=rule, reserve_units=reserve)


def context():
    actors = [{'id':identity, 'resources':balance, 'can_author':True, 'is_active':True,
               'project_end_year':end} for identity,balance,end in [('near',20,4),('soon',18,2),('donor',24,5)]]
    return {'period':1, 'random_seed':42, 'state':{}, 'parameters':{},
        'inputs':{'world':[{'payload':{'ecosystem':{'agents':actors}}}]}}


def test_actual_container_rules_have_explicit_different_information_use_and_conserve():
    executor = DockerCodeExecutor(IMAGE); results = {}
    for rule in ('reserve-proximity', 'completion-priority'):
        spec = capacity_allocation_control(legacy_world_system(), IMAGE, rule=rule)
        node = next(n for n in spec.mechanisms if n.mechanism_id == 'developer-liquidity-director')
        frame = context(); frame['parameters'] = deepcopy(node.parameters)
        before = deepcopy(frame)
        execution = executor.execute(node.parameters['code_artifact'], frame)
        commands = execution.result['outputs']['funds']
        assert frame == before and len(commands) == 1
        balances = {a['id']:a['resources'] for a in frame['inputs']['world'][0]['payload']['ecosystem']['agents']}
        for command in commands:
            p = command['payload']; balances[p['from_actor']] -= p['amount']; balances[p['to_actor']] += p['amount']
        assert sum(balances.values()) == 62 and min(balances.values()) >= 0
        assert balances['donor'] >= 21
        results[rule] = commands[0]['payload']
    assert results['reserve-proximity']['to_actor'] == 'near'
    assert results['reserve-proximity']['amount'] == 1
    assert results['completion-priority']['to_actor'] == 'soon'
    assert results['completion-priority']['amount'] == 3
