"""Retained actual evidence consistency, not another execution or model test."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data/native-corrected-author-assay-closed-v1'


def evidence():
    return checked(json.loads((ROOT / 'research/results/native-corrected-author-assay-closed-v1.json').read_text()))


def test_actual_three_closed_cases_and_paired_replay_sources_are_not_new_native_losses():
    r = evidence()
    assert r['source_commits']['assay'] == '2f8d8ac38e10fbe006e399ecb846846916c95dce'
    assert r['original_assay_handle'] == 12849 and r['original_assay_exit_code'] == 0
    assert r['original_terminal']['status'] == 'closed' and r['original_terminal']['completed_cases'] == 3
    assert r['original_cold_exit_codes'] == r['original_readout_exit_codes'] == [0, 0]
    assert (DATA / 'cold-1.json').read_bytes() == (DATA / 'cold-2.json').read_bytes()
    assert file_sha256(DATA / 'cold-1.json') == r['paired_original_cold_file_sha256']
    assert (DATA / 'manifest-1.json').read_bytes() == (DATA / 'manifest-2.json').read_bytes()
    report = checked(json.loads((DATA / 'report.json').read_text()))
    assert report['content_sha256'] == r['paired_readout_content_sha256']
    assert r['new_scientific_native_worlds'] == r['new_scientific_losses'] == 0
    assert not r['held_out_conditions_consumed'] and not r['publication_ready']


def test_all_actual_calls_and_load_unknowns_reconcile_without_double_counting():
    r = evidence(); rows = r['cases']
    assert [v['actual_calibration_records'] for v in rows] == [28, 28, 29]
    assert [v['actual_proposal_started_calls'] for v in rows] == [14, 14, 7]
    assert r['calibration_transport_usage']['chat_POSTs'] == sum(v['actual_calibration_records'] for v in rows) == 85
    assert r['free_transport_usage']['chat_POSTs'] == sum(v['actual_proposal_started_calls'] for v in rows) == 35
    assert r['separate_role_load_POSTs'] == 6
    assert all(v['unknown_responses'] == 6 for v in r['role_load_token_counts'].values())
    for usage in (r['calibration_transport_usage'], r['free_transport_usage']):
        assert usage['nonfinal_responses'] == usage['completion_signal_unknown'] == usage['length_terminated_responses'] == 0
    assert sum(r[k]['prompt_tokens']['known_sum'] for k in ('calibration_transport_usage','free_transport_usage')) == 3050964
    assert sum(r[k]['output_tokens']['known_sum'] for k in ('calibration_transport_usage','free_transport_usage')) == 13832


def test_literal_edits_checkpoint_coverage_and_unscored_status_stay_distinct():
    rows = evidence()['cases']
    assert [v['implementation_phase_calls'] for v in rows] == [5, 0, 3]
    assert [v['literal_base_change']['literal_base_changed'] for v in rows] == [True, True, False]
    assert [v['session']['successful_document_changes'] for v in rows] == [2, 5, 0]
    assert sum(v['recorded_component_probe_attempts'] for v in rows) == 28
    assert all(v['free_submission_available'] and v['session']['explicit_finish_observed'] for v in rows)
    for row in rows:
        assert not any(row['visibility'].values())
        change = row['literal_base_change']
        assert not change['added_node_ids'] and not change['removed_node_ids']
        assert not change['connections_changed'] and not change['schedules_changed']
        assert change['new_native_loss'] is row['new_native_loss'] is None
        assert row['measured_full_output_reservation_fits_every_free_prompt']


def test_real_container_public_QA_is_not_a_new_model_certificate_or_scientific_gain():
    r = evidence(); qa = r['current_parameter_public_QA']
    assert r['original_clean_source_tests_passed'] == 91 and r['original_clean_source_tests_exit_code'] == 0
    assert r['original_optional_context_QA_handle'] == 5340 and r['original_optional_context_QA_exit_code'] == 0
    assert qa['real_container_probes'] == 24 and qa['actual_model_POSTs'] == qa['new_native_worlds'] == 0
    assert sum(c['literal_historical_probe_statuses'].count('raised') for c in qa['cases']) == 6
    assert sum(c['current_parameter_probe_statuses'].count('returned') for c in qa['cases']) == 12
    assert qa['HTTP_and_process_supervision'] == 'SCRIPTED'
    assert not qa['real_new_source_model_calibration_verified'] and not qa['whole_native_world_verified']
    assert not r['new_optional_context_real_model_certificate'] and not r['new_scientific_comparison_dispatched']


def test_first_failed_derived_projection_is_preserved_without_changing_raw_calls():
    r = evidence(); path = DATA / 'failed-flat-calibration-done-projection.json'
    assert file_sha256(path) == r['preserved_first_derived_readout']['file_sha256']
    failed = checked(json.loads(path.read_text()))
    assert failed['calibration_transport_usage']['nonfinal_responses'] == 85
    assert r['calibration_transport_usage']['nonfinal_responses'] == 0
    assert failed['raw_inventory_sha256'] == r['raw_inventory_sha256']
