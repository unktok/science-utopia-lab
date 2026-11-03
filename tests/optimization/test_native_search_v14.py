"""SCRIPTED software verification only; never real Qwen or research findings."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sqlite3
import sys
import threading

import pytest
import requests

from tests.optimization.test_native_world import loss_spec
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from utopia.optimization.native_jobs import NativeJobQueue
from utopia.optimization.native_search_jobs_v14 import NativeSearchQueue
from utopia.optimization.native_search_v14 import NativeSearchController, validate_search_request
from utopia.runtime.checkpointing import PortableStop
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system

REVISION = 'a' * 40
BINDING = {'model': 'qwen3:8b', 'model_digest': 'SCRIPTED-test-only',
    'corpus_sha256': 'SCRIPTED-corpus-test-only', 'dataset_identity': {'mode': 'SCRIPTED-test-only'},
    'corpus_years': 4, 'image_id': 'sha256:' + '1' * 64}


def request(method='blackbox', budget=2):
    return {'schema': 'scienceutopia.native-search-request.v14',
        'initial_system': legacy_world_system().to_dict(), 'loss_spec': loss_spec(),
        'seed': 42, 'years': 1, 'method': method, 'native_budget': budget,
        'designer': {'model': 'qwen3:8b', 'max_attempts': 2, 'max_tokens': 4096}}


def queue(path):
    return NativeSearchQueue(path, provider_binding=BINDING)


def submit(q, body=None):
    body = body or request()
    return q.submit(body, confirmed_request_sha256=digest(body), source_commit=REVISION)


def definition(_request):
    return {'base_patch': None, 'factors': [], 'continuous': [],
        'provenance': {'mode': 'SCRIPTED-software-test-only'}}


class FailedFactory:
    def __init__(self, calls=None):
        self.__dict__.update({k: v for k, v in BINDING.items() if k != 'image_id'})
        self.calls = calls if calls is not None else []
    def __call__(self, spec, run_seed, run_id):
        self.calls.append(run_id)
        raise RuntimeError('SCRIPTED technical failure; no model called')


def test_validate_submit_exact_consent_idempotency_and_bounded_queue(tmp_path):
    q = queue(tmp_path)
    body = request()
    checked = q.validate(body, source_commit=REVISION)
    assert checked['request_sha256'] == digest(body)
    assert checked['maximum_designer_provider_attempts'] == 4
    assert not list(tmp_path.glob('search-*'))
    with pytest.raises(ValueError, match='compute consent'):
        q.submit(body, confirmed_request_sha256='wrong', source_commit=REVISION)
    first = submit(q, body)
    assert first['status'] == 'queued' and first['records'] == []
    assert submit(queue(tmp_path), body)['search_id'] == first['search_id']
    assert first['immutable_plan']['stage_counts'] == [1, 1]
    submit(q, request(budget=3))
    with pytest.raises(ValueError, match='queue is full'):
        submit(q, request(budget=4))


@pytest.mark.parametrize('change', [
    lambda r: r.update(command='host code'), lambda r: r.update(url='https://example.invalid'),
    lambda r: r.update(method='invented'), lambda r: r.update(native_budget=True),
    lambda r: r.update(native_budget=9), lambda r: r.update(seed=701),
    lambda r: r.update(years=5), lambda r: r['designer'].update(model='remote-model'),
    lambda r: r['designer'].update(max_attempts=4), lambda r: r['designer'].update(max_tokens=9000),
    lambda r: r['designer'].update(path='/host/path'),
    lambda r: r['initial_system']['initial_state'].update(seed=43),
])
def test_invalid_requests_fail_without_enqueue(tmp_path, change):
    body = request(); change(body)
    with pytest.raises((ValueError, TypeError, KeyError)):
        submit(queue(tmp_path), body)
    assert not list(tmp_path.glob('search-*'))


@pytest.mark.parametrize('budget', [1, 2, 3, 5, 8])
def test_nested_requires_exact_unchanged_four_slot_schedule(budget):
    with pytest.raises(ValueError, match='exactly four'):
        validate_search_request(request('nested-lr', budget))


def test_v13_efficiency_loss_is_available_without_relaxing_old_job_metrics(tmp_path):
    body = request('nested-lr', 4)
    root = Path(__file__).resolve().parents[2]
    body['loss_spec'] = json.loads((root / 'research/objectives/losses/native-reviewed-production-efficiency-v13.json').read_text())
    checked = submit(queue(tmp_path), body)
    assert checked['immutable_plan']['stage_counts'] == [2, 1, 1]
    assert checked['immutable_plan']['generator_calls'] == 2


def test_generation_failures_consume_all_slots_without_replacement(tmp_path):
    q = queue(tmp_path); first = submit(q, request('nested-lr', 4))
    calls = []
    def generator(body):
        calls.append(body['stage'])
        raise RuntimeError('SCRIPTED bounded adapter failure')
    result = q.run_one(lambda *a: FailedFactory(), generator_builder=lambda *a: generator, source_commit=REVISION)
    assert result['status'] == 'complete' and result['search_id'] == first['search_id']
    assert result['budget'] == {'scheduled': 4, 'consumed': 4, 'native_observations': 0, 'remaining': 0}
    assert calls == ['initial-batch', 'redesign']
    assert len(result['records']) == 3 and all(r['generation_error']['loss'] is None for r in result['records'])
    assert result['best']['loss'] is None and result['current'] is None
    assert submit(q, request('nested-lr', 4))['search_id'] == first['search_id']
    assert q.run_one(lambda *a: pytest.fail('no repeat'), generator_builder=lambda *a: pytest.fail('no repeat'), source_commit=REVISION) is None


def test_failed_worlds_are_null_and_restart_resumes_exact_next_slot(tmp_path):
    q = queue(tmp_path); first = submit(q)
    calls, author_requests = [], []
    def author(body): author_requests.append(copy.deepcopy(body)); return definition(body)
    def stop(controller): raise PortableStop('SCRIPTED cold restart boundary after committed stage')
    with pytest.raises(PortableStop):
        q.run_one(lambda *a: FailedFactory(calls), generator_builder=lambda *a: author,
            source_commit=REVISION, after_stage=stop)
    assert q.get(first['search_id'])['budget']['consumed'] == 1
    resumed = queue(tmp_path).run_one(lambda *a: FailedFactory(calls), generator_builder=lambda *a: author, source_commit=REVISION)
    assert resumed['status'] == 'complete' and len(calls) == len(set(calls)) == 2
    assert len(author_requests) == 2 and len(author_requests[1]['history']) == 1
    assert all(o['observation']['loss'] is None for o in resumed['observations'])
    assert len(resumed['errors']) == 2


def test_final_commit_restart_only_marks_terminal_without_constructing_providers(tmp_path):
    q = queue(tmp_path); first = submit(q, request(budget=1))
    def stop(controller): raise PortableStop('SCRIPTED stop after last campaign commit')
    with pytest.raises(PortableStop):
        q.run_one(lambda *a: FailedFactory(), generator_builder=lambda *a: definition,
            source_commit=REVISION, after_stage=stop)
    assert q.get(first['search_id'])['status'] == 'running'
    result = queue(tmp_path).run_one(lambda *a: pytest.fail('no factory on terminal resume'),
        generator_builder=lambda *a: pytest.fail('no generator on terminal resume'), source_commit=REVISION)
    assert result['status'] == 'complete' and result['budget']['consumed'] == 1


def test_real_cold_process_restart_never_repeats_committed_native_attempt(tmp_path):
    """Two separate Python workers; native factory is explicitly failing SCRIPTED QA."""
    q = queue(tmp_path); first = submit(q)
    script = '''
import sys
from pathlib import Path
from tests.optimization.test_native_search_v14 import queue, FailedFactory, definition, REVISION
from utopia.runtime.checkpointing import PortableStop
root = Path(sys.argv[1])
class Factory(FailedFactory):
    def __call__(self, spec, run_seed, run_id):
        with (root / 'attempts.txt').open('a') as handle:
            handle.write(run_id + '\\n')
        return super().__call__(spec, run_seed, run_id)
def stop(controller):
    raise PortableStop('SCRIPTED process stop after committed first stage')
try:
    queue(root).run_one(lambda *a: Factory(), generator_builder=lambda *a: definition,
        source_commit=REVISION, after_stage=stop if sys.argv[2] == 'stop' else None)
except PortableStop:
    pass
'''
    for mode in ('stop', 'resume'):
        subprocess.run([sys.executable, '-c', script, str(tmp_path), mode], check=True,
            cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True)
    attempts = (tmp_path / 'attempts.txt').read_text().splitlines()
    assert len(attempts) == len(set(attempts)) == 2
    assert queue(tmp_path).get(first['search_id'])['status'] == 'complete'


def test_original_native_checkpoint_replays_after_cold_process_loss_of_observation(tmp_path):
    """Interrupt after native completion, before observation commit; no new replies."""
    q = queue(tmp_path); first = submit(q, request(budget=1))
    script = '''
import sys
from pathlib import Path
from pytest import MonkeyPatch
from tests.optimization.test_native_search_v14 import queue, FailedFactory, definition, REVISION, BINDING
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, FakeHTTPModel, BINDING as CB, seed
from tests.system.test_native_science_kernel import make_sim
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.runtime.checkpointing import PortableStop
from utopia.system.native_kernel import NativeScienceKernel
mp = MonkeyPatch()
fixed_corpus.__wrapped__(mp)
mp.setitem(CB, 'model_revision', BINDING['model_digest'])
mp.setitem(CB, 'corpus_sha256', BINDING['corpus_sha256'])
mp.setitem(CB, 'science_config', {'source_commit': REVISION, 'years': 1})
root = Path(sys.argv[1])
class PhysicalModel(FakeHTTPModel):
    def reply(self, **payload):
        with (root / 'physical-replies.txt').open('a') as handle:
            handle.write('SCRIPTED physical provider call\\n')
        return super().reply(**payload)
class Factory(FailedFactory):
    def __call__(self, spec, run_seed, run_id):
        mp.setitem(CB, 'cell', spec.fingerprint)
        seed()
        sim, calls = make_sim(root / 'worlds' / run_id,
            native=NativeScienceKernel(spec), model_class=PhysicalModel)
        sim.num_years = 1
        return sim
original_save = NativeAdaptiveDesignCampaign._save
def interrupted_save(campaign):
    if campaign.state['pending'] and campaign.state['pending']['observations']:
        raise PortableStop('SCRIPTED process interruption before observation persistence')
    return original_save(campaign)
if sys.argv[2] == 'stop':
    mp.setattr(NativeAdaptiveDesignCampaign, '_save', interrupted_save)
try:
    queue(root).run_one(lambda *a: Factory(), generator_builder=lambda *a: definition,
        source_commit=REVISION)
except PortableStop:
    pass
finally:
    mp.undo()
'''
    def run(mode):
        result = subprocess.run([sys.executable, '-c', script, str(tmp_path), mode],
            cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
    run('stop')
    assert q.get(first['search_id'])['status'] == 'running'
    assert q.get(first['search_id'])['pending']['observations'] == []
    physical = (tmp_path / 'physical-replies.txt').read_text()
    assert physical
    run('resume')
    result = q.get(first['search_id'])
    assert result['status'] == 'complete', result['errors']
    assert result['best']['loss'] is not None
    assert (tmp_path / 'physical-replies.txt').read_text() == physical
    assert result['budget']['native_observations'] == 1
    assert len(list((tmp_path / 'worlds').iterdir())) == 1


def test_factory_source_and_provider_mismatch_fail_before_any_generation(tmp_path):
    q = queue(tmp_path); submit(q)
    failed = q.run_one(lambda *a: pytest.fail('source rejected first'),
        generator_builder=lambda *a: pytest.fail('source rejected first'), source_commit='b' * 40)
    assert failed['status'] == 'failed' and 'source differs' in failed['errors'][0]['worker_error']
    submit(q, request(budget=3))
    def changed(*a):
        factory = FailedFactory(); factory.model_digest = 'changed'; return factory
    failed = q.run_one(changed, generator_builder=lambda *a: pytest.fail('provider rejected first'), source_commit=REVISION)
    assert failed['status'] == 'failed' and 'model/corpus differs' in failed['errors'][0]['worker_error']


@pytest.mark.parametrize('target', ['sql-plan', 'plan-file', 'campaign', 'missing'])
def test_saved_plan_state_and_missing_state_tamper_fail_closed(tmp_path, target):
    q = queue(tmp_path); first = submit(q)
    root = tmp_path / first['search_id']
    if target == 'sql-plan':
        with q.connection() as db:
            db.execute('UPDATE searches SET plan=?', ('{}',))
    elif target == 'plan-file':
        (root / 'plan.json').write_text('{}')
    elif target == 'missing':
        (root / 'campaign/native-adaptive-state.json').unlink()
    else:
        path = root / 'campaign/native-adaptive-state.json'
        state = json.loads(path.read_text()); state['binding']['seed'] = 123
        path.write_text(json.dumps(state))
    with pytest.raises((ValueError, KeyError)):
        q.get(first['search_id'])


def test_old_and_search_workers_share_one_native_execution_lock(tmp_path):
    q = queue(tmp_path)
    with NativeJobQueue(tmp_path).worker_lock():
        with pytest.raises(ValueError, match='another native/search worker'):
            with q.worker_lock(): pass


def test_original_world_scripted_http_search_preserves_ties_current_and_reopens(tmp_path, fixed_corpus, monkeypatch):
    from tests.runtime.test_portable_checkpoint_integration import BINDING as checkpoint_binding
    monkeypatch.setitem(checkpoint_binding, 'model_revision', BINDING['model_digest'])
    monkeypatch.setitem(checkpoint_binding, 'corpus_sha256', BINDING['corpus_sha256'])
    monkeypatch.setitem(checkpoint_binding, 'science_config', {'source_commit': REVISION, 'years': 1})
    q = queue(tmp_path); first = submit(q)
    calls = []
    class Factory(FailedFactory):
        def __call__(self, spec, run_seed, run_id):
            calls.append(run_id); seed()
            monkeypatch.setitem(checkpoint_binding, 'cell', spec.fingerprint)
            sim, _ = make_sim(tmp_path / 'worlds' / run_id, native=NativeScienceKernel(spec))
            sim.num_years = 1
            return sim
    result = q.run_one(lambda *a: Factory(), generator_builder=lambda *a: definition, source_commit=REVISION)
    assert result['status'] == 'complete', result['errors']
    assert result['best']['loss'] is not None and len(result['best']['ties']) == 2
    assert result['current'] != result['best']['incumbent']
    assert len(calls) == len(set(calls)) == 2
    reopened = queue(tmp_path).evidence(first['search_id'])
    reopened.pop('live_progress'); result.pop('live_progress')
    assert reopened == result


def test_live_progress_missing_evidence_is_unknown_and_read_only(tmp_path):
    q = queue(tmp_path); first = submit(q)
    before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*'))
    live = q.get(first['search_id'])['live_progress']
    assert live['scope'] == 'observed-local-files-not-final-audited-cost'
    assert all(v is None for v in live['designer'].values())
    assert live['researcher'] == {'runs': [], 'cached_responses': None, 'latest_checkpoint_year': None}
    assert sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob('*')) == before


def test_live_progress_observes_bound_files_without_claiming_native_completion(tmp_path):
    q = queue(tmp_path); first = submit(q, request(budget=1))
    class PausedFactory(FailedFactory):
        def __call__(self, *args): raise PortableStop('SCRIPTED pause with scheduled native draw')
    with pytest.raises(PortableStop):
        q.run_one(lambda *a: PausedFactory(), generator_builder=lambda *a: definition, source_commit=REVISION)
    projection = q.get(first['search_id'])
    pending = projection['pending']
    root = tmp_path / first['search_id']
    generation = root / 'authoring' / ('generation-' + digest(pending['request']))
    generation.mkdir(parents=True)
    binding = {'schema': 'scienceutopia.llm-vocabulary-request.v14', 'request': pending['request'],
        'request_sha256': digest(pending['request']), 'provider_binding': BINDING,
        'image_id': BINDING['image_id'], 'settings': request()['designer'].copy()}
    binding['settings'].pop('model')
    binding['binding_sha256'] = digest(binding)
    (generation / 'request.json').write_text(json.dumps(binding))
    for suffix in ('started', 'completed'):
        (generation / f'attempt-00.{suffix}.json').write_text(json.dumps({
            'attempt': 0, 'binding_sha256': binding['binding_sha256'], 'secret-prompt': 'DO-NOT-EXPOSE'}))
    run_id = pending['draws'][0]['suggestion']['suggestion_id'] + '-s42'
    world = root / 'worlds' / run_id
    checkpoints = world / 'simulation/checkpoints/native-design'; checkpoints.mkdir(parents=True)
    # Deliberately a filename-only placeholder, not valid checkpoint evidence.
    (checkpoints / 'portable_checkpoint_year_1.json.gz').write_bytes(b'SCRIPTED provisional filename only')
    replies = world / 'replies'; replies.mkdir()
    cache_binding = {'cell': SystemSpec.from_dict(pending['draws'][0]['suggestion']['candidate']).fingerprint,
        'seed': 42, 'model': BINDING['model'], 'model_revision': BINDING['model_digest'],
        'corpus_sha256': BINDING['corpus_sha256'], 'science_config': {'source_commit': REVISION, 'years': 1}}
    path = replies / 'responses.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE metadata (binding TEXT)')
        db.execute('INSERT INTO metadata VALUES (?)', (json.dumps(cache_binding),))
        db.execute('CREATE TABLE replies (outcome TEXT)')
        db.executemany('INSERT INTO replies VALUES (?)', [('response',), ('response',)])
    before = path.read_bytes()
    result = q.get(first['search_id']); live = result['live_progress']
    assert result['status'] == 'running' and result['best']['loss'] is None
    assert result['budget']['consumed'] == result['budget']['native_observations'] == 0
    assert live['designer'] == {'generation_directories': 1, 'attempts_started': 1, 'attempts_completed': 1}
    assert live['researcher']['cached_responses'] == 2 and live['researcher']['latest_checkpoint_year'] == 1
    assert live['researcher']['runs'][0]['cache_binding_status'] == 'matched'
    assert 'DO-NOT-EXPOSE' not in json.dumps(live) and str(tmp_path) not in json.dumps(live)
    assert path.read_bytes() == before
    with sqlite3.connect(path) as db:
        db.execute('UPDATE metadata SET binding=?', (json.dumps({**cache_binding, 'science_config': {'source_commit': 'b' * 40, 'years': 1}}),))
    mismatched = q.get(first['search_id'])['live_progress']['researcher']
    assert mismatched['cached_responses'] is None and mismatched['runs'][0]['cache_binding_status'] == 'mismatch'
    with sqlite3.connect(path) as db:
        db.execute('BEGIN EXCLUSIVE')
        unavailable = q.get(first['search_id'])['live_progress']['researcher']
        assert unavailable['cached_responses'] is None and unavailable['runs'][0]['cache_binding_status'] == 'unavailable'
    (generation / 'request.json').write_text('{}')
    broken = q.get(first['search_id'])['live_progress']
    assert all(v is None for v in broken['designer'].values())
    assert broken['warnings'] == ['designer-receipts-unavailable-or-binding-mismatch']


def test_search_http_consent_origin_source_auth_and_legacy_compatibility(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[2] / 'scripts/serve_native_lab.py'
    spec = importlib.util.spec_from_file_location('native_search_server_test', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'pinned_revision', lambda root: REVISION)
    server = module.make_server(NativeJobQueue(tmp_path), source_commit=REVISION,
        directory=tmp_path, port=0, search_queue=queue(tmp_path))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        session = requests.get(base + '/native-api/session', timeout=5).json()
        assert session['search_enabled']
        headers = {'Origin': base, 'X-Native-Lab-Token': session['token']}
        body = request()
        assert requests.post(base + '/native-api/search-validate', json=body, timeout=5).status_code == 403
        assert requests.post(base + '/native-api/searches', json=body, headers=headers, timeout=5).status_code == 400
        checked = requests.post(base + '/native-api/search-validate', json=body, headers=headers, timeout=5)
        assert checked.status_code == 200
        confirmed = {'request': body, 'confirmed_request_sha256': checked.json()['request_sha256']}
        changed = copy.deepcopy(confirmed); changed['request']['years'] = 2
        assert requests.post(base + '/native-api/searches', json=changed, headers=headers, timeout=5).status_code == 400
        created = requests.post(base + '/native-api/searches', json=confirmed, headers=headers, timeout=5)
        assert created.status_code == 201, created.text
        url = base + '/native-api/searches/' + created.json()['search_id']
        assert requests.get(url, timeout=5).status_code == 403
        assert requests.get(url + '/evidence', headers=headers, timeout=5).json()['status'] == 'queued'
        assert requests.get(url, headers={**headers, 'Origin': 'https://attacker.invalid'}, timeout=5).status_code == 403
        monkeypatch.setattr(module, 'pinned_revision', lambda root: 'b' * 40)
        assert requests.post(base + '/native-api/searches', json=confirmed, headers=headers, timeout=5).status_code == 400
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
