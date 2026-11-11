"""New audit environment checks; proof primitives are explicitly scripted QA."""
from copy import deepcopy
import json
import sqlite3
from types import SimpleNamespace
import pytest

from scripts import native_benchmark_physical as audit
from utopia.system.native_kernel import legacy_world_system
from utopia.utils.data_utils import file_sha256


def fixture(cell,monkeypatch,seed=31001,years=4):
    system=legacy_world_system(seed=seed);world={'model':'SCRIPTED-model','model_digest':'SCRIPTED-digest',
        'corpus_sha256':'SCRIPTED-corpus','source_commit':'a'*40,'experiment':{'role':'SCRIPTED'},
        'runtime_seed_binding':{'python_hash_seed_environment':'42'}}
    config={'source_commit':world['source_commit'],'years':years,'corpus_years':4,
        'runtime_seed_binding':world['runtime_seed_binding'],'experiment':world['experiment'],
        'population':{'institutions':5,'per_institution':1,'strategy':'balanced'},
        'thinking_override':False,'max_tokens':768,'maximum_http_attempts':512 if years==2 else 1024,
        'lab_inference_serialized':True}
    binding={'cell':system.fingerprint,'seed':seed,'model':world['model'],'model_revision':world['model_digest'],
        'corpus_sha256':world['corpus_sha256'],'science_config':config}
    cache=cell/'replies/responses.sqlite';cache.parent.mkdir(parents=True)
    with sqlite3.connect(cache) as db:
        db.execute('CREATE TABLE metadata (binding TEXT)');db.execute('INSERT INTO metadata VALUES (?)',(json.dumps(binding),))
    (cell/'system.json').write_text(json.dumps(system.to_dict()))
    states={}
    for year in range(years+1):
        path=cell/'simulation/checkpoints/SCRIPTED'/f'portable_checkpoint_year_{year}.json.gz'
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(('SCRIPTED checkpoint '+str(year)).encode())
        states[path.name]={'year':year,'phase':0 if year==0 else 5,
            'portable':{'contract':{'binding':binding,'native_system':{'system_fingerprint':system.fingerprint},
                'model':world['model'],'model_revision':world['model_digest']},
                'response_cache_count':year,'llm_call_stats':{'elapsed_seconds':year}},
            'native_system':{'spec':system.to_dict(),'events':[],'last_year':year,'event_stream_hash':'SCRIPTED'},
            'rag':{'ordered_documents_sha256':world['corpus_sha256']},
            'ecosystem_data':{'agents':[{'id':str(i),'can_author':True} for i in range(5)]}}
    evidence={'checkpoint_path':str(path),'checkpoint_sha256':file_sha256(path),'seed':seed,
        'run_id':cell.name,'system_fingerprint':system.fingerprint,'event_stream_hash':'SCRIPTED'}
    monkeypatch.setattr(audit,'read_portable_checkpoint',lambda path:deepcopy(states[path.name]))
    monkeypatch.setattr(audit,'NativeScienceKernel',lambda *a,**kw:SimpleNamespace(design_history=[]))
    monkeypatch.setattr(audit,'zero_http_response_proofs',lambda *a,**kw:{'wire_requests':years,
        'responses_by_physical_year':{str(y):1 for y in range(1,years+1)}})
    monkeypatch.setattr(audit,'code_proofs',lambda *a,**kw:{'SCRIPTED':True})
    monkeypatch.setattr(audit,'physical_initial_identity',lambda state:{'SCRIPTED':True})
    monkeypatch.setattr(audit,'checkpoint_measurements',lambda *a:{'SCRIPTED':True})
    monkeypatch.setattr(audit,'domain_proofs',lambda *a:{'SCRIPTED':True})
    monkeypatch.setattr(audit,'context_input_proofs',lambda *a:{'SCRIPTED':True})
    return system,world,evidence,states


def test_declared_non42_seed_and_four_year_horizon_are_audited_not_replaced_by_legacy_defaults(tmp_path,monkeypatch):
    cell=tmp_path/'SCRIPTED-world';s,w,e,_=fixture(cell,monkeypatch)
    r=audit.physical_proof(cell,s,world=w,seed=31001,years=4,evidence=e)
    assert r['status']=='complete' and r['seed']==31001 and len(r['annual_checkpoints'])==4
    assert r['new_model_calls']==r['new_code_executions']==0
    with pytest.raises(ValueError,match='source/model/data/seed'):audit.physical_proof(cell,s,world=w,seed=42,years=4,evidence=e)
    with pytest.raises(ValueError):audit.physical_proof(cell,s,world=w,seed=31001,years=2,evidence=e)


def test_wrong_http_budget_and_missing_annual_prefix_are_visible_audit_failures(tmp_path,monkeypatch):
    cell=tmp_path/'SCRIPTED-world';s,w,e,states=fixture(cell,monkeypatch)
    monkeypatch.setattr(audit,'zero_http_response_proofs',lambda *a,**kw:{'wire_requests':1025,'responses_by_physical_year':{}})
    with pytest.raises(ValueError,match='HTTP attempts'):audit.physical_proof(cell,s,world=w,seed=31001,years=4,evidence=e)
    # Remove exactly the disposable scripted year3 fixture, not any research record.
    (cell/'simulation/checkpoints/SCRIPTED/portable_checkpoint_year_3.json.gz').unlink()
    with pytest.raises(ValueError,match='annual checkpoint'):audit.physical_proof(cell,s,world=w,seed=31001,years=4,evidence=e)


def test_empty_bound_cache_before_initial_checkpoint_is_null_not_a_fabricated_world(tmp_path,monkeypatch):
    cell=tmp_path/'SCRIPTED-world';s,w,e,_=fixture(cell,monkeypatch)
    for path in cell.rglob('portable_checkpoint_year_*.json.gz'):path.unlink()  # disposable QA only
    monkeypatch.setattr(audit,'zero_http_response_proofs',lambda *a,**kw:{'wire_requests':0,'researcher_responses':0})
    monkeypatch.setattr(audit,'code_proofs',lambda *a,**kw:{'recorded_executions':0})
    result=audit.physical_proof(cell,s,world=w,seed=31001,years=4)
    assert result['measurement'] is None and result['initial_identity'] is None
    assert result['status']=='technical-failure-before-initial-checkpoint'
    with pytest.raises(ValueError,match='initial checkpoint'):
        audit.physical_proof(cell,s,world=w,seed=31001,years=4,evidence=e)
    monkeypatch.setattr(audit,'zero_http_response_proofs',lambda *a,**kw:{'wire_requests':1,'researcher_responses':0})
    with pytest.raises(ValueError,match='activity without original'):
        audit.physical_proof(cell,s,world=w,seed=31001,years=4)


def test_optional_world_conditions_bind_cache_and_actual_founder_records(tmp_path,monkeypatch):
    from utopia.simulation import build_population_blueprint
    cell=tmp_path/'SCRIPTED-world';s,w,e,states=fixture(cell,monkeypatch)
    conditions={'schema':'scienceutopia.native-world-conditions.v1','initial_funding':60.,
        'population_resource_profile':'balanced_two_band','log_resource_ledger':True}
    w['world_conditions']=conditions
    with pytest.raises(ValueError,match='world-condition binding'):
        audit.physical_proof(cell,s,world=w,seed=31001,years=4,evidence=e)
    initial=states['portable_checkpoint_year_0.json.gz'];binding=initial['portable']['contract']['binding']
    binding['science_config']['world_conditions']=deepcopy(conditions)
    with sqlite3.connect(cell/'replies/responses.sqlite') as db:
        db.execute('UPDATE metadata SET binding=?',(json.dumps(binding),))
    # Metadata is insufficient: the actual actors must match the original blueprint.
    with pytest.raises(ValueError,match='actual native initial resource population'):
        audit.physical_proof(cell,s,world=w,seed=31001,years=4,evidence=e)
    blueprint=build_population_blueprint(5,1,31001,strategy_mix=['balanced'],
        resource_profile='balanced_two_band',base_funding=60.)
    initial['ecosystem_data']['agents']=[{'id':r['researcher_name'],'can_author':True,
        'resources':r['initial_funding'],'initial_funding':r['initial_funding'],
        'resource_band':r['resource_band'],'is_active':True} for r in blueprint]
    initial['project_cost_policy']={'log_resource_ledger':True};initial['resource_ledger']={}
    result=audit.physical_proof(cell,s,world=w,seed=31001,years=4,evidence=e)
    assert result['world_conditions_proof']['actual_initial_total']==300.
    initial['ecosystem_data']['agents'][0]['resources']+=1
    with pytest.raises(ValueError,match='actual native initial resource population'):
        audit.physical_proof(cell,s,world=w,seed=31001,years=4,evidence=e)
