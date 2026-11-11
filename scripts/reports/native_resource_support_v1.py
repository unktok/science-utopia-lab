"""Source-bound year-end resource snapshots from the CLOSED old O/E study.

No new model calls, simulations, institution changes or within-year inference.
The child uses the original source's portable reader and audited annual hashes.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys


def snapshot(state):
    from utopia.system.design_patch import digest
    actors=[]
    for a in state['ecosystem_data']['agents']:
        if a.get('can_author') is not True:continue
        if (type(a['resources']) not in (int,float) or not math.isfinite(a['resources'])
                or type(a['is_active']) is not bool):raise ValueError('literal finite resource and boolean activity required')
        other=state['portable']['agent_states'][a['id']]['state']
        if any(other.get(k)!=a.get(k) for k in ('resources','is_active','initial_funding')):
            raise ValueError('portable restored state and ecosystem snapshot differ')
        actors.append({'actor_id_sha256':digest(a['id']),**{k:a.get(k) for k in
            ('resources','is_active','initial_funding','project_start_year','project_end_year')}})
    if not actors or len({a['actor_id_sha256'] for a in actors})!=len(actors):raise ValueError('unique actual native authors required')
    actors.sort(key=lambda a:a['actor_id_sha256'])
    return {'year':state['year'],'actors':actors,'year_end_active_authors':sum(a['is_active'] for a in actors),
        'year_end_total_resources':math.fsum(a['resources'] for a in actors),
        'year_end_minimum_actor_resources':min(a['resources'] for a in actors),
        'year_end_maximum_actor_resources':max(a['resources'] for a in actors)}


def worker(args):
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.native_benchmark_source import source_proofs
    from utopia.optimization.native_jobs import pinned_revision
    from utopia.optimization.native_numeric_designer import checked
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import file_sha256,write_json_atomic
    run,args.output=args.run.resolve(),args.output.resolve();source=Path.cwd()
    if args.output.exists() or args.output.is_relative_to(run) or args.output.is_relative_to(source):
        raise ValueError('fresh resource readout outside original raw/source required')
    before=_inventory(run);audit_hash=file_sha256(args.audit)
    audit=checked(json.loads(args.audit.read_text()));plan=checked(json.loads((run/'plan.json').read_text()))
    if (audit['schema']!='scienceutopia.pre-scale-search-audit.v1' or audit['source_commit']!=pinned_revision(source)
            or audit['source_commit']!=plan['source_commit'] or audit['plan_sha256']!=plan['content_sha256']
            or digest(before)!=audit['raw_inventory_sha256'] or len(before)!=audit['raw_files']
            or not (run/'complete.json').exists()):raise ValueError('exact closed original study/audit/inventory required')
    proof=source_proofs(source,plan['source_commit'],scripts=['scripts/native_benchmark_physical.py'],resources=[plan['protocol']])
    cells={}
    for cell in run.glob('**/worlds/*'):
        if not cell.is_dir():continue
        if cell.name in cells:raise ValueError('ambiguous original physical cell')
        cells[cell.name]=cell
    worlds=[];skipped=[]
    for w in audit['worlds']:
        p=w['physical_proof']
        if p['status']!='complete':skipped.append({'identity':w['identity'],'status':w['status']});continue
        cell=cells[w['identity']+'-s'+str(w['seed'])];annual=[]
        if [a['year'] for a in p['annual_checkpoints']]!=[1,2,3,4]:raise ValueError('four exact audited annual boundaries required')
        for a in p['annual_checkpoints']:
            paths=list(cell.rglob(f'portable_checkpoint_year_{a["year"]}.json.gz'))
            if len(paths)!=1 or file_sha256(paths[0])!=a['checkpoint_sha256']:raise ValueError('annual checkpoint differs from original full audit')
            state=read_portable_checkpoint(paths[0])
            if state['year']!=a['year'] or state['native_system']['spec']!=w['system']:raise ValueError('annual native system/year differs')
            annual.append({**snapshot(state),'checkpoint_sha256':a['checkpoint_sha256'],
                'project_cost_policy':state['project_cost_policy']})
        ids={x['actor_id_sha256'] for x in annual[0]['actors']}
        if any({x['actor_id_sha256'] for x in r['actors']}!=ids for r in annual):raise ValueError('native author identities changed across saved boundaries')
        m=p['measurement']['metrics'];last=annual[-1]
        if (m['native.final_active_authors']['value']!=last['year_end_active_authors']
                or not math.isclose(m['native.final_author_resources']['value'],last['year_end_total_resources'],rel_tol=1e-12,abs_tol=1e-12)):
            raise ValueError('final resource/activity reconstruction differs from original measurement')
        worlds.append({'identity':w['identity'],'role':w['role'],'seed':w['seed'],'annual':annual})
    if before!=_inventory(run) or audit_hash!=file_sha256(args.audit) or pinned_revision(source)!=plan['source_commit']:
        raise ValueError('original evidence changed during resource readout')
    rows=[r for w in worlds for r in w['annual']];actors=[a for r in rows for a in r['actors']]
    from collections import Counter
    result={'schema':'scienceutopia.native-year-end-resource-support.v1','source_commit':plan['source_commit'],
        'plan_sha256':plan['content_sha256'],'input_full_audit_content_sha256':audit['content_sha256'],
        'input_full_audit_file_sha256':audit_hash,'source_proof':proof,'raw_inventory_sha256':digest(before),
        'raw_files':len(before),'worlds':worlds,'skipped_worlds':skipped,
        'summary':{'complete_worlds':len(worlds),'skipped_worlds':len(skipped),'annual_boundaries':len(rows),
            'actor_boundaries':len(actors),'active_actor_boundaries':sum(a['is_active'] for a in actors),
            'minimum_observed_year_end_actor_resources':min(a['resources'] for a in actors),
            'maximum_observed_year_end_actor_resources':max(a['resources'] for a in actors),
            'year_end_active_author_distribution':dict(Counter(str(r['year_end_active_authors']) for r in rows)),
            'recorded_initial_funding_distribution':dict(Counter(str(a['initial_funding']) for a in actors))},
        'scope':{'new_model_calls':0,'new_native_worlds':0,'new_authored_code_executions':0,
            'within_year_resource_minima_observed':False,'transient_exits_excluded':False,
            'resource_constraint_never_binding_claimed':False,'new_loss_chosen':False,'full_raw_audit_repeated':False},
        'analysis_adapter_sha256':file_sha256(Path(__file__))}
    result['content_sha256']=digest(result);write_json_atomic(args.output,result,sort_keys=True,allow_nan=False)
    print(json.dumps({'content_sha256':result['content_sha256'],'summary':result['summary']}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','audit','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--frozen-source',type=Path);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.worker:worker(a);return
    if a.frozen_source is None:raise ValueError('explicit unchanged original source required')
    script=Path(__file__).resolve();before=hashlib.sha256(script.read_bytes()).hexdigest()
    response=subprocess.run([sys.executable,'-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(a.frozen_source.resolve()),str(script),'--worker','--run',str(a.run.resolve()),
        '--audit',str(a.audit.resolve()),'--output',str(a.output.resolve())],cwd=a.frozen_source,
        env={**os.environ,'PYTHONHASHSEED':'42'},timeout=900,check=False)
    if hashlib.sha256(script.read_bytes()).hexdigest()!=before:raise ValueError('resource analysis adapter changed')
    if response.returncode:raise SystemExit(response.returncode)


if __name__=='__main__':main()
