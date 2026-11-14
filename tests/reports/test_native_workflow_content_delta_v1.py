"""SCRIPTED fixed-record arithmetic, not new native/scientist evaluations."""
import pytest

from scripts.reports.native_workflow_content_delta_v1 import analyze
from utopia.system.design_patch import clone, digest


def seal(value):
    value.pop('content_sha256', None)
    value['content_sha256'] = digest(value)
    return value


def fixture():
    def record(paper, year, score):
        return {'paper_id': paper, 'year': year, 'rating': {'status': 'measured',
            'ratings': [{'score': score}] * 3, 'mean_score': float(score), 'content_sha256': digest(paper)}}
    sets = {'R7': [record('shared', 1, 4), record('r7-only', 2, 3)],
        'hand': [record('shared', 1, 4), record('hand-only', 2, 4)],
        'U2': [record('shared', 1, 4), record('own-only', 2, 3)], 'failed': None}
    worlds = []; observations = {}
    for key, rows in sets.items():
        complete = rows is not None; n = len(rows or [])
        u = sum(r['rating']['mean_score'] - 3 for r in rows or [])
        scores = {'throughput': -float(n), 'content-utility': -float(u)} if complete else dict.fromkeys(('throughput', 'content-utility'))
        objective = 'content-utility' if key == 'U2' else 'throughput'
        w = {'identity': key, 'role': 'SCRIPTED', 'seed': 1, 'system': {'SCRIPTED': key},
            'status': 'complete' if complete else 'failed', 'scores': scores, 'objective': objective}
        o = {'suggestion_id': key, 'candidate': clone(w['system']), 'status': w['status'], 'loss': scores[objective]}
        if complete:
            observer = seal({'accepted_decisions': rows, 'unique_contents': n})
            metrics = {'native.accepted_decisions': {'status': 'measured', 'value': n},
                'native.common_content_score_sum': {'status': 'measured', 'value': 3 * n + u},
                'native.common_content_utility_sum': {'status': 'measured', 'value': u}}
            o['metadata'] = {'measurements': [{'common_content_observer': observer, 'metrics': metrics}]}
        worlds.append(w); observations[key] = o
    audit = seal({'schema': 'scienceutopia.native-workflow-objective-loop-audit.v1',
        'source_commit': 'SCRIPTED', 'plan_sha256': '0' * 64,
        'closure': {'terminal': {'status': 'closed'}}, 'source_proof': {'status': 'verified-exact-source-closure'},
        'held_out_evaluation': False, 'new_model_calls': 0, 'new_code_executions': 0, 'worlds': worlds})
    slots = [{'objective': o, 'generation': g, 'status': 'generation-null', 'physical_job': None}
        for o, g in [('throughput', 0), ('content-utility', 0), ('content-utility', 1),
            ('throughput', 1), ('throughput', 2), ('content-utility', 2)]]
    slots[0].update(status='failed', physical_job='failed')
    slots[-1].update(status='complete', physical_job='U2')
    report = seal({'schema': 'scienceutopia.native-workflow-objective-report.v1',
        'source_commit': audit['source_commit'], 'plan_sha256': audit['plan_sha256'],
        'audit_content_sha256': audit['content_sha256'], 'score_order': ['throughput', 'content-utility'],
        'physical_worlds': 4, 'references': [{'label': k, 'physical_job': k} for k in ('R7', 'hand')], 'slots': slots})
    return report, audit, observations


def test_all_pairs_reconstruct_without_causal_or_zero_filled_nulls():
    report, audit, obs = fixture(); before = clone([report, audit, obs])
    result = analyze(report, audit, obs)
    assert [report, audit, obs] == before
    assert len(result['all_slots']) == 6 and len(result['all_complete_pairs']) == 3
    failed, = [w for w in result['worlds'] if w['status'] == 'failed']
    assert failed['accepted_records'] is None and failed['sign_counts'] is None
    pair, = [p for p in result['all_complete_pairs'] if (p['left'], p['right']) == ('R7', 'U2')]
    assert pair['overlap']['common']['occurrences'] == 1
    assert pair['overlap']['left_only']['occurrences'] == pair['overlap']['right_only']['occurrences'] == 1
    assert pair['overlap']['left_minus_right']['utility_loss_at_declared_center_3'] == 0
    assert result['new_model_calls'] == result['new_native_worlds'] == result['new_code_executions'] == 0
    assert not result['loss_changed'] and not result['selection_changed']


@pytest.mark.parametrize('change', ['missing-observation', 'missing-generation-null', 'scientific-null-zero',
    'wrong-loss', 'mixed-seeds', 'inconsistent-fixed-rating'])
def test_incomplete_or_inconsistent_evidence_is_not_a_content_comparison(change):
    report, audit, obs = fixture()
    if change == 'missing-observation': obs.pop('failed')
    elif change == 'missing-generation-null': report['slots'].pop(1)
    elif change == 'scientific-null-zero': audit['worlds'][-1]['scores']['throughput'] = 0.
    elif change == 'wrong-loss': obs['U2']['loss'] = -999.
    elif change == 'mixed-seeds': audit['worlds'][0]['seed'] = 2
    else:
        rating = obs['U2']['metadata']['measurements'][0]['common_content_observer']
        rating['accepted_decisions'][0]['rating'].update(ratings=[{'score': 5}] * 3, mean_score=5.)
        seal(rating)
    seal(audit); report['audit_content_sha256'] = audit['content_sha256']; seal(report)
    with pytest.raises(ValueError): analyze(report, audit, obs)
