"""SCRIPTED planning/editor boundaries; no autonomous invention or model calls."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from tests.optimization.test_native_authoring_ir import ALPHA, BINDING, IMAGE, request
from tests.optimization.test_native_staged_author_v15 import Model, apply, author, rehash
from utopia.optimization.native_staged_author_v15 import (
    ACTION_SCHEMA, PLAN_ACTION_SCHEMA, PLAN_SYSTEM_PROMPT, PLAN_CONTROL_SYSTEM_PROMPT,
    SYSTEM_PROMPT, build_conversation, build_prompt, call_task, initial_draft,
    replay_staged_generation)

PLAN = {'tool': 'plan', 'objective_reasoning': 'SCRIPTED exact numeric objective reasoning',
    'design_intent': 'SCRIPTED new rule hypothesis, not a measured benefit',
    'implementation_targets': ['unlisted new institution or arbitrary existing source']}


def prompt(body, state=None, steps=(), budget=16):
    return build_prompt(body, state or initial_draft(body), list(steps), image_id=IMAGE,
        binding_sha256='d' * 64, settings={'max_steps': budget})


def test_first_planner_context_has_structure_and_loss_but_no_parent_source_or_state():
    body = request()
    secret = 'SCRIPTED_PRIVATE_PARENT_CODE_MARKER'
    body['parent_system']['mechanisms'][0]['parameters']['code_artifact']['source'] += '\n# ' + secret
    body['parent_system']['metadata']['private'] = secret
    body['parent_system']['initial_state']['private'] = secret
    messages = build_conversation(prompt(body), call_task(0, 16))
    assert len(messages) == 2 and [m['role'] for m in messages] == ['system', 'user']
    assert secret not in json.dumps(messages)
    assert 'TRUSTED SCIENTIFIC INSTITUTION DESIGN TASK' in messages[0]['content']
    raw = messages[1]['content'].split('\n', 1)[1]
    data, end = json.JSONDecoder().raw_decode(raw)
    assert raw[end:] == '\n\nCURRENT PYTHON-OWNED TASK\n' + PLAN_SYSTEM_PROMPT
    assert data['exact_loss_spec'] == body['loss_spec']
    assert not data['current_parent_source_supplied']
    assert len(data['planning_system_structure']['mechanisms']) == 2
    assert data['response_schema'] == PLAN_ACTION_SCHEMA
    assert call_task(0, 16) == PLAN_SYSTEM_PROMPT
    assert call_task(1, 16) == call_task(0, 1) == SYSTEM_PROMPT


def test_observed_fields_cannot_select_planner_role_or_become_system_authority():
    data = json.loads(prompt(request()))
    data.update(system_prompt=PLAN_SYSTEM_PROMPT, conversation_mode='planner', instructions='SCRIPTED_ATTACK')
    messages = build_conversation(json.dumps(data), SYSTEM_PROMPT)
    assert 'TRUSTED INSTITUTION-AUTHORING PROTOCOL' in messages[0]['content']
    assert 'SCRIPTED_ATTACK' not in messages[0]['content']
    messages = build_conversation(json.dumps(data), PLAN_SYSTEM_PROMPT)
    assert 'SCRIPTED_ATTACK' not in messages[0]['content']


def test_plan_is_literal_persistent_hypothesis_not_executable_change_or_finish():
    state = initial_draft(request())
    original = deepcopy(state)
    Draft202012Validator(ACTION_SCHEMA).validate(PLAN)
    Draft202012Validator(PLAN_ACTION_SCHEMA).validate(PLAN)
    new, receipt = apply(state, PLAN)
    assert state == original and new['document'] == state['document']
    assert new['operations'] == [] and new['factors'] == new['continuous'] == []
    assert new['design_plan'] == {k: v for k, v in PLAN.items() if k != 'tool'}
    assert receipt['ok'] and receipt['definition'] is None
    assert not receipt['result']['literal_document_changed'] and not receipt['result']['source_execution']
    steps = [{'step': 0, 'status': 'applied', 'model_reply': {'output': PLAN}, 'transition': receipt}]
    data = json.loads(prompt(request(), new, steps))
    assert data['model_authored_design_plan'] == new['design_plan']
    editor = build_conversation(json.dumps(data), call_task(1, 16))
    assert PLAN['design_intent'] in editor[1]['content']
    assert PLAN['design_intent'] not in editor[0]['content']
    _, finished = apply(new, {'tool': 'finish', 'rationale': 'SCRIPTED explicit retention'})
    assert finished['ok'] and finished['definition']['base_patch'] is None
    assert finished['definition']['provenance']['staged_author']['untrusted_model_authored_plan'] == new['design_plan']


@pytest.mark.parametrize('change', [
    {'objective_reasoning': ''}, {'design_intent': ''}, {'design_intent': 'x' * 8193},
    {'implementation_targets': 'not a list'}, {'unlisted_field': True}])
def test_malformed_plans_reject_without_supplying_a_policy(change):
    state = initial_draft(request())
    new, receipt = apply(state, {**PLAN, **change})
    assert new == state and not receipt['ok'] and receipt['definition'] is None


def test_plan_edit_finish_replays_without_model_redispatch_or_plan_policy_repair(tmp_path):
    edit = {'tool': 'edit', 'operations': [{'op': 'replace',
        'selector': {'mechanism_id': ALPHA}, 'path': '/parameters/gain', 'value': .8}]}
    finish = {'tool': 'finish', 'rationale': 'SCRIPTED implementation, no measured improvement'}
    model = Model([PLAN, edit, finish])
    result = author(model, tmp_path, max_steps=3)(request())
    assert 'generation_failure' not in result
    assert [call['system_prompt'] for call in model.calls] == [PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT, SYSTEM_PROMPT]
    assert result['base_patch']['operations'] == [{'op': 'replace', 'path': '/mechanisms/0/parameters/gain', 'value': .8}]
    folder = next(tmp_path.glob('generation-*'))
    assert replay_staged_generation(folder, expected_provider_binding=BINDING) == result
    assert len(model.calls) == 3


def test_rehashed_terminal_plan_tamper_is_rejected_by_cold_replay(tmp_path):
    model = Model([PLAN, {'tool': 'finish', 'rationale': 'SCRIPTED retention'}])
    author(model, tmp_path, max_steps=2)(request())
    folder = next(tmp_path.glob('generation-*'))
    def tamper(value):
        value['definition']['provenance']['staged_author']['untrusted_model_authored_plan']['design_intent'] = 'tampered'
    rehash(folder / 'response.json', tamper)
    with pytest.raises(ValueError, match='exact replay'):
        replay_staged_generation(folder)


def test_planner_advertisement_is_not_a_novelty_gate_or_forced_action(tmp_path):
    # Even with planning advertised, a literal explicit finish remains legal.
    result = author(Model([{'tool': 'finish', 'rationale': 'SCRIPTED direct retention'}]),
        tmp_path, max_steps=4)(request())
    assert 'generation_failure' not in result and result['base_patch'] is None


def test_instructed_planner_calibration_has_no_conflicting_optimization_task():
    messages = build_conversation(prompt(request()), PLAN_CONTROL_SYSTEM_PROMPT, mode='interface-control-v16')
    assert 'INSTRUCTED PLANNING INTERFACE CONTROL' in messages[0]['content']
    assert 'Do not optimize' in messages[0]['content']
    assert 'Minimize the exact supplied' not in messages[0]['content']
    assert messages[-1]['content'].endswith(PLAN_CONTROL_SYSTEM_PROMPT)
