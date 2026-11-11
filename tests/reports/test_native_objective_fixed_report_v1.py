"""All-seed projection with scripted physical proofs and literal extra metrics."""
from types import SimpleNamespace

import pytest

from scripts import audit_native_objective_fixed_evaluation_v1 as audit_module
from scripts.reports import native_objective_fixed_evaluation_v1 as module
from tests.reports.test_native_objective_fixed_audit_v1 import setup
from tests.reports.test_native_objective_fixed_evaluation_v1 import seal
from utopia.system.design_patch import clone


def evidence(tmp_path,monkeypatch):
    root,p=setup(tmp_path,monkeypatch);path=tmp_path/'audit.json';audit_module.worker(root,path)
    return root,p,module.checked(__import__('json').loads(path.read_text()))


def test_every_logical_seed_unavailable_arm_alias_and_null_pair_survives(tmp_path,monkeypatch):
    root,p,a=evidence(tmp_path,monkeypatch);a['worlds'].reverse();seal(a)
    r=module.summarize(p,a)
    assert len(r['physical_worlds'])==15 and len(r['logical_rows'])==21 and len(r['paired_differences'])==30
    assert len([v for v in r['logical_rows'] if v['status']=='no-completed-submission'])==3
    rows=[v for v in r['paired_differences'] if v['label']=='selected:throughput' and v['reference']=='reviewed-all-connected']
    assert all(v['same_physical_job'] for v in rows)
    assert rows[0]['differences']=={'throughput':None,'content-utility':None}
    assert all(v['differences']=={'throughput':0.,'content-utility':0.} for v in rows[1:])
    assert r['fixed_selection']==p['fixed_selection'] and not r['interpretation']['candidate_reselection']


@pytest.mark.parametrize('change',['score','physical-label','duplicate-world','selection','job','closed','truth'])
def test_fixed_report_rejects_modified_evidence(tmp_path,monkeypatch,change):
    root,p,a=evidence(tmp_path,monkeypatch)
    if change=='score':a['worlds'][0]['scores']['content-utility']=999
    elif change=='physical-label':a['worlds'][0]['labels'].append('invented-policy')
    elif change=='duplicate-world':a['worlds'].append(clone(a['worlds'][0]))
    elif change=='selection':a['fixed_selection']['selected']['throughput']['selected_id']='reselected'
    elif change=='job':p['jobs'][0]['system']['initial_state']['SCRIPTED-extra']=1;seal(p);a['plan_sha256']=p['content_sha256']
    elif change=='closed':a['closure']['terminal']['status']='stopped'
    else:a['held_out_world_seeds']=False
    seal(a)
    with pytest.raises(ValueError):module.summarize(p,a)


def test_actual_export_twice_keeps_raw_unchanged_and_all_eight_files_match(tmp_path,monkeypatch):
    from scripts.analyze_native_open_v7 import _inventory
    root,p,a=evidence(tmp_path,monkeypatch);paths=[tmp_path/'one.json',tmp_path/'two.json']
    for path in paths:module.save(path,{k:v for k,v in a.items() if k!='content_sha256'})
    outputs=[tmp_path/'out-one',tmp_path/'out-two'];before=_inventory(root)
    for output in outputs:module.export(SimpleNamespace(run=root,audit_one=paths[0],audit_two=paths[1],output=output))
    assert before==_inventory(root)
    assert len(list(outputs[0].iterdir()))==8
    assert {f.name:f.read_bytes() for f in outputs[0].iterdir()}=={f.name:f.read_bytes() for f in outputs[1].iterdir()}
