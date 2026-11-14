"""Explicit plan/factory boundaries with a named SCRIPTED bank, no inference."""
import pytest

from scripts import run_native_workflow_objective_loop_v1 as driver
from tests.reports.test_native_workflow_objective_loop_v1 import setup
from tests.optimization.test_native_post_edit_feedback_v1 import fixture, finish
from utopia.system.design_patch import clone


def plan_options(p, original, audit, sources):
    return dict(source=p['source_commit'], origin=p['origin'], backend=p['backend'],
        observer_backend=p['observer_contract']['backend'], prerequisite=p['prerequisite'], sources=sources)


def test_staged_plan_declares_multicall_budget_and_exact_generated_request_contract(tmp_path, monkeypatch):
    old, original, audit, sources = setup(tmp_path/'input', monkeypatch)
    generator, _, _, _ = fixture(tmp_path/'SCRIPTED-fixture', [finish()],
        reference='R7-original', extended=True, maximum_probes=64)
    bank = generator.edit_feedback.bank
    seen = []
    monkeypatch.setattr(driver.staged_author,'require_bank',
        lambda b,e,a: seen.append((clone(b),clone(e),clone(a))) or clone(b))
    evidence = {'SCRIPTED':'this is not original native input attribution'}
    p = driver.build_plan(original, audit, **plan_options(old,original,audit,sources),
        designer_mode=driver.staged_author.MODE, component_bank=bank, component_evidence=evidence)
    assert driver.open_institutions(p) and p['protocol'] == driver.staged_author.PROTOCOL
    assert len(seen)==1 and seen[0][2] == old['initial_system']
    for field in ('losses','reference_systems','reference_order','initial_system','design_space','schedule'):
        assert p[field] == old[field]
    assert p['world']['world_conditions'] == old['world']['world_conditions']
    assert p['budget']['native_worlds_upper_bound'] == 8 and p['budget']['candidate_slots'] == 6
    assert p['budget']['designer_POSTs_upper_bound'] == 376
    assert p['budget']['component_probes_upper_bound'] == 384
    assert not p['budget']['replace_failed_slots']
    c = driver.campaign(tmp_path/'campaign-root',p,'throughput',prototype=True)
    request = c._request([],c._validate(),1)
    assert request['strategy_provenance']['post_edit_component_contract'] == p['post_edit_contract']
    assert p['post_edit_contract']['maximum_probe_attempts']==64
    assert p['post_edit_contract']['fixture_reference']=='R7-original'
    assert not p['post_edit_contract']['veto_on_test_failure'] and not p['post_edit_contract']['source_repair']
    author = driver.designer_for(tmp_path/'author',p,tmp_path/'root')
    assert isinstance(author,driver.staged_author.StagedWorkflowDesigner)
    assert author.feedback.contract == p['post_edit_contract']


def test_new_profile_requires_original_bank_and_old_profiles_do_not_acquire_tests(tmp_path,monkeypatch):
    p, original, audit, sources = setup(tmp_path,monkeypatch)
    options = plan_options(p,original,audit,sources)
    with pytest.raises(ValueError,match='explicit original component'):
        driver.build_plan(original,audit,**options,designer_mode=driver.staged_author.MODE)
    for mode in (None,driver.OPEN_IR_MODE,driver.FEEDBACK_MODE):
        with pytest.raises(ValueError,match='explicit staged workflow'):
            driver.build_plan(original,audit,**options,designer_mode=mode,component_bank={'SCRIPTED':True})


def test_scope_cannot_claim_staged_mode_with_historical_protocol(tmp_path,monkeypatch):
    p, _, _, _ = setup(tmp_path,monkeypatch)
    p.update(designer_mode=driver.staged_author.MODE,authoring_scope=driver.OPEN_SCOPE,protocol=driver.OPEN_PROTOCOL)
    with pytest.raises(ValueError,match='explicit open-institution'):
        driver.open_institutions(p)
