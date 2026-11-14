"""Light explicit scope/plan/report/handoff checks, no native/model execution."""
import pytest

from scripts import run_native_workflow_objective_loop_v1 as driver
from scripts import run_native_workflow_fixed_evaluation_v1 as fixed
from scripts.reports.native_workflow_objective_loop_v1 import graph_change, summarize
from tests.reports.test_native_workflow_objective_loop_v1 import setup
from tests.reports.test_native_workflow_objective_report_v1 import fixture
from tests.reports.test_native_workflow_fixed_evaluation_v1 import evidence
from tests.reports.test_native_planning_objective_loop_v1 import seal
from tests.reports.native_open_workflow_fixture_v1 import authored_program
from tests.optimization.test_native_workflow_designer_v1 import PROVIDER
from utopia.optimization.native_open_workflow_submission_v1 import compile_submission
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
from utopia.system import SystemSpec
from utopia.system.design_patch import clone


def opened(p):
    p['designer_mode'] = driver.OPEN_IR_MODE; p['authoring_scope'] = driver.OPEN_SCOPE
    p['protocol'] = driver.OPEN_PROTOCOL
    p['optimizer_reference_labels'] = ['R7-original']
    return p


def test_new_scope_preserves_native_world_losses_controls_budget_and_default_strictness(tmp_path, monkeypatch):
    old, original, audit, sources = setup(tmp_path, monkeypatch)
    p = driver.build_plan(original, audit, source=old['source_commit'], origin=old['origin'],
        backend=old['backend'], observer_backend=old['observer_contract']['backend'],
        prerequisite=old['prerequisite'], sources=sources, designer_mode=driver.OPEN_IR_MODE)
    assert driver.open_institutions(p) and not driver.open_institutions(old)
    for key in ('losses', 'reference_systems', 'initial_system', 'design_space', 'budget', 'schedule'):
        assert p[key] == old[key]
    assert p['world']['world_conditions'] == old['world']['world_conditions']
    assert p['author_profile_protocol']['path'] == p['author_settings']['open_protocol']
    assert p['optimizer_reference_labels'] == ['R7-original']
    assert p['comparison_only_reference_labels'] == ['post-funding-cost']
    p['authoring_scope'] = old['authoring_scope']
    with pytest.raises(ValueError, match='explicit open-institution'): driver.open_institutions(p)


def test_comparison_control_is_measured_but_not_in_open_optimizer_feedback(tmp_path, monkeypatch):
    p, _, _, _ = setup(tmp_path, monkeypatch); opened(p)
    pairs = [{'suggestion': {'suggestion_id': 'workflow-reference-' + label.lower()},
        'observation': {'SCRIPTED': label}} for label in p['reference_order']]
    seen = []
    monkeypatch.setattr(driver, 'build_context', lambda rows, **kwargs: seen.extend(rows) or {'SCRIPTED': rows})
    driver.reference_context(p, pairs)
    assert seen == pairs[:1]
    assert pairs[1]['observation'] == {'SCRIPTED': 'post-funding-cost'}
    p['optimizer_reference_labels'].append('post-funding-cost')
    with pytest.raises(ValueError, match='exposes only'): driver.reference_context(p, pairs)


def test_source_node_and_protocol_changes_are_explicit_and_legacy_readout_rejects_them():
    p, _, _ = fixture(); before = p['initial_system']; after = clone(before)
    node = clone(after['mechanisms'][0]); node['mechanism_id'] = 'new-office'
    node.update(implementation='code.python.v1', parameters={'code_artifact': {'source': 'def step(context): pass'}})
    after['mechanisms'] = [node]
    after['schedules'] = [{'mechanism_id': 'new-office', 'phase': 3, 'trigger': 'annual'}]
    after['artifact_types'] = [{'artifact_type_id': 'new-protocol'}]
    with pytest.raises(ValueError, match='changes source'): graph_change(before, after)
    diff = graph_change(before, after, allow_institution_edits=True)
    assert set(diff['added_nodes']) == {'new-office'} and set(diff['removed_nodes']) == {'a'}
    assert set(diff['source_edits']) == {'new-office'} and not diff['source_parameters_nodes_unchanged']
    assert 'artifact_types' in diff['changed_system_fields']
    assert diff['added_schedules']['new-office']['phase'] == 3


def test_open_report_keeps_every_slot_null_and_source_change_without_reselecting():
    p, a, records = fixture(); opened(p)
    for candidate in (records['throughput', 0]['observations'][0]['candidate'],
            records['throughput', 0]['draws'][0]['suggestion']['candidate'], a['worlds'][2]['system']):
        candidate['mechanisms'][0]['parameters']['literal'] = 99
    result = summarize(p, a, records)
    assert result['authoring_scope'] == driver.OPEN_SCOPE
    assert len(result['slots']) == 6 and result['slots'][1]['loss'] is None
    assert result['slots'][0]['graph_from_parent']['changed_mechanisms']['a']['changed_fields'] == ['parameters']
    assert result['selection'] == a['selection']
    assert result['loss_paths']['throughput'][0]['best_known_loss'] == -10
    assert not result['references'][1]['optimizer_visible']


def test_authored_fixture_replaces_real_planner_source_and_rewires_native_consumer(tmp_path):
    from tests.optimization.test_native_workflow_submission_v1 import request
    req = request(tmp_path / 'campaign'); literal = authored_program(req)
    definition = compile_submission(req, literal, binding_sha256='c' * 64, provider=PROVIDER)
    base = GeneratedMixedDesign(SystemSpec.from_dict(req['parent_system']), definition,
        loss_spec=req['loss_spec'], seed=42, single_draw_blackbox=True).base
    node = next(n for n in base.mechanisms if n.mechanism_id == 'authored-long-horizon-office')
    assert 'direction = max(' in node.parameters['code_artifact']['source']
    assert any(e.source_mechanism == node.mechanism_id and e.target_mechanism == 'developer-catalog-effects'
        for e in base.connections)
    assert base.initial_state == req['parent_system']['initial_state']


def test_open_frozen_selection_handoff_keeps_code_but_old_scope_still_rejects(tmp_path, monkeypatch):
    original, audit, p, usages, sources = evidence(tmp_path, monkeypatch)
    # An actual valid native candidate with changed code/new mechanism wiring.
    from tests.optimization.test_native_workflow_submission_v1 import request
    req = request(tmp_path / 'input-native')
    req.update(parent_system=clone(original['initial_system']),
        design_space_anchor=clone(original['initial_system']), design_space=clone(original['design_space']))
    image = next(n['parameters']['runtime_image_id'] for n in original['initial_system']['mechanisms']
        if n['implementation'] == 'code.python.v1')
    literal = authored_program(req)
    definition = compile_submission(req, literal, binding_sha256='c' * 64,
        provider={**PROVIDER, 'image_id': image})
    candidate = GeneratedMixedDesign(SystemSpec.from_dict(req['parent_system']), definition,
        loss_spec=req['loss_spec'], seed=42, single_draw_blackbox=True).base.to_dict()
    # Keep the fixed evaluator's original seed/state; only the institution changes.
    candidate['initial_state'] = clone(original['initial_system']['initial_state'])
    for w in audit['worlds']: w['system'] = clone(candidate)
    audit['selection']['selected']['throughput']['system'] = clone(candidate)
    seal(audit['selection']); seal(audit)
    kwargs = dict(source=p['source_commit'], origin={}, usages=usages, seeds=p['evaluation']['seeds'],
        observer_backend=p['observer_contract']['backend'], source_proof=sources)
    with pytest.raises(ValueError): fixed.build_plan(original, audit, **kwargs)
    opened(original); seal(original); audit['plan_sha256'] = original['content_sha256']
    audit['selection']['plan_sha256'] = original['content_sha256']; seal(audit['selection']); seal(audit)
    result = fixed.build_plan(original, audit, **kwargs)
    assert result['origin_authoring_scope'] == driver.OPEN_SCOPE
    assert result['protocol'] == fixed.OPEN_PROTOCOL
    chosen = next(j for j in result['jobs'] if 'selected:throughput' in j['labels'])
    assert any(n['mechanism_id'] == 'authored-long-horizon-office' for n in chosen['system']['mechanisms'])
    assert result['fixed_selection'] == audit['selection'] and result['budget']['designer_generation_POSTs'] == 0
