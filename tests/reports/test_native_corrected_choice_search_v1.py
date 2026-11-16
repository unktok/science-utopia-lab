"""SCRIPTED plans, input journals and losses; not real scientific outcomes."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_native_corrected_choice_search_v1 as driver
from tests.reports.test_native_topic_free_plan_v1 import plan as free_plan
from tests.system.test_native_topic_priority_controls import actors
from utopia.optimization.blackbox import Observation
from utopia.optimization.native_code_trace import validate_record
from utopia.optimization.native_component_parameter_context_v1 import OPTION, SCOPE
from utopia.optimization.native_parameter_space_v1 import NativeParameterOptimizer
from utopia.system.design_patch import clone, digest


def seal(value):
    result={k:deepcopy(v) for k,v in value.items() if k!='content_sha256'}
    return {**result,'content_sha256':digest(result)}


def plan(tmp_path,monkeypatch):
    old,original=free_plan(tmp_path,monkeypatch)
    bank=seal({**old['component_bank'],OPTION:SCOPE})
    evidence={**old['component_evidence'],'parameter_context_scope':SCOPE}
    p=driver.build_plan(original,{'content_sha256':'SCRIPTED-upstream'},source=old['source_commit'],
        origin={'SCRIPTED':True},backend=old['backend'],observer_backend=old['observer_contract']['backend'],
        bank=bank,evidence=evidence,sources=old['original_native_sources'])
    return seal(p),old


def scalar_context(p,monkeypatch):
    pairs=[]
    for index,label in enumerate(driver.PARENTS):
        candidate=p['reference_systems'][label]
        observation=Observation('SCRIPTED-reference-'+label,'workflow-reference-'+label,candidate,'complete',-20. if index else -10.).to_dict()
        pairs.append({'suggestion':{'suggestion_id':observation['suggestion_id'],'candidate':clone(candidate)},'observation':observation})
    context={'pairs':pairs}
    monkeypatch.setattr(driver,'objective_view',lambda c,loss:{'observations':deepcopy(c['pairs'])})
    return context


def recorded_initial(p,context,root):
    zero=context['pairs'][0]['observation'];run_id='SCRIPTED-reference-s61001'
    cell=root/'worlds'/run_id;cell.mkdir(parents=True)
    checkpoint=cell/'simulation/checkpoints/native-design/SCRIPTED-checkpoint.json.gz'
    zero['metadata']['runs']=[{'run_id':run_id,'checkpoint_path':str(checkpoint)}]
    node=next(n for n in zero['candidate']['mechanisms'] if n['mechanism_id']=='developer-catalog-agenda')
    context_value={'period':1,'phase':1,'random_seed':42,'state':{},
        'parameters':driver.parameters(zero['candidate'],node['mechanism_id']),
        'inputs':{'world':[{'payload':{'ecosystem':{'agents':actors()}}}]}}
    result={'outputs':{'agenda':[],'commands':[]},'state':{}}
    record={'schema':'scienceutopia.native-code-input.v1',
        'binding':{'source_commit':p['source_commit'],'system_fingerprint':digest(zero['candidate']),'run_id':run_id},
        'artifact':node['parameters']['code_artifact'],'context':context_value,'result':result,
        'receipt':{'image_id':p['designer']['image_id'],'artifact_sha256':digest(node['parameters']['code_artifact']),
            'context_sha256':digest(context_value),'result_sha256':digest(result)}}
    record['bundle_sha256']=digest(record);validate_record(record)
    path=cell/'code-contexts.jsonl';path.write_text(json.dumps(record)+'\n')
    return path,record


def test_same_native_budget_deeper_history_exact_losses_and_optional_context(tmp_path,monkeypatch):
    p,old=plan(tmp_path,monkeypatch)
    assert driver.open_institutions(p)
    assert p['replication_seeds']==[79011] and p['generations']==4
    assert len(p['schedule'])==24 and len(driver.all_history_keys(p))==6 and len(driver.history_keys(p))==2
    for g in range(4):
        order=[driver.history_key(s) for s in p['schedule'][g*6:(g+1)*6]]
        if g:assert order==[driver.history_key(s) for s in p['schedule'][(g-1)*6:g*6]][::-1]
    assert p['budget']['candidate_slots']==24 and p['budget']['native_worlds_upper_bound']==27
    assert p['budget']['designer_POSTs_upper_bound']==488 and p['budget']['component_probes_upper_bound']==512
    assert p['losses']==old['losses'] and p['scientist']==old['scientist']
    assert p['world']['world_conditions']==old['world']['world_conditions']
    assert p['component_bank'][OPTION]==SCOPE and not p['budget']['replace_failed_slots']
    assert p['post_edit_contract']['parameter_context_scope']==SCOPE
    assert not p['independent_optimizer_replications'] and not p['held_out_evaluation']
    for key in driver.history_keys(p):
        c=driver.campaign(tmp_path/'campaigns',p,key)
        request=c._request([],c._validate(),1)
        assert request['loss_spec']==p['losses'][key[2]]
        assert request['strategy_provenance']['post_edit_component_contract']==p['post_edit_contract']


def test_fresh_exact_recorded_actor_projection_is_bound_without_code_execution(tmp_path,monkeypatch):
    p,_=plan(tmp_path/'plan',monkeypatch);context=scalar_context(p,monkeypatch)
    path,record=recorded_initial(p,context,tmp_path/'native');before=deepcopy(context)
    projection=driver.choice_projection(p,context)
    expected=[{k:clone(a[k]) for k in p['initial_choice_contract']['actor_fields'] if k in a} for a in actors()]
    assert projection['actor_projection']==expected and context==before
    assert projection['original_bundle_sha256']==record['bundle_sha256']
    assert projection['code_journal_path']==str(path)
    driver.save(tmp_path/'run/initial-choice-context.json',projection)
    assert driver.require_choice(tmp_path/'run',p,context)==projection


@pytest.mark.parametrize('problem',['duplicate','binding','parameters','absent'])
def test_initial_actor_input_cannot_be_guessed_reused_or_swapped(tmp_path,monkeypatch,problem):
    p,_=plan(tmp_path/'plan',monkeypatch);context=scalar_context(p,monkeypatch)
    path,record=recorded_initial(p,context,tmp_path/'native')
    if problem=='duplicate':path.write_text(path.read_text()*2)
    elif problem=='absent':path.write_text('')
    else:
        if problem=='binding':record['binding']['source_commit']='b'*40
        else:
            record['context']['parameters']['topic_priorities']={'SCRIPTED':99.}
            record['receipt']['context_sha256']=digest(record['context'])
        record['bundle_sha256']=digest({k:v for k,v in record.items() if k!='bundle_sha256'})
        path.write_text(json.dumps(record)+'\n')
    with pytest.raises(ValueError):driver.choice_projection(p,context)


def test_real_four_step_numeric_ask_tell_and_state_have_actual_initial_choice_kernel(tmp_path,monkeypatch):
    p,_=plan(tmp_path/'plan',monkeypatch);context=scalar_context(p,monkeypatch)
    recorded_initial(p,context,tmp_path/'native')
    objective=p['objectives'][0]
    uniform=driver.numeric_optimizer(p,context,(driver.METHODS[0],0,objective))
    adaptive=driver.numeric_optimizer(p,context,(driver.METHODS[1],0,objective))
    for g in range(4):
        a,b=uniform.ask()[0],adaptive.ask()[0]
        assert a.phase=='initial' and b.phase==('initial' if g==0 else 'adaptive')
        if not g:assert a.candidate==b.candidate
        for opt,s in ((uniform,a),(adaptive,b)):
            opt.tell([Observation('SCRIPTED-own-'+str(g),s.suggestion_id,s.candidate,'complete',-9.+g)])
    state=adaptive.state_dict()
    assert state['space_binding']['initial_choice_kernel']['groups']
    restored=NativeParameterOptimizer.from_state(adaptive._space,deepcopy(state))
    assert restored.state_dict()==state and len(state['optimizer']['observations'])==5


@pytest.mark.parametrize('loss,origin',[(-9.,'reference'),(-20.,'reference'),(-21.,'own'),(None,'reference')])
def test_primary_warm_incumbent_and_secondary_own_are_never_conflated(loss,origin):
    ref={'status':'complete','loss':-20.,'suggestion_id':'SCRIPTED-ref','candidate':{'SCRIPTED':'ref'}}
    own={'status':'failed' if loss is None else 'complete','loss':loss,'suggestion_id':'SCRIPTED-own','candidate':{'SCRIPTED':'own'}}
    primary=driver.endpoint([('reference',ref),('own',own)],reference_loss=-20.,complete_own=int(loss is not None))
    secondary=driver.endpoint([('own',own)],reference_loss=-20.,complete_own=int(loss is not None))
    assert primary['selected_origin']==origin
    assert secondary['selected_origin']==('own' if loss is not None else None)
    assert secondary['loss']==loss
    if loss is None:assert secondary['system'] is secondary['selected_id'] is None
    if loss==-20.:assert primary['all_tied_ids']==['SCRIPTED-ref','SCRIPTED-own']


def test_all_four_slots_and_known_free_nulls_keep_both_frozen_endpoint_banks(tmp_path,monkeypatch):
    p,_=plan(tmp_path/'plan',monkeypatch);context=scalar_context(p,monkeypatch)
    monkeypatch.setattr(driver,'campaign',lambda *a,**kw:SimpleNamespace(state={'pending':None,
        'records':[{'observations':[]} for _ in range(4)]}))
    for key in driver.all_history_keys(p):
        if key[0]==driver.METHODS[2]:continue
        for g in range(4):
            complete=key[0]==driver.METHODS[1]
            obs=Observation('SCRIPTED-own'+str(g),'SCRIPTED-own'+str(g),p['reference_systems'][driver.PARENTS[0]],
                'complete' if complete else 'failed',-1. if complete else None).to_dict()
            driver.save(driver.history_directory(tmp_path/'run',key)/f'generation-{g}/observation.json',obs)
    result=driver.selection(tmp_path/'run',p,context)
    assert not result['baseline_fallback']
    for method in driver.METHODS:
        assert list(result['selected'][method])==['0']
        for objective in driver.OBJECTIVES:
            assert result['selected'][method]['0'][objective]['selected_origin']=='reference'
            own=result['own_only_selected'][method]['0'][objective]
            assert own['selected_origin']==('own' if method==driver.METHODS[1] else None)
            if own['selected_id'] is not None:assert own['selected_id']=='SCRIPTED-own0'


@pytest.mark.parametrize('error',[ValueError('SCRIPTED failed readiness'),KeyboardInterrupt('SCRIPTED unknown completion')])
def test_readiness_failure_stops_and_consumes_run_without_refill_or_native_calls(tmp_path,monkeypatch,error):
    p,_=plan(tmp_path/'plan',monkeypatch);origin=tmp_path/'origin';origin.mkdir();(origin/'writer.lock').touch()
    p['origin']={'run':str(origin)};root=tmp_path/'run';root.mkdir()
    monkeypatch.setattr(driver,'require_plan',lambda root:p)
    monkeypatch.setattr(driver.free.base,'require_environment',lambda:None)
    monkeypatch.setattr(driver,'campaign',lambda *a,**kw:SimpleNamespace(_request=lambda *a:{'SCRIPTED':True},_validate=lambda:None))
    calls=[]
    class Author:
        def calibrate(self,request):calls.append(request);raise error
    monkeypatch.setattr(driver,'designer_for',lambda *a:Author())
    monkeypatch.setattr(driver,'evaluate_native_suggestion',lambda *a,**kw:pytest.fail('no native/model call after failed readiness'))
    with pytest.raises(type(error)):driver.run(root)
    assert driver.read(root/'terminal.json')['status']=='stopped' and len(calls)==1
    with pytest.raises(ValueError,match='no redispatch'):driver.run(root)
    assert len(calls)==1
