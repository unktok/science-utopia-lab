"""SCRIPTED table QA, not study outcomes or a full original-source audit."""
from copy import deepcopy
import hashlib
import json

import pytest

from scripts.reports import native_design_benchmark as projection
from scripts.reports import native_design_tex as table
from tests.reports.test_native_design_benchmark_report import fixture, hashed


def report():
    plan, audit = fixture()
    for arm, selection in audit['selection']['selected'].items():
        ties = [f'{run}:{arm}:g3' for run in table.RUNS]
        selection.update(all_tied_row_ids=ties, selected_row_id=ties[0])
    hashed(audit['selection']); hashed(audit)
    return projection.project(plan, audit, expected_source=plan['source_commit'])


def summarize(value):
    return table.summarize(value, expected_source=value['source_commit'])


def reselect(value, arm):
    objective = arm.split(':')[0]
    initial = value['reference_scores']['open-seed'][objective]
    pool = [('reference:open-seed', initial)] + [(r['row_id'], r['own_loss'])
        for run in table.RUNS for r in value['search_arms'][run][arm]['rows']]
    available = [(identity, loss) for identity, loss in pool if loss is not None]
    best = min((loss for _, loss in available), default=None)
    ties = [identity for identity, loss in available if loss == best]
    value['selection']['selected'][arm].update(loss=best, all_tied_row_ids=ties,
        selected_row_id=ties[0] if ties else None)
    hashed(value)


def test_all_slots_nulls_and_exact_ties_are_retained_without_mutation():
    value = report(); before = deepcopy(value)
    data = summarize(value)
    assert value == before and data == summarize(value)
    assert len(data['rows']) == 10 and sum(r['scheduled'] for r in data['rows']) == 120
    assert data['counts'] == {'complete': 90, 'technical-failure': 30}
    assert all(r['measured_assigned_losses'] == 9 and len(r['all_tied_row_ids']) == 3 for r in data['rows'])
    body = table.render(data)
    assert body.count('9/12') == 10 and 'SCRIPTED QA -- NOT EXPERIMENTAL RESULTS' in body
    assert 'M-null' in body and 'not independent environment replications' in body
    assert data['new_model_calls'] == data['new_code_executions'] == 0


def test_initial_selection_is_not_invented_or_counted_as_extra_candidate():
    value = report(); arm = 'throughput:parameters'
    for run in table.RUNS:
        for row in value['search_arms'][run][arm]['rows']:
            row.update(status='generation-failure', own_loss=None)
            row['cross_scores']['throughput'] = None
    reselect(value, arm)
    data = summarize(value); row = data['rows'][0]
    assert row['scheduled'] == 12 and row['measured_assigned_losses'] == 0
    assert row['selected_initial'] and row['all_tied_row_ids'] == ['reference:open-seed']
    assert r'0.000$^{\ast}$' in table.render(data)


def test_display_rounding_does_not_create_ties():
    value = report(); arm = 'throughput:parameters'
    row = value['search_arms']['run-00'][arm]['rows'][3]
    row['own_loss'] = row['cross_scores']['throughput'] = -4.000000000000001
    reselect(value, arm)
    result = summarize(value)['rows'][0]
    assert result['all_tied_row_ids'] == [row['row_id']]
    assert '-4.000' in table.render(summarize(value))


def test_missing_assigned_metric_is_separate_from_execution_and_generation():
    value = report(); arm = 'throughput:parameters'
    row = value['search_arms']['run-00'][arm]['rows'][2]
    row['status'] = 'loss-unavailable'; hashed(value)
    result = summarize(value)['rows'][0]
    assert result['status_counts']['loss-unavailable'] == 1
    assert result['status_counts']['technical-failure'] == 2
    assert result['measured_assigned_losses'] == 9


@pytest.mark.parametrize('mutate', [
    lambda v: v['all_candidate_rows'].pop(),
    lambda v: v['all_candidate_rows'].append(deepcopy(v['all_candidate_rows'][0])),
    lambda v: v['all_candidate_rows'][0].update(status='unknown'),
    lambda v: v['all_candidate_rows'][0].update(generation=True),
    lambda v: v['all_candidate_rows'][0].update(own_loss=False),
    lambda v: v['all_candidate_rows'][0]['cross_scores'].update(throughput=999),
    lambda v: v['selection']['selected']['throughput:parameters']['all_tied_row_ids'].pop(),
    lambda v: v['selection']['selected']['throughput:parameters'].update(selected_row_id='reference:open-seed'),
    lambda v: v['selection']['selected']['throughput:parameters'].update(loss=-99),
    lambda v: v['selection']['selected']['throughput:parameters'].update(system=None),
    lambda v: v['search_arms']['run-00']['throughput:parameters']['rows'].pop(),
    lambda v: v['search_arms']['run-00']['throughput:parameters'].update(initial_loss=99),
    lambda v: v.update(source_commit='wrong'),
    lambda v: v.update(input_audit_content_sha256='not-an-audit-hash'),
])
def test_rehashed_inconsistent_rows_selections_and_bindings_are_rejected(mutate):
    value = report(); mutate(value); hashed(value)
    with pytest.raises(ValueError): summarize(value)


def test_unknown_hash_or_wrong_expected_source_is_not_accepted():
    value = report(); value['classification'] = 'tampered'
    with pytest.raises(ValueError): summarize(value)
    value = report()
    with pytest.raises(ValueError): table.summarize(value, expected_source='e' * 40)


def test_cli_is_fresh_deterministic_and_does_not_edit_inputs(tmp_path):
    value = report(); source = tmp_path / 'closed-report.json'
    source.write_text(json.dumps(value)); before = source.read_bytes()
    for name in ('one', 'two'):
        assert table.main(['--report', str(source), '--expected-source', value['source_commit'],
            '--output', str(tmp_path / name)]) == 0
    assert source.read_bytes() == before
    for path in (tmp_path / 'one').iterdir():
        assert path.read_bytes() == (tmp_path / 'two' / path.name).read_bytes()
    manifest = json.loads((tmp_path / 'one' / 'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        assert hashlib.sha256((tmp_path / 'one' / name).read_bytes()).hexdigest() == expected
    with pytest.raises(SystemExit):
        table.main(['--report', str(source), '--expected-source', value['source_commit'],
            '--output', str(tmp_path / 'one')])
