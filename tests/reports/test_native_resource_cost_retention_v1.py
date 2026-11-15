"""Actual retained diagnostic evidence, not new world replications."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pytest

from scripts.reports.native_resource_cost_paper_v1 import summarize
from scripts.reports.native_resource_cost_v1 import SCOPES, measure_world
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data/native-resource-cost-development-v1'


def read(path):
    return checked(json.loads(path.read_text()))


def reports():
    return [read(DATA / name) for name in ('longitudinal-report.json', 'choice-controls-report.json')]


def test_actual_paired_reports_and_reviewed_figure_are_bound_and_preserved():
    receipt = read(ROOT / 'research/results/native-resource-cost-development-retention-v1.json')
    assert len(receipt['paired_original_source_exports']) == 2
    for row in receipt['paired_original_source_exports']:
        raw = (ROOT / row['retained']).read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
        report = read(ROOT / row['retained'])
        assert report['content_sha256'] == row['content_sha256']
        assert report['reader_source_commit'].startswith('3f5f9525')
        assert len(row['original_exports']) == len(row['sessions_exited_0']) == 2
        assert report['interpretation']['development_only']
        assert not report['interpretation']['held_out_rescored']
    for path, sha in receipt['derived_files'].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha
    assert receipt['visual_review']['reviewed'] and receipt['two_render_exports_match']
    assert not receipt['loss_changed'] and not receipt['policy_selection']
    assert not receipt['optimization_improvement_demonstrated'] and not receipt['publication_ready']


def test_all_development_outcomes_and_both_unknowns_are_kept_without_imputation():
    dev, choices = reports()
    assert dev['scientific_source_commit'].startswith('a5be8d31')
    assert choices['scientific_source_commit'].startswith('566f2c91')
    complete = [w for w in dev['worlds'] if w['resource_cost_status'] == 'measured']
    unknown = [w for w in dev['worlds'] if w['resource_cost_status'] == 'unknown']
    assert len(complete) == 12 and len(unknown) == 2
    assert all(w['status'] == 'failed' and w['resource_cost'] is None for w in unknown)
    for w in complete:
        r = w['resource_cost']
        hand = w['identity'] == 'workflow-reference-post-funding-cost'
        assert (r['value'], w['accepted_decisions']) == ((200., 20) if hand else (190., 18))
        assert r['uncollected_value'] == 0
        assert len(r['checkpoint_sha256s']) == 5
        assert sum(y['costs_by_category']['annual_research_cost'] for y in r['annual']) == r['value']
        assert r['new_model_calls'] == r['new_code_executions'] == 0
    assert [(w['resource_cost']['value'], w['accepted_decisions']) for w in choices['worlds']] == [
        (200., 20), (200., 14), (200., 16)]


def test_separate_study_support_and_fixed_pair_algebra_do_not_become_optimization():
    summary = summarize(reports())
    actual = read(ROOT / 'research/results/native-resource-cost-development-summary-v1.json')
    assert {k: v for k, v in actual.items() if k != 'content_sha256'} == summary
    assert len(summary['studies']) == 2
    assert [s['measured_worlds'] for s in summary['studies']] == [12, 3]
    assert sorted(len(p['physical_worlds']) for p in summary['studies'][0]['observed_points']) == [1, 11]
    algebra = summary['fixed_observed_pair_algebra']
    assert Fraction(algebra['equal_loss_lambda']) == Fraction(1, 5)
    assert not summary['studies_pooled'] and not summary['policy_selection']
    assert not summary['loss_changed']


def test_failed_original_world_cannot_call_measurement_or_get_zero_cost(tmp_path):
    world = {'identity': 'SCRIPTED-failed', 'role': 'own', 'seed': 42, 'status': 'failed',
        'scores': {'throughput': None}, 'physical_proof': {}}
    result = measure_world(tmp_path, world, None)
    assert result['resource_cost_status'] == 'unknown' and result['resource_cost'] is None
    assert all('fixed' not in scope for scope in SCOPES)  # no unused rescoring entry
    world['status'] = 'complete'
    with pytest.raises(ValueError, match='unique original'): measure_world(tmp_path, world, None)
