"""SCRIPTED recurrence prevention; actual backend evidence is a separate artifact."""
import json

import pytest
from jsonschema import Draft202012Validator

from tests.optimization.test_native_authoring_ir import BINDING, IMAGE, request
from utopia.optimization import native_designer_preflight as p
from utopia.optimization.native_staged_author_v15 import (
    ACTION_SCHEMA, initial_draft, transition, read_memory, turn_control, make_local_staged_generator,
)
from utopia.optimization.native_search_generator_v14 import make_local_vocabulary_generator
from utopia.system.design_patch import clone, digest


@pytest.mark.parametrize('value', p.VALUES)
def test_all_json_operand_types_are_explicit_and_host_accepted(value):
    from utopia.optimization.native_authoring_ir import ANY_JSON, OPERATION
    assert set(ANY_JSON['type']) == {'object', 'array', 'string', 'number', 'boolean', 'null'}
    for branch in OPERATION['oneOf']:
        if 'value' in branch['properties']:
            assert branch['properties']['value'] == ANY_JSON
    action = {'tool': 'edit', 'operations': [{'op': 'add', 'path': '/metadata/probe', 'value': value}]}
    Draft202012Validator(ACTION_SCHEMA).validate(action)
    state, receipt = transition(initial_draft(request()), action, request(),
        binding_sha256='d' * 64, provider_binding=BINDING)
    assert receipt['ok'] and digest(state['document']['metadata']['probe']) == digest(value)


@pytest.mark.parametrize('action', [
    {'tool': 'inspect'}, {'tool': 'inspect', 'path': '', 'text': 'wrong'},
    {'tool': 'inspect', 'resource': 'capabilities', 'selector': {'mechanism_id': 'x'}, 'path': ''},
    {'tool': 'edit'}, {'tool': 'edit', 'operations': []},
    {'tool': 'edit', 'operations': [{'op': 'add', 'path': '/metadata/x', 'value': 1}], 'rationale': 'wrong'},
    {'tool': 'splice', 'path': '/x', 'text': ''}, {'tool': 'configure'},
    {'tool': 'validate', 'path': ''}, {'tool': 'finish'}, {'tool': 'finish', 'rationale': ''},
])
def test_sender_schema_and_receiver_both_reject_incomplete_or_cross_tool_fields(action):
    assert list(Draft202012Validator(ACTION_SCHEMA).iter_errors(action))
    old = initial_draft(request())
    state, receipt = transition(old, action, request(), binding_sha256='d' * 64, provider_binding=BINDING)
    assert not receipt['ok'] and state == old


def test_alternating_alias_reads_share_memory_warn_and_real_change_resets_freshness():
    body = request(); state = initial_draft(body); steps = []
    for action in [{'tool': 'inspect', 'path': '/mechanisms/0/parameters'},
            {'tool': 'inspect', 'path': '/metadata'},
            {'tool': 'inspect', 'selector': {'mechanism_id': body['parent_system']['mechanisms'][0]['mechanism_id']},
                'path': '/parameters'}]:
        state, receipt = transition(state, action, body, binding_sha256='d' * 64, provider_binding=BINDING)
        steps.append({'step': len(steps), 'model_reply': {'output': action}, 'transition': receipt})
    memory = read_memory(state, steps)
    assert len(memory['entries']) == 2 and max(item['read_count'] for item in memory['entries']) == 2
    assert any(item.get('value') == {} for item in memory['entries'])
    control = turn_control(state, steps, max_steps=16)
    assert control['consecutive_same_successful_inspections_of_unchanged_draft'] == 1
    assert control['nonconsecutive_revisits_of_unchanged_observed_addresses'] == 1
    assert 'already observed' in control['inspection_notice']
    state, receipt = transition(state, {'tool': 'edit', 'operations': [
        {'op': 'add', 'path': '/metadata/change', 'value': True}]}, body,
        binding_sha256='d' * 64, provider_binding=BINDING)
    assert all(not item['current_document'] for item in read_memory(state, steps)['entries'])
    assert turn_control(state, steps, max_steps=16)['inspection_notice'] is None


def test_memory_caps_mark_omissions_preserve_descriptors_and_never_invent_values():
    state = initial_draft(request()); steps = []
    for index in range(8):
        value = 'x' * (8000 if index < 7 else 9000)
        steps.append({'step': index, 'transition': {'tool': 'inspect', 'ok': True,
            'document_after_sha256': digest(state['document']), 'result': {'resource': 'draft',
                'path': '/fake/observed/' + str(index), 'descriptor': {'sha256': digest(value), 'type': 'string'},
                'value_included': True, 'value': value}}})
    memory = read_memory(state, steps)
    assert len(memory['entries']) == 8
    assert sum(len(json.dumps(item.get('value', '')).encode()) for item in memory['entries']) < 32768
    assert all('omission' in item for item in memory['entries'] if not item['value_included'])


@pytest.mark.parametrize('factory', [make_local_staged_generator, make_local_vocabulary_generator])
def test_production_factories_refuse_missing_certificate_before_model_or_files(tmp_path, factory, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('model must not be constructed')
    monkeypatch.setattr('utopia.optimization.native_search_generator_v14.LocalQwenDesignerModel', forbidden)
    with pytest.raises(ValueError, match='certificate required'):
        factory(tmp_path / 'author', image_id=IMAGE, provider_binding=BINDING)
    assert not (tmp_path / 'author').exists()


class Response:
    status_code = 200
    def __init__(self, body):
        self.body, self.text = body, json.dumps(body, ensure_ascii=False)
    def json(self):
        return clone(self.body)
    def raise_for_status(self):
        pass


class ScriptedSession:
    trust_env = True
    calls = []
    def get(self, url, **kwargs):
        assert self.trust_env is False
        if url.endswith('/version'):
            return Response({'version': 'SCRIPTED-not-actual'})
        return Response({'models': [{'name': BINDING['model'], 'digest': BINDING['model_digest']}]})
    def post(self, url, **kwargs):
        payload = json.loads(kwargs['data'])
        system = payload['messages'][0]['content']
        expected, _ = json.JSONDecoder().raw_decode(system.split('nothing is executed or adopted.\n')[1])
        self.calls.append(payload)
        return Response({'model': BINDING['model'], 'message': {'content': json.dumps(expected, ensure_ascii=False)},
            'done': True, 'done_reason': 'stop', 'eval_count': 12, 'prompt_eval_count': 120})


@pytest.fixture
def certificate(tmp_path, monkeypatch):
    monkeypatch.setattr('requests.Session', ScriptedSession)
    ScriptedSession.calls = []
    directory = tmp_path / 'calibration'
    result = p.run_calibration(directory, request=request(), provider=BINDING)
    assert result['all_controls_passed'] and len(result['records']) == 13
    return directory / 'certificate.json'


def test_certificate_replays_all_exact_wire_typed_controls_and_continuous_code_sequence(certificate):
    result = p.require_certificate(certificate, BINDING, protocol='staged-v15')
    assert result['controls'] == 13


def test_one_shot_has_its_own_protocol_bound_controls_and_certificate(tmp_path, monkeypatch):
    monkeypatch.setattr('requests.Session', ScriptedSession)
    directory = tmp_path / 'one-shot'
    result = p.run_calibration(directory, request=request(), provider=BINDING, protocol='one-shot-v14')
    assert result['all_controls_passed'] and len(result['records']) == 8
    assert p.require_certificate(directory / 'certificate.json', BINDING, protocol='one-shot-v14')['controls'] == 8
    with pytest.raises(ValueError, match='protocol/runtime/backend'):
        p.require_certificate(directory / 'certificate.json', BINDING, protocol='staged-v15')


@pytest.mark.parametrize('mutation', ['pass-flag', 'drop-call', 'wire', 'output', 'schema',
    'partial', 'runtime', 'backend', 'receipt', 'model', 'seed', 'unsafe-number', 'expired', 'future'])
def test_rehashed_certificate_corruption_does_not_bypass_cold_gate(certificate, mutation):
    value = json.loads(certificate.read_text()); record = value['records'][0]
    if mutation == 'pass-flag': value['all_controls_passed'] = False
    elif mutation == 'drop-call': value['records'].pop()
    elif mutation == 'wire': record['transport']['request_wire_utf8'] += ' '
    elif mutation == 'output': record['output']['operations'][0]['value'] = 18
    elif mutation == 'schema': record['transport']['host_response_schema_sha256'] = '0' * 64
    elif mutation == 'partial':
        record['transport']['response_payload']['done'] = False
        record['transport']['raw_http_response'] = json.dumps(record['transport']['response_payload'])
    elif mutation == 'runtime': value['plan']['runtime']['optimization/native_staged_author_v15.py'] = '0' * 64
    elif mutation == 'backend': value['plan']['backend']['ollama_version'] = 'changed'
    elif mutation == 'receipt': record['receipt']['document_after_sha256'] = '0' * 64
    elif mutation == 'model': record['transport']['model_digest'] = '0' * 64
    elif mutation == 'seed': record['transport']['request_payload']['options']['seed'] += 1
    elif mutation == 'unsafe-number': value['records'][7]['output']['operations'][0]['value'] = 9007199254740992
    elif mutation == 'expired': value['completed_epoch'] -= 86401
    elif mutation == 'future': value['completed_epoch'] += 100
    value['content_sha256'] = digest({key: item for key, item in value.items() if key != 'content_sha256'})
    certificate.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        p.require_certificate(certificate, BINDING, protocol='staged-v15')


def test_production_transport_rechecks_certificate_before_any_post(certificate, monkeypatch):
    generator = make_local_staged_generator(certificate.parent / 'author', image_id=IMAGE,
        provider_binding=BINDING, preflight_certificate=certificate)
    before = len(ScriptedSession.calls)
    certificate.write_text('{}')
    with pytest.raises(ValueError, match='hash/schema'):
        generator.model.generate(prompt='not reached', system_prompt='not reached', seed_ctx=[],
            max_tokens=512, temperature=.2, response_format={'json_object': {'schema': ACTION_SCHEMA}})
    assert len(ScriptedSession.calls) == before


def test_failed_control_is_charged_and_never_replaced(tmp_path, monkeypatch):
    class WrongSession(ScriptedSession):
        def post(self, *args, **kwargs):
            super().post(*args, **kwargs)
            return Response({'model': BINDING['model'], 'message': {'content': '{"tool":"validate"}'}, 'done': True})
    monkeypatch.setattr('requests.Session', WrongSession)
    ScriptedSession.calls = []
    result = p.run_calibration(tmp_path / 'failed', request=request(), provider=BINDING)
    assert len(result['records']) == len(ScriptedSession.calls) == 1 and not result['all_controls_passed']
    with pytest.raises(ValueError, match='incomplete'):
        p.require_certificate(tmp_path / 'failed/certificate.json', BINDING, protocol='staged-v15')
