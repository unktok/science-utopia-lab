"""Closed path projection, not additional native/scientific experiments."""
import gzip
import json
from pathlib import Path

import pytest

from scripts.reports.native_priority_method_figures_v1 import derive
from utopia.system.design_patch import digest

ROOT = Path(__file__).resolve().parents[2]


def inputs():
    report = json.loads(gzip.decompress((ROOT /
        'research/data/native-priority-method-closed-v1/method/report.json.gz').read_bytes()))
    closed = json.loads((ROOT / 'research/results/native-priority-method-comparison-closed-v1.json').read_text())
    return report, closed


def test_all_twelve_two_point_paths_keep_actual_losses_incumbents_and_reference_gaps():
    report, closed = inputs(); data = derive(report, closed)
    assert len(data['paths']) == 12 and sum(len(p['points']) for p in data['paths']) == 24
    for path in data['paths']:
        points = path['points']
        assert [p['generation'] for p in points] == [0, 1]
        assert points[1]['best_own_loss'] == min(p['observed_loss'] for p in points)
        assert all(p['best_known_including_visible_parent'] == p['reference_loss'] for p in points)
        assert all(p['observed_minus_reference'] >= 0 for p in points)
    assert not data['selection_changed'] and not data['publication_ready']


@pytest.mark.parametrize('mutation', ['missing-slot', 'wrong-path', 'wrong-frozen-minimum'])
def test_resealed_but_inconsistent_projection_still_fails(mutation):
    report, closed = inputs()
    if mutation == 'missing-slot': report['slots'].pop()
    elif mutation == 'wrong-path': next(iter(report['paths'].values()))[0]['observed_loss'] += 1
    else: report['selected'][0]['loss'] += 1
    report['content_sha256'] = digest({k:v for k,v in report.items() if k != 'content_sha256'})
    closed['readout_content_sha256'] = report['content_sha256']
    closed['content_sha256'] = digest({k:v for k,v in closed.items() if k != 'content_sha256'})
    with pytest.raises(ValueError): derive(report, closed)
