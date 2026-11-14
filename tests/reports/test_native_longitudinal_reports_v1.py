"""SCRIPTED joins/paths/nulls/contrasts, not physical or scientific attestations."""
from copy import deepcopy

from scripts.reports import native_workflow_objective_loop_v1 as development
from scripts.reports import native_objective_fixed_evaluation_v1 as fixed_report
from scripts import run_native_longitudinal_fixed_evaluation_v1 as fixed
from scripts import run_native_longitudinal_comparison_v1 as driver
from tests.reports.test_native_longitudinal_comparison_v1 import plan, closed, sealed
from utopia.optimization.native_longitudinal_feedback_v1 import VIEW
from utopia.system.design_patch import clone, digest


def development_fixture(tmp_path, monkeypatch):
    p, _ = plan(tmp_path, monkeypatch); a = closed(p)
    references = [{'identity': 'workflow-reference-'+label.lower(), 'role': 'developer-reference',
        'status': 'complete', 'system': clone(p['reference_systems'][label]),
        'scores': {'throughput': -2.-i, 'content-utility': -3.-i}}
        for i, label in enumerate(p['reference_order'])]
    a = sealed({**{k: v for k, v in a.items() if k != 'content_sha256'}, 'worlds': references+a['worlds']})
    records = {}
    for arm, objective in driver.history_keys(p):
        for g in range(3):
            w = next(w for w in a['worlds'] if w['identity'] == arm+'::'+objective+'-'+str(g))
            request = {'generation': g, 'loss_spec': clone(p['losses'][objective]),
                'parent_system': clone(p['initial_system']), VIEW: {'access_contract': {'mode': arm},
                    'active_parent': [] if arm == 'scalar' else [{'observation_id': 'SCRIPTED-parent'}],
                    'archive_items': [] if arm == 'scalar' else [{'SCRIPTED': 'not physical evidence'}]}}
            records[(arm,objective),g] = {'request': request, 'request_sha256': digest(request),
                'generation_error': None, 'draws': [{'suggestion': {'candidate': clone(w['system'])}}],
                'observations': [{'suggestion_id': w['identity'], 'candidate': clone(w['system']),
                    'status': 'complete', 'loss': w['scores'][objective]}]}
    return p, a, records


def test_two_objectives_are_not_relabelled_as_four_objectives(tmp_path, monkeypatch):
    p, a, records = development_fixture(tmp_path, monkeypatch)
    r = development.summarize(p, a, records)
    assert r['score_order'] == ['throughput', 'content-utility']
    assert r['information_arms'] == ['scalar', 'parent-trajectory']
    assert set(r['loss_paths']) == {'::'.join(k) for k in driver.history_keys(p)}
    assert len(r['slots']) == 12 and r['physical_worlds'] == 14
    assert r['loss_paths']['scalar::throughput'][0]['best_own_loss'] == -1.
    assert r['loss_paths']['scalar::throughput'][0]['best_known_loss'] == -2.  # hand -3 is withheld.
    assert r['loss_paths']['scalar::content-utility'][0]['best_known_loss'] == -3.
    assert not r['single_information_field_causal_effect_claimed']
    for row in r['slots']:
        assert row['trajectory_access']['active_parent_runs'] == (row['arm'] == 'parent-trajectory')


def test_a_failed_world_keeps_its_slot_and_unavailable_loss(tmp_path, monkeypatch):
    p, a, records = development_fixture(tmp_path, monkeypatch)
    key = ('scalar', 'throughput'); identity = 'scalar::throughput-1'
    a.pop('content_sha256'); a['selection'].pop('content_sha256')
    w = next(w for w in a['worlds'] if w['identity'] == identity)
    w.update(status='failed', scores={'throughput': None, 'content-utility': None})
    s = a['selection']['selected']['scalar::throughput']
    s['all_tied_ids'].remove(identity); s['completed_submissions'] = 2
    a['selection']['content_sha256'] = digest(a['selection']); a['content_sha256'] = digest(a)
    records[key,1]['observations'][0].update(status='failed', loss=None)
    r = development.summarize(p, a, records)
    row = next(row for row in r['slots'] if row['physical_job'] == identity)
    assert row['status'] == 'failed' and row['loss'] is None
    path = r['loss_paths']['scalar::throughput']
    assert path[1]['observed_loss'] is None and path[1]['best_own_loss'] == -1.
    assert len(r['slots']) == 12


def fixed_fixture(tmp_path, monkeypatch):
    p, _ = plan(tmp_path, monkeypatch); a = closed(p)
    u = sealed({'valid': True, 'errors': [], 'prior_matching_runs': [], 'seeds': p['reserved_unused_seeds']})
    q = sealed(fixed.build_plan(p,a,source=p['source_commit'],origin={'SCRIPTED': True},usages=[u],
        seeds=p['reserved_unused_seeds'],observer_backend=p['observer_contract']['backend'],
        source_proof={'original_source': p['source_commit']}))
    worlds = []
    for job in q['jobs']:
        measurement = {'run_id': 'SCRIPTED-'+job['identity'], 'metrics': {'native.accepted_decisions': {'status': 'measured', 'value': 1},
            'native.common_content_utility_sum': {'status': 'measured', 'value': 2}}}
        worlds.append({**clone(job), 'role': 'selection-fixed-evaluation', 'status': 'complete',
            'measurements': [measurement], 'scores': {'throughput': -1., 'content-utility': -2.}})
    b = sealed({'schema': 'scienceutopia.native-longitudinal-fixed-evaluation-audit.v1',
        'source_commit': q['source_commit'], 'plan_sha256': q['content_sha256'],
        'source_proof': {'status': 'verified-exact-source-closure'},
        'closure': {'terminal': {'status': 'closed', 'completed_jobs': len(q['jobs'])}},
        'held_out_world_seeds': True, 'fixed_selection': q['fixed_selection'],
        'origin_audit_content_sha256': q['origin_audit_content_sha256'], 'worlds': worlds,
        'new_model_calls': 0, 'new_code_executions': 0, 'SCRIPTED': 'synthetic report primitive'})
    return q, b


def test_six_labels_and_separate_objective_vs_access_contrasts(tmp_path, monkeypatch):
    p, a = fixed_fixture(tmp_path, monkeypatch)
    r = fixed_report.summarize(p, a, study='longitudinal-v1')
    assert len(r['logical_rows']) == 6 and len(r['physical_worlds']) == 2
    assert len(r['paired_differences']) == 8
    assert len(r['objective_choice_differences']) == len(r['information_access_differences']) == 2
    assert {r['arm'] for r in r['objective_choice_differences']} == set(driver.ARMS)
    assert {r['objective'] for r in r['information_access_differences']} == set(driver.OBJECTIVES)
    assert all(row['same_physical_job'] and set(row['differences'].values()) == {0.}
        for name in ('objective_choice_differences','information_access_differences') for row in r[name])
    assert r['fixed_selection'] == p['fixed_selection']


def test_two_actual_renders_are_byte_identical_and_not_empty_contrast_panels(tmp_path, monkeypatch):
    p, a = fixed_fixture(tmp_path/'input', monkeypatch)
    r = fixed_report.summarize(p,a,study='longitudinal-v1')
    directories = [tmp_path/'one',tmp_path/'two']
    for d in directories: d.mkdir(); fixed_report.render(r,d)
    assert {p.name: p.read_bytes() for p in directories[0].iterdir()} == {p.name:p.read_bytes() for p in directories[1].iterdir()}
    svg = (directories[0]/'fixed-policy-paired-differences.svg').read_text()
    assert 'Unavailable: no paired completed loss' not in svg
    assert all('Selected '+key+' / scored by' in svg for key in r['selection_order'])
