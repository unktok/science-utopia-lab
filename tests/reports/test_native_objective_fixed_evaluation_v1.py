"""Finite fixed-evaluation orchestration with scripted science, not real outcomes."""
import pytest

from scripts import run_native_objective_fixed_evaluation_v1 as module
from scripts.native_design_benchmark_plan import policy_identity
from tests.reports.test_native_objective_instrument_loop_v1 import plan as original_plan,usage
from utopia.optimization.common_content_observer import CommonContentObserver,ObserverCompletionUnknown
from utopia.system.design_patch import clone,digest


def seal(v):
    v.pop('content_sha256',None);v['content_sha256']=digest(v);return v


def evidence(tmp_path,monkeypatch):
    original=original_plan(tmp_path,monkeypatch);system=original['initial_system']
    worlds=[{'identity':'SCRIPTED-first','role':'search:throughput','status':'complete','system':clone(system),
        'scores':{'throughput':-2.,'content-utility':-1.}},
        {'identity':'SCRIPTED-second','role':'search:throughput','status':'complete','system':clone(system),
        'scores':{'throughput':-2.,'content-utility':-1.}}]
    selected=seal({'plan_sha256':original['content_sha256'],'baseline_fallback':False,'held_out_evaluation':False,
        'frozen_utc':'2026-11-11T18:00:00+00:00','selected':{
            'throughput':{'loss':-2.,'completed_submissions':2,'all_tied_ids':['SCRIPTED-first','SCRIPTED-second'],
                'selected_id':'SCRIPTED-first','system':clone(system)},
            'content-utility':{'loss':None,'completed_submissions':0,'all_tied_ids':[],'selected_id':None,'system':None}}})
    a=seal({'schema':'scienceutopia.native-objective-instrument-loop-audit.v1','source_commit':original['source_commit'],
        'plan_sha256':original['content_sha256'],'closure':{'terminal':{'status':'closed'}},
        'source_proof':{'status':'verified-exact-source-closure'},'new_model_calls':0,'new_code_executions':0,
        'held_out_evaluation':False,'selection':selected,'worlds':worlds})
    p=module.build_plan(original,a,source='e'*40,origin={'SCRIPTED':'not real origin'},usages=[usage()],
        observer_backend=original['observer_contract']['backend'])
    return original,a,seal(p)


def test_preserves_all_five_controls_null_arm_and_selected_ties_without_reselection(tmp_path,monkeypatch):
    original,a,p=evidence(tmp_path,monkeypatch)
    assert p['fixed_selection']==a['selection'] and p['evaluation']['seeds']==[64101,64107,64113]
    assert len(p['jobs'])==15 and p['budget']['designer_generation_POSTs']==0
    assert p['world']['world_conditions']==original['world']['world_conditions']
    for job in p['jobs']:
        assert policy_identity(job['system'])==job['policy_sha256']
        assert 'selected:content-utility' not in job['labels']
    selected=[j for j in p['jobs'] if 'selected:throughput' in j['labels']]
    assert len(selected)==3 and all('reference:reviewed-all-connected' in j['labels'] for j in selected)
    c=clone(p);c['fixed_selection']['selected']['throughput']['system']['initial_state']['SCRIPTED-new']=1
    assert len(module.jobs_for(c))==18  # Only exact literal equality deduplicates.
    old=original['observer_contract'];new=p['observer_contract']
    assert {k:v for k,v in old.items() if k not in ('source_commit','content_sha256')}=={
        k:v for k,v in new.items() if k not in ('source_commit','content_sha256')}


@pytest.mark.parametrize('change',['stopped','wrong-source','reference-fallback','changed-system','tie-missing','consumed-seed','changed-judge'])
def test_rejects_changed_science_or_fabricated_selection(tmp_path,monkeypatch,change):
    original,a,p=evidence(tmp_path,monkeypatch);usages=[usage()];backend=original['observer_contract']['backend']
    if change=='stopped':a['closure']['terminal']['status']='stopped'
    elif change=='wrong-source':a['source_commit']='f'*40
    elif change=='reference-fallback':a['selection']['baseline_fallback']=True
    elif change=='changed-system':a['selection']['selected']['throughput']['system']['initial_state']['SCRIPTED-new']=1
    elif change=='tie-missing':a['selection']['selected']['throughput']['all_tied_ids'].pop()
    elif change=='consumed-seed':usages[0]['prior_matching_runs']=[{'SCRIPTED':'used'}]
    else:backend={**backend,'ollama_version':'changed'}
    seal(a['selection']);seal(a)
    with pytest.raises(ValueError):module.build_plan(original,a,source='e'*40,origin={},usages=usages,observer_backend=backend)


def setup_run(tmp_path,monkeypatch):
    original,a,p=evidence(tmp_path,monkeypatch);root=tmp_path/'evaluation';root.mkdir()
    origin=tmp_path/'origin';origin.mkdir();(origin/'writer.lock').touch();p['origin']={'run':str(origin)};seal(p)
    u={**usage(),'root':str(tmp_path),'checked_utc':'2026-11-11T17:00:00+00:00'};seal(u)
    module.save(root/'seed-usage-00.json',{k:v for k,v in u.items() if k!='content_sha256'})
    module.save(root/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    monkeypatch.setattr(module,'require_environment',lambda:None);monkeypatch.setattr(module,'require_plan',lambda root:p)
    monkeypatch.setattr(module,'usage_inventory',lambda *a:u)
    monkeypatch.setattr(module,'LocalObserverBackend',lambda **k:None)
    return root,p


def test_all_jobs_close_including_known_technical_nulls_and_public_observer_retention(tmp_path,monkeypatch):
    root,p=setup_run(tmp_path,monkeypatch);jobs=[]
    def observe(root,p,job,observer):
        jobs.append(clone(job));module.save(root/'evaluation'/job['identity']/'observation.json',{
            'status':'failed' if len(jobs)==1 else 'complete','SCRIPTED':'not a native scientific result'})
    monkeypatch.setattr(module,'observe',observe);module.run(root)
    assert jobs==p['jobs'] and module.read(root/'terminal.json')['status']=='closed'
    assert module.read(root/'terminal.json')['completed_jobs']==15
    assert module.read(root/'observer-audit.json')==CommonContentObserver(root/'observer',p['observer_contract'],backend=None).audit()
    with pytest.raises(ValueError,match='consumed'):module.run(root)


def test_unknown_physical_completion_stops_without_refill(tmp_path,monkeypatch):
    root,p=setup_run(tmp_path,monkeypatch);calls=[]
    def observe(*a):calls.append(1);raise ObserverCompletionUnknown('SCRIPTED unresolved critic')
    monkeypatch.setattr(module,'observe',observe)
    with pytest.raises(ObserverCompletionUnknown):module.run(root)
    assert calls==[1] and module.read(root/'terminal.json')['status']=='stopped'
    assert module.read(root/'terminal.json')['completed_jobs']==0
