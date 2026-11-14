"""Pure readout tests: no model, Docker, fixture simulation or TeX execution."""
from types import SimpleNamespace

import pytest

from scripts.reports.native_institution_effect_trace_v1 import workflow_boundary
from utopia.funding.accounting import ResourceLedger
from utopia.system.design_patch import clone


def event(stage, phase, *, year=1):
    return {'event_id': 'SCRIPTED-' + stage, 'event_type': 'native.system.phase_executed',
        'year': year, 'phase': phase, 'provenance': {'mechanism_id': 'world.' + stage},
        'payload': {'stage': stage, 'observation_sha256': 'a' * 64}}


def actor(identity, resources, active=True):
    return SimpleNamespace(id=identity, can_author=True, resources=resources,
        is_active=active, get_type=lambda: 'SCRIPTED-author')


def test_literal_order_and_real_ledger_keep_zero_inactive_author_and_actual_charges():
    actors = {'a': actor('a', 30.), 'b': actor('b', 0., False)}
    ledger = ResourceLedger(); ledger.start_year(1, actors)
    rows = ledger.close_year(1, actors)
    events = [event('open', 0), event('funding', 160), event('costs', 163), event('close', 180)]
    before = clone(events)
    result = workflow_boundary(events, 1, ledger.reconcile(1, actors, require_closed=True), ledger.categories)
    assert events == before
    assert [v['event']['payload']['stage'] for v in result['native_phase_witnesses_in_original_order']] == [
        'open', 'funding', 'costs', 'close']
    assert result['all_author_opening_resources'] == result['all_author_closing_resources'] == 30
    assert result['all_author_opening_active'] == result['all_author_closing_active'] == 1
    # A scheduled costs phase is not evidence that a nominal fee was collected.
    assert result['all_author_cashflows']['annual_research_cost'] == 0
    assert len(rows) == 2
    for key in ('funding_stage_summary_used_as_end_year_state',
        'phase_resource_vectors_recovered_from_observation_hashes', 'within_phase_attrition_timestamp_measured'):
        assert result[key] is False


def test_other_years_are_not_mixed_and_original_ordinals_are_not_renumbered():
    events = [event('open', 0, year=1), event('open', 0, year=2), event('close', 180, year=2)]
    result = workflow_boundary(events, 2, [], ())
    assert [v['original_event_ordinal'] for v in result['native_phase_witnesses_in_original_order']] == [1, 2]


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'phase-bool', 'phase-string', 'short-hash',
    'invalid-hash', 'missing-stage', 'nonstring-stage', 'bad-owner'])
def test_missing_or_corrupted_witness_is_not_reconstructed_from_a_schedule(change):
    events = [event('costs', 163)]
    if change == 'missing':
        events = []
    elif change == 'duplicate':
        events += [event('costs', 164)]
    elif change in ('phase-bool', 'phase-string'):
        events[0]['phase'] = True if change == 'phase-bool' else '163'
    elif change in ('short-hash', 'invalid-hash'):
        events[0]['payload']['observation_sha256'] = 'a' if change == 'short-hash' else 'g' * 64
    elif change in ('missing-stage', 'nonstring-stage'):
        events[0]['payload']['stage'] = '' if change == 'missing-stage' else 163
    else:
        events[0]['provenance']['mechanism_id'] = None
    with pytest.raises(ValueError):
        workflow_boundary(events, 1, [], ())


def test_nonzero_realized_fee_and_grant_are_not_confused_with_conserving_transfers():
    actors = {'a': actor('a', 30.)}
    ledger = ResourceLedger(); ledger.start_year(1, actors)
    # Exercise the ledger's own prepare/record contract, not a synthetic total.
    intent = ledger.prepare(actors['a'], -10., category='annual_research_cost', year=1)
    actors['a'].resources = 20.
    ledger.record(actors['a'], intent)
    ledger.close_year(1, actors)
    result = workflow_boundary([event('costs', 163)], 1,
        ledger.reconcile(1, actors, require_closed=True), ledger.categories)
    assert result['all_author_cashflows']['annual_research_cost'] == 10
    assert result['all_author_cashflows']['grant_income'] == 0
    assert result['all_author_opening_resources'] - 10 == result['all_author_closing_resources']
