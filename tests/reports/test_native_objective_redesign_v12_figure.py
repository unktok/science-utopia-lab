"""Explicit synthetic-only plot guards, not simulated or model evidence."""
from copy import deepcopy
import json
import warnings

import pytest

from scripts.analyze_native_objective_redesign_v12 import (
    ACTUAL, ARM_IDS, FIXTURE, SCHEMA, design_change, executable_contracts, objective_specs,
)
from scripts.analyze_native_open_estimators_v11 import incumbent_path
from scripts.figures.native_objective_redesign_v12 import figure_data, render
from tests.reports.test_native_objective_structure_v8_audit import system
from utopia.optimization.loss import evaluate_loss
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def seal(value):
    value.pop('content_sha256', None)
    value['content_sha256'] = digest(value)
    return value


def fixture():
    spec = system()
    losses = objective_specs()
    arms = {}
    for arm_index, identity in enumerate(ARM_IDS):
        rows, records = [], []
        for generation in range(3):
            metrics = {'native.accepted_decisions': {'status': 'measured', 'value': generation+1},
                'native.accepted_peer_score_sum': {'status': 'measured', 'value': 4.*(generation+1)},
                'native.review_records': {'status': 'measured', 'value': 12}}
            cross = {key:evaluate_loss(loss, [{'run_id': 'synthetic-fixture', 'metrics': metrics}])['loss'] for key,loss in losses.items()}
            rows.append({'arm': identity, 'generation': generation, 'draw_index': 0,
                'observation_id': f'synthetic-{arm_index}-{generation}', 'own_loss': cross[identity], 'loss': cross[identity],
                'cross_scores': cross, 'status': 'complete', 'metrics': metrics,
                'checkpoint_sha256': 'a'*64, 'system': spec.to_dict(), 'system_fingerprint': spec.fingerprint,
                'contracts': executable_contracts(spec.to_dict()), 'parent_system_fingerprint': spec.fingerprint,
                'lineage': {'vs_parent': design_change(spec.to_dict(), spec.to_dict()),
                    'vs_initial': design_change(spec.to_dict(), spec.to_dict())}})
            records.append({'request': {'parent_system': spec.to_dict()}})
        arms[identity] = {'objective_id': identity, 'loss_spec': losses[identity],
            'records': records, 'pending': None, 'observations': rows, 'incumbents': incumbent_path(rows)}
    return seal({'schema': SCHEMA, 'classification': FIXTURE, 'status': 'complete',
        'source_commit': 'fixture-source', 'objective_order': list(ARM_IDS), 'loss_specs': losses,
        'arms': arms, 'physical_native_worlds': 6, 'logical_completed_draws': 6,
        'physical_researcher_responses': 42, 'reused_responses_in_completed_worlds': 0,
        'claims': {'live_fixed_Qwen_researchers': False, 'scripted_researcher_HTTP': True,
            'held_out': False, 'causal_institutional_benefit': False, 'scientific_value': False,
            'designer_improvement_established': False, 'full_native_world_pathwise_autograd': False,
            'external_authorship_authenticated': False},
        'audit': {'raw_inventory_sha256': 'b'*64, 'new_model_calls': 0, 'new_container_executions': 0,
            'checkpoint_loss_reextracted': True, 'campaign_and_lineage_replayed': True,
            'all_observations_and_exact_ties_retained': True, 'own_history_only_verified': True}})


def test_synthetic_plot_is_explicitly_opted_in_and_kept_in_temp(tmp_path):
    report = fixture()
    with pytest.raises(ValueError, match='synthetic'):
        figure_data(report, 'fixture-source')
    result = figure_data(report, 'fixture-source', allow_synthetic=True)
    assert len(result['rows'][ARM_IDS[0]]) == 3
    audit = tmp_path / 'audit.json'
    write_json_atomic(audit, report)
    manifest = render(report, tmp_path / 'figure', audit_path=audit,
        expected_source='fixture-source', allow_synthetic=True)
    assert len(manifest['files']) == 2
    svg = (tmp_path / 'figure.svg').read_text()
    assert 'SYNTHETIC CONTRACT FIXTURE' in svg
    assert 'Same-checkpoint objective profiles' in svg
    assert 'held-out' in svg
    with pytest.raises(ValueError, match='temporary'):
        render(report, '/Users/shiro/forbidden-fixture-output', audit_path=audit,
            expected_source='fixture-source', allow_synthetic=True)


@pytest.mark.parametrize('tamper', ['content', 'loss-coefficient', 'crossscore', 'ownloss', 'tie',
    'source', 'contract', 'parent', 'lineage', 'worlds', 'claim', 'audit', 'identity'])
def test_rehashed_render_input_tampering_rejected(tamper):
    report = fixture()
    row = report['arms'][ARM_IDS[0]]['observations'][0]
    if tamper == 'content':
        row['own_loss'] = 9.
    elif tamper == 'loss-coefficient':
        report['loss_specs'][ARM_IDS[0]]['per_run']['terms'][0]['coefficient'] = -100.
    elif tamper == 'crossscore': row['cross_scores'][ARM_IDS[1]] = 999.
    elif tamper == 'ownloss': row['own_loss'] = row['loss'] = 99.
    elif tamper == 'tie': report['arms'][ARM_IDS[0]]['incumbents']['best_loss'] = -999.
    elif tamper == 'source': row['system']['mechanisms'][0]['parameters']['code_artifact']['source'] += '# forged\n'
    elif tamper == 'contract': row['contracts']['executable_sources']['source']['source_sha256'] = 'c'*64
    elif tamper == 'parent': row['parent_system_fingerprint'] = 'c'*64
    elif tamper == 'lineage': row['lineage']['vs_parent']['counts']['edges_added'] = 99
    elif tamper == 'worlds': report['physical_native_worlds'] = 7
    elif tamper == 'claim': report['claims']['held_out'] = True
    elif tamper == 'audit': report['audit']['new_model_calls'] = 1
    elif tamper == 'identity': row['observation_id'] = report['arms'][ARM_IDS[0]]['observations'][1]['observation_id']
    if tamper != 'content': seal(report)
    with pytest.raises(ValueError):
        figure_data(report, 'fixture-source', allow_synthetic=True)


def test_failed_attempt_is_retained_as_null_not_assigned_zero():
    report = fixture()
    arm = report['arms'][ARM_IDS[0]]
    row = arm['observations'][1]
    row.update(status='technical-failure', own_loss=None, loss=None, metrics=None,
        cross_scores={key:None for key in ARM_IDS})
    arm['incumbents'] = incumbent_path(arm['observations'])
    report.update(status='budget-complete-with-failures', physical_native_worlds=5, logical_completed_draws=5)
    seal(report)
    result = figure_data(report, 'fixture-source', allow_synthetic=True)
    assert result['rows'][ARM_IDS[0]][1]['own_loss'] is None
    assert result['rows'][ARM_IDS[0]][1]['incumbent_loss'] == -1.


def test_actual_flag_cannot_be_used_as_fixture_escape_hatch():
    report = fixture()
    report['classification'] = 'actual-native-qwen-objective-redesign-development-v12'
    seal(report)
    with pytest.raises(ValueError, match='synthetic'):
        figure_data(report, 'fixture-source', allow_synthetic=True)


def zero_reply_failure_contract():
    """Fabricated zero-execution test contract; not an actual run/audit receipt.

    Its source-proof status is deliberately a stub so the render boundary can
    be tested without inventing a Qwen reply, checkpoint or source execution.
    This fixture stays only in pytest temporary output.
    """
    report = fixture()
    report.update(classification=ACTUAL, source_commit='a'*40,
        status='budget-complete-with-failures', physical_native_worlds=0,
        logical_completed_draws=0, physical_researcher_responses=0)
    report['claims'].update(live_fixed_Qwen_researchers=False, scripted_researcher_HTTP=False)
    report['audit']['replay_source_proofs'] = {
        'status': 'verified-exact-replay-source-blobs',
        'scope': 'TEST-ONLY SOURCE-PROOF STUB; NO ACTUAL RUN OR MODEL EVIDENCE'}
    for arm in report['arms'].values():
        for row in arm['observations']:
            row.update(status='generation-failure', own_loss=None, loss=None,
                cross_scores={key:None for key in ARM_IDS}, observation_id=None,
                system=None, system_fingerprint=None, contracts=None, lineage=None,
                metrics=None, checkpoint_sha256=None)
        arm['incumbents'] = incumbent_path(arm['observations'])
    return seal(report)


def test_zero_reply_actual_failure_contract_retains_nulls_and_renders_all_missing_matrix_without_warning(tmp_path):
    report = zero_reply_failure_contract()
    data = figure_data(report, 'a'*40)
    assert data['physical_researcher_responses'] == 0
    assert all(row['own_loss'] is row['incumbent_loss'] is row['lineage'] is None
        for rows in data['rows'].values() for row in rows)
    audit = tmp_path / 'TEST-ONLY-zero-execution-contract.json'
    write_json_atomic(audit, report)
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        manifest = render(report, tmp_path / 'TEST-ONLY-zero-execution-figure',
            audit_path=audit, expected_source='a'*40)
    assert manifest['data']['physical_researcher_responses'] == 0
    svg = (tmp_path / 'TEST-ONLY-zero-execution-figure.svg').read_text()
    assert svg.count('No completed native loss') == 2
    assert 'No completed cross-scores' in svg
    assert svg.count('<!-- n/a -->') == 24
    report['claims']['live_fixed_Qwen_researchers'] = True
    seal(report)
    with pytest.raises(ValueError, match='attribution'):
        figure_data(report, 'a'*40)
    report['claims']['live_fixed_Qwen_researchers'] = False
    report['status'] = 'complete'
    seal(report)
    with pytest.raises(ValueError, match='terminal status'):
        figure_data(report, 'a'*40)


@pytest.mark.parametrize('replies', [None, -1, 1.5, True])
def test_invalid_physical_response_counts_are_not_coerced(replies):
    report = fixture()
    report['physical_researcher_responses'] = replies
    seal(report)
    with pytest.raises(ValueError, match='physical response count'):
        figure_data(report, 'fixture-source', allow_synthetic=True)
