"""Persistent extensible native entities/effects; scripted HTTP, real Docker QA."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from tests.runtime.test_portable_checkpoint_integration import FakeHTTPModel, SmallRealSimulation, fixed_corpus, seed, science_snapshot
from tests.system.test_native_science_kernel import make_sim, original_science
from tests.system.test_native_resource_transfers import Actor
from utopia.funding.accounting import ResourceLedger
from utopia.runtime.checkpointing import PortableStop, capture_rng
from utopia.system import AgentTypeSpec, ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from utopia.system.code_mechanisms import CODE_SCHEMA, DockerCodeExecutor, sha
from utopia.system.native_kernel import NativeScienceKernel, WORLD_ARTIFACT, legacy_world_system, _hash
from utopia.system.native_migration import commit_native_design
from utopia.system.native_open_domain import (
    BOOTSTRAP, COMMAND_SCHEMA, EVENT, IMPLEMENTATION, STATE_ARTIFACT, add_domain_action_receiver,
    apply_domain_commands, validate_domain_state,
)
from utopia.system.runtime import DeliveredValue, GraphRuntimeError, MechanismContext


CAPABILITIES = {'bootstrap': ['actor.create'], 'roles': {'unanticipated-planner': [
    'actor.update', 'artifact.create', 'artifact.update', 'state.put', 'native.context', 'native.project', 'native.transfer']}}


def declared_world():
    spec = legacy_world_system()
    return replace(spec, agent_types=(*spec.agent_types, AgentTypeSpec('new-research-cooperative', ('unanticipated-planner',))),
        artifact_types=(*spec.artifact_types, ArtifactTypeSpec('new-protocol-record'), ArtifactTypeSpec('any-source-protocol')))


def command(identity, action, payload, principal='cooperative'):
    return {'schema': COMMAND_SCHEMA, 'command_id': identity, 'actor_id': principal, 'action': action, 'payload': payload}


def value(body, *, emitted=1):
    return DeliveredValue(ChannelKind.ARTIFACT, 'any-source-protocol', body, (), (),
        ('actual-sandbox-source-event',), 'free-institution-source', 'commands', emitted, emitted)


def create_actor():
    return command('create', 'actor.create', {'id': 'cooperative', 'type': 'new-research-cooperative',
        'roles': ['unanticipated-planner'], 'state': {'arbitrary': [1, 'not a fixed ontology']}}, BOOTSTRAP)


def unit_world(*, ledger=False):
    kernel = NativeScienceKernel(declared_world())
    actors = {'a': Actor('a', 20.), 'b': Actor('b', 10.)}
    accounting = ResourceLedger() if ledger else None
    if accounting:
        accounting.start_year(1, actors)
    for actor in actors.values():
        actor.resource_ledger = accounting
    kernel._simulation = SimpleNamespace(ecosystem=SimpleNamespace(agent_population=actors,
        get_available_authors=lambda: list(actors.values())), resource_ledger=accounting,
        paper_tracker=SimpleNamespace(papers_by_id={}))
    kernel._frame = {'year': 1, 'results': {}}
    node = MechanismSpec('domain-actions', MechanismFamily.CUSTOM, IMPLEMENTATION,
        inputs=(PortSpec('commands', ChannelKind.ARTIFACT, 'any-source-protocol', required=False),),
        parameters={'capabilities': deepcopy(CAPABILITIES)})
    ctx = MechanismContext(kernel.spec.system_id, kernel.spec.fingerprint, node, 1, 15, 'annual', {}, {}, {})
    return kernel, actors, accounting, ctx


def run_commands(kernel, ctx, *commands):
    return apply_domain_commands(kernel, replace(ctx, inputs={'commands': tuple(value(c) for c in commands)}))


def test_data_defined_actor_artifact_custom_state_real_input_and_conserving_resources():
    kernel, actors, ledger, ctx = unit_world(ledger=True)
    artifact = command('artifact', 'artifact.create', {'id': 'assay-record', 'type': 'new-protocol-record',
        'owner_actor': 'cooperative', 'content': {'hypothesis': 'arbitrary text', 'timestamp': 17},
        'actor_ids': ['cooperative', 'a'], 'artifact_ids': [], 'native_paper_ids': []})
    state = command('state', 'state.put', {'key': 'unanticipated-memory', 'value': {'tensor': [[1, 2]]}, 'expected_revision': None})
    context = command('input', 'native.context', {'actor_ids': ['a'], 'content': {'instruction': 'actual input'}, 'artifact_ids': ['assay-record']})
    transfer = command('transfer', 'native.transfer', {'from_actor': 'b', 'to_actor': 'a', 'amount': 2.})
    result = run_commands(kernel, ctx, create_actor(), artifact, state, context, transfer)
    assert actors['a'].resources == 22. and actors['b'].resources == 8.
    assert len(ledger.transactions) == 2
    assert actors['a'].institutional_context[0]['origin_actor_id'] == 'cooperative'
    assert actors['a'].institutional_context[0]['artifact_records'][0]['content']['timestamp'] == 17
    assert len(kernel.open_domain_state['values']) == 1
    validate_domain_state(kernel.open_domain_state, events=result.events)
    assert any(e.event_type == 'agent.registered' for e in result.events)
    before = deepcopy(kernel.open_domain_state), deepcopy(ledger.to_dict())
    assert not run_commands(kernel, ctx, create_actor(), artifact, state, context, transfer).events
    assert (kernel.open_domain_state, ledger.to_dict()) == before
    with pytest.raises(GraphRuntimeError, match='replayed'):
        run_commands(kernel, ctx, {**create_actor(), 'payload': {**create_actor()['payload'], 'state': {}}})


@pytest.mark.parametrize('bad', [
    command('unknown', 'native.context', {'actor_ids': ['absent'], 'content': {}, 'artifact_ids': []}),
    command('role', 'actor.create', {'id': 'other', 'type': 'new-research-cooperative', 'roles': [], 'state': {}}),
    command('revision', 'actor.update', {'id': 'cooperative', 'expected_revision': 9, 'roles': [], 'state': {}}),
    command('mint', 'native.transfer', {'from_actor': 'b', 'to_actor': 'a', 'amount': 100.}),
    command('float', 'native.transfer', {'from_actor': 'b', 'to_actor': 'a', 'amount': 0.1}),
    command('artifact-bad', 'artifact.create', {'id': 'bad', 'type': 'new-protocol-record', 'owner_actor': 'cooperative',
        'content': {}, 'actor_ids': [], 'artifact_ids': [], 'native_paper_ids': ['nonexistent-paper']}),
])
def test_entire_batch_invalidity_has_no_custom_native_accounting_or_prompt_effect(bad):
    kernel, actors, ledger, ctx = unit_world(ledger=True)
    before = deepcopy(ledger.to_dict())
    with pytest.raises(GraphRuntimeError):
        run_commands(kernel, ctx, create_actor(), command('first', 'native.context', {
            'actor_ids': ['a'], 'content': {'must-not-commit': True}, 'artifact_ids': []}), bad)
    assert kernel.open_domain_state == {}
    assert actors['a'].resources == 20. and actors['b'].resources == 10.
    assert not hasattr(actors['a'], 'institutional_context')
    assert ledger.to_dict() == before and 'native_resource_transactions' not in kernel._frame


def test_runtime_resource_failure_rolls_back_all_base_native_and_domain_state():
    kernel, actors, ledger, ctx = unit_world(ledger=True)
    actors['a'].update_resources = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('actual credit failure'))
    before = deepcopy(ledger.to_dict())
    with pytest.raises(RuntimeError, match='actual credit failure'):
        run_commands(kernel, ctx, create_actor(), command('transfer', 'native.transfer', {'from_actor': 'b', 'to_actor': 'a', 'amount': 2.}))
    assert [a.resources for a in actors.values()] == [20., 10.]
    assert ledger.to_dict() == before and kernel.open_domain_state == {}


def test_additional_typed_handler_is_not_an_institution_menu():
    kernel, actors, ledger, ctx = unit_world()
    def arbitrary_plugin(tx, payload, principal):
        tx.deliver_context(['a'], {'unanticipated-action': payload['question'][::-1]}, principal=principal)
        tx.put_state('plugin-state', payload, principal=principal)
    kernel.domain_actions.register('new.action.from.plugin', {'type': 'object', 'required': ['question'],
        'properties': {'question': {'type': 'string'}}, 'additionalProperties': False}, arbitrary_plugin)
    capabilities = deepcopy(CAPABILITIES)
    capabilities['roles']['unanticipated-planner'].append('new.action.from.plugin')
    ctx = replace(ctx, mechanism=replace(ctx.mechanism, parameters={'capabilities': capabilities}))
    run_commands(kernel, ctx, create_actor(), command('plugin', 'new.action.from.plugin', {'question': 'science'}))
    assert actors['a'].institutional_context[0]['payload']['unanticipated-action'] == 'ecneics'
    assert next(iter(kernel.open_domain_state['values'].values()))['value'] == {'question': 'science'}


def test_custom_action_registration_is_rebuilt_for_each_runtime_and_preview():
    def extend(kernel, mechanism_registry):
        kernel.domain_actions.register('plugin.explicit.capability', {'type': 'object'}, lambda tx, p, principal: None)
    kernel = NativeScienceKernel(declared_world(), registry_extension=extend)
    kernel._registry()
    kernel._registry()  # annual construction must not duplicate old registrations
    assert 'plugin.explicit.capability' in kernel.domain_actions.actions


def test_invalid_plugin_result_is_rejected_before_native_commit():
    kernel, actors, ledger, ctx = unit_world(ledger=True)
    def invalid_plugin(tx, payload, principal):
        tx.deliver_context(['a'], {'not-json': object()}, principal=principal)
    kernel.domain_actions.register('plugin.invalid.result', {'type': 'object'}, invalid_plugin)
    capabilities = deepcopy(CAPABILITIES)
    capabilities['roles']['unanticipated-planner'].append('plugin.invalid.result')
    ctx = replace(ctx, mechanism=replace(ctx.mechanism, parameters={'capabilities': capabilities}))
    before = deepcopy(ledger.to_dict())
    with pytest.raises(GraphRuntimeError, match='strict JSON'):
        run_commands(kernel, ctx, create_actor(), command('plugin', 'plugin.invalid.result', {}))
    assert kernel.open_domain_state == {} and not hasattr(actors['a'], 'institutional_context')
    assert ledger.to_dict() == before


def test_invalid_output_declaration_is_rejected_before_native_commit():
    kernel, actors, ledger, ctx = unit_world()
    ctx = replace(ctx, mechanism=replace(ctx.mechanism, outputs=(
        PortSpec('incorrect-port', ChannelKind.ARTIFACT, STATE_ARTIFACT),)))
    with pytest.raises(GraphRuntimeError, match='undeclared output'):
        run_commands(kernel, ctx, create_actor())
    assert kernel.open_domain_state == {}


def test_data_schema_constraints_and_receipt_content_corruption_fail_closed():
    kernel, actors, ledger, ctx = unit_world()
    ctx = replace(ctx, mechanism=replace(ctx.mechanism, parameters={**ctx.mechanism.parameters,
        'actor_schemas': {'new-research-cooperative': {'type': 'object', 'required': ['required-scientific-state']}}}))
    with pytest.raises(GraphRuntimeError, match='payload/schema'):
        run_commands(kernel, ctx, create_actor())
    assert kernel.open_domain_state == {}
    kernel, actors, ledger, ctx = unit_world()
    result = run_commands(kernel, ctx, create_actor())
    state = deepcopy(kernel.open_domain_state)
    state['actors']['cooperative']['state']['fabricated'] = True
    with pytest.raises(GraphRuntimeError, match='content differs'):
        validate_domain_state(state, events=result.events)


SOURCE = '''def step(context):
    w = context['inputs']['world'][0]['payload']
    year = context['period']
    domain = w.get('open_domain', {'actors': {}, 'values': {}})
    authors = [a['id'] for a in w['ecosystem']['agents'] if a['can_author']]
    out = []
    def emit(identity, action, payload, actor='cooperative'):
        out.append({'payload': dict(schema='native-domain-command-v1', command_id=identity,
            actor_id=actor, action=action, payload=payload)})
    old = domain['actors'].get('cooperative')
    if old is None:
        emit('create', 'actor.create', dict(id='cooperative', type='new-research-cooperative',
            roles=['unanticipated-planner'], state={'turns': 0}), '$mechanism')
        revision, turns = 0, 0
    else:
        revision, turns = old['revision'], old['state']['turns']
    emit('update', 'actor.update', dict(id='cooperative', expected_revision=revision,
        roles=['unanticipated-planner'], state={'turns': turns + 1, 'timestamp': year}))
    note = 'protocol-record-' + str(year)
    emit('scientific-artifact', 'artifact.create', dict(id=note, type='new-protocol-record',
        owner_actor='cooperative', content={'hypothesis': 'OPEN_DOMAIN_V7 reciprocal replication', 'round': turns + 1},
        actor_ids=['cooperative', authors[0]], artifact_ids=[],
        native_paper_ids=[p['id'] for p in w['papers']['papers'][:1]]))
    emit('real-input', 'native.context', dict(actor_ids=[authors[0]],
        content={'proposal': 'OPEN_DOMAIN_V7 reciprocal replication', 'turn': turns + 1}, artifact_ids=[note]))
    emit('real-project', 'native.project', dict(assignment=dict(actor_id=authors[0],
        direction=dict(topic='New institution-chosen scientific topic', focus_areas=['replication'], years=1,
            keywords=['replication', 'institutional design'], related_topics=[]),
        detailed_focus='OPEN_DOMAIN_V7 project chosen by custom persistent actor', reason='code-defined actor initiative',
        project_start_year=year, project_end_year=year)))
    emit('real-resource', 'native.transfer', dict(from_actor=authors[1], to_actor=authors[0], amount=1.0))
    emit('persistent-state', 'state.put', dict(key='arbitrary-measurement-history', value={'round': turns + 1},
        expected_revision=turns - 1 if turns else None))
    return {'outputs': {'commands': out}, 'state': {'source_cycles': year}}
'''


def source_spec(image, *, linked=True, source=SOURCE, latency=0):
    spec = declared_world()
    node = MechanismSpec('free-institution-source', MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('world', ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
        outputs=(PortSpec('commands', ChannelKind.ARTIFACT, 'any-source-protocol', required=False),),
        parameters={'runtime_image_id': image, 'code_artifact': {'schema': CODE_SCHEMA,
            'label': 'Scripted arbitrary actor institution, not live invention', 'source': source,
            'inputs': {'world': {'type': 'object'}}, 'outputs': {'commands': {'type': 'object'}},
            'state_schema': {'type': 'object'}}})
    spec = replace(spec, mechanisms=(*spec.mechanisms, node),
        schedules=(*spec.schedules, ScheduleSpec(node.mechanism_id, 10)),
        connections=(*spec.connections, ConnectionSpec('world.open', 'world', node.mechanism_id, 'world', ChannelKind.ARTIFACT)))
    if linked:
        spec = add_domain_action_receiver(spec, source=node.mechanism_id, source_port='commands', capabilities=CAPABILITIES, latency=latency)
    return spec


def native_sim(root, spec, executor, *, stopped=False):
    calls = []
    sim = SmallRealSimulation(root, FakeHTTPModel(root, calls), ledger=True, after_effects=stopped)
    sim.native_system = NativeScienceKernel(spec, code_executor=executor)
    return sim, calls


def test_absent_domain_retains_original_six_year_science_and_every_request(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    baseline, old_calls = make_sim(tmp_path / 'old')
    baseline.run()
    seed()
    native, calls = make_sim(tmp_path / 'native', native=NativeScienceKernel(legacy_world_system()))
    native.run()
    assert original_science(native) == original_science(baseline)
    assert [p for _, p in calls] == [p for _, p in old_calls]
    assert 'open_domain' not in native.native_system.to_dict()
    baseline.llm.response_cache.close()
    native.llm.response_cache.close()


def test_custom_actor_scientific_record_and_actions_really_change_native_world(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    executor = DockerCodeExecutor()
    disconnected, old_calls = native_sim(tmp_path / 'off', source_spec(executor.image_id, linked=False), executor)
    disconnected.run()
    seed()
    native, calls = native_sim(tmp_path / 'on', source_spec(executor.image_id), executor)
    native.run()
    state = native.native_system.open_domain_state
    assert state['actors']['cooperative']['state']['turns'] == 6
    assert len(state['artifacts']) == 6 and len(state['values']) == 1
    validate_domain_state(state, events=native.native_system.events)
    original_checkpoint = native.native_system.to_dict()
    corrupted = deepcopy(original_checkpoint)
    corrupted['open_domain']['actors']['cooperative']['state']['fabricated'] = True
    with pytest.raises(GraphRuntimeError, match='content differs'):
        native.native_system.restore(corrupted)
    assert native.native_system.to_dict() == original_checkpoint
    omitted = {k: v for k, v in original_checkpoint.items() if k != 'open_domain'}
    with pytest.raises(GraphRuntimeError, match='missing its persistent state'):
        native.native_system.restore(omitted)
    assert native.native_system.to_dict() == original_checkpoint
    assert any('OPEN_DOMAIN_V7' in json.dumps(p) for (ctx, _, _), p in calls if ctx[:2] == ('phase2_intentions', 1))
    assert not any('OPEN_DOMAIN_V7' in json.dumps(p) for _, p in old_calls)
    assert len([1 for (ctx, _, _), p in calls if ctx[:2] == ('phase1_directions', 1)]) == 3
    assert len([1 for (ctx, _, _), p in old_calls if ctx[:2] == ('phase1_directions', 1)]) == 4
    assert native.ecosystem.get_available_authors()[0].newest_direction['direction'].topic == 'New institution-chosen scientific topic'
    assert len([r for r in native.resource_ledger.transactions if r['category'].startswith('institution_transfer_')]) == 12
    by_id = {e.event_id: e for e in native.native_system.events}
    for receipt in state['receipts'].values():
        assert all(by_id[i].event_type == 'generated.code_executed' for i in receipt['input_event_ids'])
    from utopia.replay import ArtifactBundle, convert_artifacts, validate_references
    checkpoint = __import__('pathlib').Path(native.output_dir) / 'portable_checkpoint_year_6.json.gz'
    assert validate_references(convert_artifacts(ArtifactBundle.discover(checkpoint))) == []
    native.llm.response_cache.close()
    disconnected.llm.response_cache.close()


def test_domain_native_effects_and_source_survive_interruption_cold_restart(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    executor = DockerCodeExecutor()
    spec = source_spec(executor.image_id)
    reference, _ = native_sim(tmp_path / 'reference', spec, executor)
    reference.run()
    seed()
    stopped, _ = native_sim(tmp_path / 'restart', spec, executor, stopped=True)
    with pytest.raises(PortableStop):
        stopped.run()
    stopped.llm.response_cache.close()
    resumed, _ = native_sim(tmp_path / 'restart', spec, executor)
    resumed.run()
    assert science_snapshot(resumed) == science_snapshot(reference)
    assert resumed.native_system.to_dict() == reference.native_system.to_dict()
    resumed.llm.response_cache.close()
    reference.llm.response_cache.close()


def test_persistent_domain_survives_actual_same_society_migration_and_cold_bootstrap(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    executor = DockerCodeExecutor()
    spec = source_spec(executor.image_id)
    sim, _ = native_sim(tmp_path / 'society', spec, executor)
    original = sim.checkpoint_callback
    def boundary(path):
        original(path)
        if sim.native_system.last_year != 2:
            return
        before, rng = deepcopy(sim.native_system.open_domain_state), capture_rng()
        removed = {'free-institution-source', 'open-domain-actions'}
        target = replace(sim.native_system.spec,
            mechanisms=tuple(n for n in sim.native_system.spec.mechanisms if n.mechanism_id not in removed),
            schedules=tuple(s for s in sim.native_system.spec.schedules if s.mechanism_id not in removed),
            connections=tuple(c for c in sim.native_system.spec.connections
                if c.source_mechanism not in removed and c.target_mechanism not in removed),
            agent_types=tuple(t for t in sim.native_system.spec.agent_types if t.agent_type_id != 'new-research-cooperative'),
            metadata={**sim.native_system.spec.metadata, 'arbitrary-new-process-description': 'creator removed; society persists'})
        commit_native_design(sim, target, expected_checkpoint_sha256=_hash(sim.native_system.to_dict()))
        assert sim.native_system.open_domain_state == before and capture_rng() == rng
    sim.checkpoint_callback = boundary
    sim.run()
    expected = sim.native_system.to_dict()
    sim.llm.response_cache.close()
    seed()
    resumed, calls = native_sim(tmp_path / 'society', spec, executor)
    resumed.run()
    assert not calls and resumed.native_system.to_dict() == expected
    assert resumed.native_system.open_domain_state['actors']['cooperative']['state']['turns'] == 2
    assert len(resumed.native_system.open_domain_state['artifacts']) == 2
    assert not any(n.mechanism_id == 'free-institution-source' for n in resumed.native_system.spec.mechanisms)
    resumed.llm.response_cache.close()


DELAYED_SOURCE = '''def step(context):
    if context['period'] != 1:
        return {'outputs': {'commands': []}, 'state': {}}
    world = context['inputs']['world'][0]['payload']
    author = next(a['id'] for a in world['ecosystem']['agents'] if a['can_author'])
    def command(identity, action, payload, actor='cooperative'):
        return {'payload': dict(schema='native-domain-command-v1',command_id=identity,actor_id=actor,action=action,payload=payload)}
    return {'outputs': {'commands': [
        command('create', 'actor.create', dict(id='cooperative',type='new-research-cooperative',roles=['unanticipated-planner'],state={}), '$mechanism'),
        command('delayed-input', 'native.context', dict(actor_ids=[author],content={'proposal':'DELAYED_CUSTOM_ACTOR_V7'},artifact_ids=[]))]}, 'state': {}}
'''


def test_delayed_actor_creation_input_and_pending_messages_survive_cold_checkpoint(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    executor = DockerCodeExecutor()
    spec = source_spec(executor.image_id, source=DELAYED_SOURCE, latency=1)
    stopped, calls0 = native_sim(tmp_path / 'delayed', spec, executor)
    original = stopped.checkpoint_callback
    def boundary(path):
        original(path)
        if stopped.native_system.last_year == 1:
            assert stopped.native_system.open_domain_state == {}
            assert stopped.native_system.graph_checkpoint['queued_deliveries']
            raise PortableStop('inspect cold delayed creation')
    stopped.checkpoint_callback = boundary
    with pytest.raises(PortableStop):
        stopped.run()
    assert not any('DELAYED_CUSTOM_ACTOR_V7' in json.dumps(p) for _, p in calls0)
    stopped.llm.response_cache.close()
    seed()
    resumed, calls = native_sim(tmp_path / 'delayed', spec, executor)
    resumed.run()
    years = [ctx[1] for (ctx, _, _), p in calls if ctx[0] == 'phase1_directions'
        and 'DELAYED_CUSTOM_ACTOR_V7' in json.dumps(p)]
    assert min(years) == 2
    assert resumed.native_system.open_domain_state['actors']['cooperative']['created_year'] == 2
    receipts = resumed.native_system.open_domain_state['receipts']
    assert len(receipts) == 2
    assert all(r['origin']['emitted_period'] == 1 and r['received_year'] == 2 for r in receipts.values())
    resumed.llm.response_cache.close()
