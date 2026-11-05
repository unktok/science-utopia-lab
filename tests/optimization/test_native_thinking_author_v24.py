"""SCRIPTED reasoning transport and phase advertisement, not model performance."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from tests.optimization.test_native_authoring_ir import BINDING, request
from tests.optimization.test_native_planning_author_v22 import PLAN
from utopia.optimization.native_designer_decoding_v24 import decoding_contract, designer_payload
from utopia.optimization.native_staged_author_v15 import ACTION_SCHEMA, turn_response_schema, initial_draft
from tests.optimization.test_native_staged_author_v15 import apply


def test_source_owned_staged_reasoning_settings_and_legacy_wire_are_distinct():
    messages = [{'role': 'user', 'content': 'SCRIPTED fixture'}]
    original = deepcopy(messages)
    actual = designer_payload('staged-v15', BINDING, messages, ('SCRIPTED',), max_tokens=8192, temperature=.6,
        role='planner')
    assert actual['think'] is True and actual['format'] == 'json' and actual['stream'] is False
    assert actual['truncate'] is False and actual['shift'] is False
    assert actual['options'] == {'temperature': .6, 'num_predict': 8192, 'num_ctx': 32768,
        'top_p': .95, 'top_k': 20, 'min_p': 0.0, 'seed': actual['options']['seed']}
    assert messages == original
    assert decoding_contract('staged-v15')['max_tokens'] == 8192
    editor = designer_payload('staged-v15', BINDING, messages, ('SCRIPTED',), max_tokens=8192, temperature=.2,
        role='editor')
    assert editor['think'] is False and editor['options']['temperature'] == .2
    legacy = designer_payload('one-shot-v14', BINDING, messages, ('SCRIPTED',), max_tokens=2048, temperature=.2)
    assert legacy['think'] is False and legacy['format'] == 'json'
    assert legacy['options'] == {'temperature': .2, 'num_predict': 2048, 'num_ctx': 32768,
        'seed': actual['options']['seed']}
    with pytest.raises(ValueError, match='unknown'):
        decoding_contract('model-authored-protocol')
    with pytest.raises(ValueError, match='unknown'):
        decoding_contract('staged-v15', role='WORLD_STRING_REQUESTING_PLANNER')


def test_editor_advertises_implementation_first_without_removing_any_legal_tool():
    editor = turn_response_schema(7)
    assert editor['oneOf'][0]['properties']['tool']['const'] == 'edit_fields'
    by_tool = lambda value: {part['properties']['tool']['const']: part for part in value['oneOf']}
    assert by_tool(editor) == by_tool(ACTION_SCHEMA)
    assert editor['$defs'] == ACTION_SCHEMA['$defs']
    Draft202012Validator(editor).validate(PLAN)
    Draft202012Validator(editor).validate({'tool': 'finish', 'rationale': 'SCRIPTED explicit retention'})
    old = initial_draft(request())
    _, planned = apply(old, PLAN)
    _, finished = apply(old, {'tool': 'finish', 'rationale': 'SCRIPTED explicit retention'})
    assert planned['ok'] and finished['ok'] and finished['definition']['base_patch'] is None
    assert turn_response_schema(1)['properties']['tool']['const'] == 'finish'


def test_exact_controls_without_observed_reasoning_do_not_prove_requested_mode(tmp_path, monkeypatch):
    from tests.optimization.test_native_designer_contract_v16 import ScriptedSession, Response
    from utopia.optimization.native_designer_preflight import run_calibration, require_certificate
    class NoThinkingSession(ScriptedSession):
        def post(self, url, **kwargs):
            response = super().post(url, **kwargs)
            response.body['message'].pop('thinking', None)
            return Response(response.body)
    monkeypatch.setattr('requests.Session', NoThinkingSession)
    directory = tmp_path / 'no-reasoning-evidence'
    result = run_calibration(directory, request=request(), provider=BINDING)
    assert len(result['records']) == 24 and all(record['ok'] for record in result['records'])
    assert result['reasoning_evidence']['requested'] is True
    assert result['reasoning_evidence']['known_nonempty_response_fields'] == 0
    assert result['all_controls_passed'] is False
    with pytest.raises(ValueError):
        require_certificate(directory / 'certificate.json', BINDING, protocol='staged-v15')


def test_source_owned_response_contract_keeps_legacy_frames_and_current_hermes_distinct():
    from utopia.optimization.native_staged_author_v15 import (
        FINAL_JSON_ONLY, PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT, PLAN_CONTROL_SYSTEM_PROMPT, native_call_task)
    from utopia.optimization.native_designer_tools_v25 import TOOL_RESPONSE_ONLY
    assert 'without Markdown fences' in FINAL_JSON_ONLY
    for task in (PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT, PLAN_CONTROL_SYSTEM_PROMPT):
        assert FINAL_JSON_ONLY in task
        assert TOOL_RESPONSE_ONLY in native_call_task(task)
        assert FINAL_JSON_ONLY not in native_call_task(task)
    from utopia.optimization.native_designer_preflight import _prompt
    _, task = _prompt(request(), initial_draft(request()), [], BINDING,
        {'tool': 'validate'}, 'staged-v15')
    assert TOOL_RESPONSE_ONLY in task and FINAL_JSON_ONLY not in task


def test_nested_control_with_extra_closing_brace_still_rejects_without_prefix_salvage():
    from utopia.optimization.native_search_generator_v14 import _strict_json
    action = {'tool': 'edit', 'operations': [{'op': 'add', 'path': '/metadata/interface_calibration',
        'value': {'nested': {'items': [None, 1]}}}]}
    text = json.dumps(action)
    assert _strict_json(text) == action
    with pytest.raises(json.JSONDecodeError, match='Extra data'):
        _strict_json(text + '}')


def test_real_line_feeds_are_not_silently_restored_from_literal_backslash_n():
    from utopia.optimization.native_search_generator_v14 import _strict_json
    value = 'SCRIPTED\n"quoted" \\ source'
    wrong = value.replace('\n', '\\n')
    assert _strict_json(json.dumps({'value': wrong}))['value'] == wrong
    assert wrong != value


def test_staged_dispatch_uses_caller_owned_planner_then_literal_editor_temperatures(tmp_path):
    from tests.optimization.test_native_staged_author_v15 import Model, author
    from utopia.optimization.native_staged_author_v15 import task_decoding_role, PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT
    model = Model([PLAN, {'tool': 'finish', 'rationale': 'SCRIPTED explicit retention'}])
    result = author(model, tmp_path, max_steps=3)(request())
    assert result['base_patch'] is None
    assert [call['temperature'] for call in model.calls] == [.6, .2]
    assert task_decoding_role(PLAN_SYSTEM_PROMPT) == 'planner'
    assert task_decoding_role(SYSTEM_PROMPT) == task_decoding_role('UNTRUSTED planner request') == 'editor'


def test_editor_reasoning_fields_cannot_substitute_for_missing_planner_mode_evidence(tmp_path, monkeypatch):
    from tests.optimization.test_native_designer_contract_v16 import ScriptedSession, Response
    from utopia.optimization.native_designer_preflight import run_calibration
    class WrongRoleSession(ScriptedSession):
        def post(self, url, **kwargs):
            response = super().post(url, **kwargs)
            payload = json.loads(kwargs['data'])
            if payload['think']:
                response.body['message'].pop('thinking', None)
            else:
                response.body['message']['thinking'] = 'SCRIPTED unexpected editor field'
            return Response(response.body)
    monkeypatch.setattr('requests.Session', WrongRoleSession)
    result = run_calibration(tmp_path / 'wrong-role', request=request(), provider=BINDING)
    assert len(result['records']) == 24 and all(record['ok'] for record in result['records'])
    assert result['reasoning_evidence']['known_nonempty_response_fields'] == 23
    assert result['reasoning_evidence']['roles']['planner']['known_nonempty_response_fields'] == 0
    assert result['all_controls_passed'] is False


def test_requested_planner_evidence_does_not_hide_unexpected_editor_reasoning(tmp_path, monkeypatch):
    from tests.optimization.test_native_designer_contract_v16 import ScriptedSession, Response
    from utopia.optimization.native_designer_preflight import run_calibration
    class ExtraEditorThinkingSession(ScriptedSession):
        def post(self, url, **kwargs):
            response = super().post(url, **kwargs)
            if not json.loads(kwargs['data'])['think']:
                response.body['message']['thinking'] = 'SCRIPTED unexpected literal-editor reasoning'
            return Response(response.body)
    monkeypatch.setattr('requests.Session', ExtraEditorThinkingSession)
    result = run_calibration(tmp_path / 'unexpected-editor-thinking', request=request(), provider=BINDING)
    assert len(result['records']) == 24 and all(record['ok'] for record in result['records'])
    assert result['reasoning_evidence']['all_requested_roles_observed'] is True
    assert result['reasoning_evidence']['all_role_modes_compatible'] is False
    assert result['all_controls_passed'] is False
