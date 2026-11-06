"""SCRIPTED six-call diagnostic gates/accounting; never contacts a backend."""
import hashlib
import json
from types import SimpleNamespace

import pytest

from scripts import diagnose_native_json_history_v40 as h
from tests.optimization.test_native_authoring_ir import IMAGE, request
from tests.optimization.test_native_designer_roles_v38 import designer_binding
from tests.optimization.test_native_designer_contract_v16 import Response
from utopia.optimization.native_staged_author_v15 import initial_draft, build_prompt, transition
from utopia.optimization.native_designer_tools_v25 import response_message_from_action
from utopia.utils.data_utils import write_json_atomic


def save(path, value, *, hashed=False, field='content_sha256'):
    if hashed:
        value[field] = h.digest({k: v for k, v in value.items() if k != field})
    write_json_atomic(path, value, sort_keys=True, allow_nan=False)


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    raw = tmp_path / 'raw'; raw.mkdir()
    (raw / 'pilot-writer.lock').write_bytes(b'')
    provider = designer_binding(); provider['image_id'] = IMAGE
    scientist = {**provider, 'model': 'qwen3:8b'}
    save(raw / 'plan.json', {'source_commit': h.ORIGINAL_SOURCE,
        'provider_binding': scientist, 'designer_provider_binding': provider})
    start = {'source_commit': h.ORIGINAL_SOURCE, 'status': 'started', 'started_utc': 'SCRIPTED-start'}
    save(raw / 'writer.started.json', start)
    save(raw / 'writer.ended.json', {**start, 'status': 'exited', 'exit_code': 0, 'ended_utc': 'SCRIPTED-end'})
    bodies = [request(), request()]; bodies[1]['generation'] = 1
    frames = (('g0-step01-eof', h.digest(bodies[0]), 1),
        ('g1-step03-eof', h.digest(bodies[1]), 3), ('g0-step03-write', h.digest(bodies[0]), 3))
    monkeypatch.setattr(h, 'FRAMES', frames)
    backend = {'model': provider['model'], 'model_digest': provider['model_digest'], 'ollama_version': 'SCRIPTED'}
    for identity, generation, step in frames:
        body = bodies[1 if identity.startswith('g1') else 0]
        cell = raw / 'queue' / h.SEARCH / 'authoring' / ('generation-' + generation)
        binding = {'request': body, 'request_sha256': generation, 'provider_binding': provider,
            'settings': {'max_steps': 8, 'max_tokens': 8192}}
        save(cell / 'request.json', binding, hashed=True, field='binding_sha256')
        state, steps = initial_draft(body), []
        for index in range(step):
            action = {'tool': 'inspect', 'path': '/metadata'}
            state, receipt = transition(state, action, body,
                binding_sha256=binding['binding_sha256'], provider_binding=provider)
            steps.append({'step': index, 'status': 'applied', 'model_reply': {'output': action},
                'transition': receipt, 'errors': []})
        prompt = build_prompt(body, state, steps, image_id=IMAGE,
            binding_sha256=binding['binding_sha256'], settings={'max_steps': 8})
        started = {'binding_sha256': binding['binding_sha256'], 'prompt': prompt,
            'prompt_sha256': h.digest(prompt), 'response_schema': h.ACTION_SCHEMA, 'step': step}
        path = cell / f'step-{step:02d}.started.json'; save(path, started)
        messages = h.build_conversation(prompt, h.call_task(step, 8), native_tools=True)
        payload = h.designer_payload('staged-v15', provider, messages,
            ('native-staged-designer-v15', binding['binding_sha256'], step),
            max_tokens=8192, temperature=.6, role='editor')
        transport = {'request_payload': payload, 'preflight': {'backend': backend},
            'http_timeout_seconds': [10, 900], **h.wire_record(payload, h.ACTION_SCHEMA)}
        if identity.endswith('eof'):
            transport.update(http_status=500, raw_http_response='{"error":"EOF"}')
        else:
            transport.update(http_status=200, raw_http_response='SCRIPTED historical body remains opaque')
        save(cell / f'step-{step:02d}.completed.json', {
            'status': 'transport-error' if identity.endswith('eof') else 'applied',
            'started_file_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'model_reply': {'output': None if identity.endswith('eof') else {'tool': 'write_file'},
                'transport': transport}}, hashed=True)
    required = ['utopia/SCRIPTED.py', 'scripts/analyze_native_staged_search_v15.py',
        'scripts/run_native_designer_roles_v38.py', 'scripts/run_native_staged_search_v15.py',
        'research/protocols/campaigns/native-execution-readiness-v39-a1.md']
    monkeypatch.setattr(h, 'subprocess', SimpleNamespace(check_output=lambda *a, **k: 'utopia/SCRIPTED.py\n'))
    monkeypatch.setattr(h, 'git_hashes', lambda names: {name: '0' * 64 for name in names})
    monkeypatch.setattr(h, 'runtime_binding', lambda: {'SCRIPTED-runtime': '1' * 64})
    monkeypatch.setattr(h, 'pinned_revision', lambda _: 'a' * 40)
    inventory = h._inventory(raw)
    audit = {'schema': h.AUDIT_SCHEMA, 'classification': h.ROLE_CLASSIFICATION,
        'source_commit': h.ORIGINAL_SOURCE, 'engineering_revision': 'v39-a1',
        'budget_terminal': True, 'queue_terminal': True, 'planned_native_slots': 8, 'consumed_native_slots': 8,
        'status': 'complete', 'audit': {'raw_root': str(raw), 'new_model_calls': 0, 'new_container_executions': 0,
            'exact_raw_tools_draft_source_definition_replayed': True, 'own_history_loss_and_all_ties_replayed': True,
            'raw_input_sha256s': inventory, 'raw_inventory_sha256': h.digest(inventory),
            'raw_files_verified_unchanged': len(inventory), 'analysis_source_sha256': '0' * 64,
            'source_proofs': {'status': 'verified-exact-staged-runtime-driver-helper-source-blobs',
                'files': {name: {'actual_source_sha256': '0' * 64, 'analysis_source_sha256': '0' * 64}
                    for name in required}}}}
    audits = [tmp_path / 'audit-one.json', tmp_path / 'audit-two.json']
    for path in audits:
        save(path, audit, hashed=True)
    return {'raw': raw, 'audits': audits, 'writer_ended': raw / 'writer.ended.json',
        'provider': provider, 'source_commit': 'a' * 40}


def plan(inputs):
    values = dict(inputs); raw = values.pop('raw')
    return h.build_plan(raw, **values)


class Session:
    def __init__(self, provider, output, outcomes=None):
        self.provider, self.output = provider, output
        self.outcomes = outcomes or ['success'] * 6
        self.posts, self.gets = [], []

    def get(self, url, **kwargs):
        assert url.startswith('http://127.0.0.1:11434/api/')
        self.gets.append(url)
        return Response({'version': 'SCRIPTED'} if url.endswith('/version') else
            {'models': [{'name': self.provider['model'], 'digest': self.provider['model_digest']}]})

    def post(self, url, **kwargs):
        index = len(self.posts)
        assert (self.output / f'call-{index:02d}.started.json').is_file()
        assert kwargs['timeout'] == (10, 900)
        payload = json.loads(kwargs['data']); self.posts.append(payload)
        outcome = self.outcomes[index]
        if outcome == 'timeout':
            raise TimeoutError('SCRIPTED unknown response and tokens')
        if outcome == 'interrupt':
            raise KeyboardInterrupt('SCRIPTED unknown interrupted response')
        if outcome == 'eof':
            response = Response({'error': 'EOF'}); response.status_code = 500
            def fail():
                raise RuntimeError('SCRIPTED HTTP500')
            response.raise_for_status = fail
            return response
        action = {'tool': 'read_file', 'filename': 'system.json'}
        if outcome == 'schema':
            action['filename'] = []
        body = {'model': self.provider['model'], 'message': response_message_from_action(action),
            'done': outcome != 'partial', 'done_reason': 'length' if outcome == 'partial' else 'stop',
            'prompt_eval_count': 100, 'eval_count': 20}
        if outcome == 'foreign':
            body['model'] = 'wrong'
        return Response(body)


def test_fixed_balanced_pairs_reconstruct_original_seed_options_and_preserve_archives(inputs, tmp_path, monkeypatch):
    value = plan(inputs)
    assert value['maximum_POSTs'] == 6 and len(value['frames']) == 3
    assert [c['conversation_profile'] for c in value['calls']] == [h.LEGACY_HISTORY, h.PLAIN_JSON_HISTORY] * 3
    for frame in value['frames']:
        old, new = frame['payloads'][h.LEGACY_HISTORY], frame['payloads'][h.PLAIN_JSON_HISTORY]
        assert {k: v for k, v in old.items() if k != 'messages'} == {k: v for k, v in new.items() if k != 'messages'}
    def forbidden(*a, **k):
        raise AssertionError('no interpreter, generated code or Docker execution')
    monkeypatch.setattr('utopia.optimization.native_staged_author_v15.transition', forbidden)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.__init__', forbidden)
    output = tmp_path / 'diagnostic'; session = Session(inputs['provider'], output)
    before = h._inventory(inputs['raw'])
    with h.ended_writer_lock(inputs['raw']):
        summary = h.run(value, output, session=session)
    assert summary['recorded_attempts'] == summary['technical_successes'] == len(session.posts) == 6
    assert len(session.gets) == 14 and summary['actions_applied'] == summary['native_worlds'] == 0
    assert all(row['recorded_receipts'] == 3 for row in summary['profiles'].values())
    assert before == h._inventory(inputs['raw']) and summary['original_files_unchanged']
    for index, call in enumerate(value['calls']):
        assert session.posts[index] == value['frames'][call['frame']]['payloads'][call['conversation_profile']]
    with pytest.raises(FileExistsError):
        h.run(value, output, session=session)
    assert len(session.posts) == 6


@pytest.mark.parametrize('mutation', ['unfinished', 'different-audits', 'not-terminal', 'wrong-source',
    'source-proof', 'raw-change', 'legacy-wire', 'same-audit'])
def test_actual_run_gates_reject_incomplete_or_changed_original_evidence(inputs, mutation):
    if mutation == 'unfinished':
        inputs['writer_ended'].unlink()
    elif mutation == 'same-audit':
        inputs['audits'][1] = inputs['audits'][0]
    elif mutation in ('raw-change', 'legacy-wire'):
        raw_file = next(inputs['raw'].glob('queue/*/authoring/*/step-*.completed.json'))
        value = h.read(raw_file)
        value['model_reply']['transport']['request_wire_utf8'] += ' '
        save(raw_file, value, hashed=True)
        if mutation == 'legacy-wire':
            for path in inputs['audits']:
                audit = h.read(path); inventory = h._inventory(inputs['raw'])
                audit['audit'].update(raw_input_sha256s=inventory, raw_inventory_sha256=h.digest(inventory))
                save(path, audit, hashed=True)
    else:
        for index, path in enumerate(inputs['audits']):
            value = h.read(path)
            if mutation == 'different-audits' and index == 0:
                continue
            if mutation == 'not-terminal':
                value['budget_terminal'] = False
            elif mutation == 'wrong-source':
                value['source_commit'] = 'b' * 40
            elif mutation == 'source-proof':
                value['audit']['analysis_source_sha256'] = 'c' * 64
            else:
                value['status'] = 'budget-complete-with-failures'
            save(path, value, hashed=True)
    with pytest.raises((ValueError, FileNotFoundError)):
        plan(inputs)


def test_errors_partial_envelopes_unknown_costs_and_foreign_models_are_separate_charged_calls(inputs, tmp_path):
    value = plan(inputs); output = tmp_path / 'failures'
    session = Session(inputs['provider'], output, ['eof', 'timeout', 'partial', 'schema', 'foreign', 'success'])
    summary = h.run(value, output, session=session)
    rows = [h.read(output / f'call-{index:02d}.completed.json') for index in range(6)]
    assert len(session.posts) == summary['recorded_attempts'] == 6
    assert summary['technical_successes'] == 1
    assert rows[0]['transport']['raw_http_response'] == json.dumps({'error': 'EOF'})
    assert rows[0]['costs'] == rows[1]['costs'] == {'prompt_eval_count': None, 'eval_count': None}
    assert rows[2]['complete_envelope'] is False and not rows[2]['strict_action_parse']
    assert rows[2]['costs']['eval_count'] == 20
    assert rows[3]['strict_action_parse'] and not rows[3]['action_schema_valid']
    assert rows[4]['action_schema_valid'] and not rows[4]['provider_matches']
    assert all(not row['action_applied'] for row in rows)


def test_interrupt_consumes_intent_and_cannot_resume_or_redispatch(inputs, tmp_path):
    output = tmp_path / 'interrupt'; session = Session(inputs['provider'], output, ['interrupt'])
    value = plan(inputs)
    with pytest.raises(KeyboardInterrupt):
        h.run(value, output, session=session)
    assert len(session.posts) == 1
    row = h.read(output / 'call-00.completed.json')
    assert row['interrupted'] and row['costs']['eval_count'] is None
    with pytest.raises(FileExistsError):
        h.run(value, output, session=session)
    assert len(session.posts) == 1


@pytest.mark.parametrize('mutation', ['backend', 'source', 'budget', 'order'])
def test_bound_identity_and_six_call_budget_fail_before_post(inputs, tmp_path, monkeypatch, mutation):
    value = plan(inputs); output = tmp_path / mutation
    session = Session(inputs['provider'], output)
    if mutation == 'backend':
        value['backend']['ollama_version'] = 'wrong'
    elif mutation == 'source':
        monkeypatch.setattr(h, 'pinned_revision', lambda _: 'b' * 40)
    elif mutation == 'budget':
        value['maximum_POSTs'] = 7
    else:
        value['calls'].reverse()
    value['content_sha256'] = h.digest({k: v for k, v in value.items() if k != 'content_sha256'})
    with pytest.raises(ValueError):
        h.run(value, output, session=session)
    assert not session.posts


def test_cli_requires_explicit_actual_run_authorization_before_any_backend_access(monkeypatch):
    monkeypatch.setattr(h.sys, 'argv', ['diagnose', '--raw', 'unused', '--audit', 'one', '--audit', 'two',
        '--writer-ended', 'ended', '--provider-config', 'provider', '--output', 'new'])
    with pytest.raises(SystemExit) as error:
        h.main()
    assert error.value.code == 2


def test_read_only_writer_lock_refuses_a_running_original_writer(inputs):
    path = inputs['raw'] / 'pilot-writer.lock'
    before = path.read_bytes()
    with path.open('rb') as writer:
        h.fcntl.flock(writer, h.fcntl.LOCK_EX | h.fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            with h.ended_writer_lock(inputs['raw']):
                pytest.fail('diagnostic must not share a live writer')
    assert path.read_bytes() == before
