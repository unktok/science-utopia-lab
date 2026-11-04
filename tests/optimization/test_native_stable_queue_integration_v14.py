"""SCRIPTED production-helper/HTTP/queue integration; no model/native forwards."""
import importlib.util
import json
from pathlib import Path
import threading

import pytest
import requests

from tests.optimization.test_native_search_generator_v14 import Model
from tests.optimization.test_native_search_v14 import BINDING, REVISION, FailedFactory, request
from utopia.optimization.native_jobs import NativeJobQueue
from utopia.optimization.native_search_generator_v14 import make_local_vocabulary_generator
from utopia.optimization.native_search_jobs_v14 import NativeSearchQueue
from utopia.runtime.checkpointing import PortableStop
from utopia.system.design_patch import digest
from utopia.system.native_open_examples import open_native_system


@pytest.fixture(autouse=True)
def scripted_certificate_boundary(monkeypatch):
    # These tests explicitly replace the real model; real-certificate checks
    # have their own tests and are never bypassed in production constructors.
    monkeypatch.setattr('utopia.optimization.native_designer_preflight.require_certificate', lambda *a, **k: None)


def body():
    value = request(budget=2)
    value['initial_system'] = open_native_system(BINDING['image_id']).to_dict()
    return value


def authored_output():
    # An explicitly unused numeric parameter exercises syntax transport only;
    # this fixture does not claim an institutional effect or useful invention.
    return {'operations': [{'op': 'add', 'selector': {'mechanism_id': 'world.selection'},
        'path': '/parameters/scripted-interface-number', 'value': .5}],
        'factors': [], 'continuous': [{'id': 'scripted-number',
            'selector': {'mechanism_id': 'world.selection'}, 'path': '/parameters/scripted-interface-number',
            'lower': 0., 'upper': 1., 'mean': 0., 'sigma': .5}],
        'rationale': 'SCRIPTED interface fixture; parameter deliberately unused by source'}


def builder(root, request, binding):
    return make_local_vocabulary_generator(root / 'authoring', image_id=binding['image_id'],
        provider_binding=binding, max_attempts=request['designer']['max_attempts'],
        max_tokens=request['designer']['max_tokens'], inference_lock=root.parent / 'inference.lock')


def test_http_exact_consent_to_stable_helper_has_two_null_slots_at_most_four_attempts(tmp_path, monkeypatch):
    invalid = authored_output(); invalid['operations'][0]['path'] = '/parameters/missing/source'
    model = Model([invalid] * 4)
    monkeypatch.setattr('utopia.optimization.native_search_generator_v14.LocalQwenDesignerModel', lambda *a, **k: model)
    q = NativeSearchQueue(tmp_path, provider_binding=BINDING)
    path = Path(__file__).resolve().parents[2] / 'scripts/serve_native_lab.py'
    spec = importlib.util.spec_from_file_location('stable_queue_http_test', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'pinned_revision', lambda root: REVISION)
    server = module.make_server(NativeJobQueue(tmp_path), search_queue=q,
        source_commit=REVISION, directory=tmp_path, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    native_calls = []
    try:
        token = requests.get(base + '/native-api/session', timeout=5).json()['token']
        headers = {'Origin': base, 'X-Native-Lab-Token': token}
        value = body()
        checked = requests.post(base + '/native-api/search-validate', json=value, headers=headers, timeout=5)
        assert checked.status_code == 200 and checked.json()['maximum_designer_provider_attempts'] == 4
        assert model.calls == []
        created = requests.post(base + '/native-api/searches', json={
            'request': value, 'confirmed_request_sha256': checked.json()['request_sha256']}, headers=headers, timeout=5)
        assert created.status_code == 201 and created.json()['status'] == 'queued' and model.calls == []
        identity = created.json()['search_id']
        result = q.run_one(lambda *a: FailedFactory(native_calls), generator_builder=builder, source_commit=REVISION)
        assert result['status'] == 'complete' and result['budget'] == {
            'scheduled': 2, 'consumed': 2, 'native_observations': 0, 'remaining': 0}
        assert native_calls == [] and len(model.calls) == 4
        third_prompt = json.loads(model.calls[2]['prompt'])
        previous = third_prompt['own_history']['generation_authoring_failures'][0]
        assert previous['technical_errors'][0]['diagnostics'][0]['first_missing_segment'] == 'missing'
        assert len(previous['failed_ir_receipts']) == 2
        assert third_prompt['prompt_view_metadata']['other_arm_data_included'] is False
        evidence = requests.get(base + '/native-api/searches/' + identity + '/evidence', headers=headers, timeout=5).json()
        assert evidence['status'] == 'complete' and len(evidence['records']) == 2
        assert all(r['generation_error']['loss'] is None for r in evidence['records'])
        assert evidence['live_progress']['designer'] == {
            'generation_directories': 2, 'attempts_started': 4, 'attempts_completed': 4}
        roots = sorted((tmp_path / identity / 'authoring').glob('generation-*'))
        assert len(roots) == 2
        for directory in roots:
            journal = json.loads((directory / 'request.json').read_text())
            assert journal['authoring_protocol']['schema'] == 'scienceutopia.native-stable-id-authoring.v1'
            assert journal['settings'] == {'max_attempts': 2, 'max_tokens': 4096}
            assert journal['provider_binding'] == BINDING
        # Terminal reuse and reads cannot create replacement generations.
        assert q.submit(value, confirmed_request_sha256=digest(value), source_commit=REVISION)['search_id'] == identity
        assert q.run_one(lambda *a: pytest.fail('terminal native factory'),
            generator_builder=lambda *a: pytest.fail('terminal generator'), source_commit=REVISION) is None
        assert len(model.calls) == 4
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


def test_stable_definition_pending_native_restart_reuses_translation_then_next_generation(tmp_path, monkeypatch):
    first_model, resumed_model = Model([authored_output()]), Model([authored_output()])
    models = iter([first_model, resumed_model])
    monkeypatch.setattr('utopia.optimization.native_search_generator_v14.LocalQwenDesignerModel', lambda *a, **k: next(models))
    q = NativeSearchQueue(tmp_path, provider_binding=BINDING)
    value = body(); queued = q.submit(value, confirmed_request_sha256=digest(value), source_commit=REVISION)
    class PauseFactory(FailedFactory):
        def __call__(self, *args): raise PortableStop('SCRIPTED pause before any native forward')
    with pytest.raises(PortableStop):
        q.run_one(lambda *a: PauseFactory(), generator_builder=builder, source_commit=REVISION)
    pending = q.get(queued['search_id'])['pending']
    assert pending['generated'] and pending['compiled'] and pending['observations'] == []
    trace = pending['definition']['provenance']['authoring_compiler']
    assert trace['raw_ir'] == authored_output()
    assert len(first_model.calls) == 1
    native_calls = []
    result = NativeSearchQueue(tmp_path, provider_binding=BINDING).run_one(lambda *a: FailedFactory(native_calls),
        generator_builder=builder, source_commit=REVISION)
    assert result['status'] == 'complete' and result['budget']['consumed'] == 2
    assert len(first_model.calls) == len(resumed_model.calls) == 1
    assert len(native_calls) == len(set(native_calls)) == 2
    assert result['records'][0]['definition'] == pending['definition']
    for record in result['records']:
        operations = record['definition']['base_patch']['operations']
        assert operations[0]['op'] == 'add' and 'selector' not in operations[0]
        assert operations[0]['path'].endswith('/parameters/scripted-interface-number')
        assert record['observations'][0]['loss'] is None
    assert result['live_progress']['designer']['attempts_started'] == 2


def test_interrupted_stable_dispatch_consumes_attempt_then_resumes_within_four_attempt_total(tmp_path, monkeypatch):
    interrupted = Model([KeyboardInterrupt()])
    resumed = Model([authored_output(), authored_output()])
    models = iter([interrupted, resumed])
    monkeypatch.setattr('utopia.optimization.native_search_generator_v14.LocalQwenDesignerModel', lambda *a, **k: next(models))
    q = NativeSearchQueue(tmp_path, provider_binding=BINDING)
    value = body(); queued = q.submit(value, confirmed_request_sha256=digest(value), source_commit=REVISION)
    with pytest.raises(KeyboardInterrupt):
        q.run_one(lambda *a: FailedFactory(), generator_builder=builder, source_commit=REVISION)
    assert q.get(queued['search_id'])['pending']['generated'] is False
    native_calls = []
    result = NativeSearchQueue(tmp_path, provider_binding=BINDING).run_one(lambda *a: FailedFactory(native_calls),
        generator_builder=builder, source_commit=REVISION)
    assert result['status'] == 'complete' and result['budget']['consumed'] == 2
    assert len(interrupted.calls) + len(resumed.calls) == 3 <= 4
    assert interrupted.calls[0]['seed_ctx'][-1] == 0 and resumed.calls[0]['seed_ctx'][-1] == 1
    assert len(native_calls) == len(set(native_calls)) == 2
    live = result['live_progress']['designer']
    assert live == {'generation_directories': 2, 'attempts_started': 3, 'attempts_completed': 2}
    receipts = [json.loads(path.read_text()) for path in (tmp_path / queued['search_id'] / 'authoring').glob('generation-*/response.json')]
    statuses = [attempt['status'] for receipt in receipts for attempt in receipt['attempts']]
    assert statuses.count('interrupted-response-unknown') == 1
