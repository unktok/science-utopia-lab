"""SCRIPTED report-contract tests, not original-source scientific audits."""
import pytest

from scripts.figures.native_workflow_controls_paper_v1 import summarize, AUDIT_SCHEMA, LABELS
from utopia.system.design_patch import digest


def fixture():
    worlds, traces = [], []
    for identity in LABELS:
        checkpoints = [{'year': i, 'checkpoint_sha256': str(i) * 64} for i in range(1, 5)]
        worlds.append({'identity': identity, 'status': 'complete', 'role': 'developer-reference', 'seed': 61001,
            'scores': {'throughput': -12, 'content-utility': -8},
            'physical_proof': {'status': 'complete', 'annual_checkpoints': checkpoints}})
        traces.append({'identity': identity, 'annual': [{**r, 'active_founders': 5,
            'total_founder_resources': 100 - 10 * r['year'], 'workflow_boundary': {'all_author_cashflows': {
                'grant_income': 20, 'annual_research_cost': 30, 'institution_transfer_out': 2,
                'institution_transfer_in': 2}}} for r in checkpoints]})
    a = {'schema': AUDIT_SCHEMA, 'scientific_study_closed': False,
        'original_closure': {'terminal': {'status': 'stopped'}}, 'selection': None,
        'fixed_evaluation_eligible': False, 'source_proof': {'status': 'verified-exact-source-closure'},
        'new_model_calls': 0, 'new_code_executions': 0, 'worlds': worlds, 'effect_traces': traces,
        'source_commit': 'SCRIPTED', 'external_adapter': {'source_commit': 'SCRIPTED'}}
    return a


def seal(a): return {**a, 'content_sha256': digest(a)}


def test_keeps_all_actual_coordinates_and_stopped_scope():
    a = fixture(); data = summarize(seal(a))
    assert len(data['worlds']) == 2 and not data['scientific_study_closed']
    assert not data['automatic_invention'] and not data['additional_objective_or_veto']
    assert [r['original_author_resources'] for r in data['worlds'][0]['annual']] == [90, 80, 70, 60]
    assert data['worlds'][0]['scores'] == a['worlds'][0]['scores']


@pytest.mark.parametrize('kind', ['normal-closure', 'changed-seed', 'changed-checkpoint'])
def test_cannot_relabel_closure_or_join_different_worlds(kind):
    a = fixture()
    if kind == 'normal-closure': a['scientific_study_closed'] = True
    elif kind == 'changed-seed': a['worlds'][0]['seed'] = 61011
    else: a['effect_traces'][0]['annual'][0]['checkpoint_sha256'] = 'b' * 64
    with pytest.raises(ValueError): summarize(seal(a))
