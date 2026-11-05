"""SCRIPTED regression for the contradictory task. Not autonomous invention."""
import json

import pytest

from tests.optimization.test_native_authoring_ir import ALPHA, BINDING, request
from tests.optimization.test_native_staged_author_v15 import apply
from utopia.optimization.native_staged_author_v15 import build_conversation, build_prompt, initial_draft


@pytest.mark.parametrize('completed_turns', [0, 1])
def test_every_author_turn_permits_invention_but_forbids_fabricated_measurements(completed_turns):
    body = request()
    state = initial_draft(body)
    action = {'tool': 'inspect', 'path': ''}
    _, receipt = apply(state, action, body)
    steps = [{'step': 0, 'status': 'applied', 'model_reply': {'output': action}, 'transition': receipt}] * completed_turns
    prompt = build_prompt(body, state, steps, image_id=BINDING['image_id'], binding_sha256='d' * 64,
        settings={'max_steps': 16})
    messages = build_conversation(prompt, 'Return the next tool action')
    assert 'You may invent arbitrary literal Python' in messages[0]['content']
    for message in messages:
        assert 'do not invent a candidate' not in message['content']
    assert 'You may invent new candidate code and institutions' in messages[-1]['content']
    assert 'do not fabricate measured outcomes' in messages[-1]['content']
    assert 'Explicit retention is legal' in messages[-1]['content']


def test_literal_changed_source_and_explicit_retention_are_both_still_legal():
    body = request()
    state = initial_draft(body)
    source = state['document']['mechanisms'][0]['parameters']['code_artifact']['source']
    changed_source = source.replace('return {"outputs": {}, "state": {}}',
        'return {"outputs": {}, "state": {"SCRIPTED_new_state": True}}')
    changed, receipt = apply(state, {'tool': 'edit', 'operations': [{
        'op': 'replace', 'selector': {'mechanism_id': ALPHA},
        'path': '/parameters/code_artifact/source', 'value': changed_source}]}, body)
    assert receipt['ok'] and receipt['result']['literal_document_changed']
    assert changed['document']['mechanisms'][0]['parameters']['code_artifact']['source'] == changed_source
    for draft in (state, changed):
        _, finish = apply(draft, {'tool': 'finish', 'rationale': 'SCRIPTED boundary test'}, body)
        assert finish['ok'] and finish['definition'] is not None
    assert json.loads(build_prompt(body, state, [], image_id=BINDING['image_id'],
        binding_sha256='d' * 64, settings={'max_steps': 16}))['draft_index']['applied_operation_count'] == 0
