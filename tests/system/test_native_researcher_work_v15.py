"""Open scientific work: original native researchers, scripted HTTP, real Docker.

No model is downloaded/called; SCRIPTED replies only test executable plumbing.
"""
from copy import deepcopy
from dataclasses import replace
import json

from openai.types.chat import ChatCompletion
import pytest

from tests.runtime.test_portable_checkpoint_integration import FakeHTTPModel, SmallRealSimulation, fixed_corpus, seed, science_snapshot
from tests.system.test_native_science_kernel import make_sim
from utopia.runtime.checkpointing import PortableStop
from utopia.replay.events import EventEnvelope
from utopia.system import AgentTypeSpec, ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from utopia.system.code_mechanisms import CODE_SCHEMA, DockerCodeExecutor, sha
from utopia.system.native_kernel import NativeScienceKernel, WORLD_ARTIFACT, legacy_world_system
from utopia.system.native_open_domain import add_domain_action_receiver
from utopia.system.native_process import controlled_activity
from utopia.system.native_researcher_work import (
    EVENT, IMPLEMENTATION, REQUEST, RESPONSE, STATE,
    add_researcher_work_receiver, execute_researcher_work, validate_work_checkpoint,
    validate_work_node, validate_work_receipt, validate_work_request, validate_work_state,
)
from utopia.system.runtime import DeliveredValue, GraphRuntimeError, MechanismContext


class WorkHTTPModel(FakeHTTPModel):
    def reply(self, **payload):
        self.context = self.contexts.get(payload['extra_body']['seed'], getattr(self, 'context', None))
        if self.context[0][0] != 'native_researcher_work_v15':
            return super().reply(**payload)
        data = json.loads(payload['messages'][-1]['content'].rsplit('\n', 1)[-1])
        request = data['request']
        result = {'proposal': 'WORK_V15_RESPONSE ' + request['content']['question'],
                  'author': data['actual_researcher_state']['actor_id']}
        self.requests.append((self.context, payload))
        return ChatCompletion.model_validate(dict(id='work-scripted', object='chat.completion', created=0,
            model=self.model_name, choices=[dict(index=0, message=dict(role='assistant', content=json.dumps(result)), finish_reason='stop')],
            usage=dict(prompt_tokens=5, completion_tokens=3, total_tokens=8)))


def request(**changes):
    return {'schema': REQUEST, 'request_id': 'arbitrary-discussion', 'actor_id': 'researcher-0',
        'instruction': 'Discuss the supplied open scientific record using your own research experience.',
        'content': {'question': 'an arbitrary institution-defined scientific question'}, 'artifact_ids': [],
        'response_schema': {'type': 'object', 'properties': {'proposal': {'type': 'string'}, 'author': {'type': 'string'}},
            'required': ['proposal', 'author'], 'additionalProperties': False}, **changes}


def delivered(body=None, *, source='free-institution', emitted=1):
    body = body or request()
    return DeliveredValue(ChannelKind.ARTIFACT, REQUEST, body, (body['actor_id'],), tuple(body['artifact_ids']),
        ('actual-source-event',), source, 'tasks', emitted, emitted)


def unit(tmp_path, *, cap=2):
    sim, calls = make_sim(tmp_path, model_class=WorkHTTPModel)
    sim.initialize_agents()
    node = MechanismSpec('work', MechanismFamily.CUSTOM, IMPLEMENTATION,
        inputs=(PortSpec('tasks', ChannelKind.ARTIFACT, REQUEST, required=False),),
        outputs=(PortSpec('responses', ChannelKind.ARTIFACT, RESPONSE, required=False),),
        parameters={'max_requests_per_invocation': cap})
    kernel = NativeScienceKernel(legacy_world_system())
    kernel._simulation, kernel._frame = sim, {'year': 1, 'results': {}}
    context = MechanismContext(kernel.spec.system_id, kernel.spec.fingerprint, node, 1, 25, 'annual',
        {'tasks': (delivered(),)}, {}, {})
    return sim, calls, kernel, context


def test_arbitrary_task_uses_real_fixed_author_persona_memory_context_and_transport(tmp_path, fixed_corpus):
    sim, calls, kernel, context = unit(tmp_path)
    actor = sim.ecosystem.agent_population['researcher-0']
    actor.memory_bank.append({'type': 'new-experience', 'year': 1, 'thought': 'REAL_AUTHOR_MEMORY_V15'})
    actor.institutional_context = [{'payload': {'message': 'REAL_INSTITUTION_INPUT_V15'}}]
    before = deepcopy(sim.ecosystem.to_dict())
    result = execute_researcher_work(kernel, context)
    assert len(calls) == 1 and len(result.events) == 1
    record = result.events[0].payload
    validate_work_receipt(record); validate_work_state(result.next_state)
    assert record['native_snapshot']['actor_id'] == 'researcher-0'
    assert 'university-0' in record['prompt'] and 'REAL_AUTHOR_MEMORY_V15' in record['prompt']
    assert 'REAL_INSTITUTION_INPUT_V15' in record['prompt']
    assert result.outputs['responses'][0].payload['response']['author'] == actor.id
    assert sim.ecosystem.to_dict() == before  # no impersonated privileged state changes
    assert calls[0][0][0] == tuple(record['seed_ctx'])
    sim.llm.response_cache.close()


@pytest.mark.parametrize('bad', [
    request(actor_id='invented-researcher'), request(artifact_ids=['invented-artifact']),
    request(response_schema={'type': 'object', 'properties': {'x': {'$ref': 'file:///private'}}}),
    request(content={'x': float('nan')}), request(response_schema={'type': 'array'}),
    request(instruction=''),
])
def test_entire_batch_preflight_rejects_bad_later_task_before_any_model_call(tmp_path, fixed_corpus, bad):
    sim, calls, kernel, context = unit(tmp_path)
    context = replace(context, inputs={'tasks': (delivered(), delivered(bad, source='other-source'))})
    with pytest.raises(GraphRuntimeError):
        execute_researcher_work(kernel, context)
    assert calls == [] and sim.llm.response_cache.committed_count() == 0
    sim.llm.response_cache.close()


def test_explicit_cap_and_duplicate_never_clip_or_reroll(tmp_path, fixed_corpus):
    sim, calls, kernel, context = unit(tmp_path, cap=1)
    with pytest.raises(GraphRuntimeError, match='cap'):
        execute_researcher_work(kernel, replace(context, inputs={'tasks': (delivered(), delivered())}))
    assert not calls
    result = execute_researcher_work(kernel, context)
    with pytest.raises(GraphRuntimeError, match='duplicate'):
        execute_researcher_work(kernel, replace(context, state=result.next_state))
    assert len(calls) == 1
    sim.llm.response_cache.close()


@pytest.mark.parametrize('cap', [True, 0, -1, 65, 1.5, '2'])
def test_invalid_compute_caps_are_not_coerced(tmp_path, fixed_corpus, cap):
    sim, calls, kernel, context = unit(tmp_path, cap=cap)
    with pytest.raises(GraphRuntimeError, match='cap'):
        execute_researcher_work(kernel, context)
    assert not calls
    sim.llm.response_cache.close()


def test_multiple_outputs_have_no_future_task_event_ancestry(tmp_path, fixed_corpus):
    sim, calls, kernel, context = unit(tmp_path)
    second = delivered(request(request_id='second-independent-task'))
    result = execute_researcher_work(kernel, replace(context, inputs={'tasks': (delivered(), second)}))
    assert len(calls) == 2
    assert [v.event_prefix_length for v in result.outputs['responses']] == [1, 2]
    assert result.next_state['receipts'][1]['previous_receipt_sha256'] == result.events[0].payload['receipt_sha256']
    validate_work_state(result.next_state)
    sim.llm.response_cache.close()


def test_empty_task_batch_is_explicit_no_work_not_a_fake_reply(tmp_path, fixed_corpus):
    sim, calls, kernel, context = unit(tmp_path)
    result = execute_researcher_work(kernel, replace(context, inputs={'tasks': ()}))
    assert result.outputs == {'responses': ()} and not result.events and not calls
    validate_work_state(result.next_state)
    sim.llm.response_cache.close()


def test_task_source_body_and_process_iteration_have_distinct_actual_request_cache_identities(tmp_path, fixed_corpus):
    sim, calls, kernel, context = unit(tmp_path)
    results = []
    variants = [context,
        replace(context, inputs={'tasks': (delivered(source='different-source'),)}),
        replace(context, inputs={'tasks': (delivered(request(content={'question': 'different question'})),)}),
        replace(context, mechanism=replace(context.mechanism, mechanism_id='work.iteration-1'))]
    for variant in variants:
        results.append(execute_researcher_work(kernel, variant))
    assert len(calls) == 4 and len({tuple(r.events[0].payload['seed_ctx']) for r in results}) == 4
    # A cold rewind of the SAME physical task reuses its exact durable response.
    replay = execute_researcher_work(kernel, context)
    assert len(calls) == 4 and replay == results[0]
    sim.llm.response_cache.close()


@pytest.mark.parametrize('change', ['response', 'request', 'snapshot', 'artifact', 'seed', 'origin', 'chain'])
def test_receipt_semantic_hashes_and_authorship_reject_corruption(tmp_path, fixed_corpus, change):
    sim, _, kernel, context = unit(tmp_path)
    record = deepcopy(execute_researcher_work(kernel, context).events[0].payload)
    if change == 'response': record['response']['author'] = 'invented'
    if change == 'request': record['request']['actor_id'] = 'invented'
    if change == 'snapshot': record['native_snapshot']['actor_id'] = 'invented'
    if change == 'artifact': record['request']['artifact_ids'] = ['invented']
    if change == 'seed': record['seed_ctx'][2] = 'another-iteration'
    if change == 'origin': record['origin']['source_mechanism'] = 'another-source'
    if change == 'chain': record['previous_receipt_sha256'] = '0' * 64
    record['receipt_sha256'] = sha({k: v for k, v in record.items() if k != 'receipt_sha256'})
    with pytest.raises(GraphRuntimeError):
        validate_work_state({'schema': STATE, 'receipts': [record]})
    sim.llm.response_cache.close()


def test_schema_invalid_model_response_not_committed_or_replaced(tmp_path, fixed_corpus):
    sim, calls, kernel, context = unit(tmp_path)
    body = request(response_schema={'type': 'object', 'required': ['a-field-the-model-did-not-return']})
    context = replace(context, inputs={'tasks': (delivered(body),)})
    with pytest.raises(GraphRuntimeError, match='response violates'):
        execute_researcher_work(kernel, context)
    assert len(calls) == 1 and sim.llm.response_cache.committed_count() == 1
    assert context.state == {}  # external cost is retained, not fictitiously rolled back
    sim.llm.response_cache.close()


def test_resolves_real_native_paper_content_without_creating_or_scoring_a_paper(tmp_path, fixed_corpus):
    from utopia.data.paper_tracker import ArchivedPaper
    sim, calls, kernel, context = unit(tmp_path)
    paper = ArchivedPaper('existing-native-paper', 'Actual fixture paper', 'Actual fixture abstract',
        'researcher-1', 'university', 1, 'fixture-venue', 'pending')
    sim.paper_tracker.papers_by_id[paper.id] = paper
    before = deepcopy(paper.to_dict())
    body = request(artifact_ids=[paper.id])
    result = execute_researcher_work(kernel, replace(context, inputs={'tasks': (delivered(body),)}))
    record = result.events[0].payload
    assert record['native_snapshot']['artifact_records'] == [{'id': paper.id, 'kind': 'native-paper', 'record': before}]
    assert paper.to_dict() == before and list(sim.paper_tracker.papers_by_id) == [paper.id]
    sim.llm.response_cache.close()


def test_sandbox_event_cannot_impersonate_completed_original_researcher_work(tmp_path, fixed_corpus):
    sim, _, kernel, context = unit(tmp_path)
    record = execute_researcher_work(kernel, context).events[0].payload
    forged = EventEnvelope.create(sequence=0, year=1, phase=25, event_type=EVENT,
        actor_ids=('researcher-0',), payload=record,
        provenance={'mechanism_id': 'free-source', 'implementation': 'code.python.v1',
            'input_event_ids': ['actual-source-event']})
    with pytest.raises(GraphRuntimeError, match='canonical receipt'):
        validate_work_checkpoint(kernel.spec, None, [forged])
    sim.llm.response_cache.close()


def test_delayed_work_request_shape_is_checked_before_cold_replay(tmp_path, fixed_corpus):
    sim, _, kernel, context = unit(tmp_path)
    spec = replace(kernel.spec, mechanisms=(*kernel.spec.mechanisms, context.mechanism),
        artifact_types=(*kernel.spec.artifact_types, ArtifactTypeSpec(REQUEST), ArtifactTypeSpec(RESPONSE)),
        schedules=(*kernel.spec.schedules, ScheduleSpec('work', 25)))
    malformed = request(response_schema={'type': 'object', '$ref': 'https://must-not-resolve.invalid/schema'})
    graph = {'mechanism_states': {}, 'queued_deliveries': [{'target_mechanism': 'work', 'target_port': 'tasks',
        'value': {'payload': malformed}}]}
    with pytest.raises(GraphRuntimeError, match='schema'):
        validate_work_checkpoint(spec, graph, [])
    sim.llm.response_cache.close()


SOURCE = '''def step(context):
    world = context['inputs']['world'][0]['payload']
    author = [a for a in world['ecosystem']['agents'] if a['can_author']][0]['id']
    year = context['period']
    commands = []
    if year == 1:
        commands.append({'payload': {'schema': 'native-domain-command-v1', 'command_id': 'create-cooperative',
            'actor_id': '$mechanism', 'action': 'actor.create', 'payload': {'id': 'cooperative',
            'type': 'open-scientific-cooperative', 'roles': ['arbitrary-work-authority'], 'state': {}}}})
    note = 'custom-record-' + str(year)
    commands.append({'payload': {'schema': 'native-domain-command-v1', 'command_id': 'create-note',
        'actor_id': 'cooperative', 'action': 'artifact.create', 'payload': {'id': note,
        'type': 'open-scientific-note', 'owner_actor': 'cooperative',
        'content': {'question': 'Not a paper or a review: discuss the new custom artifact.',
            'timestamp': 'SCIENTIFIC_FIELD_NOT_AN_OPERATIONAL_CLOCK_V15'},
        'actor_ids': [author], 'artifact_ids': [], 'native_paper_ids': []}}})
    task = {'schema': 'native-researcher-work-request-v15', 'request_id': 'open-artifact-discussion',
        'actor_id': author, 'instruction': 'Discuss the custom scientific artifact and propose a next question.',
        'content': {'question': 'OPEN_WORK_V15'}, 'artifact_ids': [note],
        'response_schema': {'type': 'object', 'properties': {'proposal': {'type': 'string'}, 'author': {'type': 'string'}},
            'required': ['proposal', 'author'], 'additionalProperties': False}}
    return {'outputs': {'commands': commands, 'tasks': [{'payload': task, 'actor_ids': [author], 'artifact_ids': [note]}]}, 'state': {}}
'''

CONSUMER = '''def step(context):
    commands = []
    for item in context['inputs']['responses']:
        body = item['payload']
        commands.append({'payload': {'schema': 'native-domain-command-v1', 'command_id': body['request_id'],
            'actor_id': 'cooperative', 'action': 'native.context', 'payload': {
                'actor_ids': [body['actor_id']], 'content': {'authored-protocol': body['response']},
                'artifact_ids': item['artifact_ids']}}})
    return {'outputs': {'commands': commands}, 'state': {}}
'''


def code_node(identity, image, source, inputs, outputs):
    return MechanismSpec(identity, MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=tuple(PortSpec(k, ChannelKind.ARTIFACT, v, required=False) for k, v in inputs.items()),
        outputs=tuple(PortSpec(k, ChannelKind.ARTIFACT, v, required=False) for k, v in outputs.items()),
        parameters={'runtime_image_id': image, 'code_artifact': {'schema': CODE_SCHEMA,
            'label': 'SCRIPTED open-work capability QA, not model-invented science', 'source': source,
            'inputs': {k: {'type': 'object'} for k in inputs}, 'outputs': {k: {'type': 'object'} for k in outputs},
            'state_schema': {'type': 'object'}}})


def world_spec(image, *, connected=True, repeated=1):
    spec = legacy_world_system()
    author = code_node('unanticipated-institution', image, SOURCE, {'world': WORLD_ARTIFACT}, {'commands': 'commands', 'tasks': REQUEST})
    consumer = code_node('unanticipated-consumer', image, CONSUMER, {'responses': RESPONSE}, {'commands': 'commands'})
    spec = replace(spec, agent_types=(*spec.agent_types, AgentTypeSpec('open-scientific-cooperative', ('arbitrary-work-authority',))),
        artifact_types=(*spec.artifact_types, ArtifactTypeSpec('open-scientific-note'), ArtifactTypeSpec('commands'), ArtifactTypeSpec(REQUEST), ArtifactTypeSpec(RESPONSE)),
        mechanisms=(*spec.mechanisms, author, consumer), schedules=(*spec.schedules, ScheduleSpec(author.mechanism_id, 10), ScheduleSpec(consumer.mechanism_id, 30)),
        connections=(*spec.connections, ConnectionSpec('world.open', 'world', author.mechanism_id, 'world', ChannelKind.ARTIFACT)))
    grants = {'bootstrap': ['actor.create'], 'roles': {'arbitrary-work-authority': ['artifact.create', 'native.context']}}
    spec = add_domain_action_receiver(spec, source=author.mechanism_id, source_port='commands', capabilities=grants, phase=15)
    spec = add_researcher_work_receiver(spec, source=author.mechanism_id, source_port='tasks', phase=25, max_requests_per_invocation=1)
    if repeated != 1:
        spec = replace(spec, mechanisms=tuple(controlled_activity(n, count=repeated, limit=3)
            if n.mechanism_id == 'researcher-work' else n for n in spec.mechanisms))
        if 'native-process-control-v1' not in {a.artifact_type_id for a in spec.artifact_types}:
            spec = replace(spec, artifact_types=(*spec.artifact_types, ArtifactTypeSpec('native-process-control-v1')))
    spec = replace(spec, connections=(*spec.connections, ConnectionSpec('researcher-work', 'responses', consumer.mechanism_id, 'responses', ChannelKind.ARTIFACT)))
    spec = add_domain_action_receiver(spec, source=consumer.mechanism_id, source_port='commands', capabilities=grants, receiver='response-effects', phase=35)
    if not connected:
        spec = replace(spec, connections=tuple(e for e in spec.connections if e.target_mechanism != 'researcher-work'))
    return spec


def world(root, spec, executor, *, stopped=False):
    calls = []
    sim = SmallRealSimulation(root, WorkHTTPModel(root, calls), after_effects=stopped)
    sim.native_system = NativeScienceKernel(spec, code_executor=executor)
    return sim, calls


def test_open_authored_artifact_work_reaches_actual_researcher_inputs_and_edge_removal_stops_it(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    executor = DockerCodeExecutor()
    enabled, calls = world(tmp_path / 'enabled', world_spec(executor.image_id), executor)
    enabled.run()
    records = [e for e in enabled.native_system.events if e.event_type == EVENT]
    assert len(records) == 6
    assert all(e.payload['native_snapshot']['artifact_records'][0]['kind'] == 'open-domain-artifact' for e in records)
    assert all(e.payload['native_snapshot']['artifact_records'][0]['record']['content']['timestamp'] ==
        'SCIENTIFIC_FIELD_NOT_AN_OPERATIONAL_CLOCK_V15' for e in records)
    assert any('WORK_V15_RESPONSE OPEN_WORK_V15' in json.dumps(p) for (ctx, _, _), p in calls if ctx[0] == 'phase1_directions')
    assert sum(ctx[0] == 'native_researcher_work_v15' for (ctx, _, _), _ in calls) == 6
    checkpoint = enabled.native_system.to_dict()
    assert NativeScienceKernel(enabled.native_system.spec, code_executor=executor, checkpoint=checkpoint).to_dict() == checkpoint
    corrupted = deepcopy(checkpoint)
    corrupted['graph_checkpoint']['mechanism_states']['researcher-work']['receipts'].pop()
    with pytest.raises(GraphRuntimeError, match='canonical receipt'):
        NativeScienceKernel(enabled.native_system.spec, checkpoint=corrupted)
    seed()
    disabled, off_calls = world(tmp_path / 'disabled', world_spec(executor.image_id, connected=False), executor)
    disabled.run()
    assert not any(ctx[0] == 'native_researcher_work_v15' for (ctx, _, _), _ in off_calls)
    assert not any('WORK_V15_RESPONSE' in json.dumps(p) for _, p in off_calls)
    from utopia.replay import ArtifactBundle, convert_artifacts, validate_references
    from pathlib import Path
    assert validate_references(convert_artifacts(ArtifactBundle.discover(Path(enabled.output_dir) / 'portable_checkpoint_year_6.json.gz'))) == []
    enabled.llm.response_cache.close(); disabled.llm.response_cache.close()


def test_original_world_work_cold_restart_reuses_completed_requests_and_preserves_native_state(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    executor = DockerCodeExecutor(); spec = world_spec(executor.image_id)
    reference, _ = world(tmp_path / 'reference', spec, executor)
    reference.run()
    expected = science_snapshot(reference)
    seed()
    interrupted, first_calls = world(tmp_path / 'interrupted', spec, executor, stopped=True)
    with pytest.raises(PortableStop): interrupted.run()
    completed_keys = {ctx for (ctx, _, _), _ in first_calls if ctx[0] == 'native_researcher_work_v15'}
    assert len(completed_keys) == 3
    interrupted.llm.response_cache.close()
    resumed, second_calls = world(tmp_path / 'interrupted', spec, executor)
    resumed.run()
    assert science_snapshot(resumed) == expected
    assert resumed.native_system.to_dict() == reference.native_system.to_dict()
    assert not completed_keys & {ctx for (ctx, _, _), _ in second_calls if ctx[0] == 'native_researcher_work_v15'}
    assert sum(ctx[0] == 'native_researcher_work_v15' for (ctx, _, _), _ in second_calls) == 3
    reference.llm.response_cache.close(); resumed.llm.response_cache.close()


def test_repeated_work_caps_each_invocation_and_never_reuses_another_iterations_response(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    executor = DockerCodeExecutor(); spec = world_spec(executor.image_id, repeated=2)
    sim, calls = world(tmp_path / 'repeated', spec, executor)
    sim.run()
    work = [(ctx, p) for (ctx, _, _), p in calls if ctx[0] == 'native_researcher_work_v15']
    assert len(work) == 12 and len({ctx for ctx, _ in work}) == 12
    assert {ctx[2] for ctx, _ in work} == {'researcher-work.iteration-0', 'researcher-work.iteration-1'}
    state = sim.native_system.to_dict()
    assert len(state['graph_checkpoint']['mechanism_states']['researcher-work']['delegate_state']['receipts']) == 12
    NativeScienceKernel(spec, checkpoint=state)
    sim.llm.response_cache.close()
