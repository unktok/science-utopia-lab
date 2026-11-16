"""Mixed-method plan/scalar contracts; no new native scientific results."""
from copy import deepcopy
from types import SimpleNamespace
import pytest

from scripts import run_native_priority_method_comparison_v1 as driver
from tests.reports.test_native_topic_free_plan_v1 import plan as free_plan
from utopia.optimization.blackbox import Observation
from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest
from utopia.system import SystemSpec


def plan(tmp_path, monkeypatch):
    old, original = free_plan(tmp_path, monkeypatch)
    p = driver.build_plan(original, {'content_sha256': 'SCRIPTED-upstream'},
        source=old['source_commit'], origin={'SCRIPTED': True}, backend=old['backend'],
        observer_backend=old['observer_contract']['backend'], bank=old['component_bank'],
        evidence=old['component_evidence'], sources=old['original_native_sources'])
    return {**p, 'content_sha256': digest(p)}, original


def test_three_methods_shared_strong_visible_parents_and_literal_world_losses(tmp_path, monkeypatch):
    p, old = plan(tmp_path, monkeypatch)
    assert driver.open_institutions(p)
    assert p['methods'] == list(driver.METHODS) and p['objectives'] == list(driver.OBJECTIVES)
    assert p['reference_order'] == [*driver.PARENTS, 'literal-related']
    assert p['optimizer_reference_labels'] == list(driver.PARENTS)
    assert p['scientist'] == old['scientist'] and p['world']['world_conditions'] == old['world']['world_conditions']
    for name, spec in old['losses'].items(): assert p['losses'][name] == spec
    assert p['replication_seeds'] == [79011, 79019]
    assert p['budget']['candidate_slots'] == 24 and p['budget']['native_worlds_upper_bound'] == 27
    assert p['budget']['designer_POSTs_upper_bound'] == 488
    assert p['budget']['observer_POSTs_upper_bound'] == p['observer_contract']['maximum_posts'] == 6000
    assert len(driver.history_keys(p)) == 4 and len(driver.all_history_keys(p)) == 12
    assert len(p['schedule']) == len({tuple(v.values()) for v in p['schedule']}) == 24
    assert [driver.history_key(s) for s in p['schedule'][12:]] == [driver.history_key(s) for s in p['schedule'][:12]][::-1]
    assert not p['budget']['replace_failed_slots'] and not p['held_out_evaluation'] and not p['publication_ready']
    assert p['comparison']['known_terminal_rule_visible']
    for key in driver.history_keys(p):
        c = driver.campaign(tmp_path / 'campaigns', p, key)
        request = c._request([], c._validate(), 1)
        assert request['loss_spec'] == p['losses'][key[2]]
        assert request['design_space']['world_law_scope'] == driver.free.SCOPE


def scalar_context(p, monkeypatch):
    rows = []
    for i, name in enumerate(driver.PARENTS):
        candidate = p['reference_systems'][name]
        rows.append({'suggestion': {'suggestion_id': 'workflow-reference-' + name, 'candidate': candidate},
                     'observation': Observation('SCRIPTED-ref-' + name, 'workflow-reference-' + name,
                        candidate, 'complete', -20. if i else -10.).to_dict()})
    monkeypatch.setattr(driver, 'objective_view', lambda context, loss: {'observations': deepcopy(rows)})
    return {'SCRIPTED': 'synthetic scalar fixture, no measured native reference'}, rows


def test_numeric_methods_share_exact_parent_and_first_sample_without_coercing_other_fields(tmp_path, monkeypatch):
    p, _ = plan(tmp_path, monkeypatch); context, rows = scalar_context(p, monkeypatch)
    a = driver.numeric_optimizer(p, context, (driver.METHODS[0], 0, driver.OBJECTIVES[0]))
    b = driver.numeric_optimizer(p, context, (driver.METHODS[1], 0, driver.OBJECTIVES[0]))
    assert a.state_dict()['space_binding']['anchor'] == rows[1]['suggestion']['candidate']
    first_a, first_b = a.ask()[0], b.ask()[0]
    assert first_a.to_dict() == first_b.to_dict()
    for opt, suggestion in ((a, first_a), (b, first_b)):
        opt.tell([Observation('SCRIPTED-own0', suggestion.suggestion_id, suggestion.candidate, 'failed', None)])
    assert a.ask()[0].phase == 'initial' and b.ask()[0].phase == 'adaptive'


def test_unmeasured_parent_program_is_rejected_instead_of_becoming_a_warm_start(tmp_path, monkeypatch):
    p, _ = plan(tmp_path, monkeypatch); context, rows = scalar_context(p, monkeypatch)
    rows[1]['suggestion']['candidate']['metadata']['SCRIPTED-incompatible'] = True
    monkeypatch.setattr(driver, 'objective_view', lambda context, loss: {'observations': rows})
    with pytest.raises(ValueError, match='exact parent'):
        driver.numeric_optimizer(p, context, (driver.METHODS[0], 0, driver.OBJECTIVES[0]))


def test_own_only_selection_keeps_nulls_and_earliest_ties_separate_from_parent(tmp_path, monkeypatch):
    p, _ = plan(tmp_path, monkeypatch); context, rows = scalar_context(p, monkeypatch)
    candidate = rows[1]['suggestion']['candidate']
    monkeypatch.setattr(driver, 'campaign', lambda *a, **kw: SimpleNamespace(state={'pending': None,
        'records': [{'observations': []}, {'observations': []}]}))
    for key in driver.all_history_keys(p):
        if key[0] == driver.METHODS[2]: continue
        for g in range(2):
            status = 'failed' if key[0] == driver.METHODS[0] else 'complete'
            o = Observation('SCRIPTED-own' + str(g), 'SCRIPTED-s' + str(g), candidate,
                status, None if status == 'failed' else -1.).to_dict()
            driver.save(driver.history_directory(tmp_path, key) / ('generation-' + str(g)) / 'observation.json', o)
    r = driver.selection(tmp_path, p, context)
    for rep in ('0', '1'):
        for objective in driver.OBJECTIVES:
            assert r['selected'][driver.METHODS[0]][rep][objective]['selected_id'] is None
            assert r['selected'][driver.METHODS[2]][rep][objective]['selected_id'] is None
            a = r['selected'][driver.METHODS[1]][rep][objective]
            assert a['selected_id'] == 'SCRIPTED-s0' and len(a['all_tied_ids']) == 2
            assert a['reference_loss'] == -20. and a['loss'] == -1.
    assert not r['baseline_fallback']
