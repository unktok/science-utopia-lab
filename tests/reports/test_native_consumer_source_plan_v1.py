"""Finite matched allocation, information isolation and real-source boundaries."""
from types import SimpleNamespace
import subprocess

import pytest

from scripts import run_native_consumer_source_comparison_v1 as driver
from tests.reports.test_native_legacy_choice_pilot_v1 import inputs
from tests.optimization.test_native_post_edit_feedback_v1 import fixture, finish
from utopia.optimization.native_consumer_evidence_v1 import OPTION
from utopia.system.design_patch import clone,digest


def plan(tmp_path,monkeypatch):
    original,audit,fixed=inputs(tmp_path/'original',monkeypatch)
    preceding=driver.topic.build_plan(original,audit,fixed,source=original['source_commit'],origin={'SCRIPTED':True},
        observer_backend=original['observer_contract']['backend'],original_sources={'original_source':original['source_commit']})
    preceding['content_sha256']='SCRIPTED upstream physical attribution is tested separately'
    gen,_,_,_=fixture(tmp_path/'bank',[finish()],reference='core-only',extended=True,maximum_probes=64)
    source=driver.pinned_revision(driver.ROOT)
    p=driver.build_plan(preceding,{'content_sha256':'SCRIPTED'},source=source,origin={'SCRIPTED':True},
        backend=original['backend'],observer_backend=original['observer_contract']['backend'],
        bank=gen.edit_feedback.bank,evidence={'SCRIPTED':True},sources={'SCRIPTED':True})
    return {**p,'content_sha256':digest(p)},preceding


def test_eight_scheduled_slots_keep_native_world_and_source_only_information_difference(tmp_path,monkeypatch):
    p,old=plan(tmp_path,monkeypatch)
    assert driver.open_institutions(p)
    assert len(p['schedule'])==8 and p['budget']['native_worlds_upper_bound']==11
    assert p['budget']['readiness_sessions']==10 and p['budget']['designer_POSTs_upper_bound']==528
    assert p['budget']['component_probes_upper_bound']==512 and not p['budget']['replace_failed_slots']
    assert p['world']['world_conditions']==old['world']['world_conditions']
    assert p['scientist']==old['scientist'] and p['scientist_transport']==old['scientist_transport']
    assert p['losses']['content-utility']==old['losses']['content-utility']
    assert p['reference_order']==['core-only','core-plus-related','terminal-consolidation']
    assert p['optimizer_reference_labels']==['core-only','core-plus-related']
    left,right=[clone(p['strategies_by_arm'][arm]) for arm in driver.ARMS]
    assert right['local-workflow-designer'].pop(OPTION)==p['consumer_source_evidence']
    assert left==right
    assert [(s['arm'],s['objective']) for s in p['schedule'][:4]]==[
        ('interface-only','content-utility'),('literal-consumers','resource-aware-content'),
        ('interface-only','resource-aware-content'),('literal-consumers','content-utility')]
    assert [(s['arm'],s['objective']) for s in p['schedule'][4:]]==list(reversed([
        (s['arm'],s['objective']) for s in p['schedule'][:4]]))
    for key in driver.history_keys(p):
        c=driver.campaign(tmp_path/'campaigns',p,key)
        req=c._request([],c._validate(),1)
        assert (OPTION in req['strategy_provenance'])==(key[0]=='literal-consumers')
        assert req['world_binding']==p['world'] and req['loss_spec']==p['losses'][key[1]]


def test_unavailable_own_selection_is_not_filled_by_reference(tmp_path,monkeypatch):
    p,_=plan(tmp_path,monkeypatch)
    monkeypatch.setattr(driver,'campaign',lambda *a:SimpleNamespace(state={
        'pending':None,'records':[{'observations':[]} for _ in range(2)]}))
    result=driver.selection(tmp_path,p,{})
    assert not result['baseline_fallback'] and len(result['selected'])==4
    assert all(r['loss'] is r['system'] is r['selected_id'] is None for r in result['selected'].values())


def test_both_initial_readiness_jobs_have_separate_exact_roots_and_no_worlds(tmp_path,monkeypatch):
    p,_=plan(tmp_path,monkeypatch); jobs=driver.initial_readiness_jobs(p)
    assert len(jobs)==2 and len({str(path) for _,path in jobs})==2
    for key,_ in jobs:
        c=driver.campaign(tmp_path,p,key,prototype=True)
        assert not c.state['records'] and c.state['pending'] is None


def test_actual_native_source_guard_registers_current_feedback_and_preserves_original_consumers(tmp_path):
    source=driver.pinned_revision(driver.ROOT)
    archive=subprocess.check_output(['git','archive',source,'utopia',
        'scripts/run_native_objective_instrument_loop_v1.py','scripts/native_benchmark_physical.py',
        'scripts/native_observer_physical_v1.py'],cwd=driver.ROOT)
    subprocess.run(['tar','-xf','-','-C',str(tmp_path)],input=archive,check=True)
    original='a5be8d3103854368a4bc6ba4c13eff7552e9dd15'
    bound=driver.native_sources(original,source,source_root=tmp_path)
    assert 'utopia/simulation.py' in bound['literal_files']
    assert 'utopia/agents/base_agent.py' in bound['literal_files']
    assert 'utopia/optimization/native_post_edit_feedback_v1.py' in bound['explicit_native_adapters']
    target=tmp_path/'utopia/agents/base_agent.py'
    target.write_text(target.read_text()+'\n# SCRIPTED forbidden native-source mutation\n')
    with pytest.raises(ValueError,match='original scientist/effect source differs'):
        driver.native_sources(original,source,source_root=tmp_path)
