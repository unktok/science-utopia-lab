"""Read-only original-source audit of the separate fixed-submission evaluation."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def worker(root, output):
    from scripts import run_native_fixed_candidate_evaluation_v1 as driver
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.analyze_native_design_benchmark import loaded
    from scripts.native_benchmark_physical import physical_proof
    from scripts.native_benchmark_source import source_proofs
    from utopia.optimization.blackbox import Observation
    from utopia.optimization.native_discrete_policy import verify_native_observation
    from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
    from utopia.system import SystemSpec
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import file_sha256, write_json_atomic
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(root) or output.is_relative_to(driver.ROOT):
        raise ValueError('fresh audit output outside scientific source/raw required')
    read = driver.read
    with (root/'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = _inventory(root); p = driver.require_plan(root)
        original, origin_audit = driver.origin_evidence(p['origin'])
        if (driver.fixed_selection(original, origin_audit) != p['fixed_selection']
                or p['origin_audit_content_sha256'] != origin_audit['content_sha256']):
            raise ValueError('selection differs from original stopped submissions')
        usages = [read(path) for path in sorted(root.glob('seed-usage-*.json'))]
        rebuilt = driver.build_plan(original, origin_audit, source=p['source_commit'], origin=p['origin'], usages=usages)
        if rebuilt != {k:v for k,v in p.items() if k != 'content_sha256'}:
            raise ValueError('evaluation plan differs from deterministic reconstruction')
        start, end = read(root/'started.json'), read(root/'terminal.json')
        if (start['schema'] != driver.SCHEMA+'.start' or start['plan_sha256'] != p['content_sha256']
                or end['schema'] != driver.SCHEMA+'.terminal' or end['status'] != 'closed'
                or end['completed_jobs'] != len(p['jobs'])
                or set(end) != {'schema','status','ended_utc','completed_jobs','content_sha256'}):
            raise ValueError('normal separate evaluation closure required')
        proof = source_proofs(driver.ROOT, p['source_commit'], scripts=[
            'scripts/run_native_fixed_candidate_evaluation_v1.py',
            'scripts/native_benchmark_physical.py', 'scripts/run_pre_scale_search_v1.py'],
            resources=[driver.PROTOCOL])
        worlds = []; cells = set(); caches = set()
        for job in p['jobs']:
            directory = root/'evaluation'/job['identity']; dispatched = read(directory/'started.json')
            if (dispatched['identity'], dispatched['system'], dispatched['seed'], dispatched['role']) != (
                    job['identity'], job['system'], job['seed'], 'selection-fixed-evaluation'):
                raise ValueError('world differs from frozen evaluation job')
            spec = SystemSpec.from_dict(job['system']); o = read(directory/'observation.json')
            if (o['status'] != 'complete' or o['suggestion_id'] != job['identity']
                    or o['candidate'] != job['system'] or o['metadata']['system_fingerprint'] != spec.fingerprint
                    or o['metadata']['loss_spec_sha256'] != loss_spec_sha256(p['losses']['throughput'])):
                raise ValueError('observation differs from fixed policy/loss')
            verify_native_observation(Observation.from_dict(o), p['world'], [job['seed']])
            cell = directory/'worlds'/(job['identity']+'-s'+str(job['seed'])); cells.add(cell.resolve())
            caches.add((cell/'replies/responses.sqlite').resolve())
            gate = loaded(cell/'role-load-000.json', cell/'loaded-role-context-000.json',
                provider=p['scientist'], purpose='before-native-world:'+cell.name, role='scientist')
            physical = physical_proof(cell, spec, world=p['world'], seed=job['seed'], years=4,
                                      evidence=o['metadata']['runs'][0])
            if o['metadata']['measurements'] != [physical['measurement']]:
                raise ValueError('measurement differs from actual checkpoint')
            scores = {k:evaluate_loss(v, o['metadata']['measurements']) for k,v in p['losses'].items()}
            if (read(directory/'cross-scores.json') != {
                    **scores, 'content_sha256':digest(scores)} or o['loss'] != scores['throughput']['loss']
                    or o['metadata']['loss_evaluation'] != scores['throughput']):
                raise ValueError('literal cross-score/loss differs')
            worlds.append({**job, 'role':'selection-fixed-evaluation', 'status':o['status'],
                'scores':{k:v['loss'] for k,v in scores.items()}, 'loaded':gate, 'physical_proof':physical})
        if (cells != {v.resolve() for v in root.glob('**/worlds/*') if v.is_dir()}
                or caches != {v.resolve() for v in root.rglob('responses.sqlite')}
                or {v.name for v in (root/'evaluation').iterdir()} != {j['identity'] for j in p['jobs']}):
            raise ValueError('unaccounted physical evaluation world')
        progress = json.loads((root/'progress.json').read_text())
        if ({k:v for k,v in progress.items() if k != 'observed_utc'} != {
                'stage':'closed', 'active':None, 'complete_jobs':len(p['jobs']), 'total_jobs':len(p['jobs'])}):
            raise ValueError('final progress differs from audited worlds')
        if before != _inventory(root): raise ValueError('raw evaluation changed during audit')
        result = {'schema':'scienceutopia.native-fixed-candidate-evaluation-audit.v1',
            'source_commit':p['source_commit'], 'plan_sha256':p['content_sha256'], 'source_proof':proof,
            'closure':{'started':start, 'terminal':end, 'progress':progress}, 'worlds':worlds,
            'fixed_selection':p['fixed_selection'], 'origin_audit_content_sha256':origin_audit['content_sha256'],
            'raw_inventory_sha256':digest(before), 'raw_files':len(before),
            'analysis_adapter_sha256':file_sha256(Path(__file__)),
            'new_model_calls':0, 'new_code_executions':0, 'original_search_status':'stopped'}
        result['content_sha256'] = digest(result)
        write_json_atomic(output, result, sort_keys=True, allow_nan=False)
        print(json.dumps({'audit':str(output), 'content_sha256':result['content_sha256'], 'worlds':len(worlds)}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('run','output','frozen-source'): p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--worker', action='store_true'); a = p.parse_args()
    if a.worker: worker(a.run, a.output); return
    terminal = json.loads((a.run/'terminal.json').read_text())
    if terminal.get('status') != 'closed': raise ValueError('closed separate evaluation required')
    script = Path(__file__).resolve(); before = hashlib.sha256(script.read_bytes()).hexdigest()
    result = subprocess.run([sys.executable,'-c',
        'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(a.frozen_source.resolve()), str(script), '--worker', '--run',str(a.run.resolve()),
        '--output',str(a.output.resolve()), '--frozen-source',str(a.frozen_source.resolve())],
        cwd=a.frozen_source.resolve(), env={**os.environ,'PYTHONHASHSEED':'42'}, timeout=1800, check=False)
    if hashlib.sha256(script.read_bytes()).hexdigest() != before: raise ValueError('audit adapter changed')
    if result.returncode: raise SystemExit(result.returncode)


if __name__ == '__main__': main()
