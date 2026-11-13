"""Post-stop scheduler units; no scientific/model/backend evidence is fabricated."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import dispatch_native_parameter_after_stop_v1 as driver
from scripts.run_pre_scale_completion_chain_v1 import save as chain_save
from utopia.optimization.native_numeric_designer import save as scientific_save


def fixture(tmp_path, monkeypatch):
    args = SimpleNamespace(run=tmp_path / 'numeric-source/outputs/numeric', frozen_source=tmp_path / 'numeric-source',
        stopped_run=tmp_path / 'stopped-source/outputs/stopped', stopped_source=tmp_path / 'stopped-source',
        stopped_chain=tmp_path / 'old-chain', output=tmp_path / 'new-chain')
    args.stopped_chain.mkdir()
    scientific_save(args.run / 'plan.json', {'schema': 'scienceutopia.native-parameter-comparator.v1.plan',
        'source_commit': 'b' * 40, 'budget': {'native_worlds_upper_bound': 6},
        'origin': {'run': str(tmp_path / 'normally-closed-bank'), 'source_commit': 'd' * 40},
        'observer_contract': {'backend': {'ollama_version': 'SCRIPTED'}}})
    original = scientific_save(args.stopped_run / 'plan.json', {
        'schema': 'scienceutopia.native-parent-presentation-loop.v1.plan', 'source_commit': 'c' * 40})
    scientific_save(args.stopped_run / 'started.json', {'pid': 101, 'plan_sha256': original['content_sha256']})
    scientific_save(args.stopped_run / 'terminal.json', {'status': 'stopped', 'stage': 'readiness',
        'error_type': 'CompletionUnknown'})
    (args.stopped_run / 'writer.lock').touch()
    scientific_save(args.stopped_run / 'search/throughput-literal/readiness-1/editor-readiness/result.json', {
        'worker_result_exists': False, 'execution': {'timed_out': True, 'server_cancel_confirmed': False}})
    chain_save(args.stopped_chain / 'started.json', {'schema': 'scienceutopia.native-parameter-comparator-chain.v1',
        'wait_writer_pid': 101, 'pid': 102, 'wait_analysis_pid': 103,
        'numeric_source_commit': 'b' * 40, 'numeric_plan_file_sha256': driver.sha(args.run / 'plan.json')})
    chain_save(args.stopped_chain / 'ended.json', {'status': 'stopped', 'stage': 'wait-upstream-science', 'steps': []})
    monkeypatch.setattr(driver, 'revision', lambda p: ('b' * 40 if Path(p) == args.frozen_source else
        'c' * 40 if Path(p) == args.stopped_source else 'a' * 40))
    monkeypatch.setattr(driver, 'process_identity', lambda pid: None)
    args.output.mkdir(); chain_save(args.output / 'plan.json', driver.binding(args, observe=lambda pid: None))
    return args


def quiet():
    return {'schema': driver.SCHEMA + '.quiescence', 'inference_POSTs': 0,
        'ps': {'payload': {'models': []}}, 'version': {'payload': {'version': 'SCRIPTED'}}}


def mock_commands(args, calls, *, fail_stage=None, mutate=None):
    def execute(argv, **kwargs):
        module = argv[2]; calls.append(argv)
        assert kwargs['cwd'] == args.frozen_source
        assert kwargs['env']['PYTHONHASHSEED'] == '42' and kwargs['env']['HF_HUB_OFFLINE'] == '1'
        if module == 'scripts.run_native_parameter_comparator_v1':
            assert 'timeout' not in kwargs
            scientific_save(args.run / 'started.json', {'SCRIPTED': 'one first scientific dispatch'})
        else:
            assert kwargs['timeout'] == 1800
            path = Path(argv[argv.index('--output') + 1])
            if module == 'scripts.reports.native_parameter_comparator_v1':
                path.mkdir(); chain_save(path / 'report.json', {'SCRIPTED': 'same report'})
            else:
                scientific_save(path, {'SCRIPTED': 'same deterministic projection', 'module': module})
        if mutate: mutate()
        return SimpleNamespace(returncode=1 if len(calls) == fail_stage else 0)
    return execute


def test_one_first_dispatch_after_fresh_quiescence_then_original_double_projections(tmp_path, monkeypatch):
    args = fixture(tmp_path, monkeypatch); ticks = [0.]; observations, calls = [], []
    def poll(seconds): assert seconds == 30; ticks[0] += seconds
    def backend(): observations.append(ticks[0]); return quiet()
    before = driver.digest(driver._inventory(args.stopped_run))
    driver.run(args.output, observe=lambda pid: None, backend=backend, poll=poll, clock=lambda: ticks[0],
        command=mock_commands(args, calls))
    assert observations == [0., 30.] and len(calls) == 7
    assert driver.read(args.output / 'ended.json')['status'] == 'closed'
    assert driver.read(args.stopped_run / 'terminal.json')['status'] == 'stopped'
    assert before == driver.digest(driver._inventory(args.stopped_run))
    assert driver.read(args.stopped_chain / 'ended.json')['steps'] == []
    assert driver.read(args.output / 'quiescence-review.json')['historical_completion_unknown'] is True
    with pytest.raises(ValueError, match='unconsumed'):
        driver.run(args.output, observe=lambda pid: None, command=lambda *a, **k: pytest.fail('no repeat'))


@pytest.mark.parametrize('fault', ['live-pid', 'busy-backend', 'changed-version', 'no-time-separation',
    'source-change', 'old-stop-change', 'numeric-consumed', 'different-numeric-plan'])
def test_any_failed_prerequisite_prevents_science_without_rewriting_old_stop(tmp_path, monkeypatch, fault):
    args = fixture(tmp_path, monkeypatch); ticks = [0.]; count = [0]
    observe = lambda pid: 'live or reused PID' if fault == 'live-pid' and pid == 101 else None
    def backend():
        count[0] += 1; value = quiet()
        if fault == 'busy-backend': value['ps']['payload']['models'] = [{'name': 'busy'}]
        if fault == 'changed-version': value['version']['payload']['version'] = 'other'
        return value
    def poll(seconds):
        if fault != 'no-time-separation': ticks[0] += seconds
        if fault == 'source-change':
            monkeypatch.setattr(driver, 'revision', lambda p: 'f' * 40)
        if fault == 'old-stop-change':
            (args.stopped_run / 'extra-drift.json').write_text('{}')
    if fault == 'numeric-consumed': scientific_save(args.run / 'started.json', {'SCRIPTED': 'already used'})
    if fault == 'different-numeric-plan':
        path = args.stopped_chain / 'started.json'; value = driver.read(path)
        value['numeric_plan_file_sha256'] = '0' * 64; path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        driver.run(args.output, observe=observe, backend=backend, poll=poll, clock=lambda: ticks[0],
            command=lambda *a, **k: pytest.fail('unsafe scientific dispatch'))
    if fault != 'numeric-consumed': assert not (args.run / 'started.json').exists()
    assert driver.read(args.stopped_run / 'terminal.json')['error_type'] == 'CompletionUnknown'


@pytest.mark.parametrize('failed_stage', range(1, 8))
def test_failed_stage_is_never_retried_or_followed_by_later_commands(tmp_path, monkeypatch, failed_stage):
    args = fixture(tmp_path, monkeypatch); ticks = [0.]; calls = []
    with pytest.raises(ValueError, match='never retry'):
        driver.run(args.output, observe=lambda pid: None, backend=quiet,
            poll=lambda s: ticks.__setitem__(0, ticks[0] + s), clock=lambda: ticks[0],
            command=mock_commands(args, calls, fail_stage=failed_stage))
    assert len(calls) == failed_stage
    assert sum(c[2] == 'scripts.run_native_parameter_comparator_v1' for c in calls) == 1
    assert driver.read(args.output / 'ended.json')['status'] == 'stopped'
    if failed_stage == 1: assert not list(args.output.glob('audit-*.started.json'))


@pytest.mark.parametrize('models', [[], [{'name': 'loaded'}], None])
def test_metadata_observer_uses_get_only_and_requires_literal_empty_residency(models):
    class Response:
        status_code = 200
        def __init__(self, body): self.text = json.dumps(body)
        def raise_for_status(self): pass
    class Session:
        def __init__(self): self.calls = []
        def get(self, url, **kwargs):
            self.calls.append(url); assert kwargs == {'timeout': 10}
            return Response({'models': models} if url.endswith('/ps') else {'version': 'SCRIPTED'})
        def post(self, *a, **k): pytest.fail('metadata gate cannot POST')
    session = Session()
    if models == []:
        value = driver.backend_observation(session=session)
        assert value['inference_POSTs'] == 0 and not value['restart_or_unload']
    else:
        with pytest.raises(ValueError, match='empty/known'): driver.backend_observation(session=session)
    assert len(session.calls) == 2
