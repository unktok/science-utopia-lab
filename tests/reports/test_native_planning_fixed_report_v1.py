"""SCRIPTED full-label projections; no actual optimization or held-out claim."""
from types import SimpleNamespace

import pytest

from scripts import audit_native_planning_fixed_evaluation_v1 as audit_module
from scripts import finish_native_planning_fixed_report_v1 as finish
from scripts.reports import native_objective_fixed_evaluation_v1 as shared
from scripts.reports import native_planning_fixed_evaluation_v1 as module
from scripts.run_native_planning_fixed_evaluation_v1 import read, save
from scripts.analyze_native_open_v7 import _inventory
from tests.reports.test_native_objective_fixed_audit_v1 import setup
from tests.reports.test_native_objective_fixed_evaluation_v1 import seal
from utopia.system.design_patch import clone


def evidence(tmp_path, monkeypatch):
    root, p = setup(tmp_path, monkeypatch, planning=True)
    path = tmp_path / 'audit.json'; audit_module.worker(root, path)
    return root, p, read(path)


def test_every_reference_selected_null_and_shared_physical_policy_survives(tmp_path, monkeypatch):
    _, p, a = evidence(tmp_path, monkeypatch)
    r = shared.summarize(p, a, study='planning-v1')
    assert len(r['physical_worlds']) == 16 and len(r['logical_rows']) == 20
    assert len(r['paired_differences']) == 32 and len(r['reference_labels']) == 8
    assert len([v for v in r['logical_rows'] if v['status'] == 'no-completed-submission']) == 2
    same = [v for v in r['paired_differences'] if v['label'] == 'selected:throughput'
            and v['reference'] == 'cut-reserve21-all']
    assert all(v['same_physical_job'] for v in same)
    assert same[0]['differences'] == {'throughput': None, 'content-utility': None}
    assert same[1]['differences'] == {'throughput': 0., 'content-utility': 0.}
    assert r['fixed_selection'] == p['fixed_selection']
    with pytest.raises(ValueError): shared.summarize(p, a)  # Never an old-study alias.


@pytest.mark.parametrize('change', ['selection', 'score', 'missing-reference', 'job-label', 'unused'])
def test_modified_fixed_evaluation_never_acquires_a_report(tmp_path, monkeypatch, change):
    _, p, a = evidence(tmp_path, monkeypatch)
    if change == 'selection': a['fixed_selection']['selected']['throughput']['selected_id'] = 'reselected'
    elif change == 'score': a['worlds'][0]['scores']['throughput'] = -999
    elif change == 'missing-reference': p['evaluation']['reference_labels'].pop(); seal(p); a['plan_sha256'] = p['content_sha256']
    elif change == 'job-label': a['worlds'][0]['labels'].append('selected:unplanned')
    else: a['held_out_world_seeds'] = False
    seal(a)
    with pytest.raises(ValueError): shared.summarize(p, a, study='planning-v1')


def test_double_export_is_read_only_and_keeps_all_eight_files(tmp_path, monkeypatch):
    root, _, a = evidence(tmp_path, monkeypatch)
    paths = [tmp_path / 'one.json', tmp_path / 'two.json']
    for path in paths: save(path, {k: v for k, v in a.items() if k != 'content_sha256'})
    outputs = [tmp_path / 'out-one', tmp_path / 'out-two']; before = _inventory(root)
    for output in outputs:
        module.export(SimpleNamespace(run=root, audit_one=paths[0], audit_two=paths[1], output=output))
    assert before == _inventory(root) and len(list(outputs[0].iterdir())) == 8
    assert {f.name: f.read_bytes() for f in outputs[0].iterdir()} == {f.name: f.read_bytes() for f in outputs[1].iterdir()}


def test_finish_binds_new_plan_and_normal_closure(monkeypatch):
    seen = {}; monkeypatch.setattr(finish, 'finish', lambda args, **kw: seen.update(kw))
    finish.run(SimpleNamespace())
    assert seen['plan_schema'] == 'scienceutopia.native-planning-fixed-evaluation.v1.plan'
    assert seen['preceding_schema'] == 'scienceutopia.native-planning-fixed-evaluation-finish.v1'
    assert seen['report_module'] == 'scripts.reports.native_planning_fixed_evaluation_v1'
