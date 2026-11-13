"""Keep the complete actual planning pilot distinct from preparation and gain."""
import csv
import hashlib
import json
from pathlib import Path

from scripts.check_repository_docs import check
from scripts.reports.native_planning_content_contributions_v1 import summarize
from utopia.optimization.native_numeric_designer import checked
from utopia.system.native_planning_controls import ORDER

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data/native-planning-objective-loop-v1'


def read(path):
    return checked(json.loads(path.read_text()))


def test_exact_artifacts_and_normal_closure_are_not_a_readiness_claim():
    receipt = read(ROOT / 'research/results/native-planning-objective-closed-verification-v1.json')
    assert receipt['scientific_source_commit'] == '8cd61578b94d86dd0cf2ff3b0e581d9a2698fc0f'
    assert (receipt['physical_attempts'], receipt['complete_worlds'], receipt['own_submissions']) == (14, 14, 6)
    assert receipt['technical_nulls'] == 0 and receipt['seed'] == 61001 and receipt['raw_files'] == 2302
    assert len(receipt['retained_files']) == 22
    for path, expected in receipt['retained_files'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    assert set(receipt['observed_session_exit_codes'].values()) == {0}
    assert len(receipt['observed_session_exit_codes']) == 7
    assert receipt['audit_and_cost_closure']['status'] == 'closed'
    assert [s['exit_code'] for s in receipt['audit_and_cost_closure']['steps']] == [0] * 4
    assert set(receipt['readers']) == {'scores', 'content', 'choices', 'effects', 'requests'}
    assert all(v['all_export_bytes_match'] for v in receipt['readers'].values())
    assert not any(receipt[k] for k in ('held_out_evaluation_dispatched',
        'independent_optimizer_replications', 'generated_policy_advantage_demonstrated',
        'scientific_truth_measured', 'publication_ready', 'new_model_calls_by_retention',
        'new_native_worlds_by_retention'))


def test_all_reference_and_own_scores_and_own_only_selection():
    r = read(DATA / 'report.json')
    assert [x['label'] for x in r['references']] == list(ORDER)
    assert [(x['scores']['throughput'], x['scores']['content-utility']) for x in r['references']] == [
        (-12., -8.), (-18., -11.333333333333332), (-18., -13.), (-12., -8.),
        (-12., -8.), (-18., -13.), (-18., -13.333333333333332), (0., 0.)]
    assert [(x['objective'], x['generation']) for x in r['slots']] == [
        ('throughput', 0), ('content-utility', 0), ('content-utility', 1),
        ('throughput', 1), ('throughput', 2), ('content-utility', 2)]
    assert all(s['status'] == 'complete' for s in r['slots'])
    for objective, expected in [('throughput', -18.), ('content-utility', -13.333333333333332)]:
        own = [s for s in r['slots'] if s['objective'] == objective]
        assert [s['loss'] for s in own] == [expected] * 3
        assert expected == min(x['scores'][objective] for x in r['references'])
        chosen = r['frozen_selection'][objective]
        assert chosen['completed_submissions'] == 3 and len(chosen['all_tied_ids']) == 3
        assert chosen['selected_id'] == chosen['all_tied_ids'][0] == own[0]['physical_job']


def test_literal_plans_and_actual_selection_only_edits_are_separate():
    r = read(DATA / 'report.json'); plans = read(DATA / 'initial-plans.json')
    assert len(plans['slots']) == 6 and plans['scientific_source_commit'] == r['source_commit']
    assert plans['original_audit_content_sha256'] == r['audit_sha256']
    for slot, plan in zip(r['slots'], plans['slots']):
        assert (slot['objective'], slot['generation'], slot['request_sha256']) == (
            plan['objective'], plan['generation'], plan['request_sha256'])
        index = 7 if slot['objective'] == 'throughput' else 6
        assert slot['changed_paths_from_parent'] == [f'/mechanisms/{index}/parameters/code_artifact/source']
        assert not any(slot[k] for k in ('connections_changed', 'schedules_changed', 'nodes_added', 'nodes_removed'))
        parent = 'reference-advice-reserve21-all' if index == 7 else 'reference-assignment-reserve21-no-review-all'
        assert slot['parent_matching_observation_ids'] == [parent]
        assert plan['actual_changed_paths_from_parent'] == slot['changed_paths_from_parent']
    assert 'code/developer-catalog-agenda.py' in plans['slots'][-1]['untrusted_initial_plan']['implementation_targets']
    assert not plans['new_model_calls'] and not plans['new_code_executions']


def test_signed_content_and_observed_preference_refinement():
    source = read(DATA / 'report.json'); r = read(DATA / 'content-contributions.json')
    assert summarize(source) == r
    assert sum(len(w['accepted_records']) for w in r['worlds']) == 216
    assert len({a['content_sha256'] for w in r['worlds'] for a in w['accepted_records']}) == 54
    assert all(w['sign_counts']['negative'] == 0 for w in r['worlds'])
    pairs = r['recorded_preference_geometry']['by_world_seed'][0]['objective_pairs'][0]
    assert pairs['pair_counts'] == {'joint-tie': 12, 'same-strict-preference': 43,
        'strict-conflict': 0, 'tie-only-first': 36, 'tie-only-second': 0}
    assert len(pairs['observed_minimum_set_intersection']) == 4
    assert not any(r[k] for k in ('loss_changed', 'candidate_reselection', 'causal_mediation_claimed', 'publication_ready'))
    with (DATA / 'accepted-records.csv').open(newline='') as f:
        assert len(list(csv.DictReader(f))) == 216


def test_observed_full_inputs_distinguish_equal_scores_from_retention():
    r = read(DATA / 'requests.json'); groups = r['complete_observed_input_classes']
    assert len(r['worlds']) == 14 and len(groups) == 8
    common = next(g for g in groups if len(g['physical_ids']) == 4)
    assert set(common['physical_ids']) == {'reference-assignment-reserve21-no-review-all',
        'native-adaptive-8a2e63bef510c15603d0d083', 'native-adaptive-5eda97605f6c4f8a25c16663',
        'native-adaptive-6b80487d1da63173d45adf55'}
    pair = next(g for g in groups if 'native-adaptive-069fea462ce717f8ad1618bc' in g['physical_ids'])
    assert set(pair['physical_ids']) == {'reference-advice-reserve21-all', 'native-adaptive-069fea462ce717f8ad1618bc'}
    t0 = next(g for g in groups if 'native-adaptive-d548b0de7dd069ea38b30a4c' in g['physical_ids'])
    assert set(t0['physical_ids']) == {'native-adaptive-d548b0de7dd069ea38b30a4c', 'native-adaptive-d00832cd2375d848541793d7'}
    assert all(g['all_literal_response_choices_equal'] and not g['all_full_provider_bodies_equal']
        for g in groups if len(g['physical_ids']) > 1)


def test_real_choices_and_all_committed_effect_boundaries():
    r = read(DATA / 'report.json'); c = read(DATA / 'choices.json'); e = read(DATA / 'effects.json')
    assert len(c['worlds']) == len(e['worlds']) == 14
    assert sum(len(w['code_calls']) for w in e['worlds']) == 336
    assert sum(len(w['annual']) for w in e['worlds']) == 56
    for s in r['slots']:
        w = next(w for w in c['worlds'] if w['identity'] == s['physical_job'])
        counts = len(w['direction_requests']), len(w['catalog_project_effects'])
        assert counts == ((10, 0) if s['objective'] == 'throughput' else (0, 10))
        w = next(w for w in e['worlds'] if w['identity'] == s['physical_job'])
        assert [a['active_founders'] for a in w['annual']] == [5, 5, 4, 2]


def test_actual_usage_keeps_design_calibration_critics_and_unknown_loads_separate():
    c = read(DATA / 'costs.json'); s = c['scientist']
    assert s['completed_responses'] == 2019 and not s['wire_inputs_without_committed_reply']
    assert [s['provider_usage'][k]['recorded_sum'] for k in (
        'prompt_tokens', 'completion_tokens', 'cached_prompt_tokens')] == [2196668, 194184, 368423]
    observer = c['common_content_observer']
    assert observer['physical_requests'] == observer['known_terminal_attempts'] == 162
    assert [observer['usage'][k]['known_sum'] for k in ('prompt_tokens', 'output_tokens')] == [77940, 24002]
    groups = c['auxiliary']['groups']
    assert {k: v['recorded_POST_attempt'] for k, v in groups.items()} == {
        'editor-readiness': 200, 'staged-proposal': 86, 'load-designer': 13, 'load-scientist': 14}
    for name, prompt, output in [('editor-readiness', 3843374, 9844), ('staged-proposal', 3598980, 8820)]:
        m = groups[name]['measurements']
        assert m['native_prompt_eval_count']['recorded_sum'] == prompt
        assert m['native_eval_count']['recorded_sum'] == output
    for name in ('load-designer', 'load-scientist'):
        assert groups[name]['measurements']['native_prompt_eval_count']['recorded_sum'] is None
    assert not c['unknown_usage_imputed']


def test_result_and_data_navigation_are_portable():
    r = check(ROOT, documents=('research/INDEX.md', 'research/STATUS.md',
        'research/results/native-planning-objective-loop-v1.md',
        'research/data/native-planning-objective-loop-v1/README.md'), manifest=None)
    assert r['status'] == 'passed', r['errors']
