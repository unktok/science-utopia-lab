"""Original-source fixed T/P evaluation proof; no inference or authored execution."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

SCHEMA='scienceutopia.native-capacity-fixed-evaluation-audit.v1'


def worker(root,output):
    from scripts import run_native_capacity_fixed_evaluation_v1 as driver
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.analyze_native_design_benchmark import loaded
    from scripts.native_benchmark_physical import physical_proof
    from scripts.native_benchmark_source import source_proofs
    from scripts.audit_native_institution_loop_v1 import epoch
    from utopia.optimization.blackbox import Suggestion,Observation
    from utopia.optimization.native_active_founders import measure_from_checkpoints
    from utopia.optimization.native_discrete_policy import verify_native_observation
    from utopia.optimization.loss import evaluate_loss,loss_spec_sha256
    from utopia.system import SystemSpec
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import file_sha256
    root,output=Path(root).resolve(),Path(output).resolve();read=driver.read
    if output.exists() or output.is_relative_to(root) or output.is_relative_to(driver.ROOT):
        raise ValueError('fresh audit outside scientific source/raw required')
    with (root/'writer.lock').open('r') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB);before=_inventory(root);p=driver.require_plan(root)
        start,end=read(root/'started.json'),read(root/'terminal.json')
        if (start['schema']!=driver.SCHEMA+'.start' or end['schema']!=driver.SCHEMA+'.terminal'
                or start['plan_sha256']!=p['content_sha256'] or end['status']!='closed'
                or end['completed_jobs']!=len(p['jobs']) or end['held_out_world_seeds'] is not True
                or epoch(end['ended_utc'])<epoch(start['started_utc']) or (root/'observer').exists()):
            raise ValueError('normal fixed T/P closure without critic required')
        for i in range(len(p['evaluation']['seed_usage'])):
            prepared=read(root/f'seed-usage-{i:02d}.json');dispatched=read(root/f'pre-dispatch-seed-usage-{i:02d}.json')
            if (prepared['content_sha256']!=p['evaluation']['seed_usage'][i]
                    or not dispatched['valid'] or dispatched['errors'] or dispatched['prior_matching_runs']
                    or dispatched['root']!=prepared['root'] or dispatched['seeds']!=p['evaluation']['seeds']
                    or not epoch(prepared['checked_utc'])<=epoch(dispatched['checked_utc'])<=epoch(start['started_utc'])):
                raise ValueError('literal pre-dispatch unused-seed proof differs')
        source=source_proofs(driver.ROOT,p['source_commit'],scripts=[
            'scripts/run_native_capacity_fixed_evaluation_v1.py','scripts/audit_native_capacity_fixed_evaluation_v1.py',
            'scripts/native_benchmark_physical.py'],resources=[driver.PROTOCOL,driver.INSTRUMENT])
        cells=set();caches=set();worlds=[]
        for job in p['jobs']:
            directory=root/'evaluation'/job['identity'];dispatched=read(directory/'started.json')
            suggestion=Suggestion(job['identity'],job['system'],0,'selection-fixed-evaluation')
            if (any(dispatched[k]!=v for k,v in job.items()) or dispatched['suggestion']!=suggestion.to_dict()
                    or not epoch(start['started_utc'])<=epoch(dispatched['started_utc'])<=epoch(end['ended_utc'])):
                raise ValueError('literal frozen evaluation dispatch differs')
            spec=SystemSpec.from_dict(job['system']);o=read(directory/'observation.json');m=o['metadata']
            if (o['suggestion_id']!=job['identity'] or o['candidate']!=job['system']
                    or m['system_fingerprint']!=spec.fingerprint
                    or m['loss_spec_sha256']!=loss_spec_sha256(p['losses']['throughput'])):
                raise ValueError('fixed native observation identity/loss differs')
            cell=directory/'worlds'/(job['identity']+'-s'+str(job['seed']));cells.add(cell)
            cache=cell/'replies/responses.sqlite'
            if cache.exists():caches.add(cache)
            gate=loaded(cell/'role-load-000.json',cell/'loaded-role-context-000.json',provider=p['scientist'],
                purpose='before-native-world:'+cell.name,role='scientist',allow_unconfirmed=o['status']=='failed')
            runs,measurements=m['runs'],m['measurements']
            if len(runs)>1 or len(measurements)>1 or measurements and not runs:
                raise ValueError('ambiguous fixed native observation')
            if runs:
                proof=physical_proof(cell,spec,world=p['world'],seed=job['seed'],years=4,evidence=runs[0])
                if measurements:
                    checkpoint=Path(runs[0]['checkpoint_path'])
                    paths=[checkpoint.parent/f'portable_checkpoint_year_{year}.json.gz' for year in range(5)]
                    rebuilt={**measure_from_checkpoints(proof['measurement'],paths),
                        'measurement_adapter_contract_sha256':digest(p['measurement_contract'])}
                    if measurements!=[rebuilt] or m['technical_failures']:
                        raise ValueError('literal initial/annual P and base measurements differ')
                    verify_native_observation(Observation.from_dict(o),p['world'],[job['seed']])
                elif o['status']!='failed' or not m['technical_failures']:
                    raise ValueError('missing P measurement without explicit technical failure')
            else:
                if o['status']!='failed' or not m['technical_failures']:
                    raise ValueError('unobserved job cannot acquire a loss')
                if cache.exists() and not gate['confirmed']:
                    raise ValueError('responses follow unconfirmed role load')
                proof=physical_proof(cell,spec,world=p['world'],seed=job['seed'],years=4) if cache.exists() else {
                    'status':'pre-response-journal-failure'}
            scores={k:evaluate_loss(v,measurements) for k,v in p['losses'].items()}
            if (o['loss']!=scores['throughput']['loss'] or m['loss_evaluation']!=scores['throughput']
                    or (o['status']=='complete')!=(scores['throughput']['status']=='complete')
                    or read(directory/'cross-scores.json')!={**scores,'content_sha256':digest(scores)}):
                raise ValueError('literal cross-score/status differs')
            worlds.append({**job,'role':'selection-fixed-evaluation','status':o['status'],
                'scores':{k:v['loss'] for k,v in scores.items()},'measurements':measurements,
                'physical_proof':proof,'loaded':gate})
        if (cells!={v.resolve() for v in root.glob('**/worlds/*') if v.is_dir()}
                or caches!={v.resolve() for v in root.rglob('responses.sqlite')}
                or {v.name for v in (root/'evaluation').iterdir()}!={j['identity'] for j in p['jobs']}
                or list(root.rglob('dispatch-*.intent.json'))):
            raise ValueError('unaccounted fixed world/cache/designer dispatch')
        progress=json.loads((root/'progress.json').read_text())
        if progress['stage']!='closed' or progress['active'] is not None:
            raise ValueError('fixed evaluation final progress differs')
        if before!=_inventory(root):raise ValueError('raw evaluation changed during cold proof')
        driver.save(output,{'schema':SCHEMA,'source_commit':p['source_commit'],'plan_sha256':p['content_sha256'],
            'source_proof':source,'closure':{'started':start,'terminal':end},
            'origin_audit_content_sha256':p['origin_audit_content_sha256'],'fixed_selection':p['fixed_selection'],
            'worlds':worlds,'raw_inventory_sha256':digest(before),'raw_files':len(before),
            'analysis_adapter_sha256':file_sha256(Path(__file__)),'new_model_calls':0,'new_code_executions':0,
            'held_out_world_seeds':True,'independent_optimizer_replications':False,'publication_ready':False})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    if args.worker:worker(args.run,args.output);return
    if json.loads((args.run/'terminal.json').read_text())['status']!='closed':
        raise ValueError('normal fixed evaluation closure required')
    result=subprocess.run([sys.executable,'-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()),str(Path(__file__).resolve()),'--worker','--run',str(args.run.resolve()),
        '--frozen-source',str(args.frozen_source.resolve()),'--output',str(args.output.resolve())],
        cwd=args.frozen_source,env={**os.environ,'PYTHONHASHSEED':'42'},timeout=1800,check=False)
    if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
