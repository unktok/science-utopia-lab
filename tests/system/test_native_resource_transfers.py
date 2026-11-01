"""Actual native resource effects; model replies/corpus are scripted QA only."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from tests.runtime.test_portable_checkpoint_integration import (
    FakeHTTPModel, SmallRealSimulation, fixed_corpus, seed, science_snapshot,
)
from tests.system.test_native_science_kernel import make_sim, original_science
from utopia.agents.base_agent import SimulationAgent
from utopia.funding.accounting import ResourceLedger
from utopia.runtime.checkpointing import PortableStop
from utopia.system import (ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily,
                           MechanismSpec, PortSpec, ScheduleSpec)
from utopia.system.code_mechanisms import CODE_SCHEMA, DockerCodeExecutor, sha
from utopia.system.native_kernel import NativeScienceKernel, WORLD_ARTIFACT, legacy_world_system
from utopia.system.native_resource_transfers import (
    EVENT, IMPLEMENTATION, add_resource_transfer_receiver, apply_native_resource_transfers,
)
from utopia.system.runtime import DeliveredValue, GraphRuntimeError


class Actor:
    can_author = True
    update_resources = SimulationAgent.update_resources
    def __init__(self, identity, resources):
        self.id, self.resources, self.is_active = identity, resources, True
    def get_type(self):
        return 'university'


def unit_world(*, ledger=True):
    actors = {'a': Actor('a', 10.), 'b': Actor('b', 5.)}
    accounting = ResourceLedger() if ledger else None
    if accounting:
        accounting.start_year(1, actors)
    simulation = SimpleNamespace(ecosystem=SimpleNamespace(agent_population=actors), resource_ledger=accounting)
    return SimpleNamespace(_simulation=simulation, _frame={}, events=[]), actors, accounting


def value(identity='one', *, amount=3., source='a', target='b'):
    return DeliveredValue(ChannelKind.RESOURCE, 'custom-fund-command',
        {'transaction_id': identity, 'from_actor': source, 'to_actor': target, 'amount': amount},
        (source, target), (), ('actual-generated-source-event',), 'arbitrary-institution', 'funds', 1, 1)


def context(*values, state=None, period=1):
    return SimpleNamespace(inputs={'transfers': values}, period=period, state=state or {})


def test_native_transfer_atomic_accounting_replay_and_source_lineage():
    kernel, actors, ledger = unit_world()
    result = apply_native_resource_transfers(kernel, context(value()))
    assert [actors[k].resources for k in ['a', 'b']] == [7., 8.]
    assert ledger.native_transfer_accounting
    assert len(ledger.transactions) == 2
    assert math_totals(ledger, actors) == 15.
    event = result.events[0]
    assert event.event_type == EVENT and event.payload['input_event_ids'] == ['actual-generated-source-event']
    assert event.payload['command_sha256'] == sha(dict(value().payload))
    before = deepcopy(ledger.to_dict())
    assert not apply_native_resource_transfers(kernel, context(value())).events
    assert ledger.to_dict() == before
    with pytest.raises(GraphRuntimeError, match='replay changes'):
        apply_native_resource_transfers(kernel, context(value(amount=4.)))
    assert ledger.to_dict() == before


def math_totals(ledger, actors):
    rows = ledger.reconcile(1, actors)
    assert all(row['residual'] == 0 for row in rows)
    return sum(row['closing_balance'] for row in rows)


@pytest.mark.parametrize('bad', [value(amount=-1.), value(amount=True), value(amount=float('nan')),
    value(amount=100.), value(target='missing')])
def test_entire_batch_preflight_rejects_without_any_effect(bad):
    kernel, actors, ledger = unit_world()
    before = deepcopy(ledger.to_dict())
    with pytest.raises(GraphRuntimeError):
        apply_native_resource_transfers(kernel, context(value(), bad))
    assert [actors[k].resources for k in ['a', 'b']] == [10., 5.]
    assert ledger.to_dict() == before and not kernel._frame


def test_unexpected_second_leg_failure_rolls_back_balances_flags_and_ledger():
    kernel, actors, ledger = unit_world()
    def failure(*args, **kwargs):
        raise RuntimeError('injected credit failure')
    actors['b'].update_resources = failure
    before = deepcopy(ledger.to_dict())
    with pytest.raises(RuntimeError, match='injected credit'):
        apply_native_resource_transfers(kernel, context(value()))
    assert [actors[k].resources for k in ['a', 'b']] == [10., 5.]
    assert ledger.to_dict() == before and not kernel._frame


def test_invalid_receipt_state_and_past_replay_do_not_mutate_resources():
    kernel, actors, ledger = unit_world()
    before = ledger.to_dict()
    with pytest.raises(GraphRuntimeError, match='persistent receipt state'):
        apply_native_resource_transfers(kernel, context(value(), state={'unexpected': 'state'}))
    assert ledger.to_dict() == before and actors['a'].resources == 10.
    result = apply_native_resource_transfers(kernel, context(value()))
    kernel.events = [SimpleNamespace(event_type=EVENT, payload=result.events[0].payload)]
    kernel._frame = {}
    before = ledger.to_dict()
    assert not apply_native_resource_transfers(kernel, context(value(), period=2)).events
    assert ledger.to_dict() == before and actors['a'].resources == 7.


def test_ledger_absent_behavior_and_opt_in_serialization():
    plain = ResourceLedger()
    assert set(plain.to_dict()) == {'schema_version', 'transactions', 'years', 'entry_years'}
    assert plain.categories == __import__('utopia.funding.accounting', fromlist=['CATEGORIES']).CATEGORIES
    kernel, actors, _ = unit_world(ledger=False)
    apply_native_resource_transfers(kernel, context(value()))
    assert [actors[k].resources for k in ['a', 'b']] == [7., 8.]


@pytest.mark.parametrize('opening,amount', [(1e20, 1.), (10., 0.1)])
def test_unrepresentable_float_debit_or_credit_is_atomically_rejected(opening, amount):
    kernel, actors, ledger = unit_world()
    actors['a'].resources = opening
    before = ledger.to_dict()
    with pytest.raises(GraphRuntimeError, match='exactly representable'):
        apply_native_resource_transfers(kernel, context(value(amount=amount)))
    assert actors['a'].resources == opening and actors['b'].resources == 5.
    assert ledger.to_dict() == before and not kernel._frame


def test_exactly_representable_fractional_transfer_is_not_an_integer_only_rule():
    kernel, actors, ledger = unit_world()
    apply_native_resource_transfers(kernel, context(value(amount=0.25)))
    assert actors['a'].resources == 9.75 and actors['b'].resources == 5.25
    assert math_totals(ledger, actors) == 15.


@pytest.mark.parametrize('bad', [value('self', source='a', target='a', amount=10.),
    value('zero', source='b', target='a', amount=0.)])
def test_self_and_zero_commands_reject_entire_batch_before_native_active_flag_or_ledger_changes(bad):
    kernel, actors, ledger = unit_world()
    # This Actor binds the ACTUAL SimulationAgent.update_resources method.
    actors['b'].resources = 0.
    ledger.years['1']['b']['opening_balance'] = 0.
    before = deepcopy(ledger.to_dict())
    with pytest.raises(GraphRuntimeError, match='strictly positive|distinct actors'):
        apply_native_resource_transfers(kernel, context(value(), bad))
    assert [(actors[k].resources, actors[k].is_active) for k in ['a', 'b']] == [(10., True), (0., True)]
    assert ledger.to_dict() == before and not ledger.native_transfer_accounting
    assert not kernel._frame


SOURCE = """def step(context):
    world = context['inputs']['world'][0]['payload']
    authors = sorted(a['id'] for a in world['ecosystem']['agents'] if a['can_author'])
    messages = [{'payload': {'transaction_id': 'native-genuine-transfer',
        'from_actor': authors[0], 'to_actor': authors[1], 'amount': 7.0}}]
    return {'outputs': {'funds': messages}, 'state': {'cycles': context['period']}}
"""


def transfer_spec(image_id, *, latency=0, connected=True):
    base = legacy_world_system()
    node = MechanismSpec('arbitrary-resource-director', MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('world', ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
        outputs=(PortSpec('funds', ChannelKind.RESOURCE, 'custom-resource-command'),),
        parameters={'runtime_image_id': image_id, 'code_artifact': {'schema': CODE_SCHEMA,
            'label': 'Scripted free allocation code, not invention', 'source': SOURCE,
            'inputs': {'world': {'type': 'object'}}, 'outputs': {'funds': {'type': 'object'}},
            'state_schema': {'type': 'object'}}})
    base = replace(base, mechanisms=(*base.mechanisms, node),
        artifact_types=(*base.artifact_types, ArtifactTypeSpec('custom-resource-command')),
        schedules=(*base.schedules, ScheduleSpec(node.mechanism_id, 10)),
        connections=(*base.connections, ConnectionSpec('world.open', 'world', node.mechanism_id, 'world', ChannelKind.ARTIFACT)))
    if connected:
        return add_resource_transfer_receiver(base, source=node.mechanism_id, source_port='funds', phase=15, latency=latency)
    return base


def real_sim(path, spec, executor, *, ledger=True, after_effects=False):
    calls = []
    simulation = SmallRealSimulation(path, FakeHTTPModel(path, calls), ledger=ledger, after_effects=after_effects)
    simulation.native_system = NativeScienceKernel(spec, code_executor=executor)
    return simulation, calls


def test_bridge_absent_retains_exact_original_six_year_world(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.0)
    reference, calls0 = make_sim(tmp_path / 'original')
    reference.run()
    expected = original_science(reference)
    seed()
    native, calls1 = make_sim(tmp_path / 'native', native=NativeScienceKernel(legacy_world_system()))
    native.run()
    assert original_science(native) == expected
    assert [request for _, request in calls0] == [request for _, request in calls1]
    reference.llm.response_cache.close()
    native.llm.response_cache.close()


def test_actual_code_effect_reaches_native_resources_prompts_and_ledger(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.0)
    executor = DockerCodeExecutor()
    disconnected, before_calls = real_sim(tmp_path / 'off', transfer_spec(executor.image_id, connected=False), executor)
    disconnected.run()
    seed()
    linked, after_calls = real_sim(tmp_path / 'on', transfer_spec(executor.image_id), executor)
    linked.run()
    events = [e for e in linked.native_system.events if e.event_type == EVENT]
    assert len(events) == 6
    assert [e.payload['received_period'] for e in events] == list(range(1, 7))
    by_id = {e.event_id: e for e in linked.native_system.events}
    for event in events:
        assert event.provenance['input_event_ids'] == event.payload['input_event_ids']
        assert all(by_id[identity].event_type == 'generated.code_executed' for identity in event.payload['input_event_ids'])
        assert event.payload['balances_after'] != event.payload['balances_before']
    old_prompts = {repr(key): payload for key, payload in before_calls}
    new_prompts = {repr(key): payload for key, payload in after_calls}
    assert any('Funding level:' in json.dumps(new_prompts[key])
        and old_prompts[key] != new_prompts[key] for key in old_prompts.keys() & new_prompts.keys())
    assert len(linked.resource_ledger.transactions) > 12
    assert len([e for e in linked.resource_ledger.transactions if e['category'].startswith('institution_transfer_')]) == 12
    linked.resource_ledger.reconcile(6, linked.ecosystem.agent_population, require_closed=True)
    assert linked.resource_ledger.to_dict()['native_transfer_accounting'] is True
    disconnected.llm.response_cache.close()
    linked.llm.response_cache.close()


def test_delayed_resource_queue_and_ledger_survive_cold_restart(tmp_path, fixed_corpus):
    executor = DockerCodeExecutor()
    spec = transfer_spec(executor.image_id, latency=1)
    reference, calls = real_sim(tmp_path / 'reference', spec, executor)
    reference.run()
    expected = science_snapshot(reference)
    reference.llm.response_cache.close()
    seed()
    stopped, requests = real_sim(tmp_path / 'resume', spec, executor, after_effects=True)
    with pytest.raises(PortableStop):
        stopped.run()
    stopped.llm.response_cache.close()
    restored, _ = real_sim(tmp_path / 'resume', spec, executor)
    restored.run()
    assert science_snapshot(restored) == expected
    events = [e for e in restored.native_system.events if e.event_type == EVENT]
    assert len(events) == 5 and min(e.year for e in events) == 2
    assert len({e.payload['transaction_key'] for e in events}) == 5
    assert len([e for e in restored.resource_ledger.transactions if e['category'].startswith('institution_transfer_')]) == 10
    restored.llm.response_cache.close()
