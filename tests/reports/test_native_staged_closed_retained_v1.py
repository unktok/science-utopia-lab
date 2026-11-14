"""Compact retained closure consistency; no new models, worlds or cold audit."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def evidence():
    return checked(json.loads((ROOT / 'research/results/native-open-staged-institution-closed-v1.json').read_text()))


def test_complete_schedule_reconciles_all_steps_and_probes():
    r = evidence()
    assert r['source_commit'] == 'f47270b967fa167d59df759bebe7b6b104b383d3'
    assert r['terminal']['status'] == 'closed'
    assert r['terminal']['consumed_slots'] == 6 and r['terminal']['observations'] == 8
    slots = r['slots']
    assert [(s['objective'], s['generation']) for s in slots] == [
        ('throughput', 0), ('content-utility', 0), ('content-utility', 1),
        ('throughput', 1), ('throughput', 2), ('content-utility', 2)]
    assert [s['slot_index'] for s in slots] == list(range(6))
    assert all(s['status'] == 'complete' for s in slots)
    assert sum(s['completed_author_steps'] for s in slots) == 84
    probes = [s['component_testing'] for s in slots]
    assert [p['probe_attempts'] for p in probes] == [8, 0, 16, 4, 20, 16]
    assert sum(p['probe_attempts'] for p in probes) == r['construction_counts']['known_probe_attempts'] == 64
    assert sum(p['returned'] for p in probes) == r['construction_counts']['returned'] == 64
    assert sum(p['raised'] for p in probes) == r['construction_counts']['raised'] == 0
    assert all(not p['veto_on_finish'] for p in probes)


def test_all_unfavorable_scores_and_literal_first_tie_selection_stay():
    r = evidence()
    assert [s['cross_scores']['throughput'] for s in r['slots']] == [-18.] * 6
    assert [s['cross_scores']['content-utility'] for s in r['slots']] == [
        -13.333333333333332, -13.333333333333332, -12.,
        -13.333333333333332, -13.333333333333332, -13.333333333333332]
    for objective, selection in r['selection'].items():
        own = [s for s in r['slots'] if s['objective'] == objective]
        best = min(own, key=lambda s: s['cross_scores'][objective])
        assert selection['selected_id'] == best['physical_job']
        assert selection['loss'] == best['cross_scores'][objective]
        assert selection['all_tied_ids'] == [s['physical_job'] for s in own
            if s['cross_scores'][objective] == selection['loss']]
    assert r['references'][0]['optimizer_visible']
    assert not r['references'][1]['optimizer_visible']
    assert r['references'][1]['scores']['throughput'] == -20.
    assert r['references'][1]['scores']['content-utility'] == -15.333333333333332
    assert not any(s['added_nodes'] or s['added_connections'] for s in r['slots'])


def test_report_and_cost_scopes_do_not_become_publication_or_replication_claims():
    r = evidence()
    assert r['audit']['double_audit_bytes_equal'] and r['audit']['double_cost_bytes_equal']
    assert set(r['readouts']) == {'report', 'choices', 'effects', 'requests', 'construction'}
    assert all(x['all_export_files_byte_identical'] for x in r['readouts'].values())
    costs = r['costs']
    assert costs['scientist_completed_responses'] == 937
    assert costs['scientist_wire_inputs_without_committed_reply'] == 0
    assert costs['scientist_provider_usage']['prompt_tokens']['recorded_sum'] == 1117688
    assert costs['scientist_provider_usage']['completion_tokens']['recorded_sum'] == 98457
    assert costs['scientist_provider_usage']['cached_prompt_tokens']['recorded_sum'] == 190032
    assert not costs['aliases_or_nested_durations_added']
    assert costs['common_content_observer']['physical_requests'] == 93
    assert costs['auxiliary_group_counts']['staged-proposal']['recorded_POST_attempt'] == 84
    assert costs['auxiliary_group_counts']['editor-readiness']['recorded_POST_attempt'] == 200
    for key in ('automatic_error_repair_demonstrated', 'own_improvement_over_R7_observed',
                'own_advantage_over_hand_observed', 'unused_evaluation_completed',
                'independent_optimizer_replication', 'scientific_truth_demonstrated', 'publication_ready'):
        assert not r['interpretation'][key]


def test_first_fixed_completion_is_literal_sharing_and_not_whole_run_closure():
    p = ROOT/'research/results/native-open-staged-fixed-first-completion-v1.json'
    r = checked(json.loads(p.read_text()))
    assert r['seed'] == 1891355522 and r['completed_job'] == 'evaluation-000'
    assert r['labels'] == ['reference:R7-original', 'selected:content-utility']
    assert r['literal_policy_identity_sharing_only']
    assert r['cross_scores'] == {'throughput': -32., 'content-utility': -28.666666666666668}
    assert r['scientist_completed_responses'] == 161
    assert r['completed_physical_jobs_at_snapshot'] == 1 and r['total_physical_jobs'] == 3
    assert r['observed_progress']['active'] == 'evaluation-001'
    assert not r['whole_fixed_evaluation_complete'] and not r['whole_original_cold_audit_complete']
    assert not r['terminal_present_at_snapshot'] and not r['own_improvement_or_advantage_claimed']
    assert r['new_designer_POSTs'] == r['new_model_calls_by_this_reader'] == 0
    assert not r['publication_ready']
