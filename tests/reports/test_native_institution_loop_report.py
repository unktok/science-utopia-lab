"""Synthetic reporting/figure checks, never measured scientific results."""
from copy import deepcopy
import json

import pytest

from scripts.audit_pre_scale_search_v1 import actual_policy_order
from scripts.reports.pre_scale_search_v1 import summarize, render
from scripts.reports.pre_scale_search_reproduce_v1 import validate, reproduce
from scripts.reports.pre_scale_mechanism_changes_v1 import project
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


def test_retained_native_report_recomputes_components_ties_and_physical_sharing(tmp_path):
    p,a = fixture(tmp_path); r = summarize(a,plan=p)
    assert validate(r) == r
    changes = project(r)
    assert len(changes['rows']) == 12
    assert all(row['difference_from_common_initial'] is None for row in changes['rows'])
    assert not changes['semantic_novelty_or_effect_inferred']
    for problem in ('raw','tie','seed','count'):
        changed = deepcopy(r)
        if problem == 'raw': changed['worlds'][0]['measurement']['metrics']['native.accepted_decisions']['value'] = 1
        if problem == 'tie': changed['optimization_paths']['efficiency:parameters']['fixed_selection']['all_tied_row_ids'] = []
        if problem == 'seed': changed['evaluation_rows'][0]['seed'] = 51001
        if problem == 'count': changed['physical_evaluation_worlds'] = 33
        with pytest.raises(ValueError): validate(rehash(changed))


def test_native_portable_rebuild_needs_no_models_native_world_or_generated_execution(tmp_path):
    from utopia.utils.data_utils import file_sha256, write_json_atomic
    p,a = fixture(tmp_path); r = summarize(a,plan=p)
    retained=tmp_path/'SCRIPTED-retained';retained.mkdir()
    write_json_atomic(retained/'report.json',r,sort_keys=True,allow_nan=False);render(r,retained)
    manifest=rehash({'schema':'scienceutopia.pre-scale-search-figures.v1',
        'report_content_sha256':r['content_sha256'],
        'files':{path.name:file_sha256(path) for path in retained.iterdir()}})
    write_json_atomic(retained/'manifest.json',manifest,sort_keys=True,allow_nan=False)
    result=reproduce(retained/'report.json',retained/'manifest.json',retained,tmp_path/'SCRIPTED-rebuild')
    assert result['schema']=='scienceutopia.native-institution-loop-reproduction.v1'
    assert result['report_and_four_figure_files_byte_identical']
    assert result['raw_available_cross_scores_recomputed']==26*3
    assert result['new_model_calls']==result['new_native_worlds']==result['new_code_executions']==0
