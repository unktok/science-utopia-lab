"""Cold evaluation joins; physical/native primitives explicitly scripted here."""
import pytest

from scripts import audit_native_objective_fixed_evaluation_v1 as module
from scripts import run_native_objective_fixed_evaluation_v1 as driver
from scripts.analyze_native_open_v7 import _inventory
from scripts.native_observer_physical_v1 import reconstruct_measurement
from tests.reports.test_native_objective_fixed_evaluation_v1 import evidence,seal
from utopia.optimization.blackbox import Suggestion,Observation
from utopia.optimization.common_content_observer import CommonContentObserver
from utopia.optimization.loss import evaluate_loss,loss_spec_sha256
from utopia.system import SystemSpec
from utopia.system.design_patch import clone


def setup(tmp_path,monkeypatch):
    original,old,p=evidence(tmp_path,monkeypatch);root=tmp_path/'raw';root.mkdir();(root/'writer.lock').touch()
    usage={'valid':True,'errors':[],'prior_matching_runs':[],'root':'SCRIPTED-root',
        'seeds':p['evaluation']['seeds'],'checked_utc':'2026-11-11T18:01:00+00:00'};seal(usage)
    p['evaluation']['seed_usage']=[usage['content_sha256']];seal(p)
    for name in ('seed-usage-00.json','pre-dispatch-seed-usage-00.json'):
        driver.save(root/name,{k:v for k,v in usage.items() if k!='content_sha256'})
    driver.save(root/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    driver.save(root/'started.json',{'schema':driver.SCHEMA+'.start','plan_sha256':p['content_sha256'],
        'started_utc':'2026-11-11T18:02:00+00:00'})
    driver.save(root/'terminal.json',{'schema':driver.SCHEMA+'.terminal','status':'closed','completed_jobs':len(p['jobs']),
        'ended_utc':'2026-11-11T18:05:00+00:00'})
    driver.progress(root,'closed');observer=CommonContentObserver(root/'observer',p['observer_contract'],backend=None)
    states={};proofs={}
    for index,job in enumerate(p['jobs']):
        directory=root/'evaluation'/job['identity'];cell=directory/'worlds'/(job['identity']+'-s'+str(job['seed']))
        (cell/'replies').mkdir(parents=True);(cell/'replies/responses.sqlite').write_text('SCRIPTED physical primitive')
        checkpoint=cell/'checkpoint.json';checkpoint.write_text('SCRIPTED checkpoint decoder')
        spec=SystemSpec.from_dict(job['system'])
        base={'run_id':cell.name,'system_fingerprint':spec.fingerprint,
            'measurement_schema':'scienceutopia.native-domain-measurements.v1','metrics':{
                'native.accepted_decisions':{'status':'measured','value':0},
                'native.accepted_peer_score_sum':{'status':'measured','value':0},
                'native.review_records':{'status':'measured','value':0}}}
        state={'native_system':{'spec':job['system'],'last_year':4},'year':4,'phase':5,
            'portable':{'contract':{'simulation':{'num_years':4}}},'paper_tracker':{'papers':[]}}
        measurement=reconstruct_measurement(state,base,observer)
        failed=index==0;measurements=[] if failed else [measurement]
        scores={k:evaluate_loss(v,measurements) for k,v in p['losses'].items()}
        o=Observation('observed-'+job['identity'],job['identity'],job['system'],'failed' if failed else 'complete',
            scores['throughput']['loss'],{'system_fingerprint':spec.fingerprint,
                'loss_spec_sha256':loss_spec_sha256(p['losses']['throughput']),'loss_evaluation':scores['throughput'],
                'runs':[{'checkpoint_path':str(checkpoint)}],'measurements':measurements,
                'technical_failures':[{'SCRIPTED':'completed world, missing critic measurement'}] if failed else []}).to_dict()
        suggestion=Suggestion(job['identity'],job['system'],0,'selection-fixed-evaluation')
        driver.save(directory/'started.json',{**clone(job),'suggestion':suggestion.to_dict(),'started_utc':'2026-11-11T18:03:00+00:00'})
        driver.save(directory/'observation.json',o);driver.save(directory/'cross-scores.json',scores)
        states[str(checkpoint)]=state;proofs[cell.name]={'status':'complete','measurement':base,'SCRIPTED':True}
    a=observer.audit();driver.save(root/'observer-audit.json',{k:v for k,v in a.items() if k!='content_sha256'})
    monkeypatch.setattr(driver,'require_plan',lambda root:p)
    monkeypatch.setattr('scripts.native_benchmark_source.source_proofs',lambda *a,**k:{'status':'verified-exact-source-closure','SCRIPTED':True})
    monkeypatch.setattr('scripts.native_benchmark_physical.physical_proof',lambda cell,*a,**k:proofs[cell.name])
    monkeypatch.setattr('scripts.analyze_native_design_benchmark.loaded',lambda *a,**k:{'confirmed':True,'SCRIPTED':True})
    monkeypatch.setattr('utopia.runtime.checkpointing.read_portable_checkpoint',lambda path:states[str(path)])
    monkeypatch.setattr('utopia.optimization.native_discrete_policy.verify_native_observation',lambda *a:None)
    return root,p


def test_two_cold_joins_retain_all_jobs_and_completed_world_with_missing_measurement(tmp_path,monkeypatch):
    root,p=setup(tmp_path,monkeypatch);before=_inventory(root)
    module.worker(root,tmp_path/'audit-1.json');module.worker(root,tmp_path/'audit-2.json')
    assert (tmp_path/'audit-1.json').read_bytes()==(tmp_path/'audit-2.json').read_bytes() and before==_inventory(root)
    a=driver.read(tmp_path/'audit-1.json');assert len(a['worlds'])==15 and a['fixed_selection']==p['fixed_selection']
    assert a['worlds'][0]['status']=='failed' and all(v is None for v in a['worlds'][0]['scores'].values())
    assert a['worlds'][0]['physical_proof']['status']=='complete' and a['worlds'][0]['measurements']==[]
    assert a['observer']==driver.read(root/'observer-audit.json')


@pytest.mark.parametrize('change',['dispatch','usage','score','stopped','extra-designer'])
def test_cold_join_rejects_unbound_records_without_repair(tmp_path,monkeypatch,change):
    root,p=setup(tmp_path,monkeypatch)
    if change=='extra-designer':
        driver.save(root/'unexpected/wire/dispatch-000.intent.json',{'SCRIPTED':'unplanned'} )
    else:
        if change=='dispatch':path=next((root/'evaluation').glob('*/started.json'));v=driver.read(path);v['seed']=-1
        elif change=='usage':path=root/'pre-dispatch-seed-usage-00.json';v=driver.read(path);v['valid']=False
        elif change=='score':path=next((root/'evaluation').glob('*/cross-scores.json'));v=driver.read(path);v['throughput']['loss']=999
        else:path=root/'terminal.json';v=driver.read(path);v['status']='stopped'
        path.unlink();driver.save(path,{k:x for k,x in v.items() if k!='content_sha256'})
    with pytest.raises(ValueError):module.worker(root,tmp_path/'must-not-pass.json')
