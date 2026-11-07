#!/usr/bin/env python3
"""Read-only physical evidence audit of all eight developer-control slots."""
import argparse
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from scripts import run_native_benchmark_controls as driver
from scripts.native_benchmark_source import source_proofs
from scripts.analyze_native_autonomous_search_v14 import (
    read, _inventory, audit_native_run_v14, partial_physical_proof_v14)
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.optimization.native_scientist_load_v38 import replay_load
from utopia.optimization.native_loaded_roles_v38 import replay_loaded_context
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic


def analyze(root,source):
    root = Path(root).resolve(); before = _inventory(root)
    try:
        closure = source_proofs(ROOT,source,scripts=[
            'scripts/run_native_benchmark_controls.py','scripts/analyze_native_benchmark_controls.py'],
            resources=[driver.PROTOCOL,*['research/objectives/losses/'+n+'.json' for n in driver.LOSSES]])
        plan = read(root/'plan.json')
        if plan['source_commit'] != source or plan != driver.build_plan(source=source,
                scientist=plan['scientist'],designer=plan['designer_binding_metadata_only'],
                runtime_seed=plan['runtime_seed_binding']):
            raise ValueError('control plan differs from frozen reconstruction')
        start,end = read(root/'writer.started.json'),read(root/'writer.ended.json')
        if (start.get('source_commit') != source or start.get('action')!='run' or start.get('status')!='started'
                or end!={**start,'status':'exited','exit_code':0,'ended_utc':end.get('ended_utc')}
                or datetime.fromisoformat(end['ended_utc']) < datetime.fromisoformat(start['started_utc'])):
            raise ValueError('control writer terminal record differs')
        rows,proofs,physical = [],{},set()
        for index,name in enumerate(plan['order']):
            directory = root/'controls'/name
            o = read(directory/'observation.json'); spec = SystemSpec.from_dict(plan['systems'][name])
            started = read(directory/'started.json')
            if ({k:started.get(k) for k in ('slot','name','candidate_sha256')} != {
                    'slot':index,'name':name,'candidate_sha256':digest(spec.to_dict())}
                    or o['candidate']!=spec.to_dict() or o['suggestion_id']!='control-'+name
                    or o['observation_id']!='observation-control-'+name):
                raise ValueError('control candidate identity differs')
            measurement = o['metadata']['measurements']
            score = {key:evaluate_loss(loss,measurement) for key,loss in plan['losses'].items()}
            if (score != read(directory/'cross-scores.json') or o['loss'] != score['throughput']['loss']
                    or o['metadata']['loss_evaluation'] != score['throughput']
                    or o['metadata']['loss_spec_sha256'] != loss_spec_sha256(plan['losses']['throughput'])
                    or o['metadata']['world_backend'] != 'native-research-world'
                    or o['metadata']['system_fingerprint'] != spec.fingerprint):
                raise ValueError('control score differs from exact measurements')
            cells = sorted((directory/'worlds').glob('*'))
            if len(cells)!=1 or cells[0].name!='control-'+name+'-s42':
                raise ValueError('control has undeclared/missing physical worlds')
            cell = cells[0];physical.add(cell.resolve())
            purpose='before-native-world:'+cell.name
            load = replay_load(read(cell/'role-load-000.started.json'),read(cell/'role-load-000.json'),
                provider=plan['scientist'],purpose=purpose)['empty_prompt_load_confirmed']
            context_path=cell/'loaded-role-context-000.json'
            context = replay_loaded_context(read(context_path),expected={'scientist':plan['scientist']},
                purpose=purpose) if context_path.exists() else False
            if (not load or not context) and o['status']=='complete':
                raise ValueError('complete control lacks confirmed scientist load/context')
            if o['status']=='complete':
                if len(o['metadata']['runs'])!=1 or o['metadata']['technical_failures']:
                    raise ValueError('complete control lacks one clean native trajectory')
                proof = audit_native_run_v14(directory,{'suggestion':{'candidate':spec.to_dict()}},o,
                    o['metadata']['runs'][0],plan['world'],driver.CLASSIFICATION,
                    expected_experiment=plan['experiment'],expected_loss=plan['losses']['throughput'])
                if measurement != [proof['measurement']]:
                    raise ValueError('control checkpoint measurement differs')
            elif o['status']=='failed' and o['loss'] is None and not measurement:
                if (cell/'replies/responses.sqlite').exists():
                    if not load or not context:
                        raise ValueError('native inference lacks a valid preceding load/context')
                    proof=partial_physical_proof_v14(cell,spec,plan['world'],driver.CLASSIFICATION)
                else:
                    if o['metadata']['runs'] or not o['metadata']['technical_failures']:
                        raise ValueError('pre-inference failure lacks its actual error')
                    if (cell/'wire-requests.jsonl').exists() or (cell/'code-contexts.jsonl').exists():
                        raise ValueError('recorded inference/code has no response-cache binding')
                    proof={'status':'failed-before-response-journal','loss':None,
                        'scientist_load_confirmed':load,'scientist_context_confirmed':context,
                        'files':_inventory(cell),'physical_responses':'unknown-not-imputed'}
            else:
                raise ValueError('control has unknown outcome/null semantics')
            proofs[name]=proof
            rows.append({'name':name,'slot':index,'status':o['status'],
                'cross_scores':{k:v['loss'] if o['status']=='complete' else None for k,v in score.items()}})
        if {p.resolve() for p in root.glob('controls/*/worlds/*')} != physical:
            raise ValueError('undeclared physical control world')
        if any(root.rglob('authoring')) or any(root.rglob('generation.json')):
            raise ValueError('static controls contain an undeclared designer campaign')
        progress={'schema':driver.SCHEMA+'.progress','plan_sha256':plan['content_sha256'],
            'rows':rows,'consumed_slots':8,'terminal':True}
        progress['content_sha256']=digest(progress)
        if read(root/'progress.json') != progress:
            raise ValueError('control heartbeat differs from all eight outcomes')
        result={'schema':driver.SCHEMA+'.audit','source_commit':source,'plan_sha256':plan['content_sha256'],
            'rows':rows,'proofs':proofs,'source_proofs':closure,'writer':{'started':start,'ended':end},
            'new_model_calls':0,'new_code_executions':0,'input_inventory':before,
            'best':{key:{'loss':min((r['cross_scores'][key] for r in rows if r['status']=='complete'),default=None)}
                for key in plan['losses']}}
        for key,v in result['best'].items():
            v['all_tied_names']=[r['name'] for r in rows if r['status']=='complete' and r['cross_scores'][key]==v['loss']]
        result['content_sha256']=digest(result)
        return result
    finally:
        if before != _inventory(root):
            raise ValueError('raw control evidence changed during audit')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--expected-source',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(argv)
    if a.output.exists() or a.output.resolve().is_relative_to(a.run.resolve()):
        p.error('audit output must be fresh and outside raw run')
    result=analyze(a.run,a.expected_source)
    write_json_atomic(a.output,result,sort_keys=True,allow_nan=False)
    print({k:result[k] for k in ['schema','content_sha256','best']})
    return 0


if __name__=='__main__':
    raise SystemExit(main())
