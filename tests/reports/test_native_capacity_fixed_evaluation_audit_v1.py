"""SCRIPTED cold joins; physical/calibration identities here are explicitly mocked."""
from pathlib import Path

import pytest

from scripts import run_native_capacity_fixed_evaluation_v1 as driver
from scripts import audit_native_capacity_fixed_evaluation_v1 as module
from scripts.analyze_native_open_v7 import _inventory
from tests.reports.test_native_capacity_fixed_evaluation_v1 import setup as setup_run
from utopia.optimization.blackbox import Observation,Suggestion
from utopia.optimization.loss import evaluate_loss,loss_spec_sha256
from utopia.system import SystemSpec
from utopia.system.design_patch import clone,digest


def setup(tmp_path,monkeypatch):
    root,p,_=setup_run(tmp_path,monkeypatch);proofs={};rebuilt={}
    def observe(root,p,job):
        identity=job['identity'];directory=root/'evaluation'/identity
        cell=directory/'worlds'/(identity+'-s'+str(job['seed']));(cell/'replies').mkdir(parents=True)
        (cell/'replies/responses.sqlite').write_text('SCRIPTED journal placeholder')
        checkpoint=cell/'simulation/checkpoints/portable_checkpoint_year_4.json.gz'
        spec=SystemSpec.from_dict(job['system'])
        base={'run_id':cell.name,'system_fingerprint':spec.fingerprint,
            'metrics':{'native.accepted_decisions':{'status':'measured','value':2}}}
        m={**clone(base),'metrics':{**base['metrics'],'native.active_founder_boundary_sum':{
            'status':'measured','value':15}},'active_founder_boundary_instrument':{'SCRIPTED':'not actual flags'}}
        rebuilt[str(checkpoint.parent)]=clone(m)
        m['measurement_adapter_contract_sha256']=digest(p['measurement_contract'])
        scores={k:evaluate_loss(v,[m]) for k,v in p['losses'].items()}
        o=Observation('observation-'+identity,identity,job['system'],'complete',scores['throughput']['loss'],{
            'system_fingerprint':spec.fingerprint,'loss_spec_sha256':loss_spec_sha256(p['losses']['throughput']),
            'loss_evaluation':scores['throughput'],'measurements':[m],
            'runs':[{'checkpoint_path':str(checkpoint)}],'technical_failures':[]}).to_dict()
        driver.save(directory/'started.json',{**clone(job),'suggestion':Suggestion(
            identity,job['system'],0,'selection-fixed-evaluation').to_dict(),'started_utc':driver.utc()})
        driver.save(directory/'observation.json',o);driver.save(directory/'cross-scores.json',scores)
        proofs[cell.name]={'status':'complete','measurement':base,'SCRIPTED':True}
    monkeypatch.setattr(driver,'observe',observe);driver.run(root)
    monkeypatch.setattr('scripts.native_benchmark_source.source_proofs',
        lambda *a,**k:{'status':'verified-exact-source-closure','SCRIPTED':True})
    monkeypatch.setattr('scripts.native_benchmark_physical.physical_proof',lambda cell,*a,**k:proofs[cell.name])
    monkeypatch.setattr('scripts.analyze_native_design_benchmark.loaded',lambda *a,**k:{'confirmed':True,'SCRIPTED':True})
    monkeypatch.setattr('utopia.optimization.native_active_founders.measure_from_checkpoints',
        lambda base,paths:rebuilt[str(Path(paths[0]).parent)])
    monkeypatch.setattr('utopia.optimization.native_discrete_policy.verify_native_observation',lambda *a:None)
    return root,p


def replace(path,value):
    path.unlink();driver.save(path,{k:v for k,v in value.items() if k!='content_sha256'})


def test_two_cold_exports_preserve_all_jobs_literal_selection_and_no_new_calls(tmp_path,monkeypatch):
    root,p=setup(tmp_path,monkeypatch);before=_inventory(root)
    module.worker(root,tmp_path/'one.json');module.worker(root,tmp_path/'two.json')
    assert (tmp_path/'one.json').read_bytes()==(tmp_path/'two.json').read_bytes()
    assert before==_inventory(root)
    a=driver.read(tmp_path/'one.json')
    assert a['fixed_selection']==p['fixed_selection'] and len(a['worlds'])==10
    assert {w['seed'] for w in a['worlds']}=={67101,67107}
    assert not a['independent_optimizer_replications'] and not a['new_model_calls']
    assert not a['new_code_executions'] and not a['publication_ready']


@pytest.mark.parametrize('change',['metric','cross-score','dispatch','extra-cache','critic','extra-designer','used-seed','progress','terminal'])
def test_fabricated_measurements_dispatches_and_closures_are_rejected(tmp_path,monkeypatch,change):
    root,_=setup(tmp_path,monkeypatch)
    if change=='extra-cache':
        path=root/'unplanned/replies/responses.sqlite';path.parent.mkdir(parents=True);path.write_text('SCRIPTED extra')
    elif change=='critic':(root/'observer').mkdir()
    elif change=='extra-designer':driver.save(root/'unplanned/wire/dispatch-000.intent.json',{'SCRIPTED':'extra'})
    elif change=='progress':(root/'progress.json').write_text('{"stage":"evaluation","active":null}')
    else:
        if change=='metric':
            path=next((root/'evaluation').glob('*/observation.json'));v=driver.read(path)
            v['metadata']['measurements'][0]['metrics']['native.active_founder_boundary_sum']['value']=999
        elif change=='cross-score':
            path=next((root/'evaluation').glob('*/cross-scores.json'));v=driver.read(path);v['founder-activity']['loss']=0
        elif change=='dispatch':
            path=next((root/'evaluation').glob('*/started.json'));v=driver.read(path);v['seed']=100
        elif change=='used-seed':
            path=root/'pre-dispatch-seed-usage-00.json';v=driver.read(path);v['prior_matching_runs']=[{'SCRIPTED':'already used'}]
        else:path=root/'terminal.json';v=driver.read(path);v['status']='stopped'
        replace(path,v)
    with pytest.raises(ValueError):module.worker(root,tmp_path/'must-not-pass.json')
