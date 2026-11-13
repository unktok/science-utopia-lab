"""Tracked readout is a literal projection, not a new selected scientific run."""
import csv
import json
from pathlib import Path

from scripts.reports.native_optimization_incumbents_v1 import summarize
from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256


def test_retained_closed_projection_matches_source_and_all_exported_bytes():
    root = Path(__file__).resolve().parents[2]
    data = root / 'research/data/native-planning-incumbents-v1'
    figures = root / 'paper/figures/native-planning-incumbents-v1'
    report = checked(json.loads((data / 'report.json').read_text()))
    manifest = checked(json.loads((data / 'manifest.json').read_text()))
    original = checked(json.loads((root / 'research/data/native-planning-objective-loop-v1/report.json').read_text()))
    for key, value in summarize(original).items():
        assert report[key] == value
    assert not report['software_qa_plot']
    assert report['content_sha256'] == manifest['report_content_sha256']
    assert report['analysis_source_commit'] == manifest['analysis_source_commit']
    assert set(manifest['files']) == {'report.json', 'paths.csv', 'optimization-incumbents.png', 'optimization-incumbents.svg'}
    for name, expected in manifest['files'].items():
        location = figures if name.startswith('optimization-incumbents.') else data
        assert file_sha256(location / name) == expected
    with (data / 'paths.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 8
    for history in report['histories']:
        expected = [r for r in rows if r['history'] == history['history']]
        assert [int(r['consumed_slots']) for r in expected] == [0, 1, 2, 3]
        assert expected[0]['best_own_loss'] == ''
        assert history['final']['known_improvement_over_reference'] == 0
        assert history['final']['own_improvement_over_reference'] == 0
