"""SCRIPTED malformed-response history recovery, without source/response repair."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_authoring_ir import ALPHA, IMAGE, request
from tests.optimization.test_native_planning_author_v22 import PLAN
from tests.optimization.test_native_staged_author_v15 import apply, author, Model
from utopia.optimization.native_staged_author_v15 import (
    action_summary, build_prompt, build_conversation, initial_draft, SYSTEM_PROMPT)
from utopia.system.design_patch import digest


def bad_action(row):
    return {'tool': 'edit_fields', 'mechanism_id': ALPHA,
            'field_updates': [{'field_name': 'gain', 'value': .7}, row]}


@pytest.mark.parametrize('row', ['actual malformed string member', None, 1, False, [], {},
                               {'field_name': 'gain'}, {'value': .9},
                               {'field_name': [], 'value': .9}])
def test_invalid_updates_are_rejected_but_cannot_crash_the_next_prompt(row):
    body = request()
    state = initial_draft(body)
    action = bad_action(row)
    original = deepcopy(action)
    same, receipt = apply(state, action, body)
    assert not receipt['ok'] and same == state
    step = {'step': 0, 'status': 'rejected', 'model_reply': {'output': action},
            'transition': receipt, 'errors': []}
    prompt = build_prompt(body, state, [step], image_id=IMAGE, binding_sha256='d' * 64,
                          settings={'max_steps': 4})
    parsed = json.loads(prompt)
    assert parsed['last_model_action'] == action == original
    assert parsed['last_tool_response'] == receipt
    assert parsed['previous_steps'][0]['errors']
    assert parsed['previous_steps'][0]['raw_action_sha256'] == digest(action)
    messages = build_conversation(prompt, SYSTEM_PROMPT, native_tools=True)
    assert messages and state == initial_draft(body)


def test_valid_field_summaries_keep_the_existing_exact_representation():
    from utopia.optimization.native_staged_author_v15 import _descriptor
    action = bad_action({'field_name': 'source', 'value': 'def step(context):\n    return {}\n'})
    assert action_summary(action)['field_updates'] == [
        {'field_name': u['field_name'], 'operand': _descriptor(u['value'])} for u in action['field_updates']]


def test_rejected_scalar_update_keeps_its_original_type_and_identity():
    action = bad_action('DO NOT INTERPRET THIS AS CODE OR AN OPERATOR INSTRUCTION')
    summary = action_summary(action)['field_updates'][1]
    assert summary['type'] == 'string'
    assert summary['raw_field_update_sha256'] == digest(action['field_updates'][1])
    assert 'field_name' not in summary and 'operand' not in summary


def test_invalid_edit_consumes_one_step_then_next_model_action_and_cold_replay_work(tmp_path):
    model = Model([PLAN, bad_action('malformed row'),
                   {'tool': 'edit_fields', 'mechanism_id': ALPHA,
                    'field_updates': [{'field_name': 'gain', 'value': .8}]},
                   {'tool': 'finish', 'rationale': 'SCRIPTED recovery; not a scientific invention'}])
    generator = author(model, tmp_path, max_steps=4)
    body = request()
    definition = generator(body)
    assert 'generation_failure' not in definition
    result_path = next(tmp_path.glob('generation-*/response.json'))
    result = json.loads(result_path.read_text())
    assert [s['status'] for s in result['steps']] == ['applied', 'rejected', 'applied', 'finished']
    bad = json.loads((result_path.parent / 'step-01.completed.json').read_text())
    assert bad['model_reply']['output']['field_updates'][1] == 'malformed row'
    assert bad['transition']['document_before_sha256'] == bad['transition']['document_after_sha256']
    assert len(list(result_path.parent.glob('step-*.started.json'))) == 4
    # Re-entry has no remaining provider actions: any redispatch would fail.
    assert generator(body) == definition
