"""SCRIPTED fixed T/P joins/exports; not actual Qwen evaluation or new evidence."""
from types import SimpleNamespace

import pytest

from scripts import audit_native_capacity_fixed_evaluation_v1 as auditor
from scripts.reports import native_objective_fixed_evaluation_v1 as core
from scripts.reports import native_capacity_fixed_evaluation_v1 as module
from tests.reports.test_native_capacity_fixed_evaluation_audit_v1 import setup
from tests.reports.test_native_objective_fixed_evaluation_v1 import seal
from utopia.system.design_patch import clone


def evidence(tmp_path,monkeypatch):
    root,p=setup(tmp_path,monkeypatch);path=tmp_path/'audit.json';auditor.worker(root,path)
    return root,p,core.checked(__import__('json').loads(path.read_text()))


def test_all_controls_null_selection_cross_scores_and_shared_physical_jobs_are_retained(tmp_path,monkeypatch):
    _,p,a=evidence(tmp_path,monkeypatch);a['worlds'].reverse();seal(a)
    r=core.summarize(p,a,study='capacity-v1')
    assert r['schema']=='scienceutopia.native-capacity-fixed-report.v1'
    assert r['score_order']==['throughput','founder-activity']
    assert len(r['physical_worlds'])==10 and len(r['logical_rows'])==14
    assert len(r['paired_differences'])==20
    assert len([v for v in r['logical_rows'] if v['status']=='no-completed-submission'])==2
    assert r['fixed_selection']==p['fixed_selection'] and not r['interpretation']['candidate_reselection']
    rows=[v for v in r['paired_differences'] if v['label']=='selected:throughput'
          and v['reference']=='reviewed-all-equalization']
    assert len(rows)==2 and all(v['same_physical_job'] for v in rows)
    assert all(v['differences']=={'throughput':0.,'founder-activity':0.} for v in rows)
    with pytest.raises(ValueError):core.summarize(p,a)  # old T/U scope stays strict


@pytest.mark.parametrize('change',['score','label','duplicate','selection','job','closed','heldout'])
def test_rejects_changed_fixed_capacity_observations(tmp_path,monkeypatch,change):
    _,p,a=evidence(tmp_path,monkeypatch)
    if change=='score':a['worlds'][0]['scores']['founder-activity']=999
    elif change=='label':a['worlds'][0]['labels'].append('invented')
    elif change=='duplicate':a['worlds'].append(clone(a['worlds'][0]))
    elif change=='selection':a['fixed_selection']['selected']['throughput']['selected_id']='new-choice'
    elif change=='job':p['jobs'][0]['system']['initial_state']['SCRIPTED-new']=1;seal(p);a['plan_sha256']=p['content_sha256']
    elif change=='closed':a['closure']['terminal']['status']='stopped'
    else:a['held_out_world_seeds']=False
    seal(a)
    with pytest.raises(ValueError):core.summarize(p,a,study='capacity-v1')


def test_actual_export_twice_preserves_all_csv_rows_and_exact_raw_bytes(tmp_path,monkeypatch):
    from scripts.analyze_native_open_v7 import _inventory
    root,_,a=evidence(tmp_path,monkeypatch);paths=[tmp_path/'one.json',tmp_path/'two.json']
    for path in paths:core.save(path,{k:v for k,v in a.items() if k!='content_sha256'})
    before=_inventory(root);outs=[tmp_path/'out-one',tmp_path/'out-two']
    for out in outs:module.export(SimpleNamespace(run=root,audit_one=paths[0],audit_two=paths[1],output=out))
    assert before==_inventory(root) and len(list(outs[0].iterdir()))==8
    assert {p.name:p.read_bytes() for p in outs[0].iterdir()}=={p.name:p.read_bytes() for p in outs[1].iterdir()}
    header=(outs[0]/'logical-scores.csv').read_text().splitlines()[0]
    assert 'founder-activity' in header and 'content-utility' not in header
