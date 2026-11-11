"""Fixed-record reviewer-subset readouts, NOT new institutions or world effects.

Keep accepted papers and actual review work fixed. Enumerate readout subsets
of already observed scores; do not pretend omitted reviews were never made.
The worker imports the closed study's original checkpoint reader and checks
the full raw inventory against its earlier original-source audit.
"""
import argparse
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import subprocess
import sys


def panel_readouts(scores):
    if not isinstance(scores,list) or any(type(v) not in (int,float) or not math.isfinite(v) for v in scores):
        raise ValueError('literal finite original review scores required; no coercion or imputation')
    n=len(scores)
    if n>16:raise ValueError('finite diagnostic enumerates at most16 observed reviews per panel')
    if not n:return {'reviews':0,'original_mean':None,'subsets':[]}
    mean=math.fsum(scores)/n;rows=[]
    for k in range(1,n+1):
        values=[math.fsum(v)/k for v in itertools.combinations(scores,k)]
        average=math.fsum(values)/len(values)
        if not math.isclose(average,mean,rel_tol=1e-12,abs_tol=1e-12):
            raise ValueError('uniform subset readout identity failed')
        rows.append({'size':k,'subsets':len(values),'minimum':min(values),'maximum':max(values),
            'uniform_mean':average,'uniform_variance':math.fsum((v-average)**2 for v in values)/len(values)})
    return {'reviews':n,'original_mean':mean,'subsets':rows}


def fixed_world(papers):
    if not isinstance(papers,list):raise ValueError('original paper list required')
    accepted=[];review_work=0;rounds=0
    for paper in papers:
        for i,decision in enumerate(paper['review_history']):
            rounds+=1;reviews=decision.get('reviews',[]);review_work+=len(reviews)
            if decision['decision']!='accept':continue
            scores=[r.get('overall_score') for r in reviews]
            readout=panel_readouts(scores)
            accepted.append({'paper_id':paper['id'],'year':decision['year'],'decision_index':i,
                'scores':scores,'readout':readout})
    reviewed=[r for r in accepted if r['readout']['reviews']]
    q=math.fsum(r['readout']['original_mean'] for r in reviewed)
    low=math.fsum(r['readout']['subsets'][0]['minimum'] for r in reviewed)
    high=math.fsum(r['readout']['subsets'][0]['maximum'] for r in reviewed)
    return {'accepted_decisions':len(accepted),'reviewed_accepted_decisions':len(reviewed),
        'unreviewed_accepted_decisions':len(accepted)-len(reviewed),'decision_records':rounds,
        'actual_review_records':review_work,'original_Q':q,
        'conditional_one_review_readout_Q_range':[low,high],
        'conditional_E_readout_range_same_actual_R':[-high+.5*review_work,-low+.5*review_work],
        'panels':accepted}


def worker(run,audit_path,output):
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.native_benchmark_source import source_proofs
    from utopia.optimization.native_jobs import pinned_revision
    from utopia.optimization.native_numeric_designer import checked
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import file_sha256,write_json_atomic
    run=Path(run).resolve();audit_path=Path(audit_path).resolve();output=Path(output).resolve();source=Path.cwd()
    if output.exists() or output.is_relative_to(run) or output.is_relative_to(source):
        raise ValueError('fresh external analysis destination required')
    before=_inventory(run);audit_sha=file_sha256(audit_path)
    audit=checked(json.loads(audit_path.read_text()));plan=checked(json.loads((run/'plan.json').read_text()))
    if (audit['schema']!='scienceutopia.pre-scale-search-audit.v1'
            or audit['source_commit']!=pinned_revision(source) or audit['source_commit']!=plan['source_commit']
            or audit['plan_sha256']!=plan['content_sha256'] or digest(before)!=audit['raw_inventory_sha256']
            or len(before)!=audit['raw_files'] or not (run/'complete.json').exists()):
        raise ValueError('closed exact original-source search/audit/inventory required')
    proofs=source_proofs(source,plan['source_commit'],scripts=['scripts/native_benchmark_physical.py'],resources=[plan['protocol']])
    cells={}
    for path in run.glob('**/worlds/*'):
        if not path.is_dir():continue
        if path.name in cells:raise ValueError('ambiguous physical cell identity')
        cells[path.name]=path
    rows=[];skipped=[]
    for world in audit['worlds']:
        if world['physical_proof']['status']!='complete':
            skipped.append({'identity':world['identity'],'status':world['status'],
                'physical_status':world['physical_proof']['status'],'reason':'no complete four-year checkpoint'});continue
        cell=cells[world['identity']+'-s'+str(world['seed'])]
        paths=list(cell.rglob('portable_checkpoint_year_4.json.gz'))
        if len(paths)!=1 or file_sha256(paths[0])!=world['physical_proof']['checkpoint_sha256']:
            raise ValueError('completed checkpoint differs from original audit')
        state=read_portable_checkpoint(paths[0]);metrics=world['physical_proof']['measurement']['metrics']
        if state['year']!=4 or state['native_system']['spec']!=world['system']:
            raise ValueError('native checkpoint horizon/system differs')
        detail=fixed_world(state['paper_tracker']['papers'])
        for key,metric in (('accepted_decisions','native.accepted_decisions'),
                           ('actual_review_records','native.review_records'),
                           ('original_Q','native.accepted_peer_score_sum')):
            recorded=metrics[metric]
            if (recorded['status']!='measured' or not math.isclose(detail[key],recorded['value'],rel_tol=1e-12,abs_tol=1e-12)):
                raise ValueError('reconstructed original A/Q/R differs from original checkpoint audit')
        for panel in detail['panels']:
            panel['paper_id_sha256']=digest(panel.pop('paper_id'))
        rows.append({'identity':world['identity'],'role':world['role'],'seed':world['seed'],
            'checkpoint_sha256':file_sha256(paths[0]),**detail})
    if len(rows)+len(skipped)!=len(audit['worlds']):raise ValueError('physical worlds omitted')
    summary={'complete_physical_worlds':len(rows),'incomplete_physical_worlds':len(skipped),
        'reviewed_accepted_decision_records':sum(r['reviewed_accepted_decisions'] for r in rows),
        'unreviewed_accepted_decision_records':sum(r['unreviewed_accepted_decisions'] for r in rows),
        'complete_worlds_with_nonzero_readout_range':sum(r['conditional_one_review_readout_Q_range'][1]>
            r['conditional_one_review_readout_Q_range'][0] for r in rows)}
    result={'schema':'scienceutopia.fixed-record-panel-sensitivity.v1','source_commit':plan['source_commit'],
        'plan_sha256':plan['content_sha256'],'input_full_audit_content_sha256':audit['content_sha256'],
        'input_full_audit_file_sha256':audit_sha,'source_proof':proofs,
        'raw_inventory_sha256':digest(before),'raw_files':len(before),'summary':summary,'worlds':rows,'skipped_worlds':skipped,
        'interpretation':'Conditional readouts of already recorded panels, fixing publications and actual review work. Extremes may require hindsight and need not be realizable by an ex ante institution. Not a reviewer-routing counterfactual, independent quality measure, policy effect or new optimization.',
        'independent_samples_inferred_from_subsets':False,'cost_of_omitted_reviews_removed':False,
        'analysis_adapter_sha256':file_sha256(Path(__file__)),'new_model_calls':0,'new_native_worlds':0,'new_authored_code_executions':0}
    if before!=_inventory(run) or audit_sha!=file_sha256(audit_path):raise ValueError('original evidence changed during analysis')
    result['content_sha256']=digest(result)
    write_json_atomic(output,result,sort_keys=True,allow_nan=False)
    print(json.dumps({'output':str(output),'content_sha256':result['content_sha256'],'summary':summary}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run','audit','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--frozen-source',type=Path);parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if args.worker:worker(args.run,args.audit,args.output);return
    if args.frozen_source is None:raise ValueError('explicit original frozen scientific source required')
    script=Path(__file__).resolve();before=hashlib.sha256(script.read_bytes()).hexdigest()
    command=[sys.executable,'-c',
        'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()),str(script),'--worker','--run',str(args.run.resolve()),
        '--audit',str(args.audit.resolve()),'--output',str(args.output.resolve())]
    result=subprocess.run(command,cwd=args.frozen_source.resolve(),env={**os.environ,'PYTHONHASHSEED':'42'},timeout=900,check=False)
    if hashlib.sha256(script.read_bytes()).hexdigest()!=before:raise ValueError('analysis adapter changed during execution')
    if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
