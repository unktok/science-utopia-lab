"""Pure plot data/metadata exports only; never render during real inference."""
import csv
import gzip
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

import pytest

from scripts.reports import native_corrected_choice_figures_v1 as module
from scripts.reports.native_priority_method_readout_v1 import analyze
from tests.reports.test_native_corrected_choice_readout_v1 import fixture, seal
from utopia.optimization.native_numeric_designer import save
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def data(*, delta=-1., missing=False):
    p, a, slots, refs = fixture(delta=delta, null_free=missing)
    return seal(analyze(p, a, slots, refs))


@pytest.mark.parametrize('delta,origin,count', [(-1., 'own', 'better'), (0., 'reference', 'tie'), (1., 'reference', 'worse')])
def test_all_six_four_point_paths_use_data_driven_counts_and_keep_both_scopes(delta, origin, count):
    report = data(delta=delta); result = module.derive(report)
    assert len(result['paths']) == 6 and sum(len(p['points']) for p in result['paths']) == 24
    assert result['own_vs_reference_counts'][count] == 24
    for path in result['paths']:
        assert [p['generation'] for p in path['points']] == [0, 1, 2, 3]
        assert all(p['observed_minus_reference'] == delta for p in path['points'])
        assert all(p['best_known_minus_reference'] == min(0, delta) for p in path['points'])
        assert path['primary_endpoint']['selected_origin'] == origin
        assert path['own_only_endpoint']['cell_id'] is not None
    assert not result['selection_changed'] and not result['publication_ready']


def test_generation_nulls_have_no_loss_or_own_endpoint_but_known_reference_remains():
    result = module.derive(data(missing=True)); assert result['own_vs_reference_counts']['unavailable'] == 4
    path = next(p for p in result['paths'] if p['method'] == module.METHODS[2] and p['objective'] == module.OBJECTIVES[0])
    assert all(p['observed_loss'] is p['best_own_loss'] is p['observed_minus_reference'] is None for p in path['points'])
    assert all(p['best_known_minus_reference'] == 0 for p in path['points'])
    assert path['own_only_endpoint']['cell_id'] is None and path['primary_endpoint']['selected_origin'] == 'reference'


def test_actual_retained_native_public_QA_format_keeps_its_prescribed_execution_null():
    # Existing actual native/container/public API evidence, with SCRIPTED
    # HTTP/corpus. Reading it is not a new world or model-performance result.
    path = ROOT / 'research/data/native-corrected-choice-full-public-v1/report.json.gz'
    report = checked(json.loads(gzip.decompress(path.read_bytes())))
    result = module.derive(report)
    assert result['coverage'] == {'complete_own_slots': 23, 'declared_own_slots': 24,
        'execution_or_measurement_nulls': 1, 'generation_nulls': 0, 'physical_worlds': 27}
    nulls = [(p['method'], p['objective'], q) for p in result['paths'] for q in p['points'] if q['observed_loss'] is None]
    assert len(nulls) == 1 and nulls[0][:2] == (module.METHODS[2], module.OBJECTIVES[1])
    assert nulls[0][2]['generation'] == 2 and nulls[0][2]['status'] == 'failed'
    assert result['own_vs_reference_counts'] == {'better': 0, 'tie': 23, 'worse': 0, 'unavailable': 1}


@pytest.mark.parametrize('change', ['missing', 'coverage', 'path', 'origin', 'best', 'program', 'reference-loss', 'ties', 'legacy', 'bool-generation'])
def test_resealed_but_contradictory_plot_data_cannot_hide_or_relabel_observations(change):
    report = data()
    if change == 'missing': report['slots'].pop()
    elif change == 'coverage': report['coverage']['generation_nulls'] = 3
    elif change == 'path': next(iter(report['paths'].values()))[-1]['best_own_loss'] += 1
    elif change == 'origin': report['selected'][0]['selected_origin'] = 'reference'
    elif change == 'best': report['own_only_selected'][0]['loss'] += 1
    elif change == 'program': report['selected'][0]['literal_system_sha256'] = 'f' * 64
    elif change == 'reference-loss': report['selected'][0]['reference_loss'] += 1
    elif change == 'ties': report['own_only_selected'][0]['all_tied_ids'].reverse()
    elif change == 'bool-generation': report['slots'][0]['generation'] = False
    else: report['schema'] = 'scienceutopia.native-priority-method-readout.v1'
    with pytest.raises(ValueError): module.derive(seal(report))


def test_data_only_public_pair_has_literal_null_csv_and_never_calls_renderer_or_science(tmp_path, monkeypatch):
    roots = {k: tmp_path / k for k in ('run', 'source', 'analysis', 'readouts', 'reader')}
    for path in roots.values(): path.mkdir()
    report = data(missing=True); save(roots['run'] / 'plan.json', {'source_commit': 'a' * 40})
    (roots['run'] / 'writer.lock').touch(); (roots['readouts'] / 'report-1').mkdir()
    save(roots['readouts'] / 'report-1/report.json', {k: v for k, v in report.items() if k != 'content_sha256'})
    monkeypatch.setattr(module, 'ROOT', roots['reader']); monkeypatch.setattr(module, 'pinned_revision', lambda root: 'b' * 40)
    monkeypatch.setattr(module, 'evidence_files', lambda origin: [roots['run'] / 'plan.json', roots['readouts'] / 'report-1/report.json'])
    calls = []
    def origin(value, **kw): calls.append(kw); return {'SCRIPTED': 'not actual provenance'}, {}, {}
    monkeypatch.setattr(module, 'origin_evidence', origin)
    def forbidden(*a, **kw): pytest.fail('pure data export may not render, execute code or call a model')
    monkeypatch.setattr(module, 'render', forbidden)
    monkeypatch.setattr('requests.Session.post', forbidden); monkeypatch.setattr('openai.OpenAI.__init__', forbidden)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)
    before = module._inventory(roots['run'])
    with tempfile.TemporaryDirectory(prefix='scienceutopia-corrected-figure-data-') as directory:
        outputs = [Path(directory) / str(i) for i in (1, 2)]
        for output in outputs:
            module.export(SimpleNamespace(output=output, render=False, **{'origin_' + k: roots[k] for k in ('run', 'source', 'analysis', 'readouts')}))
        assert {p.name: p.read_bytes() for p in outputs[0].iterdir()} == {p.name: p.read_bytes() for p in outputs[1].iterdir()}
        assert set(p.name for p in outputs[0].iterdir()) == {'report.json', 'points.csv', 'manifest.json'}
        with (outputs[0] / 'points.csv').open() as stream: points = list(csv.DictReader(stream))
        nulls = [p for p in points if p['status'] == 'generation-null']
        assert len(points) == 24 and len(nulls) == 4
        assert all(p['observed_loss'] == p['best_own_loss'] == '' and float(p['best_known_minus_reference']) == 0 for p in nulls)
    assert before == module._inventory(roots['run']) and calls == [{'profile': 'corrected-choice-v1'}] * 2
