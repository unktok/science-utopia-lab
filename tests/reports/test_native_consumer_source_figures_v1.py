"""Light pure SCRIPTED plot-data/closure tests; no rendering or native run."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_consumer_source_figures_v1 as figures
from scripts.reports.native_consumer_source_comparison_v1 import analyze
from tests.reports.test_native_consumer_source_readout_v1 import fixture
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256


def report(*, null=None):
    result = {**analyze(*fixture(null=null)), 'analysis_source_commit': 'SCRIPTED-reader'}
    return {**result, 'content_sha256': digest(result)}


def reseal(value):
    value.pop('content_sha256')
    return {**value, 'content_sha256': digest(value)}


def test_all_slots_and_references_are_literal_and_input_is_not_mutated():
    value = report(); before = clone(value); result = figures.derive(value)
    assert value == before
    assert len(result['outcomes']) == 11 and len(result['paths']) == 4
    assert [r['optimizer_visible_reference'] for r in result['outcomes'][:3]] == [True, True, False]
    assert result['selection'] == value['selection']
    assert result['literal_consumers_minus_interface_own_best'] == dict.fromkeys(figures.OBJECTIVES, 0.0)
    assert all(r['requested_cost'] == r['collected_cost'] + r['unpaid_cost'] for r in result['outcomes'])
    assert not result['requested_cost_is_optimized'] and not result['unpaid_or_activity_veto']


def test_generation_null_stays_visible_and_never_becomes_a_zero_point_or_charge():
    result = figures.derive(report(null=('interface-only', 'content-utility', 0)))
    first = result['outcomes'][3]
    assert first['status'] == 'generation-null' and first['content-utility'] is None
    assert first['collected_cost'] is None and first['unpaid_cost'] is None and first['requested_cost'] is None
    path = result['paths']['interface-only::content-utility']
    assert path[0]['observed_loss'] is None and path[0]['best_own_loss'] is None
    assert path[0]['best_known_loss_including_visible_references'] is not None


@pytest.mark.parametrize('change', ['path', 'selection', 'visibility', 'cost', 'independence', 'missing'])
def test_plotting_does_not_reselect_leak_hidden_control_impute_or_rewrite_scope(change):
    value = report()
    if change == 'path':
        value['loss_paths']['interface-only::content-utility'][0]['best_own_loss'] = -999
    elif change == 'selection':
        value['selection']['selected']['interface-only::content-utility']['loss'] = -999
    elif change == 'visibility':
        value['references'][2]['optimizer_visible'] = True
    elif change == 'cost':
        value['slots'][0]['requested_activity_cost'] = 0
    elif change == 'independence':
        value['interpretation']['independent_optimizer_replications'] = True
    else:
        value['slots'].pop()
    with pytest.raises(ValueError):
        figures.derive(reseal(value))


def saved_pair(root):
    value = report()
    save(root / 'started.json', {'schema': 'scienceutopia.native-consumer-source-comparison.v1.readout.finish',
        'analysis_source_commit': 'SCRIPTED-reader', 'scientific_source_commit': value['scientific_source_commit']})
    names = ('report.json', 'slots.csv', 'manifest.json')
    for i in (1, 2):
        directory = root / ('report-' + str(i)); directory.mkdir()
        save(directory / 'report.json', {k: v for k, v in value.items() if k != 'content_sha256'})
        (directory / 'slots.csv').write_text('SCRIPTED software fixture only\n')
        save(directory / 'manifest.json', {'files': {name: file_sha256(directory / name) for name in names[:2]}})
    save(root / 'ended.json', {'status': 'closed',
        'steps': [{'stage': 'report-1', 'exit_code': 0}, {'stage': 'report-2', 'exit_code': 0}],
        'new_model_calls': 0, 'new_native_worlds': 0,
        'report_files': {name: file_sha256(root / 'report-1' / name) for name in names}})
    return value


def test_saved_pair_scope_and_hashes_reject_changed_second_export(tmp_path, monkeypatch):
    root = tmp_path / 'pair'; root.mkdir(); value = saved_pair(root)
    monkeypatch.setattr(figures, 'pinned_revision', lambda p: 'SCRIPTED-reader')
    actual, hashes = figures.closed_readout(root, tmp_path / 'frozen')
    assert actual == value and len(hashes) == 8
    (root / 'report-2/slots.csv').write_text('changed after closure\n')
    with pytest.raises(ValueError, match='closure'):
        figures.closed_readout(root, tmp_path / 'frozen')


def test_no_render_export_is_deterministic_without_matplotlib_or_model_calls(tmp_path, monkeypatch):
    root = tmp_path / 'pair'; root.mkdir(); saved_pair(root)
    monkeypatch.setattr(figures, 'pinned_revision', lambda p: 'SCRIPTED-reader')
    monkeypatch.setattr(figures, 'render', lambda *a: pytest.fail('pure export must not render'))
    for i in (1, 2):
        figures.export(SimpleNamespace(readouts=root, frozen_reader=tmp_path / 'frozen',
            output=tmp_path / ('export-' + str(i)), render=False))
    names = ('report.json', 'outcomes.csv', 'manifest.json')
    assert sorted(p.name for p in (tmp_path / 'export-1').iterdir()) == sorted(names)
    for name in names:
        assert (tmp_path / 'export-1' / name).read_bytes() == (tmp_path / 'export-2' / name).read_bytes()
    value = json.loads((tmp_path / 'export-1/report.json').read_text())
    assert value['new_model_calls'] == value['new_code_executions'] == value['new_native_worlds'] == 0
    assert not value['publication_ready']
