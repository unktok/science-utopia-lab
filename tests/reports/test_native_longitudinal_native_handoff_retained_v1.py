"""Retained SCRIPTED software boundary; never promote it to research evidence."""
import hashlib
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT/'research/results/native-longitudinal-native-handoff-software-v1.json'


def test_original_failures_and_literal_continuation_are_preserved():
    p = checked(json.loads(PATH.read_text()))
    assert p['source_commit'] == '85520c4dac89c33a9c5f41bc7407737a7af83500'
    assert [r['actual_terminal_exit_code'] for r in p['original_attempts']] == [1, 1, 0]
    assert [int(r['tests']['failures']) for r in p['original_attempts']] == [1, 1, 0]
    h = p['continuation_harness']
    assert hashlib.sha256((ROOT/h['retained_path']).read_bytes()).hexdigest() == h['file_sha256']
    v = p['verification']
    assert v['original_development_pytest_failed']
    assert not v['original_development_reopened_or_refilled']


def test_full_history_and_frozen_readouts_do_not_impute_missing_loss():
    p = checked(json.loads(PATH.read_text())); v = p['verification']
    assert (v['own_slots'], v['native_development_worlds'], v['complete_development_worlds']) == (12, 13, 12)
    assert v['known_invalid_generation_nulls_preserved'] == v['native_timeout_nulls_preserved'] == 1
    assert v['all_observed_annual_checkpoints_including_partial_failed_world'] == 50
    assert (v['actual_bounded_sessions_replayed'], v['readiness_POSTs'], v['proposal_POSTs']) == (25, 372, 71)
    assert p['fixed_completed_worlds'] == v['fixed_native_worlds'] == 3
    assert (p['fixed_logical_rows'], p['fixed_reference_paired_rows']) == (6, 8)
    assert p['fixed_objective_choice_contrasts'] == p['fixed_information_access_contrasts'] == 2
    assert len(v['paired_readout_files']) == 8
    assert set(p['full_proposal_frame_examples']) == {'scalar', 'parent-trajectory'}
    for rows in p['full_proposal_frame_examples'].values():
        assert len(rows) == 6 and max(r['history_records'] for r in rows) == 2
        assert all(0 < r['largest_wire_utf8_bytes'] <= 200000 for r in rows)


def test_software_closure_never_claims_real_capacity_gain_or_readiness():
    p = checked(json.loads(PATH.read_text())); v = p['verification']
    for key in ('real_backend_token_capacity_proved', 'real_backend_readiness_proved',
                'scientific_comparison_dispatched', 'scientific_gain_claimed', 'publication_ready'):
        assert p[key] is False
    assert p['new_real_model_calls'] == v['new_model_calls'] == 0
    assert v['fixed_fixture_seed'] == 72101 and not v['scientific_reserved_seed_used']
