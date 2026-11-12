"""Original-source cold proof of the normally closed instruction timing assay."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys


def worker(root, output):
    from scripts import run_native_instruction_timing_support_v1 as driver
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.analyze_native_design_benchmark import loaded
    from scripts.audit_native_institution_loop_v1 import epoch
    from scripts.native_benchmark_physical import physical_proof
    from scripts.native_benchmark_source import source_proofs
    from scripts.native_observer_physical_v1 import ColdObserver, accepted_request_keys, reconstruct_measurement
    from utopia.optimization.blackbox import Suggestion, Observation
    from utopia.optimization.native_discrete_policy import verify_native_observation
    from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import file_sha256, write_json_atomic
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(root) or output.is_relative_to(driver.ROOT):
        raise ValueError('fresh cold audit outside scientific source/raw required')
    with (root/'writer.lock').open('r') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        before=_inventory(root);p=driver.require_plan(root);start=driver.read(root/'started.json');end=driver.read(root/'terminal.json')
        if (start['schema']!=driver.SCHEMA+'.start' or end['schema']!=driver.SCHEMA+'.terminal'
                or start['plan_sha256']!=p['content_sha256'] or end['status']!='closed'
                or end['completed_jobs']!=3 or len(p['jobs'])!=3
                or epoch(end['ended_utc'])<epoch(start['started_utc'])):
            raise ValueError('normal exact three-control closure required')
        source=source_proofs(driver.ROOT,p['source_commit'],scripts=[
            'scripts/run_native_instruction_timing_support_v1.py',
            'scripts/native_benchmark_physical.py','scripts/native_observer_physical_v1.py'],
            resources=[driver.PROTOCOL,driver.CONTENT_LOSS])
        observer=ColdObserver(root/'observer',p['observer_contract']);observer_audit=observer.audit()
        if observer_audit!=driver.read(root/'observer-audit.json'):
            raise ValueError('original observer audit differs')
        cells=set();caches=set();eligible=set();worlds=[]
        for job in p['jobs']:
            directory=root/'controls'/job['identity'];dispatched=driver.read(directory/'started.json')
            s=Suggestion(job['identity'],job['system'],0,'developer-instruction-timing-control')
            if (dispatched['job']!=job or dispatched['suggestion']!=s.to_dict()
                    or not epoch(start['started_utc'])<=epoch(dispatched['started_utc'])<=epoch(end['ended_utc'])):
                raise ValueError('literal instruction control dispatch differs')
            o=driver.read(directory/'observation.json');spec=SystemSpec.from_dict(job['system']);m=o['metadata']
            if (o['status']!='complete' or o['suggestion_id']!=job['identity'] or o['candidate']!=job['system']
                    or m['system_fingerprint']!=spec.fingerprint
                    or m['loss_spec_sha256']!=loss_spec_sha256(p['losses']['throughput'])
                    or len(m['runs'])!=1 or len(m['measurements'])!=1 or m['technical_failures']):
                raise ValueError('complete literal native control required')
            cell=directory/'worlds'/(job['identity']+'-s'+str(job['seed']));cells.add(cell)
            caches.add(cell/'replies/responses.sqlite')
            gate=loaded(cell/'role-load-000.json',cell/'loaded-role-context-000.json',provider=p['scientist'],
                purpose='before-native-world:'+cell.name,role='scientist')
            proof=physical_proof(cell,spec,world=p['world'],seed=job['seed'],years=4,evidence=m['runs'][0])
            state=read_portable_checkpoint(m['runs'][0]['checkpoint_path'])
            eligible.update(accepted_request_keys(state,p['observer_contract']))
            rebuilt=reconstruct_measurement(state,proof['measurement'],observer)
            if m['measurements']!=[rebuilt]:raise ValueError('literal content measurement differs')
            verify_native_observation(Observation.from_dict(o),p['world'],[job['seed']])
            scores={k:evaluate_loss(v,[rebuilt]) for k,v in p['losses'].items()}
            if (o['loss']!=scores['throughput']['loss'] or m['loss_evaluation']!=scores['throughput']
                    or driver.read(directory/'cross-scores.json')!={**scores,'content_sha256':digest(scores)}):
                raise ValueError('actual control criterion differs')
            worlds.append({**job,'role':'developer-instruction-timing-control','status':'complete',
                'scores':{k:v['loss'] for k,v in scores.items()},'measurements':[rebuilt],
                'physical_proof':proof,'loaded':gate})
        if (cells!={v.resolve() for v in root.glob('**/worlds/*') if v.is_dir()}
                or caches!={v.resolve() for v in root.rglob('responses.sqlite')}
                or {v.name for v in (root/'controls').iterdir()}!={j['identity'] for j in p['jobs']}
                or not {r['key'] for r in observer_audit['rows']}<=eligible
                or list(root.rglob('dispatch-*.intent.json'))):
            raise ValueError('unaccounted control world/cache/critic/designer dispatch')
        progress=json.loads((root/'progress.json').read_text())
        if progress['stage']!='closed' or progress['active'] is not None or before!=_inventory(root):
            raise ValueError('scientific closure or raw inventory changed')
        result={'schema':driver.AUDIT_SCHEMA,'source_commit':p['source_commit'],'plan_sha256':p['content_sha256'],
            'source_proof':source,'closure':{'started':start,'terminal':end},'worlds':worlds,'observer':observer_audit,
            'raw_inventory_sha256':digest(before),'raw_files':len(before),
            'analysis_adapter_sha256':file_sha256(Path(__file__)),'new_model_calls':0,'new_code_executions':0,
            'policy_selection':False,'held_out_evaluation':False,'scientific_truth_measured':False,'publication_ready':False}
        result['content_sha256']=digest(result);write_json_atomic(output,result,sort_keys=True,allow_nan=False)
        print(json.dumps({'audit':str(output),'worlds':len(worlds),'content_sha256':result['content_sha256']}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.worker:worker(a.run,a.output);return
    if json.loads((a.run/'terminal.json').read_text())['status']!='closed':
        raise ValueError('normal instruction assay closure required')
    result=subprocess.run([sys.executable,'-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(a.frozen_source.resolve()),str(Path(__file__).resolve()),'--worker','--run',str(a.run.resolve()),
        '--frozen-source',str(a.frozen_source.resolve()),'--output',str(a.output.resolve())],cwd=a.frozen_source,
        env={**os.environ,'PYTHONHASHSEED':'42'},timeout=1800,check=False)
    if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
