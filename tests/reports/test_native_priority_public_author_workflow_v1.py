"""Light staged canaries for the future public proof; no model/native/Docker.

The public native driver remains unexecuted here. Exact real native documents,
prescribed author actions, actual saved request envelopes and cold author replay
exercise the same action builder/checker consumed by that opt-in public path.
"""
import json
from pathlib import Path

import pytest

from tests.optimization.test_native_authoring_ir import request
from tests.optimization import test_native_json_history_v40 as dialogue
from tests.optimization.test_native_bounded_author_context_v45 import Model
from tests.reports.test_native_priority_method_public_v1 import (
    prescribed_author_actions, checked_actual_workflow,
)
from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator, replay_staged_generation
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.system.design_patch import clone

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/native_author_context_boundary_v1'


@pytest.fixture(autouse=True)
def no_models_native_or_generated_code(monkeypatch):
    def forbidden(*a, **kw): pytest.fail('light canary cannot call real models or generated code')
    monkeypatch.setattr('requests.Session.post', forbidden)
    monkeypatch.setattr('openai.OpenAI.__init__', forbidden)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)


@pytest.mark.parametrize('name', ['parent-zero', 'parent-terminal', 'after-feature-write'])
def test_same_public_prescribed_actions_reach_both_checkpoints_and_cold_saved_envelopes(tmp_path, monkeypatch, name):
    body = request(); body['parent_system'] = json.loads((FIXTURES / (name + '.json')).read_text())
    body['generation'] = 0
    image = next(n['parameters']['runtime_image_id'] for n in body['parent_system']['mechanisms']
                 if n['implementation'] == 'code.python.v1')
    binding = {**dialogue.BINDING, 'image_id': image}; monkeypatch.setattr(dialogue, 'BINDING', binding)
    actions = prescribed_author_actions(body)
    assert [a['tool'] for a in actions] == ['plan', *(['read_file'] * 3), 'edit', *(['read_file'] * 3), 'finish']
    # DialogueModel consumes its private queue with pop(0); retain the expected
    # public canary list independently rather than asserting on the emptied queue.
    model = Model(clone(actions))
    generator = StagedVocabularyGenerator(model, tmp_path / 'author', image_id=image,
        provider_binding=binding, max_steps=16, max_tokens=8192, conversation_profile=BOUNDED_AUTHORING)
    result = generator(body)
    assert 'generation_failure' not in result and len(model.calls) == len(actions) == 9
    directory = next((tmp_path / 'author').glob('generation-*'))
    rows = []
    for i in range(len(actions)):
        step = json.loads((directory / f'step-{i:02d}.completed.json').read_text())
        assert step['status'] == ('finished' if i == 8 else 'applied')
        payload = step['model_reply']['transport']['request_payload']
        rows.append(checked_actual_workflow(payload, step=i, request=body))
    assert rows[4]['recorded_phase'] == rows[8]['recorded_phase'] == 'implementation'
    assert rows[4]['inspection_attempts'] == rows[8]['inspection_attempts'] == 3
    assert rows[5]['inspection_attempts'] == 0 and rows[5]['recorded_phase'] == 'general'
    assert rows[8]['whole_document_actually_supplied']
    assert rows[8]['compact_document_utf8_bytes'] > rows[4]['compact_document_utf8_bytes']
    before = {f.name: f.read_bytes() for f in directory.glob('*.json')}
    assert replay_staged_generation(directory) == result
    assert before == {f.name: f.read_bytes() for f in directory.glob('*.json')}
    # The checker must reject the actual diagnosed contradiction, not merely
    # count serializer sizes while accepting an old general-phase frame.
    payload = json.loads((directory / 'step-04.completed.json').read_text())['model_reply']['transport']['request_payload']
    marker = 'BOUNDED ACTIVE SESSION DATA\n'
    modified = clone(payload)
    message = next(m for m in modified['messages'] if m['role'] == 'user' and m['content'].startswith(marker))
    data, offset = json.JSONDecoder().raw_decode(message['content'].split('\n', 1)[1])
    suffix = message['content'].split('\n', 1)[1][offset:]
    data['000_current_turn']['authoring_workflow']['phase'] = 'general'
    message['content'] = marker + json.dumps(data, ensure_ascii=False) + suffix
    with pytest.raises(AssertionError, match='actual body/phase mismatch'):
        checked_actual_workflow(modified, step=4, request=body)


def test_actions_are_fresh_and_do_not_mutate_the_measured_parent():
    body = request(); body['parent_system'] = json.loads((FIXTURES / 'parent-terminal.json').read_text())
    body['generation'] = 0; before = clone(body)
    a, b = prescribed_author_actions(body), prescribed_author_actions(body)
    assert a == b and body == before
    a[1]['filename'] = 'SCRIPTED changed local test list'
    assert b[1]['filename'] == 'system.json' and body == before


def test_checker_rejects_missing_literal_active_backend_frame():
    with pytest.raises(AssertionError, match='one literal active-session backend message'):
        checked_actual_workflow({'messages': [{'role': 'user', 'content': 'SCRIPTED no frame'}]},
            step=0, request=request())
