import hashlib
import json
from pathlib import Path

from scripts.reports.native_capacity_preference_geometry_v1 import summarize
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data/native-capacity-objective-loop-v1'


def read(path):
    return checked(json.loads(path.read_text()))


def test_original_exports_and_negative_search_boundary_preserved():
    receipt = read(ROOT / 'research/results/native-capacity-objective-closed-verification-v1.json')
    for path, expected in receipt['retained_files'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    assert receipt['scientific_source_commit'] == '16cfdcef2151e01365c1fc2bea3f5cc928954220'
    assert (receipt['physical_attempts'], receipt['complete_worlds'], receipt['own_submissions']) == (9, 8, 4)
    assert receipt['technical_nulls'] == 1 and receipt['seed'] == 61001
    assert not receipt['held_out_evaluation_dispatched']
    assert not receipt['independent_optimizer_replications']
    assert not receipt['generated_policy_advantage_demonstrated']
    assert not receipt['publication_ready']


def test_all_slots_scores_paths_and_own_only_ties():
    report = read(DATA / 'report.json')
    assert [s['status'] for s in report['slots']] == ['complete', 'complete', 'failed', 'complete']
    for slot in report['slots']:
        assert not slot['connections_changed'] and not slot['schedules_changed']
        assert not slot['nodes_added'] and not slot['nodes_removed']
        assert slot['parent_matching_observation_ids'] == ['reference-reviewed-all-reserve-proximity']
        expected = None if slot['status'] == 'failed' else (-12., -15.)
        assert tuple(slot['cross_scores'][k] for k in report['score_order']) == (expected or (None, None))
    assert len(report['frozen_selection']['throughput']['all_tied_ids']) == 2
    assert len(report['frozen_selection']['founder-activity']['all_tied_ids']) == 1
    worlds = report['physical_worlds']
    assert [w['scores'] for w in worlds[:3]] == [dict(zip(report['score_order'], [-10., -12.]))] * 3
    paths = [[a['active_founders'] for a in w['measurements'][0]['active_founder_boundary_instrument']['annual']]
             for w in worlds[:3]]
    assert paths == [[5, 5, 1, 1], [4, 4, 2, 2], [5, 5, 1, 1]]


def test_observed_geometry_is_not_an_interior_optimization():
    report, retained = read(DATA / 'report.json'), read(DATA / 'geometry.json')
    assert summarize(report) == {k: v for k, v in retained.items() if k != 'content_sha256'}
    assert [(c['T'], c['P']) for c in retained['curves']] == [('-12', '-15'), ('-10', '-12')]
    assert retained['geometry']['open_intervals'] == [{'left': '0', 'right': '1', 'winning_curve_indices': [0]}]
    assert not retained['family']['interior_objectives_optimized']
    assert not retained['candidate_reselection']


def test_input_equality_is_not_provider_envelope_equality_or_program_equivalence():
    report = read(DATA / 'requests.json')
    groups = report['complete_observed_input_classes']
    assert len(groups) == 5
    common = next(g for g in groups if len(g['physical_ids']) == 4)
    assert common['all_literal_response_choices_equal']
    assert not common['all_full_provider_bodies_equal']
    assert set(common['physical_ids']) == {
        'native-adaptive-38e879f7d6ef5b3449ee528e',
        'native-adaptive-bae9b09003c3fcb7764b8c8f',
        'reference-reviewed-all-completion-priority',
        'reference-reviewed-all-reserve-proximity',
    }


def test_failed_virtual_source_and_partial_boundaries_remain_unscored():
    receipt = read(ROOT / 'research/results/native-capacity-objective-closed-verification-v1.json')
    bad = receipt['failed_transfer_diagnostic']
    assert bad['year'] == 3 and not bad['host_repair'] and not bad['loss_imputed']
    assert [(x['from_actor'], x['amount']) for x in bad['commands']] == [('system', 10), ('system', 10)]
    effects = read(DATA / 'effects.json')
    failed = next(w for w in effects['worlds'] if w['status'] != 'complete')
    assert [a['year'] for a in failed['annual']] == [1, 2]
    assert failed['partial_boundaries_are_not_completed_outcomes']
    assert len(failed['uncommitted_recorded_bundles']) == 2
    assert sum(len(w['code_calls']) for w in effects['worlds']) == 172
    assert sum(len(w['annual']) for w in effects['worlds']) == 34


def test_physical_costs_and_no_critic_or_duplicate_load_tokens():
    costs = read(DATA / 'costs.json')
    assert costs['scientist']['completed_responses'] == 1171
    usage = costs['scientist']['provider_usage']
    assert usage['prompt_tokens']['recorded_sum'] == 1117703
    assert usage['completion_tokens']['recorded_sum'] == 111959
    assert usage['cached_prompt_tokens']['recorded_sum'] == 213168
    groups = costs['auxiliary']['groups']
    assert set(groups) == {'editor-readiness', 'staged-proposal', 'load-designer', 'load-scientist'}
    assert groups['staged-proposal']['recorded_POST_attempt'] == 58
    assert groups['editor-readiness']['recorded_POST_attempt'] == 142
    for name in ('load-designer', 'load-scientist'):
        assert groups[name]['recorded_POST_attempt'] == 9
        assert groups[name]['measurements']['native_prompt_eval_count']['recorded_sum'] is None


def test_integrated_argument_keeps_actual_null_and_no_fixed_evaluation():
    entry = (ROOT / 'paper/integrated.tex').read_text()
    text = (ROOT / 'paper/integrated/native-capacity.tex').read_text()
    assert '\\input{integrated/native-capacity}' in entry
    assert 'nonexistent actor\\code{system}' in text
    assert 'not dispatched for this flat pilot' in text.replace('\n', ' ')
    assert 'not an additional constraint on T' in text
    assert '172 code calls' in text and '34 committed annual boundaries' in text
