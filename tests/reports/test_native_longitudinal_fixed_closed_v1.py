"""Retained unused outcomes and alias-safe paper data, not new inference."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def read(name):
    return checked(json.loads((ROOT / name).read_text()))


def test_all_frozen_labels_and_paired_files_are_retained_without_reselection():
    receipt = read('research/results/native-longitudinal-fixed-closed-v1.json')
    assert receipt['terminal']['status'] == 'closed'
    assert receipt['physical_worlds'] == 5 and receipt['logical_labels'] == 6
    assert receipt['unused_seeds'] == [676047151]
    assert receipt['new_designer_generation_POSTs'] == 0
    assert not receipt['candidate_reselection'] and not receipt['publication_ready']
    for row in receipt['logical_rows']:
        assert row['status'] == 'complete'
        if row['label'] != 'reference:post-funding-cost':
            assert row['scores'] == {'throughput': -34., 'content-utility': -25.666666666666668}
    assert sorted(len(c['physical_ids']) for c in receipt['input_classes']) == [1, 4]
    assert len(receipt['paired_readout_files']) == 18
    for entry in receipt['paired_readout_files']:
        assert hashlib.sha256((ROOT / entry['retained']).read_bytes()).hexdigest() == entry['sha256']
    for name, sha in receipt['derived_files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha


def test_fixed_figure_does_not_turn_six_labels_into_six_physical_worlds():
    from scripts.reports.native_longitudinal_fixed_paper_v1 import physical_rows
    report = read('research/data/native-longitudinal-fixed-v1/readout/report.json')
    rows = physical_rows(report)
    assert len(rows) == 5
    assert [len(r['labels']) for r in rows] == [2, 1, 1, 1, 1]


def test_exact_content_difference_and_role_costs_are_not_independent_samples():
    delta = read('research/results/native-longitudinal-fixed-content-delta-v1.json')
    assert delta['shared']['count'] == 28
    assert delta['reference_only']['count'] == 6 and delta['hand_only']['count'] == 8
    assert Fraction(delta['hand_minus_reference_utility_exact']) == Fraction(13, 3)
    assert not delta['isolated_causal_effect_claimed']
    cost = read('research/data/native-longitudinal-fixed-v1/cost-summary.json')
    assert cost['scientist_completed_responses'] == 825
    assert cost['common_content_observer']['physical_requests'] == 126
    usage = cost['scientist_provider_usage']
    assert usage['prompt_tokens']['recorded_sum'] + usage['completion_tokens']['recorded_sum'] == 1384326
    assert usage['total_tokens']['recorded_sum'] == 1384326
    assert usage['cached_prompt_tokens']['recorded_sum'] == 191272
