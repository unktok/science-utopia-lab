import copy
import importlib.util
import json
from pathlib import Path
import threading
from types import SimpleNamespace

import pytest
import requests

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_jobs import NativeJobQueue, validate_job_request
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system

REVISION = 'a' * 40


def request():
    spec = legacy_world_system().to_dict()
    return {'parent_system': spec, 'system': copy.deepcopy(spec), 'loss_spec': loss_spec(), 'seed': 42, 'years': 2}


def test_queue_persists_and_does_not_execute_on_submit(tmp_path):
    queue = NativeJobQueue(tmp_path)
    row = queue.submit(request(), source_commit=REVISION)
    assert row['status'] == 'queued' and row['result'] is None
    assert NativeJobQueue(tmp_path).get(row['job_id']) == row
    with pytest.raises(ValueError, match='completed evidence'):
        queue.evidence(row['job_id'])
    queue.submit(request(), source_commit=REVISION)
    with pytest.raises(ValueError, match='queue is full'):
        queue.submit(request(), source_commit=REVISION)


@pytest.mark.parametrize('change', [
    lambda r: r.update(command='anything'),
    lambda r: r.update(seed=701),
    lambda r: r.update(seed=True),
    lambda r: r.update(years=100),
    lambda r: r['loss_spec']['per_run']['terms'][0].update(metric_id='not-implemented'),
    lambda r: r['system']['initial_state'].update(seed=999),
])
def test_invalid_jobs_fail_without_enqueuing(change, tmp_path):
    body = request(); change(body)
    with pytest.raises((ValueError, KeyError)):
        NativeJobQueue(tmp_path).submit(body, source_commit=REVISION)


def test_queue_request_tamper_is_rejected(tmp_path):
    queue = NativeJobQueue(tmp_path)
    job = queue.submit(request(), source_commit=REVISION)
    body = request(); body['years'] = 3
    with queue.connection() as db:
        db.execute('UPDATE jobs SET request=? WHERE id=?', (json.dumps(body), job['job_id']))
    with pytest.raises(ValueError, match='hash mismatch'):
        queue.get(job['job_id'])


def test_actual_native_job_returns_reopenable_viewer(tmp_path, fixed_corpus):
    queue = NativeJobQueue(tmp_path)
    job = queue.submit(request(), source_commit=REVISION)
    class Factory:
        model = 'QA-scripted-HTTP'; model_digest = 'QA'; corpus_sha256 = 'QA'; dataset_identity = {'mode': 'QA'}; corpus_years = 4
        def __init__(self, root): self.root = root
        def __call__(self, spec, run_seed, run_id):
            seed()
            sim, _ = make_sim(self.root / 'runs' / run_id, native=NativeScienceKernel(spec))
            sim.num_years = 2
            return sim
    result = queue.run_one(lambda root, body: Factory(root), source_commit=REVISION)
    assert result['status'] == 'complete', result
    assert result['result']['native_loss'] is not None
    evidence = queue.evidence(job['job_id'])
    payload = json.loads(evidence['payload_json'])
    assert payload['systems'][0]['native_loss'] == result['result']['native_loss']
    assert len(payload['systems'][0]['runs'][0]['frames']) == 2
    assert queue.run_one(lambda *a: pytest.fail('no rerun'), source_commit=REVISION) is None


def test_technical_failure_is_null_not_penalty(tmp_path):
    queue = NativeJobQueue(tmp_path)
    queue.submit(request(), source_commit=REVISION)
    result = queue.run_one(lambda *a: (_ for _ in ()).throw(RuntimeError('actual technical error')), source_commit=REVISION)
    assert result['status'] == 'failed' and result['result'] is None


def test_only_one_queue_worker_can_execute(tmp_path):
    queue = NativeJobQueue(tmp_path)
    with queue.worker_lock():
        with pytest.raises(ValueError, match='another worker'):
            with queue.worker_lock(): pass


def test_loopback_api_rejects_cross_origin_host_and_missing_token(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[2] / 'scripts/serve_native_lab.py'
    spec = importlib.util.spec_from_file_location('native_lab_server', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'pinned_revision', lambda root: REVISION)
    static = tmp_path / 'static'; static.mkdir(); (static / 'native.html').write_text('Local test')
    server = module.make_server(NativeJobQueue(tmp_path / 'queue'), source_commit=REVISION, directory=static, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        assert requests.get(base + '/native-api/session', headers={'Origin': 'https://attacker.invalid'}, timeout=5).status_code == 403
        assert requests.get(base + '/native-api/session', headers={'Host': 'attacker.invalid'}, timeout=5).status_code == 403
        token = requests.get(base + '/native-api/session', timeout=5).json()['token']
        assert requests.post(base + '/native-api/jobs', json=request(), headers={'Origin': base}, timeout=5).status_code == 403
        headers = {'Origin': base, 'X-Native-Lab-Token': token}
        valid = requests.post(base + '/native-api/validate', json=request(), headers=headers, timeout=5)
        assert valid.status_code == 200, valid.text
        created = requests.post(base + '/native-api/jobs', json=request(), headers=headers, timeout=5)
        assert created.status_code == 201 and created.json()['status'] == 'queued'
        assert requests.get(base + '/native-api/jobs/' + created.json()['job_id'], headers={'X-Native-Lab-Token': token}, timeout=5).json()['status'] == 'queued'
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
