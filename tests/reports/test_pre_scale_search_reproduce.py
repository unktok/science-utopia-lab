"""SYNTHETIC retained-report QA, not live O/E results or authored-code execution."""
from copy import deepcopy
import csv
import io
import json

import pytest

from scripts.reports.pre_scale_search_v1 import summarize,render
from scripts.reports.pre_scale_search_reproduce_v1 import validate,world_csv,reproduce
from scripts.native_design_benchmark_plan import policy_identity
from tests.reports.test_pre_scale_search_report import fixture,rehash
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256,write_json_atomic


def report(tmp_path):
    result=summarize(fixture(tmp_path));result['figure_scope']='SYNTHETIC QA';return rehash(result)


def completed_candidate(root):
    audit=fixture(root);selection=audit['selection'];row=next(r for r in selection['all_rows']
        if r['row_id']=='run-00:throughput:parameters:g0')
    system=deepcopy(selection['reference_systems']['open-seed'])
    scores={'throughput':-1.,'efficiency':-2.5,'selective':.3}
    row.update(system=system,status='complete',forward_complete=True,cross_scores=scores)
    chosen={'loss':-1.,'all_tied_row_ids':[row['row_id']],'selected_row_id':row['row_id'],
        'system':system,'policy_sha256':policy_identity(system)}
    selection['selected']['throughput:parameters']=deepcopy(chosen)
    selection['pooled']['throughput']=deepcopy(chosen)
    selection['pooled']['efficiency']={**deepcopy(chosen),'loss':-2.5}
    rehash(selection)
    audit['worlds'].insert(6,{'identity':'SCRIPTED-candidate-0','role':'search:throughput:parameters',
        'seed':41001,'system':system,'status':'complete','scores':scores,
        'physical_proof':{'status':'complete','measurement':{'metrics':{key:{'status':'measured','value':value}
            for key,value in [('native.accepted_decisions',1),('native.accepted_peer_score_sum',4),('native.review_records',3)]}}}})
    result=summarize(rehash(audit));result['figure_scope']='SYNTHETIC QA';return rehash(result)


def test_all_null_attempts_and_shared_labels_are_reconstructed_without_extra_worlds(tmp_path):
    r=validate(report(tmp_path))
    assert r['status_counts']=={'generation-failure':16}
    assert r['physical_evaluation_worlds']==12 and r['logical_evaluation_rows']==36
    assert all(not p['strict_development_gain_over_initial'] for p in r['optimization_paths'].values())
    rows=list(csv.DictReader(io.StringIO(world_csv(r))))
    assert len(rows)==18 and sum(v['role']=='selection-fixed-evaluation' for v in rows)==12
    assert all(v['A']=='0' and v['A_status']=='measured' for v in rows)


def test_complete_then_null_path_keeps_actual_gain_and_same_policy_is_not_invented_novelty(tmp_path):
    r=validate(completed_candidate(tmp_path));path=r['optimization_paths']['throughput:parameters']
    assert path['candidate_slots'][0]['best_including_initial_for_final_comparison']==-1.
    assert path['candidate_slots'][1]['own_loss'] is None
    assert path['candidate_slots'][1]['best_including_initial_for_final_comparison']==-1.
    assert path['strict_development_gain_over_initial']
    assert r['development_world_bindings'][path['candidate_slots'][0]['row_id']]=='SCRIPTED-candidate-0'


def test_failed_evaluation_keeps_null_pairs_unknown_raw_components_and_physical_job(tmp_path):
    a=fixture(tmp_path);world=next(w for w in a['worlds'] if w['role']=='selection-fixed-evaluation')
    world.update(status='failed',scores={k:None for k in world['scores']},physical_proof={
        'status':'partial-or-technical-failure','measurement':None})
    r=validate(summarize(rehash(a)))
    assert r['physical_evaluation_worlds']==12
    assert any(p['differences']['throughput'] is None for p in r['paired_reference_differences'])
    rows=list(csv.DictReader(io.StringIO(world_csv(r))));failed=next(row for row in rows if row['assigned_status']=='failed')
    assert failed['A']=='' and failed['A_status']=='not-recorded' and failed['throughput']==''


def test_completed_physics_can_have_unavailable_assigned_loss_without_erasing_other_metrics(tmp_path):
    a=fixture(tmp_path);selection=a['selection'];row=next(r for r in selection['all_rows']
        if r['row_id']=='run-00:efficiency:parameters:g0')
    system=deepcopy(selection['reference_systems']['no-review-accept-all'])
    scores={'throughput':-1.,'efficiency':None,'selective':None}
    row.update(system=system,status='failed',forward_complete=True,cross_scores=scores)
    selection['pooled']['throughput']={'loss':-1.,'all_tied_row_ids':[row['row_id']],
        'selected_row_id':row['row_id'],'system':system,'policy_sha256':policy_identity(system)}
    rehash(selection)
    a['worlds'].insert(6,{'identity':'SCRIPTED-unavailable-E','role':'search:efficiency:parameters',
        'seed':41001,'system':system,'status':'failed','scores':scores,'physical_proof':{'status':'complete',
            'measurement':{'metrics':{'native.accepted_decisions':{'status':'measured','value':1},
                'native.accepted_peer_score_sum':{'status':'unavailable','value':None},
                'native.review_records':{'status':'measured','value':0}}}}})
    r=validate(summarize(rehash(a)));path=r['optimization_paths']['efficiency:parameters']
    assert path['candidate_slots'][0]['own_loss'] is None
    assert path['candidate_slots'][0]['cross_scores']['throughput']==-1.
    rows=list(csv.DictReader(io.StringIO(world_csv(r))));raw=next(v for v in rows if v['identity']=='SCRIPTED-unavailable-E')
    assert raw['assigned_status']=='failed' and raw['physical_forward_status']=='complete'
    assert raw['Q']=='' and raw['Q_status']=='unavailable' and raw['throughput']=='-1.0'


@pytest.mark.parametrize('part',['raw-count','unavailable-metric','boolean-score','path','tie','pooled-tie',
    'shared-count','wrong-physical-seed','missing-evaluation','wrong-source-dictionary'])
def test_resealed_inconsistent_report_is_rejected(tmp_path,part):
    r=report(tmp_path)
    if part=='raw-count':r['worlds'][0]['measurement']['metrics']['native.accepted_decisions']['value']=1
    if part=='unavailable-metric':r['worlds'][0]['measurement']['metrics']['native.accepted_peer_score_sum']['status']='unavailable'
    if part=='boolean-score':r['worlds'][0]['scores']['throughput']=False
    if part=='path':r['optimization_paths']['throughput:parameters']['candidate_slots'][0]['best_including_initial_for_final_comparison']=-100
    if part=='tie':r['optimization_paths']['throughput:parameters']['fixed_selection']['all_tied_row_ids']=[]
    if part=='pooled-tie':r['selection_pooled']['throughput']['all_tied_row_ids'].reverse()
    if part=='shared-count':r['physical_evaluation_worlds']=36
    if part=='wrong-physical-seed':r['evaluation_rows'][0]['seed']=51017
    if part=='missing-evaluation':r['evaluation_rows'].pop()
    if part=='wrong-source-dictionary':next(iter(r['systems_by_sha256'].values()))['SCRIPTED']='tampered'
    with pytest.raises(ValueError):validate(rehash(r))


def test_fresh_numerical_roundtrip_rebuilds_report_and_four_figures_without_inference(tmp_path):
    root=tmp_path/'SYNTHETIC-input';root.mkdir();r=completed_candidate(root/'fixture')
    write_json_atomic(root/'report.json',r,sort_keys=True,allow_nan=False);render(r,root)
    manifest={'schema':'scienceutopia.pre-scale-search-figures.v1','report_content_sha256':r['content_sha256'],
        'input_file_sha256':'b'*64,'files':{p.name:file_sha256(p) for p in root.iterdir() if p.is_file()},
        'new_model_calls':0,'new_native_worlds':0}
    write_json_atomic(root/'manifest.json',{**manifest,'content_sha256':digest(manifest)},sort_keys=True,allow_nan=False)
    output=tmp_path/'SYNTHETIC-rebuild'
    result=reproduce(root/'report.json',root/'manifest.json',root,output)
    assert result['report_and_four_figure_files_byte_identical'] and result['new_model_calls']==0
    assert result['raw_available_cross_scores_recomputed']==19*3
    assert json.loads((output/'report.json').read_text())==r
    with pytest.raises(ValueError,match='fresh independent'):reproduce(root/'report.json',root/'manifest.json',root,output)
