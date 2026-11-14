"""Pure prospective graph contrasts, without native worlds, Docker or LLMs."""
from dataclasses import replace

import pytest

from scripts.native_workflow_timing_contrasts_v1 import corner, describe
from tests.reports.test_native_workflow_objective_loop_v1 import setup
from utopia.optimization.native_workflow_domain_v4 import require_workflow_candidate, execution_order, post_funding_cost_control
from utopia.system import SystemSpec


def anchor(tmp_path, monkeypatch):
    p, _, _, _ = setup(tmp_path, monkeypatch)
    return SystemSpec.from_dict(p['initial_system'])


def test_four_legal_corners_preserve_every_nonstructural_field_and_exact_endpoints(tmp_path, monkeypatch):
    original = anchor(tmp_path, monkeypatch); before = original.to_dict(); rows = describe(original)
    assert original.to_dict() == before
    assert rows[0]['system'] == before and rows[-1]['system'] == post_funding_cost_control(original).to_dict()
    assert len({SystemSpec.from_dict(r['system']).fingerprint for r in rows}) == 4
    for row in rows:
        spec = SystemSpec.from_dict(row['system'])
        assert require_workflow_candidate(original, spec, structure_only=True)
        assert {k: v for k, v in row['system'].items() if k not in ('schedules', 'connections')} == {
            k: v for k, v in before.items() if k not in ('schedules', 'connections')}
        order = execution_order(spec); grant = order.index('world.funding')
        assert (order.index('developer-liquidity-effects') > grant) == row['late_liquidity']
        assert (order.index('world.costs') > grant) == row['late_cost']
        if row['late_liquidity'] and row['late_cost']:
            assert order.index('developer-liquidity-effects') < order.index('world.costs')
        assert row['selection_feature_snapshot_source'] == ('world.submission' if row['late_cost'] else 'world.costs')


@pytest.mark.parametrize('kwargs', [{'late_liquidity': 1, 'late_cost': False},
    {'late_liquidity': False, 'late_cost': 'late'}, {'late_liquidity': None, 'late_cost': True}])
def test_factors_are_not_coerced_from_ambiguous_values(tmp_path, monkeypatch, kwargs):
    with pytest.raises(ValueError, match='boolean'): corner(anchor(tmp_path, monkeypatch), **kwargs)


@pytest.mark.parametrize('change', ['missing-edge', 'duplicate-edge', 'already-late', 'no-room'])
def test_no_edge_repair_implicit_rescheduling_or_inferred_anchor(tmp_path, monkeypatch, change):
    spec = anchor(tmp_path, monkeypatch)
    if change in ('missing-edge', 'duplicate-edge'):
        edge = next(e for e in spec.connections if e.source_mechanism == 'world.submission'
            and e.target_mechanism == 'developer-liquidity-director')
        spec = replace(spec, connections=tuple(e for e in spec.connections if e != edge) if change == 'missing-edge'
            else spec.connections + (edge,))
    elif change == 'already-late': spec = post_funding_cost_control(spec)
    else: spec = replace(spec, schedules=tuple(replace(s, phase=162) if s.mechanism_id == 'world.communication' else s for s in spec.schedules))
    with pytest.raises(ValueError): corner(spec, late_liquidity=True, late_cost=True)
