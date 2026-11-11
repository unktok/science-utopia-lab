"""Portable report fixtures are scripted, not independent native scientific proof."""
import pytest

from scripts.reports import native_objective_instrument_loop_v1 as module
from tests.reports.test_native_objective_instrument_loop_v1 import plan
from tests.reports.test_native_objective_fixed_evaluation_v1 import seal
from utopia.optimization.loss import evaluate_loss
from utopia.system import SystemSpec
from utopia.system.design_patch import clone,digest


def evidence(tmp_path,monkeypatch):
    p=plan(tmp_path,monkeypatch);worlds=[];pairs=[];records={};traces={};authors=[]
    def world(identity,role,system,failed=False):
        spec=SystemSpec.from_dict(system)
        base={'run_id':identity,'system_fingerprint':spec.fingerprint,'metrics':{
            'native.accepted_decisions':{'status':'measured','value':2},
            'native.accepted_peer_score_sum':{'status':'measured','value':7.},
            'native.review_records':{'status':'measured','value':3}}}
        m=clone(base);m['metrics']['native.common_content_utility_sum']={'status':'measured','value':1.}
        m['measurement_adapter_contract_sha256']=digest(p['observer_contract'])
        measurements=[] if failed else [m];scores={k:evaluate_loss(v,measurements)['loss'] for k,v in p['losses'].items()}
        worlds.append({'identity':identity,'role':role,'seed':61001,'system':clone(system),
            'status':'failed' if failed else 'complete','scores':scores,'physical_proof':{'measurement':base}})
        o={'suggestion_id':identity,'candidate':clone(system),'status':worlds[-1]['status'],
            'loss':scores['throughput' if role=='developer-reference' else role.split(':',1)[1]],
            'metadata':{'measurements':measurements}}
        return o
    for label in p['reference_order']:
        identity='reference-'+label;o=world(identity,'developer-reference',p['reference_systems'][label])
        pairs.append({'suggestion':{'suggestion_id':identity,'candidate':clone(p['reference_systems'][label])},'observation':o})
    context=seal({'pairs':pairs,'SCRIPTED':'common-reference validator is tested elsewhere'})
    for i,s in enumerate(p['schedule']):
        objective,g=s['objective'],s['generation'];parent=p['reference_systems']['one-reviewer-all-connected']
        request={'generation':g,'parent_system':clone(parent),'loss_spec':clone(p['losses'][objective]),
            'history':[{'SCRIPTED':'own previous slot'}]*g,'observations':clone(pairs),
            'developer_reference_context':{'context_sha256':context['content_sha256']}}
        generation_null=i==0;native_null=i==1;identity='SCRIPTED-own-'+str(i)
        o=None if generation_null else world(identity,'search:'+objective,parent,failed=native_null)
        error={'type':'ValueError','message':'SCRIPTED worker failed','loss':None} if generation_null else None
        definition=None if generation_null else {'SCRIPTED':'submitted definition'}
        r={'request':request,'request_sha256':digest(request),'definition':definition,'generation_error':error,
            'draws':[] if generation_null else [{'suggestion':{'suggestion_id':identity,'candidate':clone(parent)}}],
            'observations':[] if generation_null else [o]};records[objective,g]=r
        component=None if generation_null else {'probe_attempts':0,'returned':0,'raised':0}
        traces[objective,g]={'component_testing':component,'events':[],'completed_steps':None if generation_null else 0}
        authors.append({**s,'request_sha256':r['request_sha256'],'definition':definition,'generation_error':error,
            'component_testing':component})
    selected={}
    for objective in p['objectives']:
        pool=[o for g in range(4) for o in records[objective,g]['observations'] if o['status']=='complete']
        loss=min(o['loss'] for o in pool);ids=[o['suggestion_id'] for o in pool if o['loss']==loss]
        selected[objective]={'loss':loss,'all_tied_ids':ids,'selected_id':ids[0],
            'system':clone(pool[0]['candidate']),'completed_submissions':len(pool)}
    a=seal({'schema':'scienceutopia.native-objective-instrument-loop-audit.v1','source_commit':p['source_commit'],
        'plan_sha256':p['content_sha256'],'closure':{'terminal':{'status':'closed'}},
        'source_proof':{'status':'verified-exact-source-closure'},'new_model_calls':0,'new_code_executions':0,
        'held_out_evaluation':False,'worlds':worlds,'authoring':authors,'selection':{'selected':selected},
        'developer_references':context})
    return p,a,records,traces


def test_all_eight_slots_two_kinds_of_null_both_scores_and_real_parent_are_retained(tmp_path,monkeypatch):
    p,a,records,traces=evidence(tmp_path,monkeypatch);a['worlds'].reverse();a['authoring'].reverse();seal(a)
    r=module.summarize(p,a,dict(reversed(list(records.items()))),traces)
    assert len(r['slots'])==8 and len(r['physical_worlds'])==12 and len(r['references'])==5
    assert r['slots'][0]['status']=='generation-failure' and r['slots'][0]['component_trace']['component_testing'] is None
    assert r['slots'][1]['status']=='failed' and r['slots'][1]['loss'] is None
    assert all(v is None for v in r['slots'][1]['cross_scores'].values())
    assert r['slots'][2]['parent_differs_from_design_anchor'] and not r['slots'][2]['changed_paths_from_parent']
    assert r['slots'][2]['changed_paths_from_anchor'] and r['slots'][2]['parent_matching_observation_ids']
    assert len(r['frozen_selection']['throughput']['all_tied_ids'])==3
    assert not r['interpretation']['held_out_evaluation'] and not r['interpretation']['scientific_truth']


@pytest.mark.parametrize('change',['slot','request','score','measurement','trace','selection','extra-world','context','stopped'])
def test_report_rejects_changed_or_inferred_evidence(tmp_path,monkeypatch,change):
    p,a,records,traces=evidence(tmp_path,monkeypatch);key=next(iter(records))
    if change=='slot':records.pop(key)
    elif change=='request':records[key]['request']['history'].append({'SCRIPTED':'changed'})
    elif change=='score':a['worlds'][0]['scores']['content-utility']=-999
    elif change=='measurement':a['worlds'][0]['physical_proof']['measurement']['metrics']['native.accepted_decisions']['value']=999
    elif change=='trace':traces[key]['component_testing']={'returned':999}
    elif change=='selection':a['selection']['selected']['throughput']['all_tied_ids'].pop()
    elif change=='extra-world':a['worlds'].append(clone(a['worlds'][0]))
    elif change=='context':a['developer_references']['content_sha256']='changed'
    else:a['closure']['terminal']['status']='stopped'
    seal(a)
    with pytest.raises(ValueError):module.summarize(p,a,records,traces)


def test_two_static_scientific_figures_are_byte_deterministic(tmp_path,monkeypatch):
    p,a,records,traces=evidence(tmp_path,monkeypatch);r=module.summarize(p,a,records,traces)
    one,two=tmp_path/'one',tmp_path/'two';one.mkdir();two.mkdir();module.render(r,one);module.render(r,two)
    assert {p.name:p.read_bytes() for p in one.iterdir()}=={p.name:p.read_bytes() for p in two.iterdir()}
    assert {p.name for p in one.iterdir()}=={'objective-loss-paths.png','objective-loss-paths.svg','objective-cross-scores.png','objective-cross-scores.svg'}
