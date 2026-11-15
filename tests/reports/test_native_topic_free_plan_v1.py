"""Finite study/selection contracts with explicitly SCRIPTED upstream evidence."""
from types import SimpleNamespace
import pytest

from scripts import run_native_topic_free_optimization_v1 as driver
from tests.reports.test_native_legacy_choice_pilot_v1 import inputs
from tests.optimization.test_native_post_edit_feedback_v1 import fixture, finish
from utopia.system.design_patch import clone, digest


def plan(tmp_path,monkeypatch):
    original,audit,fixed=inputs(tmp_path/'original',monkeypatch)
    p=driver.pilot.build_plan(original,audit,fixed,source=original['source_commit'],origin={'SCRIPTED':True},
        observer_backend=original['observer_contract']['backend'],original_sources={'original_source':original['source_commit']})
    p['content_sha256']='SCRIPTED-original-plan-not-physical-closure'
    gen,_,_,_=fixture(tmp_path/'bank',[finish()],reference='core-only',extended=True,maximum_probes=64)
    result=driver.build_plan(p,{'content_sha256':'SCRIPTED-not-closure'},source=original['source_commit'],
        origin={'SCRIPTED':True},backend=original['backend'],observer_backend=original['observer_contract']['backend'],
        bank=gen.edit_feedback.bank,evidence={'SCRIPTED':True},sources={'SCRIPTED':True})
    return {**result,'content_sha256':digest(result)},p


def test_finite_whole_system_three_objectives_keep_original_world_and_visible_strong_parents(tmp_path,monkeypatch):
    p,old=plan(tmp_path,monkeypatch)
    assert driver.open_institutions(p)
    assert p['reference_order']==p['optimizer_reference_labels']==list(driver.pilot.LABELS)
    assert p['reference_systems']=={j['condition']:j['system'] for j in old['jobs']}
    assert p['world']['world_conditions']==old['world']['world_conditions']
    assert p['scientist']==old['scientist'] and p['scientist_transport']==old['scientist_transport']
    assert p['losses']['throughput']==old['losses']['throughput']
    assert p['losses']['content-utility']==old['losses']['content-utility']
    assert p['budget']['candidate_slots']==6 and p['budget']['native_worlds_upper_bound']==8
    assert p['budget']['designer_POSTs_upper_bound']==376
    assert not p['budget']['replace_failed_slots']
    assert [(v['objective'],v['generation']) for v in p['schedule']]==[
        ('throughput',0),('content-utility',0),('resource-aware-content',0),
        ('resource-aware-content',1),('content-utility',1),('throughput',1)]
    assert p['additional_measurements']['historical_losses_unchanged']
    assert p['additional_measurements']['optimization_loss_changed']
    assert not p['held_out_evaluation'] and not p['independent_optimizer_replications'] and not p['publication_ready']
    for objective in p['objectives']:
        c=driver.campaign(tmp_path/'campaigns',p,objective)
        req=c._request([],c._validate(),1)
        assert req['loss_spec']==p['losses'][objective]
        assert req['design_space']['world_law_scope']==driver.SCOPE
        assert req['strategy_provenance']['planning_parent_presentation']=='literal-parent-and-observation-v1'
        assert req['strategy_provenance']['post_edit_component_contract']==p['post_edit_contract']


def test_missing_own_results_are_not_replaced_by_visible_reference_or_made_up_loss(tmp_path,monkeypatch):
    p,_=plan(tmp_path,monkeypatch)
    monkeypatch.setattr(driver,'campaign',lambda *a:SimpleNamespace(state={
        'pending':None,'records':[{'observations':[]} for _ in range(2)]}))
    result=driver.selection(tmp_path,p,{})
    assert not result['baseline_fallback']
    assert all(v['loss'] is v['system'] is v['selected_id'] is None
               and v['completed_submissions']==0 for v in result['selected'].values())


def test_unknown_or_historical_scope_cannot_claim_new_open_study(tmp_path,monkeypatch):
    p,_=plan(tmp_path,monkeypatch); p=clone(p)
    p['design_space']['world_law_scope']='fixed-native-effects-workflow-v4'
    with pytest.raises(ValueError,match='prospective free-topic'):
        driver.open_institutions(p)
