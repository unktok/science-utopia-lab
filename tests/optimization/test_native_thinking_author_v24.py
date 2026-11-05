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
    actual = designer_payload('staged-v15', BINDING, messages, ('SCRIPTED',), max_tokens=8192, temperature=.6)
    assert actual['think'] is True and actual['format'] == 'json' and actual['stream'] is False
    assert actual['options'] == {'temperature': .6, 'num_predict': 8192, 'num_ctx': 32768,
        'top_p': .95, 'top_k': 20, 'min_p': 0.0, 'seed': actual['options']['seed']}
    assert messages == original
    assert decoding_contract('staged-v15')['max_tokens'] == 8192
    legacy = designer_payload('one-shot-v14', BINDING, messages, ('SCRIPTED',), max_tokens=2048, temperature=.2)
    assert legacy['think'] is False and legacy['format'] == 'json'
    assert legacy['options'] == {'temperature': .2, 'num_predict': 2048, 'num_ctx': 32768,
        'seed': actual['options']['seed']}
    with pytest.raises(ValueError, match='unknown'):
        decoding_contract('model-authored-protocol')


def test_editor_advertises_implementation_first_without_removing_any_legal_tool():
    editor = turn_response_schema(7)
    assert editor['oneOf'][0]['properties']['tool']['const'] == 'edit'
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
    assert len(result['records']) == 14 and all(record['ok'] for record in result['records'])
    assert result['reasoning_evidence']['requested'] is True
    assert result['reasoning_evidence']['known_nonempty_response_fields'] == 0
    assert result['all_controls_passed'] is False
    with pytest.raises(ValueError):
        require_certificate(directory / 'certificate.json', BINDING, protocol='staged-v15')


def test_raw_final_json_instruction_is_source_owned_in_planner_editor_and_controls():
    from utopia.optimization.native_staged_author_v15 import (
        FINAL_JSON_ONLY, PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT, PLAN_CONTROL_SYSTEM_PROMPT)
    assert 'without Markdown fences' in FINAL_JSON_ONLY
    for task in (PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT, PLAN_CONTROL_SYSTEM_PROMPT):
        assert FINAL_JSON_ONLY in task
    from utopia.optimization.native_designer_preflight import _prompt
    _, task = _prompt(request(), initial_draft(request()), [], BINDING,
        {'tool': 'validate'}, 'staged-v15')
    assert FINAL_JSON_ONLY in task


def test_nested_control_with_extra_closing_brace_still_rejects_without_prefix_salvage():
    from utopia.optimization.native_search_generator_v14 import _strict_json
    action = {'tool': 'edit', 'operations': [{'op': 'add', 'path': '/metadata/interface_calibration',
        'value': {'nested': {'items': [None, 1]}}}]}
    text = json.dumps(action)
    assert _strict_json(text) == action
    with pytest.raises(json.JSONDecodeError, match='Extra data'):
        _strict_json(text + '}')
