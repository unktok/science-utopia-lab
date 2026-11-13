"""Joint frozen-selection contracts with explicit SCRIPTED upstream evidence."""
from pathlib import Path
import json

import pytest

from scripts import run_native_joint_fixed_evaluation_v1 as driver
from scripts.run_native_objective_fixed_evaluation_v1 import fixed_selection
from tests.reports.test_native_planning_objective_loop_v1 import plan as planning_plan, seal
from tests.reports.test_native_capacity_fixed_evaluation_v1 import usage
from utopia.optimization.common_content_observer import ObserverCompletionUnknown
from utopia.system.design_patch import clone


def audited(p,kind,*,missing=()):
    keys=p['arm_order'] if kind=='presentation' else p['objectives']
    worlds=[];selected={}
    for key in keys:
        objective=p['arms'][key]['objective'] if kind=='presentation' else key
        system=clone(p['reference_systems'][p['reference_order'][1 if objective=='throughput' else 6]])
        if kind=='numeric' and objective=='throughput':
            next(n for n in system['mechanisms'] if n['mechanism_id']=='developer-liquidity-director')['parameters']['reserve_units']=22
        ids=[]
        for generation in range(3):
            if key in missing:continue
            identity='SCRIPTED-'+kind+'-'+key+'-'+str(generation);ids.append(identity)
            worlds.append({'identity':identity,'system':clone(system),'status':'complete',
                'scores':{'throughput':-2.,'content-utility':-1.},
                'role':'numeric-own-proposal' if kind=='numeric' else 'search:'+key,
                'objective':objective,'generation':generation})
        selected[key]={'loss':None if not ids else (-2. if objective=='throughput' else -1.),
            'completed_submissions':len(ids),'all_tied_ids':ids,'selected_id':ids[0] if ids else None,
            'system':system if ids else None}
    schema={'planning':'scienceutopia.native-planning-objective-loop-audit.v1',
        'presentation':'scienceutopia.native-parent-presentation-loop-audit.v1',
        'numeric':'scienceutopia.native-parameter-comparator-audit.v1'}[kind]
    selection=seal({'plan_sha256':p['content_sha256'],'baseline_fallback':False,'held_out_evaluation':False,'selected':selected})
    return seal({'schema':schema,'source_commit':p['source_commit'],'plan_sha256':p['content_sha256'],
        'source_proof':{'status':'verified-exact-source-closure','SCRIPTED':'not actual provenance'},
        'closure':{'terminal':{'status':'closed'}},'selection':selection,'worlds':worlds,
        'new_model_calls':0,'new_code_executions':0,'held_out_evaluation':False,
        'developer_references':seal({'SCRIPTED':'not actual reference context'})})


def evidence(tmp_path,monkeypatch,*,seeds=None,image_override=None):
    old,_,_,_=planning_plan(tmp_path,monkeypatch,image_override=image_override)
    presentation=clone(old);presentation['schema']='scienceutopia.native-parent-presentation-loop.v1.plan'
    presentation['arm_order']=['throughput-control','content-utility-literal','content-utility-control','throughput-literal']
    presentation['arms']={a:{'objective':'throughput' if a.startswith('throughput-') else 'content-utility',
        'presentation':a.rsplit('-',1)[-1]} for a in presentation['arm_order']};seal(presentation)
    numeric=clone(old);numeric['schema']='scienceutopia.native-parameter-comparator.v1.plan'
    old_audit=audited(old,'planning')
    numeric['origin_audit_content_sha256']=old_audit['content_sha256']
    numeric['reference_context_sha256']=old_audit['developer_references']['content_sha256'];seal(numeric)
    values={'planning':(old,old_audit),'presentation':(presentation,audited(presentation,'presentation')),
        'numeric':(numeric,audited(numeric,'numeric',missing=('content-utility',)))}
    seeds=[81701,81707] if seeds is None else seeds
    origins={k:{'run':str(tmp_path/('origin-'+k)),'SCRIPTED':'not actual original closure'} for k in driver.STUDIES}
    p=seal(driver.build_plan(values,source='e'*40,origins=origins,usages=[usage(seeds)],seeds=seeds,
        observer_backend=old['observer_contract']['backend'],native_sources={'original_source':old['source_commit'],'SCRIPTED':True}))
    return values,p


def test_three_study_selection_abis_literal_ties_and_no_numeric_fallback(tmp_path,monkeypatch):
    values,p=evidence(tmp_path,monkeypatch)
    for kind,(original,audit) in values.items():
        assert fixed_selection(original,audit,study=driver.STUDIES[kind])==audit['selection']
    assert len(p['selection_order'])==8 and len(p['fixed_selection']['selected'])==8
    assert p['fixed_selection']['selected']['numeric:content-utility']['system'] is None
    assert p['fixed_selection']['original_selections']=={k:a['selection'] for k,(_,a) in values.items()}
    assert p['evaluation']['maximum_physical_worlds']==32 and len(p['jobs'])==18
    assert p['budget']['designer_generation_POSTs']==0 and not p['budget']['replace_failed_slots']
    assert p['budget']['observer_POSTs_upper_bound']==6000 and p['claims']['candidate_reselection'] is False
    assert len(p['contrasts'])==8
    assert all('selected:numeric:content-utility' not in j['labels'] for j in p['jobs'])
    shared=[j for j in p['jobs'] if 'selected:planning:throughput' in j['labels']]
    assert len(shared)==2 and all('selected:presentation:throughput-control' in j['labels'] for j in shared)
    assert all('reference:advice-reserve21-all' in j['labels'] for j in shared)
    roundtrip=json.loads(json.dumps(p,sort_keys=True))
    assert p['jobs']==driver.jobs_for(roundtrip)
    assert [label for label in shared[0]['labels'] if label.startswith('selected:')]==[
        'selected:'+key for key in p['selection_order'] if key in (
            'planning:throughput','presentation:throughput-control','presentation:throughput-literal')]


@pytest.mark.parametrize('change',['stopped','fallback','tie','system','science','reference','bank','judge','used','missing-origin','bool','development','duplicate','four','empty'])
def test_changed_origin_selection_science_bank_or_seed_rejected(tmp_path,monkeypatch,change):
    values,p=evidence(tmp_path,monkeypatch);seeds=clone(p['evaluation']['seeds']);u=usage(seeds)
    if change=='stopped':values['presentation'][1]['closure']['terminal']['status']='stopped'
    elif change=='fallback':values['numeric'][1]['selection']['baseline_fallback']=True
    elif change=='tie':values['presentation'][1]['selection']['selected']['throughput-literal']['all_tied_ids'].pop()
    elif change=='system':values['numeric'][1]['selection']['selected']['throughput']['system']['metadata']['SCRIPTED']='not literal'
    elif change=='science':values['presentation'][0]['world']['world_conditions']['initial_funding']=999
    elif change=='reference':values['presentation'][0]['reference_systems']['cut-reserve21-all']['metadata']['SCRIPTED']='not same'
    elif change=='bank':values['numeric'][0]['origin_audit_content_sha256']='f'*64
    elif change=='judge':values['numeric'][0]['observer_contract']['options']['temperature']=.7
    elif change=='used':u['prior_matching_runs']=[{'SCRIPTED':True}]
    elif change=='missing-origin':values.pop('numeric')
    elif change=='bool':seeds=[True]
    elif change=='development':seeds=[61001]
    elif change=='duplicate':seeds=[81701,81701]
    elif change=='four':seeds=[81701,81703,81707,81709]
    elif change=='empty':seeds=[]
    for original,audit in values.values():
        seal(original);audit['plan_sha256']=original['content_sha256']
        audit['selection']['plan_sha256']=original['content_sha256'];seal(audit['selection']);seal(audit)
    u['seeds']=clone(seeds);seal(u)
    with pytest.raises(ValueError):
        driver.build_plan(values,source='e'*40,origins=p['origins'],usages=[u],seeds=seeds,
            observer_backend=p['observer_contract']['backend'],native_sources=p['original_native_sources'])


def setup(tmp_path,monkeypatch):
    values,p=evidence(tmp_path/'inputs',monkeypatch);root=tmp_path/'evaluation';root.mkdir()
    for origin in p['origins'].values():
        Path(origin['run']).mkdir(parents=True);(Path(origin['run'])/'writer.lock').touch()
    inventory=tmp_path/'inventory';inventory.mkdir();u=usage(p['evaluation']['seeds']);u['root']=str(inventory);seal(u)
    p['evaluation']['seed_usage']=[u['content_sha256']];seal(p)
    driver.save(root/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    driver.save(root/'seed-usage-00.json',{k:v for k,v in u.items() if k!='content_sha256'})
    monkeypatch.setattr(driver,'require_environment',lambda:None)
    monkeypatch.setattr(driver,'require_plan',lambda root:p)
    monkeypatch.setattr(driver,'usage_inventory',lambda *a:u)
    monkeypatch.setattr(driver,'LocalObserverBackend',lambda **kw:None)
    return root,p,u


def test_every_frozen_job_consumes_once_and_no_model_authoring(tmp_path,monkeypatch):
    root,p,_=setup(tmp_path,monkeypatch);calls=[]
    monkeypatch.setattr(driver,'observe',lambda root,p,job,observer:calls.append(clone(job)))
    driver.run(root)
    assert calls==p['jobs'] and driver.read(root/'terminal.json')['completed_jobs']==18
    assert driver.read(root/'terminal.json')['status']=='closed'
    with pytest.raises(ValueError,match='consumed'):driver.run(root)


def test_unknown_observer_completion_stops_remaining_seeds(tmp_path,monkeypatch):
    root,_,_=setup(tmp_path,monkeypatch);calls=[]
    def unknown(*args):calls.append(1);raise ObserverCompletionUnknown('SCRIPTED unknown completion')
    monkeypatch.setattr(driver,'observe',unknown)
    with pytest.raises(ObserverCompletionUnknown):driver.run(root)
    assert len(calls)==1 and driver.read(root/'terminal.json')['status']=='stopped'


def test_new_seed_consumption_blocks_before_start(tmp_path,monkeypatch):
    root,_,u=setup(tmp_path,monkeypatch);u['valid']=False;seal(u)
    monkeypatch.setattr(driver,'observe',lambda *a:pytest.fail('no new inference'))
    with pytest.raises(ValueError,match='consumed after preparation'):driver.run(root)
    assert not (root/'started.json').exists()


def test_source_whitespace_and_annotations_are_not_normalized_into_a_shared_policy(tmp_path,monkeypatch):
    values,p=evidence(tmp_path,monkeypatch)
    a=values['presentation'][1];key='throughput-literal'
    system=a['selection']['selected'][key]['system']
    node=next(n for n in system['mechanisms'] if n['implementation']=='code.python.v1')
    node['parameters']['code_artifact']['source']+='\n# SCRIPTED distinct literal source\n'
    for w in a['worlds']:
        if w['role']=='search:'+key:w['system']=clone(system)
    seal(a['selection']);seal(a)
    new=driver.build_plan(values,source=p['source_commit'],origins=p['origins'],usages=[usage(p['evaluation']['seeds'])],
        seeds=p['evaluation']['seeds'],observer_backend=p['observer_contract']['backend'],native_sources=p['original_native_sources'])
    assert len(new['jobs'])==20
    selected=[j for j in new['jobs'] if 'selected:presentation:throughput-literal' in j['labels']]
    assert len(selected)==2 and all(j['labels']==['selected:presentation:throughput-literal'] for j in selected)


def test_disappeared_seed_root_cannot_be_misread_as_unused_empty_directory(tmp_path,monkeypatch):
    root,_,u=setup(tmp_path,monkeypatch);Path(u['root']).rmdir()
    monkeypatch.setattr(driver,'observe',lambda *a:pytest.fail('no new inference'))
    with pytest.raises(ValueError,match='root disappeared'):driver.run(root)
    assert not (root/'started.json').exists()
