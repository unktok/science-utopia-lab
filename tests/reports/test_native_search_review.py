"""Offline retrospective selection is not new optimization or new execution."""
from copy import deepcopy
import json
import socket
import subprocess

import pytest

from scripts.review_native_search import INPUT_SCHEMA, main, review_summary
from utopia.system.design_patch import digest

SOURCE = 'a' * 40
AUDIT = 'b' * 64
T = 'native-joint-v5-throughput'
E = 'native-reviewed-production-efficiency-v13'


def rehash(value):
    value['content_sha256'] = digest({k: v for k, v in value.items() if k != 'content_sha256'})
    return value


def loss(identity, terms):
    return {'schema': 'scienceutopia.loss-spec.v1', 'id': identity, 'version': '1',
        'status': 'SCRIPTED', 'optimization_seed_role': 'development', 'direction': 'minimize',
        'per_run': {'intercept': 0., 'terms': [{'metric_id': metric, 'slice_id': None,
            'coefficient': coefficient} for metric, coefficient in terms]},
        'across_seeds': {'aggregation': 'mean_plus_population_sd',
            'dispersion_weight': 0., 'minimum_valid_runs': 1}}


def row(slot, *, status='complete', accepted=0, quality=0., reviews=24, arm='efficiency'):
    complete = status == 'complete'
    scores = {T: -float(accepted), E: -quality + .5 * reviews} if complete else {T: None, E: None}
    return {'slot': slot, 'generation': slot, 'status': status,
        'loss': scores[E if arm == 'efficiency' else T],
        'original_observation_status': 'complete' if complete else None,
        'original_observation_loss': scores[E if arm == 'efficiency' else T],
        'cross_scores': scores, 'observation_id': f'SCRIPTED-{arm}-{slot}',
        'system_fingerprint': f'SCRIPTED-system-{arm}-{slot}', 'checkpoint_sha256': 'c' * 64,
        'native_A_Q_R': {k: {'status': 'measured', 'value': v} for k, v in
            [('A', accepted), ('Q', quality), ('R', reviews)]} if complete else {k: None for k in 'AQR'}}


def fixture():
    return rehash({'schema': INPUT_SCHEMA, 'source_commit': SOURCE,
        'exact_full_audit_content_sha256': AUDIT, 'budget_terminal': True, 'queue_terminal': True,
        'consumed_native_slots': 4, 'planned_native_slots': 4,
        'physical_native_worlds': 3, 'physical_researcher_responses': 100,
        'designer_costs': {'SCRIPTED': True}, 'audit': {
            'exact_raw_tools_draft_source_definition_replayed': True,
            'own_history_loss_and_all_ties_replayed': True,
            'source_proofs': {'status': 'verified-exact-staged-runtime-driver-helper-source-blobs'}},
        'runs': {'efficiency': {'loss_spec': loss(E, [('native.accepted_peer_score_sum', -1.),
                ('native.review_records', .5)]),
            'observations': [row(0), row(1, status='technical-failure'), row(2, status='generation-failure')]},
            'throughput': {'loss_spec': loss(T, [('native.accepted_decisions', -1.)]),
                'observations': [row(0, arm='throughput', accepted=7, quality=67/3, reviews=21)]}}})


@pytest.fixture(autouse=True)
def no_backend_or_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('review must not call a backend or execute any source')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)


def review(value):
    return review_summary(value, expected_source=SOURCE, expected_full_audit=AUDIT)


def test_same_archived_measurements_reveal_pool_gap_without_new_improvement():
    value = fixture(); before = deepcopy(value)
    result = review(value)
    assert result == review(value) and value == before
    assert result['status_counts'] == {'complete': 2, 'generation-failure': 1, 'technical-failure': 1}
    selected = result['selection']['efficiency']
    assert selected['original_arm_observed_best']['loss'] == 12.
    assert selected['retrospective_pooled_best']['loss'] == pytest.approx(-11.833333333333332)
    assert selected['retrospective_pool_gap'] == pytest.approx(23.833333333333332)
    assert result['selection']['throughput']['retrospective_pool_gap'] == 0.
    assert selected['retrospective_pooled_best']['ties'] == ['throughput:slot-0']
    for key in ('new_model_calls', 'new_world_executions', 'new_code_executions'):
        assert result[key] == 0
    for key in ('fresh_raw_audit', 'held_out', 'new_optimization_run',
            'new_institution_invented', 'historical_feedback_modified'):
        assert result[key] is False
    assert all(all(v is None for v in r['scores'].values())
        for r in result['rows'] if r['status'] != 'complete')


@pytest.mark.parametrize('change,message', [
    (lambda v: v.update(source_commit='d' * 40), 'binding'),
    (lambda v: v.update(exact_full_audit_content_sha256='e' * 64), 'binding'),
    (lambda v: v.update(queue_terminal=False), 'terminal'),
    (lambda v: v.update(consumed_native_slots=3), 'counts'),
    (lambda v: v['audit'].update(own_history_loss_and_all_ties_replayed=False), 'incomplete'),
    (lambda v: v['runs']['efficiency']['observations'][1].update(loss=1000.), 'numerical loss'),
    (lambda v: v['runs']['efficiency']['observations'][0]['cross_scores'].update({E: -100.}), 'cross-score'),
    (lambda v: v['runs']['efficiency']['observations'][0].update(original_observation_loss=0.), 'own loss'),
    (lambda v: v['runs']['efficiency']['observations'][0]['native_A_Q_R']['Q'].update(status='unknown'), 'unmeasured'),
    (lambda v: v['runs']['efficiency']['observations'][0]['native_A_Q_R']['Q'].update(value=True), 'unmeasured'),
    (lambda v: v['runs']['efficiency']['loss_spec']['across_seeds'].update(minimum_valid_runs=2), 'single-world'),
])
def test_invalid_or_reinterpreted_evidence_is_rejected(change, message):
    value = fixture(); change(value); rehash(value)
    with pytest.raises(ValueError, match=message):
        review(value)


def test_unhashed_edit_is_not_accepted():
    value = fixture(); value['physical_native_worlds'] = 100
    with pytest.raises(ValueError, match='content hash'):
        review(value)


def test_all_exact_ties_and_reused_checkpoints_remain_logical_records_not_iid_worlds():
    value = fixture()
    duplicate = deepcopy(value['runs']['throughput']['observations'][0]); duplicate['slot'] = 1
    value['runs']['throughput']['observations'].append(duplicate)
    value['planned_native_slots'] += 1; value['consumed_native_slots'] += 1; rehash(value)
    result = review(value)
    assert result['physical_native_worlds'] == 3
    assert result['logical_slots'] == 5
    assert result['selection']['efficiency']['retrospective_pooled_best']['ties'] == [
        'throughput:slot-0', 'throughput:slot-1']
    duplicate['slot'] = 0; rehash(value)
    with pytest.raises(ValueError, match='duplicate logical slot'):
        review(value)


def test_all_failed_arm_has_no_imputed_best_or_gap():
    value = fixture(); value['runs']['efficiency']['observations'][0] = row(0, status='technical-failure')
    rehash(value); selected = review(value)['selection']['efficiency']
    assert selected['original_arm_observed_best'] == {'loss': None, 'ties': []}
    assert selected['retrospective_pool_gap'] is None


def test_cli_is_read_only_and_refuses_overwriting_input_or_output(tmp_path):
    source = tmp_path/'input.json'; output = tmp_path/'review.json'
    source.write_text(json.dumps(fixture()))
    before = source.read_bytes()
    argv = ['--summary', str(source), '--expected-source', SOURCE,
        '--expected-full-audit', AUDIT, '--output', str(output)]
    assert main(argv) == 0 and source.read_bytes() == before
    saved = output.read_bytes(); value = json.loads(saved)
    assert value['content_sha256'] == digest({k: v for k, v in value.items() if k != 'content_sha256'})
    with pytest.raises(ValueError, match='overwrite'):
        main(argv)
    assert source.read_bytes() == before and output.read_bytes() == saved
    with pytest.raises(ValueError, match='overwrite'):
        main(argv[:-1] + [str(source)])
