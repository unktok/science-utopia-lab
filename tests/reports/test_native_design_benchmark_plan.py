"""Pure fixed-budget/seed/policy QA; no backend or scholar calls."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest

from scripts.native_design_benchmark_plan import build_plan,policy_identity,evaluation_design
from tests.optimization.test_native_designer_roles_v38 import BINDING,designer_binding
from utopia.system.design_patch import digest


def plan():
    designer=designer_binding()
    return build_plan(source='a'*40,scientist=BINDING,designer=designer,
        runtime_seed={'python_hash_seed_environment':'42','python_hash_probe':123},
        backend={'model':designer['model'],'model_digest':designer['model_digest'],'ollama_version':'SCRIPTED'})


def test_fixed_five_methods_two_objectives_three_runs_and_exact_budgets():
    p=plan();assert p['content_sha256']==digest({k:v for k,v in p.items() if k!='content_sha256'})
    assert len(p['campaign_bindings'])==3 and len(p['reference_systems'])==9
    assert sum(len(s) for s in p['schedules'].values())==120
    for run,bindings in p['campaign_bindings'].items():
        assert len(bindings)==10
        for name,b in bindings.items():
            assert b['seeds']==[42] and b['world']==p['world']
            assert b['initial_system']==p['initial_system']
            assert 'evaluation' not in b['world']
            assert all(str(s) not in json.dumps(b) for s in p['evaluation']['seeds'])
        for arm in bindings:
            assert [s['generation'] for s in p['schedules'][run] if s['arm']==arm]==[0,1,2,3]
    assert p['budget']['maximum_total_worlds_including_evaluation']==129+114
    assert p['budget']['maximum_author_POSTs']==96*16
    assert p['budget']['maximum_calibration_POSTs']==120


def test_evaluation_changes_only_environment_seed_and_preserves_original_policy():
    p=plan();original=deepcopy(p['initial_system'])
    projected=evaluation_design(original,31001)
    assert projected.initial_state['seed']==31001 and p['initial_system']==original
    assert policy_identity(original)==policy_identity(projected.to_dict())
    assert digest(original)!=digest(projected.to_dict())
    with pytest.raises(ValueError):evaluation_design(original,701)


def test_http_budget_records_all_actual_attempts_and_never_dispatches_past_limit(tmp_path):
    from utopia.optimization.native_factory import record_native_http,NativeInferenceBudgetExceeded
    calls=[]
    def create(**payload):calls.append(payload);return 'SCRIPTED reply'
    model=SimpleNamespace(client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    simulation=SimpleNamespace(native_system=SimpleNamespace(_frame={'year':1}))
    path=tmp_path/'wire.jsonl'
    record_native_http(model,simulation,path,maximum_attempts=2)
    assert model.client.chat.completions.create(messages=['one'])=='SCRIPTED reply'
    model.client.chat.completions.create(messages=['two'])
    with pytest.raises(NativeInferenceBudgetExceeded):model.client.chat.completions.create(messages=['three'])
    assert len(calls)==len(path.read_text().splitlines())==2 and model.http_budget_exhausted is True
