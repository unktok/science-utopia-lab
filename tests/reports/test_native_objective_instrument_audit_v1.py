"""Audit joins with mocked physical/calibration primitives, real observer API.

No fake primitive here is independent evidence of real science or designer calls.
"""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import audit_native_objective_instrument_loop_v1 as module
from scripts import run_native_objective_instrument_loop_v1 as driver
from scripts.analyze_native_open_v7 import _inventory
from tests.reports.test_native_objective_instrument_loop_v1 import plan
from utopia.optimization.blackbox import Suggestion,Observation
from utopia.optimization.common_content_observer import CommonContentObserver
from utopia.optimization.loss import evaluate_loss,loss_spec_sha256
from utopia.system import SystemSpec
from utopia.system.design_patch import clone,digest


def setup(tmp_path,monkeypatch):
    p=plan(tmp_path,monkeypatch);root=tmp_path/'raw';root.mkdir();(root/'writer.lock').touch()
    driver.save(root/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    driver.save(root/'started.json',{'schema':driver.SCHEMA+'.start','plan_sha256':p['content_sha256'],
        'started_utc':'2026-11-11T18:00:00+00:00'})
    driver.save(root/'terminal.json',{'schema':driver.SCHEMA+'.terminal','status':'closed','complete_references':5,
        'ended_utc':'2026-11-11T18:04:00+00:00'})
    observer=CommonContentObserver(root/'observer',p['observer_contract'],backend=None);proofs={};states={}
    from scripts.native_observer_physical_v1 import reconstruct_measurement
    for label,system in p['reference_systems'].items():
        identity='reference-'+label;suggestion=Suggestion(identity,system,0,'developer-reference')
        directory=root/'references'/label;cell=directory/'worlds'/(identity+'-s61001');(cell/'replies').mkdir(parents=True)
        (cell/'replies/responses.sqlite').write_text('SCRIPTED cache; physical primitive mocked')
        path=cell/'checkpoint.json';path.write_text('SCRIPTED checkpoint; decoder mocked')
        spec=SystemSpec.from_dict(system)
        base={'run_id':cell.name,'system_fingerprint':spec.fingerprint,
            'measurement_schema':'scienceutopia.native-domain-measurements.v1','metrics':{
                'native.accepted_decisions':{'status':'measured','value':0},
                'native.accepted_peer_score_sum':{'status':'measured','value':0},
                'native.review_records':{'status':'measured','value':0}}}
        state={'native_system':{'spec':system,'last_year':4},'year':4,'phase':5,
            'portable':{'contract':{'simulation':{'num_years':4}}},'paper_tracker':{'papers':[]}}
        measurement=reconstruct_measurement(state,base,observer);loss=evaluate_loss(p['losses']['throughput'],[measurement])
        observation=Observation('observed-'+identity,identity,system,'complete',loss['loss'],{
            'system_fingerprint':spec.fingerprint,'loss_spec_sha256':loss_spec_sha256(p['losses']['throughput']),
            'loss_evaluation':loss,'measurements':[measurement],'technical_failures':[],
            'runs':[{'checkpoint_path':str(path)}]}).to_dict()
        driver.save(directory/'started.json',{'suggestion':suggestion.to_dict(),'seed':61001,'started_utc':'2026-11-11T18:00:01+00:00'})
        driver.save(directory/'observation.json',observation)
        driver.save(directory/'cross-scores.json',{k:evaluate_loss(v,[measurement]) for k,v in p['losses'].items()})
        states[str(path)]=state;proofs[cell.name]={'measurement':base,'status':'complete','SCRIPTED':True}
    audit=observer.audit();driver.save(root/'observer-audit.json',{k:v for k,v in audit.items() if k!='content_sha256'})
    context={'SCRIPTED':'mocked common reference validator'};context['content_sha256']=digest(context)
    driver.save(root/'developer-reference-context.json',{k:v for k,v in context.items() if k!='content_sha256'})
    driver.save(root/'developer-reference-context-ready.json',{'context_sha256':context['content_sha256'],
        'complete_references':5,'completed_utc':'2026-11-11T18:01:00+00:00'})
    controllers={}
    for objective in p['objectives']:
        records=[]
        for g in range(4):
            request={'SCRIPTED':'request','generation':g};request_sha=digest(request)
            records.append({'request':request,'request_sha256':request_sha,'definition':None,
                'generation_error':{'type':'ValueError','message':'SCRIPTED expected worker error','loss':None},
                'draws':[],'observations':[]})
            directory=root/'search'/objective;base=directory/f'readiness-{g}'/'editor-readiness'
            driver.save(base/'calibration/certificate.json',{'plan':{'request':request,'backend':p['backend'],'runtime':p['runtime'],
                'created_epoch':datetime.fromisoformat('2026-11-11T18:02:00+00:00').timestamp()},
                'completed_epoch':datetime.fromisoformat('2026-11-11T18:03:00+00:00').timestamp()})
            driver.save(base/'wire/dispatch-000.intent.json',{'SCRIPTED':'not actual model traffic'})
            generation=directory/'authoring'/('generation-'+request_sha)
            driver.save(generation/'intent.json',{'request':request,'source_commit':p['source_commit'],'provider':p['designer'],
                'post_edit_component_bank':p['component_bank'],'seconds':1800,'maximum_posts':16,
                'certificate':str((base/'calibration/certificate.json').resolve())})
        binding={'initial_system':p['initial_system'],'loss_spec':p['losses'][objective],'world':p['world'],'seeds':[61001],
            'strategies':p['strategies'],'mode':'blackbox','seed':p['optimizer_seed'],'learning_rate':.1,'strategy_learning_rate':.1,
            'strategy_baseline':0.,'exploration':.1,'design_space':p['design_space'],'development_references':context}
        controllers[objective]=SimpleNamespace(binding=binding,state={'pending':None,'records':records})
    driver.save(root/'selection.json',driver.selection(root,p,context,frozen_utc='2026-11-11T18:04:00+00:00',
        campaign_loader=lambda r,p,o,c:controllers[o]))
    monkeypatch.setattr(driver,'require_plan',lambda root:p)
    monkeypatch.setattr('scripts.native_benchmark_source.source_proofs',lambda *a,**k:{'status':'verified-exact-source-closure','SCRIPTED':True})
    monkeypatch.setattr('scripts.native_benchmark_physical.physical_proof',lambda cell,*a,**k:proofs[cell.name])
    monkeypatch.setattr('scripts.analyze_native_design_benchmark.loaded',lambda *a,**k:{'confirmed':True,'SCRIPTED':True})
    monkeypatch.setattr('utopia.runtime.checkpointing.read_portable_checkpoint',lambda path:states[str(path)])
    monkeypatch.setattr('utopia.optimization.native_development_references.build_context',lambda *a,**k:context)
    monkeypatch.setattr('scripts.analyze_native_autonomous_search_v14.replay_campaign',lambda directory,method:controllers[directory.parent.name])
    monkeypatch.setattr('scripts.audit_native_institution_loop_v1.request_at',lambda c,g:c.state['records'][g]['request'])
    monkeypatch.setattr('utopia.optimization.native_designer_preflight.require_certificate',lambda *a,**k:{'post_edit_component_contract':p['post_edit_contract']})
    def replay(directory):
        if directory.name=='editor-readiness':return None
        raise ValueError('SCRIPTED expected worker error')
    monkeypatch.setattr('utopia.optimization.native_bounded_staged_designer.replay',replay)
    return root,p


def test_full_join_preserves_five_references_eight_nulls_and_public_observer_audit_twice(tmp_path,monkeypatch):
    root,p=setup(tmp_path,monkeypatch);before=_inventory(root)
    module.worker(root,tmp_path/'audit-one.json');module.worker(root,tmp_path/'audit-two.json')
    assert (tmp_path/'audit-one.json').read_bytes()==(tmp_path/'audit-two.json').read_bytes() and before==_inventory(root)
    audit=driver.read(tmp_path/'audit-one.json')
    assert len(audit['worlds'])==5 and len(audit['readiness'])==len(audit['authoring'])==8
    assert all(r['wrapper_error'] and r['component_testing'] is None for r in audit['authoring'])
    assert audit['observer']==driver.read(root/'observer-audit.json') and not audit['selection']['baseline_fallback']


def test_reference_dispatch_role_is_checked_as_the_actual_suggestion_phase(tmp_path,monkeypatch):
    root,p=setup(tmp_path,monkeypatch);path=next((root/'references').glob('*/started.json'))
    value=driver.read(path);value['suggestion']['phase']='SCRIPTED unplanned role'
    path.unlink();driver.save(path,{k:v for k,v in value.items() if k!='content_sha256'})
    with pytest.raises(ValueError,match='reference dispatch differs'):module.worker(root,tmp_path/'no-audit.json')
