"""Actual retained all-slot results and scientific interpretation boundaries."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT/'research/data/native-objective-instrument-loop-v1'


def read(name): return checked(json.loads((DATA/name).read_text()))


def test_closed_export_hashes_and_original_audit_identities():
    v = checked(json.loads((ROOT/'research/results/native-objective-instrument-loop-closed-verification-v1.json').read_text()))
    for group in ('retained_files', 'figure_files'):
        for name, expected in v[group].items():
            assert file_sha256(ROOT/name) == expected
    r = read('report.json'); c = read('costs.json'); e = read('effects.json')
    assert r['audit_sha256'] == c['input_audit_content_sha256'] == e['audit_content_sha256'] == v['audit_content_sha256']
    for name in ('preferences.json', 'request-classes.json'):
        assert read(name)['audit_content_sha256'] == v['audit_content_sha256']
    assert v['comparison_pairs'] == 16 and v['all_independent_outputs_byte_equal']
    assert v['fixed_evaluation_launch']['physical_worlds'] == 18
    assert v['fixed_evaluation_launch']['seeds'] == [64101,64107,64113]
    assert not v['fixed_evaluation_launch']['completed']
    assert not any(v['scope'].values())


def test_all_eight_slots_actual_probes_failures_and_own_ties():
    r = read('report.json'); slots = r['slots']
    assert len(slots) == 8 and len(r['physical_worlds']) == 13
    assert [x['status'] for x in slots] == ['complete','failed','complete','complete','complete','complete','complete','failed']
    assert [x['loss'] for x in slots] == [-7,None,-4,-7,-7,-4,-4,None]
    assert not any(x['connections_changed'] or x['schedules_changed'] or x['nodes_added'] or x['nodes_removed'] for x in slots)
    assert slots[2]['changed_paths_from_parent'] == []
    assert sum(x['component_trace']['component_testing']['probe_attempts'] for x in slots) == 52
    for x in slots:
        t = x['component_trace']; probe = t['component_testing']
        assert probe['raised'] == 0 and probe['returned'] == probe['probe_attempts']
        for c in t['drawn_candidate_artifact_observations']['components']:
            assert c['test_applicability'] == 'same-current-artifact'
    for objective, loss in [('throughput',-7), ('content-utility',-4)]:
        s = r['frozen_selection'][objective]
        assert s['loss'] == loss and s['completed_submissions'] == 3
        assert len(s['all_tied_ids']) == 3 and s['selected_id'] == s['all_tied_ids'][0]
        assert s['loss_minus_each_reference']['reviewed-all-connected'] == 0
    assert not r['interpretation']['held_out_evaluation']


def test_observed_preference_geometry_keeps_ties_without_claiming_global_optima():
    g = read('preferences.json')['geometry']['by_world_seed'][0]
    assert g['physical_rows'] == 13 and g['common_completed_rows'] == 11
    assert len(g['excluded_from_common_geometry']) == 2
    assert len(g['observed_minima']['throughput']['all_tied_physical_ids']) == 9
    assert len(g['observed_minima']['content-utility']['all_tied_physical_ids']) == 10
    assert g['objective_pairs'][0]['pair_counts'] == {
        'joint-tie':36, 'same-strict-preference':10, 'strict-conflict':0,
        'tie-only-first':0, 'tie-only-second':9}


def test_observed_input_identity_does_not_replace_behavior_or_outcome_evidence():
    q = read('request-classes.json'); r = read('report.json')
    by = {w['identity']:w for w in q['worlds']}
    reference = by['reference-reviewed-all-connected']['requests']
    same = [w for w in q['worlds'] if w['status']=='complete'
            and w['requests']['ordered_full_request_payload_sha256'] == reference['ordered_full_request_payload_sha256']]
    assert len(same) == 5 and len(q['complete_observed_input_classes']) == 7
    assert all(w['requests']['wire_requests'] == 129 for w in same)
    assert all(w['requests']['ordered_literal_response_choices_sha256'] == reference['ordered_literal_response_choices_sha256'] for w in same)
    shared = next(g for g in q['complete_observed_input_classes'] if len(g['physical_ids']) == 5)
    assert shared['all_literal_response_choices_equal'] and not shared['all_full_provider_bodies_equal']
    assert sorted(w['requests']['wire_requests'] for w in q['worlds'] if w['status']=='failed') == [5,34]
    for slot in r['slots']:
        if slot['status'] == 'complete':
            assert slot['cross_scores'] == {'throughput':-7.0,'content-utility':-4.0}
    assert not q['new_model_calls'] and not q['new_code_executions']


def test_partial_code_calls_and_usage_are_not_lost_or_zero_filled():
    e = read('effects.json'); c = read('costs.json')
    assert sum(len(w['code_calls']) for w in e['worlds']) == 236
    assert sum(len(w['annual']) for w in e['worlds']) == 45
    assert sum(len(y['founders']) for w in e['worlds'] for y in w['annual']) == 225
    assert sum(len(w['uncommitted_recorded_bundles']) for w in e['worlds']) == 7
    assert c['scientist']['completed_responses'] == 1383
    usage = c['scientist']['provider_usage']
    assert usage['prompt_tokens']['recorded_sum'] == 1258863
    assert usage['completion_tokens']['recorded_sum'] == 140155
    assert usage['cached_prompt_tokens']['recorded_sum'] == 214438
    assert c['common_content_observer']['physical_requests'] == 33
    for role in ('load-designer','load-scientist'):
        assert c['auxiliary']['groups'][role]['measurements']['native_prompt_eval_count']['recorded_sum'] is None
    assert not c['unknown_usage_imputed']
