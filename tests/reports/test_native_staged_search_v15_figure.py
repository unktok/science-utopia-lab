"""Explicit SCRIPTED figure/rejection contracts, never generated research data."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.figures.native_staged_search_v15 import (
    ACTUAL, COUNT_KEYS, FIXTURE, SCHEMA, _report, figure_data, objective_specs, render,
)
from utopia.optimization.loss import evaluate_loss
from utopia.system.design_patch import digest

SOURCES = ('a' * 40, 'b' * 40)


def seal(value):
    value['content_sha256'] = digest({k: v for k, v in value.items() if k != 'content_sha256'})
    return value


def fixture(revision, *, null=False, unknown=False, changed=False):
    """Deliberately synthetic compact schema contract; no simulator/model call."""
    inventory = {'SCRIPTED-only.json': digest('SCRIPTED original bytes')}
    value = {'schema': SCHEMA, 'classification': FIXTURE, 'source_commit': SOURCES[int(revision == 'a2')],
        'status': 'budget-complete-with-failures' if null or revision == 'a1' else 'complete',
        'budget_terminal': True, 'queue_terminal': True, 'planned_native_slots': 4, 'consumed_native_slots': 4,
        'exact_full_audit_reproducible': True, 'exact_full_audit_content_sha256': digest('SCRIPTED full audit'),
        'claims': {key: False for key in ('held_out', 'scientific_benefit_established',
            'designer_improvement_established', 'method_superiority_established', 'model_weights_trained',
            'full_world_pathwise_autograd', 'same_society_adoption')},
        'audit': {'exact_raw_tools_draft_source_definition_replayed': True,
            'own_history_loss_and_all_ties_replayed': True, 'new_model_calls': 0, 'new_container_executions': 0,
            'raw_input_sha256s': inventory, 'raw_inventory_sha256': digest(inventory),
            'raw_files_verified_unchanged': 1}, 'runs': {}}
    native = 0
    for arm, spec in objective_specs().items():
        generations, observations = [], []
        for index in range(2):
            valid = revision == 'a2' and not null
            identity = digest([revision, arm, index]); parent = digest(['SCRIPTED', arm, 'parent']) if not index else observations[0]['system_fingerprint'] or digest(['SCRIPTED', arm, 'parent'])
            system = digest(['SCRIPTED', arm, 'changed']) if index and changed else parent
            counts = {key: 0 for key in COUNT_KEYS}; counts.update(dispatch_intents=1,
                completed_step_receipts=int(not unknown), known_designer_responses=int(not unknown),
                known_HTTP_responses=int(not unknown), recorded_POST_attempts=int(not unknown),
                interrupted_response_unknown=int(unknown), valid_finished_generations=int(valid and not unknown))
            valid = valid and not unknown
            generation = {'generation': index, 'request_sha256': identity, 'status': 'generated' if valid else 'generation-failed',
                'exact_raw_tools_draft_finish_replayed': True, 'own_history_and_loss_prompt_replayed': True,
                'counts': counts, 'step_receipts': [{'step': 0, 'started_sha256': digest([identity, 'start']),
                    'completed_sha256': None if unknown else digest([identity, 'done']),
                    'status': 'interrupted-response-unknown' if unknown else 'finished' if valid else 'applied'}]}
            row = {'generation': index, 'record_index': index, 'slot': index, 'scheduled_native_slots': 1,
                'request_sha256': identity, 'status': 'complete' if valid else 'generation-failure',
                'loss': None, 'observation_id': f'SCRIPTED-{arm}-{index}' if valid else None,
                'checkpoint_sha256': digest([identity, 'checkpoint']) if valid else None,
                'system_fingerprint': system if valid else None}
            if revision == 'a2':
                generation.update(authoring_change={'valid_explicit_finish': valid, 'parent_document_sha256': parent,
                        'compiled_base_document_sha256': system if valid else None,
                        'explicit_exact_parent_retention': valid and system == parent},
                    own_scalar_outcomes_received=[{'observation_id': r['observation_id'],
                        'status': r['original_observation_status'], 'loss': r['original_observation_loss']}
                        for r in observations if r['observation_id'] is not None],
                    based_on_observation_id=observations[0]['observation_id'] if index else None)
            if valid:
                metrics = {'native.accepted_decisions': {'status': 'measured', 'value': 3 + index},
                    'native.accepted_peer_score_sum': {'status': 'measured', 'value': 7 + index * 2},
                    'native.review_records': {'status': 'measured', 'value': 2 + index}}
                row['native_A_Q_R'] = {key: metrics[metric] for key, metric in [('A', 'native.accepted_decisions'),
                    ('Q', 'native.accepted_peer_score_sum'), ('R', 'native.review_records')]}
                row['cross_scores'] = {loss['id']: evaluate_loss(loss, [{'run_id': row['observation_id'], 'metrics': metrics}])['loss']
                    for loss in objective_specs().values()}
                row['loss'] = row['cross_scores'][spec['id']]
                row['native_physical_counts'] = {'scientist_responses': 1, 'wire_requests': 1}
                native += 1
            if revision == 'a2':
                row.update(original_observation_status='complete' if valid else None,
                    original_observation_loss=row['loss'])
            generations.append(generation); observations.append(row)
        value['runs'][arm] = {'loss_spec': spec, 'terminal': True, 'queue_status': 'complete',
            'consumed_native_slots': 2, 'request_sha256': digest([revision, arm]),
            'runtime_plan_sha256': digest([revision, arm, 'plan']), 'generations': generations, 'observations': observations}
    value.update(physical_native_worlds=native, technical_failures=4 - native,
        completed_researcher_responses=native, physical_researcher_responses=native,
        designer_costs={'generations': 4, **{key: sum(g['counts'][key] for r in value['runs'].values() for g in r['generations']) for key in COUNT_KEYS}})
    return seal(value)


def data(a1=None, a2=None, **kwargs):
    return figure_data(a1 or fixture('a1'), a2 or fixture('a2'),
        expected_a1_source=SOURCES[0], expected_a2_source=SOURCES[1], allow_scripted=True, **kwargs)


def test_valid_actual_a1_summary_is_accepted_without_making_up_a2():
    report = json.loads((Path(__file__).resolve().parents[2] / 'research/results/native-staged-search-v15-a1.json').read_text())
    value = _report(report, 'f969f7cc2f88549ce12c5afbbbeba7b30f38828e', 'a1', allow_scripted=False)
    assert value['completed_native_worlds'] == 0 and value['designer_known'] == 64
    assert all(point['loss'] is None for points in value['paths'].values() for point in points)


def test_retention_changes_nulls_and_best_paths_are_literal_not_scientific_claims():
    value = data(a2=fixture('a2', changed=True))
    assert value['native_paths']['throughput'][0]['loss'] == -3
    assert value['native_paths']['throughput'][1]['best_loss_so_far'] == -4
    assert value['native_paths']['throughput'][0]['literal_relation_to_parent'] == 'same-parent'
    assert value['native_paths']['throughput'][1]['literal_relation_to_parent'] == 'changed-system'
    assert not value['held_out'] and not value['controlled_comparison']
    failed = data(a2=fixture('a2', null=True))
    assert failed['native_paths']['efficiency'][0]['loss'] is None
    assert failed['native_paths']['efficiency'][0]['best_loss_so_far'] is None
    assert data(a2=fixture('a2', unknown=True))['revisions'][1]['designer_unknown'] == 4


def test_measured_zero_is_not_conflated_with_null():
    report = fixture('a2')
    for arm, run in report['runs'].items():
        for row in run['observations']:
            for item in row['native_A_Q_R'].values(): item['value'] = 0
            row['cross_scores'] = {spec['id']: 0 for spec in objective_specs().values()}; row['loss'] = 0
            row['original_observation_loss'] = 0
        run['generations'][1]['own_scalar_outcomes_received'][0]['loss'] = 0
    assert data(a2=seal(report))['native_paths']['throughput'][0]['loss'] == 0


def test_unavailable_nonobjective_metric_is_not_imputed_to_zero():
    report = fixture('a2')
    for row in report['runs']['throughput']['observations']:
        row['native_A_Q_R']['Q'] = {'status': 'unavailable', 'value': None, 'reason': 'SCRIPTED unavailable'}
        row['cross_scores']['native-reviewed-production-efficiency-v13'] = None
    assert data(a2=seal(report))['native_paths']['throughput'][0]['loss'] == -3


def test_invalid_native_observation_original_scalar_is_not_a_valid_optimization_loss():
    report = fixture('a2'); run = report['runs']['throughput']; row = run['observations'][0]
    row.update(status='technical-failure', loss=None, original_observation_status='complete',
        original_observation_loss=123, cross_scores={spec['id']: None for spec in objective_specs().values()})
    run['generations'][1]['own_scalar_outcomes_received'] = [{'observation_id': row['observation_id'], 'status': 'complete', 'loss': 123}]
    run['generations'][1]['based_on_observation_id'] = None
    report.update(physical_native_worlds=3, technical_failures=1, completed_researcher_responses=3,
        physical_researcher_responses=4)
    values = data(a2=seal(report))
    assert values['native_paths']['throughput'][0]['loss'] is None
    assert values['native_paths']['throughput'][0]['best_loss_so_far'] is None
    assert values['revisions'][1]['physical_scientist_replies'] == 4


@pytest.mark.parametrize('mutation', ['content-hash', 'source', 'unclosed', 'budget', 'claim', 'inventory', 'tools',
    'history-proof', 'generation-request', 'step-hash', 'unknown-reply', 'designer-cost', 'native-cost',
    'null-penalty', 'nonfinite', 'own-feedback', 'parent', 'metric', 'cross-score', 'retention'])
def test_rehashed_malformed_or_borrowed_data_is_rejected(mutation):
    report = fixture('a2'); run = report['runs']['throughput']; generation = run['generations'][1]; row = run['observations'][1]
    if mutation == 'content-hash': report['content_sha256'] = 'forged'
    elif mutation == 'source': report['source_commit'] = 'c' * 40
    elif mutation == 'unclosed': report['budget_terminal'] = False
    elif mutation == 'budget': report['consumed_native_slots'] = 5
    elif mutation == 'claim': report['claims']['held_out'] = True
    elif mutation == 'inventory': report['audit']['raw_inventory_sha256'] = '0' * 64
    elif mutation == 'tools': report['audit']['exact_raw_tools_draft_source_definition_replayed'] = False
    elif mutation == 'history-proof': generation['own_history_and_loss_prompt_replayed'] = False
    elif mutation == 'generation-request': row['request_sha256'] = '0' * 64
    elif mutation == 'step-hash': generation['step_receipts'][0]['started_sha256'] = 'bad'
    elif mutation == 'unknown-reply': generation['step_receipts'][0]['completed_sha256'] = None
    elif mutation == 'designer-cost': report['designer_costs']['known_designer_responses'] = 99
    elif mutation == 'native-cost': report['physical_native_worlds'] = 0
    elif mutation == 'null-penalty': row.update(status='generation-failure', loss=0)
    elif mutation == 'nonfinite': row['loss'] = float('inf')
    elif mutation == 'own-feedback': generation['own_scalar_outcomes_received'][0]['observation_id'] = 'SCRIPTED-efficiency-0'
    elif mutation == 'parent': generation['based_on_observation_id'] = None
    elif mutation == 'metric': row['native_A_Q_R']['A']['value'] = 999
    elif mutation == 'cross-score': row['cross_scores'][run['loss_spec']['id']] = 999
    elif mutation == 'retention': row['system_fingerprint'] = 'c' * 64
    if mutation not in {'content-hash', 'nonfinite'}: seal(report)
    with pytest.raises((ValueError, KeyError)): data(a2=report)


def test_actual_mode_refuses_scripted_or_mixed_labels():
    with pytest.raises(ValueError, match='actual evidence'):
        figure_data(fixture('a1'), fixture('a2'), expected_a1_source=SOURCES[0], expected_a2_source=SOURCES[1])
    forged = fixture('a2'); forged['classification'] = ACTUAL; seal(forged)
    with pytest.raises(ValueError, match='actual evidence'): data(a2=forged)


def test_scripted_render_is_clearly_labelled_vector_and_tracks_exact_inputs(tmp_path):
    reports = [fixture('a1'), fixture('a2', changed=True)]; paths = [tmp_path / 'a1.json', tmp_path / 'a2.json']
    for path, report in zip(paths, reports): path.write_text(json.dumps(report))
    manifest = render(*reports, tmp_path / 'SCRIPTED-v15-contract', expected_a1_source=SOURCES[0],
        expected_a2_source=SOURCES[1], a1_path=paths[0], a2_path=paths[1], allow_scripted=True)
    svg = (tmp_path / 'SCRIPTED-v15-contract.svg').read_text()
    assert 'SCRIPTED CONTRACT FIXTURE - NOT NATIVE RESULTS' in svg
    assert 'not a controlled comparison' in svg and 'Retention is not invented code' in svg
    assert manifest['width_inches'] == 5.5 and len(manifest['files']) == 3
    assert manifest['content_sha256'] == digest({k: v for k, v in manifest.items() if k != 'content_sha256'})
    assert manifest['data']['classification'] == FIXTURE


def test_closed_actual_a2_paths_and_costs_join_independent_audits():
    root = Path(__file__).resolve().parents[2]
    reports = [json.loads((root / f'research/results/native-staged-search-v15-{revision}.json').read_text())
        for revision in ('a1', 'a2')]
    values = figure_data(*reports,
        expected_a1_source='f969f7cc2f88549ce12c5afbbbeba7b30f38828e',
        expected_a2_source='51d9cbbd49054cdb89c24ea5bc192ff9b63e9155')
    assert [p['loss'] for p in values['native_paths']['throughput']] == [-1, -1]
    assert [p['loss'] for p in values['native_paths']['efficiency']] == [8, 8]
    assert {p['literal_relation_to_parent'] for path in values['native_paths'].values() for p in path} == {'same-parent'}
    assert [r['completed_native_worlds'] for r in values['revisions']] == [0, 4]
    assert [r['physical_scientist_replies'] for r in values['revisions']] == [0, 368]
    assert values['controlled_comparison'] is values['held_out'] is False
