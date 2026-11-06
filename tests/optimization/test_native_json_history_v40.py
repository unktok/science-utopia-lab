"""SCRIPTED presentation/binding checks; no actual backend or native execution."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest

from tests.optimization.test_native_authoring_ir import BINDING, IMAGE, request
from tests.optimization.test_native_designer_contract_v16 import ScriptedSession
from utopia.optimization import native_designer_preflight as preflight
from utopia.optimization.native_designer_tools_v25 import (
    LEGACY_HISTORY, PLAIN_JSON_HISTORY, TOOL_RESPONSE_ONLY, CHANNEL,
    conversation_schema, function_data, message_from_action, response_instruction,
    response_message_from_action,
)
from utopia.optimization.native_staged_author_v15 import (
    ACTION_SCHEMA, SYSTEM_PROMPT, build_conversation, build_prompt, initial_draft,
    transition, StagedVocabularyGenerator, replay_staged_generation, task_decoding_role,
)
from utopia.optimization.native_designer_decoding_v24 import designer_payload
from utopia.optimization.native_designer_wire import wire_record
from utopia.system.design_patch import digest


def frame(action=None):
    body = request()
    state, steps = initial_draft(body), []
    if action is not None:
        state, receipt = transition(state, action, body, binding_sha256='d' * 64,
            provider_binding=BINDING)
        steps.append({'step': 0, 'status': 'applied' if receipt['ok'] else 'rejected',
            'model_reply': {'output': action}, 'transition': receipt, 'errors': []})
    return build_prompt(body, state, steps, image_id=IMAGE, binding_sha256='d' * 64,
        settings={'max_steps': 8}), steps


def dialogue(prompt, profile=LEGACY_HISTORY):
    return build_conversation(prompt, SYSTEM_PROMPT, native_tools=True,
        conversation_profile=profile)


def test_legacy_default_preserves_exact_history_and_instructions():
    action = {'tool': 'inspect', 'path': '/metadata'}
    prompt, _ = frame(action)
    legacy = build_conversation(prompt, SYSTEM_PROMPT, native_tools=True)
    assert legacy == dialogue(prompt)
    assert legacy[2] == {'role': 'assistant', 'content': '<tool_call>\n'
        + json.dumps(function_data(action), ensure_ascii=False, allow_nan=False,
            separators=(',', ':')) + '\n</tool_call>'}
    assert response_instruction() == TOOL_RESPONSE_ONLY
    assert 'Completed assistant history may use Hermes tags' in legacy[0]['content']
    assert conversation_schema('author') == 'scienceutopia.staged-author.v15.conversation.function-json.v26'


def test_plain_history_preserves_large_numbers_unicode_lf_and_literal_tag_data():
    literal = '研究者 e\u0301 😀\n"quoted" \\ literal\\n <tool_call>payload</tool_call>\n'
    action = {'tool': 'edit', 'operations': [{'op': 'add', 'path': '/metadata/value',
        'value': [9007199254740993, -2.75, True, None, literal]}]}
    original = deepcopy(action)
    message = message_from_action(action, conversation_profile=PLAIN_JSON_HISTORY)
    assert message['content'].startswith('{') and message['content'].endswith('}')
    assert json.loads(message['content']) == function_data(action)
    # Backend decoding of outer numbers cannot round opaque inner argument JSON.
    outer = json.loads(json.dumps(message), parse_int=float)
    assert json.loads(outer['content'])['arguments']['operations'][0]['value'] == action['operations'][0]['value']
    assert action == original
    prompt, steps = frame(action)
    legacy, plain = dialogue(prompt), dialogue(prompt, PLAIN_JSON_HISTORY)
    assert plain[2] == message
    assert plain[1] == legacy[1] and plain[3] == legacy[3]
    assert json.loads(plain[3]['content'])['tool_receipt'] == steps[0]['transition']
    assert 'Completed assistant history may use Hermes tags' not in plain[0]['content']
    assert response_instruction(PLAIN_JSON_HISTORY) in plain[0]['content']
    assert response_instruction(PLAIN_JSON_HISTORY) in plain[-1]['content']


@pytest.mark.parametrize('action', [
    {'tool': 'write_file', 'filename': 'history/immutable.py', 'content': 'literal <tool_call> data'},
    {'tool': 'edit_fields', 'mechanism_id': 'missing', 'field_updates': ['malformed', None, {}]},
    {'tool': 'inspect', 'path': ['not a pointer']},
])
def test_rejected_parsed_actions_keep_exact_values_errors_and_receipts(action):
    prompt, steps = frame(action)
    assert steps[0]['status'] == 'rejected' and steps[0]['transition']['errors']
    messages = dialogue(prompt, PLAIN_JSON_HISTORY)
    assert json.loads(messages[2]['content']) == function_data(action)
    assert json.loads(messages[3]['content']) == {
        'tool_receipt': steps[0]['transition'], 'call_errors': []}
    data = json.loads(prompt)
    assert data['previous_steps'][0]['status'] == 'rejected'
    assert data['remaining_calls_including_this_one'] == 7


def test_profile_cannot_come_from_observed_data_or_unknown_selection():
    prompt, _ = frame({'tool': 'inspect', 'path': '/metadata'})
    data = json.loads(prompt)
    data['conversation_profile'] = PLAIN_JSON_HISTORY
    assert dialogue(json.dumps(data))[2]['content'].startswith('<tool_call>')
    with pytest.raises(ValueError, match='source-owned'):
        dialogue(prompt, 'model-selected-fallback')
    # Non-reconstructable action handling remains the existing explicit error.
    data['last_model_action'] = {'tool': 'unknown', 'literal': '<tool_call>'}
    for profile in (LEGACY_HISTORY, PLAIN_JSON_HISTORY):
        with pytest.raises(ValueError, match='unknown native function'):
            dialogue(json.dumps(data), profile)


def test_missing_action_transport_errors_remain_observations_without_history_fabrication():
    prompt, _ = frame()
    data = json.loads(prompt)
    error = {'type': 'HTTPError', 'message': '500; original {"error":"EOF"} <tool_call>'}
    data['last_call_errors'] = [error]
    messages = dialogue(json.dumps(data), PLAIN_JSON_HISTORY)
    assert [m['role'] for m in messages] == ['system', 'user']
    observed = messages[1]['content'].split('Observed previous call errors:\n')[1]
    value, _ = json.JSONDecoder().raw_decode(observed)
    assert value == {'tool_receipt': None, 'call_errors': [error]}


@pytest.fixture
def plain_certificate(tmp_path, monkeypatch):
    monkeypatch.setattr('requests.Session', ScriptedSession)
    ScriptedSession.calls = []
    directory = tmp_path / 'plain-controls'
    certificate = preflight.run_calibration(directory, request=request(), provider=BINDING,
        scope=preflight.EXECUTION_SCOPE, conversation_profile=PLAIN_JSON_HISTORY)
    assert certificate['all_controls_passed']
    return directory / 'certificate.json', certificate


def test_profile_certificate_replays_exact_wires_without_post_and_refuses_legacy(plain_certificate):
    path, certificate = plain_certificate
    count = len(ScriptedSession.calls)
    checked = preflight.require_certificate(path, BINDING, protocol='staged-v15',
        scope=preflight.EXECUTION_SCOPE, conversation_profile=PLAIN_JSON_HISTORY)
    assert checked['conversation_profile'] == certificate['plan']['conversation_profile'] == PLAIN_JSON_HISTORY
    assert len(ScriptedSession.calls) == count
    for row in certificate['records']:
        transport = row['transport']
        assert transport['conversation_profile'] == PLAIN_JSON_HISTORY
        assert json.loads(transport['request_wire_utf8']) == transport['request_payload']
        for message in transport['request_payload']['messages']:
            if message['role'] == 'assistant':
                assert set(json.loads(message['content'])) == {'name', 'arguments'}
    with pytest.raises(ValueError, match='protocol/runtime/backend'):
        preflight.require_certificate(path, BINDING, protocol='staged-v15', scope=preflight.EXECUTION_SCOPE)


def test_legacy_certificate_has_no_profile_fields_and_cannot_authorize_plain_history(tmp_path, monkeypatch):
    monkeypatch.setattr('requests.Session', ScriptedSession)
    directory = tmp_path / 'legacy'
    certificate = preflight.run_calibration(directory, request=request(), provider=BINDING)
    assert certificate['all_controls_passed'] and 'conversation_profile' not in certificate['plan']
    assert all('conversation_profile' not in row['transport'] for row in certificate['records'])
    with pytest.raises(ValueError, match='protocol/runtime/backend'):
        preflight.require_certificate(directory / 'certificate.json', BINDING, protocol='staged-v15',
            conversation_profile=PLAIN_JSON_HISTORY)
    with pytest.raises(ValueError, match='source-owned'):
        preflight.run_calibration(tmp_path / 'unknown', request=request(), provider=BINDING,
            conversation_profile='unknown')
    assert not (tmp_path / 'unknown').exists()


def test_real_production_model_passes_bound_profile_to_preflight_before_any_dispatch(monkeypatch):
    from tests.optimization.test_native_designer_roles_v38 import designer_binding
    from utopia.optimization.native_designer_roles_v38 import LocalRoleBoundDesignerModel
    seen = []
    def require(*args, **kwargs):
        seen.append(kwargs)
        raise ValueError('SCRIPTED refusal before any HTTP access')
    monkeypatch.setattr(preflight, 'require_certificate', require)
    model = LocalRoleBoundDesignerModel(designer_binding(), preflight_certificate='operator-only',
        readiness_scope=preflight.EXECUTION_SCOPE, conversation_profile=PLAIN_JSON_HISTORY)
    with pytest.raises(ValueError, match='before any HTTP'):
        model.generate(prompt='not sent', system_prompt='not sent', seed_ctx=[],
            max_tokens=8192, temperature=.6, response_format={})
    assert seen[0]['conversation_profile'] == PLAIN_JSON_HISTORY
    assert seen[0]['scope'] == preflight.EXECUTION_SCOPE


@pytest.mark.parametrize('where', ['plan', 'transport', 'schema', 'message'])
def test_rehashed_profile_or_frame_tamper_is_rejected(plain_certificate, where):
    path, certificate = plain_certificate
    row = next(r for r in certificate['records']
        if any(m['role'] == 'assistant' for m in r['transport']['request_payload']['messages']))
    if where == 'plan':
        certificate['plan'].pop('conversation_profile')
    elif where == 'transport':
        row['transport'].pop('conversation_profile')
    elif where == 'schema':
        row['transport']['conversation_schema'] = conversation_schema('interface-control-v16')
    else:
        messages = row['transport']['request_payload']['messages']
        next(m for m in messages if m['role'] == 'assistant')['content'] += ' '
    certificate['content_sha256'] = digest({k: v for k, v in certificate.items() if k != 'content_sha256'})
    path.write_text(json.dumps(certificate))
    with pytest.raises(ValueError):
        preflight.require_certificate(path, BINDING, protocol='staged-v15',
            scope=preflight.EXECUTION_SCOPE, conversation_profile=PLAIN_JSON_HISTORY)


class DialogueModel:
    conversation_profile = PLAIN_JSON_HISTORY

    def __init__(self, actions):
        self.actions, self.calls = actions, []

    def generate(self, **kwargs):
        action = self.actions.pop(0)
        self.calls.append(deepcopy(kwargs))
        messages = build_conversation(kwargs['prompt'], kwargs['system_prompt'], native_tools=True,
            conversation_profile=self.conversation_profile)
        payload = designer_payload('staged-v15', BINDING, messages, kwargs['seed_ctx'],
            max_tokens=kwargs['max_tokens'], temperature=kwargs['temperature'],
            role=task_decoding_role(kwargs['system_prompt']), conversation_profile=self.conversation_profile)
        message = response_message_from_action(action)
        body = {'model': BINDING['model'], 'message': message, 'done': True, 'done_reason': 'stop'}
        self.last_transport = {'conversation_profile': self.conversation_profile,
            'conversation_schema': conversation_schema('author', self.conversation_profile),
            'response_channel': CHANNEL, 'response_payload': body, 'raw_http_response': json.dumps(body),
            'source_prompt_sha256': digest(kwargs['prompt']), 'request_payload': payload,
            'endpoint': 'http://127.0.0.1:11434/api/chat', 'http_status': 200,
            'model_digest': BINDING['model_digest'], 'network_retries': 0,
            'http_timeout_seconds': [10, 900], **wire_record(payload, ACTION_SCHEMA)}
        return action, messages + [message]


def test_generator_cold_replay_and_independent_transport_audit_preserve_rejection(tmp_path):
    from scripts.analyze_native_staged_search_v15 import _transport, CLASSIFICATION
    action = {'tool': 'write_file', 'filename': 'history/no-edit.py', 'content': '<tool_call>原文</tool_call>'}
    model = DialogueModel([action, {'tool': 'finish', 'rationale': 'SCRIPTED retention'}])
    generator = StagedVocabularyGenerator(model, tmp_path, image_id=IMAGE, provider_binding=BINDING,
        max_steps=2, max_tokens=8192, conversation_profile=PLAIN_JSON_HISTORY)
    body = request()
    result = generator(body)
    cell = next(tmp_path.glob('generation-*'))
    binding = json.loads((cell / 'request.json').read_text())
    assert binding['settings']['conversation_profile'] == PLAIN_JSON_HISTORY
    rejected = json.loads((cell / 'step-00.completed.json').read_text())
    assert rejected['status'] == 'rejected' and rejected['model_reply']['output'] == action
    before = {f.name: f.read_bytes() for f in cell.glob('*.json')}
    assert replay_staged_generation(cell) == result and len(model.calls) == 2
    assert before == {f.name: f.read_bytes() for f in cell.glob('*.json')}
    completed = json.loads((cell / 'step-01.completed.json').read_text())
    started = json.loads((cell / 'step-01.started.json').read_text())
    assert _transport(completed, started, binding, CLASSIFICATION)['known_designer_response']
    completed['model_reply']['transport']['conversation_profile'] = LEGACY_HISTORY
    with pytest.raises(ValueError, match='dialogue'):
        _transport(completed, started, binding, CLASSIFICATION)
    with pytest.raises(ValueError, match='profiles differ'):
        StagedVocabularyGenerator(model, tmp_path, image_id=IMAGE, provider_binding=BINDING)


def test_conditional_pilot_declares_profile_without_changing_world_or_budgets():
    from scripts.run_native_designer_roles_v38 import build_plan as old_plan
    from scripts.run_native_json_history_v40 import build_plan
    from tests.optimization.test_native_designer_roles_v38 import designer_binding, request as search_request
    from tests.optimization.test_native_search_v14 import BINDING as WORLD, REVISION
    from utopia.optimization.native_designer_roles_v38 import validate_search_request
    kwargs = dict(source_commit=REVISION, initial_system=search_request()['initial_system'],
        provider_binding=WORLD, designer_provider_binding=designer_binding(), runtime_seed_binding={})
    old, new = old_plan(**kwargs), build_plan(**kwargs)
    assert 'conversation_profile' not in old
    assert new['conversation_profile'] == PLAIN_JSON_HISTORY and new['engineering_revision'] == 'v40-a1'
    for key in ('provider_binding', 'designer_provider_binding', 'initial_system', 'budget'):
        assert new[key] == old[key]
    for previous, current in zip(old['runs'], new['runs']):
        restored = deepcopy(current['request'])
        assert restored['designer'].pop('conversation_profile') == PLAIN_JSON_HISTORY
        assert restored == previous['request']
        assert current['runtime_plan']['conversation_profile'] == PLAIN_JSON_HISTORY
        assert current['plan_sha256'] == digest(current['runtime_plan'])
        bad = deepcopy(current['request']); bad['designer']['conversation_profile'] = 'unapproved'
        with pytest.raises(ValueError):
            validate_search_request(bad)


def test_optional_archived_frames_preserve_all_observations_and_original_bytes():
    # Deliberate opt-in diagnostic; normal tests have no ignored/absolute dependency.
    root = os.environ.get('SCIENCEUTOPIA_V40_DIAGNOSTIC_AUTHORING')
    if not root:
        pytest.skip('optional read-only archived-frame diagnostic not requested')
    files = sorted(Path(root).glob('generation-*/step-*.started.json'))
    assert files
    checked, recorded = 0, 0
    for file in files:
        original = file.read_bytes()
        started = json.loads(original)
        from utopia.optimization.native_staged_author_v15 import call_task
        task = call_task(started['step'], 8)
        old = build_conversation(started['prompt'], task, native_tools=True)
        completed_path = file.with_name(file.name.replace('.started.json', '.completed.json'))
        if completed_path.exists():
            completed_bytes = completed_path.read_bytes()
            transport = json.loads(completed_bytes)['model_reply'].get('transport', {})
            if 'request_payload' in transport:
                assert old == transport['request_payload']['messages']
                assert json.loads(transport['request_wire_utf8']) == transport['request_payload']
                assert all(transport[key] == value for key, value in
                    wire_record(transport['request_payload'], ACTION_SCHEMA).items())
                recorded += 1
            assert completed_path.read_bytes() == completed_bytes
        plain = build_conversation(started['prompt'], task, native_tools=True,
            conversation_profile=PLAIN_JSON_HISTORY)
        assert [m['role'] for m in plain] == [m['role'] for m in old]
        for previous, current in zip(old, plain):
            if previous['role'] == 'assistant':
                payload = previous['content'].removeprefix('<tool_call>\n').removesuffix('\n</tool_call>')
                assert json.loads(payload) == json.loads(current['content'])
                checked += 1
            elif previous['role'] == 'tool':
                assert current == previous
            else:
                assert previous['content'].replace(TOOL_RESPONSE_ONLY,
                    response_instruction(PLAIN_JSON_HISTORY)) == current['content']
        assert file.read_bytes() == original
    assert checked
    print(json.dumps({'archived_started_frames': len(files), 'archived_recorded_wire_frames': recorded,
        'reconstructed_assistant_history_frames': checked, 'original_files_changed': False}))
