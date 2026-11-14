"""Literal workflow selection handoff, not unused-world scientific evaluation."""
import pytest

from scripts.run_native_objective_fixed_evaluation_v1 import fixed_selection
from tests.reports.test_native_workflow_objective_report_v1 import fixture
from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import clone, digest


def seal(value):
    value = {k: v for k, v in clone(value).items() if k != 'content_sha256'}
    return {**value, 'content_sha256': digest(value)}


def evidence(*, all_null=False):
    p, a, _ = fixture(all_null=all_null)
    p = seal(p)
    s = seal({**a['selection'], 'schema': 'scienceutopia.native-workflow-objective-loop.v1.selection',
        'plan_sha256': p['content_sha256'], 'baseline_fallback': False, 'held_out_evaluation': False})
    a.update(plan_sha256=p['content_sha256'], selection=s, held_out_evaluation=False)
    return p, seal(a)


def test_exact_original_workflow_ties_and_system_are_returned_without_reselection_or_added_count():
    p, a = evidence(); before = clone(a)
    selected = fixed_selection(p, a, study='workflow-v1')
    assert selected == checked(a['selection']) and a == before
    t = selected['selected']['throughput']
    assert t['selected_id'] == 'throughput:1' and t['all_tied_ids'] == ['throughput:1', 'throughput:2']
    assert 'completed_submissions' not in t


def test_all_null_workflow_pool_stays_null_even_when_a_reference_has_finite_loss():
    p, a = evidence(all_null=True)
    selected = fixed_selection(p, a, study='workflow-v1')
    assert all(v['loss'] is None and v['system'] is None and v['selected_id'] is None
        and not v['all_tied_ids'] for v in selected['selected'].values())


@pytest.mark.parametrize('change', ['reference-fallback', 'later-tie', 'missing-tie', 'loss',
    'system', 'stopped', 'wrong-source', 'wrong-plan', 'held-out'])
def test_selection_cannot_be_revised_using_a_reference_or_evaluation(change):
    p, a = evidence(); s = clone(a['selection']); t = s['selected']['throughput']
    if change == 'reference-fallback':
        t['selected_id'] = a['worlds'][0]['identity']; t['system'] = clone(a['worlds'][0]['system'])
    elif change == 'later-tie':
        t['selected_id'] = 'throughput:2'
    elif change == 'missing-tie':
        t['all_tied_ids'] = ['throughput:1']
    elif change == 'loss':
        t['loss'] = -999
    elif change == 'system':
        t['system']['schedules'][0]['phase'] = 99
    elif change == 'stopped':
        a['closure']['terminal']['status'] = 'stopped'
    elif change == 'wrong-source':
        a['source_commit'] = 'a' * 40
    elif change == 'wrong-plan':
        s['plan_sha256'] = 'a' * 64
    else:
        a['held_out_evaluation'] = True
    a['selection'] = seal(s); a = seal(a)
    with pytest.raises(ValueError):
        fixed_selection(p, a, study='workflow-v1')
