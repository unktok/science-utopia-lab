"""Retain actual conditional commands without relabeling them world outcomes."""
import csv
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data/native-reserve-command-response-v1'


def test_exact_retained_rows_and_figures_match_original_manifest():
    report = checked(json.loads((DATA / 'report.json').read_text()))
    manifest = checked(json.loads((DATA / 'manifest.json').read_text()))
    for name, expected in manifest['files'].items():
        directory = ROOT / 'paper/figures/native-reserve-command-response-v1' if name.startswith('reserve-command-response.') else DATA
        assert file_sha256(directory / name) == expected
    with (DATA / 'response.csv').open(newline='') as stream: rows = list(csv.DictReader(stream))
    for row in rows:
        for k in ('year', 'reserve_units', 'command_count', 'recipient_count', 'requested_units'): row[k] = int(row[k])
    assert rows == report['rows'] and len(rows) == report['new_code_executions'] == 240
    assert report['original_reserve21_replays_match']
    assert [f['distinct_transfer_outputs'] for f in report['frames']] == [19, 17, 15, 8]
    assert not report['interpretation']['native_transfer_commit_reexecuted']
    assert not report['interpretation']['loss_improvement_inferred_from_commands']
    assert report['interpretation']['new_model_calls'] == report['interpretation']['new_native_worlds'] == 0
    for year in range(1, 5):
        assert [r['reserve_units'] for r in rows if r['year'] == year] == list(range(1, 61))


def test_actual_year3_conditional_commands_are_nonmonotonic_without_loss_ranking():
    report = checked(json.loads((DATA / 'report.json').read_text()))
    by = {r['reserve_units']: r for r in report['rows'] if r['year'] == 3}
    assert (by[18]['recipient_count'], by[18]['requested_units']) == (3, 15)
    assert (by[19]['recipient_count'], by[19]['requested_units']) == (2, 10)
    assert by[26]['command_count'] == 0
    assert all('loss' not in r and 'activity_after' not in r for r in report['rows'])


def test_realized_ledger_join_is_separate_from_counterfactual_component_outputs():
    ledger = checked(json.loads((DATA / 'year3-realized-ledger.json').read_text()))
    assert ledger['recorded_transfer_commands_match_realized_ledger'] and ledger['all_resource_residuals_zero']
    rows = ledger['rows']; assert len(rows) == 5
    assert sum(r['opening_balance'] for r in rows) == ledger['opening_total'] == 90
    assert sum(r['closing_balance'] for r in rows) == ledger['closing_total'] == 60
    assert sum(r['grant_income'] for r in rows) == ledger['grant_income_total'] == 20
    assert sum(r['annual_research_cost'] for r in rows) == ledger['annual_cost_total'] == 50
    assert all(r['closing_balance'] > 0 and r['closing_active'] == (r['closing_balance'] > 10) for r in rows)
    assert sum(r['closing_active'] for r in rows) == 4
    assert not ledger['loss_or_selection_changed'] and ledger['new_model_calls'] == ledger['new_native_worlds'] == 0
