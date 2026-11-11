"""Synthetic reporting/figure checks, never measured scientific results."""
from copy import deepcopy
import json

import pytest

from scripts.audit_pre_scale_search_v1 import actual_policy_order
from scripts.reports.pre_scale_search_v1 import summarize, render
from scripts.run_native_institution_loop_v1 import campaign, selection_payload, evaluation_jobs
from tests.reports.test_native_institution_loop_v1 import plan
from tests.reports.test_pre_scale_search_v1 import references
from utopia.system.design_patch import digest


def rehash(value):
    return {**{k:v for k,v in value.items() if k != 'content_sha256'},
        'content_sha256':digest({k:v for k,v in value.items() if k != 'content_sha256'})}


def fixture(root):
    p = plan(); references(root, p)
    for arm in p['arm_order']:
        c = campaign(root, p, 'run-00', arm)
        for _ in range(2):
            c.advance(simulation_factory=lambda *a:pytest.fail('null cannot dispatch'),
                generators={'local-designer':lambda request:None}, count=1)
    s = selection_payload(root, p, frozen_utc='SCRIPTED')
    s = rehash({**s, 'schema':'scienceutopia.native-institution-loop.v1.selection'})
    jobs = evaluation_jobs(p, s)
    proof = {'status':'complete','measurement':{'metrics':{k:{'status':'measured','value':0}
        for k in ('native.accepted_decisions','native.accepted_peer_score_sum','native.review_records')}}}
    worlds = [{'identity':'reference-'+name, 'role':'developer-reference', 'seed':61001,
        'system':p['reference_systems'][name], 'status':'complete',
        'scores':{'throughput':0,'efficiency':0,'selective':0}, 'physical_proof':deepcopy(proof)}
        for name in p['reference_order']]
    worlds.extend({'identity':j['identity'], 'role':'selection-fixed-evaluation','seed':j['seed'],
        'system':j['system'], 'status':'complete','scores':{'throughput':0,'efficiency':0,'selective':0},
        'physical_proof':deepcopy(proof)} for j in jobs)
    audit = rehash({'schema':'scienceutopia.native-institution-loop-audit.v1',
        'source_commit':p['source_commit'], 'plan_sha256':p['content_sha256'],
        'selection':s, 'worlds':worlds, 'logical_evaluation':actual_policy_order(p,s,jobs),
        'source_proof':{'status':'verified-exact-source-closure'}, 'closure':{'terminal':{'status':'closed'}},
        'new_model_calls':0, 'new_code_executions':0})
    return p, audit


def test_all_native_slots_and_new_routing_references_keep_their_physical_join(tmp_path):
    p,a = fixture(tmp_path); before = deepcopy((p,a)); r = summarize(a,plan=p)
    assert (p,a) == before
    assert r['schema'] == 'scienceutopia.native-institution-loop-report.v1'
    assert len(r['search_slots']) == 12 and r['status_counts'] == {'generation-failure':12}
    assert len(r['optimization_paths']) == 6 and len(r['references']) == 8
    assert all(row['own_loss'] is None for row in r['search_slots'])
    assert r['evaluation_seeds'] == [62001,62011,62017]
    assert r['logical_evaluation_rows'] == 33 and r['physical_evaluation_worlds'] == 18
    assert len(r['paired_reference_differences']) == 90
    assert len(r['development_world_bindings']) == 20
    assert not r['scientific_goal_complete'] and r['new_model_calls'] == 0


@pytest.mark.parametrize('error', ['no-plan','wrong-plan','stopped','wrong-seed','missing-slot'])
def test_native_projection_cannot_relabel_old_or_incomplete_evidence(tmp_path,error):
    p,a = fixture(tmp_path)
    if error == 'no-plan': p = None
    if error == 'wrong-plan': p = rehash({**p,'source_commit':'b'*40})
    if error == 'stopped': a['closure']['terminal']['status'] = 'stopped'
    if error == 'wrong-seed': a['logical_evaluation'][0]['seed'] = 51001
    if error == 'missing-slot': a['selection']['all_rows'].pop()
    with pytest.raises(ValueError): summarize(rehash(a),plan=p)


def test_native_figures_render_new_methods_and_seeds_without_random_or_old_seed_fallback(tmp_path):
    p,a = fixture(tmp_path); r = summarize(a,plan=p)
    figures = tmp_path/'SCRIPTED-figures'; figures.mkdir()
    render(r,figures)
    assert len(list(figures.iterdir())) == 4
    text = (figures/'selection-fixed-common-scores.svg').read_text()
    assert '62001' in text and '51001' not in text
    paths = (figures/'objective-conditioned-paths.svg').read_text()
    assert 'code-and-graph' in paths and 'random' not in paths
    assert 'not a method-superiority study' in paths
    assert summarize(json.loads(json.dumps(a)),plan=json.loads(json.dumps(p))) == r
