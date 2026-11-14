"""SCRIPTED combined editor interaction, not native integration/readiness."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_authoring_ir import BINDING, IMAGE
from tests.optimization.test_native_author_long_rationale_v1 import note, write_action
from tests.optimization.test_native_bounded_author_context_v45 import Model
from tests.optimization.test_native_common_metric_semantics_v1 import utility_request
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.optimization.native_staged_author_v15 import (
    StagedVocabularyGenerator, replay_staged_generation,
)


@pytest.fixture(autouse=True)
def forbid_execution_and_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('combined editor checks must not execute code or use a network')
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)
    monkeypatch.setattr('requests.sessions.Session.request', forbidden)


def test_long_note_edit_keeps_inline_utility_literal_archive_and_cold_replay(tmp_path):
    body = utility_request()
    before = deepcopy(body)
    edit = {**write_action(body), 'rationale': note(16081)}
    actions = [
        {'tool': 'plan', 'objective_reasoning': 'SCRIPTED interaction, not optimization',
         'design_intent': 'Preserve the literal test edit and non-executable note'},
        edit,
        {'tool': 'finish', 'rationale': 'SCRIPTED explicit submission'},
    ]
    model = Model(deepcopy(actions))
    author = StagedVocabularyGenerator(model, tmp_path/'author', image_id=IMAGE,
        provider_binding=BINDING, max_steps=8, max_tokens=8192,
        conversation_profile=BOUNDED_AUTHORING)
    result = author(body)
    assert 'generation_failure' not in result and len(model.calls) == 3
    assert body == before
    directory = next((tmp_path/'author').glob('generation-*'))
    step = json.loads((directory/'step-01.completed.json').read_text())
    assert step['status'] == 'applied' and step['model_reply']['output'] == edit
    assert step['transition']['untrusted_author_annotations']['rationale'] == edit['rationale']
    metric = 'native.common_content_utility_sum'
    for call in model.calls:
        prompt = json.loads(call['prompt'])
        arithmetic = prompt['loss_arithmetic']
        assert arithmetic['metrics_without_text_definition'] == []
        assert 'subtract 3' in arithmetic['measurement_definitions'][metric]
        assert arithmetic['per_run'] == body['loss_spec']['per_run']
    final_frame = json.loads(model.calls[-1]['prompt'])
    assert final_frame['completed_steps'][1]['status'] == 'applied'
    binding = json.loads((directory/'request.json').read_text())
    assert binding['request'] == body
    original_bytes = {p.name: p.read_bytes() for p in directory.glob('*.json')}
    assert replay_staged_generation(directory, expected_provider_binding=BINDING) == result
    assert len(model.calls) == 3
    assert original_bytes == {p.name: p.read_bytes() for p in directory.glob('*.json')}
