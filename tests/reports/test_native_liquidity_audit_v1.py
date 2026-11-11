"""Resource audit flow with scripted proof primitives and real ledger replay."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import audit_native_liquidity_support_v1 as module
from scripts import run_native_liquidity_support_v1 as driver
from tests.reports.test_native_liquidity_support_v1 import plan
from tests.system.test_native_resource_transfers import Actor
from utopia.optimization.loss import evaluate_loss
from utopia.funding.accounting import ResourceLedger
from utopia.system import SystemSpec
from utopia.utils.data_utils import file_sha256


def fixture(root,monkeypatch):
    root.mkdir();p=plan();monkeypatch.setattr(driver,'require_plan',lambda directory:p)
    driver.save(root/'started.json',{'schema':driver.SCHEMA+'.start','plan_sha256':p['content_sha256']})
    driver.save(root/'terminal.json',{'schema':driver.SCHEMA+'.terminal','status':'closed','complete_worlds':4})
    (root/'writer.lock').touch();measurements={};proofs={}
    for job in p['jobs']:
        identity=job['identity'];directory=root/'worlds-by-job'/identity
        cell=directory/'worlds'/(identity+'-s61001');(cell/'replies').mkdir(parents=True)
        (cell/'replies/responses.sqlite').write_text('SCRIPTED cache; physical primitive is mocked')
        metrics={k:{'status':'measured','value':v} for k,v in {
            'native.accepted_decisions':2,'native.accepted_peer_score_sum':7.,'native.review_records':3}.items()}
        measurement={'run_id':cell.name,'system_fingerprint':SystemSpec.from_dict(job['system']).fingerprint,
            'measurement_schema':'scienceutopia.native-domain-measurements.v1','metrics':metrics}
        measurements[identity]=measurement
        driver.save(directory/'started.json',{'job':job})
        scores={k:evaluate_loss(v,[measurement]) for k,v in p['losses'].items()}
        observation={'observation_id':'observed-'+identity,'suggestion_id':identity,'candidate':job['system'],
            'status':'complete','loss':scores['throughput']['loss'],'metadata':{'measurements':[measurement],'runs':[{}]}}
        driver.save(directory/'observation.json',observation);driver.save(directory/'cross-scores.json',scores)
        actors={str(i):Actor(str(i),30.) for i in range(5)}
        ledger=ResourceLedger();annual=[]
        for year in range(1,5):
            ledger.start_year(year,actors);ledger.close_year(year,actors)
            path=cell/'simulation'/f'portable_checkpoint_year_{year}.json.gz';path.parent.mkdir(exist_ok=True)
            path.write_text(json.dumps({'resource_ledger':ledger.to_dict(),
                'ecosystem_data':{'agents':[{k:getattr(a,k) for k in ('id','can_author','resources','is_active')}
                    for a in actors.values()]},'native_system':{'events':[]}}))
            annual.append({'year':year,'checkpoint_sha256':file_sha256(path)})
        proofs[identity]={'measurement':measurement,'annual_checkpoints':annual}
    monkeypatch.setattr('scripts.native_benchmark_source.source_proofs',lambda *a,**kw:{'status':'verified-exact-source-closure','SCRIPTED':True})
    monkeypatch.setattr('scripts.native_benchmark_physical.physical_proof',lambda cell,*a,**kw:proofs[cell.name.rsplit('-s',1)[0]])
    monkeypatch.setattr('scripts.analyze_native_design_benchmark.loaded',lambda *a,**kw:{'confirmed':True,'SCRIPTED':True})
    monkeypatch.setattr('utopia.optimization.native_discrete_policy.verify_native_observation',lambda *a:None)
    monkeypatch.setattr('utopia.runtime.checkpointing.read_portable_checkpoint',lambda path:json.loads(Path(path).read_text()))
    return p,proofs


def test_four_complete_jobs_join_actual_ledger_reconciliation_and_remain_read_only(tmp_path,monkeypatch):
    root=tmp_path/'raw';p,proofs=fixture(root,monkeypatch)
    module.worker(root,tmp_path/'audit-one.json');module.worker(root,tmp_path/'audit-two.json')
    assert (tmp_path/'audit-one.json').read_bytes()==(tmp_path/'audit-two.json').read_bytes()
    audit=driver.read(tmp_path/'audit-one.json')
    assert len(audit['worlds'])==4 and not audit['policy_selection']
    assert audit['new_model_calls']==audit['new_code_executions']==0
    assert sum(len(w['annual_resources']) for w in audit['worlds'])==16
    assert all(row['residual']==0 for w in audit['worlds'] for y in w['annual_resources'] for row in y['ledger_reconciliation'])


def test_changed_checkpoint_bytes_are_not_accepted_from_cached_annual_proof(tmp_path,monkeypatch):
    root=tmp_path/'raw';p,proofs=fixture(root,monkeypatch)
    path=next(root.rglob('portable_checkpoint_year_4.json.gz'));path.write_text(path.read_text()+' ')
    with pytest.raises(ValueError,match='annual resource checkpoint differs'):module.worker(root,tmp_path/'no-audit.json')
    assert not (tmp_path/'no-audit.json').exists()


def test_cost_adapter_adds_new_scope_without_relabeling_older_audits():
    from scripts.reports.pre_scale_costs_v1 import AUDITS
    assert AUDITS[6]=='scienceutopia.native-liquidity-support-audit.v1'
    assert AUDITS[5]=='scienceutopia.native-code-tested-loop-audit.v1'
