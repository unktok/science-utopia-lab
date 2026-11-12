"""SCRIPTED frozen-selection/unused-seed control flow, not real T/P results."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_native_capacity_fixed_evaluation_v1 as module
from tests.reports.test_native_capacity_objective_loop_v1 import plan as original_plan
from tests.reports.test_native_objective_fixed_evaluation_v1 import seal
from utopia.optimization.native_bounded_staged_designer import CompletionUnknown
from utopia.system.design_patch import clone


def usage(seeds):
    return seal({'valid':True,'errors':[],'prior_matching_runs':[],'seeds':clone(seeds),
        'root':'SCRIPTED-unused-root','checked_utc':'2026-11-12T00:00:00+00:00'})


def evidence(tmp_path,monkeypatch,*,seeds=None,image_override=None):
    original=original_plan(tmp_path,monkeypatch,image_override=image_override)
    system=original['initial_system'];seeds=[67101,67107] if seeds is None else seeds
    worlds=[{'identity':'SCRIPTED-first','role':'search:throughput','status':'complete','system':clone(system),
        'scores':{'throughput':-2.,'founder-activity':-15.}},
        {'identity':'SCRIPTED-second','role':'search:throughput','status':'complete','system':clone(system),
        'scores':{'throughput':-2.,'founder-activity':-15.}}]
    selected=seal({'plan_sha256':original['content_sha256'],'baseline_fallback':False,'held_out_evaluation':False,
        'frozen_utc':'2026-11-12T00:00:00+00:00','selected':{
            'throughput':{'loss':-2.,'completed_submissions':2,'all_tied_ids':['SCRIPTED-first','SCRIPTED-second'],
                'selected_id':'SCRIPTED-first','system':clone(system)},
            'founder-activity':{'loss':None,'completed_submissions':0,'all_tied_ids':[],
                'selected_id':None,'system':None}}})
    audit=seal({'schema':'scienceutopia.native-capacity-objective-loop-audit.v1',
        'source_commit':original['source_commit'],'plan_sha256':original['content_sha256'],
        'closure':{'terminal':{'status':'closed'}},'source_proof':{'status':'verified-exact-source-closure'},
        'new_model_calls':0,'new_code_executions':0,'held_out_evaluation':False,
        'selection':selected,'worlds':worlds})
    p=module.build_plan(original,audit,source='e'*40,origin={'SCRIPTED':'not real origin'},
        usages=[usage(seeds)],seeds=seeds)
    return original,audit,seal(p)


def test_exact_controls_null_selection_ties_measurement_and_policy_deduplication(tmp_path,monkeypatch):
    original,audit,p=evidence(tmp_path,monkeypatch)
    assert p['fixed_selection']==audit['selection'] and p['evaluation']['seeds']==[67101,67107]
    assert len(p['jobs'])==10 and p['evaluation']['maximum_physical_worlds']==14
    assert p['world']['world_conditions']==original['world']['world_conditions']
    assert p['losses']==original['losses']
    assert {k:v for k,v in original['measurement_contract'].items() if k!='source_commit'}=={
        k:v for k,v in p['measurement_contract'].items() if k!='source_commit'}
    assert p['measurement_contract']['source_commit']=='e'*40
    assert p['budget']['designer_generation_POSTs']==p['budget']['critic_POSTs']==0
    assert not p['claims']['independent_optimizer_replications']
    for job in p['jobs']:
        assert 'selected:founder-activity' not in job['labels']
        assert job['system']['initial_state']['seed']==job['seed']
    chosen=[j for j in p['jobs'] if 'selected:throughput' in j['labels']]
    assert len(chosen)==2 and all('reference:reviewed-all-equalization' in j['labels'] for j in chosen)
    with pytest.raises(ValueError):module.fixed_selection(original,audit)  # no T/U reinterpretation


@pytest.mark.parametrize('change',['stopped','source','fallback','system','tie','instrument','used','empty','four','bool','development','duplicate'])
def test_changed_selection_instrument_and_unused_seed_fail_closed(tmp_path,monkeypatch,change):
    original,audit,p=evidence(tmp_path,monkeypatch);seeds=[67101,67107];u=usage(seeds)
    if change=='stopped':audit['closure']['terminal']['status']='stopped'
    elif change=='source':audit['source_commit']='f'*40
    elif change=='fallback':audit['selection']['baseline_fallback']=True
    elif change=='system':audit['selection']['selected']['throughput']['system']['initial_state']['SCRIPTED-new']=1
    elif change=='tie':audit['selection']['selected']['throughput']['all_tied_ids'].pop()
    elif change=='instrument':original['measurement_contract']['instrument_sha256']='f'*64
    elif change=='used':u['prior_matching_runs']=[{'SCRIPTED':'used'}]
    elif change=='empty':seeds=[]
    elif change=='four':seeds=[67101,67103,67107,67109]
    elif change=='bool':seeds=[True]
    elif change=='development':seeds=[module.SEED]
    else:seeds=[67101,67101]
    seal(audit['selection']);seal(audit);u['seeds']=seeds;seal(u)
    with pytest.raises(ValueError):module.build_plan(original,audit,source='e'*40,origin={},usages=[u],seeds=seeds)


def setup(tmp_path,monkeypatch):
    _,_,p=evidence(tmp_path/'inputs',monkeypatch)
    root=tmp_path/'evaluation';root.mkdir();origin=tmp_path/'origin';origin.mkdir();(origin/'writer.lock').touch()
    p['origin']={'run':str(origin)};u=usage(p['evaluation']['seeds']);p['evaluation']['seed_usage']=[u['content_sha256']];seal(p)
    module.save(root/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    module.save(root/'seed-usage-00.json',{k:v for k,v in u.items() if k!='content_sha256'})
    monkeypatch.setattr(module,'require_environment',lambda:None)
    monkeypatch.setattr(module,'require_plan',lambda root:p)
    monkeypatch.setattr(module,'usage_inventory',lambda *a:u)
    return root,p,u


def test_all_declared_jobs_including_known_nulls_close_without_refill_or_observer(tmp_path,monkeypatch):
    root,p,_=setup(tmp_path,monkeypatch);calls=[]
    def observe(root,p,job):
        calls.append(clone(job));module.save(root/'evaluation'/job['identity']/'observation.json',{
            'status':'failed' if len(calls)==1 else 'complete','SCRIPTED':'not native science'})
    monkeypatch.setattr(module,'observe',observe);module.run(root)
    assert calls==p['jobs'] and module.read(root/'terminal.json')['status']=='closed'
    assert module.read(root/'terminal.json')['completed_jobs']==10
    assert not (root/'observer').exists() and not (root/'observer-audit.json').exists()
    with pytest.raises(ValueError,match='consumed'):module.run(root)


def test_unknown_completion_stops_and_later_seeds_are_not_dispatched(tmp_path,monkeypatch):
    root,_,_=setup(tmp_path,monkeypatch);calls=[]
    def observe(*a):calls.append(1);raise CompletionUnknown('SCRIPTED unresolved native dispatch')
    monkeypatch.setattr(module,'observe',observe)
    with pytest.raises(CompletionUnknown):module.run(root)
    assert calls==[1]
    end=module.read(root/'terminal.json');assert end['status']=='stopped' and end['completed_jobs']==0


def test_predispatch_usage_change_blocks_before_started_and_inference(tmp_path,monkeypatch):
    root,_,u=setup(tmp_path,monkeypatch);used=clone(u);used['valid']=False
    monkeypatch.setattr(module,'usage_inventory',lambda *a:used)
    monkeypatch.setattr(module,'observe',lambda *a:pytest.fail('used seed cannot dispatch'))
    with pytest.raises(ValueError,match='consumed after preparation'):module.run(root)
    assert not (root/'started.json').exists()


def test_observe_uses_actual_sealed_observation_and_both_null_cross_scores(tmp_path,monkeypatch):
    _,_,p=evidence(tmp_path/'inputs',monkeypatch);calls=[]
    monkeypatch.setattr(module,'factory_for',lambda *a:'SCRIPTED-factory')
    def evaluate(suggestion,**kwargs):
        calls.append((suggestion,kwargs));return SimpleNamespace(to_dict=lambda:{
            'status':'failed','loss':None,'metadata':{'measurements':[]}})
    monkeypatch.setattr(module,'evaluate_native_suggestion',evaluate)
    root=tmp_path/'raw';job=p['jobs'][0];module.observe(root,p,job)
    assert calls[0][1]['seeds']==[job['seed']]
    assert calls[0][1]['loss_spec']==p['losses']['throughput']
    scores=module.read(root/'evaluation'/job['identity']/'cross-scores.json')
    assert all(scores[name]['loss'] is None for name in module.OBJECTIVES)
    with pytest.raises(ValueError,match='consumed'):module.observe(root,p,job)
