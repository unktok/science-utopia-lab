"""SCRIPTED profile/transport/certificate checks; no real backend or code execution."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_authoring_ir import BINDING, IMAGE, request
from tests.optimization.test_native_designer_contract_v16 import ScriptedSession
from tests.optimization.test_native_json_history_v40 import DialogueModel, frame
from utopia.optimization import native_designer_preflight as preflight
from utopia.optimization.native_designer_decoding_v24 import decoding_contract, decoding_contracts, designer_payload
from utopia.optimization.native_designer_tools_v25 import (
    LEGACY_HISTORY, PLAIN_JSON_HISTORY, PLAIN_FUNCTION_DIRECT as DIRECT, conversation_schema,
    function_data, message_from_action,
)
from utopia.optimization.native_staged_author_v15 import (
    ACTION_SCHEMA, PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT, StagedVocabularyGenerator,
    build_conversation, replay_staged_generation,
)
from utopia.optimization.native_designer_wire import wire_record
from utopia.system.design_patch import digest


@pytest.fixture(autouse=True)
def no_candidate_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('profile tests must not execute candidate code')
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)


@pytest.mark.parametrize('role', ['planner', 'editor'])
def test_direct_changes_only_think_and_keeps_default_legacy_and_v40(role):
    legacy = decoding_contract('staged-v15', role=role)
    assert legacy == decoding_contract('staged-v15', role=role, conversation_profile=LEGACY_HISTORY)
    assert legacy == decoding_contract('staged-v15', role=role, conversation_profile=PLAIN_JSON_HISTORY)
    direct = decoding_contract('staged-v15', role=role, conversation_profile=DIRECT)
    assert direct == {**legacy, 'think': False}
    assert direct['max_tokens'] == 8192 and direct['temperature'] == .6
    assert direct['sampling_options']['num_ctx'] == 40960
    assert direct['http_timeout_seconds'] == [10, 900]
    args = dict(max_tokens=8192, temperature=.6, role=role)
    old = designer_payload('staged-v15', BINDING, [], ['seed', 42], **args)
    assert old == designer_payload('staged-v15', BINDING, [], ['seed', 42],
        conversation_profile=PLAIN_JSON_HISTORY, **args)
    assert designer_payload('staged-v15', BINDING, [], ['seed', 42],
        conversation_profile=DIRECT, **args) == {**old, 'think': False}
    for changed in ({'max_tokens': 2048}, {'temperature': .2}):
        with pytest.raises(ValueError, match='source-owned decoding'):
            designer_payload('staged-v15', BINDING, [], ['seed', 42],
                conversation_profile=DIRECT, **{**args, **changed})
    with pytest.raises(ValueError, match='requires staged'):
        decoding_contract('one-shot-v14', conversation_profile=DIRECT)
    with pytest.raises(ValueError, match='source-owned'):
        decoding_contract('staged-v15', conversation_profile='model-selected')


@pytest.mark.parametrize('task', [PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT])
def test_plain_rendering_and_literal_values_are_identical_to_v40(task):
    action = {'tool': 'write_file', 'filename': 'history/immutable.py',
        'content': '研究者\n<tool_call>literal</tool_call>\\n"', 'large': 9007199254740993}
    assert message_from_action(action, conversation_profile=DIRECT) == message_from_action(
        action, conversation_profile=PLAIN_JSON_HISTORY)
    assert json.loads(message_from_action(action, conversation_profile=DIRECT)['content']) == function_data(action)
    prompt, _ = frame(action)
    direct = build_conversation(prompt, task, native_tools=True, conversation_profile=DIRECT)
    assert direct == build_conversation(prompt, task, native_tools=True, conversation_profile=PLAIN_JSON_HISTORY)
    assert 'Hermes tags' not in direct[0]['content']
    assert conversation_schema('author', DIRECT) != conversation_schema('author', PLAIN_JSON_HISTORY)


@pytest.fixture
def direct_certificate(tmp_path, monkeypatch):
    monkeypatch.setattr('requests.Session', ScriptedSession)
    ScriptedSession.calls = []
    root = tmp_path / 'direct-controls'
    certificate = preflight.run_calibration(root, request=request(), provider=BINDING,
        conversation_profile=DIRECT, scope=preflight.EXECUTION_SCOPE)
    assert certificate['all_controls_passed']
    return root / 'certificate.json', certificate


def test_calibration_binds_both_role_modes_and_cold_replays_without_dispatch(direct_certificate):
    path, value = direct_certificate
    count = len(ScriptedSession.calls)
    assert value['plan']['decoding_contract'] == decoding_contracts('staged-v15', conversation_profile=DIRECT)
    roles = value['reasoning_evidence']['roles']
    assert set(roles) == {'planner', 'editor'}
    assert all(not row['requested'] and row['controls_seen'] and not row['known_nonempty_response_fields']
        for row in roles.values())
    assert value['reasoning_evidence']['all_role_modes_compatible']
    checked = preflight.require_certificate(path, BINDING, protocol='staged-v15',
        conversation_profile=DIRECT, scope=preflight.EXECUTION_SCOPE)
    assert checked['conversation_profile'] == DIRECT and len(ScriptedSession.calls) == count
    for record in value['records']:
        transport = record['transport']
        assert transport['request_payload']['think'] is False
        assert json.loads(transport['request_wire_utf8']) == transport['request_payload']
        assert transport['http_timeout_seconds'] == [10, 900] and transport['network_retries'] == 0
    for profile in (LEGACY_HISTORY, PLAIN_JSON_HISTORY):
        with pytest.raises(ValueError, match='binding changed'):
            preflight.require_certificate(path, BINDING, protocol='staged-v15',
                conversation_profile=profile, scope=preflight.EXECUTION_SCOPE)


@pytest.mark.parametrize('profile', [LEGACY_HISTORY, PLAIN_JSON_HISTORY])
def test_old_profiles_cannot_authorize_direct(tmp_path, monkeypatch, profile):
    monkeypatch.setattr('requests.Session', ScriptedSession)
    root = tmp_path / 'old-controls'
    preflight.run_calibration(root, request=request(), provider=BINDING, conversation_profile=profile)
    with pytest.raises(ValueError, match='binding changed'):
        preflight.require_certificate(root / 'certificate.json', BINDING,
            protocol='staged-v15', conversation_profile=DIRECT)


@pytest.mark.parametrize('mutation', ['profile', 'contract', 'payload', 'thinking'])
def test_rehashed_certificate_tamper_is_rejected(direct_certificate, mutation):
    path, value = direct_certificate
    if mutation == 'profile':
        value['plan']['conversation_profile'] = PLAIN_JSON_HISTORY
    elif mutation == 'contract':
        value['plan']['decoding_contract']['planner']['think'] = True
    elif mutation == 'payload':
        value['records'][0]['transport']['request_payload']['think'] = True
    else:
        transport = value['records'][0]['transport']
        transport['response_payload']['message']['thinking'] = 'unexpected separate thinking'
        transport['raw_http_response'] = json.dumps(transport['response_payload'])
        value['reasoning_evidence'] = preflight.reasoning_evidence(value['records'],
            protocol='staged-v15', conversation_profile=DIRECT)
    value['content_sha256'] = digest({k: v for k, v in value.items() if k != 'content_sha256'})
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        preflight.require_certificate(path, BINDING, protocol='staged-v15',
            conversation_profile=DIRECT, scope=preflight.EXECUTION_SCOPE)


@pytest.mark.parametrize('thinking', [12, True, {}, []])
def test_direct_invalid_thinking_field_type_is_incompatible_not_absence(direct_certificate, thinking):
    path, value = direct_certificate
    transport = value['records'][0]['transport']
    transport['response_payload']['message']['thinking'] = thinking
    transport['raw_http_response'] = json.dumps(transport['response_payload'])
    evidence = preflight.reasoning_evidence(value['records'], protocol='staged-v15', conversation_profile=DIRECT)
    assert evidence['roles']['editor']['invalid_thinking_response_fields'] == 1
    assert not evidence['all_role_modes_compatible']
    value['reasoning_evidence'] = evidence
    value['content_sha256'] = digest({k: v for k, v in value.items() if k != 'content_sha256'})
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='response evidence'):
        preflight.require_certificate(path, BINDING, protocol='staged-v15',
            conversation_profile=DIRECT, scope=preflight.EXECUTION_SCOPE)
    assert transport['response_payload']['message']['thinking'] == thinking


@pytest.mark.parametrize('thinking', [None, '', ' \n\t'])
def test_direct_absent_or_empty_thinking_keeps_original_metadata_and_legacy_evidence_shape(thinking):
    record = {'intent': {'id': 'sequence-plan'},
        'transport': {'response_payload': {'message': {'thinking': thinking}}}}
    direct = preflight.reasoning_evidence([record], protocol='staged-v15', conversation_profile=DIRECT)
    assert direct['all_role_modes_compatible'] and not direct['roles']['planner']['invalid_thinking_response_fields']
    for profile in (LEGACY_HISTORY, PLAIN_JSON_HISTORY):
        old = preflight.reasoning_evidence([record], protocol='staged-v15', conversation_profile=profile)
        assert all('invalid_thinking_response_fields' not in row for row in old['roles'].values())
    assert record['transport']['response_payload']['message']['thinking'] == thinking


@pytest.mark.parametrize('task', [PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT])
def test_production_sender_uses_explicit_direct_contract(monkeypatch, task):
    from tests.optimization.test_native_designer_contract_v16 import Response
    from utopia.optimization.native_staged_author_v15 import LocalStagedQwenDesignerModel
    class Session(ScriptedSession):
        def post(self, url, **kwargs):
            assert kwargs['timeout'] == (10, 900)
            payload = json.loads(kwargs['data'])
            assert payload['think'] is False and payload['options']['num_predict'] == 8192
            assert payload['options']['temperature'] == .6 and 'tools' not in payload
            self.calls.append(payload)
            return Response({'model': BINDING['model'], 'done': True, 'done_reason': 'stop',
                'message': {'role': 'assistant', 'content': '{"name":"finish","arguments":{"rationale":"SCRIPTED"}}'}})
    monkeypatch.setattr('requests.Session', Session)
    model = LocalStagedQwenDesignerModel(BINDING, conversation_profile=DIRECT)
    prompt, _ = frame()
    action, _ = model.generate(prompt=prompt, system_prompt=task, seed_ctx=['seed', 42],
        max_tokens=8192, temperature=.6, response_format={'json_object': {'schema': ACTION_SCHEMA}})
    assert action == {'tool': 'finish', 'rationale': 'SCRIPTED'}
    assert model.last_transport['conversation_profile'] == DIRECT


def test_separate_designer_refuses_missing_direct_authority_before_http(monkeypatch):
    from tests.optimization.test_native_designer_roles_v38 import designer_binding
    from utopia.optimization.native_designer_roles_v38 import LocalRoleBoundDesignerModel
    seen = []
    def refuse(*args, **kwargs):
        seen.append(kwargs)
        raise ValueError('SCRIPTED direct certificate refusal before HTTP')
    monkeypatch.setattr(preflight, 'require_certificate', refuse)
    model = LocalRoleBoundDesignerModel(designer_binding(), preflight_certificate='operator-only',
        conversation_profile=DIRECT, readiness_scope=preflight.EXECUTION_SCOPE)
    with pytest.raises(ValueError, match='before HTTP'):
        model.generate(prompt='never sent', system_prompt=PLAN_SYSTEM_PROMPT, seed_ctx=[],
            max_tokens=8192, temperature=.6, response_format={})
    assert seen[0]['conversation_profile'] == DIRECT and seen[0]['scope'] == preflight.EXECUTION_SCOPE


class DirectModel(DialogueModel):
    conversation_profile = DIRECT


@pytest.mark.parametrize('mutation', [None, 'think', 'wire', 'schema', 'profile'])
def test_journal_replay_and_independent_auditor_check_direct_decoding_without_redispatch(tmp_path, mutation):
    from scripts.analyze_native_staged_search_v15 import _transport, CLASSIFICATION
    from utopia.utils.data_utils import write_json_atomic
    action = {'tool': 'write_file', 'filename': 'history/no-edit.py', 'content': '<tool_call>原文\n</tool_call>'}
    model = DirectModel([action, {'tool': 'finish', 'rationale': 'SCRIPTED retention'}])
    generator = StagedVocabularyGenerator(model, tmp_path, image_id=IMAGE, provider_binding=BINDING,
        max_steps=2, max_tokens=8192, conversation_profile=DIRECT)
    result = generator(request())
    cell = next(tmp_path.glob('generation-*'))
    binding = json.loads((cell / 'request.json').read_text())
    assert binding['settings']['designer_decoding'] == decoding_contracts('staged-v15', conversation_profile=DIRECT)
    path = cell / 'step-01.completed.json'
    completed = json.loads(path.read_text())
    started = json.loads((cell / 'step-01.started.json').read_text())
    assert json.loads((cell / 'step-00.completed.json').read_text())['status'] == 'rejected'
    assert replay_staged_generation(cell) == result and len(model.calls) == 2
    assert _transport(completed, started, binding, CLASSIFICATION)['known_designer_response']
    if mutation is None:
        return
    transport = completed['model_reply']['transport']
    if mutation == 'think':
        transport['request_payload']['think'] = True
        transport.update(wire_record(transport['request_payload'], ACTION_SCHEMA))
    elif mutation == 'wire':
        transport['request_wire_utf8'] += ' '
    elif mutation == 'schema':
        transport.pop('conversation_schema')
    else:
        transport['conversation_profile'] = PLAIN_JSON_HISTORY
    completed['content_sha256'] = digest({k: v for k, v in completed.items() if k != 'content_sha256'})
    write_json_atomic(path, completed, sort_keys=True, allow_nan=False)
    with pytest.raises(ValueError):
        replay_staged_generation(cell)
    with pytest.raises(ValueError):
        _transport(completed, started, binding, CLASSIFICATION)
    assert len(model.calls) == 2


def test_conditional_driver_and_runtime_plan_bind_direct_without_changing_scientific_scope():
    from scripts.run_native_json_history_v40 import build_plan as v40
    from scripts.run_native_direct_profile_v43 import build_plan
    from tests.optimization.test_native_designer_roles_v38 import designer_binding, request as search_request
    from tests.optimization.test_native_search_v14 import BINDING as WORLD, REVISION
    kwargs = dict(source_commit=REVISION, initial_system=search_request()['initial_system'],
        provider_binding=WORLD, designer_provider_binding=designer_binding(), runtime_seed_binding={})
    old, new = v40(**kwargs), build_plan(**kwargs)
    assert new['conversation_profile'] == DIRECT and new['engineering_revision'] == 'v43-a1'
    assert new['native_campaign_status'].startswith('CONDITIONAL')
    assert new['designer_decoding'] == decoding_contracts('staged-v15', conversation_profile=DIRECT)
    for key in ('provider_binding', 'designer_provider_binding', 'initial_system', 'budget'):
        assert old[key] == new[key]
    for previous, current in zip(old['runs'], new['runs']):
        restored = deepcopy(current['request'])
        assert restored['designer'].pop('conversation_profile') == DIRECT
        restored['designer']['conversation_profile'] = PLAIN_JSON_HISTORY
        assert restored == previous['request']
        assert current['runtime_plan']['conversation_profile'] == DIRECT
        assert current['runtime_plan']['designer_decoding'] == new['designer_decoding']
        assert current['plan_sha256'] == digest(current['runtime_plan'])


def test_direct_rejects_other_budget_before_authoring_or_queue_dispatch(tmp_path):
    from tests.optimization.test_native_designer_roles_v38 import request as search_request
    from utopia.optimization.native_designer_roles_v38 import validate_search_request
    body = search_request()
    body['designer'].update(conversation_profile=DIRECT, max_tokens=2048)
    with pytest.raises(ValueError, match='source-owned decoding token budget'):
        validate_search_request(body)
    with pytest.raises(ValueError, match='source-owned decoding token budget'):
        StagedVocabularyGenerator(DirectModel([]), tmp_path / 'not-created', image_id=IMAGE,
            provider_binding=BINDING, max_tokens=2048, conversation_profile=DIRECT)
    assert not (tmp_path / 'not-created').exists()
