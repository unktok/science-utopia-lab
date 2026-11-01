import pytest
import json
from pathlib import Path

from scripts.figures.native_society_v6 import FIXTURE, load_evidence, make_figure


def fixture():
    return {'schema': 'scienceutopia.native-society-v6-audit.v1', 'classification': FIXTURE,
        'status': 'complete', 'physical_societies': 1, 'adoptions': 2, 'audit_new_model_calls': 0,
        'causal_benefit_established': False, 'loss_path': [0., -3., -2.],
        'rows': [{'through_year': y, 'after_year': y - 1, 'loss': loss,
            'system_fingerprint': str(y) * 64, 'code': [None] * code,
            'actual_activity_effects': int(y > 1),
            'measurement': {'metrics': {key: {'status': 'measured', 'value': value} for key, value in (
                ('native.accepted_decisions', accepts), ('native.rejected_decisions', rejects),
                ('native.review_records', reviews))}}}
            for y, loss, accepts, rejects, reviews, code in [(1, 0., 0, 0, 0, 0), (2, -3., 3, 1, 12, 2), (3, -2., 2, 1, 9, 3)]]}


@pytest.mark.parametrize('mutate', [
    lambda r: r.update(status='incomplete'), lambda r: r.update(physical_societies=3),
    lambda r: r.update(causal_benefit_established=True), lambda r: r.update(audit_new_model_calls=1),
    lambda r: r.update(loss_path=[0, -9, -2]),
    lambda r: r['rows'][1].update(loss=None),
    lambda r: r['rows'][1].update(after_year=0),
    lambda r: r['rows'][1]['measurement']['metrics']['native.review_records'].update(value=-1),
])
def test_false_or_incomplete_evidence_is_not_a_loss_point(mutate):
    report = fixture(); mutate(report)
    with pytest.raises(ValueError):
        load_evidence(report)


def test_deterministic_fixture_bound_and_not_publishable_as_empirical_asset(tmp_path):
    from utopia.utils.data_utils import write_json_atomic
    path, output = tmp_path / 'fixture.json', tmp_path / 'fixture-figure'
    write_json_atomic(path, fixture(), sort_keys=True)
    manifest = make_figure(path, output)
    before = {suffix: output.with_suffix(suffix).read_bytes() for suffix in ('.pdf', '.png', '.manifest.json')}
    assert make_figure(path, output) == manifest
    assert before == {suffix: output.with_suffix(suffix).read_bytes() for suffix in before}
    assert not manifest['causal_benefit_established']
    assert [r['code_nodes'] for r in manifest['observed_intervals']] == [0, 2, 3]
    with pytest.raises(ValueError, match='paper/figures'):
        make_figure(path, tmp_path / 'paper/figures/fake')


def test_actual_auditor_adoption_receipt_list_is_not_mistaken_for_a_count():
    report = fixture()
    report['adoptions'] = [{'receipt': 'first'}, {'receipt': 'second'}]
    assert len(load_evidence(report)) == 3
    report['adoptions'].pop()
    with pytest.raises(ValueError, match='two actual adoptions'):
        load_evidence(report)


def test_published_figure_is_bound_to_actual_readonly_audit_and_reproduces(tmp_path):
    from utopia.utils.data_utils import file_sha256
    root = Path(__file__).resolve().parents[2]
    report = root / 'research/results/native-society-v6-a2.json'
    published = root / 'paper/figures/native-society-v6'
    manifest = json.loads(published.with_suffix('.manifest.json').read_text())
    assert manifest['classification'] == 'actual-native-qwen-online-design-pilot'
    assert manifest['source_report_sha256'] == file_sha256(report)
    assert manifest['generator_sha256'] == file_sha256(root / 'scripts/figures/native_society_v6.py')
    for suffix, expected in manifest['files'].items():
        assert file_sha256(published.with_suffix(suffix)) == expected
    assert make_figure(report, tmp_path / 'reproduced') == manifest
    audit = json.loads(report.read_text())
    assert audit['researcher_responses'] == 130
    assert audit['raw_files_verified_unchanged'] == 36
    assert audit['code_contexts']['one_to_one_physical_execution_proven'] is True
    assert [r['activity_plans']['code_authored_primary_plan_batches'] for r in audit['rows']] == [0, 0, 1]


def test_figure_ignores_and_restores_another_reports_plotting_defaults(tmp_path):
    import matplotlib
    from utopia.utils.data_utils import write_json_atomic
    report = tmp_path / 'fixture.json'
    write_json_atomic(report, fixture(), sort_keys=True)
    expected = make_figure(report, tmp_path / 'default')
    with matplotlib.rc_context({'axes.facecolor': 'magenta', 'font.size': 21,
                                'savefig.facecolor': 'yellow', 'axes.grid': True}):
        assert make_figure(report, tmp_path / 'polluted') == expected
        assert matplotlib.rcParams['axes.facecolor'] == 'magenta'
        assert matplotlib.rcParams['font.size'] == 21
