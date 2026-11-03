"""SCRIPTED model authoring/transport units, not Qwen or scientific results."""
from dataclasses import replace
import json

import pytest

from tests.optimization.test_native_adaptive_search import tiny_parent, loss_spec
from utopia.optimization.native_search_generator_v14 import (
    LLMVocabularyGenerator, LocalQwenDesignerModel, compile_authored_output,
    build_prompt, _strict_json)
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest

IMAGE = 'sha256:' + 'a' * 64
BINDING = {'model': 'qwen3:8b', 'model_digest': 'b' * 64, 'image_id': IMAGE}


def request():
    return {'parent_system': tiny_parent().to_dict(), 'loss_spec': loss_spec(),
            'rng_seed': 42, 'count': 1, 'generation': 0, 'observations': [], 'history': []}


def output():
    return {'operations': [{'op': 'replace', 'path': '/initial_state/coordinate', 'value': 1.25}],
            'factors': [], 'continuous': [], 'rationale': 'SCRIPTED technical fixture only'}


class Model:
    def __init__(self, values):
        self.values, self.calls = iter(values), []

    def generate(self, **kwargs):
        self.calls.append(clone(kwargs))
        value = next(self.values)
        if isinstance(value, BaseException):
            raise value
        if isinstance(value, tuple):
            parsed, raw = value
        else:
            parsed, raw = value, json.dumps(value)
        return parsed, [{'role': 'assistant', 'content': raw}]


def author(model, path, **kwargs):
    return LLMVocabularyGenerator(model, path, image_id=IMAGE, provider_binding=BINDING, **kwargs)


def result_path(path):
    return next(path.glob('generation-*/response.json'))


def rehash(path):
    value = json.loads(path.read_text())
    value['content_sha256'] = digest({k: v for k, v in value.items() if k != 'content_sha256'})
    path.write_text(json.dumps(value))


def test_exact_model_edits_and_cold_cached_response_no_more_calls(tmp_path):
    model = Model([output()])
    definition = author(model, tmp_path)(request())
    assert definition['base_patch']['operations'] == output()['operations']
    assert definition['provenance']['authored_output_sha256'] == digest(output())
    assert len(model.calls) == 1
    no_calls = Model([])
    assert author(no_calls, tmp_path)(request()) == definition
    assert no_calls.calls == []
    receipt = json.loads(result_path(tmp_path).read_text())
    assert receipt['status'] == 'generated' and receipt['selected_attempt'] == 0


def test_arbitrary_new_python_body_and_graph_are_compiled_not_executed():
    value = output()
    source = 'def step(context):\n    raise RuntimeError("NEVER_EXECUTE_ON_HOST")\n'
    node = {'mechanism_id': 'new-unlisted-institution', 'family': 'custom', 'implementation': 'code.python.v1',
        'version': 1, 'inputs': [], 'outputs': [],
        'parameters': {'runtime_image_id': IMAGE, 'code_artifact': {
            'schema': 'scienceutopia.code-mechanism.v1', 'label': 'new-institution',
            'source': source, 'inputs': {}, 'outputs': {}, 'state_schema': {'type': 'object'}}}}
    value['operations'] = [{'op': 'add', 'path': '/mechanisms/-', 'value': node},
        {'op': 'add', 'path': '/schedules/-', 'value': {
            'mechanism_id': node['mechanism_id'], 'phase': 1, 'trigger': 'annual'}}]
    definition = compile_authored_output(request(), value, binding_sha256='c' * 64, provider_binding=BINDING)
    assert definition['base_patch']['operations'][0]['value']['parameters']['code_artifact']['source'] == source
    assert definition['factors'] == []
    value['operations'][0]['value']['parameters']['runtime_image_id'] = 'sha256:' + 'f' * 64
    with pytest.raises(ValueError, match='pinned operator sandbox'):
        compile_authored_output(request(), value, binding_sha256='c' * 64, provider_binding=BINDING)


def test_invalid_first_attempt_gets_model_feedback_without_host_repair(tmp_path):
    invalid = output()
    invalid['operations'][0]['path'] = '/absent/value'
    model = Model([invalid, output()])
    result = author(model, tmp_path)(request())
    assert result['base_patch']['operations'] == output()['operations']
    assert len(model.calls) == 2
    second = json.loads(model.calls[1]['prompt'])
    assert second['technical_feedback_from_previous_attempts']
    receipt = json.loads(result_path(tmp_path).read_text())
    assert receipt['selected_attempt'] == 1
    assert [v['status'] for v in receipt['attempts']] == ['invalid', 'valid']


def test_exhaustion_is_invalid_vocabulary_not_silent_retention(tmp_path):
    model = Model([{'bad': 1}, {'bad': 2}])
    definition = author(model, tmp_path)(request())
    assert set(definition) == {'generation_failure'}
    assert len(model.calls) == 2
    receipt = json.loads(result_path(tmp_path).read_text())
    assert receipt['status'] == 'generation-failed' and receipt['selected_attempt'] is None
    assert author(Model([]), tmp_path)(request()) == definition


def test_explicit_model_identity_is_legal_not_a_novelty_gate(tmp_path):
    value = output()
    value['operations'] = []
    definition = author(Model([value]), tmp_path)(request())
    assert definition['base_patch'] is None
    assert definition['provenance']['kind'] == 'automatic-local-LLM-v14'


def test_process_interruption_consumes_started_attempt_without_redispatch(tmp_path):
    with pytest.raises(KeyboardInterrupt):
        author(Model([KeyboardInterrupt()]), tmp_path)(request())
    model = Model([output()])
    definition = author(model, tmp_path)(request())
    assert len(model.calls) == 1 and definition['base_patch'] is not None
    receipt = json.loads(result_path(tmp_path).read_text())
    assert [v['status'] for v in receipt['attempts']] == ['interrupted-response-unknown', 'valid']
    assert receipt['attempts'][0]['completed_sha256'] is None
    assert author(Model([]), tmp_path)(request()) == definition


@pytest.mark.parametrize('raw', ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}'])
def test_duplicate_and_nonfinite_json_rejected(raw):
    with pytest.raises(ValueError):
        _strict_json(raw)


def test_raw_reply_must_equal_generated_parsed_value(tmp_path):
    model = Model([(output(), '{}'), output()])
    author(model, tmp_path)(request())
    receipt = json.loads(result_path(tmp_path).read_text())
    assert receipt['attempts'][0]['status'] == 'invalid'


def test_nonfinite_generic_provider_output_is_durably_failed_not_serialized_as_penalty(tmp_path):
    model = Model([({'bad': float('inf')}, '{"bad":1e999}'), output()])
    author(model, tmp_path)(request())
    first = json.loads((result_path(tmp_path).parent / 'attempt-00.completed.json').read_text())
    assert first['status'] == 'invalid' and first['model_reply']['output'] is None
    assert first['model_reply']['messages'][-1]['content'] == '{"bad":1e999}'
    assert first['definition'] is None


def test_rehashed_result_cannot_replace_selected_source_definition(tmp_path):
    author(Model([output()]), tmp_path)(request())
    path = result_path(tmp_path)
    value = json.loads(path.read_text())
    value['definition']['base_patch']['operations'][0]['value'] = 2.75
    path.write_text(json.dumps(value))
    rehash(path)
    with pytest.raises(ValueError, match='selected definition'):
        author(Model([]), tmp_path)(request())


def test_rehashed_prompt_and_receipts_still_require_exact_prompt_reconstruction(tmp_path):
    author(Model([output()]), tmp_path)(request())
    path = result_path(tmp_path)
    directory = path.parent
    started_path = directory / 'attempt-00.started.json'
    started = json.loads(started_path.read_text())
    started['prompt'] += 'foreign instructions'
    started['prompt_sha256'] = digest(started['prompt'])
    started_path.write_text(json.dumps(started))
    # Response-chain hashes need not be updated: either independent protection
    # must reject. The protocol's read-only audit independently rebuilds prompts.
    with pytest.raises(ValueError, match='sequence or prompt'):
        author(Model([]), tmp_path)(request())


def test_settings_or_operator_model_binding_cannot_change_at_resume(tmp_path):
    author(Model([output()]), tmp_path)(request())
    with pytest.raises(ValueError, match='changed'):
        author(Model([]), tmp_path, max_attempts=3)(request())
    with pytest.raises(ValueError, match='image binding'):
        LLMVocabularyGenerator(Model([]), tmp_path, image_id='sha256:' + 'c' * 64, provider_binding=BINDING)


def test_prompt_preserves_every_own_scalar_outcome_null_failure_and_update():
    value = request()
    value['observations'] = [
        {'suggestion': {'candidate': tiny_parent().to_dict()}, 'observation': {
            'observation_id': 'observed-' + str(i), 'status': 'failed' if cost is None else 'complete',
            'loss': cost, 'metadata': {'measurements': [], 'technical_failures': ['failure'] if cost is None else []}}}
        for i, cost in enumerate([1., None, 1., -2.])]
    value['history'] = [{'report': {'gradient': [0.1], 'weights_before': [0.], 'weights_after': [-.01]},
                         'generation_error': None}]
    prompt = json.loads(build_prompt(value, image_id=IMAGE, errors=[]))
    assert [v['loss'] for v in prompt['own_history']['all_observations']] == [1., None, 1., -2.]
    assert prompt['own_history']['all_stages'][0]['report'] == value['history'][0]['report']
    assert prompt['parent_system'] == value['parent_system']


def test_local_transport_is_one_fixed_loopback_post_without_proxy_or_retries(monkeypatch):
    calls = []
    class Response:
        status_code = 200
        def __init__(self, body):
            self.body, self.text = body, json.dumps(body)
        def raise_for_status(self):
            pass
        def json(self):
            return self.body
    class Session:
        trust_env = True
        def get(self, url, **kwargs):
            calls.append(('GET', url))
            assert self.trust_env is False
            return Response({'models': [{'name': 'qwen3:8b', 'digest': BINDING['model_digest']}]})
        def post(self, url, **kwargs):
            calls.append(('POST', url))
            assert kwargs['json']['think'] is False and kwargs['json']['stream'] is False
            return Response({'message': {'content': json.dumps(output())}, 'done': True,
                'done_reason': 'stop', 'prompt_eval_count': 123, 'eval_count': 45})
    monkeypatch.setattr('requests.Session', Session)
    model = LocalQwenDesignerModel(BINDING)
    parsed, messages = model.generate(prompt='SCRIPTED prompt', system_prompt='fixture',
        seed_ctx=('test',), max_tokens=512, temperature=.2,
        response_format={'json_object': {'schema': {'type': 'object'}}})
    assert parsed == output()
    assert calls == [('GET', 'http://127.0.0.1:11434/api/tags'), ('POST', 'http://127.0.0.1:11434/api/chat')]
    assert model.last_transport['network_retries'] == 0
    assert model.last_transport['completion_tokens'] == 45
    assert messages[-1]['role'] == 'assistant'
