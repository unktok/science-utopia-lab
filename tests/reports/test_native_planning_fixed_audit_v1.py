"""SCRIPTED cold joins, including unavailable completed-world measurements."""
import pytest

from scripts import audit_native_planning_fixed_evaluation_v1 as module
from scripts import run_native_planning_fixed_evaluation_v1 as driver
from scripts import audit_native_objective_fixed_evaluation_v1 as shared
from scripts.analyze_native_open_v7 import _inventory
from tests.reports.test_native_objective_fixed_audit_v1 import setup


def test_two_cold_joins_keep_all_16_jobs_null_and_same_critic_contract(tmp_path, monkeypatch):
    root, p = setup(tmp_path, monkeypatch, planning=True); before = _inventory(root)
    paths = [tmp_path / 'one.json', tmp_path / 'two.json']
    for path in paths: module.worker(root, path)
    assert paths[0].read_bytes() == paths[1].read_bytes() and _inventory(root) == before
    report = driver.read(paths[0])
    assert report['schema'] == 'scienceutopia.native-planning-fixed-evaluation-audit.v1'
    assert len(report['worlds']) == len(p['jobs']) == 16
    assert report['worlds'][0]['status'] == 'failed'
    assert report['worlds'][0]['physical_proof']['status'] == 'complete'
    assert report['worlds'][0]['measurements'] == []
    assert report['observer'] == driver.read(root / 'observer-audit.json')
    assert report['held_out_world_seeds'] and not report['independent_optimizer_replications']
    with pytest.raises(ValueError, match='explicit known'): shared.worker(root, tmp_path / 'bad.json', study='unknown')


@pytest.mark.parametrize('change', ['dispatch', 'seed', 'score', 'stopped', 'extra-designer'])
def test_changed_fixed_planning_evidence_never_becomes_a_complete_audit(tmp_path, monkeypatch, change):
    root, _ = setup(tmp_path, monkeypatch, planning=True)
    if change == 'extra-designer':
        driver.save(root / 'unexpected/wire/dispatch-000.intent.json', {'SCRIPTED': 'not a permitted author'})
    else:
        if change == 'dispatch': path = next((root / 'evaluation').glob('*/started.json')); data = driver.read(path); data['seed'] = -1
        elif change == 'seed': path = root / 'pre-dispatch-seed-usage-00.json'; data = driver.read(path); data['valid'] = False
        elif change == 'score': path = next((root / 'evaluation').glob('*/cross-scores.json')); data = driver.read(path); data['throughput']['loss'] = 999
        else: path = root / 'terminal.json'; data = driver.read(path); data['status'] = 'stopped'
        path.unlink(); driver.save(path, {k: v for k, v in data.items() if k != 'content_sha256'})
    with pytest.raises(ValueError): module.worker(root, tmp_path / 'must-not-pass.json')
