"""Bind new manuscript source to closed component data, not pending world results."""
import csv
import hashlib
import json
from pathlib import Path
import re

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data/native-reserve-command-response-v1'
SECTION = ROOT / 'paper/integrated/native-reserve-response.tex'


def test_exact_240_original_input_rows_and_joint_signatures_support_source_counts():
    rows = list(csv.DictReader((DATA / 'response.csv').open()))
    assert len(rows) == 240
    assert {(int(r['year']), int(r['reserve_units'])) for r in rows} == {
        (year, reserve) for year in range(1, 5) for reserve in range(1, 61)}
    assert [len({r['transfer_payload_sha256'] for r in rows if int(r['year']) == year})
        for year in range(1, 5)] == [19, 17, 15, 8]
    by = {(int(r['year']), int(r['reserve_units'])): r for r in rows}
    assert len({tuple(by[year, reserve]['transfer_payload_sha256'] for year in range(1, 5))
        for reserve in range(1, 61)}) == 23
    text = SECTION.read_text()
    for marker in ('All 240 calls complete', '19, 17, 15 and 8 distinct exact',
            'signature has 23 distinct values', 'not newly', 'does not alter any',
            'global policy equivalence', 'not a fairness floor', 'It does not predict'):
        assert marker in text


def test_actual_year3_table_matches_every_declared_reserve_projection():
    rows = {int(r['reserve_units']): r for r in csv.DictReader((DATA / 'response.csv').open())
        if r['year'] == '3'}
    reserves = [18, 19, 20, 21, 26]
    units = [int(rows[r]['requested_units']) for r in reserves]
    recipients = [int(rows[r]['recipient_count']) for r in reserves]
    assert units == [15, 10, 3, 5, 0] and recipients == [3, 2, 1, 2, 0]
    text = SECTION.read_text()
    assert 'Reserve &' + '&'.join(map(str, reserves)) in text
    assert 'Requested transfer units &' + '&'.join(map(str, units)) in text
    assert 'Recipients &' + '&'.join(map(str, recipients)) in text


def test_all_five_realized_founder_rows_and_inherited_attrition_are_retained():
    ledger = checked(json.loads((DATA / 'year3-realized-ledger.json').read_text()))
    rows = ledger['rows']; assert len(rows) == 5 and ledger['all_resource_residuals_zero']
    assert [r['opening_balance'] for r in rows] == [31, 17, 11, 11, 20]
    assert [r['closing_balance'] for r in rows] == [16, 11, 21, 1, 11]
    for r in rows:
        assert r['opening_balance'] + r['institution_transfer_in'] - r['institution_transfer_out'] \
            - r['annual_research_cost'] + r['grant_income'] == r['closing_balance']
    assert sum(r['closing_active'] for r in rows) == 4
    assert (ledger['opening_total'], ledger['annual_cost_total'], ledger['grant_income_total'],
        ledger['closing_total']) == (90, 50, 20, 60)
    assert "if getattr(agent, 'resources', None) and agent.resources <= 10" in ledger['actual_attrition_loop']
    assert not ledger['loss_or_selection_changed'] and ledger['new_native_worlds'] == ledger['new_model_calls'] == 0
    text = SECTION.read_text()
    for marker in ('0&31&$-5$&10&0&16&Yes', '1&17&4&10&0&11&Yes',
        '2&11&0&10&20&21&Yes', '3&11&0&10&0&1&No', '4&20&1&10&0&11&Yes',
        'Total&90&0&50&20&60&4/5', 'truthiness check also excludes exactly zero'):
        assert marker in text


def test_existing_real_figure_is_bound_and_old_reviewed_pdf_is_unchanged():
    manifest = checked(json.loads((DATA / 'manifest.json').read_text()))
    for ext in ('png', 'svg'):
        name = 'reserve-command-response.' + ext
        path = ROOT / 'paper/figures/native-reserve-command-response-v1' / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['files'][name]
    old = checked(json.loads((ROOT / 'paper/integrated-planning-search-build-v1.json').read_text()))
    assert old['pages'] == 69 and hashlib.sha256((ROOT / old['output']).read_bytes()).hexdigest() == old['pdf_sha256']
    assert 'Source ahead of PDF' in (ROOT / 'paper/README.md').read_text()
    assert '\\input{integrated/native-reserve-response}' in (ROOT / 'paper/integrated.tex').read_text()
    text = SECTION.read_text(); assert all(ord(c) < 128 for c in text)
    labels = re.findall(r'\\label\{([^}]+)\}', text)
    assert len(labels) == len(set(labels)) == 4
