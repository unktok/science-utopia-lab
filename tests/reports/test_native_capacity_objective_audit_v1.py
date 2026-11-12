"""Cold-join unit checks with explicitly mocked physical/designer primitives.

Original factory/conservation/checkpoint execution is separately exercised by
test_native_capacity_full_path_v1; these joins are not actual-model evidence.
"""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import audit_native_capacity_objective_loop_v1 as module
from scripts import run_native_capacity_objective_loop_v1 as driver
from scripts.analyze_native_open_v7 import _inventory
from tests.reports.test_native_capacity_objective_loop_v1 import plan
from utopia.optimization.blackbox import Observation, Suggestion
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest


def setup(tmp_path,monkeypatch):
    p=plan(tmp_path/'inputs',monkeypatch);root=tmp_path/'run';root.mkdir()
    driver.save(root/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    driver.save(root/'started.json',{'schema':driver.SCHEMA+'.start','plan_sha256':p['content_sha256'],
        'started_utc':'2026-11-12T01:00:00+00:00','pid':123})
    driver.save(root/'terminal.json',{'schema':driver.SCHEMA+'.terminal','status':'closed','complete_references':5,
        'ended_utc':'2026-11-12T01:05:00+00:00'})
    context=driver.save(root/'developer-reference-context.json',{'SCRIPTED':'common references, not raw native evidence'})
    driver.save(root/'developer-reference-context-ready.json',{'context_sha256':context['content_sha256'],
        'complete_references':5,'completed_utc':'2026-11-12T01:02:00+00:00'})
    proofs={};rebuilt={}
    for label in p['reference_order']:
        identity='reference-'+label;directory=root/'references'/label;system=p['reference_systems'][label]
        cell=directory/'worlds'/(identity+'-s61001');(cell/'replies').mkdir(parents=True)
        (cell/'replies/responses.sqlite').write_text('SCRIPTED physical primitive')
        checkpoint=cell/'checkpoints/portable_checkpoint_year_4.json.gz'
        spec=SystemSpec.from_dict(system)
        base={'run_id':cell.name,'system_fingerprint':spec.fingerprint,'metrics':{
            'native.accepted_decisions':{'status':'measured','value':2}}}
        measurement={**clone(base),'metrics':{**base['metrics'],driver.METRIC:{'status':'measured','value':15}},
            'active_founder_boundary_instrument':{'SCRIPTED':'cold mapper, not actual flags'}}
        rebuilt[str(checkpoint.parent)]=measurement
        measurement={**measurement,'measurement_adapter_contract_sha256':digest(p['measurement_contract'])}
        scores={k:evaluate_loss(v,[measurement]) for k,v in p['losses'].items()}
        o=Observation('observation-'+identity,identity,system,'complete',scores['throughput']['loss'],{
            'system_fingerprint':spec.fingerprint,'loss_spec_sha256':loss_spec_sha256(p['losses']['throughput']),
            'loss_evaluation':scores['throughput'],'measurements':[measurement],
            'runs':[{'checkpoint_path':str(checkpoint)}],'technical_failures':[]}).to_dict()
        driver.save(directory/'started.json',{'suggestion':Suggestion(identity,system,0,'developer-reference').to_dict(),
            'seed':61001,'started_utc':'2026-11-12T01:01:00+00:00'})
        driver.save(directory/'observation.json',o);driver.save(directory/'cross-scores.json',scores)
        proofs[cell.name]={'status':'complete','measurement':base,'SCRIPTED':True}
    def binding(objective,refs=None):
        value={'initial_system':p['initial_system'],'loss_spec':p['losses'][objective],'world':p['world'],'seeds':[61001],
            'strategies':p['strategies'],'mode':'blackbox','seed':p['optimizer_seed'],'learning_rate':.1,
            'strategy_learning_rate':.1,'strategy_baseline':0.,'exploration':.1,'design_space':p['design_space']}
        if refs is not None:value['development_references']=refs
        return value
    def certificate(base,request,initial=False):
        driver.save(base/'calibration/certificate.json',{'plan':{'request':request,'backend':p['backend'],
            'runtime':p['runtime'],'created_epoch':datetime.fromisoformat(
                '2026-11-12T01:00:00+00:00' if initial else '2026-11-12T01:03:00+00:00').timestamp()},
            'completed_epoch':datetime.fromisoformat(
                '2026-11-12T01:00:01+00:00' if initial else '2026-11-12T01:04:00+00:00').timestamp()})
        driver.save(base/'wire/dispatch-000.intent.json',{'SCRIPTED':'not actual traffic'})
    prototype=SimpleNamespace(binding=binding('throughput'),state={'records':[],'pending':None})
    initial_request={'SCRIPTED':'empty prototype request'}
    certificate(root/'initial-readiness/editor-readiness',initial_request,initial=True)
    controllers={}
    for objective in p['objectives']:
        records=[]
        for g in range(2):
            request={'SCRIPTED':objective,'generation':g};request_sha=digest(request)
            records.append({'request':request,'request_sha256':request_sha,'definition':None,
                'generation_error':{'type':'ValueError','message':'SCRIPTED expected wrapper error','loss':None},
                'draws':[],'observations':[]})
            base=root/'search'/objective/f'readiness-{g}'/'editor-readiness';certificate(base,request)
            generation=root/'search'/objective/'authoring'/('generation-'+request_sha)
            driver.save(generation/'intent.json',{'request':request,'source_commit':p['source_commit'],
                'provider':p['designer'],'post_edit_component_bank':p['component_bank'],'seconds':1800,'maximum_posts':16,
                'certificate':str((base/'calibration/certificate.json').resolve())})
        controllers[objective]=SimpleNamespace(binding=binding(objective,context),state={'pending':None,'records':records})
    driver.save(root/'selection.json',driver.selection(root,p,context,frozen_utc='2026-11-12T01:05:00+00:00',
        campaign_loader=lambda r,p,o,c:controllers[o]))
    monkeypatch.setattr(driver,'require_plan',lambda root:p)
    monkeypatch.setattr('scripts.native_benchmark_source.source_proofs',lambda *a,**k:{'status':'verified-exact-source-closure','SCRIPTED':True})
    monkeypatch.setattr('scripts.native_benchmark_physical.physical_proof',lambda cell,*a,**k:proofs[cell.name])
    monkeypatch.setattr('scripts.analyze_native_design_benchmark.loaded',lambda *a,**k:{'confirmed':True,'SCRIPTED':True})
    monkeypatch.setattr('utopia.optimization.native_active_founders.measure_from_checkpoints',
        lambda base,paths:rebuilt[str(Path(paths[0]).parent)])
    monkeypatch.setattr('utopia.optimization.native_development_references.build_context',lambda *a,**k:context)
    monkeypatch.setattr('scripts.analyze_native_autonomous_search_v14.replay_campaign',
        lambda directory,method:prototype if 'initial-readiness' in directory.parts else controllers[directory.parent.name])
    monkeypatch.setattr('scripts.audit_native_institution_loop_v1.request_at',
        lambda c,g:initial_request if c is prototype else c.state['records'][g]['request'])
    monkeypatch.setattr('utopia.optimization.native_designer_preflight.require_certificate',
        lambda *a,**k:{'post_edit_component_contract':p['post_edit_contract']})
    def replay(directory):
        if directory.name=='editor-readiness':return None
        raise ValueError('SCRIPTED expected wrapper error')
    monkeypatch.setattr('utopia.optimization.native_bounded_staged_designer.replay',replay)
    return root,p


def test_two_cold_joins_keep_five_references_four_nulls_and_initial_gate(tmp_path,monkeypatch):
    root,p=setup(tmp_path,monkeypatch);before=_inventory(root)
    module.worker(root,tmp_path/'one.json');module.worker(root,tmp_path/'two.json')
    assert (tmp_path/'one.json').read_bytes()==(tmp_path/'two.json').read_bytes() and before==_inventory(root)
    a=driver.read(tmp_path/'one.json')
    assert len(a['worlds'])==5 and len(a['authoring'])==len(a['readiness'])==4
    assert a['initial_readiness'] and not a['selection']['baseline_fallback']


@pytest.mark.parametrize('change',['metric','early-reference','initial-request','extra-cache','critic','selection'])
def test_unbound_or_fabricated_evidence_is_rejected(tmp_path,monkeypatch,change):
    root,p=setup(tmp_path,monkeypatch)
    if change=='extra-cache':
        path=root/'unexpected/replies/responses.sqlite';path.parent.mkdir(parents=True);path.write_text('SCRIPTED extra')
    elif change=='critic':(root/'observer').mkdir()
    else:
        if change=='metric':
            path=next((root/'references').glob('*/observation.json'));v=driver.read(path)
            v['metadata']['measurements'][0]['metrics'][driver.METRIC]['value']=999
        elif change=='early-reference':
            path=next((root/'references').glob('*/started.json'));v=driver.read(path);v['started_utc']='2026-11-12T00:00:00+00:00'
        elif change=='initial-request':
            path=root/'initial-readiness/editor-readiness/calibration/certificate.json';v=driver.read(path);v['plan']['request']={'SCRIPTED':'wrong'}
        else:
            path=root/'selection.json';v=driver.read(path);v['baseline_fallback']=True
        path.unlink();driver.save(path,{k:x for k,x in v.items() if k!='content_sha256'})
    with pytest.raises(ValueError):module.worker(root,tmp_path/'must-not-pass.json')
