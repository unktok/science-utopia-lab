"""Immutable closed evaluation values, complete comparators and literal data."""
import csv
import hashlib
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT/'research/data/native-objective-fixed-evaluation-v1'


def test_every_retained_file_matches_original_closed_receipt():
    receipt = checked(json.loads((ROOT/'research/results/native-objective-fixed-evaluation-closed-verification-v1.json').read_text()))
    for name, expected in receipt['retained_files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected
    assert receipt['physical_worlds'] == 18 and receipt['logical_rows'] == 21
    assert receipt['seeds'] == [64101, 64107, 64113]
    assert not receipt['candidate_reselection'] and not receipt['independent_optimizer_replications']
    assert not receipt['publication_ready'] and not receipt['scientific_truth_measured']


def test_all_labels_seeds_and_literal_shared_control_remain_present():
    report = checked(json.loads((DATA/'report.json').read_text()))
    with (DATA/'logical-scores.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(report['logical_rows']) == 21
    assert len({r['physical_job'] for r in rows}) == len(report['physical_worlds']) == 18
    assert {r['status'] for r in rows} == {'complete'}
    values = {(r['label'], int(r['seed'])): r for r in rows}
    for seed, count in zip(report['seeds'], [11, 7, 9]):
        selected = values['selected:throughput', seed]
        for name in ['reviewed-all-connected', 'one-reviewer-all-connected', 'no-review-all-connected']:
            assert float(values['reference:'+name, seed]['throughput']) == float(selected['throughput']) == -count
        unchanged = values['selected:content-utility', seed]
        assert unchanged['physical_job'] == values['reference:reviewed-all-connected', seed]['physical_job']
        assert values['reference:no-review-reject-all-connected', seed]['throughput'] == '0.0'


def test_every_comparator_and_mixed_cross_objective_result_are_retained():
    with (DATA/'paired-differences.csv').open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 30
    lookup = {(r['label'], r['reference'], int(r['seed'])): r for r in rows}
    differences = [float(lookup['selected:throughput', 'no-review-all-connected', seed]['content-utility'])
                   for seed in [64101, 64107, 64113]]
    assert differences[0] == 1 and differences[1] == 0 and abs(differences[2]+2/3) < 1e-12
    assert all(lookup['selected:content-utility', 'reviewed-all-connected', seed]['same_physical_job'] == 'True'
               for seed in [64101, 64107, 64113])


def test_original_cost_counts_do_not_double_count_labels_or_cached_inputs():
    costs = checked(json.loads((DATA/'costs.json').read_text()))
    scientist = costs['scientist']
    assert scientist['completed_responses'] == 2377
    assert scientist['provider_usage']['prompt_tokens']['recorded_sum'] == 2431115
    assert scientist['provider_usage']['completion_tokens']['recorded_sum'] == 225508
    assert scientist['provider_usage']['cached_prompt_tokens']['recorded_sum'] == 441737
    assert costs['common_content_observer']['physical_requests'] == 144
    assert not costs['unknown_usage_imputed'] and not costs['aliases_or_nested_durations_added']


def test_original_effects_cover_all_actual_worlds_and_boundaries():
    effects = checked(json.loads((DATA/'effects.json').read_text()))
    assert len(effects['worlds']) == 18
    assert sum(len(w['annual']) for w in effects['worlds']) == 72
    assert sum(len(w['code_calls']) for w in effects['worlds']) == 372
