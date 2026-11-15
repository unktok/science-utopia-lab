"""Scripted accounting examples; not real-model scientific replications."""
from copy import deepcopy
import hashlib
from types import SimpleNamespace

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.funding.accounting import ResourceLedger
from utopia.optimization.native_resource_cost import (
    INSTRUMENT, METRIC, UNCOLLECTED_METRIC, from_states, measure, measure_from_checkpoints,
)
from utopia.system.design_patch import digest


def states(*, empty=False):
    """Actual ledger class, scripted actors/deltas, including a later entrant."""
    ledger = ResourceLedger()
    ledger.enable_native_transfers()
    actors = {} if empty else {
        'SCRIPTED-a': SimpleNamespace(id='SCRIPTED-a', can_author=True, resources=30.,
                                     is_active=True, get_type=lambda: 'SCRIPTED'),
        'SCRIPTED-b': SimpleNamespace(id='SCRIPTED-b', can_author=True, resources=4.,
                                     is_active=True, get_type=lambda: 'SCRIPTED'),
    }

    def snapshot(year):
        return {'year': year, 'phase': 0 if year == 0 else 5,
            'portable': {'contract': {'binding': {'SCRIPTED': 'same'},
                                     'simulation': {'num_years': 2}}},
            'native_system': {'spec': {'SCRIPTED': 'fixed'}, 'last_year': year},
            'resource_ledger': ledger.to_dict(),
            'ecosystem_data': {'agents': [{k: a.__dict__[k] for k in
                ('id', 'can_author', 'resources', 'is_active')} for a in actors.values()]}}

    def debit(aid, delta, category, year):
        actor = actors[aid]
        event = ledger.prepare(actor, delta, category=category, year=year)
        actor.resources = max(0., actor.resources + delta)
        ledger.record(actor, event)

    result = [snapshot(0)]
    for year in (1, 2):
        if year == 2 and not empty:
            actors['SCRIPTED-new'] = SimpleNamespace(id='SCRIPTED-new', can_author=True,
                resources=7., is_active=False, get_type=lambda: 'SCRIPTED')
        ledger.start_year(year, actors)
        if not empty:
            if year == 1:
                debit('SCRIPTED-a', 20, 'grant_income', year)
                debit('SCRIPTED-a', -5, 'institution_transfer_out', year)
                debit('SCRIPTED-b', 5, 'institution_transfer_in', year)
                debit('SCRIPTED-a', -3, 'production_submission_cost', year)
                debit('SCRIPTED-a', -2, 'resubmission_cost', year)
                debit('SCRIPTED-a', -1, 'funding_application_cost', year)
            for aid in actors:
                debit(aid, -10, 'annual_research_cost', year)
        ledger.close_year(year, actors)
        result.append(snapshot(year))
    return result


def test_actual_collections_not_requested_cost_income_transfers_or_active_count():
    source = states(); before = digest(source)
    result = from_states(source)
    assert digest(source) == before
    assert result['value'] == 42  # year1:25, year2:17
    assert result['uncollected_value'] == 14  # year1:1, year2:10+3
    assert result['annual'][0]['costs_by_category'] == {
        'annual_research_cost': 19., 'production_submission_cost': 3.,
        'resubmission_cost': 2., 'funding_application_cost': 1.}
    assert [r['collected_activity_cost'] for r in result['annual']] == [25, 17]
    entrant = result['annual'][1]['reconciled_authors'][2]
    assert entrant['researcher_id'] == 'SCRIPTED-new' and not entrant['closing_active']
    assert entrant['annual_research_cost'] == 7
    assert result['new_model_calls'] == result['new_code_executions'] == 0


def test_measured_zero_requires_complete_known_empty_ledgers():
    assert from_states(states(empty=True))['value'] == 0
    source = states(empty=True); del source[1]['resource_ledger']
    with pytest.raises(ValueError, match='unknown zero'): from_states(source)


def test_uncollected_transfer_is_not_activity_cost_or_its_uncollected_diagnostic():
    source = states()
    # The native ledger represents requested/collected transfers separately.
    # Alter only the requested amount, preserving its actual conserving legs.
    for state in source[1:]:
        event = next(e for e in state['resource_ledger']['transactions']
                     if e['category'] == 'institution_transfer_out')
        event['requested_delta'] = -50
        event['uncollected_cost'] = 45
    # Such a request exceeds native clipping and is not an executable event.
    with pytest.raises(ValueError, match='native resource transition'): from_states(source)
    # A valid zero-balance transfer request can have uncollected transfer cost;
    # it still does not belong to the activity-cost vocabulary.
    source = states()
    for year in (1, 2):
        raw = source[year]['resource_ledger']
        e = {'event_id': 'SCRIPTED-uncollected-transfer', 'year': 1,
            'researcher_id': 'SCRIPTED-b', 'category': 'institution_transfer_out',
            'requested_delta': -5., 'delta': 0., 'balance_before': 0.,
            'balance_after': 0., 'uncollected_cost': 5., 'active_after': True}
        # Append after b's annual debit, before any later-year transactions.
        i = next((i for i, v in enumerate(raw['transactions']) if v['year'] > 1), len(raw['transactions']))
        raw['transactions'].insert(i, e)
        raw['years']['1']['SCRIPTED-b']['uncollected_cost'] += 5
    assert from_states(source)['uncollected_value'] == 14


@pytest.mark.parametrize('change', ['partial', 'missing-year', 'wrong-phase', 'changed-contract',
    'changed-spec', 'unknown-resource', 'boolean-resource', 'unknown-activity', 'duplicate-actor',
    'unaccounted-author', 'unclosed', 'residual', 'deleted-event', 'edited-past-year',
    'nan-event', 'bool-event', 'wrong-sign', 'false-uncollected', 'future-event', 'initial-history',
    'between-year-credit'])
def test_unknown_or_inconsistent_evidence_is_not_a_numeric_loss(change):
    source = states()
    if change == 'partial': source.pop()
    if change == 'missing-year': source.pop(1)
    if change == 'wrong-phase': source[1]['phase'] = 4
    if change == 'changed-contract': source[1]['portable']['contract']['binding'] = {'SCRIPTED': 'other'}
    if change == 'changed-spec': source[1]['native_system']['spec'] = {'SCRIPTED': 'other'}
    if change == 'unknown-resource': source[1]['ecosystem_data']['agents'][0]['resources'] = None
    if change == 'boolean-resource': source[1]['ecosystem_data']['agents'][0]['resources'] = True
    if change == 'unknown-activity': source[1]['ecosystem_data']['agents'][0]['is_active'] = None
    if change == 'duplicate-actor': source[1]['ecosystem_data']['agents'] *= 2
    if change == 'unaccounted-author': source[1]['ecosystem_data']['agents'].append(
        {'id': 'SCRIPTED-unaccounted', 'can_author': True, 'is_active': True, 'resources': 0})
    if change == 'unclosed': source[1]['resource_ledger']['years']['1']['SCRIPTED-a']['closing_balance'] = None
    if change == 'residual': source[1]['ecosystem_data']['agents'][0]['resources'] += 1
    if change == 'deleted-event': source[2]['resource_ledger']['transactions'].pop(0)
    if change == 'edited-past-year': source[2]['resource_ledger']['years']['1']['SCRIPTED-a']['opening_balance'] += 1
    if change == 'nan-event': source[1]['resource_ledger']['transactions'][0]['delta'] = float('nan')
    if change == 'bool-event': source[1]['resource_ledger']['transactions'][0]['delta'] = True
    if change == 'wrong-sign': source[1]['resource_ledger']['transactions'][0]['requested_delta'] = -20
    if change == 'false-uncollected': source[1]['resource_ledger']['transactions'][0]['uncollected_cost'] = 7
    if change == 'future-event': source[1]['resource_ledger']['transactions'][0]['year'] = 2
    if change == 'initial-history': source[0]['resource_ledger']['entry_years'] = {'SCRIPTED-old': 0}
    if change == 'between-year-credit':
        raw = source[2]['resource_ledger']
        row = raw['years']['2']['SCRIPTED-a']
        row['opening_balance'] += 1; row['closing_balance'] += 1
        source[2]['ecosystem_data']['agents'][0]['resources'] += 1
        for event in raw['transactions']:
            if event['year'] == 2 and event['researcher_id'] == 'SCRIPTED-a':
                event['balance_before'] += 1; event['balance_after'] += 1
    with pytest.raises(ValueError): from_states(source)


def test_existing_loss_evaluator_can_use_cost_without_new_hidden_constraints():
    from utopia.optimization.loss import evaluate_loss
    loss = {'schema': 'scienceutopia.loss-spec.v1', 'id': 'SCRIPTED-cost', 'version': '1',
        'status': 'SCRIPTED-not-adopted', 'direction': 'minimize', 'optimization_seed_role': 'development',
        'per_run': {'intercept': 0., 'terms': [
            {'metric_id': 'native.accepted_decisions', 'coefficient': -1., 'slice_id': None},
            {'metric_id': METRIC, 'coefficient': .25, 'slice_id': None}]},
        'across_seeds': {'aggregation': 'mean_plus_population_sd',
                         'dispersion_weight': 0., 'minimum_valid_runs': 1}}
    base = {'run_id': 'SCRIPTED-cost', 'metrics': {
        'native.accepted_decisions': {'status': 'measured', 'value': 20}}}
    assert evaluate_loss(loss, [base])['loss'] is None
    base['metrics'][METRIC] = {'status': 'measured', 'value': 200}
    assert evaluate_loss(loss, [base])['loss'] == 30


def test_actual_native_checkpoint_live_and_cold_paths_are_additive(tmp_path, fixed_corpus):
    from pathlib import Path
    from tests.runtime.test_portable_checkpoint_integration import SmallRealSimulation, FakeHTTPModel
    from utopia.optimization.native_world import measure_native_world
    from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
    root = tmp_path / 'SCRIPTED-native-resource'
    sim = SmallRealSimulation(root, FakeHTTPModel(root, []), ledger=True)
    sim.native_system = NativeScienceKernel(legacy_world_system())
    try:
        sim.run()
        base = measure_native_world(sim, run_id='SCRIPTED-actual-native-states')
        before = digest(base)
        paths = [Path(sim.output_dir) / f'portable_checkpoint_year_{y}.json.gz'
                 for y in range(sim.num_years + 1)]
        result = measure(sim, base)
        assert result == measure_from_checkpoints(base, paths)
        assert digest(base) == before
        assert all(result[k] == v for k, v in base.items() if k != 'metrics')
        assert all(result['metrics'][k] == v for k, v in base['metrics'].items())
        assert result['metrics'][METRIC]['value'] > 0
        assert result['metrics'][UNCOLLECTED_METRIC]['value'] >= 0
        assert len(result[INSTRUMENT]['checkpoint_sha256s']) == 7
        assert result[INSTRUMENT]['checkpoint_sha256s'] == {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        with pytest.raises(ValueError, match='nonoverwriting'): measure(sim, result)
        wrong = deepcopy(base); wrong['system_fingerprint'] = 'SCRIPTED-other'
        with pytest.raises(ValueError, match='literal native system'): measure_from_checkpoints(wrong, paths)
        with pytest.raises(ValueError, match='distinct'): measure_from_checkpoints(base, [paths[0]] * 2)
    finally:
        sim.llm.response_cache.close()


def test_new_metric_reaches_the_public_native_loss_observation_boundary(tmp_path, fixed_corpus):
    from tests.runtime.test_portable_checkpoint_integration import SmallRealSimulation, FakeHTTPModel, seed
    from tests.optimization.test_native_world import loss_spec
    from utopia.optimization.blackbox import Suggestion
    from utopia.optimization.native_world import evaluate_native_suggestion
    from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system

    def factory(spec, run_seed, run_id):
        seed()
        root = tmp_path / run_id
        sim = SmallRealSimulation(root, FakeHTTPModel(root, []), ledger=True)
        sim.native_system = NativeScienceKernel(spec)
        return sim

    system = legacy_world_system()
    result = evaluate_native_suggestion(Suggestion('SCRIPTED-resource-public', system.to_dict(), 0, 'initial'),
        seeds=[42], simulation_factory=factory, loss_spec=loss_spec(METRIC, .25), measurement_adapter=measure)
    assert result.status == 'complete'
    measurement = result.metadata['measurements'][0]
    assert result.loss == .25 * measurement['metrics'][METRIC]['value']
    assert measurement['metrics']['native.accepted_decisions']['status'] == 'measured'
    assert not result.metadata['technical_failures']
