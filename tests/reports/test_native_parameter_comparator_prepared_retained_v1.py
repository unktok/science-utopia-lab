"""Prepared exact native comparison is not an executed optimization result."""
import json
from pathlib import Path

from scripts.check_repository_docs import check
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def test_preparation_keeps_failed_fixture_and_separates_scripted_full_path_from_actual_prepare():
    p = checked(json.loads((ROOT / 'research/results/native-parameter-comparator-preparation-verification-v1.json').read_text()))
    assert p['scientific_source_commit'] == '04d0c3e3b5660a858f8241231e83b2ff679b9c25'
    assert [t['observed_exit_code'] for t in p['tests']] == [1, 0, 0]
    assert p['SCRIPTED_native_worlds'] == 14 and p['SCRIPTED_annual_checkpoints'] == 56
    assert p['SCRIPTED_numeric_worlds'] == 6 and p['SCRIPTED_original_common_reference_worlds'] == 8
    assert p['SCRIPTED_original_upstream_study_audit_is_fixture']
    assert p['SCRIPTED_production_role_factory_and_receipt_replay_used']
    assert p['SCRIPTED_two_cold_cost_CLI_outputs_match'] and p['SCRIPTED_two_four_file_reports_match']
    assert len(p['SCRIPTED_report_files']) == 4 and p['SCRIPTED_figure_viewed']
    assert p['actual_prepare_observed_exit_code'] == 0 and p['actual_original_bank_and_native_sources_validated']
    assert p['literal_original_native_source_files'] == 265
    assert p['anchors']['throughput']['reference'] == 'reference-advice-reserve21-all'
    assert p['anchors']['content-utility']['reference'] == 'reference-assignment-reserve21-no-review-all'
    assert not any(p[k] for k in ('actual_prepare_new_model_calls', 'new_numeric_study_dispatched',
        'new_numeric_scientific_worlds', 'held_out_evaluation', 'scientific_gain_demonstrated', 'publication_ready'))


def test_numeric_component_protocol_and_log_links_are_portable():
    result = check(ROOT, documents=('research/components/native-parameter-comparator-v1.md',
        'research/protocols/campaigns/native-parameter-comparator-v1.md',
        'research/logbook/2026-11-14-native-parameter-comparator.md'), manifest=None)
    assert result['status'] == 'passed', result['errors']
