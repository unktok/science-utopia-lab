import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_native_workflow_objective_loop_v1 as driver
from tests.reports.test_native_planning_objective_loop_v1 import plan, seal
from scripts.finish_native_institution_loop_v1 import same_files
from utopia.system.design_patch import clone


def setup(tmp_path, monkeypatch):
    original, _, _, _ = plan(tmp_path / 'inputs', monkeypatch)
    audit = seal({'schema': 'scienceutopia.native-planning-objective-loop-audit.v1',
        'source_commit': original['source_commit'], 'SCRIPTED': 'not actual original closure'})
    origin = {'SCRIPTED': 'no actual archive attestation'}
    sources = {'original_source': original['source_commit'], 'SCRIPTED': 'not source equivalence'}
    prerequisite = {'directory': str(tmp_path / 'prior-chain'), 'SCRIPTED': True}
    p = driver.build_plan(original, audit, source='e' * 40, origin=origin, backend=original['backend'],
        observer_backend=original['observer_contract']['backend'], prerequisite=prerequisite, sources=sources)
    return p, original, audit, sources


def test_explicit_eight_world_domain_and_literal_plan_reconstruction(tmp_path, monkeypatch):
    p, original, audit, sources = setup(tmp_path, monkeypatch)
    assert p['budget']['native_worlds_upper_bound'] == 8 and p['budget']['candidate_slots'] == 6
    assert p['budget']['designer_POSTs_upper_bound'] == 13 and p['budget']['readiness_sessions'] == 7
    assert p['budget']['replace_failed_slots'] is False
    assert p['design_space']['world_law_scope'] == 'fixed-native-effects-workflow-v4'
    assert p['authoring_scope'] == 'literal-existing-institutions-workflow-only'
    assert p['world']['world_conditions'] == original['world']['world_conditions']
    assert p['reference_systems']['R7-original']['mechanisms'] == p['reference_systems']['post-funding-cost']['mechanisms']
    assert p['reference_order'] == ['R7-original', 'post-funding-cost']
    assert [(r['objective'], r['generation']) for r in p['schedule']] == [
        ('throughput', 0), ('content-utility', 0), ('content-utility', 1), ('throughput', 1),
        ('throughput', 2), ('content-utility', 2)]
    root = tmp_path / 'run'; driver.save(root / 'plan.json', p)
    monkeypatch.setattr(driver, 'pinned_revision', lambda root: p['source_commit'])
    monkeypatch.setattr(driver, 'origin_evidence', lambda origin: (original, audit))
    monkeypatch.setattr(driver, 'native_sources', lambda source: sources)
    monkeypatch.setattr(driver, 'prerequisite_binding', lambda directory: p['prerequisite'])
    assert driver.require_plan(root) == driver.read(root / 'plan.json')
    changed = clone(p); changed['budget']['candidate_slots'] = 7
    other = tmp_path / 'changed'; driver.save(other / 'plan.json', changed)
    with pytest.raises(ValueError, match='reconstruction'):
        driver.require_plan(other)


def test_batched_source_check_reads_actual_git_blobs_and_rechecks_local_bytes(monkeypatch):
    import hashlib
    import subprocess
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=driver.ROOT, text=True).strip()
    proof = driver.native_sources(source)
    assert len(proof['literal_files']) > 200
    for name in ('utopia/optimization/native_factory.py', 'utopia/system/native_kernel.py',
            'scripts/native_benchmark_physical.py'):
        raw = subprocess.check_output(['git', 'show', source + ':' + name], cwd=driver.ROOT)
        assert proof['literal_files'][name] == hashlib.sha256(raw).hexdigest()
    read_bytes = Path.read_bytes
    def changed(path):
        raw = read_bytes(path)
        return raw + b'\n# injected local drift\n' if path == driver.ROOT / 'utopia/optimization/native_factory.py' else raw
    monkeypatch.setattr(Path, 'read_bytes', changed)
    with pytest.raises(ValueError, match='source differs'):
        driver.native_sources(source)


def test_no_reference_fallback_when_all_own_generations_are_null(tmp_path, monkeypatch):
    p, _, _, _ = setup(tmp_path, monkeypatch)
    seal(p)
    monkeypatch.setattr(driver, 'campaign', lambda *a: SimpleNamespace(state={
        'pending': None, 'records': [{'observations': []}, {'observations': []}, {'observations': []}]}))
    result = driver.selection(tmp_path, p, {})
    assert not result['baseline_fallback']
    assert all(r['system'] is None and r['loss'] is None and not r['all_tied_ids'] for r in result['selected'].values())


def test_prerequisite_rejection_occurs_before_any_study_start_or_author(tmp_path, monkeypatch):
    root = tmp_path / 'run'; root.mkdir()
    monkeypatch.setattr(driver, 'require_environment', lambda: None)
    monkeypatch.setattr(driver, 'require_plan', lambda root: {'prerequisite': {'SCRIPTED': True}})
    def forbidden(binding): raise ValueError('numeric continuation is still active')
    monkeypatch.setattr(driver, 'require_prerequisite', forbidden)
    monkeypatch.setattr(driver, 'WorkflowDesigner', lambda *a, **k: pytest.fail('must not construct an author'))
    with pytest.raises(ValueError, match='still active'): driver.run(root)
    assert not list(root.iterdir())


def test_runner_forwards_the_actual_trusted_measurement_contract_to_advance(tmp_path, monkeypatch):
    p, _, _, _ = setup(tmp_path, monkeypatch); seal(p)
    root = tmp_path / 'run'; root.mkdir(); seen = []
    class StopAfterContractCheck(BaseException): pass
    class Campaign:
        state = {'pending': None, 'records': []}
        def _validate(self): return {}
        def _request(self, *a): return {'SCRIPTED': 'unit request, no actual author/certificate'}
        def advance(self, **kwargs):
            assert kwargs['measurement_contract'] == p['observer_contract']
            assert callable(kwargs['measurement_adapter']) and kwargs['count'] == 1
            seen.append('exact-contract-forwarded')
            raise StopAfterContractCheck()
    monkeypatch.setattr(driver, 'require_environment', lambda: None)
    monkeypatch.setattr(driver, 'require_plan', lambda root: p)
    monkeypatch.setattr(driver, 'require_prerequisite', lambda p: {})
    monkeypatch.setattr(driver, 'campaign', lambda *a, **k: Campaign())
    monkeypatch.setattr(driver, 'WorkflowDesigner', lambda *a, **k: SimpleNamespace(
        calibrate=lambda *a: tmp_path / 'SCRIPTED-certificate-not-used-by-unit-advance'))
    monkeypatch.setattr(driver, 'CommonContentObserver', lambda *a, **k: SimpleNamespace())
    monkeypatch.setattr(driver, 'LocalObserverBackend', lambda **k: None)
    monkeypatch.setattr(driver, 'factory_for', lambda *a: lambda *a: pytest.fail('no native world in unit fixture'))
    monkeypatch.setattr(driver, 'measurement', lambda *a: lambda *a: pytest.fail('no measurement in unit fixture'))
    monkeypatch.setattr(driver, 'build_context', lambda *a, **k: {})
    def observed(s, **kwargs):
        return SimpleNamespace(to_dict=lambda: {'status': 'complete', 'metadata': {'measurements': [{
            'metrics': {'native.accepted_decisions': {'status': 'measured', 'value': 1},
                'native.common_content_utility_sum': {'status': 'measured', 'value': 1}}}]}})
    monkeypatch.setattr(driver, 'evaluate_native_suggestion', observed)
    with pytest.raises(StopAfterContractCheck): driver.run(root)
    assert seen == ['exact-contract-forwarded']
    assert driver.read(root / 'terminal.json')['status'] == 'stopped'


@pytest.mark.parametrize('bad', ['active', 'stopped', 'unequal-audit', 'unequal-cost', 'unequal-report'])
def test_queue_guard_requires_absence_and_original_matching_normal_closure(tmp_path, monkeypatch, bad):
    root = tmp_path / 'chain'; root.mkdir()
    driver.save(root / 'started.json', {'schema': 'scienceutopia.native-parameter-comparator-chain.v1',
        'pid': 12345, 'numeric_source_commit': 'a' * 40})
    binding = driver.prerequisite_binding(root)
    audit = {'schema': 'scienceutopia.native-parameter-comparator-audit.v1', 'source_commit': 'a' * 40,
        'source_proof': {'status': 'verified-exact-source-closure'}, 'closure': {'terminal': {'status': 'closed'}}}
    for i in (1, 2): driver.save(root / ('audit-' + str(i) + '.json'), audit)
    for i in (1, 2):
        (root / ('costs-' + str(i) + '.json')).write_text('{}')
        report = root / ('report-' + str(i)); report.mkdir(); (report / 'data.txt').write_text('SCRIPTED')
    files = same_files(root / 'report-1', root / 'report-2')
    end = {'status': 'closed', 'steps': [{'exit_code': 0}] * 7, 'report_files': files}
    monkeypatch.setattr('scripts.run_pre_scale_completion_chain_v1.process_identity', lambda pid: None)
    if bad == 'active':
        monkeypatch.setattr('scripts.run_pre_scale_completion_chain_v1.process_identity', lambda pid: 'original active process')
    elif bad == 'stopped': end['status'] = 'stopped'
    elif bad == 'unequal-audit':
        path = root / 'audit-2.json'; changed = clone(audit); changed['source_commit'] = 'b' * 40
        path.write_text(json.dumps(seal(changed)))
    elif bad == 'unequal-cost': (root / 'costs-2.json').write_text('{"changed":true}')
    else: (root / 'report-2/data.txt').write_text('changed')
    driver.save(root / 'ended.json', end)
    with pytest.raises(ValueError): driver.require_prerequisite(binding)
