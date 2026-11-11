"""Four-slot finite resource support orchestration, never actual science."""
from types import SimpleNamespace

import pytest

from scripts import run_native_liquidity_support_v1 as module
from tests.reports.test_native_institution_loop_v1 import plan as operator
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import clone,digest


def plan():
    p=module.build_plan(operator(),source='a'*40,preceding={'SCRIPTED':'closed observer'})
    return {**p,'content_sha256':digest(p)}


def test_four_explicit_jobs_change_only_operator_endowment_and_delivery():
    p=plan()
    assert [(j['initial_funding'],j['condition']) for j in p['jobs']]==[
        (30,'disconnected'),(30,'connected'),(60,'connected'),(60,'disconnected')]
    assert all(j['world_conditions']['population_resource_profile']=='balanced_two_band' for j in p['jobs'])
    assert all(j['world_conditions']['log_resource_ledger'] for j in p['jobs'])
    assert p['budget']['designer_generation_POSTs']==0 and not p['policy_selection']
    assert p['development_seed_reused'] and not p['held_out_evaluation']
    off,on=p['jobs'][0]['system'],p['jobs'][1]['system']
    assert off['mechanisms']==on['mechanisms'] and off['schedules']==on['schedules']
    assert off['connections']==on['connections'][:-1]


@pytest.mark.parametrize('failure',[None,'control','unknown','factory'])
def test_no_retry_or_replacement_after_failed_control_or_unknown_completion(tmp_path,monkeypatch,failure):
    from utopia.runtime.checkpointing import PortableStop
    p=plan();monkeypatch.setattr(module,'require_environment',lambda:None)
    monkeypatch.setattr(module,'require_plan',lambda root:p)
    conditions=[];requests=[];safe_points=[]
    class Factory:
        def __init__(self,*args,**kwargs):
            conditions.append(clone(kwargs['world_conditions']))
            self.model_digest='wrong' if failure=='factory' else p['scientist']['model_digest']
            self.corpus_sha256=p['scientist']['corpus_sha256']
        def __call__(self,*args):
            stop=SimpleNamespace(deadline=None);safe_points.append(stop)
            return SimpleNamespace(portable_stop=stop,llm=SimpleNamespace(response_cache=SimpleNamespace(stop=stop)))
    monkeypatch.setattr(module,'LocalRoleBoundNativeFactory',Factory)
    def evaluate(suggestion,**kwargs):
        requests.append(suggestion.suggestion_id)
        sim=kwargs['simulation_factory'](None,61001,'SCRIPTED')
        assert sim.portable_stop is sim.llm.response_cache.stop and sim.portable_stop.deadline is not None
        if failure=='unknown':raise PortableStop('SCRIPTED unresolved inference')
        return SimpleNamespace(to_dict=lambda:{'status':'failed' if failure=='control' else 'complete',
            'metadata':{'measurements':[]},'loss':None})
    monkeypatch.setattr(module,'evaluate_native_suggestion',evaluate)
    if failure:
        with pytest.raises((ValueError,PortableStop)):module.run(tmp_path)
    else:module.run(tmp_path)
    assert len(conditions)==(1 if failure else 4)
    assert len(requests)==(0 if failure=='factory' else 1 if failure else 4)
    end=module.read(tmp_path/'terminal.json')
    assert end['status']==('stopped' if failure else 'closed')
    assert end['complete_worlds']==(0 if failure else 4)
    assert not end['policy_selection'] and not end['publication_ready']
    with pytest.raises(ValueError,match='consumed'):module.run(tmp_path)


def test_plan_roundtrip_binds_initial_conditions_and_prior_closed_observer(tmp_path,monkeypatch):
    prior=tmp_path/'prior';prior.mkdir();save(prior/'terminal.json',{'status':'closed'})
    save(prior/'plan.json',{'SCRIPTED':'prior plan'})
    preceding={'directory':str(prior),'terminal_file_sha256':module.file_sha256(prior/'terminal.json'),
        'plan_file_sha256':module.file_sha256(prior/'plan.json')}
    p=module.build_plan(operator(),source='a'*40,preceding=preceding)
    saved=save(tmp_path/'plan.json',p);monkeypatch.setattr(module,'pinned_revision',lambda root:'a'*40)
    assert module.require_plan(tmp_path)==saved
    saved['jobs'][0]['world_conditions']['initial_funding']=999
    (tmp_path/'plan.json').unlink();save(tmp_path/'plan.json',{k:v for k,v in saved.items() if k!='content_sha256'})
    with pytest.raises(ValueError,match='reconstruction'):module.require_plan(tmp_path)
