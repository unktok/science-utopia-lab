"""Exact finite-plan contracts, not real-model feasibility."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_native_legacy_topic_pilot_v1 as driver
from tests.reports.test_native_legacy_choice_pilot_v1 import inputs
from utopia.optimization.native_resource_cost import METRIC
from utopia.system import SystemSpec
from utopia.system.native_legacy_topic_controls import legacy_topic_control


def test_exact_two_controls_same_world_transport_losses_and_explicit_resource_diagnostic(tmp_path, monkeypatch):
    original, audit, fixed = inputs(tmp_path, monkeypatch)
    p = driver.build_plan(original, audit, fixed, source=original['source_commit'], origin={'SCRIPTED': True},
        observer_backend=original['observer_contract']['backend'], original_sources={'original_source': original['source_commit']})
    assert [j['condition'] for j in p['jobs']] == list(driver.LABELS)
    assert p['budget']['native_worlds_upper_bound'] == 2 and not p['budget']['replace_failed_slots']
    assert p['losses'] == original['losses'] and p['scientist_transport'] == original['scientist_transport']
    assert p['world']['world_conditions'] == original['world']['world_conditions']
    assert p['additional_measurements']['metrics'][0] == METRIC
    assert not p['additional_measurements']['optimization_loss_changed']
    assert p['design_space']['world_law_scope'] == 'fixed-native-effects-legacy-topic-workflow-v5'
    anchor = SystemSpec.from_dict(original['reference_systems']['post-funding-cost'])
    assert [j['system'] for j in p['jobs']] == [legacy_topic_control(anchor, candidate_policy=k).to_dict() for k in driver.LABELS]
    assert not p['automatic_invention'] and not p['held_out_evaluation'] and not p['publication_ready']


def test_exact_source_adapter_binds_native_science_without_a_global_equivalence_claim():
    r = driver.native_sources('a5be8d3103854368a4bc6ba4c13eff7552e9dd15')
    assert set(r['explicit_native_adapters']) == set(driver.ADAPTERS)
    assert all(v['source_commit'] == driver.ADAPTER_SOURCE for v in r['explicit_native_adapters'].values())
    assert not r['global_semantic_equivalence_claimed']
    assert 'utopia/simulation.py' in r['literal_files']
    assert 'utopia/system/native_open_domain.py' not in r['literal_files']
    assert 'utopia/agents/research_direction.py' in r['literal_files']


def test_new_interval_and_finish_use_new_scope_and_original_finite_chain(monkeypatch):
    from scripts import finish_native_legacy_topic_pilot_v1 as finish
    captured = {}
    def invoke(args, **kwargs): captured.update(kwargs)
    monkeypatch.setattr(finish, 'finish', invoke); finish.run(SimpleNamespace())
    assert captured['plan_schema'] == driver.SCHEMA + '.plan'
    assert captured['writer_command'] == 'scripts.run_native_legacy_topic_pilot_v1 run'
    with pytest.raises(ValueError, match='reused development'):
        driver.interval({}, None, [], 42)
