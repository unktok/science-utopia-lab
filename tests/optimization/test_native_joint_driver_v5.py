"""Orchestration QA only: no scientific evidence, LLM, container or inference.

The real CLI control flow and durable progress/completion writes are exercised;
native campaigns/proposers/factories are scripted narrowly to inject failures.
Native checkpoint/adoption semantics have separate real-phase tests.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
EXHAUSTED = 'bounded region technical drafts exhausted; no native loss fabricated'


@pytest.fixture
def driver_harness(tmp_path, monkeypatch):
    from scripts import run_native_joint_objectives_v5 as driver
    from utopia.optimization import native_code_trace, native_design, native_factory
    from utopia.optimization import native_region_proposer_v5, native_shared_initial
    from utopia.system import code_mechanisms, native_selection_slot
    from utopia.models import models, response_cache

    output = tmp_path / 'run'
    controls = SimpleNamespace(error=None, pending_error=None, error_arm=None,
        controllers={}, proposer_calls=[], physical_runs=[], caches=[])

    class Factory:
        source_commit = 'scripted-orchestration-source'
        model = 'scripted-no-model-calls'
        model_digest = 'scripted-digest'
        corpus_sha256 = 'scripted-corpus'
        dataset_identity = {'fixture': 'orchestration-only'}
        runtime_seed_binding = {'fixture': True}

        def __init__(self, *args, **kwargs):
            pass

    class Cache:
        def __init__(self, *args, **kwargs):
            self.closed = False
            controls.caches.append(self)

        def close(self):
            self.closed = True

    class Model:
        def __init__(self, *args, **kwargs):
            self.response_cache = None

    class Proposer:
        def __init__(self, *args, receipts, **kwargs):
            self.arm = Path(receipts).parent.name

        def __call__(self, *args):
            controls.proposer_calls.append(self.arm)
            if controls.error is not None and (controls.error_arm is None or controls.error_arm == self.arm):
                raise controls.error
            return {'scripted': 'orchestration-only'}

    def row(arm, index, fingerprint):
        physical = f'{arm}-physical-{index}'
        return {'observation': {'status': 'complete', 'loss': -index - 1,
            'metadata': {'system_fingerprint': fingerprint, 'runs': [{'run_id': physical}]}}}

    class Campaign:
        def __new__(cls, directory, **kwargs):
            key = str(directory)
            if key not in controls.controllers:
                controls.controllers[key] = super().__new__(cls)
            return controls.controllers[key]

        def __init__(self, directory, *, initial_system, loss_spec, seeds, world_binding):
            if hasattr(self, 'state'):
                return
            self.directory = Path(directory)
            self.arm = self.directory.parent.name
            self.initial = initial_system
            self.binding = {'loss': loss_spec, 'seeds': seeds, 'world': world_binding}
            self.state = {'records': [], 'pending': None}

        def advance(self, *, simulation_factory, proposer=None):
            index = len(self.state['records'])
            if self.state['pending'] is None:
                if index:
                    proposer(self.initial, self.state['records'], index, self.binding['loss'])
                self.state['pending'] = {'exact_index': index}
            if index and controls.pending_error is not None:
                raise controls.pending_error
            record = row(self.arm, index, self.initial.fingerprint)
            controls.physical_runs.append(record['observation']['metadata']['runs'][0]['run_id'])
            self.state['records'].append(record)
            self.state['pending'] = None
            return record

    def adopt(target, source, **kwargs):
        if not target.state['records']:
            target.state['records'] = [deepcopy(source.state['records'][0])]

    monkeypatch.setattr(driver.subprocess, 'check_output', lambda *a, **k: b'')
    monkeypatch.setattr(native_factory, 'LocalQwenNativeFactory', Factory)
    monkeypatch.setattr(native_factory, 'serialize_native_http', lambda *a: None)
    monkeypatch.setattr(native_design, 'NativeDesignCampaign', Campaign)
    monkeypatch.setattr(native_code_trace, 'parent_context_provider', lambda *a, **k: None)
    monkeypatch.setattr(native_region_proposer_v5, 'NativeRegionIRProposer', Proposer)
    monkeypatch.setattr(native_shared_initial, 'adopt_shared_initial', adopt)
    monkeypatch.setattr(code_mechanisms, 'DockerCodeExecutor', lambda: SimpleNamespace(image_id='scripted-no-container'))
    monkeypatch.setattr(native_selection_slot, 'selection_source_slot', lambda spec, **kwargs: spec)
    monkeypatch.setattr(models, 'VLLMServerModel', Model)
    monkeypatch.setattr(response_cache, 'CompletedResponseCache', Cache)

    def run(*, budget=3):
        argv = ['native-joint-driver', '--output', str(output), '--data-cache', str(tmp_path / 'data'),
                '--inference-lock', str(tmp_path / 'no-inference.lock'), '--budget', str(budget)]
        for suffix in ('throughput', 'net-reviewed-utility'):
            argv.extend(['--loss', str(ROOT / f'research/objectives/losses/native-joint-v5-{suffix}.json')])
        monkeypatch.setattr(driver.sys, 'argv', argv)
        return driver.main()

    return SimpleNamespace(run=run, output=output, controls=controls,
        first='native-joint-v5-throughput', second='native-joint-v5-net-reviewed-utility')


@pytest.mark.parametrize('error', [TimeoutError('transport interrupted'), OSError('cache unavailable'),
                                  ValueError('integrity mismatch, not exhausted technical drafts')])
def test_transport_cache_or_integrity_error_is_not_terminal_authoring(driver_harness, error):
    h = driver_harness
    h.controls.error = error
    with pytest.raises(type(error), match=str(error)):
        h.run()
    assert not (h.output / 'terminal-authoring-errors.json').exists()
    assert not (h.output / 'completion.json').exists()
    progress = json.loads((h.output / 'progress.json').read_text())
    assert progress['status'] == 'interrupted-preserve-pending-and-exact-drafts'
    assert len(h.controls.physical_runs) == 1
    assert all(cache.closed for cache in h.controls.caches)
    h.controls.error = None
    h.run()
    assert len(h.controls.physical_runs) == 5  # shared initial + 2 fresh systems per arm
    assert json.loads((h.output / 'completion.json').read_text())['status'] == 'declared-budget-complete'


def test_pending_native_error_propagates_then_reuses_exact_pending_proposal(driver_harness):
    h = driver_harness
    # Even an exhaustion-shaped ValueError must NOT terminate an already
    # committed pending native evaluation.
    h.controls.pending_error = ValueError(EXHAUSTED)
    with pytest.raises(ValueError, match='bounded region'):
        h.run()
    assert not (h.output / 'terminal-authoring-errors.json').exists()
    first = next(c for c in h.controls.controllers.values() if c.arm == h.first)
    assert first.state['pending'] == {'exact_index': 1}
    assert h.controls.proposer_calls == [h.first]
    h.controls.pending_error = None
    h.run()
    assert first.state['pending'] is None
    assert h.controls.proposer_calls.count(h.first) == 2  # index1 once, index2 once
    assert len(h.controls.physical_runs) == 5
    assert all(cache.closed for cache in h.controls.caches)


def test_bounded_technical_exhaustion_is_null_and_other_arm_finishes(driver_harness):
    h = driver_harness
    h.controls.error, h.controls.error_arm = ValueError(EXHAUSTED), h.first
    h.run()
    errors = json.loads((h.output / 'terminal-authoring-errors.json').read_text())
    assert set(errors) == {h.first}
    assert errors[h.first]['loss'] is None and errors[h.first]['automatic_redraft'] is False
    assert h.controls.proposer_calls.count(h.first) == 1
    assert h.controls.proposer_calls.count(h.second) == 2
    root = json.loads((h.output / 'completion.json').read_text())
    assert root['status'] == 'terminal-with-preserved-failures'
    assert root['physical_complete_runs'] == 3
    for arm, actual, status in [(h.first, 1, 'terminal-authoring-failure-not-budget-complete'),
                                (h.second, 3, 'declared-budget-complete')]:
        completion = json.loads((h.output / 'arms' / arm / 'completion.json').read_text())
        assert completion['budget'] == actual  # exact key/count expected by audit_campaign
        assert completion['logical_observations'] == actual
        assert completion['declared_budget'] == 3
        assert completion['status'] == status
    before = list(h.controls.proposer_calls)
    h.run()
    assert h.controls.proposer_calls == before  # terminal arm is not silently redrafted
    assert len(h.controls.physical_runs) == 3
    assert all(cache.closed for cache in h.controls.caches)
