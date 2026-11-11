"""Fake executor only: API, finite budget, raw inputs and cold replay."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from tests.optimization.test_native_code_trace import case
from utopia.optimization.native_component_lab_v1 import NativeComponentLab, ComponentProbePending
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.code_mechanisms import CodeExecution, sha


def fixture(tmp_path, *, maximum_probes=2):
    r,a,c,b=case(tmp_path/'recorded')
    r.execute(a,c)
    bundle=json.loads(r.path.read_text());seen=[]
    def execute(artifact,context):
        seen.append((deepcopy(artifact),deepcopy(context)))
        result={'outputs':{'custom':[]},'state':{}}
        return CodeExecution(result,{'image_id':'qa-image','artifact_sha256':sha(artifact),
            'context_sha256':sha(context),'result_sha256':sha(result),'wall_seconds':.25})
    executor=SimpleNamespace(image_id='qa-image',timeout=15.,execute=execute)
    lab=NativeComponentLab(tmp_path/'lab',records=[bundle],provenance={'kind':'scripted fixture, NOT a native audit'},
        executor=executor,source_commit='a'*40,maximum_probes=maximum_probes)
    return lab,a,c,bundle,seen


def test_literal_changed_source_can_be_tested_without_golden_policy_output_gate(tmp_path):
    lab,a,c,bundle,seen=fixture(tmp_path)
    changed={**a,'source':"def step(context):\n return {'outputs': {'custom': []}, 'state': {'new': True}}"}
    key=next(iter(lab.fixtures));reply=lab.probe(changed,key)
    assert reply['status']=='returned' and reply['new_native_worlds']==reply['new_model_calls']==0
    assert seen==[(changed,c)] and bundle['artifact']==a
    assert lab.replay()[0]['terminal']==reply


def test_bad_literal_fixture_uses_a_slot_and_does_not_guess_an_alternative(tmp_path):
    lab,a,c,bundle,seen=fixture(tmp_path,maximum_probes=1)
    reply=lab.probe(a,'no-such-fixture')
    assert reply['status']=='raised' and not seen and not reply['remote_completion_inferred']
    with pytest.raises(ValueError,match='budget exhausted'):lab.probe(a,next(iter(lab.fixtures)))
    assert len(lab.replay())==1


def test_reported_executor_failure_keeps_source_and_cannot_be_host_repaired(tmp_path):
    lab,a,c,bundle,seen=fixture(tmp_path)
    def execute(artifact,context):raise TypeError("'float' object is not subscriptable")
    lab.executor.execute=execute
    reply=lab.probe(a,next(iter(lab.fixtures)))
    assert reply['status']=='raised' and reply['error_type']=='TypeError'
    assert lab.replay()[0]['intent']['artifact']==a
    assert lab.replay()[0]['intent']['fixture_id']==next(iter(lab.fixtures))


def test_interruption_leaves_a_pending_intent_and_stops_next_probe(tmp_path):
    lab,a,c,bundle,seen=fixture(tmp_path)
    def interrupted(*args):raise KeyboardInterrupt('SCRIPTED interrupted executor')
    lab.executor.execute=interrupted
    with pytest.raises(KeyboardInterrupt):lab.probe(a,next(iter(lab.fixtures)))
    assert lab.replay()[0]['terminal'] is None
    with pytest.raises(ComponentProbePending):lab.probe(a,next(iter(lab.fixtures)))


def test_budget_cannot_reset_on_reload_and_contract_cannot_silently_expand(tmp_path):
    lab,a,c,bundle,seen=fixture(tmp_path,maximum_probes=1);key=next(iter(lab.fixtures));lab.probe(a,key)
    args=dict(records=[bundle],provenance={'kind':'scripted fixture, NOT a native audit'},executor=lab.executor,
        source_commit='a'*40,maximum_probes=1)
    again=NativeComponentLab(lab.directory,**args)
    with pytest.raises(ValueError,match='budget exhausted'):again.probe(a,key)
    with pytest.raises(ValueError,match='budget changed'):
        NativeComponentLab(lab.directory,**{**args,'maximum_probes':2})
    assert len(seen)==1


def test_executor_drift_stops_before_any_consumed_dispatch(tmp_path):
    lab,a,c,bundle,seen=fixture(tmp_path);lab.executor.timeout=60.
    with pytest.raises(ValueError,match='time bound changed'):lab.probe(a,next(iter(lab.fixtures)))
    assert not seen and not lab.replay()


def test_cold_replay_rejects_receipt_corruption_and_unaccounted_results(tmp_path):
    lab,a,c,bundle,seen=fixture(tmp_path);lab.probe(a,next(iter(lab.fixtures)))
    path=lab.directory/'probe-000.result.json';r=checked(json.loads(path.read_text()))
    r['receipt']['context_sha256']='not original'
    path.unlink();save(path,{k:v for k,v in r.items() if k!='content_sha256'})
    with pytest.raises(ValueError,match='receipt differs'):lab.replay()


@pytest.mark.parametrize('budget',[0,9,True,1.5])
def test_probe_budget_is_finite_and_not_coerced(tmp_path,budget):
    with pytest.raises(ValueError,match='finite component budget'):fixture(tmp_path,maximum_probes=budget)


def test_extended_budget_is_explicit_and_cannot_refill_or_relabel_a_legacy_contract(tmp_path):
    lab,a,c,bundle,seen=fixture(tmp_path,maximum_probes=1)
    args=dict(records=[bundle],provenance={'kind':'scripted fixture, NOT a native audit'},executor=lab.executor,
        source_commit='a'*40,maximum_probes=64,budget_scope='declared-sixtyfour-v2')
    with pytest.raises(ValueError,match='budget changed'):NativeComponentLab(lab.directory,**args)
    extended=NativeComponentLab(tmp_path/'extended',**args);key=next(iter(extended.fixtures))
    for _ in range(9):extended.probe(a,key)
    assert len(extended.replay())==len(seen)==9
    assert NativeComponentLab(tmp_path/'extended',**args).replay()==extended.replay()
    with pytest.raises(ValueError,match='finite component budget'):
        NativeComponentLab(tmp_path/'invalid',**{**args,'maximum_probes':65})
