"""SCRIPTED cross-objective figure QA, not new inference or study evidence."""
from copy import deepcopy
import hashlib
import json

import pytest

from scripts.figures import native_design_cross_objective as figures
from tests.reports.test_native_design_benchmark_report import hashed
from tests.reports.test_native_design_evaluation_figures import sample, varied_sample


def two_policies():
    r = varied_sample()
    for row in r['selection']['selected'].values(): row['policy_sha256'] = 'SCRIPTED-target-policy'
    for job in r['evaluation']:
        if job['labels'][0].startswith('selected:'): job['policy_sha256'] = 'SCRIPTED-target-policy'
    return hashed(r)


def initial_and_new_policies():
    """SCRIPTED one initial-selected row, other selected rows distinct from it."""
    from scripts.reports.native_design_benchmark import descriptive
    r = two_policies(); arm = 'throughput:parameters'; label = 'selected:' + arm
    r['selection']['selected'][arm].update(selected_row_id='reference:open-seed',
        all_tied_row_ids=['reference:open-seed'], policy_sha256='SCRIPTED-policy')
    lookup = {}
    for job in r['evaluation']:
        if job['labels'][0].startswith('selected:'): job['labels'].remove(label)
        else:
            job['labels'].append(label); lookup[job['seed'], job['years']] = job
    for objectives in r['paired_vs_all_references'][arm].values():
        for loss, horizons in objectives.items():
            for block in horizons.values():
                for pair in block['pairs']:
                    target = lookup[pair['seed'], pair['years']]; value = target['cross_scores'][loss]
                    pair.update(target_job_id=target['job_id'], physically_shared=True,
                        target_loss=value, difference=0. if value is not None else None)
                block['summary'] = descriptive(block['pairs'], 'difference')
    return hashed(r)


def test_paper_layout_preserves_every_row_point_null_and_sharing(tmp_path):
    from PIL import Image
    r = initial_and_new_policies(); before = deepcopy(r)
    overview = figures.plot_cross_objective(r, tmp_path / 'overview')
    paper = figures.plot_cross_objective(r, tmp_path / 'paper', paper=True)
    assert r == before
    assert overview['layout_profile'] == 'overview-8.2in-v1'
    assert paper['layout_profile'] == 'paper-5.5in-v1'
    assert overview['plot_data_content_sha256'] == paper['plot_data_content_sha256']
    assert (tmp_path / 'overview/plot-data.json').read_bytes() == (tmp_path / 'paper/plot-data.json').read_bytes()
    for years in (2, 4):
        with Image.open(tmp_path / f'paper/cross-objective-{years}y.png') as img:
            assert img.size == (990, 1170)


def test_every_policy_all_three_scores_raw_seeds_nulls_and_physical_sharing_remain():
    r = sample(); before = deepcopy(r); data = figures.cross_objective_data(r)
    assert r == before and data == figures.cross_objective_data(r)
    assert len(data['panels']) == 2 and data['loss_order'] == ['throughput', 'selective', 'efficiency']
    assert data['physical_policies'] == 1 and data['logical_evaluation_labels'] == 19
    assert data['physical_evaluation_jobs'] == 6  # SCRIPTED all19 labels share one exact policy.
    for panel in data['panels']:
        assert len(panel['rows']) == 19
        assert panel['single_seed_diagnostic'] == (panel['years'] == 4)
        for row in panel['rows']:
            assert row['physical_group'] == 'P01'
            for loss in figures.LOSSES:
                cell = row['cells'][loss]
                assert [p['seed'] for p in cell['points']] == panel['seeds']
                for point in cell['points']:
                    physical = next(j for j in r['evaluation'] if j['job_id'] == point['job_id'])
                    assert point['value'] == physical['cross_scores'][loss]
                    assert len(point['shared_labels']) == 19
    row = data['panels'][0]['rows'][-1]
    assert row['cells']['throughput']['summary']['available'] == 4
    assert row['cells']['efficiency']['summary']['available'] == 3
    assert row['all_tied_row_ids'] == r['selection']['selected']['selective:random']['all_tied_row_ids']
    assert data['horizons_pooled'] is data['null_losses_imputed'] is data['losses_normalized_or_aggregated'] is False


def test_distinct_policies_share_only_their_actual_jobs_and_keep_all_raw_values():
    r = two_policies(); data = figures.cross_objective_data(r)
    assert data['physical_policies'] == 2 and data['physical_evaluation_jobs'] == 12
    rows = data['panels'][0]['rows']
    assert {x['physical_group'] for x in rows[:9]} == {'P01'}
    assert {x['physical_group'] for x in rows[9:]} == {'P02'}
    assert [p['value'] for p in rows[9]['cells']['throughput']['points']] == [-9., -4., -7., None, -2.]
    assert rows[9]['cells']['throughput']['summary']['mean'] == -5.5


def test_no_selection_is_distinct_from_selected_policy_with_all_missing_scores():
    r = sample(); arm = 'throughput:parameters'; label = 'selected:' + arm
    r['selection']['selected'][arm]['system'] = None
    r['paired_vs_all_references'][arm] = {}
    for job in r['evaluation']: job['labels'].remove(label)
    r['logical_evaluation_labels'] -= 1; hashed(r)
    data = figures.cross_objective_data(r)
    for panel in data['panels']:
        row = next(x for x in panel['rows'] if x['label'] == label)
        assert row['selection_available'] is False and row['physical_group'] is None
        assert all(c['summary'] is None and c['points'] == [] for c in row['cells'].values())


def test_initial_selection_is_labeled_as_initial_not_a_successful_authored_invention():
    r = initial_and_new_policies()
    data = figures.cross_objective_data(r)
    for panel in data['panels']:
        initial = next(x for x in panel['rows'] if x['label'] == 'selected:throughput:parameters')
        assert initial['initial_reference_selected'] and initial['display'].endswith('*')
        assert initial['physical_group'] == panel['rows'][1]['physical_group']
        assert not panel['rows'][0]['initial_reference_selected']


def test_initial_label_cannot_hide_a_different_policy_or_extra_job():
    r = two_policies()
    r['selection']['selected']['throughput:parameters']['selected_row_id'] = 'reference:open-seed'; hashed(r)
    with pytest.raises(ValueError, match='initial selection must share'):
        figures.cross_objective_data(r)


def test_all_missing_still_has_scheduled_points_and_never_fabricated_zero_or_mean():
    from tests.reports.test_native_design_benchmark_report import fixture
    from scripts.reports.native_design_benchmark import project
    p, a = fixture()
    for entry in a['evaluated'].values():
        for score in entry['scores'].values(): score['loss'] = None
        entry['observation']['status'] = 'failed'
    hashed(a); r = project(p, a, expected_source=p['source_commit'])
    data = figures.cross_objective_data(r)
    for panel in data['panels']:
        for row in panel['rows']:
            for cell in row['cells'].values():
                assert cell['summary']['available'] == 0 and cell['summary']['mean'] is None
                assert len(cell['points']) == len(panel['seeds'])
                assert all(p['value'] is None for p in cell['points'])


def test_live_progress_schema_cannot_become_closed_report_figures():
    with pytest.raises(ValueError, match='schema/content hash'):
        figures.cross_objective_data({'schema': figures.SCHEMA + '.progress'})


@pytest.mark.parametrize('mutate', [
    lambda r: r['evaluation'][0]['cross_scores'].update(efficiency=999.),
    lambda r: r['paired_vs_all_references']['throughput:parameters']['legacy']['efficiency']['2']['pairs'][0].update(difference=999.),
    lambda r: r['evaluation'][1].update(policy_sha256='CHANGED-POLICY'),
    lambda r: r['selection']['selected']['throughput:parameters'].update(policy_sha256='WRONG'),
    lambda r: r['evaluation'][0]['labels'].append('selected:invented'),
    lambda r: r['evaluation'][1].update(job_id=r['evaluation'][0]['job_id']),
    lambda r: r.update(logical_evaluation_labels=99),
    lambda r: r.update(physical_evaluation_jobs=99),
    lambda r: r['reference_scores'].pop('open-reject-all'),
    lambda r: r['evaluation'][0]['cross_scores'].pop('efficiency'),
])
def test_rehashed_cross_scores_identity_conditions_and_third_loss_tampering_are_rejected(mutate):
    r = sample(); mutate(r); hashed(r)
    with pytest.raises(ValueError): figures.cross_objective_data(r)


@pytest.mark.parametrize('bad', [True, float('inf'), float('nan')])
def test_third_loss_is_not_allowed_to_contain_boolean_or_nonfinite_points(bad):
    r = sample(); r['evaluation'][0]['cross_scores']['efficiency'] = bad
    if type(bad) is bool: hashed(r)
    with pytest.raises(ValueError): figures.cross_objective_data(r)


def test_even_same_policy_cannot_be_split_into_unapproved_extra_physical_replicates():
    r = varied_sample()  # Two jobs/condition falsely claim the same exact policy identity.
    with pytest.raises(ValueError, match='split into multiple physical jobs'):
        figures.cross_objective_data(r)


def test_rendered_files_are_watermarked_bound_and_fresh_without_changing_report(tmp_path):
    r = initial_and_new_policies(); before = deepcopy(r); output = tmp_path / 'figures'
    m = figures.plot_cross_objective(r, output)
    assert r == before and len(m['files']) == 5
    assert m['input_report_content_sha256'] == r['content_sha256']
    assert m['new_model_calls'] == m['new_code_executions'] == 0
    for name, digest in m['files'].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    for path in output.glob('*.svg'):
        text = path.read_text()
        assert 'SCRIPTED QA - NOT EXPERIMENTAL RESULTS' in text
        assert 'Null: outside data axis' in text
        assert 'E = -Q + 0.5R' in text
    with pytest.raises(ValueError, match='fresh'): figures.plot_cross_objective(r, output)


def test_cli_preserves_the_report_and_never_dispatches_a_candidate(tmp_path, monkeypatch):
    r = sample(); source = tmp_path / 'report.json'; source.write_text(json.dumps(r)); before = source.read_bytes()
    calls = []
    monkeypatch.setattr(figures, '_render', lambda *args, **kwargs: calls.append(kwargs))
    assert figures.main(['--report', str(source), '--output', str(tmp_path / 'figures')]) == 0
    assert calls == [{'paper': False}, {'paper': False}]
    assert source.read_bytes() == before
