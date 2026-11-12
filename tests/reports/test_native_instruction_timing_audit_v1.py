"""Audit joins use real observer API but scripted physical primitives."""
from pathlib import Path

import pytest

from scripts import audit_native_instruction_timing_support_v1 as module
from scripts import run_native_instruction_timing_support_v1 as driver
from scripts.analyze_native_open_v7 import _inventory
from scripts.native_observer_physical_v1 import reconstruct_measurement
from tests.reports.test_native_instruction_timing_support_v1 import prospective_plan
from utopia.optimization.blackbox import Suggestion, Observation
from utopia.optimization.common_content_observer import CommonContentObserver
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.system import SystemSpec


def setup(tmp_path,monkeypatch):
    p=prospective_plan();root=tmp_path/'raw';root.mkdir();(root/'writer.lock').touch()
    driver.save(root/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    driver.save(root/'started.json',{'schema':driver.SCHEMA+'.start','plan_sha256':p['content_sha256'],
        'started_utc':'2026-11-12T00:00:00+00:00'})
    driver.save(root/'terminal.json',{'schema':driver.SCHEMA+'.terminal','status':'closed','completed_jobs':3,
        'ended_utc':'2026-11-12T00:04:00+00:00'})
    observer=CommonContentObserver(root/'observer',p['observer_contract'],backend=None)
    states={};proofs={}
    for job in p['jobs']:
        directory=root/'controls'/job['identity'];cell=directory/'worlds'/(job['identity']+'-s61001')
        (cell/'replies').mkdir(parents=True);(cell/'replies/responses.sqlite').write_text('SCRIPTED physical/cache primitive')
        path=cell/'checkpoint.json';path.write_text('SCRIPTED physical decoder')
        spec=SystemSpec.from_dict(job['system']);base={'run_id':cell.name,'system_fingerprint':spec.fingerprint,
            'measurement_schema':'scienceutopia.native-domain-measurements.v1','metrics':{
                'native.accepted_decisions':{'status':'measured','value':0},
                'native.accepted_peer_score_sum':{'status':'measured','value':0},
                'native.review_records':{'status':'measured','value':0}}}
        state={'native_system':{'spec':job['system'],'last_year':4},'year':4,'phase':5,
            'portable':{'contract':{'simulation':{'num_years':4}}},'paper_tracker':{'papers':[]}}
        m=reconstruct_measurement(state,base,observer);loss=evaluate_loss(p['losses']['throughput'],[m])
        o=Observation('observed-'+job['identity'],job['identity'],job['system'],'complete',loss['loss'],{
            'system_fingerprint':spec.fingerprint,'loss_spec_sha256':loss_spec_sha256(p['losses']['throughput']),
            'loss_evaluation':loss,'measurements':[m],'technical_failures':[],
            'runs':[{'checkpoint_path':str(path)}]}).to_dict()
        s=Suggestion(job['identity'],job['system'],0,'developer-instruction-timing-control')
        driver.save(directory/'started.json',{'job':job,'suggestion':s.to_dict(),'started_utc':'2026-11-12T00:00:01+00:00'})
        driver.save(directory/'observation.json',o)
        driver.save(directory/'cross-scores.json',{k:evaluate_loss(v,[m]) for k,v in p['losses'].items()})
        states[str(path)]=state;proofs[cell.name]={'measurement':base,'SCRIPTED':True}
    a=observer.audit();driver.save(root/'observer-audit.json',{k:v for k,v in a.items() if k!='content_sha256'})
    driver.progress(root,'closed')
    monkeypatch.setattr(driver,'require_plan',lambda root:p)
    monkeypatch.setattr('scripts.native_benchmark_source.source_proofs',lambda *a,**k:{'status':'verified-exact-source-closure','SCRIPTED':True})
    monkeypatch.setattr('scripts.native_benchmark_physical.physical_proof',lambda cell,*a,**k:proofs[cell.name])
    monkeypatch.setattr('scripts.analyze_native_design_benchmark.loaded',lambda *a,**k:{'confirmed':True,'SCRIPTED':True})
    monkeypatch.setattr('utopia.runtime.checkpointing.read_portable_checkpoint',lambda path:states[str(path)])
    monkeypatch.setattr('utopia.optimization.native_discrete_policy.verify_native_observation',lambda *a:None)
    return root,p


def test_actual_worker_join_and_public_observer_audit_roundtrip_twice(tmp_path,monkeypatch):
    root,p=setup(tmp_path,monkeypatch);before=_inventory(root)
    module.worker(root,tmp_path/'audit-one.json');module.worker(root,tmp_path/'audit-two.json')
    assert (tmp_path/'audit-one.json').read_bytes()==(tmp_path/'audit-two.json').read_bytes()
    assert _inventory(root)==before
    a=driver.read(tmp_path/'audit-one.json')
    assert a['schema']==driver.AUDIT_SCHEMA and len(a['worlds'])==3
    assert a['observer']==driver.read(root/'observer-audit.json')
    assert not a['new_model_calls'] and not a['new_code_executions'] and not a['policy_selection']


@pytest.mark.parametrize('change',['role','cross-score','unaccounted'])
def test_audit_rejects_changed_dispatch_score_or_unplanned_control(tmp_path,monkeypatch,change):
    root,p=setup(tmp_path,monkeypatch)
    if change=='role':
        path=root/'controls/instruction-cut/started.json';r=driver.read(path);r.pop('content_sha256')
        r['suggestion']['phase']='SCRIPTED different role';path.unlink();driver.save(path,r)
    elif change=='cross-score':
        path=root/'controls/instruction-cut/cross-scores.json';r=driver.read(path);r.pop('content_sha256')
        r['throughput']['loss']=-99;path.unlink();driver.save(path,r)
    else:(root/'controls/unaccounted').mkdir()
    with pytest.raises(ValueError):module.worker(root,tmp_path/'must-not-pass.json')
