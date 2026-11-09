"""Synthetic closed-record guard tests; no model, Docker or scientific result."""
from copy import deepcopy
import json

import pytest

from scripts.audit_pre_scale_search_v1 import actual_policy_order,forward_evidence,main,stage_receipt
from scripts.run_pre_scale_search_v1 import evaluation_jobs
from tests.reports.test_pre_scale_search_v1 import plan
from utopia.system.design_patch import digest


def saved(value):return {**value,'content_sha256':digest(value)}


def closed_stage(root,stage='search'):
    start={'stage':stage,'plan_sha256':'a'*64,'pid':123,
        'schema':'scienceutopia.pre-scale-search.v1.stage-start','started_utc':'2026-11-09T00:00:00+00:00'}
    end=saved({**start,'status':'closed','ended_utc':'2026-11-09T00:01:00+00:00'})
    start=saved(start)
    (root/(stage+'.started.json')).write_text(json.dumps(start))
    (root/(stage+'.ended.json')).write_text(json.dumps(end))
    return start,end


def test_normal_stage_requires_matching_exact_start_and_finite_chronology(tmp_path):
    start,end=closed_stage(tmp_path)
    assert stage_receipt(tmp_path,'search','a'*64)=={'started':start,'ended':end}
    for changes in ({'pid':124},{'status':'stopped'},{'ended_utc':'2026-11-08T00:00:00+00:00'}):
        core={k:v for k,v in end.items() if k!='content_sha256'}
        (tmp_path/'search.ended.json').write_text(json.dumps(saved({**core,**changes})))
        with pytest.raises(ValueError,match='closure'):stage_receipt(tmp_path,'search','a'*64)


def test_corrupted_stage_hash_is_rejected_before_interpreting_a_closed_status(tmp_path):
    _,end=closed_stage(tmp_path)
    (tmp_path/'search.ended.json').write_text(json.dumps({**end,'content_sha256':'0'*64}))
    with pytest.raises(ValueError,match='content changed'):stage_receipt(tmp_path,'search','a'*64)


def test_unavailable_objective_does_not_erase_a_complete_native_forward():
    o={'status':'failed','loss':None,'metadata':{'runs':[{'actual':'receipt'}],
        'measurements':[{'actual':'measured-other-metrics'}],'technical_failures':[]}}
    assert forward_evidence(o)
    assert not forward_evidence({'status':'failed','loss':None,
        'metadata':{'runs':[],'measurements':[],'technical_failures':[{'technical':'failure'}]}})
    with pytest.raises(ValueError,match='imputed'):
        forward_evidence({**o,'loss':0.})
    with pytest.raises(ValueError,match='ambiguous'):
        forward_evidence({**o,'metadata':{**o['metadata'],'runs':[]}})


def selection_and_jobs():
    p=plan();s={'plan_sha256':p['content_sha256'],
        'selected':{arm:{'system':deepcopy(p['reference_systems']['open-seed'])} for arm in p['arm_order']}}
    s['content_sha256']=digest(s)
    return p,s,evaluation_jobs(p,s)


def test_shared_physical_jobs_are_not_extra_independent_observations():
    p,s,jobs=selection_and_jobs()
    rows=actual_policy_order(p,s,jobs)
    assert len(rows)==36 and len(jobs)==12
    selected=[r for r in rows if r['label'].startswith('selected:')]
    assert len(selected)==24 and len({r['physical_job'] for r in selected})==3
    assert sorted(r['seed'] for r in selected)==sorted(p['evaluation']['seeds']*8)


@pytest.mark.parametrize('error',['duplicate','missing','wrong-label','wrong-seed','wrong-policy'])
def test_invalid_shared_evaluation_lineage_is_rejected(error):
    p,s,jobs=selection_and_jobs()
    if error=='duplicate':jobs.append(deepcopy(jobs[0]))
    if error=='missing':jobs.pop()
    if error=='wrong-label':jobs[0]['labels'].append('selected:does-not-exist')
    if error=='wrong-seed':jobs[0]['seed']=99999
    if error=='wrong-policy':jobs[0]['policy_sha256']='c'*64
    with pytest.raises(ValueError):actual_policy_order(p,s,jobs)


def test_running_writer_is_rejected_before_subprocess_or_model(tmp_path,monkeypatch):
    monkeypatch.setattr('sys.argv',['audit','--run',str(tmp_path),'--output',str(tmp_path/'out.json'),
        '--frozen-source',str(tmp_path)])
    monkeypatch.setattr('subprocess.run',lambda *a,**kw:pytest.fail('must not audit an active study'))
    with pytest.raises(ValueError,match='closed study'):main()
