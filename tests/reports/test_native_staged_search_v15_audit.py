"""SCRIPTED author/queue/audit contracts; no actual LLM, Docker or world call."""
from copy import deepcopy
import json
import sqlite3

import pytest

from scripts import analyze_native_staged_search_v15 as audit
from tests.optimization.test_native_search_v14 import BINDING, REVISION, FailedFactory
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_search_v15 import NativeStagedSearchQueue
from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator
from utopia.runtime.checkpointing import PortableStop
from utopia.system.native_kernel import legacy_world_system
from utopia.utils.data_utils import write_json_atomic


def save(path, value):
    write_json_atomic(path, value, sort_keys=True, allow_nan=False)


def rehash(path, change, field='content_sha256'):
    value = audit.read(path); change(value)
    value[field] = audit.digest({k: v for k, v in value.items() if k != field})
    save(path, value)


def fixture(root, *, generation_fails=False, unknown=False, run_jobs=True):
    plan = audit.build_plan(source_commit=REVISION, initial_system=legacy_world_system().to_dict(),
        provider_binding=BINDING, runtime_seed_binding={'python_hash_seed_environment': '42', 'python_hash_probe': 123})
    plan['classification'] = audit.FIXTURE
    save(root / 'plan.json', plan); save(root / 'operator-config.json', {'provider_binding': BINDING})
    queue = NativeStagedSearchQueue(root / 'queue', provider_binding=BINDING)
    searches = {}
    for entry in plan['runs']:
        queued = queue.submit(entry['request'], confirmed_request_sha256=audit.digest(entry['request']), source_commit=REVISION)
        searches[entry['id']] = queued['search_id']
    save(root / 'searches.json', searches)
    class Model:
        calls = 0
        def generate(self, **kwargs):
            self.calls += 1
            if unknown and self.calls == 1:
                raise KeyboardInterrupt('SCRIPTED unknown response boundary')
            action = ({'tool': 'edit', 'operations': [{'op': 'replace', 'path': '/absent', 'value': 1}]}
                if generation_fails else {'tool': 'finish', 'rationale': 'SCRIPTED explicit parent retention, not scientific invention'})
            return action, [{'role': 'assistant', 'content': json.dumps(action)}]
    model = Model()
    def author(directory, request, provider):
        return StagedVocabularyGenerator(model, directory / 'authoring', image_id=provider['image_id'],
            provider_binding=provider, max_steps=request['designer']['max_steps'], max_tokens=request['designer']['max_tokens'])
    if run_jobs:
        if unknown:
            with pytest.raises(KeyboardInterrupt):
                queue.run_one(lambda *a: FailedFactory(), generator_builder=author, source_commit=REVISION)
        for _ in range(2):
            queue.run_one(lambda *a: FailedFactory(), generator_builder=author, source_commit=REVISION)
    runs = {name: queue.get(identity) for name, identity in searches.items()}
    progress = {'schema': audit.RAW_SCHEMA + '.progress', 'classification': audit.FIXTURE,
        'source_commit': REVISION, 'plan_sha256': audit.digest(plan), 'runs': runs,
        'terminal': all(r['status'] in ('complete', 'failed') for r in runs.values()),
        'scheduled_native_slots': 4, 'consumed_native_slots': sum(r['budget']['consumed'] for r in runs.values())}
    progress['content_sha256'] = audit.digest(progress)
    save(root / 'progress.json', progress)
    return queue, plan, model


@pytest.mark.parametrize('failed,unknown', [(False, False), (True, False), (False, True)])
def test_all_null_paths_distinguish_generation_native_failures_and_interrupted_unknown(tmp_path, failed, unknown):
    _, _, model = fixture(tmp_path, generation_fails=failed, unknown=unknown)
    before = audit._inventory(tmp_path)
    first = audit.analyze(tmp_path, expected_source=REVISION)
    assert first == audit.analyze(tmp_path, expected_source=REVISION)
    assert before == audit._inventory(tmp_path)
    assert first['status'] == 'budget-complete-with-failures' and first['budget_terminal']
    assert first['consumed_native_slots'] == first['technical_failures'] == 4
    assert first['physical_native_worlds'] == first['physical_researcher_responses'] == 0
    assert first['designer_costs']['generations'] == 4
    assert first['designer_costs']['dispatch_intents'] == model.calls
    assert first['designer_costs']['interrupted_response_unknown'] == int(unknown)
    assert first['designer_costs']['known_designer_responses'] == model.calls - int(unknown)
    assert first['designer_costs']['valid_finished_generations'] == (0 if failed else 4)
    assert first['claims']['scripted_HTTP_only'] and not first['claims']['actual_local_Qwen_automatic_loop']
    assert not first['claims']['operational_two_generation_native_feedback_arm']
    compact = audit.compact_summary(first)
    assert compact['exact_full_audit_content_sha256'] == first['content_sha256']
    assert compact['designer_costs'] == first['designer_costs']
    assert len(compact['runs']['throughput']['generations']) == 2
    assert 'started_records' not in compact['runs']['throughput']['generations'][0]
    original = first['runs']['throughput']['observations'][0]['observation'] or {}
    assert compact['runs']['throughput']['observations'][0]['original_observation_status'] == original.get('status')
    assert compact['runs']['throughput']['observations'][0]['original_observation_loss'] == original.get('loss')
    change = compact['runs']['throughput']['generations'][0]['authoring_change']
    assert change['valid_explicit_finish'] == (not failed)
    if not failed:
        assert change['explicit_exact_parent_retention'] and change['base_patch_null']
        assert change['authored_operation_count'] == 0 and not change['exact_document_changed']
    second_prompt = first['runs']['throughput']['designer']['proofs'][1]['started_records'][0]['prompt']
    assert json.loads(second_prompt)['own_history']['all_observations'] or failed


def test_empty_queued_revision_remains_incomplete_without_charging_trials(tmp_path):
    fixture(tmp_path, run_jobs=False)
    first = audit.analyze(tmp_path, expected_source=REVISION, require_complete=False)
    assert first['status'] == 'in-progress' and first['consumed_native_slots'] == 0
    assert first['designer_costs']['dispatch_intents'] == 0
    with pytest.raises(ValueError, match='incomplete'):
        audit.analyze(tmp_path, expected_source=REVISION)


@pytest.mark.parametrize('with_code', [False, True])
def test_original_native_success_paths_join_source_world_actual_scientist_replies_and_next_own_loss(
        tmp_path, fixed_corpus, monkeypatch, with_code):
    from pathlib import Path
    from tests.runtime.test_portable_checkpoint_integration import BINDING as physical_binding, FakeHTTPModel, SmallRealSimulation, seed
    from utopia.models.response_cache import CompletedResponseCache
    from utopia.optimization.native_factory import record_native_http
    from utopia.optimization.native_code_trace import RecordingCodeExecutor
    from utopia.system.code_mechanisms import CODE_SCHEMA, DockerCodeExecutor
    from utopia.system.native_kernel import NativeScienceKernel
    executor = DockerCodeExecutor() if with_code else None
    if with_code:
        monkeypatch.setitem(BINDING, 'image_id', executor.image_id)
    queue, plan, _ = fixture(tmp_path, run_jobs=False)
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    monkeypatch.setitem(physical_binding, 'model', BINDING['model'])
    monkeypatch.setitem(physical_binding, 'model_revision', BINDING['model_digest'])
    monkeypatch.setitem(physical_binding, 'corpus_sha256', BINDING['corpus_sha256'])
    native_calls, scientist_calls, prompts = [], [], []
    class Factory(FailedFactory):
        def __init__(self, root, request):
            super().__init__(); self.root, self.request = root, request
        def __call__(self, candidate, world_seed, run_id):
            native_calls.append(run_id); cell = self.root / 'worlds' / run_id; seed()
            monkeypatch.setitem(physical_binding, 'cell', candidate.fingerprint)
            monkeypatch.setitem(physical_binding, 'science_config', {'source_commit': REVISION, 'years': 2,
                'experiment': {'request_sha256': audit.digest(self.request), 'loss_spec': self.request['loss_spec']}})
            model = FakeHTTPModel(cell, scientist_calls)
            unused_empty_cache = model.response_cache.path
            model.response_cache.close(); unused_empty_cache.unlink()
            model.response_cache = CompletedResponseCache(cell / 'replies/responses.sqlite', binding=physical_binding)
            sim = SmallRealSimulation(cell, model)
            recording = RecordingCodeExecutor(executor, cell / 'code-contexts.jsonl', binding={
                'source_commit': REVISION, 'system_fingerprint': candidate.fingerprint, 'run_id': run_id}) if with_code else None
            sim.native_system = NativeScienceKernel(candidate, code_executor=recording); sim.num_years = 2
            sim.enable_portable_checkpoints(physical_binding)
            record_native_http(model, sim, cell / 'wire-requests.jsonl')
            save(cell / 'system.json', candidate.to_dict())
            return sim
    class Feedback:
        def generate(self, **kwargs):
            prompt = json.loads(kwargs['prompt']); prompts.append(prompt)
            if not prompt['previous_steps']:
                action = {'tool': 'edit', 'operations': [{'op': 'add', 'path': '/metadata/scripted-feedback-proof',
                    'value': {'generation': prompt['generation'], 'own_prior_losses': [
                        row['loss'] for row in prompt['own_history']['all_observations']]}}]}
                if with_code:
                    identity = 'scripted-code-generation-' + str(prompt['generation'])
                    node = {'mechanism_id': identity, 'family': 'custom', 'implementation': 'code.python.v1',
                        'version': 1, 'inputs': [], 'outputs': [], 'parameters': {'runtime_image_id': executor.image_id,
                            'code_artifact': {'schema': CODE_SCHEMA, 'label': 'SCRIPTED arbitrary source audit QA, not live invention',
                                'source': 'def step(context):\n    return {"outputs": {}, "state": {"calls": context["state"].get("calls", 0) + 1, "generation": '
                                    + str(prompt['generation']) + '}}\n',
                                'inputs': {}, 'outputs': {}, 'state_schema': {'type': 'object'}}}}
                    action['operations'] += [{'op': 'add', 'path': '/mechanisms/-', 'value': node},
                        {'op': 'add', 'path': '/schedules/-', 'value': {'mechanism_id': identity, 'phase': 15, 'trigger': 'annual'}}]
            else:
                action = {'tool': 'finish', 'rationale': 'SCRIPTED source/world/own-loss audit integration, not invention'}
            return action, [{'role': 'assistant', 'content': json.dumps(action)}]
    def author(root, request, provider):
        return StagedVocabularyGenerator(Feedback(), root / 'authoring', image_id=provider['image_id'],
            provider_binding=provider, max_steps=request['designer']['max_steps'], max_tokens=request['designer']['max_tokens'])
    for _ in range(2):
        outcome = queue.run_one(lambda root, request: Factory(root, request), generator_builder=author, source_commit=REVISION)
        assert outcome['status'] == 'complete' and not outcome['errors']
    searches = audit.read(tmp_path / 'searches.json')
    runs = {name: queue.get(identity) for name, identity in searches.items()}
    progress = {'schema': audit.RAW_SCHEMA + '.progress', 'classification': audit.FIXTURE,
        'source_commit': REVISION, 'plan_sha256': audit.digest(plan), 'runs': runs,
        'terminal': True, 'scheduled_native_slots': 4, 'consumed_native_slots': 4}
    progress['content_sha256'] = audit.digest(progress); save(tmp_path / 'progress.json', progress)
    before = audit._inventory(tmp_path)
    result = audit.analyze(tmp_path, expected_source=REVISION)
    assert result == audit.analyze(tmp_path, expected_source=REVISION)
    assert before == audit._inventory(tmp_path)
    assert result['status'] == 'complete' and result['physical_native_worlds'] == 4
    assert result['physical_researcher_responses'] == len(scientist_calls) > 0
    assert result['claims']['operational_two_generation_native_feedback_arm']
    assert not result['claims']['actual_local_Qwen_automatic_loop']
    assert len(native_calls) == len(set(native_calls)) == 4
    assert result['designer_costs']['dispatch_intents'] == 8
    assert bool(result['completed_code_executions']) == with_code
    compact = audit.compact_summary(result)
    for name, run in result['runs'].items():
        proof = run['designer']['proofs'][1]
        prompt = json.loads(proof['started_records'][0]['prompt'])
        assert prompt['own_history']['all_observations'][0]['loss'] == run['observations'][0]['loss']
        final = run['observations'][1]['system']['metadata']['scripted-feedback-proof']
        assert final['generation'] == 1 and final['own_prior_losses'] == [run['observations'][0]['loss']]
        assert all(row['checkpoint_sha256'] and row['physical_proof'] for row in run['observations'])
        change = compact['runs'][name]['generations'][0]['authoring_change']
        assert change['exact_document_changed'] and not change['explicit_exact_parent_retention']
        assert change['graph_contract_excluding_metadata_changed'] == with_code
        assert change['authored_operation_count'] == (3 if with_code else 1)
        assert compact['runs'][name]['generations'][1]['own_scalar_outcomes_received'][0]['loss'] == run['observations'][0]['loss']
        assert compact['runs'][name]['observations'][0]['native_A_Q_R']['A']['status'] == 'measured'
        assert bool(compact['runs'][name]['observations'][0]['native_physical_counts']['recorded_code_executions']) == with_code


def transport_fixture():
    binding = {'provider_binding': BINDING, 'binding_sha256': 'b' * 64, 'settings': {'max_tokens': 2048}}
    started = {'prompt': json.dumps({'000_current_turn': {},
        'fixture_scope': 'SCRIPTED transport checker only, not an actual model request'}), 'step': 0}
    action = {'tool': 'finish', 'rationale': 'SCRIPTED'}
    body = {'model': 'qwen3:8b', 'done': True, 'done_reason': 'stop',
        'message': {'role': 'assistant', 'content': json.dumps(action)}}
    payload = {'model': 'qwen3:8b',
        'messages': audit.staged_author.build_conversation(started['prompt'], audit.staged_author.SYSTEM_PROMPT),
        'format': audit.ACTION_SCHEMA, 'think': False, 'stream': False,
        'options': {'temperature': .2, 'num_predict': 2048, 'num_ctx': 32768,
            'seed': int(audit.digest(('native-staged-designer-v15', binding['binding_sha256'], 0))[:8], 16) % (2**31)}}
    step = {'status': 'finished', 'model_reply': {'messages': [{'role': 'assistant', 'content': body['message']['content']}],
        'output': action, 'transport': {'request_payload': payload, 'response_payload': body,
            'raw_http_response': json.dumps(body), 'http_status': 200, 'model_digest': BINDING['model_digest'],
            'endpoint': 'http://127.0.0.1:11434/api/chat', 'network_retries': 0,
            'conversation_schema': audit.staged_author.PROTOCOL + '.conversation.v1',
            'source_prompt_sha256': audit.digest(started['prompt'])}}}
    return step, started, binding


def test_exact_original_post_and_http_body_are_checked_without_dispatching():
    step, started, binding = transport_fixture()
    assert audit._transport(step, started, binding, audit.CLASSIFICATION) == {
        'recorded_POST_attempt': True, 'known_HTTP_response': True, 'known_designer_response': True}


@pytest.mark.parametrize('mutation', ['no-transport', 'seed', 'model', 'prompt', 'schema', 'raw-body',
    'assistant', 'truncated', 'not-done', 'foreign-response-model'])
def test_synthetic_transport_proofs_reject_wrong_provider_prompt_or_truncated_accepted_action(mutation):
    step, started, binding = transport_fixture(); transport = step['model_reply']['transport']
    if mutation == 'no-transport': step['model_reply']['transport'] = {}
    elif mutation == 'seed': transport['request_payload']['options']['seed'] += 1
    elif mutation == 'model': transport['request_payload']['model'] = 'a-different-model'
    elif mutation == 'prompt': transport['request_payload']['messages'][-1]['content'] = 'different prompt'
    elif mutation == 'schema': transport['request_payload']['format'] = {'type': 'object'}
    elif mutation == 'raw-body': transport['raw_http_response'] = '{}'
    elif mutation == 'assistant': step['model_reply']['messages'][-1]['content'] = '{}'
    else:
        if mutation == 'truncated': transport['response_payload']['done_reason'] = 'length'
        elif mutation == 'not-done': transport['response_payload']['done'] = False
        else: transport['response_payload']['model'] = 'foreign-model'
        transport['raw_http_response'] = json.dumps(transport['response_payload'])
    with pytest.raises(ValueError):
        audit._transport(step, started, binding, audit.CLASSIFICATION)


@pytest.mark.parametrize('mutation', ['prompt', 'definition', 'source-protocol', 'loss', 'budget',
    'extra-queue', 'shared-search', 'extra-world', 'extra-author', 'extra-system',
    'trace', 'current', 'known-cost', 'negative-cost'])
def test_rehashed_corruption_or_unaccounted_cost_is_not_accepted(tmp_path, mutation):
    fixture(tmp_path)
    journal = next((tmp_path / 'queue').glob('search-*/authoring/generation-*'))
    if mutation == 'prompt':
        path = journal / 'step-00.started.json'; value = audit.read(path)
        value['prompt'] += ' hidden other-arm data'; value['prompt_sha256'] = audit.digest(value['prompt']); save(path, value)
    elif mutation == 'definition':
        rehash(journal / 'response.json', lambda v: v['definition']['provenance'].update(kind='manual replacement'))
    elif mutation == 'source-protocol':
        rehash(journal / 'request.json', lambda v: v['authoring_protocol'].update(source_execution_on_host=True), field='binding_sha256')
    elif mutation in {'loss', 'budget'}:
        plan = audit.read(tmp_path / 'plan.json')
        if mutation == 'loss': plan['runs'][0]['request']['loss_spec']['per_run']['terms'][0]['coefficient'] = -2.0
        else: plan['budget']['maximum_generation_POSTs'] = 65
        save(tmp_path / 'plan.json', plan)
    elif mutation == 'extra-queue':
        with sqlite3.connect(tmp_path / 'queue/native-search-jobs-v15.sqlite') as db:
            row = db.execute('SELECT * FROM searches LIMIT 1').fetchone()
            db.execute('INSERT INTO searches VALUES (?,?,?,?,?,?,?)', ('search-' + 'f' * 32, row[1], 'f' * 64, *row[3:]))
    elif mutation == 'shared-search':
        searches = audit.read(tmp_path / 'searches.json'); searches['efficiency'] = searches['throughput']; save(tmp_path / 'searches.json', searches)
    elif mutation == 'extra-world':
        save(tmp_path / 'queue/undeclared/worlds/fake/replies/responses.sqlite', {'not': 'a real cache'})
    elif mutation == 'extra-author':
        save(tmp_path / 'outside/generation-undeclared/request.json', {'not': 'an accounted author request'})
    elif mutation == 'extra-system':
        save(tmp_path / 'outside/worlds/undeclared/system.json', {'not': 'an accounted native source'})
    elif mutation in {'trace', 'current'}:
        def change(v):
            if mutation == 'trace': v['runs']['throughput']['authoring_trace']['generations'][0]['status'] = 'invented-success'
            else: v['runs']['throughput']['current'] = {'invented_loss': -1000}
        rehash(tmp_path / 'progress.json', change)
    else:
        path = journal / 'step-00.completed.json'
        def change(v):
            if mutation == 'negative-cost': v['model_call_seconds'] = -1.0
            else: v['model_reply']['transport'] = {'elapsed_seconds': float('nan')}
        if mutation == 'known-cost':
            value = audit.read(path); change(value)
            # Non-finite JSON is deliberately malformed external evidence.
            path.write_text(json.dumps(value))
        else: rehash(path, change)
    with pytest.raises((ValueError, KeyError)):
        audit.analyze(tmp_path, expected_source=REVISION)
