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
