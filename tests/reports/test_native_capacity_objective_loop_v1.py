"""Finite production controller with explicitly scripted science/designer IO."""
from pathlib import Path

import pytest

from scripts import run_native_capacity_objective_loop_v1 as module
from tests.reports.test_native_institution_loop_v1 import plan as operator_plan
from tests.optimization.test_native_post_edit_feedback_v1 import fixture, finish
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_bounded_staged_designer import CompletionUnknown
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest


def plan(tmp_path, monkeypatch, *, image_override=None):
    gen,_,_,_ = fixture(tmp_path/'fixture',[finish()],extended=True,
        reference='resource-30-connected',maximum_probes=64)
    bank=clone(gen.edit_feedback.bank); operator=operator_plan()
    image=gen.image_id if image_override is None else image_override
    if image_override is not None:
        # This is a newly constructed SCRIPTED bank, not historical evidence.
        # Rebuild its own bundle/origin identities for the actual test executor.
        changes={}
        for row in bank['records']:
            old=row.pop('bundle_sha256');row['receipt']['image_id']=image
            row['bundle_sha256']=digest(row);changes[old]=row['bundle_sha256']
        for origin in bank['origins']:origin['bundle_sha256']=changes[origin['bundle_sha256']]
        bank.pop('content_sha256');bank['content_sha256']=digest(bank)
    operator['scientist']['image_id']=operator['designer']['image_id']=image
    real=module.read
    def read(path):
        if Path(path)==module.ROOT/module.BANK_MANIFEST:
            return {'bank_file_sha256':'SCRIPTED-bank','bank_content_sha256':bank['content_sha256']}
        return real(path)
    monkeypatch.setattr(module,'read',read)
    p=module.build_plan(operator,source='d'*40,backend=operator['backend'],bank=bank,
        bank_file_hash='SCRIPTED-bank',support={'SCRIPTED':'historical diagnostic'},
        preceding={'SCRIPTED':'closed upstream; not observations'})
    return {**p,'content_sha256':digest(p)}


def test_exact_finite_objectives_capacities_and_same_authority_references(tmp_path,monkeypatch):
    p=plan(tmp_path,monkeypatch)
    assert list(p['losses'])==['throughput','founder-activity']
    assert p['losses']['founder-activity']['per_run']['terms']==[{
        'metric_id':module.METRIC,'slice_id':None,'coefficient':-1.}]
    assert p['world']['world_conditions']['papers_per_project']==2
    assert p['world']['world_conditions']['funding_budget_slots_frac']==.2
    assert len(p['reference_order'])==5 and p['budget']['development_native_worlds_upper_bound']==9
    assert p['budget']['critic_POSTs']==0 and p['budget']['readiness_sessions']==5
    assert [s['objective'] for s in p['schedule']]==['throughput','founder-activity','founder-activity','throughput']
    assert p['generations']==2 and not p['budget']['replace_failed_slots']
    assert not p['measurement_contract']['adoption_constraint']


def setup(tmp_path,monkeypatch):
    p=plan(tmp_path,monkeypatch)
    monkeypatch.setattr(module,'require_environment',lambda:None)
    monkeypatch.setattr(module,'require_plan',lambda root:p)
    contexts=[]
    def context(pairs,**kw):
        contexts.append(clone(pairs)); body={'SCRIPTED':'reference context'}
        return {**body,'content_sha256':digest(body)}
    monkeypatch.setattr(module,'build_context',context)
    def campaign(root,p,objective,context=None,*,prototype=False):
        directory=root/'initial-readiness/campaign' if prototype else root/'search'/objective/'campaign'
        return NativeAdaptiveDesignCampaign(directory,initial_system=SystemSpec.from_dict(p['initial_system']),
            loss_spec=p['losses'][objective],seeds=[module.SEED],world_binding=p['world'],
            strategies=p['strategies'],mode='blackbox',seed=p['optimizer_seed'],design_space=p['design_space'])
    monkeypatch.setattr(module,'campaign',campaign)
    monkeypatch.setattr(module,'factory_for',lambda *a:lambda *a:pytest.fail('null cannot dispatch native science'))
    return p,contexts


def test_all_terminal_generation_nulls_keep_five_gates_four_slots_and_no_fallback(tmp_path,monkeypatch):
    p,contexts=setup(tmp_path,monkeypatch); events=[]; requests=[]
    monkeypatch.setattr(module,'observe',lambda root,p,label:events.append('reference') or {'SCRIPTED':label})
    def readiness(root,p,**kw):
        events.append('readiness'); requests.append(clone(kw['request'])); return tmp_path/'SCRIPTED-cert'
    monkeypatch.setattr(module,'readiness',readiness)
    def execute(*a,**kw):
        assert kw['seconds']==1800 and kw['post_edit_bank']==p['component_bank']
        events.append('proposal'); return {'generation_failure':'SCRIPTED terminal invalid proposal'}
    monkeypatch.setattr(module,'execute',execute); module.run(tmp_path)
    assert events[:6]==['readiness']+['reference']*5 and len(contexts)==1
    assert events.count('proposal')==4 and events.count('readiness')==5
    assert [len(r['history']) for r in requests]==[0,0,0,1,1]
    selected=module.read(tmp_path/'selection.json')
    assert all(v['system'] is None and v['loss'] is None for v in selected['selected'].values())
    assert not selected['baseline_fallback'] and module.read(tmp_path/'terminal.json')['status']=='closed'
    assert not (tmp_path/'observer').exists()
    with pytest.raises(ValueError,match='no redispatch'):module.run(tmp_path)


@pytest.mark.parametrize('failure',['initial-readiness','reference','proposal-readiness','designer-unknown'])
def test_failures_stop_without_repair_or_later_dispatch(tmp_path,monkeypatch,failure):
    setup(tmp_path,monkeypatch); events=[]
    def readiness(root,p,**kw):
        events.append('readiness')
        if failure=='initial-readiness' or failure=='proposal-readiness' and len(events)>1:
            raise ValueError('SCRIPTED failed calibration')
        return tmp_path/'SCRIPTED-cert'
    def observe(*a):
        events.append('reference')
        if failure=='reference':raise ValueError('SCRIPTED failed reference')
        return {'SCRIPTED':'reference'}
    def execute(*a,**kw):
        events.append('proposal'); raise CompletionUnknown('SCRIPTED unknown completion')
    monkeypatch.setattr(module,'readiness',readiness); monkeypatch.setattr(module,'observe',observe)
    monkeypatch.setattr(module,'execute',execute)
    with pytest.raises((ValueError,CompletionUnknown)):module.run(tmp_path)
    assert module.read(tmp_path/'terminal.json')['status']=='stopped'
    assert not (tmp_path/'selection.json').exists() and events.count('proposal')<=1


def test_missing_parent_closure_never_becomes_permission_to_launch(tmp_path):
    with pytest.raises(ValueError,match='closed preceding'):
        module.preceding_descriptor(tmp_path/'evaluation',tmp_path/'controls')
