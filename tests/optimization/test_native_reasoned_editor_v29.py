"""SCRIPTED reasoning configuration boundaries, not invention evidence."""
import json

import pytest

from tests.optimization.test_native_authoring_ir import BINDING
from utopia.optimization.native_designer_decoding_v24 import decoding_contract, designer_payload
from utopia.optimization.native_designer_tools_v25 import action_from_body, response_message_from_action


@pytest.mark.parametrize('role', ['planner', 'editor'])
def test_reasoning_configuration_is_caller_owned_and_leaves_model_and_observations_unchanged(role):
    messages = [{'role': 'user', 'content': json.dumps({'think': False, 'temperature': 0,
        'model': 'untrusted-alternate-model', 'source': 'SCRIPTED observed source'})}]
    config = decoding_contract('staged-v15', role=role)
    payload = designer_payload('staged-v15', BINDING, messages, ['SCRIPTED', role],
        max_tokens=config['max_tokens'], temperature=config['temperature'], role=role)
    assert payload['model'] == BINDING['model']
    assert payload['think'] is True and payload['options']['temperature'] == .6
    assert payload['options']['num_ctx'] == 32768 and payload['options']['num_predict'] == 8192
    assert payload['messages'] == messages and payload['messages'] is not messages
    assert payload['format'] == 'json' and payload['shift'] is False and payload['truncate'] is False
    assert decoding_contract('one-shot-v14')['think'] is False
    assert decoding_contract('one-shot-v14')['temperature'] == .2


def test_separate_reasoning_never_replaces_an_invalid_final_function():
    action = {'tool': 'finish', 'rationale': 'SCRIPTED explicit retention, not a new institution'}
    message = response_message_from_action(action)
    final = message['content']
    message.update(thinking=final, content='not a JSON function')
    with pytest.raises(ValueError):
        action_from_body({'done': True, 'message': message})


def test_reasoning_never_makes_an_incomplete_known_reply_acceptable():
    action = {'tool': 'finish', 'rationale': 'SCRIPTED explicit retention'}
    message = response_message_from_action(action)
    message['thinking'] = 'SCRIPTED separate reasoning, not an action or proof of improvement'
    assert action_from_body({'done': True, 'message': message}) == action
    with pytest.raises(ValueError, match='incomplete'):
        action_from_body({'done': False, 'message': message})


def test_editor_failure_reference_reconstructs_every_exact_field_and_planner_stays_self_contained(tmp_path):
    from copy import deepcopy
    from tests.optimization.test_native_authoring_ir import request
    from tests.optimization.test_native_staged_author_v15 import Model, author
    from tests.optimization.test_native_planning_author_v22 import prompt
    from utopia.optimization.native_staged_author_v15 import SYSTEM_PROMPT, PLAN_SYSTEM_PROMPT, build_conversation
    from utopia.system.design_patch import digest
    body = request()
    definition = author(Model([{'tool': 'validate'}]), tmp_path, max_steps=1)(body)
    failure = definition['generation_failure']
    body.update(generation=1, history=[{'definition': definition,
        'generation_error': {'message': 'SCRIPTED no candidate', 'loss': None}}])
    original = deepcopy(body)
    messages = build_conversation(prompt(body), SYSTEM_PROMPT, native_tools=True)
    data, _ = json.JSONDecoder().raw_decode(messages[1]['content'].split('EXACT SESSION DATA\n', 1)[1])
    view = data['own_trial_feedback']['all_own_trials'][0]['generation_failure']
    assert view['exact_literal_reference'] == '/own_history/generation_authoring_failures/0'
    referenced = data['own_history']['generation_authoring_failures'][0]
    restored = {key: referenced[target] for key, target in view['referenced_field_map'].items()}
    assert restored == failure and digest(restored) == view['original_failure_sha256']
    assert data['own_trial_feedback']['all_own_trials'][0]['generation_error']['loss'] is None
    planner = build_conversation(prompt(body), PLAN_SYSTEM_PROMPT, native_tools=True)
    planned, _ = json.JSONDecoder().raw_decode(planner[1]['content'].split('PLANNING DATA ONLY\n', 1)[1])
    assert planned['own_trial_feedback']['all_own_trials'][0]['generation_failure'] == failure
    assert body == original


@pytest.mark.parametrize('mutation', ['unknown-field', 'wrong-hash', 'wrong-body', 'duplicate-owner'])
def test_unmatched_failure_fields_never_disappear_or_gain_a_fabricated_reference(mutation):
    from copy import deepcopy
    from utopia.optimization.native_authoring_feedback_v26 import reference_duplicate_failures
    from utopia.system.design_patch import digest
    failure = {'schema': 'SCRIPTED failure', 'reason': 'SCRIPTED unchanged', 'technical_errors': [None]}
    record = {'history_index': 0, 'failure_schema': failure['schema'],
        'reason': failure['reason'], 'technical_errors': [None], 'exact_generation_failure_sha256': digest(failure)}
    feedback = {'all_own_trials': [{'history_index': 0, 'generation_failure': failure}]}
    history = {'generation_authoring_failures': [record]}
    if mutation == 'unknown-field': failure['future_unmatched_evidence'] = {'loss': None}
    elif mutation == 'wrong-hash': record['exact_generation_failure_sha256'] = '0' * 64
    elif mutation == 'wrong-body': record['technical_errors'] = []
    else: history['generation_authoring_failures'].append(deepcopy(record))
    original = deepcopy(feedback)
    assert reference_duplicate_failures(feedback, history) == original
    assert feedback == original


def test_session_order_keeps_all_values_types_unknown_fields_and_current_state():
    from copy import deepcopy
    from utopia.optimization.native_staged_author_v15 import editor_session_json
    context = {'000_current_turn': {'remaining': 4}, 'binding_sha256': 'SCRIPTED binding',
        'own_history': {'loss': None}, 'literal_editor_workbench': {'source': 'a\n"b"\\c'},
        'future_observed_field': {'items': [False, 9007199254740993, -2.75]}, 'previous_steps': []}
    original = deepcopy(context)
    encoded = editor_session_json(context)
    assert json.loads(encoded) == context == original
    assert editor_session_json(dict(reversed(list(context.items())))) == encoded
    changed = deepcopy(context); changed['literal_editor_workbench']['source'] = 'CURRENT changed source\n'
    assert json.loads(editor_session_json(changed)) == changed
    assert json.loads(encoded)['literal_editor_workbench']['source'] != changed['literal_editor_workbench']['source']


def test_unchanged_evidence_prefix_precedes_changing_budget_without_a_stale_cached_response():
    import os
    from copy import deepcopy
    from utopia.optimization.native_staged_author_v15 import editor_session_json
    first = {'000_current_turn': {'remaining': 4}, 'binding_sha256': 'SCRIPTED',
        'own_history': {'complete_prior_failures': ['x' * 4000]},
        'literal_editor_workbench': {'source': 'SCRIPTED current source\n'}, 'previous_steps': []}
    second = deepcopy(first)
    second['000_current_turn']['remaining'] = 3
    second['previous_steps'] = [{'status': 'rejected', 'loss': None}]
    old = [json.dumps(v, sort_keys=True) for v in (first, second)]
    new = [editor_session_json(v) for v in (first, second)]
    assert len(os.path.commonprefix(new)) > 4000 > len(os.path.commonprefix(old))
    assert json.loads(new[1])['previous_steps'] == second['previous_steps']
    assert new[0] != new[1]  # no response memoization or stale budget


def test_current_native_budget_notice_remains_at_end_after_full_observed_data():
    from tests.optimization.test_native_authoring_ir import request
    from tests.optimization.test_native_planning_author_v22 import prompt
    from utopia.optimization.native_staged_author_v15 import SYSTEM_PROMPT, build_conversation, native_call_task
    messages = build_conversation(prompt(request()), SYSTEM_PROMPT, native_tools=True)
    content = messages[1]['content']
    assert content.startswith('CURRENT TURN\n\nEXACT SESSION DATA\n')
    assert content.index('EXACT SESSION DATA') < content.index('Continue the current institution-authoring session')
    assert 'budgeted calls INCLUDING this one' in content
    assert messages[-1]['content'].endswith(native_call_task(SYSTEM_PROMPT))


@pytest.mark.parametrize('value,expected,path', [
    ({'reviewed': 'not a port list'}, 'array of objects', '/mechanisms/6/outputs'),
    (['not a port object'], 'object', '/mechanisms/6/outputs/0'),
    (None, 'array of objects', '/mechanisms/6/outputs')])
def test_invalid_port_edit_stays_literal_but_static_error_identifies_exact_owner_and_shape(value, expected, path):
    from tests.optimization.test_native_authoring_ir import IMAGE, request
    from tests.optimization.test_native_staged_author_v15 import apply
    from utopia.optimization.native_staged_author_v15 import initial_draft
    from utopia.system.native_open_examples import open_native_system
    req = request(); req['parent_system'] = open_native_system(IMAGE).to_dict()
    state = initial_draft(req)
    action = {'tool': 'edit_fields', 'mechanism_id': 'world.review',
        'field_updates': [{'field_name': 'outputs', 'value': value}]}
    changed, receipt = apply(state, action, req)
    assert receipt['ok']  # Invalid intermediate graphs remain legal.
    assert changed['document']['mechanisms'][6]['outputs'] == value
    validation = receipt['result']['validation']
    assert not validation['valid']
    diagnostic = validation['errors'][0]['diagnostics'][0]
    assert diagnostic['path'] == path and diagnostic['expected_type'] == expected
    assert diagnostic['actual_owner_id'] == 'world.review' and diagnostic['operation_index'] == 0
    _, finish = apply(changed, {'tool': 'finish', 'rationale': 'SCRIPTED invalid graph'}, req)
    assert not finish['ok'] and finish['definition'] is None
