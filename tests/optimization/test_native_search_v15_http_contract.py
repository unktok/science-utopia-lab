"""SCRIPTED HTTP/tool interoperability only; no local model or native worlds."""
import importlib.util
import threading
from pathlib import Path

import pytest
import requests

v15 = pytest.importorskip('utopia.optimization.native_search_v15')
from tests.optimization.test_native_search_v14 import BINDING, REVISION, FailedFactory, request
from tests.optimization.test_native_search_generator_v14 import Model
from utopia.optimization.native_jobs import NativeJobQueue
from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator
from utopia.system.design_patch import digest


def test_production_http_staged_session_exact_wire_queue_trace_and_terminal_resume(tmp_path, monkeypatch):
    root = Path(v15.__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('SCRIPTED_v15_http_contract', root / 'scripts/serve_native_lab.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'pinned_revision', lambda _: REVISION)
    queue = v15.NativeStagedSearchQueue(tmp_path / 'queue', provider_binding=BINDING)
    body = request()
    body.update(schema=v15.REQUEST_SCHEMA, designer={'model': 'qwen3:8b', 'max_steps': 2, 'max_tokens': 2048})
    body['initial_system']['metadata']['SCRIPTED_float'] = 1.0
    server = module.make_server(NativeJobQueue(tmp_path / 'queue'), source_commit=REVISION,
        directory=root / 'game-ui-v2', port=0, search_queue=queue)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    try:
        session = requests.get(base + '/native-api/session', timeout=5).json()
        assert session['search_protocol'] == 'staged-v15'
        headers = {'X-Native-Lab-Token': session['token'], 'Origin': base}
        checked = requests.post(base + '/native-api/search-validate', headers=headers, json=body, timeout=5)
        assert checked.status_code == 200, checked.text
        checked = checked.json()
        assert checked['request_sha256'] == digest(body)
        assert checked['maximum_designer_provider_attempts'] == 4
        assert requests.post(base + '/native-api/search-validate', headers=headers,
            json=request(), timeout=5).status_code == 400
        assert requests.post(base + '/native-api/searches', headers=headers,
            json={'request': body, 'confirmed_request_sha256': '0' * 64}, timeout=5).status_code == 400
        assert requests.post(base + '/native-api/searches', json=body, timeout=5).status_code == 403
        queued = requests.post(base + '/native-api/searches', headers=headers,
            json={'request': body, 'confirmed_request_sha256': checked['request_sha256']}, timeout=5)
        assert queued.status_code == 201, queued.text
        first = queued.json()
        assert first['schema'] == v15.PROGRESS_SCHEMA
        assert first['authoring_trace']['generations'] == []
        actions = [{'tool': 'edit', 'operations': [{'op': 'add',
            'path': '/metadata/SCRIPTED_v15_http_test', 'value': 'SCRIPTED no model/native execution'}]},
            {'tool': 'finish', 'rationale': 'SCRIPTED software interoperability only'}] * 2
        def generator_builder(directory, request, binding):
            return StagedVocabularyGenerator(Model(actions), directory / 'authoring',
                image_id=binding['image_id'], provider_binding=binding,
                max_steps=request['designer']['max_steps'], max_tokens=request['designer']['max_tokens'])
        result = queue.run_one(lambda *args: FailedFactory(),
            generator_builder=generator_builder, source_commit=REVISION)
        assert result['status'] == 'complete', result['errors']
        assert result['budget']['consumed'] == 2
        trace = result['authoring_trace']
        assert trace['warnings'] == []
        assert len(trace['generations']) == 2
        assert all([s['status'] for s in g['steps']] == ['applied', 'finished']
            for g in trace['generations'])
        endpoint = base + '/native-api/searches/' + first['search_id'] + '/evidence'
        response = requests.get(endpoint, headers=headers, timeout=5)
        assert response.status_code == 200
        assert response.json()['authoring_trace'] == trace
        def no_builders(*args):
            pytest.fail('terminal resume must not construct a model or native factory')
        assert queue.run_one(no_builders, generator_builder=no_builders, source_commit=REVISION) is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
