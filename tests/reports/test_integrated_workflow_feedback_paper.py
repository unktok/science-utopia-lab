"""Actual retained study/unused result bindings, not scientific reruns or layout QA."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    return checked(json.loads((ROOT / 'research/results' / name).read_text()))


def test_complete_unused_comparison_keeps_identity_and_strong_control():
    result = load('native-workflow-feedback-fixed-closed-v3.json')
    assert result['terminal']['status'] == 'closed'
    assert result['physical_worlds'] == 3 and result['unused_seeds'] == [1858637637]
    rows = {r['label']: r for r in result['logical_rows']}
    assert rows['reference:R7-original']['scores'] == {
        'throughput': -32.0, 'content-utility': -24.666666666666668}
    for label in ('reference:post-funding-cost', 'selected:throughput', 'selected:content-utility'):
        assert rows[label]['scores'] == {'throughput': -36.0, 'content-utility': -26.0}
    assert rows['selected:content-utility']['physical_job'] == rows['reference:post-funding-cost']['physical_job']
    assert rows['selected:throughput']['physical_job'] != rows['reference:post-funding-cost']['physical_job']
    assert len(result['complete_observed_input_classes']) == 2
    assert not result['own_advantage_over_hand'] and not result['independent_optimizer_replication']
    assert result['new_designer_calls'] == 0 and not result['publication_ready']


def test_corrected_cost_components_preserve_the_original_omission_and_native_counts():
    result = load('native-workflow-feedback-fixed-closed-v3.json')
    assert result['original_cost_exports']['common_observer_component_omitted']
    assert result['original_cost_exports']['original_files_preserved']
    assert result['corrected_cost_exports']['two_exports_identical']
    assert result['corrected_cost_exports']['scientist_and_auxiliary_components_equal_original']
    assert result['scientist_cost']['completed_responses'] == 503
    assert result['scientist_cost']['wire_inputs_without_committed_reply'] == 0
    usage = result['scientist_cost']['provider_usage']
    assert usage['prompt_tokens']['recorded_sum'] == 761779
    assert usage['completion_tokens']['recorded_sum'] == 46319
    critic = result['common_content_observer_cost']
    assert critic['physical_requests'] == critic['known_terminal_attempts'] == 123
    assert critic['usage']['prompt_tokens'] == {'known_sum': 55617, 'unknown_attempts': 0}
    assert critic['usage']['output_tokens'] == {'known_sum': 18046, 'unknown_attempts': 0}


def test_native_proof_is_active_scripted_software_not_model_invention():
    proof = load('native-open-workflow-native-software-v1.json')
    assert proof['actual_model_calls'] == 0 and proof['total_native_worlds_in_final_check'] == 10
    assert proof['annual_checkpoints_in_final_check'] == 40
    assert [r['exit_code'] for r in proof['attempts']] == [1, 0, 0]
    final = proof['attempts'][-1]['fixed_native_verification']
    assert final['active_authored_scientist_input_change']['full_scientist_inputs_changed']
    assert final['common_observer_cost_bound_to_original_audit']
    assert not proof['scientific_gain_claimed'] and not proof['publication_ready']


def test_manuscript_reports_closure_without_invention_or_independence_claim():
    source = (ROOT / 'paper/integrated/native-workflow-feedback.tex').read_text()
    for literal in ('Original R7 & $-32$ & $-24.6667$ & 000',
            'Hand timing/routing & $-36$ & $-26$ & 001',
            'T-selected (T0) & $-36$ & $-26$ & 002',
            'U-selected (U0) & $-36$ & $-26$ & 001 (literal identity)',
            '503 complete scientist responses', '123 physical calls',
            'zero real-model calls', 'not an LLM-invented institution'):
        assert literal in source
    assert 'no complete evaluation outcome is reported here' not in source


def test_actual_open_prefix_preserves_worse_own_result_and_stopped_scope():
    result = load('native-open-institution-stopped-prefix-v2.json')
    assert result['terminal']['status'] == 'stopped'
    assert result['terminal']['consumed_slots'] == 1
    assert not result['scientific_study_closed'] and result['own_selections'] is None
    assert not result['fixed_evaluation_eligible'] and result['raw_unchanged']
    assert result['new_model_calls'] == result['new_code_executions'] == 0
    worlds = {r['label']: r for r in result['worlds']}
    assert worlds['T0']['throughput_loss'] == worlds['R7']['throughput_loss'] == -18.
    assert worlds['T0']['content_utility_loss'] > worlds['R7']['content_utility_loss']
    assert worlds['hand']['throughput_loss'] == -20.
    for key in ('ordered_full_request_payload_sha256', 'ordered_literal_response_choices_sha256'):
        assert worlds['T0']['requests'][key] != worlds['R7']['requests'][key]
    failed = [r for r in result['authors'] if r['status'] == 'failed']
    assert len(failed) == 1 and not failed[0]['completion_unknown']
    assert failed[0]['requested_operation_paths'] == ['/mechanisms/-', '/schedules/-']
    assert failed[0]['actual_operation_paths'] == ['/mechanisms/-']
    assert failed[0]['missing_schedule_is_only_literal_difference_except_operation_count']
    assert all(r['two_matching_original_source_replays'] for r in result['authors'])


def test_manuscript_open_result_is_not_hidden_by_calibration_stop_or_past_pdf():
    source = (ROOT / 'paper/integrated/native-workflow-feedback.tex').read_text()
    for literal in ('R7 reference & $-18$ & $-13.3333$ & 115',
            'Strong hand, comparison-only & $-20$ & $-15.3333$ & 127',
            'First own T0 & $-18$ & $-12.3333$ & 114',
            'first 70 full scientist request payloads match R7',
            'a whole-study audit or normal optimization closure',
            '374-file raw inventory remains unchanged',
            'remaining\nfive own slots have no result'):
        assert literal in source
    readme = (ROOT / 'paper/README.md').read_text()
    assert '78-page integrated draft' in readme
    assert 'revisions have not yet been rebuilt or visually reviewed' in readme
    discussion = (ROOT / 'paper/integrated/discussion.tex').read_text()
    assert 'free planning pilot is not counted as closed scientific evidence here' not in discussion


def test_completed_world_physical_readout_keeps_stopped_scope_and_rejoins_losses():
    result = load('native-open-institution-stopped-physical-readout-v2.json')
    prefix = load('native-open-institution-stopped-prefix-v2.json')
    assert result['actual_reader_exit_code'] == 0 and result['all_completed_worlds_covered']
    assert result['raw_inventory_sha256'] == prefix['raw_inventory_sha256']
    assert result['raw_files_unchanged'] and result['raw_files'] == 374
    assert not result['scientific_study_closed'] and not result['full_optimizer_history_replay_claimed']
    assert not result['original_observer_audit_present'] and not result['missing_original_journal_written']
    assert result['selection'] is None and not result['fixed_evaluation_eligible']
    aliases = {'R7-original': 'R7', 'post-funding-cost': 'hand', 'T0': 'T0'}
    prior = {r['label']: r for r in prefix['worlds']}
    for row in result['completed_worlds']:
        original = prior[aliases[row['label']]]
        assert row['physical_proof_status'] == 'complete' and row['annual_checkpoint_count'] == 4
        assert row['scores'] == {
            'throughput': original['throughput_loss'], 'content-utility': original['content_utility_loss']}
