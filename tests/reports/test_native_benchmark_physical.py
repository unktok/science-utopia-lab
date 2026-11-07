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
