"""Explicit v5 compiler/loss/ABI contracts; no models or native execution."""
import pytest

from tests.optimization.test_native_workflow_submission_v1 import request
from tests.optimization.test_native_workflow_designer_v1 import PROVIDER
from tests.reports.test_native_legacy_choice_pilot_v1 import inputs
from utopia.optimization import native_open_workflow_submission_v1 as ir
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
from utopia.optimization.native_topic_objectives_v1 import objective_specs
from utopia.optimization.native_resource_cost import METRIC
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_workflow_domain_v4 import post_funding_cost_control, SCOPE as OLD_SCOPE
from utopia.optimization.native_workflow_domain_v5 import legacy_topic_workflow_design_space
from utopia.system import SystemSpec
from utopia.system.design_patch import clone
from utopia.system.native_legacy_topic_controls import legacy_topic_control
from utopia.system.native_capability_catalog import native_capability_catalog
from scripts import run_native_topic_free_optimization_v1 as driver


def test_actual_ir_compiler_accepts_explicit_v5_and_keeps_old_v4_rejection(tmp_path):
    req=request(tmp_path/'c')
    core=legacy_topic_control(post_funding_cost_control(SystemSpec.from_dict(req['parent_system'])),candidate_policy='core-only')
    broad=legacy_topic_control(post_funding_cost_control(SystemSpec.from_dict(req['parent_system'])),candidate_policy='core-plus-related')
    req.update(parent_system=broad.to_dict(),design_space_anchor=core.to_dict(),design_space=legacy_topic_workflow_design_space(core))
    target=ir.control_submission(req,PROVIDER)
    definition=ir.compile_submission(req,target,binding_sha256='d'*64,provider=PROVIDER)
    actual=GeneratedMixedDesign(broad,definition,loss_spec=req['loss_spec'],seed=42,single_draw_blackbox=True).base
    assert len(actual.mechanisms)==len(broad.mechanisms)+1
    old=clone(req); old['design_space']['world_law_scope']=OLD_SCOPE
    with pytest.raises(ValueError,match='workflow-v5'):
        ir.bound_systems(old)
    assert req['parent_system']==broad.to_dict()


def test_new_objective_does_not_mutate_old_losses_or_hide_unknown_resource_cost(tmp_path,monkeypatch):
    original,_,_=inputs(tmp_path,monkeypatch); old=clone(original['losses'])
    losses=objective_specs(old)
    assert {k:losses[k] for k in old}==old==original['losses']
    metric='native.common_content_utility_sum'
    measured=[{'run_id':'SCRIPTED','metrics':{metric:{'status':'measured','value':12.},METRIC:{'status':'measured','value':200.}}}]
    assert evaluate_loss(losses['resource-aware-content'],measured)['loss']==8.
    measured[0]['metrics'][METRIC]={'status':'unavailable','value':None}
    assert evaluate_loss(losses['resource-aware-content'],measured)['loss'] is None
    arithmetic=__import__('utopia.optimization.native_objective_view',fromlist=['loss_arithmetic']).loss_arithmetic(losses['resource-aware-content'])
    assert not arithmetic['metrics_without_text_definition']
    assert not arithmetic['extra_eligibility_constraint']


def test_real_original_source_adapter_lists_only_explicit_science_bridges_and_author_changes():
    from utopia.optimization.native_jobs import pinned_revision
    result=driver.native_sources('a5be8d3103854368a4bc6ba4c13eff7552e9dd15',pinned_revision(driver.ROOT))
    assert set(result['explicit_native_adapters'])==set(driver.pilot.ADAPTERS)|set(driver.AUTHOR_ADAPTERS)
    assert not result['global_semantic_equivalence_claimed']
    assert 'utopia/simulation.py' in result['literal_files']


def test_author_catalog_exposes_actual_new_action_and_its_validator_without_policy_recipe():
    from utopia.system.native_legacy_topic_planning import ACTION
    card=native_capability_catalog()['cards']['native.domain.commands.v1']
    assert ACTION in card['action_payload_schemas']
    assert any(ACTION in text and 'no shortest-topic' in text for text in card['semantic_constraints'])
    assert any(s['callable']=='validate_legacy_topic_assignment' for s in card['validators'])


def test_v6_allows_fixed_scientist_response_work_without_silently_widening_v4_or_v5(tmp_path):
    from tests.reports.native_topic_work_fixture_v1 import work_system
    from utopia.optimization.native_institution_workflow_domain_v6 import institution_workflow_design_space
    from utopia.optimization.native_workflow_domain_v5 import require_legacy_topic_workflow_candidate
    req=request(tmp_path/'c')
    anchor=legacy_topic_control(post_funding_cost_control(SystemSpec.from_dict(req['parent_system'])),candidate_policy='core-only')
    changed=work_system(anchor)
    driver.require_candidate(anchor,changed)
    with pytest.raises(ValueError,match='extra research production'):
        require_legacy_topic_workflow_candidate(anchor,changed)
    req.update(parent_system=changed.to_dict(),design_space_anchor=anchor.to_dict(),
               design_space=institution_workflow_design_space(anchor))
    assert ir.bound_systems(req)[1]==changed
