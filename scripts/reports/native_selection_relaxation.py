"""Conditional decision-flag relaxation of already audited completed worlds.

This is NOT a feasible policy counterfactual or an oracle for the dynamic world.
Fix the observed records, original reviewer replies and total review count;
only relax the accept/reject flags independently. No new simulation or code.
"""
import argparse
import hashlib
import math
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_design_benchmark import checked
from utopia.optimization.native_benchmark_controls import objective_specs
from utopia.optimization.loss import evaluate_loss
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json,file_sha256,write_json_atomic

SCHEMA='scienceutopia.native-fixed-record-selection-relaxation.v1'
CONTROLS='scienceutopia.native-benchmark-controls.v2'
STUDY='scienceutopia.native-design-freedom-study.v2'


def finite(value):return type(value) in (int,float) and math.isfinite(value)


def fixed_records(papers):
    rows=[];r_count=0;out_of_scale=[]
    for p_index,paper in enumerate(papers):
        for d_index,record in enumerate(paper['review_history']):
            identity=f'p{p_index}:d{d_index}'
            reviews=record.get('reviews',[]);r_count+=len(reviews)
            scores=[review.get('overall_score') for review in reviews]
            good=all(finite(s) for s in scores)
            out_of_scale.extend({'record_id':identity,'review_index':i,'score':s}
                for i,s in enumerate(scores) if finite(s) and not 1<=s<=5)
            rows.append({'record_id':identity,'paper_id':paper.get('id'),'year':record.get('year'),
                'original_decision':record.get('decision'),'accepted':record.get('decision')=='accept',
                'review_count':len(reviews),'mean_original_review_score':math.fsum(scores)/len(scores)
                    if good and scores else 0. if good else None})
    a_count=sum(row['accepted'] for row in rows)
    accepted=[row['mean_original_review_score'] for row in rows if row['accepted']]
    q_sum=math.fsum(accepted) if all(v is not None for v in accepted) else None
    complete=all(row['mean_original_review_score'] is not None for row in rows)
    losses={}
    for name,cost,coefficient in [
            ('throughput',0.,lambda q:-1.),('efficiency',.5*r_count,lambda q:-q),
            ('selective',.1*r_count,lambda q:4.-q)]:
        available=name=='throughput' or complete
        coeffs=[coefficient(row['mean_original_review_score']) for row in rows] if available else None
        observed=(-float(a_count) if name=='throughput' else
            cost-q_sum if name=='efficiency' and q_sum is not None else
            cost+4.*a_count-q_sum if name=='selective' and q_sum is not None else None)
        minimum=cost+math.fsum(min(0.,c) for c in coeffs) if available else None
        if minimum is not None and observed is not None and observed<minimum and not math.isclose(
                observed,minimum,rel_tol=1e-12,abs_tol=1e-12):
            raise ValueError('observed decision flags contradict their own fixed-record relaxation')
        losses[name]={'observed_loss':observed,'fixed_record_minimum':minimum,
            'fixed_record_gap':observed-minimum if observed is not None and minimum is not None else None,
            'required_accept_ids':[row['record_id'] for row,c in zip(rows,coeffs) if c<0] if available else None,
            'required_reject_ids':[row['record_id'] for row,c in zip(rows,coeffs) if c>0] if available else None,
            'free_tie_ids':[row['record_id'] for row,c in zip(rows,coeffs) if c==0] if available else None,
            'all_exact_tie_assignments_represented_without_enumeration':available,
            'status':'complete' if available else 'unavailable-rejected-or-accepted-review-input',
            'feasible_dynamic_policy_minimum_claimed':False}
    return {'schema':SCHEMA+'.records','decision_records':len(rows),'review_records':r_count,
        'accepted_decisions':a_count,'accepted_peer_score_sum':q_sum,
        'accepted_unreviewed_decisions':sum(row['accepted'] and row['review_count']==0 for row in rows),
        'nonstandard_decision_records':sum(row['original_decision'] not in ('accept','reject') for row in rows),
        'unavailable_all_record_means':sum(row['mean_original_review_score'] is None for row in rows),
        'finite_review_scores_outside_declared_1_to_5':out_of_scale,'rows':rows,'losses':losses,
        'scope':'Fix realized records, reviewer replies and total R; independently relax only accept/reject flags. Changes can be dynamically infeasible because decisions change future scientists, submissions and reviews. Not new world outcomes, policy recommendations, an exact expectation or a global optimum.'}


def entries(root,plan,audit):
    if plan['schema']==CONTROLS:
        if [r['name'] for r in audit['rows']]!=plan['order']:raise ValueError('control slot set/order differs')
        for row in audit['rows']:
            directory=(root/'controls'/row['name']).resolve()
            if not directory.is_relative_to(root):raise ValueError('control directory escapes raw root')
            yield 'reference:'+row['name'],decode_json((directory/'observation.json').read_text(),
                strict=True,finite_floats=True),audit['proofs'][row['name']]
    elif plan['schema']==STUDY:
        for run,arms in audit['runs'].items():
            for arm,body in arms.items():
                for row in body['observations']:
                    yield 'search:'+run+':'+arm+':g'+str(row['generation']),row['observation'],row['physical_proof']
        for group in ['references','evaluated']:
            for name,body in audit[group].items():
                yield group+':'+name,body['observation'],body['physical_proof']
    else:raise ValueError('unsupported exact original audit protocol')


def analyze(root,plan,audit,*,expected_source):
    root=Path(root).resolve()
    if plan.get('schema') not in (CONTROLS,STUDY):raise ValueError('supported closed protocol required')
    checked(plan,plan['schema']);checked(audit,plan['schema']+'.audit')
    if (plan['source_commit']!=expected_source or audit['source_commit']!=expected_source
            or plan['content_sha256']!=audit['plan_sha256']
            or audit['source_proofs']['status']!='verified-exact-source-closure'
            or audit['new_model_calls']!=0 or audit['new_code_executions']!=0
            or audit['writer']['ended']['status']!='exited' or audit['writer']['ended']['exit_code']!=0
            or plan['losses']!=objective_specs()):
        raise ValueError('closed exact-source audit and fixed T/E/C definitions required')
    before=_inventory(root)
    if before!=audit['input_inventory']:raise ValueError('raw inventory differs from completed original audit')
    try:
        results={}
        for identity,o,proof in entries(root,plan,audit):
            meta=o.get('metadata',{}) if o else {}
            complete=(not meta.get('technical_failures') and len(meta.get('runs',[]))==1
                and len(meta.get('measurements',[]))==1 and proof is not None)
            if not complete:
                results[identity]={'status':'unavailable-no-complete-physical-forward','relaxation':None}
                continue
            evidence=meta['runs'][0];path=Path(evidence['checkpoint_path']).resolve()
            if (not path.is_relative_to(root) or file_sha256(path)!=evidence['checkpoint_sha256']
                    or evidence['checkpoint_sha256']!=proof['checkpoint_sha256']):
                raise ValueError('original audited checkpoint path/hash differs')
            saved=read_portable_checkpoint(path)
            binding=saved['portable']['contract']['binding']
            if (binding['science_config']['source_commit']!=expected_source
                    or binding['cell']!=meta['system_fingerprint']
                    or saved['year']!=binding['science_config']['years'] or saved['phase']!=5
                    or proof['measurement']!=meta['measurements'][0]):
                raise ValueError('completed checkpoint source/horizon/measurement differs')
            relaxation=fixed_records(saved['paper_tracker']['papers'])
            audited_losses={};roundoff={}
            for key,loss in plan['losses'].items():
                actual=evaluate_loss(loss,[proof['measurement']])['loss']
                observed=relaxation['losses'][key]['observed_loss']
                if ((actual is None)!=(observed is None) or actual is not None and not math.isclose(
                        actual,observed,rel_tol=1e-12,abs_tol=1e-12)):
                    raise ValueError('fixed-record observed objective differs from audited native measurement')
                audited_losses[key]=actual
                roundoff[key]=observed-actual if actual is not None else None
            results[identity]={'status':'complete','checkpoint_relative_path':str(path.relative_to(root)),
                'checkpoint_sha256':file_sha256(path),'physical_measurement_sha256':digest(proof['measurement']),
                'audited_observed_losses':audited_losses,'independent_sum_minus_audited_loss':roundoff,
                'relaxation':relaxation}
        result={'schema':SCHEMA,'source_commit':expected_source,'plan_sha256':plan['content_sha256'],
            'input_audit_content_sha256':audit['content_sha256'],'raw_inventory_sha256':digest(before),
            'analysis_source_sha256':file_sha256(Path(__file__)),'worlds':results,
            'scope':'Independent algebraic decision-flag relaxation on completed, already source-audited checkpoints. Raw scores and future histories are frozen, not resimulated. No feasibility or causal policy improvement claim.',
            'projection_is_not_a_new_raw_audit':True,'new_model_calls':0,'new_code_executions':0,
            'new_worlds':0,'raw_inventory_unchanged':True}
        result['content_sha256']=digest(result)
        return result
    finally:
        if before!=_inventory(root):raise ValueError('raw evidence changed during fixed-record analysis')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--expected-source',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(argv)
    if a.output.exists() or a.output.resolve().is_relative_to(a.run.resolve()):
        p.error('fresh output outside raw root required')
    audit_bytes=a.audit.read_bytes();plan_path=a.run/'plan.json';plan_bytes=plan_path.read_bytes()
    report=analyze(a.run,decode_json(plan_bytes.decode(),strict=True,finite_floats=True),
        decode_json(audit_bytes.decode(),strict=True,finite_floats=True),expected_source=a.expected_source)
    if a.audit.read_bytes()!=audit_bytes or plan_path.read_bytes()!=plan_bytes:raise ValueError('input changed')
    report['audit_file_sha256']=hashlib.sha256(audit_bytes).hexdigest()
    report['content_sha256']=digest({k:v for k,v in report.items() if k!='content_sha256'})
    write_json_atomic(a.output,report,sort_keys=True,allow_nan=False,indent=2)
    print({'content_sha256':report['content_sha256'],'worlds':len(report['worlds'])});return 0


if __name__=='__main__':raise SystemExit(main())
