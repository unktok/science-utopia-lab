"""Original-source cold proof of the four normally closed resource controls."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys


def worker(root,output):
    from scripts import run_native_liquidity_support_v1 as driver
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.native_benchmark_source import source_proofs
    from scripts.native_benchmark_physical import physical_proof
    from scripts.analyze_native_design_benchmark import loaded
    from utopia.optimization.loss import evaluate_loss
    from utopia.optimization.native_discrete_policy import verify_native_observation
    from utopia.optimization.blackbox import Observation
    from utopia.system import SystemSpec
    from utopia.system.design_patch import clone,digest
    from utopia.utils.data_utils import file_sha256,write_json_atomic
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists() or output.is_relative_to(root):raise ValueError('fresh audit outside raw required')
    with (root/'writer.lock').open('r') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        before=_inventory(root);p=driver.require_plan(root);start=driver.read(root/'started.json');end=driver.read(root/'terminal.json')
        if (start['schema']!=driver.SCHEMA+'.start' or start['plan_sha256']!=p['content_sha256']
                or end['schema']!=driver.SCHEMA+'.terminal' or end['status']!='closed' or end['complete_worlds']!=4):
            raise ValueError('normal four-world native closure required')
        source=source_proofs(driver.ROOT,p['source_commit'],scripts=['scripts/run_native_liquidity_support_v1.py',
            'scripts/native_benchmark_physical.py'],resources=[driver.PROTOCOL,'utopia/system/native_liquidity_controls.py'])
        worlds=[];cells=set();caches=set()
        for job in p['jobs']:
            directory=root/'worlds-by-job'/job['identity'];dispatched=driver.read(directory/'started.json')
            if dispatched['job']!=job:raise ValueError('original resource job differs')
            o=driver.read(directory/'observation.json');spec=SystemSpec.from_dict(job['system'])
            world={**clone(p['world']),'world_conditions':clone(job['world_conditions'])}
            if (o['candidate']!=job['system'] or o['suggestion_id']!=job['identity'] or o['status']!='complete'):
                raise ValueError('complete literal native control required')
            verify_native_observation(Observation.from_dict(o),world,[job['seed']])
            cell=directory/'worlds'/(job['identity']+'-s'+str(job['seed']));cells.add(cell.resolve())
            caches.add((cell/'replies/responses.sqlite').resolve())
            gate=loaded(cell/'role-load-000.json',cell/'loaded-role-context-000.json',provider=p['scientist'],
                purpose='before-native-world:'+cell.name,role='scientist')
            proof=physical_proof(cell,spec,world=world,seed=job['seed'],years=4,evidence=o['metadata']['runs'][0])
            if o['metadata']['measurements']!=[proof['measurement']]:raise ValueError('checkpoint measurement differs')
            scores={k:evaluate_loss(v,[proof['measurement']]) for k,v in p['losses'].items()}
            if (o['loss']!=scores['throughput']['loss'] or
                    {k:v for k,v in driver.read(directory/'cross-scores.json').items() if k!='content_sha256'}!=scores):
                raise ValueError('literal native losses differ')
            from utopia.runtime.checkpointing import read_portable_checkpoint
            from utopia.funding.accounting import ResourceLedger
            from types import SimpleNamespace
            annual=[];previous_events=[]
            for item in proof['annual_checkpoints']:
                year=item['year'];path=cell/'simulation'/('portable_checkpoint_year_'+str(year)+'.json.gz')
                if not path.is_file():
                    matches=list(cell.rglob(path.name))
                    if len(matches)!=1:raise ValueError('unique audited annual resource checkpoint required')
                    path=matches[0]
                if file_sha256(path)!=item['checkpoint_sha256']:raise ValueError('annual resource checkpoint differs')
                state=read_portable_checkpoint(path)
                authors=[a for a in state['ecosystem_data']['agents'] if a['can_author']]
                actors={a['id']:SimpleNamespace(id=a['id'],can_author=True,resources=a['resources'],is_active=a['is_active']) for a in authors}
                ledger=ResourceLedger(state['resource_ledger'])
                reconciled=ledger.reconcile(year,actors,require_closed=True)
                events=state['native_system']['events']
                if events[:len(previous_events)]!=previous_events:raise ValueError('resource event prefix differs')
                previous_events=events
                transfers=[e for e in events if e['event_type']=='native.system.resource_transferred' and e['year']==year]
                annual.append({'year':year,'authors':[{k:clone(a[k]) for k in ('id','resources','is_active')} for a in authors],
                    'ledger_reconciliation':reconciled,'transfer_events':transfers})
            worlds.append({'identity':job['identity'],'role':'developer-liquidity-control','seed':job['seed'],
                'initial_funding':job['initial_funding'],'condition':job['condition'],'system':job['system'],
                'status':'complete','scores':{k:v['loss'] for k,v in scores.items()},'physical_proof':proof,
                'annual_resources':annual,'loaded':gate})
        if (cells!={d.resolve() for d in root.glob('worlds-by-job/*/worlds/*') if d.is_dir()}
                or caches!={d.resolve() for d in root.rglob('responses.sqlite')}
                or set(j['identity'] for j in p['jobs'])!={d.name for d in (root/'worlds-by-job').iterdir()}):
            raise ValueError('unaccounted native resource world/cache/job')
        if before!=_inventory(root):raise ValueError('resource raw evidence changed during cold audit')
        result={'schema':'scienceutopia.native-liquidity-support-audit.v1','source_commit':p['source_commit'],
            'plan_sha256':p['content_sha256'],'source_proof':source,'closure':{'started':start,'terminal':end},
            'worlds':worlds,'raw_inventory_sha256':digest(before),'raw_files':len(before),
            'analysis_adapter_sha256':file_sha256(Path(__file__)),
            'new_model_calls':0,'new_code_executions':0,'policy_selection':False,'publication_ready':False}
        result['content_sha256']=digest(result);write_json_atomic(output,result,sort_keys=True,allow_nan=False)
        print(json.dumps({'audit':str(output),'worlds':4,'content_sha256':result['content_sha256']}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if args.worker:worker(args.run,args.output);return
    if json.loads((args.run/'terminal.json').read_text())['status']!='closed':raise ValueError('normal closure required before audit')
    script=Path(__file__).resolve()
    response=subprocess.run([sys.executable,'-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()),str(script),'--worker','--run',str(args.run.resolve()),
        '--frozen-source',str(args.frozen_source.resolve()),'--output',str(args.output.resolve())],
        cwd=args.frozen_source,env={**os.environ,'PYTHONHASHSEED':'42'},timeout=1800,check=False)
    if response.returncode:raise SystemExit(response.returncode)


if __name__=='__main__':main()
