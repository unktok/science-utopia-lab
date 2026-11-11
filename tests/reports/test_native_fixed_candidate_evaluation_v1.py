"""Finite evaluation orchestration QA; never real model/scientific results."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_native_fixed_candidate_evaluation_v1 as driver
from tests.reports.test_native_institution_loop_v1 import plan as original_plan
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import digest


def inputs():
    p = original_plan(); worlds = []
    for name in p['reference_order']:
        worlds.append({'identity':'reference-'+name, 'role':'developer-reference', 'status':'complete',
            'scores':{'throughput':-100, 'efficiency':-100}, 'system':deepcopy(p['reference_systems'][name])})
    rows = []
    for i, slot in enumerate(p['schedule'][:-1]):
        arm, g = slot['arm'], slot['generation']
        complete = 'parameters' in arm or (arm == 'throughput:code-fixed-graph' and g == 0) or (
            arm == 'efficiency:code-fixed-graph' and g == 1)
        w = {'identity':'SCRIPTED-'+str(i), 'role':'search:'+arm,
            'status':'complete' if complete else 'failed',
            'scores':{'throughput':-7 if complete else None, 'efficiency':-11 if complete else None},
            'system':deepcopy(p['reference_systems']['open-seed'])}
        worlds.append(w);rows.append({'arm':arm,'generation':g,'status':w['status'],
            'loss':w['scores'][p['assignments'][arm]['objective']]})
    a = {'schema':'scienceutopia.native-institution-loop-stopped-audit.v1',
        'source_commit':p['source_commit'], 'plan_sha256':p['content_sha256'], 'worlds':worlds,
        'source_proof':{'status':'verified-exact-source-closure'}, 'selection':None,'logical_evaluation':[],
        'new_model_calls':0,'new_code_executions':0,
        'closure':{'scientific_study_closed':False,'terminal':{'status':'stopped'},
            'unsubmitted_slots':1, 'next_unsubmitted_slot':p['schedule'][-1],
            'progress':{'candidate_slots':rows}}}
    a['content_sha256']=digest(a)
    usages = [{'valid':True,'errors':[],'prior_matching_runs':[],'seeds':list(driver.SEEDS),
        'root':'/SCRIPTED', 'content_sha256':'b'*64}]
    return p,a,usages


def test_selection_excludes_nulls_and_initial_reference_retains_all_actual_ties():
    p,a,_ = inputs(); s=driver.fixed_selection(p,a)
    assert not s['baseline_fallback'] and not s['common_initial_in_selection']
    assert s['unsubmitted_slots']==1 and len(s['all_attempts'])==11
    assert s['missing_slot']==p['schedule'][-1]
    assert sum(v['system'] is not None for v in s['selected'].values())==4
    for arm,v in s['selected'].items():
        if 'code-and-graph' in arm:
            assert v['system'] is None and v['loss'] is None and v['complete_candidates']==0
        else:
            assert v['selected_id'].startswith('SCRIPTED-')
    assert len(s['selected']['efficiency:parameters']['all_tied_ids'])==2


def test_all_failed_submissions_do_not_turn_into_fallback_initial_candidates():
    p,a,_=inputs()
    for w in a['worlds']:
        if w['role'].startswith('search:'):w.update(status='failed',scores={'throughput':None,'efficiency':None})
    assert all(v['system'] is None for v in driver.fixed_selection(p,a)['selected'].values())


@pytest.mark.parametrize('field,value',[('schema','scienceutopia.native-institution-loop-audit.v1'),
    ('source_commit','c'*40),('selection',{'fake':True}),('new_model_calls',1)])
def test_fixed_selection_requires_the_explicit_matching_stopped_audit(field,value):
    p,a,_=inputs();a[field]=value
    with pytest.raises(ValueError,match='stopped-prefix'):driver.fixed_selection(p,a)


def test_plan_deduplicates_only_exact_policies_and_preserves_all_logical_labels():
    p,a,u=inputs();b=driver.build_plan(p,a,source='c'*40,origin={},usages=u)
    assert b['budget']['designer_generation_POSTs']==0 and not b['budget']['refill']
    assert len(b['jobs'])<=30 and len(b['fixed_selection']['all_attempts'])==11
    assert b['world']['source_commit']=='c'*40 and b['world']['years']==4
    assert b['losses']==p['losses'] and not b['claims']['original_study_completed']
    assert not b['claims']['equal_search_budgets']
    assert {j['seed'] for j in b['jobs']}==set(driver.SEEDS)
    labels={s for j in b['jobs'] for s in j['labels']}
    assert len(labels)==10
    assert all('code-and-graph' not in s for s in labels)
    for j in b['jobs']:
        assert j['system']['initial_state']['seed']==j['seed']
        assert driver.policy_identity(j['system'])==j['policy_sha256']
    assert driver.jobs_for(b)==b['jobs']


@pytest.mark.parametrize('change',[{'valid':False},{'prior_matching_runs':[{'seed':62001}]},
    {'errors':['SCRIPTED']},{'seeds':[62001]}])
def test_plan_cannot_start_with_used_or_unchecked_seeds(change):
    p,a,u=inputs();u[0].update(change)
    with pytest.raises(ValueError,match='unused evaluation seeds'):
        driver.build_plan(p,a,source='c'*40,origin={},usages=u)


def run_fixture(root, monkeypatch):
    p,a,u=inputs(); origin=root/'original';origin.mkdir();(origin/'writer.lock').touch()
    u[0].pop('content_sha256');saved=save(root/'seed-usage-0.json',u[0]);u=[saved]
    b=driver.build_plan(p,a,source='c'*40,origin={'run':str(origin)},usages=u)
    b={**b,'content_sha256':digest(b)}
    monkeypatch.setattr(driver,'require_environment',lambda:None)
    monkeypatch.setattr(driver,'require_plan',lambda r:deepcopy(b))
    monkeypatch.setattr(driver,'origin_evidence',lambda o:(p,a))
    monkeypatch.setattr(driver,'usage_inventory',lambda r,s:deepcopy(saved))
    return b


def test_orchestration_never_generates_candidates_freezes_jobs_and_refuses_repeat(tmp_path,monkeypatch):
    b=run_fixture(tmp_path,monkeypatch);calls=[]
    def observe(cell,p,identity,system,seed,role):
        assert (tmp_path/'started.json').exists() and len(p['jobs'])==len(b['jobs'])
        assert p['fixed_selection']==b['fixed_selection']
        calls.append(identity);return {'status':'complete'}
    monkeypatch.setattr(driver,'observe',observe)
    driver.run(tmp_path)
    assert len(calls)==len(b['jobs'])
    assert driver.read(tmp_path/'terminal.json')['status']=='closed'
    with pytest.raises(ValueError,match='immutable'):driver.run(tmp_path)
    assert len(calls)==len(b['jobs'])


def test_evaluation_failure_stops_next_world_without_repair_or_refill(tmp_path,monkeypatch):
    run_fixture(tmp_path,monkeypatch);calls=[]
    monkeypatch.setattr(driver,'observe',lambda *args:calls.append(args[2]) or {'status':'failed'})
    with pytest.raises(ValueError,match='evaluation failed'):driver.run(tmp_path)
    assert len(calls)==1
    assert driver.read(tmp_path/'terminal.json')['completed_jobs']==0
    assert driver.read(tmp_path/'terminal.json')['status']=='stopped'


def test_a_seed_consumed_after_prepare_stops_before_any_model_or_world(tmp_path,monkeypatch):
    run_fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(driver,'usage_inventory',lambda *a:{'valid':False})
    monkeypatch.setattr(driver,'observe',lambda *a:pytest.fail('no dispatch'))
    with pytest.raises(ValueError,match='consumed after preparation'):driver.run(tmp_path)
    assert not (tmp_path/'started.json').exists()


def test_disappeared_seed_receipt_stops_before_any_model(tmp_path,monkeypatch):
    run_fixture(tmp_path,monkeypatch);(tmp_path/'seed-usage-0.json').unlink()
    monkeypatch.setattr(driver,'observe',lambda *a:pytest.fail('no dispatch'))
    with pytest.raises(ValueError,match='disappeared'):driver.run(tmp_path)


@pytest.mark.parametrize('source',[None,'main','c'*39,'z'*40])
def test_evaluation_requires_a_full_source_identity(source):
    p,a,u=inputs()
    with pytest.raises(ValueError,match='full evaluation source'):
        driver.build_plan(p,a,source=source,origin={},usages=u)


def test_closed_evaluation_auditor_rejects_stopped_runs_before_worker(tmp_path,monkeypatch):
    from scripts import audit_native_fixed_candidate_evaluation_v1 as auditor
    save(tmp_path/'terminal.json',{'status':'stopped'})
    monkeypatch.setattr('sys.argv',['audit','--run',str(tmp_path),'--output',str(tmp_path/'no.json'),
        '--frozen-source',str(tmp_path)])
    monkeypatch.setattr('subprocess.run',lambda *a,**k:pytest.fail('no closed worker'))
    with pytest.raises(ValueError,match='closed separate evaluation'):auditor.main()
