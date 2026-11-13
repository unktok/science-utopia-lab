"""Arithmetic/retention fixtures, not executable native institutions or gains."""
import pytest

from scripts.reports.native_workflow_objective_loop_v1 import graph_change, summarize
from utopia.system.design_patch import clone, digest


def fixture(*, all_null=False):
    base = {'mechanisms': [{'mechanism_id': 'a', 'parameters': {'literal': 21}}],
        'schedules': [{'mechanism_id': 'a', 'phase': 1, 'trigger': 'annual'}], 'connections': [],
        'SCRIPTED': 'analysis shape only, not a native world'}
    timing = clone(base); timing['schedules'][0]['phase'] = 2
    objectives = ['throughput', 'content-utility']
    p = {'schema': 'scienceutopia.native-workflow-objective-loop.v1.plan', 'source_commit': 'f' * 40,
        'content_sha256': 'e' * 64, 'initial_system': base, 'objectives': objectives,
        'reference_order': ['R7-original', 'post-funding-cost'],
        'reference_systems': {'R7-original': base, 'post-funding-cost': timing},
        'losses': {o: {'SCRIPTED': o} for o in objectives},
        'schedule': [{'objective': o, 'generation': g} for g in range(3) for o in objectives]}
    a = {'schema': 'scienceutopia.native-workflow-objective-loop-audit.v1', 'source_commit': p['source_commit'],
        'plan_sha256': p['content_sha256'], 'content_sha256': 'd' * 64,
        'source_proof': {'status': 'verified-exact-source-closure', 'SCRIPTED': 'not an actual source proof'},
        'closure': {'terminal': {'status': 'closed', 'SCRIPTED': True}}, 'new_model_calls': 0,
        'new_code_executions': 0, 'worlds': [], 'selection': {'selected': {}}}
    for label, scores in zip(p['reference_order'], [(-10, -10), (-12, -8)]):
        a['worlds'].append({'identity': 'workflow-reference-' + label.lower(), 'role': 'developer-reference',
            'system': clone(p['reference_systems'][label]), 'status': 'complete',
            'scores': dict(zip(objectives, scores))})
    records = {}
    for o in objectives:
        for g, value in enumerate([-9, -13, -13] if o == 'throughput' else [None, -7, -9]):
            request = {'generation': g, 'loss_spec': p['losses'][o], 'parent_system': clone(base)}
            r = {'request': request, 'request_sha256': digest(request), 'generation_error': None,
                'observations': [], 'draws': []}
            if all_null or value is None:
                r['generation_error'] = {'type': 'SCRIPTED invalid submission', 'loss': None}
            else:
                identity = o + ':' + str(g); candidate = clone(timing)
                r['draws'] = [{'suggestion': {'candidate': candidate}, 'technical_error': None}]
                r['observations'] = [{'suggestion_id': identity, 'candidate': candidate,
                    'loss': value, 'status': 'complete'}]
                scores = dict(zip(objectives, (value, value)))
                a['worlds'].append({'identity': identity, 'role': 'workflow-own-proposal', 'objective': o,
                    'system': candidate, 'status': 'complete', 'scores': scores})
            records[o, g] = r
        own = [w for w in a['worlds'] if w.get('objective') == o]
        best = min((w['scores'][o] for w in own), default=None)
        ties = [w for w in own if w['scores'][o] == best]
        a['selection']['selected'][o] = {'loss': best, 'all_tied_ids': [w['identity'] for w in ties],
            'selected_id': ties[0]['identity'] if ties else None, 'system': clone(ties[0]['system']) if ties else None}
    return p, a, records


def test_all_slots_null_ties_and_known_versus_generated_paths_remain_distinct():
    p, a, r = fixture(); result = summarize(p, a, r)
    assert len(result['slots']) == 6 and result['physical_worlds'] == 7
    t, u = result['loss_paths']['throughput'], result['loss_paths']['content-utility']
    assert t[0]['best_own_loss'] == -9 and t[0]['best_known_loss'] == -12
    assert t[1]['best_own_loss'] == t[1]['best_known_loss'] == -13
    assert u[0]['best_own_loss'] is None and u[0]['best_known_loss'] == -10
    assert u[2]['best_own_loss'] == -9 and u[2]['best_known_loss'] == -10
    assert result['selection']['selected']['throughput']['selected_id'] == 'throughput:1'
    assert result['slots'][1]['generation_error'] and result['slots'][1]['loss'] is None
    assert result['slots'][0]['graph_from_parent']['phase_updates'] == {'a': {'before': 1, 'after': 2}}


def test_all_null_own_outputs_do_not_get_replaced_by_known_references():
    p, a, r = fixture(all_null=True); result = summarize(p, a, r)
    assert result['physical_worlds'] == 2 and len(result['slots']) == 6
    assert all(v['system'] is None and v['loss'] is None for v in result['selection']['selected'].values())
    assert all(v['best_own_loss'] is None and v['best_known_loss'] is not None
        for rows in result['loss_paths'].values() for v in rows)


def test_native_failure_is_kept_apart_from_a_generation_null():
    p, a, r = fixture()
    o = r['throughput', 0]['observations'][0]; o.update(status='failed', loss=None)
    w = next(w for w in a['worlds'] if w['identity'] == 'throughput:0')
    w.update(status='failed', scores={key: None for key in p['objectives']})
    result = summarize(p, a, r)
    assert result['physical_worlds'] == 7
    assert result['slots'][0]['status'] == 'failed' and result['slots'][0]['physical_job'] == 'throughput:0'
    assert result['slots'][1]['status'] == 'generation-null' and result['slots'][1]['physical_job'] is None
    assert result['loss_paths']['throughput'][0]['best_own_loss'] is None
    assert result['loss_paths']['throughput'][0]['best_known_loss'] == -12


def test_literal_graph_edges_keep_multiset_counts():
    p, _, _ = fixture(); base = p['initial_system']; changed = clone(base)
    edge = {'source_mechanism': 'a', 'target_mechanism': 'b', 'channel': 'artifact'}
    changed['connections'] = [edge, edge]
    diff = graph_change(base, changed)
    assert diff['added_connections'] == [edge, edge] and not diff['removed_connections']


@pytest.mark.parametrize('case', ['missing-slot', 'missing-null-error', 'duplicate-world', 'wrong-selected',
    'wrong-request', 'wrong-loss', 'unaccounted-world', 'changed-source', 'changed-trigger'])
def test_unsupported_missing_or_mismatched_evidence_fails(case):
    p, a, r = fixture()
    if case == 'missing-slot': r.pop(('throughput', 0))
    elif case == 'missing-null-error': r['content-utility', 0]['generation_error'] = None
    elif case == 'duplicate-world': a['worlds'].append(clone(a['worlds'][0]))
    elif case == 'wrong-selected': a['selection']['selected']['content-utility']['selected_id'] = 'workflow-reference-r7-original'
    elif case == 'wrong-request': r['throughput', 0]['request']['generation'] = 9
    elif case == 'wrong-loss': r['throughput', 0]['observations'][0]['loss'] = -999
    elif case == 'unaccounted-world':
        a['worlds'].append({**clone(a['worlds'][0]), 'identity': 'unaccounted'})
    else:
        for candidate in (r['throughput', 0]['observations'][0]['candidate'],
                r['throughput', 0]['draws'][0]['suggestion']['candidate'], a['worlds'][2]['system']):
            if case == 'changed-source': candidate['mechanisms'][0]['parameters']['literal'] = 3
            else: candidate['schedules'][0]['trigger'] = 'not-annual'
    with pytest.raises(ValueError): summarize(p, a, r)
