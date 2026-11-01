"""Synthetic plotting QA, explicitly not native scientific observations."""
from copy import deepcopy

import pytest

from scripts.analyze_native_open_v7 import FIXTURE, SCHEMA
from scripts.figures.native_open_v7 import create, figure_data
from utopia.system.design_patch import digest
from utopia.system.native_open_examples import open_native_system


def fixture_report():
    system = open_native_system('sha256:'+'a'*64)
    rows = []
    for i in range(4):
        a, c = i+1, 2*(i+1)
        obs = {'status': 'complete', 'loss': -a-.1*c, 'metadata': {'system_fingerprint': system.fingerprint}}
        rows.append({'generation': i//2, 'observation': obs,
            'draw': {'suggestion': {'candidate': system.to_dict()}, 'assignment': {'repetition': str(i+1)},
                'continuous_operations': [{'path': '/fixture/bias', 'value': .1*i}], 'latent': [.2*i]},
            'independent_metrics': {'native.accepted_decisions': {'status': 'measured', 'value': a},
                'native.institutional_context_deliveries': {'status': 'measured', 'value': c}},
            'native_counts': {'custom_artifacts': i+1, 'process_invocations': i+2, 'custom_actors': 1}})
    value = {'schema': SCHEMA, 'classification': FIXTURE, 'source_commit': 'scripted-figure-QA',
        'observations': rows, 'claims': {'scientific_value': False},
        'audit': {'new_model_calls': 0, 'raw_inventory_sha256': 'fixture-only',
            'loss_path': [r['observation']['loss'] for r in rows]}}
    value['content_sha256'] = digest(value)
    return value


def rehash(value):
    value.pop('content_sha256', None)
    value['content_sha256'] = digest(value)
    return value


def test_exact_two_panel_fixture_generates_vector_and_raster_with_manifest(tmp_path):
    report = fixture_report()
    manifest = create(report, tmp_path/'native-open-v7-qa')
    assert manifest['classification'] == FIXTURE
    assert len(manifest['plotted_native_facts']) == 4
    assert [r['loss'] for r in manifest['plotted_native_facts']] == report['audit']['loss_path']
    assert all((tmp_path/('native-open-v7-qa.'+kind)).is_file() for kind in ('pdf', 'png', 'svg', 'manifest.json'))


def test_fake_native_identity_loss_and_paper_destination_rejected(tmp_path):
    report = fixture_report()
    with pytest.raises(ValueError, match='scripted QA'):
        create(report, tmp_path/'paper/figures/not-a-native-result')
    report['observations'][0]['observation']['loss'] = -999.
    rehash(report)
    with pytest.raises(ValueError, match='loss differs'):
        figure_data(report)
    report = fixture_report()
    report['observations'][0]['observation']['metadata']['system_fingerprint'] = 'wrong-source'
    rehash(report)
    with pytest.raises(ValueError, match='structure differs'):
        figure_data(report)


def test_null_failure_is_not_zero_or_numeric_penalty(tmp_path):
    report = fixture_report()
    row = report['observations'][1]
    row['observation'] = {'status': 'failed', 'loss': None}
    report['audit']['loss_path'][1] = None
    rehash(report)
    assert figure_data(report)[1]['loss'] is None
    create(report, tmp_path/'mixed-qa')
    row['observation']['loss'] = 0.
    rehash(report)
    with pytest.raises(ValueError, match='plotting penalty'):
        figure_data(report)


def test_unhashed_and_empty_pending_results_are_not_figures(tmp_path):
    report = fixture_report()
    report['claims']['scientific_value'] = True
    with pytest.raises(ValueError, match='hash-bound'):
        figure_data(report)
    report = fixture_report()
    report['observations'] = []
    report['audit']['loss_path'] = []
    rehash(report)
    with pytest.raises(ValueError, match='pending authoring'):
        create(report, tmp_path/'empty')
