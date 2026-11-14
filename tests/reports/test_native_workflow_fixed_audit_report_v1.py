"""Cold branch and report units with explicitly SCRIPTED physical primitives."""
import json
from types import SimpleNamespace

import pytest

from scripts import audit_native_workflow_fixed_evaluation_v1 as auditor
from scripts import run_native_workflow_fixed_evaluation_v1 as driver
from scripts.reports import native_objective_fixed_evaluation_v1 as report
from scripts.reports import native_workflow_fixed_evaluation_v1 as exporter
from scripts.analyze_native_open_v7 import _inventory
from scripts.run_native_objective_instrument_loop_v1 import progress
from scripts.native_observer_physical_v1 import reconstruct_measurement
from tests.reports.test_native_workflow_fixed_evaluation_v1 import evidence
from tests.reports.test_native_planning_objective_loop_v1 import seal
from utopia.optimization.blackbox import Observation, Suggestion
from utopia.optimization.common_content_observer import CommonContentObserver
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.system import SystemSpec
from utopia.system.design_patch import clone


def setup(tmp_path, monkeypatch, *, both=False):
    _, _, p, usages, _ = evidence(tmp_path / 'input', monkeypatch, transport=True, both=both)
    root = tmp_path / 'raw'; root.mkdir(); (root / 'writer.lock').touch()
    u = usages[0]; u['checked_utc'] = '2026-11-14T01:00:00+00:00'; seal(u)
    p['evaluation']['seed_usage'] = [u['content_sha256']]; seal(p)
    for name in ('seed-usage-00.json', 'pre-dispatch-seed-usage-00.json'):
        driver.save(root / name, {k: v for k, v in u.items() if k != 'content_sha256'})
    driver.save(root / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    driver.save(root / 'started.json', {'schema': driver.SCHEMA + '.start', 'plan_sha256': p['content_sha256'],
        'started_utc': '2026-11-14T01:01:00+00:00'})
    driver.save(root / 'terminal.json', {'schema': driver.SCHEMA + '.terminal', 'status': 'closed',
        'completed_jobs': len(p['jobs']), 'ended_utc': '2026-11-14T01:04:00+00:00'})
    progress(root, 'closed'); observer = CommonContentObserver(root / 'observer', p['observer_contract'], backend=None)
    states = {}; proofs = {}; transport_calls = []; interval_calls = []; source_calls = []
    def interval(plan, spec, events, seed):
        assert driver.seeded_anchor(plan, seed).initial_state['seed'] == seed
        assert spec.initial_state['seed'] == seed
        interval_calls.append((spec.fingerprint, seed))
        return {'SCRIPTED': 'not native effect verification', 'seed': seed}
    monkeypatch.setattr(driver, 'interval', interval)
    for index, job in enumerate(p['jobs']):
        directory = root / 'evaluation' / job['identity']
        cell = directory / 'worlds' / (job['identity'] + '-s' + str(job['seed']))
        (cell / 'replies').mkdir(parents=True); (cell / 'replies/responses.sqlite').write_text('SCRIPTED cache primitive')
        checkpoint = cell / 'checkpoint.json'; checkpoint.write_text('SCRIPTED checkpoint primitive')
        spec = SystemSpec.from_dict(job['system'])
        base = {'run_id': cell.name, 'system_fingerprint': spec.fingerprint,
            'measurement_schema': 'scienceutopia.native-domain-measurements.v1', 'metrics': {
                'native.accepted_decisions': {'status': 'measured', 'value': 0},
                'native.accepted_peer_score_sum': {'status': 'measured', 'value': 0},
                'native.review_records': {'status': 'measured', 'value': 0}}}
        state = {'native_system': {'spec': job['system'], 'last_year': 4, 'events': []}, 'year': 4, 'phase': 5,
            'portable': {'contract': {'simulation': {'num_years': 4}}}, 'paper_tracker': {'papers': []}}
        failed = index == 0
        measurements = [] if failed else [{**reconstruct_measurement(state, base, observer),
            'native_workflow_interval': interval(p, spec, [], job['seed'])}]
        scores = {k: evaluate_loss(v, measurements) for k, v in p['losses'].items()}
        o = Observation('observed-' + job['identity'], job['identity'], job['system'],
            'failed' if failed else 'complete', scores['throughput']['loss'], {
                'system_fingerprint': spec.fingerprint, 'loss_spec_sha256': loss_spec_sha256(p['losses']['throughput']),
                'loss_evaluation': scores['throughput'], 'runs': [{'checkpoint_path': str(checkpoint)}],
                'measurements': measurements, 'technical_failures': [{'SCRIPTED': 'known null'}] if failed else []}).to_dict()
        suggestion = Suggestion(job['identity'], job['system'], 0, 'selection-fixed-evaluation')
        driver.save(directory / 'started.json', {**clone(job), 'suggestion': suggestion.to_dict(),
            'started_utc': '2026-11-14T01:02:00+00:00'})
        driver.save(directory / 'observation.json', o); driver.save(directory / 'cross-scores.json', scores)
        states[str(checkpoint)] = state; proofs[cell.name] = {'status': 'complete', 'measurement': base, 'SCRIPTED': True}
    interval_calls.clear()
    a = observer.audit(); driver.save(root / 'observer-audit.json', {k: v for k, v in a.items() if k != 'content_sha256'})
    monkeypatch.setattr(driver, 'require_plan', lambda root: p)
    def source(*args, **kwargs):
        source_calls.append(kwargs); return {'status': 'verified-exact-source-closure', 'SCRIPTED': True}
    monkeypatch.setattr('scripts.native_benchmark_source.source_proofs', source)
    monkeypatch.setattr('scripts.native_benchmark_physical.physical_proof', lambda cell, *a, **k: proofs[cell.name])
    monkeypatch.setattr('scripts.analyze_native_design_benchmark.loaded', lambda *a, **k: {'confirmed': True, 'SCRIPTED': True})
    monkeypatch.setattr('utopia.runtime.checkpointing.read_portable_checkpoint', lambda path: states[str(path)])
    monkeypatch.setattr('utopia.optimization.native_discrete_policy.verify_native_observation', lambda *a: None)
    def transported(cell, plan, spec, *, seed, failed):
        transport_calls.append((cell.name, seed, failed)); assert plan['scientist_transport']['http_timeout_seconds']['read'] == 900
    monkeypatch.setattr('utopia.optimization.native_scientist_transport_v1.require_cell_transport', transported)
    return root, p, source_calls, transport_calls, interval_calls


def audited(tmp_path, monkeypatch, *, both=False):
    root, p, source, transport, intervals = setup(tmp_path, monkeypatch, both=both)
    path = tmp_path / 'audit.json'; auditor.worker(root, path)
    return root, p, driver.read(path), source, transport, intervals


def test_cold_branch_binds_transport_operational_source_and_seeded_intervals(tmp_path, monkeypatch):
    _, p, a, source, transport, intervals = audited(tmp_path, monkeypatch)
    assert a['schema'] == 'scienceutopia.native-workflow-fixed-evaluation-audit.v1'
    assert len(a['worlds']) == len(transport) == 4 and len(intervals) == 3
    assert source[0]['resources'] == [driver.PROTOCOL, p['operational_protocol']['path']]
    assert 'scripts/run_native_workflow_fixed_evaluation_v1.py' in source[0]['scripts']
    assert [s for _, s, _ in transport] == [j['seed'] for j in p['jobs']]
    assert not a['new_model_calls'] and not a['new_code_executions']


def test_all_labels_seeds_shared_jobs_nulls_and_both_objective_contrasts(tmp_path, monkeypatch):
    _, p, a, *_ = audited(tmp_path, monkeypatch)
    r = report.summarize(p, a, study='workflow-v1')
    assert len(r['physical_worlds']) == 4 and len(r['logical_rows']) == 8 and len(r['paired_differences']) == 8
    assert len(r['objective_choice_differences']) == 2
    assert all(all(v is None for v in row['differences'].values()) for row in r['objective_choice_differences'])
    same = [v for v in r['paired_differences'] if v['label'] == 'selected:throughput' and v['reference'] == 'R7-original']
    assert all(v['same_physical_job'] for v in same)
    assert same[0]['differences'] == {'throughput': None, 'content-utility': None}
    assert same[1]['differences'] == {'throughput': 0., 'content-utility': 0.}
    assert r['fixed_selection'] == p['fixed_selection']
    with pytest.raises(ValueError): report.summarize(p, a)


def test_completed_both_objective_choices_have_known_paired_contrast_without_reselection(tmp_path, monkeypatch):
    _, p, a, *_ = audited(tmp_path, monkeypatch, both=True)
    r = report.summarize(p, a, study='workflow-v1')
    assert r['objective_choice_differences'][0]['differences'] == {'throughput': None, 'content-utility': None}
    assert r['objective_choice_differences'][1]['differences'] == {'throughput': 0., 'content-utility': 0.}
    assert not r['objective_choice_differences'][1]['same_physical_job']
    assert r['fixed_selection'] == p['fixed_selection']


@pytest.mark.parametrize('change', ['score', 'reference', 'selection', 'duplicate', 'heldout', 'interval'])
def test_mutated_evidence_rejected(tmp_path, monkeypatch, change):
    root, p, a, *_ = audited(tmp_path, monkeypatch)
    if change == 'score': a['worlds'][0]['scores']['throughput'] = -999
    elif change == 'reference': p['evaluation']['reference_labels'].pop(); seal(p); a['plan_sha256'] = p['content_sha256']
    elif change == 'selection': a['fixed_selection']['selected']['throughput']['selected_id'] = 'reselected'
    elif change == 'duplicate': a['worlds'].append(clone(a['worlds'][0]))
    elif change == 'heldout': a['held_out_world_seeds'] = False
    else:
        path = root / 'evaluation' / p['jobs'][1]['identity'] / 'observation.json'
        o = driver.read(path); o['metadata']['measurements'][0]['native_workflow_interval']['seed'] = 0
        # Deliberately corrupted test journal, not a repair of scientific data.
        path.write_text(json.dumps(seal(o)))
        with pytest.raises(ValueError, match='measurement differs'): auditor.worker(root, tmp_path / 'bad-audit.json')
        return
    seal(a)
    with pytest.raises(ValueError): report.summarize(p, a, study='workflow-v1')


def test_double_export_without_rendering_is_read_only_and_keeps_new_contrast_csv(tmp_path, monkeypatch):
    root, _, a, *_ = audited(tmp_path, monkeypatch)
    paths = [tmp_path / 'one.json', tmp_path / 'two.json']
    for path in paths: driver.save(path, {k: v for k, v in a.items() if k != 'content_sha256'})
    # Heavy plotting is intentionally deferred while another project owns CPU.
    monkeypatch.setattr(report, 'render', lambda r, out: None)
    before = _inventory(root); outputs = [tmp_path / 'out-one', tmp_path / 'out-two']
    for output in outputs: exporter.export(SimpleNamespace(run=root, audit_one=paths[0], audit_two=paths[1], output=output))
    assert before == _inventory(root)
    assert 'objective-choice-differences.csv' in {f.name for f in outputs[0].iterdir()}
    assert {f.name: f.read_bytes() for f in outputs[0].iterdir()} == {f.name: f.read_bytes() for f in outputs[1].iterdir()}
