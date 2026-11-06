"""SCRIPTED metadata observations; no actual model load or inference."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from tests.optimization.test_native_designer_contract_v16 import Response
from tests.optimization.test_native_designer_roles_v38 import designer_binding
from tests.optimization.test_native_search_v14 import BINDING
from utopia.optimization.native_loaded_roles_v38 import (
    SCIENTIST_DIGEST, LocalRoleBoundNativeFactory, record_loaded_context, replay_loaded_context,
)
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.system.design_patch import digest


def bindings():
    scientist = {**deepcopy(BINDING), 'model_digest': SCIENTIST_DIGEST}
    return {'scientist': scientist, 'designer': designer_binding()}


class Session:
    def __init__(self, models=None, error=None):
        self.models = models if models is not None else [
            {'name': b['model'], 'digest': b['model_digest'], 'context_length': 40960}
            for b in bindings().values()]
        self.error, self.calls = error, []
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return Response({'models': self.models})
    def post(self, *a, **k):
        pytest.fail('metadata observation itself must never load or generate')


def test_both_contexts_exactly_observed_and_cold_replayed_without_new_calls(tmp_path):
    session = Session(); path = tmp_path / 'gate.json'
    record = record_loaded_context(path, expected=bindings(), purpose='SCRIPTED', session=session)
    assert record['valid'] and record['checks'] == {'scientist': True, 'designer': True}
    assert record['response_payload'] == json.loads(record['raw_http_response'])
    assert replay_loaded_context(json.loads(path.read_text()), expected=bindings(), purpose='SCRIPTED')
    assert len(session.calls) == 1
    assert record['new_generation_POSTs'] == record['automatic_loads'] == 0
    before = path.read_bytes()
    with pytest.raises(ValueError, match='never overwrite'):
        record_loaded_context(path, expected=bindings(), purpose='SCRIPTED', session=session)
    assert path.read_bytes() == before and len(session.calls) == 1


@pytest.mark.parametrize('change', [
    lambda m: m.pop(), lambda m: m[0].update(context_length=32768),
    lambda m: m[0].update(context_length=True),
    lambda m: m[1].update(digest='0' * 64),
    lambda m: m.append(deepcopy(m[0])),
])
def test_missing_wrong_or_duplicate_context_rejects_and_keeps_exact_observation(tmp_path, change):
    session = Session(); change(session.models)
    path = tmp_path / 'failed.json'
    with pytest.raises(ValueError, match='absent, wrong or unknown'):
        record_loaded_context(path, expected=bindings(), purpose='SCRIPTED', session=session)
    record = json.loads(path.read_text())
    assert not record['valid'] and len(session.calls) == 1
    assert not replay_loaded_context(record, expected=bindings(), purpose='SCRIPTED')


def test_transport_error_is_unknown_not_a_false_loaded_model_or_zero_time(tmp_path):
    session = Session(error=TimeoutError('SCRIPTED metadata unavailable'))
    path = tmp_path / 'unknown.json'
    with pytest.raises(ValueError):
        record_loaded_context(path, expected=bindings(), purpose='SCRIPTED', session=session)
    record = json.loads(path.read_text())
    assert record['error'].startswith('TimeoutError:')
    assert 'response_payload' not in record and 'raw_http_response' not in record
    assert record['checks'] == {'scientist': False, 'designer': False}
    assert record['elapsed_seconds'] >= 0
    assert not replay_loaded_context(record, expected=bindings(), purpose='SCRIPTED')


@pytest.mark.parametrize('change', [
    lambda d: d.update(checks={'scientist': False, 'designer': True}),
    lambda d: d.update(valid=False), lambda d: d.update(automatic_loads=True),
    lambda d: d.update(metadata_GET_attempts=True),
    lambda d: d.update(elapsed_seconds=-1),
    lambda d: d['response_payload']['models'][0].update(context_length=1),
])
def test_rehashed_outcome_raw_body_or_cost_tampering_is_still_rejected(tmp_path, change):
    record = record_loaded_context(tmp_path / 'gate.json', expected=bindings(), purpose='SCRIPTED', session=Session())
    change(record)
    record['content_sha256'] = digest({k: v for k, v in record.items() if k != 'content_sha256'})
    with pytest.raises(ValueError):
        replay_loaded_context(record, expected=bindings(), purpose='SCRIPTED')


def test_no_vacuous_or_changed_scientist_expectation_can_pass_without_a_read(tmp_path):
    for expected in ({}, {'unknown-role': designer_binding()},
            {'scientist': {**bindings()['scientist'], 'model_digest': '0' * 64}}):
        session = Session()
        with pytest.raises(ValueError):
            record_loaded_context(tmp_path / 'never.json', expected=expected, purpose='SCRIPTED', session=session)
        assert session.calls == []
    assert not (tmp_path / 'never.json').exists()


def test_world_guard_requires_same_loaded_scientist_without_changing_its_payload(tmp_path, monkeypatch):
    expected = bindings(); calls = []
    def init(self, directory, *args, **kwargs):
        self.directory = Path(directory)
        self.__dict__.update({k: v for k, v in expected['scientist'].items() if k != 'image_id'})
    def execute(self, spec, seed, run_id):
        calls.append((spec, seed, run_id))
        return 'SCRIPTED untouched native factory delegation'
    monkeypatch.setattr(LocalQwenNativeFactory, '__init__', init)
    monkeypatch.setattr(LocalQwenNativeFactory, '__call__', execute)
    class LoadSession(Session):
        def post(self, url, **kwargs):
            assert url.endswith('/api/generate') and json.loads(kwargs['data'])['prompt'] == ''
            return Response({'model':'qwen3:8b','done':True,'done_reason':'load'})
    session = LoadSession()
    monkeypatch.setattr('requests.Session', lambda: session)
    factory = LocalRoleBoundNativeFactory(tmp_path, tmp_path / 'data', designer_provider=expected['designer'])
    assert factory('SCRIPTED-spec', 42, 'native-run') == 'SCRIPTED untouched native factory delegation'
    assert calls == [('SCRIPTED-spec', 42, 'native-run')]
    gate = json.loads((tmp_path / 'native-run/loaded-role-context-000.json').read_text())
    assert gate['expected'] == {'scientist': expected['scientist']}
    assert gate['valid'] and len(session.calls) == 1
    session.models[0]['context_length'] = 4096
    with pytest.raises(ValueError, match='absent, wrong or unknown'):
        factory('SCRIPTED-another', 42, 'native-other')
    assert len(calls) == 1 and len(session.calls) == 2
    assert not (tmp_path / 'native-other/system.json').exists()
