"""Synthetic closed evidence only: no native runs, model calls or real scores."""
import json
from types import SimpleNamespace

import pytest

from scripts import run_native_fixed_candidate_evaluation_v1 as driver
from scripts.reports import native_fixed_evaluation_v1 as module
from tests.reports.test_native_fixed_candidate_evaluation_v1 import inputs
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import clone,digest


def seal(value):
    value.pop('content_sha256',None);value['content_sha256']=digest(value);return value


def fixture():
    original,origin,usages=inputs()
    p=seal(driver.build_plan(original,origin,source='c'*40,origin={},usages=usages));worlds=[]
    for job in p['jobs']:
        metrics={k:{'value':v,'status':'measured'} for k,v in {
            'native.accepted_decisions':2,'native.accepted_peer_score_sum':7.,'native.review_records':3}.items()}
        measurement={'measurement_schema':'scienceutopia.native-domain-measurements.v1','metrics':metrics,
            'run_id':job['identity'],'system_fingerprint':digest(job['system'])}
        scores={k:evaluate_loss(v,[measurement])['loss'] for k,v in p['losses'].items()}
        worlds.append({**clone(job),'status':'complete','role':'selection-fixed-evaluation',
            'scores':scores,'physical_proof':{'measurement':measurement}})
    a=seal({'schema':'scienceutopia.native-fixed-candidate-evaluation-audit.v1',
        'source_commit':p['source_commit'],'plan_sha256':p['content_sha256'],
        'closure':{'terminal':{'status':'closed','completed_jobs':len(worlds)}},
        'source_proof':{'status':'verified-exact-source-closure'},'worlds':worlds,
        'fixed_selection':clone(p['fixed_selection']),'origin_audit_content_sha256':origin['content_sha256'],
        'original_search_status':'stopped','new_model_calls':0,'new_code_executions':0})
    return p,a,original,origin


def test_all_slots_missing_arms_paired_scores_and_shared_jobs_remain_visible():
    p,a,o,b=fixture();r=module.summarize(p,a,o,b)
    assert len(r['search_slots'])==12 and r['search_slots'][-1]['status']=='not-submitted'
    assert r['search_slots'][-1]['loss'] is None and r['search_slots'][-1]['physical_job'] is None
    assert len(r['evaluation_rows'])==36 and r['unavailable_label_seed_rows']==6
    assert r['physical_evaluation_worlds']==len(p['jobs'])<30
    assert sum(x['physical_job'] is not None for x in r['evaluation_rows'])==30
    assert any(x['shared_same_physical_job'] for x in r['paired_reference_differences'])
    for label,scores in r['evaluation_summary'].items():
        if 'code-and-graph' in label:
            assert all(v['mean'] is None and v['available']==0 for v in scores.values())
    assert not r['interpretation']['publication_ready']
    assert not r['interpretation']['baseline_fallback']


@pytest.mark.parametrize('change', ['closure','plan','origin','extra-world','score','label','measurement','system-id','role'])
def test_closed_report_rejects_changed_bindings_counts_and_literal_measurements(change):
    p,a,o,b=fixture()
    if change=='closure':a['closure']['terminal']['status']='stopped'
    elif change=='plan':a['plan_sha256']='0'*64
    elif change=='origin':a['origin_audit_content_sha256']='0'*64
    elif change=='extra-world':a['worlds'].append(clone(a['worlds'][0]))
    elif change=='score':a['worlds'][0]['scores']['efficiency']+=1
    elif change=='label':a['worlds'][0]['labels'].append('selected:invented')
    elif change=='measurement':a['worlds'][0]['physical_proof']['measurement']['metrics']['native.review_records']['value']+=1
    elif change=='system-id':a['worlds'][0]['physical_proof']['measurement']['system_fingerprint']='0'*64
    else:a['worlds'][0]['role']='search:invented'
    seal(a)
    with pytest.raises(ValueError):module.summarize(p,a,o,b)


def test_changed_stopped_prefix_slot_cannot_be_given_a_fabricated_loss():
    p,a,o,b=fixture();b['closure']['progress']['candidate_slots'][-1]['loss']=999
    seal(b);p['origin_audit_content_sha256']=b['content_sha256']
    p['fixed_selection']['all_attempts']=clone(b['closure']['progress']['candidate_slots'])
    seal(p);a.update(plan_sha256=p['content_sha256'],origin_audit_content_sha256=b['content_sha256'],
        fixed_selection=clone(p['fixed_selection']));seal(a)
    with pytest.raises(ValueError,match='chronological world'):module.summarize(p,a,o,b)


def test_portable_export_rebuilds_figures_and_csv_identically_without_raw_worlds(tmp_path):
    p,a,o,b=fixture()
    for name,value in [('plan',p),('audit-one',a),('audit-two',a),('original-plan',o),('origin-audit',b)]:
        save(tmp_path/(name+'.json'),{k:v for k,v in value.items() if k!='content_sha256'})
    args=SimpleNamespace(**{name.replace('-','_'):tmp_path/(name+'.json') for name in
        ('plan','audit-one','audit-two','original-plan','origin-audit')})
    for suffix in ('a','b'):
        args.output=tmp_path/suffix;module.export(args)
    expected={'report.json','manifest.json','physical-components.csv','stopped-search-paths.png',
        'stopped-search-paths.svg','selection-fixed-common-scores.png','selection-fixed-common-scores.svg'}
    assert {p.name for p in (tmp_path/'a').iterdir()}==expected
    assert all((tmp_path/'a'/name).read_bytes()==(tmp_path/'b'/name).read_bytes() for name in expected)
    with pytest.raises(ValueError,match='fresh report'):module.export(args)


def test_two_nonidentical_cold_audits_stop_export_before_creating_output(tmp_path):
    p,a,o,b=fixture()
    args=SimpleNamespace(**{name.replace('-','_'):tmp_path/(name+'.json') for name in
        ('plan','audit-one','audit-two','original-plan','origin-audit')},output=tmp_path/'out')
    for name,value in [('plan',p),('audit-one',a),('audit-two',a),('original-plan',o),('origin-audit',b)]:
        save(tmp_path/(name+'.json'),{k:v for k,v in value.items() if k!='content_sha256'})
    args.audit_two.write_text(args.audit_two.read_text()+'\n')
    with pytest.raises(ValueError,match='cold evaluation audits differ'):module.export(args)
    assert not args.output.exists()
