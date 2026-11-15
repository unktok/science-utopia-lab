"""Actual completed three-control evidence, not a new experiment or replication."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data/native-legacy-choice-pilot-v1'


def read(path):
    return checked(json.loads(path.read_text()))


def test_normal_closure_and_all_paired_exports_are_retained_without_reselection():
    receipt = read(ROOT / 'research/results/native-legacy-choice-pilot-closed-v1.json')
    assert receipt['terminal']['status'] == 'closed' and receipt['terminal']['completed_jobs'] == 3
    assert receipt['physical_worlds'] == 3 and receipt['raw_files'] == 459
    assert receipt['two_original_audits_identical'] and receipt['two_original_costs_identical']
    assert len(receipt['paired_readout_files']) == 9
    for entry in receipt['paired_readout_files']:
        raw = (ROOT / entry['retained']).read_bytes()
        assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256']
    for name, expected in receipt['derived_files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    assert receipt['same_initial_physical_society']
    assert not receipt['automatic_invention_or_optimizer_gain_demonstrated']
    assert not receipt['held_out_evaluation'] and not receipt['publication_ready']


def test_all_three_losses_do_not_turn_an_advice_contrast_into_optimizer_superiority():
    receipt = read(ROOT / 'research/results/native-legacy-choice-pilot-closed-v1.json')
    worlds = {w['condition']: w for w in receipt['worlds']}
    assert worlds['core-assignment']['scores'] == {'throughput': -20., 'content-utility': -15.333333333333332}
    assert worlds['native-choice']['scores'] == {'throughput': -14., 'content-utility': -10.}
    assert worlds['native-choice-advice']['scores'] == {'throughput': -16., 'content-utility': -12.}
    for w in worlds.values():
        assert w['status'] == 'complete' and w['seed'] == 61001
    core = worlds['core-assignment']['scores']
    assert all(core[k] < w['scores'][k] for w in worlds.values() if w['condition'] != 'core-assignment'
        for k in core)
    assert receipt['core_assignment_dominates_other_two_on_recorded_T_and_U']
    assert not receipt['control_is_a_global_optimum']
    assert len(receipt['input_classes']) == 3
    assert all(len(group['physical_ids']) == 1 for group in receipt['input_classes'])


def test_received_advice_exact_topic_and_shortest_duration_are_different_observations():
    report = read(DATA / 'choices/report.json')
    cut, native, advised = report['worlds']
    assert [w['direction_request_attempts'] for w in report['worlds']] == [0, 10, 10]
    assert len(cut['catalog_project_effects']) == 10
    assert not native['catalog_project_effects'] and not advised['catalog_project_effects']
    assert advised['stored_advice_recipient_records'] == 10
    assert advised['assessable_current_advice_completed_direction_attempts'] == 10
    assert advised['selected_current_recommendation_attempts'] == 0
    rows = advised['direction_requests']
    assert sum(r['selected_catalog_duration_years'] == r['current_recommended_duration'] for r in rows) == 2
    assert all(r['current_effective_year_advice_messages'] == 1 for r in rows)
    assert any(r['other_effective_year_advice_messages'] > 0 for r in rows)
    all_rows = native['direction_requests'] + rows
    assert all(r['unique_actor_attribution'] for r in all_rows)
    assert not any(r['selected_catalog_duration_years'] == 1 for r in all_rows)
    assert all(r['selected_topic'] in {v['topic'] for v in r['displayed_candidates']} for r in all_rows)
    receipt = read(ROOT / 'research/results/native-legacy-choice-pilot-closed-v1.json')
    assert receipt['original_direction_topic_schema'] == {'observed_requests': 20,
        'literal_property': {'title': 'Topic', 'type': 'string'}, 'hard_enum_restriction_present': False}


def test_content_overlap_retains_replacements_not_just_two_extra_accepted_records():
    delta = read(ROOT / 'research/results/native-legacy-choice-pilot-content-delta-v1.json')
    native, advised = delta['worlds'][1:]
    assert Fraction(native['exact_utility_sum']) == 10 and Fraction(advised['exact_utility_sum']) == 12
    pair = next(p['overlap'] for p in delta['all_complete_pairs'] if
        (p['left'], p['right']) == ('native-choice', 'native-choice-advice'))
    assert pair['common']['occurrences'] == 6
    assert pair['left_only']['occurrences'] == 8 and pair['right_only']['occurrences'] == 10
    difference = pair['left_minus_right']['exact_utility_at_declared_center_3']
    assert Fraction(difference['numerator'], difference['denominator']) == -2
    assert delta['new_model_calls'] == delta['new_code_executions'] == 0
    assert not delta['loss_changed'] and not delta['policy_selection']


def test_native_scientist_critic_and_load_cost_units_are_not_pooled():
    cost = read(DATA / 'cost-summary.json')
    assert cost['scientist_completed_responses'] == 386 and cost['scientist_wire_inputs_without_committed_reply'] == 0
    assert cost['common_content_observer']['physical_requests'] == 120
    assert cost['common_content_observer']['known_terminal_attempts'] == 120
    assert set(cost['auxiliary_POST_groups']) == {'load-scientist'}
    assert cost['auxiliary_POST_groups']['load-scientist']['recorded_POST_attempt'] == 3
    usage = cost['scientist_provider_usage']
    assert usage['prompt_tokens']['recorded_sum'] == 467505
    assert usage['completion_tokens']['recorded_sum'] == 40304
    assert usage['total_tokens']['recorded_sum'] == 507809
    assert usage['cached_prompt_tokens']['recorded_sum'] == 97796
    assert cost['new_designer_generation_POSTs'] == cost['new_model_calls'] == 0
