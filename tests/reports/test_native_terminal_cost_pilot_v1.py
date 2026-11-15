"""Exact prospective controls and null/authority boundaries, not real-model gains."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from scripts import run_native_terminal_cost_pilot_v1 as driver
from tests.reports.test_native_legacy_choice_pilot_v1 import inputs
from utopia.optimization.native_resource_cost import METRIC
from utopia.system import SystemSpec
from utopia.system.native_terminal_cost_controls_v1 import terminal_consolidation_control


def test_same_world_authority_two_exact_sources_and_three_predeclared_losses(tmp_path, monkeypatch):
    original, audit, fixed = inputs(tmp_path, monkeypatch)
    p = driver.build_plan(original, audit, fixed, source=original['source_commit'], origin={'SCRIPTED': True},
        observer_backend=original['observer_contract']['backend'], original_sources={'original_source': original['source_commit']})
    assert [job['condition'] for job in p['jobs']] == list(driver.LABELS)
    assert p['budget']['native_worlds_upper_bound'] == 2 and p['budget']['designer_generation_POSTs'] == 0
    assert not p['budget']['replace_failed_slots'] and p['budget']['stop_after_technical_failure']
    assert p['world']['world_conditions'] == original['world']['world_conditions']
    assert p['scientist_transport'] == original['scientist_transport']
    for key in ('throughput', 'content-utility'):
        assert p['losses'][key] == original['losses'][key]
    terms = p['losses']['resource-aware-content']['per_run']['terms']
    assert terms[-1] == {'metric_id': METRIC, 'slice_id': None, 'coefficient': 0.1}
    assert not p['objective_comparison']['unpaid_cost_or_attrition_veto']
    assert not p['objective_comparison']['optimization_study']
    assert p['objective_comparison']['hypothesis_is_development_informed']
    left, right = [SystemSpec.from_dict(job['system']) for job in p['jobs']]
    assert terminal_consolidation_control(left, terminal_year=4).to_dict() == right.to_dict()
    a, b = deepcopy(left.to_dict()), deepcopy(right.to_dict())
    for left_node, right_node in zip(a['mechanisms'], b['mechanisms']):
        if left_node['mechanism_id'] == 'developer-liquidity-director':
            right_node['parameters']['code_artifact']['source'] = left_node['parameters']['code_artifact']['source']
    assert a == b
    assert all(not p[k] for k in ('policy_selection', 'automatic_invention', 'held_out_evaluation', 'publication_ready'))


def test_matching_explicit_interval_and_finite_original_finish_chain(monkeypatch):
    from scripts import finish_native_terminal_cost_pilot_v1 as finish
    captured = {}
    monkeypatch.setattr(finish, 'finish', lambda args, **kwargs: captured.update(kwargs))
    finish.run(SimpleNamespace())
    assert captured['plan_schema'] == driver.SCHEMA + '.plan'
    assert captured['audit_module'] == 'scripts.audit_native_terminal_cost_pilot_v1'
    assert captured['writer_command'] == 'scripts.run_native_terminal_cost_pilot_v1 run'
    with pytest.raises(ValueError, match='reused development'):
        driver.interval({}, None, [], 42)
