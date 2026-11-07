"""Algebra and synthetic checkpoint QA, never new scientific world evidence."""
from copy import deepcopy
import itertools
import json
import math
import random

import pytest

from scripts.reports import native_selection_relaxation as analysis
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_benchmark_controls import objective_specs
from utopia.runtime.checkpointing import write_portable_checkpoint
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256,write_json_atomic


def paper(scores,decision='accept'):
    return {'id':'SCRIPTED-paper','review_history':[{'year':1,'decision':decision,
        'final_score':10000.,'reviews':[{'overall_score':v} for v in scores]}]}


def test_fixed_record_optimum_uses_original_reviews_and_separate_total_review_cost():
    papers=[paper([1,5]),paper([5],'reject'),paper([])]
    r=analysis.fixed_records(papers)
    assert (r['decision_records'],r['review_records'],r['accepted_decisions'],r['accepted_peer_score_sum'])==(3,3,2,3.)
    assert r['losses']['throughput']['fixed_record_minimum']==-3.
    assert r['losses']['efficiency']['fixed_record_minimum']==-6.5
    assert r['losses']['efficiency']['free_tie_ids']==['p2:d0']
    assert r['losses']['selective']['fixed_record_minimum']==pytest.approx(-.7)
    assert r['losses']['selective']['required_accept_ids']==['p1:d0']
    assert r['losses']['selective']['required_reject_ids']==['p0:d0','p2:d0']
    changed=deepcopy(papers);changed[0]['review_history'][0]['final_score']=-1e12
    assert analysis.fixed_records(changed)==r
    assert not r['losses']['selective']['feasible_dynamic_policy_minimum_claimed']


def test_fixed_record_minima_match_exhaustive_flag_assignments_under_actual_loss_specs():
    rng=random.Random(42)
    for _ in range(12):
        papers=[paper([rng.randint(1,5) for _ in range(rng.randrange(4))],rng.choice(['accept','reject']))
            for _ in range(5)]
        r=analysis.fixed_records(papers);observed={name:[] for name in objective_specs()}
        for flags in itertools.product([False,True],repeat=5):
            metrics={'native.accepted_decisions':{'status':'measured','value':sum(flags)},
                'native.accepted_peer_score_sum':{'status':'measured','value':math.fsum(
                    row['mean_original_review_score'] for row,f in zip(r['rows'],flags) if f)},
                'native.review_records':{'status':'measured','value':r['review_records']}}
            for name,spec in objective_specs().items():
                observed[name].append(evaluate_loss(spec,[{'run_id':'SCRIPTED','metrics':metrics}])['loss'])
        for name,values in observed.items():
            assert r['losses'][name]['fixed_record_minimum']==pytest.approx(min(values))


def test_missing_rejected_review_can_leave_observed_loss_valid_but_relaxation_unavailable():
    r=analysis.fixed_records([paper([3]),paper([None],'reject')])
    assert r['losses']['efficiency']['observed_loss']==-2.
    assert r['losses']['efficiency']['fixed_record_minimum'] is None
    assert r['losses']['throughput']['fixed_record_minimum']==-2.
    assert r['accepted_peer_score_sum']==3.
    r=analysis.fixed_records([paper([None])])
    assert r['losses']['efficiency']['observed_loss'] is None
    assert r['losses']['throughput']['observed_loss']==-1.


def test_empty_unreviewed_and_exact_ties_are_not_dropped_or_rewritten():
    empty=analysis.fixed_records([])
    assert all(l['fixed_record_minimum']==0. for l in empty['losses'].values())
    tied=analysis.fixed_records([paper([4]),paper([4],'reject')])
    assert tied['losses']['selective']['free_tie_ids']==['p0:d0','p1:d0']
    unreviewed=analysis.fixed_records([paper([])])
    assert unreviewed['accepted_unreviewed_decisions']==1
    assert unreviewed['losses']['efficiency']['free_tie_ids']==['p0:d0']
    assert unreviewed['losses']['selective']['fixed_record_gap']==4.
    unusual=analysis.fixed_records([paper([-1]),paper([10])])
    assert len(unusual['finite_review_scores_outside_declared_1_to_5'])==2
    assert unusual['losses']['efficiency']['required_reject_ids']==['p0:d0']


def fixture(root):
    from tests.reports.test_native_benchmark_controls import plan
    p=plan();write_json_atomic(root/'plan.json',p)
    rows=[];proofs={}
    for i,name in enumerate(p['order']):
        cell=root/'controls'/name
        fingerprint='SCRIPTED-'+name
        checkpoint=cell/'checkpoints/year2.json.gz'
        write_portable_checkpoint(checkpoint,{'year':2,'phase':5,
            'portable':{'contract':{'binding':{'cell':fingerprint,
                'science_config':{'source_commit':p['source_commit'],'years':2}}}},
            'paper_tracker':{'papers':[paper([3]),paper([5],'reject')]}})
        measurement={'run_id':'SCRIPTED-'+name,'metrics':{
            'native.accepted_decisions':{'status':'measured','value':1},
            'native.accepted_peer_score_sum':{'status':'measured','value':3.},
            'native.review_records':{'status':'measured','value':2}}}
        o={'status':'complete','metadata':{'system_fingerprint':fingerprint,
            'runs':[{'checkpoint_path':str(checkpoint),'checkpoint_sha256':file_sha256(checkpoint)}],
            'measurements':[measurement],'technical_failures':[]}}
        if i==1:o={'status':'failed','metadata':{'runs':[],'measurements':[],'technical_failures':[{'SCRIPTED':True}]}}
        write_json_atomic(cell/'observation.json',o)
        rows.append({'name':name});proofs[name]={'measurement':measurement,'checkpoint_sha256':file_sha256(checkpoint)}
    audit={'schema':analysis.CONTROLS+'.audit','source_commit':p['source_commit'],
        'plan_sha256':p['content_sha256'],'source_proofs':{'status':'verified-exact-source-closure','files':{'SCRIPTED':'not-real'}},
        'new_model_calls':0,'new_code_executions':0,'writer':{'ended':{'status':'exited','exit_code':0}},
        'rows':rows,'proofs':proofs,'input_inventory':analysis._inventory(root)}
    audit['content_sha256']=digest(audit)
    return p,audit


def test_hash_bound_closed_fixture_analysis_is_read_only_and_keeps_failed_world(tmp_path):
    root=tmp_path/'raw';p,a=fixture(root);before=analysis._inventory(root)
    result=analysis.analyze(root,p,a,expected_source=p['source_commit'])
    assert result==analysis.analyze(root,p,a,expected_source=p['source_commit'])
    assert before==analysis._inventory(root)
    assert len(result['worlds'])==8
    assert result['worlds']['reference:open-seed']['relaxation'] is None
    assert result['worlds']['reference:legacy']['relaxation']['losses']['efficiency']['fixed_record_minimum']==-7.
    assert result['new_model_calls']==result['new_worlds']==result['new_code_executions']==0


@pytest.mark.parametrize('mutation',['source','weight','checkpoint','measurement','inventory'])
def test_mismatched_audit_source_weight_checkpoint_or_record_cannot_be_accepted(tmp_path,mutation):
    root=tmp_path/'raw';p,a=fixture(root)
    if mutation=='source':a['source_commit']='e'*40
    elif mutation=='weight':
        p['losses']['selective']['per_run']['terms'][0]['coefficient']=3.
        p['content_sha256']=digest({k:v for k,v in p.items() if k!='content_sha256'});a['plan_sha256']=p['content_sha256']
    elif mutation=='checkpoint':a['proofs']['legacy']['checkpoint_sha256']='f'*64
    elif mutation=='measurement':a['proofs']['legacy']['measurement']['metrics']['native.accepted_decisions']['value']=99
    else:a['input_inventory']={}
    a['content_sha256']=digest({k:v for k,v in a.items() if k!='content_sha256'})
    with pytest.raises(ValueError):analysis.analyze(root,p,a,expected_source=p['source_commit'])


def test_cli_preserves_existing_outputs_and_never_writes_inside_raw(tmp_path):
    root=tmp_path/'raw';p,a=fixture(root);audit_path=tmp_path/'audit.json';write_json_atomic(audit_path,a)
    output=tmp_path/'result.json'
    argv=['--run',str(root),'--audit',str(audit_path),'--expected-source',p['source_commit'],'--output',str(output)]
    assert analysis.main(argv)==0
    saved=output.read_bytes()
    with pytest.raises(SystemExit):analysis.main(argv)
    with pytest.raises(SystemExit):analysis.main(argv[:-1]+[str(root/'not-allowed.json')])
    assert output.read_bytes()==saved
