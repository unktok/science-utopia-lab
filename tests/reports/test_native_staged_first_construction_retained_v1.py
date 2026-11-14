"""Retained terminal proposal scope, not a live heartbeat or new native result."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def test_actual_staged_proposal_keeps_all_steps_probes_and_known_rejection():
    r = checked(json.loads((ROOT/'research/results/native-open-staged-first-construction-v1.json').read_text()))
    assert r['model_steps'] == 14 and r['selected_step'] == 13 and r['proposal_status'] == 'generated'
    assert r['step_status_counts'] == {'applied': 12, 'rejected': 1, 'finished': 1}
    assert r['tool_counts'] == {'plan': 1, 'read_file': 9, 'write_file': 3, 'finish': 1}
    error, = r['technical_rejections']; assert error['step'] == 12
    assert 'rationale' in error['errors'][0]['message'] and 'maxLength' in error['errors'][0]['message']
    t = r['component_trace']; assert t['component_testing']['probe_attempts'] == 8
    assert t['component_testing']['returned'] == 8 and t['component_testing']['raised'] == 0
    assert len(t['same_fixture_later_code_comparisons']) == 4
    assert all(x['transition'] == 'returned-to-returned' for x in t['same_fixture_later_code_comparisons'])
    assert r['same_fixture_outputs_equal_between_two_tested_versions']
    assert all(x['matches_current_successful_edit'] for x in r['literal_source_readbacks'])
    assert not r['component_error_repair_demonstrated'] and not r['host_source_repair']


def test_source_change_and_native_start_do_not_become_an_improvement_claim():
    r = checked(json.loads((ROOT/'research/results/native-open-staged-first-construction-v1.json').read_text()))
    g = r['literal_graph_change']
    assert set(g['source_edits']) == {'world.selection'}
    for key in ('added_nodes', 'removed_nodes', 'added_connections', 'removed_connections', 'phase_updates'):
        assert not g[key]
    assert r['native_world_entered'] and not r['own_native_observation_complete'] and r['own_loss'] is None
    assert not r['whole_study_cold_audit_complete'] and not r['new_institutional_advantage_claimed']
    assert not r['publication_ready']
    assert [c['scores']['throughput'] for c in r['completed_controls']] == [-18., -20.]


def test_first_actual_native_completion_is_a_tie_not_an_invented_gain_or_whole_study_close():
    r = checked(json.loads((ROOT/'research/results/native-open-staged-first-own-v1.json').read_text()))
    construction = checked(json.loads((ROOT/'research/results/native-open-staged-first-construction-v1.json').read_text()))
    assert r['first_construction_evidence_content_sha256'] == construction['content_sha256']
    assert r['request_sha256'] == construction['request_sha256']
    assert r['status'] == 'complete' and r['assigned_loss'] == -18.
    assert r['cross_scores'] == {'throughput': -18., 'content-utility': -13.333333333333332}
    assert r['completed_own_slots'] == 1 and r['total_declared_own_slots'] == 6
    assert all(x['requests']['completed_responses'] == 115 for x in r['literal_scientist_traces'])
    assert r['request_and_choice_comparison']['ordered_full_request_payload_sha256']
    assert r['request_and_choice_comparison']['ordered_literal_response_choices_sha256']
    assert r['no_text_ID_or_clock_scrubbing']
    assert not r['own_improvement_over_R7'] and not r['own_advantage_over_hand']
    assert not r['full_study_cold_audit_complete'] and not r['publication_ready']


def test_utility_explicit_retention_keeps_rejected_reads_and_real_loss_separate():
    r = checked(json.loads((ROOT/'research/results/native-open-staged-first-utility-own-v1.json').read_text()))
    assert r['status'] == 'complete' and r['proposal_status'] == 'generated'
    assert r['candidate_equals_literal_parent_and_R7']
    assert r['assigned_loss'] == r['cross_scores']['content-utility'] == -13.333333333333332
    assert r['cross_scores']['throughput'] == -18.
    assert r['model_steps'] == 14
    assert r['step_status_counts'] == {'applied': 4, 'rejected': 9, 'finished': 1}
    assert r['tool_counts'] == {'plan': 1, 'read_file': 12, 'finish': 1}
    assert [x['step'] for x in r['implementation_checkpoint_rejections']] == list(range(4, 13))
    assert all('implementation checkpoint' in x['errors'][0]['message']
        for x in r['implementation_checkpoint_rejections'])
    assert r['component_testing']['probe_attempts'] == 0
    assert r['designer_http_summary']['calls'] == 14
    assert r['designer_http_summary']['all_http_200_final_stop']
    assert r['designer_http_summary']['all_reported_prompt_plus_reserved_output_fit']
    frame = r['checked_last_implementation_frame']
    assert frame['literal_current_system_equals_parent'] and frame['implementation_task_present']
    assert frame['phase'] == 'implementation' and frame['previous_status'] == 'rejected'
    assert frame['advertised_functions']['read_file'] == 0
    assert r['completed_own_slots_at_snapshot'] == 2 and r['total_declared_own_slots'] == 6
    assert r['request_and_choice_comparison']['ordered_full_request_payload_sha256']
    assert r['request_and_choice_comparison']['ordered_literal_response_choices_sha256']
    assert not r['new_institution_invented_in_this_slot'] and not r['host_source_repair']
    assert not r['own_improvement_over_R7'] and not r['own_advantage_over_hand']
    assert not r['full_study_cold_audit_complete'] and not r['unused_evaluation_complete']
    assert not r['publication_ready']


def test_operated_agenda_change_keeps_worse_utility_and_objective_specific_reference():
    import math
    r = checked(json.loads((ROOT/'research/results/native-open-staged-first-operative-agenda-v1.json').read_text()))
    assert r['status'] == 'complete' and r['assigned_loss'] == -12.
    assert r['cross_scores'] == {'throughput': -18., 'content-utility': -12.}
    assert r['reference_saved_assigned_loss'] == -18.
    assert r['reference_cross_scores']['R7-original']['content-utility'] == -13.333333333333332
    assert r['reference_saved_assigned_loss_is_not_utility_comparator']
    assert math.isclose(r['own_assigned_loss_minus_R7'], 4/3)
    assert r['step_status_counts'] == {'applied': 13, 'finished': 1}
    assert r['tool_counts'] == {'plan': 1, 'read_file': 8, 'write_file': 4, 'finish': 1}
    assert r['component_testing']['probe_attempts'] == r['component_testing']['returned'] == 16
    assert r['component_testing']['raised'] == 0
    versions = r['authored_versions']
    assert [v['step'] for v in versions] == [2, 4, 6, 10]
    assert len({v['ast_sha256'] for v in versions}) == 1
    assert versions[-1]['source_utf8_sha256'] == r['literal_graph_change']['source_edits']['developer-catalog-agenda']['after_source_utf8_sha256']
    for v in versions:
        assert all(q['same_context_as_original'] for q in v['probe_comparisons_with_original_saved_input'])
        assert [q['period'] for q in v['probe_comparisons_with_original_saved_input'] if not q['result_equals_original']] == [1, 3]
    change = r['first_changed_scientist_input']
    assert change['zero_based_request_index'] == change['preceding_exact_equal_payloads'] == 22
    assert change['R7_research_topic'] == 'distributed_systems'
    assert change['U1_research_topic'] == 'software_engineering'
    assert r['source_change_reached_observed_native_scientist_input']
    assert not r['request_and_choice_comparison']['ordered_full_request_payload_sha256']
    d = r['accepted_occurrence_decomposition']
    assert d['R7_accepted_count'] == d['U1_accepted_count'] == 18 and d['shared_count'] == 12
    assert d['shared_utility'] == 8 and d['U1_only_utility'] == 4
    assert math.isclose(d['R7_only_utility'], 16/3)
    assert math.isclose(d['loss_difference_reconstructed'], r['own_assigned_loss_minus_R7'])
    assert sum(x['multiplicity'] for x in d['R7_only']) == sum(x['multiplicity'] for x in d['U1_only']) == 6
    assert r['completed_own_slots_at_snapshot'] == 3 and r['total_declared_own_slots'] == 6
    assert not r['own_improvement_over_R7'] and not r['own_advantage_over_hand']
    assert not r['host_source_repair'] and not r['component_error_repair_demonstrated']
    assert not r['full_study_cold_audit_complete'] and not r['unused_evaluation_complete']
    assert not r['publication_ready']


def test_four_slot_prefix_keeps_valid_tie_rejections_and_future_fix_separate():
    r = checked(json.loads((ROOT/'research/results/native-open-staged-four-slot-prefix-v1.json').read_text()))
    slots = r['slots_in_original_schedule_order']
    assert [(s['objective'], s['generation']) for s in slots] == [
        ('throughput', 0), ('content-utility', 0), ('content-utility', 1), ('throughput', 1)]
    assert [s['assigned_loss'] for s in slots] == [-18., -13.333333333333332, -12., -18.]
    assert all(s['status'] == 'complete' and s['assigned_loss'] == s['cross_scores'][s['objective']] for s in slots)
    t = r['T1']
    assert t['model_steps'] == 14 and t['step_status_counts'] == {'applied': 8, 'rejected': 5, 'finished': 1}
    assert [x['step'] for x in t['technical_rejections']] == [4, 5, 10, 11, 12]
    assert t['component_testing']['probe_attempts'] == t['component_testing']['returned'] == 4
    assert t['source_AST_equals_R7']
    assert all(x['requests']['completed_responses'] == 115 for x in t['literal_scientist_traces'])
    assert t['request_and_choice_comparison_with_R7']['ordered_full_request_payload_sha256']
    assert t['request_and_choice_comparison_with_R7']['ordered_literal_response_choices_sha256']
    assert r['completed_own_slots_at_snapshot'] == 4 and r['total_declared_own_slots'] == 6
    future = r['future_rationale_fix']
    assert future['verified_unit_tests'] == 25 and future['actual_rejected_actions_schema_checked'] == 3
    assert not future['merged_to_main'] and not future['applied_to_active_study']
    assert future['full_native_integration_pending']
    assert not r['candidate_repaired_or_refilled'] and not r['loss_changed']
    assert not r['full_study_cold_audit_complete'] and not r['fixed_unused_evaluation_complete']
    assert not r['publication_ready']
