"""Synthetic figure guards; no actual-data asset is produced by these tests."""
from copy import deepcopy

import pytest

from scripts import analyze_native_autonomous_search_v14 as audit
from scripts.figures.native_autonomous_search_v14 import figure_data,render
from tests.reports.test_native_autonomous_search_v14_audit import fixture,save
from utopia.system.design_patch import digest


def report(tmp_path):
    fixture(tmp_path/'raw')
    return audit.analyze(tmp_path/'raw',expected_source='fixture-source')


def test_scripted_output_requires_explicit_test_only_flag_and_retains_nulls(tmp_path):
    value = report(tmp_path)
    with pytest.raises(ValueError):
        figure_data(value)
    data = figure_data(value,allow_synthetic=True)
    assert data['consumed_native_slots'] == 8 and data['physical_native_worlds'] == 0
    assert len(data['edits']) == 6 and all(e['counts'] is None for e in data['edits'])
    assert data['designer_costs']['dispatch_intents'] == 12


@pytest.mark.parametrize('kind',['claims','loss','slots','definition','costs','checkpoint','inventory'])
def test_rehashed_audit_plot_tampering_rejected(tmp_path,kind):
    value = report(tmp_path)
    first = value['runs'][value['run_order'][0]]
    if kind == 'claims': value['claims']['method_superiority_established'] = True
    if kind == 'loss': first['observations'][0]['own_loss'] = -10
    if kind == 'slots': first['observations'][0]['scheduled_native_slots'] = 2
    if kind == 'definition': first['authored_definitions'][0]['definition'] = {'repair':'forged'}
    if kind == 'costs': value['designer_costs']['known_responses'] = 0
    if kind == 'checkpoint': first['physical_native_worlds'] = 1
    if kind == 'inventory': value['audit']['raw_inventory_sha256'] = '0'*64
    value.pop('content_sha256'); value['content_sha256'] = digest(value)
    with pytest.raises(ValueError):
        figure_data(value,allow_synthetic=True)


def test_fixture_render_is_5_5_inches_with_explicit_watermark(tmp_path):
    value = report(tmp_path)
    path = tmp_path/'fixture-audit.json'; save(path,value)
    manifest = render(value,tmp_path/'fixture-only',audit_path=path,allow_synthetic=True)
    assert manifest['width_inches'] == 5.5
    assert len(manifest['files']) == 2
    svg = (tmp_path/'fixture-only.svg').read_text()
    assert 'SYNTHETIC CONTRACT FIXTURE' in svg and '396pt' in svg
