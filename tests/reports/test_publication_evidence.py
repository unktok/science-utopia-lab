"""Offline evidence projection regressions; scripted tests are not science."""
from copy import deepcopy
import json

import pytest

from scripts.reports import publication_evidence as report


def test_actual_curated_evidence_is_hash_bound_repeatable_and_not_cross_source_ranked():
    result = report.build()
    assert result == report.build()
    cases = {c['id']: c for c in result['cases']}
    assert set(cases) == {'v10', 'v12', 'v13', 'v45'}
    v45 = cases['v45']['arms']
    assert v45['efficiency']['fresh_loss_path'] == [None]
    assert v45['throughput']['fresh_loss_path'] == [-7.]
    assert v45['throughput']['rows'][0]['retrospective_cross_scores'][
        'native-reviewed-production-efficiency-v13'] == -12.166666666666668
    assert cases['v13']['arms']['native-joint-v5-throughput']['fresh_loss_path'] == [-7., -7., -6., -10.]
    assert len(cases['v10']['arms']['gradient']['fresh_loss_path']) == 3
    assert cases['v10']['arms']['gradient']['historical_references'] == 3
    old_row = cases['v10']['arms']['gradient']['rows'][0]
    assert old_row['source_commit'] is None
    assert old_row['report_source_commit'] == cases['v10']['source_commit']
    assert result['interpretation']['cross_source_method_ranking_established'] is False
    assert 'not authenticated' in cases['v12']['provenance_note']


def test_tracked_inventory_is_exactly_reproducible_from_the_catalog():
    saved = report.read(report.ROOT/'research/results/publication-evidence-inventory-v1.json')
    assert report.build() == saved


@pytest.mark.parametrize('value', [True, float('nan'), float('inf'), None])
def test_complete_losses_are_finite_nonboolean(value):
    with pytest.raises(ValueError):
        report._row({'status': 'complete', 'loss': value}, index=0, arm='test', source='fixture', case='test')


def test_failure_stays_null_and_all_ties_are_preserved():
    rows = [report._row({'status': 'complete', 'loss': -7}, index=i, arm='a', source='s', case='c') for i in range(2)]
    rows.append(report._row({'status': 'technical-failure', 'loss': None}, index=2, arm='a', source='s', case='c'))
    assert report._best(rows) == {'loss': -7, 'tied_row_ids': ['c:a:0', 'c:a:1']}
    with pytest.raises(ValueError, match='failure'):
        report._row({'status': 'technical-failure', 'loss': 0}, index=0, arm='a', source='s', case='c')


def setup(tmp_path):
    data = {'schema': 'scienceutopia.native-warmstart-audit-summary.v45',
        'source_commit': 'scripted-source', 'arms': {}, 'claims': {}}
    data['content_sha256'] = report.digest(data)
    (tmp_path/'data.json').write_text(json.dumps(data))
    catalog = {'schema': 'scienceutopia.publication-evidence-catalog.v1', 'scope': 'SCRIPTED ONLY', 'cases': [
        {'id': 'scripted', 'path': 'data.json', 'schema': data['schema'], 'source_commit': 'scripted-source',
         'content_sha256': data['content_sha256'], 'provenance_note': 'SCRIPTED'}]}
    (tmp_path/'catalog.json').write_text(json.dumps(catalog))
    return data, catalog


@pytest.mark.parametrize('mutation', ['source', 'content', 'schema', 'duplicate', 'alias', 'escape'])
def test_evidence_identity_mismatches_fail_without_repair(tmp_path, mutation):
    data, catalog = setup(tmp_path)
    if mutation == 'source':
        data['source_commit'] = 'swapped'
    elif mutation == 'content':
        data['claims']['invented-improvement'] = True
    elif mutation == 'schema':
        catalog['cases'][0]['schema'] = 'not-supported'
    elif mutation == 'duplicate':
        catalog['cases'].append(deepcopy(catalog['cases'][0]))
    elif mutation == 'alias':
        catalog['cases'].append({**catalog['cases'][0], 'id': 'same-artifact-new-name'})
    else:
        catalog['cases'][0]['path'] = '../outside.json'
    (tmp_path/'data.json').write_text(json.dumps(data))
    (tmp_path/'catalog.json').write_text(json.dumps(catalog))
    with pytest.raises(ValueError):
        report.build(tmp_path, catalog='catalog.json')


def test_json_duplicate_keys_and_nonfinite_constants_rejected(tmp_path):
    path = tmp_path/'bad.json'
    for value in ('{"x":1,"x":2}', '{"x":NaN}'):
        path.write_text(value)
        with pytest.raises(ValueError):
            report.read(path)


def test_existing_output_is_not_overwritten(tmp_path):
    setup(tmp_path)
    output = tmp_path/'existing.json'
    output.write_text('keep-me')
    with pytest.raises(ValueError, match='already exists'):
        report.main(['--root', str(tmp_path), '--catalog', 'catalog.json', '--output', str(output)])
    assert output.read_text() == 'keep-me'
