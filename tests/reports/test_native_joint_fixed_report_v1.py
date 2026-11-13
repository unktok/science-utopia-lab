"""Complete logical/physical readouts; fabricated scores are SCRIPTED fixtures."""
import json
from types import SimpleNamespace

import pytest

from scripts import run_native_joint_fixed_evaluation_v1 as driver
from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_joint_fixed_evaluation_v1 import export
from scripts.reports.native_objective_fixed_evaluation_v1 import summarize
from tests.reports.test_native_joint_fixed_evaluation_v1 import evidence,seal
from utopia.optimization.loss import evaluate_loss
from utopia.system.design_patch import clone,digest


def fixture(tmp_path,monkeypatch):
    _,p=evidence(tmp_path,monkeypatch)
    p['scientist']['dataset_identity']={'dataset':'SCRIPTED-joint-score-fixture'};seal(p)
    p['jobs']=driver.jobs_for(p);seal(p)
    worlds=[]
    for i,job in enumerate(p['jobs']):
        metrics={'native.accepted_decisions':{'status':'measured','value':i%5},
            'native.common_content_utility_sum':{'status':'measured','value':(i%7)/3}}
        measurements=[{'run_id':'SCRIPTED-'+job['identity'],'metrics':metrics}]
        scores={k:evaluate_loss(v,measurements)['loss'] for k,v in p['losses'].items()}
        worlds.append({**clone(job),'role':'selection-fixed-evaluation','status':'complete',
            'measurements':measurements,'scores':scores})
    a=seal({'schema':'scienceutopia.native-joint-fixed-evaluation-audit.v1','source_commit':p['source_commit'],
        'plan_sha256':p['content_sha256'],'closure':{'terminal':{'status':'closed','completed_jobs':len(p['jobs'])}},
        'source_proof':{'status':'verified-exact-source-closure','SCRIPTED':True},
        'held_out_world_seeds':True,'fixed_selection':clone(p['fixed_selection']),
        'origin_audit_content_sha256':clone(p['origin_audit_content_sha256']),'worlds':worlds,
        'new_model_calls':0,'new_code_executions':0})
    return p,a


def test_every_label_seed_reference_difference_declared_contrast_and_missing_pool(tmp_path,monkeypatch):
    p,a=fixture(tmp_path,monkeypatch);r=summarize(p,a,study='joint-v1')
    assert r['score_order']==['throughput','content-utility']
    assert len(r['labels'])==16 and len(r['logical_rows'])==32 and len(r['physical_worlds'])==18
    assert len(r['paired_differences'])==128 and len(r['fixed_policy_contrasts'])==16
    nulls=[row for row in r['logical_rows'] if row['label']=='selected:numeric:content-utility']
    assert len(nulls)==2 and all(row['physical_job'] is None and row['scores']=={k:None for k in p['losses']} for row in nulls)
    by={(row['label'],row['seed']):row for row in r['logical_rows']}
    for row in r['fixed_policy_contrasts']:
        left,right=by['selected:'+row['left'],row['seed']],by['selected:'+row['right'],row['seed']]
        assert row['same_physical_job']==(left['physical_job'] is not None and left['physical_job']==right['physical_job'])
        for objective in p['objectives']:
            x,y=left['scores'][objective],right['scores'][objective]
            assert row['differences'][objective]==(None if x is None or y is None else x-y)
    assert any(row['same_physical_job'] for row in r['fixed_policy_contrasts'])
    assert any(row['differences']['throughput'] is None for row in r['fixed_policy_contrasts'])
    assert not r['interpretation']['candidate_reselection'] and not r['interpretation']['missing_losses_imputed']
    assert not r['interpretation']['independent_optimizer_replications']


@pytest.mark.parametrize('changed',['label-order','contrast','selection','job','score','world-missing','duplicate-world','closed'])
def test_changed_scope_selection_jobs_or_scores_rejected(tmp_path,monkeypatch,changed):
    p,a=fixture(tmp_path,monkeypatch)
    if changed=='label-order':p['selection_order'].pop()
    elif changed=='contrast':p['contrasts'][0]['left']='numeric:throughput'
    elif changed=='selection':a['fixed_selection']['selected']['planning:throughput']['selected_id']='different'
    elif changed=='job':a['worlds'][0]['labels']=[]
    elif changed=='score':a['worlds'][0]['scores']['throughput']=42
    elif changed=='world-missing':a['worlds'].pop()
    elif changed=='duplicate-world':a['worlds'].append(clone(a['worlds'][0]))
    else:a['closure']['terminal']['status']='stopped'
    seal(p);seal(a)
    with pytest.raises(ValueError):summarize(p,a,study='joint-v1')


def test_two_complete_exports_match_with_all_nulls_sharing_and_qa_watermark(tmp_path,monkeypatch):
    p,a=fixture(tmp_path/'inputs',monkeypatch);root=tmp_path/'evaluation';root.mkdir()
    driver.save(root/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    a['raw_inventory_sha256']=digest(_inventory(root));seal(a)
    paths=[tmp_path/'audit-1.json',tmp_path/'audit-2.json']
    for path in paths:driver.save(path,{k:v for k,v in a.items() if k!='content_sha256'})
    before=_inventory(root);outs=[tmp_path/'report-1',tmp_path/'report-2']
    for out in outs:export(SimpleNamespace(run=root,audit_one=paths[0],audit_two=paths[1],output=out))
    assert {v.name:v.read_bytes() for v in outs[0].iterdir()}=={v.name:v.read_bytes() for v in outs[1].iterdir()}
    assert len(list(outs[0].iterdir()))==9
    assert _inventory(root)==before
    for name in ('joint-policy-seed-scores.svg','joint-fixed-contrasts.svg'):
        assert 'SCRIPTED SOFTWARE QA' in (outs[0]/name).read_text()
    assert len((outs[0]/'logical-scores.csv').read_text().splitlines())==33
    assert len((outs[0]/'fixed-contrasts.csv').read_text().splitlines())==17
    assert json.loads((outs[0]/'report.json').read_text())['interpretation']['candidate_reselection'] is False
