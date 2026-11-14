"""SCRIPTED record-shape/reconciliation checks, not simulated researcher worlds."""
from types import SimpleNamespace

import pytest

from utopia.funding.accounting import ResourceLedger
from utopia.optimization.native_trajectory_projection_v1 import project_checkpoint
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from tests.optimization.test_native_workflow_submission_v1 import request


def fixture(tmp_path):
    spec = SystemSpec.from_dict(request(tmp_path / 'campaign')['parent_system'])
    actors = {key: SimpleNamespace(id=key, can_author=True, resources=balance,
        is_active=True, get_type=lambda: 'university') for key, balance in [('a', 4.), ('b', 2.)]}
    ledger = ResourceLedger()
    for year in (1, 2):
        ledger.start_year(year, actors)
        for key, delta in ([('a', -1.), ('b', -3.)] if year == 1 else [('a', 2.)]):
            actor = actors[key]; category = 'grant_income' if delta > 0 else 'annual_research_cost'
            event = ledger.prepare(actor, delta, category=category, year=year)
            actor.resources = max(0., actor.resources + delta)
            actor.is_active = actor.resources > 0
            ledger.record(actor, event)
        ledger.close_year(year, actors)
    events = [{'year': year, 'sequence': i, 'event_id': 'SCRIPTED-' + str(i),
        'phase': i, 'event_type': 'native.system.phase_executed',
        'provenance': {'mechanism_id': 'world.open'},
        'payload': {'stage': 'open', 'unselected_prose': 'NOT author data'}}
        for i, year in enumerate((1, 2))]
    assignment = {'actor_id': 'a', 'direction': {'topic': 'SCRIPTED-topic', 'years': 2},
        'project_start_year': 1, 'project_end_year': 2, 'reason': 'not exposed'}
    events.insert(1, {'year': 1, 'sequence': 1, 'event_id': 'SCRIPTED-plan', 'phase': 1,
        'event_type': 'native.domain.project_applied', 'payload': {'assignment': assignment}})
    events[-1]['sequence'] = 2
    state = {'year': 2, 'phase': 5, 'native_system': {'last_year': 2, 'spec': spec.to_dict(), 'events': events},
        'portable': {'contract': {'binding': {'seed': 11, 'cell': spec.fingerprint,
            'science_config': {'source_commit': 'SCRIPTED-source'}},
            'native_system': {'system_fingerprint': spec.fingerprint}}},
        'resource_ledger': ledger.to_dict(), 'paper_tracker': {'papers': [
            {'id': 'p', 'year': 1, 'title': 'UNSELECTED title', 'abstract': 'UNSELECTED abstract',
                'review_history': [{'year': 1, 'decision': 'reject'}, {'year': 2, 'decision': 'accept'}]}]}}
    kw = {'source_commit': 'SCRIPTED-source', 'system_fingerprint': spec.fingerprint,
        'seed': 11, 'years': 2, 'checkpoint_file_sha256': '0' * 64}
    return state, kw


def test_exact_past_balances_are_reconciled_not_final_state_copied_backwards(tmp_path):
    state, kw = fixture(tmp_path); before = digest(state)
    view = project_checkpoint(state, **kw)
    assert digest(state) == before and view['checkpoint_file_sha256'] == kw['checkpoint_file_sha256']
    a1 = view['annual'][0]['authors'][0]; a2 = view['annual'][1]['authors'][0]
    assert (a1['opening_balance'], a1['closing_balance']) == (4., 3.)
    assert (a2['opening_balance'], a2['closing_balance']) == (3., 5.)
    b1 = view['annual'][0]['authors'][1]
    assert b1['closing_balance'] == 0 and b1['closing_active'] is False
    assert b1['annual_research_cost'] == 2 and b1['uncollected_cost'] == 1
    assert view['annual'][0]['new_tracked_contents'] == 1
    assert view['annual'][0]['rejected_decision_occurrences'] == 1
    assert view['annual'][1]['new_tracked_contents'] == 0
    assert view['annual'][1]['accepted_decision_occurrences'] == 1
    assert view['annual'][1]['accepted_distinct_contents_this_year'] == 1
    assert view['annual'][0]['applied_project_commands'][0]['assignment'] == {
        'actor_id': 'a', 'topic': 'SCRIPTED-topic', 'duration': 2, 'start_year': 1, 'end_year': 2}
    assert not view['author_or_measurement_connection_implemented'] and not view['loss_or_eligibility_changed']
    assert view['new_model_calls'] == view['new_code_executions'] == 0
    assert 'UNSELECTED' not in str(view) and 'NOT author data' not in str(view)


@pytest.mark.parametrize('change', ['seed', 'source', 'fingerprint', 'incomplete', 'boolean-year'])
def test_wrong_or_incomplete_checkpoint_binding_is_not_a_trace(tmp_path, change):
    state, kw = fixture(tmp_path)
    if change == 'seed': kw['seed'] = 12
    elif change == 'source': kw['source_commit'] = 'other-source'
    elif change == 'fingerprint': kw['system_fingerprint'] = 'other-policy'
    elif change == 'boolean-year': state['year'] = True
    else: state['phase'] = 0
    with pytest.raises(ValueError): project_checkpoint(state, **kw)


@pytest.mark.parametrize('change', ['missing-year', 'open-row', 'false-cost', 'false-balance', 'false-activity',
    'duplicate-paper', 'event-order', 'unknown-decision'])
def test_missing_or_inconsistent_records_are_not_imputed(tmp_path, change):
    state, kw = fixture(tmp_path)
    row = state['resource_ledger']['years']['1']['a']
    if change == 'missing-year': del state['resource_ledger']['years']['1']
    elif change == 'open-row': row['closing_balance'] = None
    elif change == 'false-cost': row['annual_research_cost'] = 99
    elif change == 'false-balance': row['closing_balance'] = 99
    elif change == 'false-activity': row['closing_active'] = 1
    elif change == 'duplicate-paper': state['paper_tracker']['papers'].append(clone(state['paper_tracker']['papers'][0]))
    elif change == 'event-order': state['native_system']['events'].reverse()
    else: state['paper_tracker']['papers'][0]['review_history'][0]['decision'] = 'invented'
    with pytest.raises(ValueError): project_checkpoint(state, **kw)


def test_decision_occurrences_are_not_silently_replaced_with_unique_contents(tmp_path):
    state, kw = fixture(tmp_path)
    # Tracker-shaped data only: do not infer that this is an allowed native
    # resubmission history. Full physical/domain validity remains separate.
    state['paper_tracker']['papers'][0]['review_history'].append({'year': 2, 'decision': 'accept'})
    row = project_checkpoint(state, **kw)['annual'][1]
    assert row['accepted_decision_occurrences'] == 2
    assert row['accepted_distinct_contents_this_year'] == 1


def test_decoded_native_sets_tuples_and_shared_objects_need_no_json_conversion(tmp_path):
    state, kw = fixture(tmp_path)
    shared = {'native-set': {'x', 'y'}, 'native-tuple': (1, 2)}
    state['unprojected-native-state'] = [shared, shared]
    view = project_checkpoint(state, **kw)
    assert isinstance(shared['native-set'], set) and isinstance(shared['native-tuple'], tuple)
    assert state['unprojected-native-state'][0] is state['unprojected-native-state'][1]
    assert view['checkpoint_file_sha256'] == '0' * 64
    with pytest.raises(ValueError, match='file SHA256'):
        project_checkpoint(state, **{**kw, 'checkpoint_file_sha256': 'not a file digest'})


def test_export_preserves_portable_data_and_rejects_evidence_overwrite(tmp_path):
    from scripts.reports.native_trajectory_projection_v1 import export
    from utopia.runtime.checkpointing import write_portable_checkpoint
    from utopia.utils.data_utils import file_sha256
    state, kw = fixture(tmp_path)
    state['unprojected-set'] = {'native', 'state'}
    root = tmp_path / 'evidence'; root.mkdir()
    checkpoint = root / 'portable_checkpoint_year_2.json.gz'
    write_portable_checkpoint(checkpoint, state)
    before = file_sha256(checkpoint)
    args = SimpleNamespace(checkpoint=checkpoint, evidence_root=root, output=tmp_path / 'export.json',
        source_commit=kw['source_commit'], system_fingerprint=kw['system_fingerprint'], seed=11, years=2)
    result = export(args)
    assert result['original_bytes_unchanged'] and file_sha256(checkpoint) == before
    assert result['projection']['checkpoint_file_sha256'] == before
    assert not result['model_context_fit_proved'] and not result['full_physical_source_audit_claimed']
    with pytest.raises(ValueError, match='fresh output'): export(args)
    args.output = root / 'do-not-write.json'
    with pytest.raises(ValueError, match='outside it'): export(args)
