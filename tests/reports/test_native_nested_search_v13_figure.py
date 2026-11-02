"""Temporary watermarked plot contracts; never native scientific evidence."""
from copy import deepcopy
import json
from pathlib import Path
import warnings
import xml.etree.ElementTree as ET

import matplotlib
from matplotlib.figure import Figure
import pytest

from scripts.analyze_native_nested_search_v13 import (
    ARM_IDS, SCHEMA, FIXTURE, design_change, executable_contracts, objective_specs)
from scripts.figures.native_nested_search_v13 import figure_data, render, _incumbents
from scripts.native_nested_estimator_audit_v13 import conditional_update_proof
from tests.optimization.test_native_adaptive_search import tiny_definition, tiny_parent
from utopia.optimization.blackbox import Observation
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.optimization.native_nested_search import NativeNestedDesignCampaign, STAGES
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic


def seal(value):
    value.pop('content_sha256', None)
    value['content_sha256'] = digest(value)
    return value


def fixture(tmp_path, monkeypatch, *, invalid=False, failed=False):
    losses, arms = objective_specs(), {}
    world = {'source_commit': 'fixture-source', 'model_digest': 'fixture-only', 'corpus_sha256': 'fixture-only'}
    for arm_index, identity in enumerate(ARM_IDS):
        index = []
        def evaluate(suggestion, **kwargs):
            slot = len(index)
            index.append(slot)
            metrics = {key: {'status': 'measured', 'value': value} for key, value in (
                ('native.accepted_decisions', slot+1), ('native.accepted_peer_score_sum', 3.*(slot+1)),
                ('native.review_records', slot+4))}
            measurement = {'run_id': suggestion.suggestion_id+'-s42', 'metrics': metrics}
            evaluation = evaluate_loss(losses[identity], [] if failed else [measurement])
            return Observation('observation-'+suggestion.suggestion_id, suggestion.suggestion_id,
                suggestion.candidate, evaluation['status'] if evaluation['status'] == 'complete' else 'failed',
                evaluation['loss'] if evaluation['status'] == 'complete' else None,
                {'world_backend': 'native-research-world', 'loss_spec_sha256': loss_spec_sha256(losses[identity]),
                    'measurements': [] if failed else [measurement], 'loss_evaluation': evaluation,
                    'technical_failures': [{'loss': None}] if failed else []})
        with monkeypatch.context() as context:
            context.setattr('utopia.optimization.native_nested_search.evaluate_native_suggestion', evaluate)
            context.setattr(NativeNestedDesignCampaign, '_check_observation', lambda *args: None)
            controller = NativeNestedDesignCampaign(tmp_path/identity, initial_system=tiny_parent(),
                loss_spec=losses[identity], seeds=[42], world_binding=world)
            for _ in STAGES:
                controller.advance(simulation_factory=None,
                    generator=lambda request: {'invalid': 'fixture null vocabulary'} if invalid else tiny_definition())
        rows = []
        for record in controller.state['records']:
            pairs = [(None, None)] if record['generation_error'] else zip(record['draws'], record['observations'])
            for draw_index, (draw, observation) in enumerate(pairs):
                system = draw['suggestion']['candidate'] if draw else None
                metrics = observation['metadata']['measurements'][0]['metrics'] if observation and not failed else None
                cross = {key: evaluate_loss(loss, [{'run_id': 'fixture-only', 'metrics': metrics}])['loss']
                    for key, loss in losses.items()} if metrics else {key: None for key in ARM_IDS}
                own = cross[identity]
                proof = None if own is None else {
                    'checkpoint_sha256': 'a'*64, 'native_loss': own,
                    'measurement': observation['metadata']['measurements'][0],
                    'native_counts': {'kernel_restored_without_execution': True, 'migration_receipts': 0},
                    'code_proof': {'recorded_executions': 0},
                    'response_proof': {'wire_requests': 1, 'researcher_responses': 1},
                    'capability_effect_proof': {'annual': [], 'complete_plan_effect_count': 0,
                        'routing_event_count': 0, 'routed_actual_review_count': 0}}
                rows.append({'arm': identity, 'stage': record['stage'], 'generation': record['generation'],
                    'draw_index': draw_index if draw else None, 'draw': clone(draw), 'observation': clone(observation),
                    'generation_error': clone(record['generation_error']),
                    'scheduled_native_slots': 1 if draw else record['request']['count'],
                    'version_sha256': record['version_sha256'], 'system': system,
                    'system_fingerprint': SystemSpec.from_dict(system).fingerprint if draw else None,
                    'contracts': executable_contracts(system) if system else None,
                    'parent_system_fingerprint': SystemSpec.from_dict(record['request']['parent_system']).fingerprint,
                    'lineage': {'vs_parent': design_change(record['request']['parent_system'], system)} if system else None,
                    'observation_id': observation['observation_id'] if observation else None,
                    'status': 'generation-failure' if record['generation_error'] else 'technical-failure' if failed else 'complete',
                    'own_loss': own, 'loss': own, 'cross_scores': cross, 'metrics': metrics,
                    'checkpoint_sha256': 'a'*64 if own is not None else None, 'physical_proof': proof})
        arms[identity] = {'objective_id': identity, 'loss_spec': losses[identity], 'records': clone(controller.state['records']),
            'pending': None, 'observations': rows, 'incumbents': _incumbents(rows),
            'conditional_update_proof': conditional_update_proof(controller.state['records'])}
    completed = 0 if invalid or failed else 8
    return seal({'schema': SCHEMA, 'classification': FIXTURE, 'status': 'complete' if completed == 8 else 'budget-complete-with-failures',
        'source_commit': 'fixture-source', 'objective_order': list(ARM_IDS), 'loss_specs': losses, 'arms': arms,
        'planned_native_world_budget': 8, 'consumed_native_slots': 8,
        'physical_native_worlds': completed, 'logical_completed_draws': completed,
        'physical_researcher_responses': completed, 'logical_completed_researcher_responses': completed,
        'completed_code_executions': 0, 'completed_wire_requests': completed, 'reused_responses_in_completed_worlds': 0,
        'claims': {'live_fixed_Qwen_researchers': False, 'scripted_researcher_HTTP': True,
            **{key: False for key in ('held_out', 'causal_institutional_benefit', 'scientific_value',
                'designer_improvement_established', 'full_native_world_pathwise_autograd',
                'external_authorship_authenticated', 'variance_reduction_established')}},
        'audit': {'raw_inventory_sha256': 'b'*64, 'new_model_calls': 0, 'new_container_executions': 0,
            **{key: True for key in ('checkpoint_loss_reextracted', 'campaign_and_lineage_replayed', 'own_history_only_verified',
                'all_observations_and_exact_ties_retained', 'sole_conditional_LR_update_analytically_rederived')}}})


def test_watermarked_temporary_contract_has_exact_nested_paths_and_unscaled_fonts(tmp_path, monkeypatch):
    report = fixture(tmp_path/'fixture', monkeypatch)
    with pytest.raises(ValueError, match='synthetic'):
        figure_data(report, 'fixture-source')
    figures, original = [], Figure.savefig
    def save(figure, path, *args, **kwargs):
        if Path(path).suffix == '.png':
            figures.append(figure)
        return original(figure, path, *args, **kwargs)
    monkeypatch.setattr(Figure, 'savefig', save)
    audit = tmp_path/'TEST-ONLY-audit.json'
    write_json_atomic(audit, report)
    manifest = render(report, tmp_path/'TEST-ONLY-figure', audit_path=audit,
        expected_source='fixture-source', allow_synthetic=True)
    assert len(manifest['files']) == 2 and len(figures) == 1
    figure = figures[0]
    assert tuple(figure.get_size_inches()) == (5.5, 7.8) and len(figure.axes) == 6
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    for axis in figure.axes:
        texts = [axis.title, axis.xaxis.label, axis.yaxis.label,
            *axis.get_xticklabels(), *axis.get_yticklabels(), *axis.texts]
        texts.extend(cell.get_text() for table in axis.tables for cell in table.get_celld().values())
        assert all(text.get_fontsize() >= 7 for text in texts if text.get_text())
        title = axis.title.get_window_extent(renderer)
        assert title.y0 >= axis.get_window_extent(renderer).y1
        assert title.x0 >= 0 and title.x1 <= figure.bbox.x1
        for table in axis.tables:
            cells = [cell.get_window_extent(renderer) for cell in table.get_celld().values()]
            assert title.y0 > max(box.y1 for box in cells)
            assert min(box.x0 for box in cells) >= 0
            if axis.texts:
                assert min(box.y0 for box in cells) > max(text.get_window_extent(renderer).y1 for text in axis.texts)
    svg = (tmp_path/'TEST-ONLY-figure.svg').read_text()
    assert 'SYNTHETIC CONTRACT FIXTURE' in svg and 'NOT EVIDENCE' in svg
    assert 'Same-world cross-scores' in svg and 'not held-out' in svg
    assert [row['slot'] for row in manifest['data']['rows'][ARM_IDS[0]]] == [0,1,2,3]
    assert manifest['data']['policy'][ARM_IDS[0]]['mean_step_l2'] > 0
    with pytest.raises(ValueError, match='temporary'):
        render(report, '/Users/shiro/no-fixture-publication', audit_path=audit,
            expected_source='fixture-source', allow_synthetic=True)


@pytest.mark.parametrize('tamper', ['hash', 'loss', 'cross', 'own', 'source', 'contract', 'lineage',
    'native', 'route-count', 'worlds', 'replies', 'claim', 'update-proof', 'weights', 'likelihood', 'history', 'slot', 'incumbent'])
def test_rehashed_wrong_losses_native_effects_weights_history_and_lineage_fail_closed(tmp_path, monkeypatch, tamper):
    report = fixture(tmp_path/'fixture', monkeypatch)
    arm = report['arms'][ARM_IDS[0]]
    row = arm['observations'][0]
    if tamper == 'hash': report['content_sha256'] = 'f'*64
    elif tamper == 'loss': report['loss_specs'][ARM_IDS[0]]['per_run']['terms'][0]['coefficient'] = -999.
    elif tamper == 'cross': row['cross_scores'][ARM_IDS[1]] = -999.
    elif tamper == 'own': row['loss'] = row['own_loss'] = -999.
    elif tamper == 'source': row['system']['initial_state']['coordinate'] = -999.
    elif tamper == 'contract': row['contracts']['schedules'] = []
    elif tamper == 'lineage': row['lineage']['vs_parent']['counts']['edges_added'] = 999
    elif tamper == 'native': row['physical_proof']['native_loss'] = -999.
    elif tamper == 'route-count': row['physical_proof']['capability_effect_proof']['routed_actual_review_count'] = 999
    elif tamper == 'worlds': report['physical_native_worlds'] = 9
    elif tamper == 'replies': report['physical_researcher_responses'] = 999
    elif tamper == 'claim': report['claims']['variance_reduction_established'] = True
    elif tamper == 'update-proof': arm['conditional_update_proof']['updates'] = 99
    elif tamper == 'weights': arm['records'][0]['report']['weights_after']['continuous_mean'][0] += 99.
    elif tamper == 'likelihood': arm['records'][0]['draws'][0]['conditional_latent_log_probability'] += 99.
    elif tamper == 'history': arm['records'][2]['request']['history'] = []
    elif tamper == 'slot': row['scheduled_native_slots'] = 2
    elif tamper == 'incumbent': arm['incumbents']['best_loss'] = -999.
    if tamper != 'hash': seal(report)
    with pytest.raises(ValueError):
        figure_data(report, 'fixture-source', allow_synthetic=True)


@pytest.mark.parametrize('invalid', [False, True])
def test_null_native_or_generation_slots_never_become_zero_losses(tmp_path, monkeypatch, invalid):
    report = fixture(tmp_path/'fixture', monkeypatch, invalid=invalid, failed=not invalid)
    audit = tmp_path/'TEST-ONLY-null-audit.json'
    write_json_atomic(audit, report)
    with warnings.catch_warnings():
        warnings.simplefilter('error')
        manifest = render(report, tmp_path/'TEST-ONLY-null-figure', audit_path=audit,
            expected_source='fixture-source', allow_synthetic=True)
    assert all(row['own_loss'] is row['incumbent_loss'] is None for rows in manifest['data']['rows'].values() for row in rows)
    assert [r['slot_span'] for r in manifest['data']['rows'][ARM_IDS[0]]] == ([2,1,1] if invalid else [1,1,1,1])
    assert 'No completed native loss' in (tmp_path/'TEST-ONLY-null-figure.svg').read_text()


@pytest.mark.parametrize('fonttype', ['path', 'none'])
def test_rcparams_and_serialization_are_isolated_and_restored(tmp_path, monkeypatch, fonttype):
    report = fixture(tmp_path/'fixture', monkeypatch)
    audit = tmp_path/'TEST-ONLY-audit.json'
    write_json_atomic(audit, report)
    first = render(report, tmp_path/'TEST-ONLY-first', audit_path=audit,
        expected_source='fixture-source', allow_synthetic=True)
    ambient = {'font.family': ['DejaVu Serif'], 'font.size': 31., 'svg.fonttype': fonttype,
        'svg.hashsalt': 'unrelated-salt', 'axes.facecolor': 'magenta', 'savefig.facecolor': 'yellow'}
    with matplotlib.rc_context(ambient):
        second = render(report, tmp_path/'TEST-ONLY-second', audit_path=audit,
            expected_source='fixture-source', allow_synthetic=True)
        assert all(matplotlib.rcParams[key] == value for key,value in ambient.items())
    assert [f['sha256'] for f in first['files']] == [f['sha256'] for f in second['files']]


def test_exact_audit_file_and_actual_flag_are_not_fixture_escape_hatches(tmp_path, monkeypatch):
    report = fixture(tmp_path/'fixture', monkeypatch)
    audit = tmp_path/'unrelated.json'
    write_json_atomic(audit, {'not': 'this report'})
    with pytest.raises(ValueError, match='exact supplied audit'):
        render(report, tmp_path/'TEST-ONLY-figure', audit_path=audit,
            expected_source='fixture-source', allow_synthetic=True)
    report['classification'] = 'actual-native-qwen-nested-search-development-v13'
    seal(report)
    with pytest.raises(ValueError, match='synthetic'):
        figure_data(report, 'fixture-source', allow_synthetic=True)
