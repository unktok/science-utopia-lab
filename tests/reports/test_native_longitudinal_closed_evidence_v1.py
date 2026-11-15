"""Retained actual-development evidence, not another simulated replication."""
import hashlib
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data/native-longitudinal-development-v1'


def read(path):
    return checked(json.loads(path.read_text()))


def test_retained_report_files_match_the_paired_original_identities():
    manifest = read(ROOT / 'research/results/native-longitudinal-development-retention-v1.json')
    assert manifest['raw_files'] == 3321
    assert not manifest['publication_ready']
    assert manifest['new_model_calls'] == manifest['new_code_executions'] == 0
    assert len(manifest['paired_reports']) == 19
    for entry in manifest['paired_reports']:
        raw = (ROOT / entry['retained']).read_bytes()
        assert len(raw) == entry['bytes']
        assert hashlib.sha256(raw).hexdigest() == entry['sha256'] == entry['paired_sha256']
    for path, sha in manifest['derived_files'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha


def test_all_assigned_ties_do_not_erase_the_cross_objective_worsening_or_nulls():
    scores = read(DATA / 'scores/report.json')
    slots = scores['slots']
    assert len(slots) == 12
    valid = [s for s in slots if s['status'] == 'complete']
    failed = [s for s in slots if s['status'] == 'failed']
    assert len(valid) == 10 and len(failed) == 2
    assert all(s['loss'] is None for s in failed)
    reference = next(r for r in scores['references'] if r['label'] == 'R7-original')
    assert all(s['loss'] == reference['scores'][s['objective']] for s in valid)
    assert sum(s['cross_scores'] == reference['scores'] for s in valid) == 9
    assert slots[-1]['cross_scores']['content-utility'] == -12.333333333333332
    assert not scores['interpretation']['publication_ready']
    requests = read(DATA / 'requests/report.json')
    classes = requests['complete_observed_input_classes']
    assert sorted(len(c['physical_ids']) for c in classes) == [1, 1, 10]
    largest = max(classes, key=lambda c: len(c['physical_ids']))
    assert largest['all_literal_response_choices_equal']
    assert not largest['all_full_provider_bodies_equal']


def test_full_input_difference_keeps_both_score_routes_and_the_partial_trace():
    first = ROOT / 'research/results/native-longitudinal-first-score-input-divergence-v1.json'
    v1 = read(first)
    v2 = read(ROOT / 'research/results/native-longitudinal-first-score-input-divergence-v2.json')
    assert v2['supplements_v1_sha256'] == hashlib.sha256(first.read_bytes()).hexdigest()
    assert v1['first_different_request_index'] == v2['first_different_request_index'] == 70
    assert v1['previous_full_payloads_identical'] and v2['previous_full_payloads_identical']
    assert not v1['literal_score_substitution_alone_reconstructs_prompt']
    assert v2['two_literal_score_substitutions_reconstruct_entire_prompt']
    assert len(v2['all_text_edits']) == 6
    assert v2['dossier_score_fields_changed'] == 4
    assert v2['native_past_paper_score_fields_changed'] == 2
    assert not v1['isolated_causal_effect_claimed'] and not v2['isolated_causal_effect_claimed']


def test_fixed_batch_headroom_is_not_mislabeled_a_global_bound():
    value = read(ROOT / 'research/results/native-longitudinal-selection-headroom-v1.json')
    assert len(value['worlds']) == 12  # Ten measured own worlds plus two references.
    assert value['technical_nulls_excluded_from_complete_worlds'] == 2
    assert all(w['rejected_total'] == 0 for w in value['worlds'])
    hand = next(w for w in value['worlds'] if w['identity'] == 'workflow-reference-post-funding-cost')
    assert hand['accepted_total'] == 20
    assert all(w['accepted_total'] == 18 for w in value['worlds'] if w is not hand)
    assert not value['global_policy_upper_bound_claimed']
    assert not value['causal_explanation_for_search_concentration_proved']
    assert value['new_model_calls'] == value['new_code_executions'] == 0


def test_paper_path_series_keeps_unknown_losses_separate_from_best_own():
    from scripts.reports.native_longitudinal_paper_v1 import series
    value = read(DATA / 'scores/report.json')
    t = series(value, 'scalar', 'throughput')
    assert [r['observed'] for r in t] == [-18.0, -18.0, None]
    assert [r['best_own'] for r in t] == [-18.0] * 3
    assert [r['null'] for r in t] == [False, False, True]
    u = series(value, 'parent-trajectory', 'content-utility')
    assert [r['null'] for r in u] == [False, True, False]
    assert u[1]['observed'] is None


def test_observed_loss_frontier_is_finite_support_not_a_global_optimum():
    value = read(ROOT / 'research/results/native-longitudinal-observed-loss-support-v1.json')
    assert len(value['measured_rows']) == 12 and value['unknown_own_slots'] == 2
    assert len(value['unique_measured_vectors']) == 3
    hand = 'workflow-reference-post-funding-cost'
    assert value['observed_measured_pareto_frontier'] == [hand]
    assert all(rows == [hand] for rows in value['per_objective_measured_minima'].values())
    assert not value['loss_or_selection_changed']
    assert value['new_model_calls'] == value['new_code_executions'] == 0


def test_actual_first_planning_frames_advertise_more_than_selection_without_proving_model_understanding():
    value = read(ROOT / 'research/results/native-longitudinal-first-frame-scope-v1.json')
    assert value['first_planning_frames'] == len(value['sessions']) == 12
    assert value['literal_system_prompt_classes'] == 1
    for field in ('system_prompt', 'user_footer'):
        body = (ROOT / value[field + '_file']).read_bytes()
        assert hashlib.sha256(body).hexdigest() == value[field + '_file_sha256']
    assert {r['generation'] for r in value['sessions']} == {0, 1, 2}
    assert len({r['history_directory'] for r in value['sessions']}) == 4
    assert all(r['declared_space_equals_original_plan'] and r['new_node_append_advertised']
        and r['whole_draft_and_wiring_files_advertised'] for r in value['sessions'])
    assert all(len(r['fixture_node_counts']) == 5 and set(r['fixture_node_counts'].values()) == {4}
        and not r['auto_fixture_failure_veto'] for r in value['sessions'])
    assert value['first_planning_call_only']
    assert not value['fixture_support_is_selection_only']
    assert not value['causal_reason_for_edit_concentration_proved'] and not value['model_understanding_proved']
    assert not value['old_prompt_or_loss_changed']
    assert value['new_model_calls'] == value['new_code_executions'] == 0


def test_future_generic_author_capabilities_defer_to_the_actual_study_contract():
    from utopia.optimization.native_staged_author_v15 import FILE_EDITOR_INSTRUCTIONS
    assert 'Within the supplied design-space contract' in FILE_EDITOR_INSTRUCTIONS
    assert 'Generic capabilities do not override that contract' in FILE_EDITOR_INSTRUCTIONS
    assert 'editable wherever the contract permits' in FILE_EDITOR_INSTRUCTIONS
    assert 'There is no additional fairness, novelty, quality or adoption objective' in FILE_EDITOR_INSTRUCTIONS
