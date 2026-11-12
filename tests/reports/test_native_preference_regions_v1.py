"""Literal closed archive and rational envelope checks; no new inference."""
from fractions import Fraction as F
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_preference_regions_v1 as module
from utopia.system.design_patch import digest

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT/'research/data/native-objective-instrument-loop-v1/report.json'


def test_actual_archive_minima_ties_and_failed_slots_are_preserved():
    original = json.loads(REPORT.read_text()); before = digest(original); r = module.summarize(original)
    assert digest(original) == before
    assert r['physical_attempts'] == 13 and r['complete_observed_worlds'] == 11
    assert [len(c['physical_world_ids']) for c in r['curves']] == [1, 1, 9]
    assert [c['accepted_occurrences'] for c in r['curves']] == [0, 5, 7]
    assert [c['derived_fixed_score_sum'] for c in r['curves']] == ['0', '19', '25']
    assert r['geometry']['open_intervals'] == [
        {'left': '1', 'right': '3', 'winning_curve_indices': [2]},
        {'left': '3', 'right': '19/5', 'winning_curve_indices': [1]},
        {'left': '19/5', 'right': '5', 'winning_curve_indices': [0]}]
    assert r['current_center_winning_curve_indices'] == [1, 2]
    assert len(r['failed_world_ids']) == 2 and not r['candidate_reselection']
    assert not r['family']['new_objective_adopted'] and not r['new_model_calls']


def test_dominated_crossings_do_not_split_actual_optimal_regions():
    result = module.regions([(F(0), F(0)), (F(5), -F(19)), (F(7), -F(25))])
    assert [b['center'] for b in result['boundaries']] == ['1', '3', '19/5', '5']
    assert result['boundaries'][1]['winning_curve_indices'] == [1, 2]
    assert result['boundaries'][2]['winning_curve_indices'] == [0, 1]
    assert '25/7' not in [b['center'] for b in result['boundaries']]


def test_identical_parallel_and_endpoint_only_ties_are_not_lost():
    r = module.regions([(F(1), F(0)), (F(1), F(0)), (F(0), F(1)), (F(0), F(2))])
    assert r['open_intervals'] == [{'left': '1', 'right': '5', 'winning_curve_indices': [2]}]
    assert r['boundaries'][0]['winning_curve_indices'] == [0, 1, 2]
    with pytest.raises(ValueError): module.regions([])


def test_failed_attempts_cannot_be_given_an_imputed_loss():
    r = json.loads(REPORT.read_text())
    next(w for w in r['physical_worlds'] if w['status'] != 'complete')['scores']['throughput'] = 0
    r['content_sha256'] = digest({k: v for k, v in r.items() if k != 'content_sha256'})
    with pytest.raises(ValueError, match='technical null'): module.summarize(r)


def test_actual_figure_exports_agree_without_mutating_retained_report(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'pinned_revision', lambda _: 'e'*40)
    before = REPORT.read_bytes(); inventories = []
    for name in ('one', 'two'):
        out = tmp_path/name; module.export(SimpleNamespace(report=REPORT, output=out))
        inventories.append({p.name: module.file_sha256(p) for p in out.iterdir()})
    assert inventories[0] == inventories[1] and REPORT.read_bytes() == before


def test_retained_original_exports_are_bound_and_reconstruct_numerically():
    base = ROOT/'research/data/native-preference-regions-v1'
    manifest = module.checked(json.loads((base/'manifest.json').read_text()))
    assert manifest['analysis_source_commit'] == '26497eef3589e13ef95fdfee167b946e39455012'
    assert manifest['report_file_sha256'] == module.file_sha256(REPORT)
    assert set(manifest['files']) == {'summary.json', 'preference-regions.png', 'preference-regions.svg'}
    assert all(module.file_sha256(base/name) == value for name, value in manifest['files'].items())
    retained = module.checked(json.loads((base/'summary.json').read_text()))
    assert {k: v for k, v in retained.items() if k != 'content_sha256'} == module.summarize(json.loads(REPORT.read_text()))
    assert retained['family']['actual_optimized_center'] == '3'
