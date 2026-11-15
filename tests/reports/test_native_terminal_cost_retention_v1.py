"""Literal saved-world evidence and manuscript claims, not more inference."""
import csv
import hashlib
import json
from pathlib import Path

from scripts.reports.native_terminal_cost_interpretation_v1 import derive
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data/native-terminal-cost-pilot-v1'


def read(path):
    return checked(json.loads(path.read_text()))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_original_closed_workers_source_and_file_identities():
    compact = json.loads((ROOT / 'research/results/native-terminal-cost-pilot-closed-v1.json').read_text())
    assert compact['writer']['exit_code'] == compact['paired_closure']['exit_code'] == compact['paired_readout']['exit_code'] == 0
    start, end = read(DATA / 'started.json'), read(DATA / 'terminal.json')
    assert start['pid'] == compact['writer']['pid'] and end['status'] == 'closed' and end['completed_jobs'] == 2
    assert not end['automatic_invention'] and not end['policy_selection']
    audit, costs = read(DATA / 'closure/audit-1.json'), read(DATA / 'closure/costs-1.json')
    assert audit['source_commit'] == costs['source_commit'] == compact['scientific_source_commit']
    assert audit['source_proof']['status'] == 'verified-exact-source-closure'
    assert audit['raw_files'] == compact['paired_closure']['raw_files'] == 393
    for name, key in [('audit-1.json', 'audit'), ('costs-1.json', 'cost')]:
        assert sha(DATA / 'closure' / name) == compact['paired_closure'][key + '_file_sha256']
    # The original older audit continuation writes an unsealed JSON terminal.
    # Do not fabricate a numeric-journal checksum or mutate that original file.
    final_audit = json.loads((DATA / 'closure/ended.json').read_text())
    assert final_audit['status'] == 'closed'
    assert final_audit['audit_file_sha256'] == compact['paired_closure']['audit_file_sha256']
    assert final_audit['cost_file_sha256'] == compact['paired_closure']['cost_file_sha256']
    final = read(DATA / 'readout/ended.json')
    assert final['status'] == 'closed' and final['steps'] == [
        {'stage': 'report-1', 'exit_code': 0}, {'stage': 'report-2', 'exit_code': 0}]
    assert {name: sha(DATA / 'readout' / name) for name in ('report.json', 'controls.csv', 'manifest.json')} == final['report_files']


def test_loss_expense_content_and_request_paths_match_literal_report():
    report = read(DATA / 'readout/report.json')
    assert report['full_scientist_request_sequences_equal'] and report['first_literal_request_difference'] is None
    worlds = report['worlds']
    assert [w['scores']['throughput'] for w in worlds] == [-36., -36.]
    assert [w['scores']['content-utility'] for w in worlds] == [-28.666666666666668] * 2
    assert [w['scores']['resource-aware-content'] for w in worlds] == [-8.666666666666668, -12.666666666666668]
    assert [w['resource_cost'] for w in worlds] == [200., 160.]
    assert [w['uncollected_activity_cost'] for w in worlds] == [0., 40.]
    assert [w['requested_activity_cost'] for w in worlds] == [200., 200.]
    assert all(w['request_sequence']['wire_requests'] == w['request_sequence']['completed_responses'] == 179 for w in worlds)
    assert report['accepted_content_overlap']['common']['occurrences'] == 36
    assert report['accepted_content_overlap']['common']['exact_centered_utility_sum'] == {'numerator': 86, 'denominator': 3}


def test_literal_programs_are_retained_without_synthesis_or_repair():
    expected = {'strong-related-reference': 'e2180df35de70a014e3a7d0dd982d0f285a69d496a74357f50a7860e4b6b37a5',
                'terminal-consolidation': 'e39499fd743f1ab1f1c2a874e3683f1ed89ca75cb64bb3354577872f08c34bc3'}
    for name, digest in expected.items():
        assert sha(DATA / 'systems' / (name + '.json')) == digest


def test_interpretation_figure_and_accounting_are_non_veto_derived_evidence():
    source = read(DATA / 'readout/report.json')
    directory = ROOT / 'paper/figures/native-terminal-cost-v1'
    result, manifest = read(directory / 'report.json'), read(directory / 'manifest.json')
    for name, digest in manifest['files'].items():
        assert sha(directory / name) == digest
    expected = derive(source)
    assert all(result[key] == value for key, value in expected.items())
    assert result['contrast_control_minus_reference']['reported_C_loss'] == -4
    assert result['contrast_control_minus_reference']['requested_cost_score_diagnostic_not_optimized'] == 0
    assert not result['requested_cost_score_is_optimized'] and not result['loss_or_selection_changed']
    assert not result['automatic_invention'] and not result['held_out_evaluation']
    with (directory / 'accounting.csv').open() as stream:
        assert len(list(csv.DictReader(stream))) == 2


def test_complete_role_totals_not_a_subset_or_added_cache_count():
    costs = read(DATA / 'closure/costs-1.json')
    assert costs['scientist']['completed_responses'] == 358
    usage = costs['scientist']['provider_usage']
    assert [usage[key]['recorded_sum'] for key in ('prompt_tokens', 'completion_tokens', 'cached_prompt_tokens')] == [537104, 32382, 79402]
    assert costs['common_content_observer']['physical_requests'] == 108
    assert costs['auxiliary']['groups']['load-scientist']['measurements']['transport_prompt_tokens']['recorded_sum'] is None
    assert not costs['unknown_usage_imputed'] and not costs['aliases_or_nested_durations_added']


def test_manuscript_preserves_declared_loss_gain_without_invention_or_efficiency_claim():
    text = ' '.join((ROOT / 'paper/integrated/native-terminal-cost.tex').read_text().split())
    for phrase in ('L_C=L_U+0.1K', 'not automatic institution invention',
                   'four units', 'D_R', 'not optimized', 'collection avoidance',
                   'No fifth-year continuation', 'Elementary end-horizon accounting',
                   '537,104 input', '15,337 output'):
        assert phrase in text
    assert 'Reference & $-36$ & $-28.67$ & $-8.67$ & 200 & 0 & 200 & 5 & 30' in text
    assert 'Consolidation & $-36$ & $-28.67$ & $-12.67$ & 160 & 40 & 200 & 1 & 70' in text
    assert '\\input{integrated/native-terminal-cost}' in (ROOT / 'paper/integrated.tex').read_text()
