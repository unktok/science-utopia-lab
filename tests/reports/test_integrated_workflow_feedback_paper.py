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
