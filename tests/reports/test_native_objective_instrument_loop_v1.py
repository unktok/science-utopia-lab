"""Finite driver with mocked science/designer, never new scientific evidence."""
from pathlib import Path

import pytest

from scripts import run_native_objective_instrument_loop_v1 as module
from tests.reports.test_native_institution_loop_v1 import plan as operator_plan
from tests.optimization.test_native_post_edit_feedback_v1 import fixture,finish
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_bounded_staged_designer import CompletionUnknown
from utopia.optimization.common_content_observer import ObserverCompletionUnknown
from utopia.system import SystemSpec
from utopia.system.design_patch import clone,digest


def usage():
    body={'valid':True,'errors':[],'prior_matching_runs':[],'seeds':list(module.EVALUATION_SEEDS)}
    return {**body,'content_sha256':digest(body)}


def plan(tmp_path,monkeypatch):
    gen,unused,request,calls=fixture(tmp_path/'fixture',[finish()],extended=True,
        reference='resource-30-connected',maximum_probes=64)
    bank=gen.edit_feedback.bank;operator=operator_plan()
    operator['scientist']['image_id']=operator['designer']['image_id']=gen.image_id
    real=module.read
    def read(path):
        if Path(path)==module.ROOT/module.BANK_MANIFEST:
            return {'bank_file_sha256':'SCRIPTED-bank-file','bank_content_sha256':bank['content_sha256']}
        return real(path)
    monkeypatch.setattr(module,'read',read)
    support=tmp_path/'support';support.mkdir()
    module.save(support/'plan.json',{'bank_file_sha256':'SCRIPTED-bank-file'})
    module.save(support/'summary.json',{'status':'closed','observations':[{'original_result_matches':True}]*12})
    p=module.build_plan(operator,source='c'*40,backend=operator['backend'],
        observer_backend={**{k:operator['scientist'][k] for k in ('model','model_digest')},'ollama_version':'SCRIPTED'},
        bank=bank,bank_file_hash='SCRIPTED-bank-file',support={'directory':str(support),
            'plan_file_sha256':module.file_sha256(support/'plan.json'),'summary_file_sha256':module.file_sha256(support/'summary.json')},
        seed_usage=[usage()])
    return {**p,'content_sha256':digest(p)}


def setup(tmp_path,monkeypatch):
    p=plan(tmp_path,monkeypatch)
    monkeypatch.setattr(module,'require_environment',lambda:None)
    monkeypatch.setattr(module,'require_plan',lambda root:p)
    module.save(tmp_path/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    contexts=[]
    def context(pairs,**kw):
        contexts.append(clone(pairs));body={'SCRIPTED':'mocked developer references; not native receipts'}
        return {**body,'content_sha256':digest(body)}
    monkeypatch.setattr(module,'build_context',context)
    # Real campaign journal/slot logic; science and reference input validation
    # are mocked only in this driver unit test, covered natively elsewhere.
    def campaign(root,p,objective,context):
        return NativeAdaptiveDesignCampaign(root/'search'/objective/'campaign',
            initial_system=SystemSpec.from_dict(p['initial_system']),loss_spec=p['losses'][objective],
            seeds=[module.SEED],world_binding=p['world'],strategies=p['strategies'],mode='blackbox',seed=p['optimizer_seed'],
            design_space=p['design_space'])
    monkeypatch.setattr(module,'campaign',campaign)
    monkeypatch.setattr(module,'factory_for',lambda *a:lambda *a:pytest.fail('no native execution for a generation null'))
    return p,contexts


def test_plan_has_explicit_new_criterion_common_authority_probe_budget_and_finite_worlds(tmp_path,monkeypatch):
    p=plan(tmp_path,monkeypatch)
    assert list(p['losses'])==['throughput','content-utility']
    assert p['losses']['content-utility']['per_run']['terms']==[{
        'metric_id':'native.common_content_utility_sum','slice_id':None,'coefficient':-1.}]
    assert p['post_edit_contract']['maximum_probe_attempts']==64
    assert p['post_edit_contract']['fixture_reference']=='resource-30-connected'
    assert p['world']['world_conditions']['initial_funding']==30
    assert p['world']['measurement_adapter_contract']==p['observer_contract']
    assert p['budget']['development_native_worlds_upper_bound']==13 and p['evaluation']['native_worlds_upper_bound']==21
    assert len(p['reference_order'])==5 and len(p['schedule'])==8 and not p['budget']['replace_failed_slots']
    assert [s['objective'] for s in p['schedule']]==['throughput','content-utility','content-utility','throughput']*2


def test_prior_technical_stop_is_retained_but_never_becomes_a_development_observation(tmp_path,monkeypatch):
    p=plan(tmp_path,monkeypatch);old=tmp_path/'prior-stopped'
    module.save(old/'plan.json',{'schema':module.SCHEMA+'.plan','source_commit':'b'*40})
    module.save(old/'terminal.json',{'status':'stopped','error_type':'ValueError','error':'SCRIPTED cold guard mismatch'})
    p['prior_technical_stops']=[{'run':str(old),'source_commit':'b'*40,
        'plan_file_sha256':module.file_sha256(old/'plan.json'),'terminal_file_sha256':module.file_sha256(old/'terminal.json'),
        'error_type':'ValueError','error':'SCRIPTED cold guard mismatch'}]
    kwargs=dict(source=p['source_commit'],backend=p['backend'],observer_backend=p['observer_contract']['backend'],
        bank=p['component_bank'],bank_file_hash=p['component_bank_file_sha256'],support=p['component_support'],seed_usage=[usage()])
    rebuilt=module.build_plan(p,**kwargs)
    assert rebuilt['prior_technical_stops']==p['prior_technical_stops']
    assert rebuilt['prior_evidence_reused_as_development_observations'] is False
    assert len(rebuilt['reference_order'])==5 and len(rebuilt['schedule'])==8
    p['prior_technical_stops'][0]['error']='rewritten failure'
    with pytest.raises(ValueError,match='prior stopped'):module.build_plan(p,**kwargs)


def test_actual_saved_plan_reconstructs_and_rejects_a_declared_budget_that_does_not_reach_worker(tmp_path,monkeypatch):
    p=plan(tmp_path,monkeypatch);out=tmp_path/'prepared';out.mkdir()
    module.save(out/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    module.save(out/'evaluation-seed-usage-00.json',{k:v for k,v in usage().items() if k!='content_sha256'})
    monkeypatch.setattr(module,'pinned_revision',lambda root:'c'*40)
    assert module.require_plan(out)==p
    p['post_edit_contract']['maximum_probe_attempts']=8
    (out/'plan.json').unlink();module.save(out/'plan.json',{k:v for k,v in p.items() if k!='content_sha256'})
    with pytest.raises(ValueError,match='reconstruction differs'):module.require_plan(out)


def test_all_eight_generation_nulls_close_without_native_or_reference_fallback_and_preserve_public_observer_audit(tmp_path,monkeypatch):
    p,contexts=setup(tmp_path,monkeypatch);events=[];requests=[]
    monkeypatch.setattr(module,'observe',lambda root,p,label,observer:events.append('reference') or {'SCRIPTED':label})
    def readiness(root,p,**kw):
        events.append('readiness');requests.append(clone(kw['request']));return tmp_path/'SCRIPTED-cert'
    monkeypatch.setattr(module,'readiness',readiness)
    def execute(*a,**kw):
        assert kw['seconds']==1800 and kw['post_edit_bank']==p['component_bank']
        events.append('proposal');return {'generation_failure':'SCRIPTED known non-submission'}
    monkeypatch.setattr(module,'execute',execute);module.run(tmp_path)
    assert events[:5]==['reference']*5 and len(contexts)==1 and len(contexts[0])==5
    assert events.count('proposal')==events.count('readiness')==8
    assert [len(r['history']) for r in requests]==[0,0,1,1,2,2,3,3]
    selected=module.read(tmp_path/'selection.json')
    assert all(v['system'] is None and v['loss'] is None for v in selected['selected'].values())
    assert not selected['baseline_fallback'] and module.read(tmp_path/'terminal.json')['status']=='closed'
    assert module.read(tmp_path/'observer-audit.json')['dispatch_intents']==0
    with pytest.raises(ValueError,match='no redispatch'):module.run(tmp_path)


@pytest.mark.parametrize('failure',['reference','critic-unknown','designer-unknown'])
def test_known_failed_reference_or_unknown_completion_stops_later_dispatch(tmp_path,monkeypatch,failure):
    setup(tmp_path,monkeypatch);events=[]
    def observe(*a):
        events.append('reference')
        if failure=='reference':raise ValueError('SCRIPTED failed reference')
        if failure=='critic-unknown':raise ObserverCompletionUnknown('SCRIPTED unknown critic')
        return {'SCRIPTED':'reference'}
    monkeypatch.setattr(module,'observe',observe)
    monkeypatch.setattr(module,'readiness',lambda *a,**k:events.append('readiness') or tmp_path/'SCRIPTED-cert')
    def execute(*a,**kw):events.append('proposal');raise CompletionUnknown('SCRIPTED unknown designer')
    monkeypatch.setattr(module,'execute',execute)
    with pytest.raises((ValueError,ObserverCompletionUnknown,CompletionUnknown)):module.run(tmp_path)
    assert module.read(tmp_path/'terminal.json')['status']=='stopped' and not (tmp_path/'selection.json').exists()
    assert events==(['reference']*5+['readiness','proposal'] if failure=='designer-unknown' else ['reference'])
