"""SCRIPTED plan/isolation/selection contracts, not native or model evidence."""
from copy import deepcopy

import pytest

from scripts import run_native_longitudinal_comparison_v1 as driver
from scripts import run_native_longitudinal_fixed_evaluation_v1 as fixed
from tests.reports.test_native_workflow_objective_loop_v1 import setup
from tests.optimization.test_native_post_edit_feedback_v1 import fixture, finish
from utopia.optimization.native_longitudinal_feedback_v1 import VIEW
from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import clone, digest


def sealed(value):
    return {**value, 'content_sha256': digest(value)}


def plan(tmp_path, monkeypatch):
    old, original, audit, _ = setup(tmp_path/'input', monkeypatch)
    generator, _, _, _ = fixture(tmp_path/'SCRIPTED-bank', [finish()],
        reference='R7-original', extended=True, maximum_probes=64)
    monkeypatch.setattr(driver, 'require_scope', lambda value, root, source_commit: value)
    monkeypatch.setattr(driver.staged_author, 'require_bank', lambda b, e, a: clone(b))
    value = driver.build_plan(original, audit, source=old['source_commit'], origin=old['origin'],
        backend=old['backend'], observer_backend=old['observer_contract']['backend'],
        prerequisite=old['prerequisite'], declaration={'base_native_source_commit': 'SCRIPTED-base'},
        component_bank=generator.edit_feedback.bank, component_evidence={'SCRIPTED': 'no actual bank attribution'})
    return sealed(value), old


def test_two_objectives_and_four_isolated_histories_share_fourteen_world_budget(tmp_path, monkeypatch):
    p, old = plan(tmp_path, monkeypatch)
    assert driver.open_institutions(p)
    assert p['objectives'] == ['throughput', 'content-utility']
    assert driver.history_keys(p) == [(a, o) for a in driver.ARMS for o in driver.OBJECTIVES]
    assert p['losses'] == old['losses'] and p['reference_systems'] == old['reference_systems']
    assert p['design_space'] == old['design_space'] and p['initial_system'] == old['initial_system']
    assert p['world']['world_conditions'] == old['world']['world_conditions']
    assert p['budget']['candidate_slots'] == 12 and p['budget']['native_worlds_upper_bound'] == 14
    assert p['budget']['readiness_sessions'] == 13 and p['budget']['designer_POSTs_upper_bound'] == 712
    assert p['budget']['component_probes_upper_bound'] == 768 and not p['budget']['replace_failed_slots']
    assert p['reserved_unused_seeds'] == [676047151]
    assert len(p['schedule']) == 12
    assert [driver.history_key(s) for s in p['schedule'][:4]] == [
        ('scalar', 'throughput'), ('parent-trajectory', 'content-utility'),
        ('scalar', 'content-utility'), ('parent-trajectory', 'throughput')]
    for key in driver.history_keys(p):
        assert [s['generation'] for s in p['schedule'] if driver.history_key(s) == key] == [0, 1, 2]


def test_actual_campaign_constructor_binds_access_without_arm_in_scientist_world(tmp_path, monkeypatch):
    p, _ = plan(tmp_path, monkeypatch)
    campaigns = [driver.campaign(tmp_path/'runs', p, (arm, 'throughput')) for arm in driver.ARMS]
    requests = [c._request([], c._validate(), 1) for c in campaigns]
    assert campaigns[0].path != campaigns[1].path
    assert requests[0]['world_binding'] == requests[1]['world_binding'] == p['world']
    assert requests[0]['loss_spec'] == requests[1]['loss_spec']
    assert [r[VIEW]['access_contract']['mode'] for r in requests] == list(driver.ARMS)
    assert all(not r[VIEW]['active_parent'] and not r[VIEW]['archive_items'] for r in requests)
    assert campaigns[0].binding['seed'] == campaigns[1].binding['seed'] == p['optimizer_seed']


def test_all_null_own_histories_do_not_get_an_unmeasured_reference_fallback(tmp_path, monkeypatch):
    from types import SimpleNamespace
    p, _ = plan(tmp_path, monkeypatch)
    monkeypatch.setattr(driver, 'campaign', lambda *a: SimpleNamespace(state={
        'pending': None, 'records': [{'observations': []} for _ in range(3)]}))
    selected = driver.selection(tmp_path, p, {})
    assert set(selected['selected']) == {'::'.join(k) for k in driver.history_keys(p)}
    assert not selected['baseline_fallback']
    assert all(s['system'] is s['loss'] is s['selected_id'] is None
        and s['all_tied_ids'] == [] and s['completed_submissions'] == 0 for s in selected['selected'].values())


def closed(p):
    worlds, selected = [], {}
    for arm, objective in driver.history_keys(p):
        key = arm+'::'+objective
        pool = []
        for g in range(3):
            identity = key+'-'+str(g)
            pool.append(identity)
            worlds.append({'identity': identity, 'arm': arm, 'objective': objective,
                'role': 'workflow-own-proposal', 'status': 'complete',
                'system': clone(p['initial_system']), 'scores': {'throughput': -1., 'content-utility': -2.}})
        selected[key] = {'arm': arm, 'objective': objective, 'completed_submissions': 3,
            'loss': -1. if objective == 'throughput' else -2., 'all_tied_ids': pool,
            'selected_id': pool[0], 'system': clone(p['initial_system'])}
    selection = sealed({'schema': driver.SCHEMA+'.selection', 'plan_sha256': p['content_sha256'],
        'selected': selected, 'baseline_fallback': False, 'held_out_evaluation': False})
    return sealed({'schema': driver.AUDIT_SCHEMA, 'source_commit': p['source_commit'],
        'plan_sha256': p['content_sha256'], 'source_proof': {'status': 'verified-exact-source-closure'},
        'closure': {'terminal': {'status': 'closed', 'consumed_slots': 12}}, 'selection': selection,
        'worlds': worlds, 'new_model_calls': 0, 'new_code_executions': 0, 'held_out_evaluation': False,
        'SCRIPTED': 'synthetic unit records, not actual source/physical attestation'})


def test_fixed_selection_retains_all_four_chronological_own_minima(tmp_path, monkeypatch):
    p, _ = plan(tmp_path, monkeypatch); a = closed(p)
    assert fixed.fixed_selection(p, a) == a['selection']
    changed = deepcopy(a); changed.pop('content_sha256')
    item = changed['selection']; item.pop('content_sha256')
    row = item['selected']['scalar::throughput']; row['selected_id'] = row['all_tied_ids'][1]
    item['content_sha256'] = digest(item); changed['content_sha256'] = digest(changed)
    with pytest.raises(ValueError, match='chronological-first-tie'):
        fixed.fixed_selection(p, changed)


def test_reserved_seed_literal_sharing_and_no_new_author_in_fixed_plan(tmp_path, monkeypatch):
    p, _ = plan(tmp_path, monkeypatch); a = closed(p)
    usage = sealed({'valid': True, 'errors': [], 'prior_matching_runs': [], 'seeds': p['reserved_unused_seeds']})
    options = dict(source=p['source_commit'], origin={'SCRIPTED': True}, usages=[usage],
        observer_backend=p['observer_contract']['backend'], source_proof={'original_source': p['source_commit']})
    value = fixed.build_plan(p, a, seeds=p['reserved_unused_seeds'], **options)
    assert value['selection_order'] == list(a['selection']['selected'])
    assert len(value['jobs']) == 2 and sorted(len(j['labels']) for j in value['jobs']) == [1, 5]
    assert value['evaluation']['maximum_physical_worlds'] == 6
    assert value['budget']['designer_generation_POSTs'] == 0
    assert not value['claims']['candidate_reselection']
    assert fixed.jobs_for(sealed(value)) == value['jobs']
    with pytest.raises(ValueError, match='reserved unused'):
        fixed.build_plan(p, a, seeds=[72101], **options)
