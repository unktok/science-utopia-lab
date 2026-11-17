"""Retained real closed-study data, not new model/native experiments."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from scripts.reports.native_corrected_choice_figures_v1 import derive
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data/native-corrected-choice-search-v1'
RECORD = ROOT / 'research/results/native-corrected-choice-search-closed-v1.json'


def read(path):
    return json.loads(path.read_text())


def test_literal_retention_and_complete_paths():
    record = read(RECORD)
    for name, expected in record['retained_files'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    for name in ('readout.json', 'authors.json', 'visibility.json', 'costs.json',
                 'signed-content.json', 'loss-paths.json', 'selection.json',
                 'terminal.json', 'writer-exit.json'):
        checked(read(DATA / name))
    data = derive(read(DATA / 'readout.json'))
    paths = read(DATA / 'loss-paths.json')
    assert data['paths'] == paths['paths']
    assert data['own_vs_reference_counts'] == record['own_vs_assigned_reference_counts']
    assert record['coverage'] == paths['coverage']
    assert record['original_terminal']['consumed_slots'] == 24
    assert record['original_terminal']['status'] == 'closed'
    for name, expected in record['rendered_loss_paths'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected


def test_frozen_banks_keep_real_origins_and_nulls():
    record = read(RECORD)
    selection = checked(read(DATA / 'selection.json'))
    for group, rows in record['frozen_endpoints'].items():
        assert len(rows) == 6
        for row in rows:
            original = selection[group][row['method']]['0'][row['objective']]
            assert {k: v for k, v in row.items() if k not in ('method', 'replication', 'objective')} == {
                k: v for k, v in original.items() if k != 'system'}
    assert {r['selected_origin'] for r in record['frozen_endpoints']['selected']} == {'reference'}
    assert {r['selected_origin'] for r in record['frozen_endpoints']['own_only_selected']} == {'own'}
    slots = read(DATA / 'readout.json')['slots']
    nulls = [r for r in slots if r['status'] != 'complete']
    assert len(nulls) == 1 and nulls[0]['loss'] is None


def test_observed_support_dominance_and_accounting_are_not_gain():
    record = read(RECORD)
    report = read(DATA / 'readout.json')
    proof = record['observed_support_dominance']
    reference = next(r for r in report['references'] if r['label'] == proof['reference'])
    key_u, key_k = 'native.common_content_utility_sum', 'native.collected_activity_resource_cost'
    assert reference['metrics'][key_u]['value'] == proof['U']
    assert reference['metrics'][key_k]['value'] == proof['K_collected']
    complete = [r for r in report['slots'] if r['status'] == 'complete']
    assert len(complete) == proof['complete_own_points_weakly_dominated']
    assert all(r['metrics'][key_u]['value'] <= proof['U'] and
               r['metrics'][key_k]['value'] >= proof['K_collected'] for r in complete)
    content = read(DATA / 'signed-content.json')
    assert all(content[k] == v for k, v in record['signed_content'].items())
    costs = read(DATA / 'costs.json')
    assert record['physical_costs']['scientist_provider_usage'] == costs['scientist']['provider_usage']
    assert record['physical_costs']['scientist_completed_responses'] == costs['scientist']['completed_responses']
    assert not record['unused_real_evaluation_dispatched'] and not record['publication_ready']


def test_actual_software_QA_is_separate_from_scientific_evaluation():
    record = read(RECORD)
    qa = record['fixed_public_QA']
    assert qa['verification'] == read(DATA / 'fixed-public-QA.json')
    root = ET.parse(DATA / 'fixed-public-QA.xml').getroot()
    suite = root if root.tag == 'testsuite' else root.find('testsuite')
    assert qa['pytest'] == suite.attrib
    assert suite.attrib['tests'] == '1'
    assert all(suite.attrib[k] == '0' for k in ('failures', 'errors', 'skipped'))
    assert qa['verification']['evaluation_native_worlds'] == 14
    assert qa['verification']['new_real_model_calls'] == 0
    assert not qa['verification']['outer_subprocess_CLI_routing_tested']
    assert not qa['verification']['scientific_reserved_seeds_consumed']
