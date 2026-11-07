#!/usr/bin/env python3
"""Finite eight-world strong-rule baseline pilot; no designer or hidden refill."""
from datetime import datetime, timezone
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utopia.optimization.native_benchmark_controls import control_systems, objective_specs
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-benchmark-controls.v2'
PROTOCOL = 'research/protocols/campaigns/native-benchmark-controls-v2-a1.md'
CLASSIFICATION = 'actual-native-strong-control-development-v2'
LOSSES = ('native-joint-v5-throughput', 'native-reviewed-production-efficiency-v13')


def save_new(path, value):
    path = Path(path)
    if path.exists():
        raise ValueError('immutable benchmark record already exists: '+str(path))
    write_json_atomic(path, value, sort_keys=True, allow_nan=False)


def build_plan(*, source, scientist, designer, runtime_seed):
    from utopia.optimization.native_search_v14 import validate_provider_binding
    from utopia.optimization.native_designer_roles_v38 import validate_designer_binding
    validate_provider_binding(scientist)
    validate_designer_binding(designer, scientist_binding=scientist)
    systems = {k: v.to_dict() for k,v in control_systems(scientist['image_id']).items()}
    experiment = {'protocol': PROTOCOL, 'role': 'development-strong-rule-baselines'}
    plan = {'schema': SCHEMA, 'source_commit': source, 'scientist': clone(scientist),
        'designer_binding_metadata_only': clone(designer), 'designer_calls': 0,
        'runtime_seed_binding': clone(runtime_seed), 'experiment': experiment,
        'world': {**clone(scientist), 'source_commit': source, 'years': 2,
            'runtime_seed_binding': clone(runtime_seed)},
        'systems': systems, 'order': list(systems), 'losses': objective_specs(),
        'seed': 42, 'years': 2, 'maximum_worlds': 8, 'refill': False,
        'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT/PROTOCOL),
        'classification': CLASSIFICATION, 'held_out': False, 'independent_search_comparison': False}
    plan['content_sha256'] = digest(plan)
    return plan


def prepare(args):
    from utopia.system.code_mechanisms import DockerCodeExecutor
    source = pinned_revision(ROOT)
    config = json.loads(args.designer_provider_config.read_text())
    if set(config) != {'provider_binding'}:
        raise ValueError('exact existing operator binding required')
    designer = config['provider_binding']
    factory = LocalRoleBoundNativeFactory(args.output/'binding-only-no-worlds', args.data_cache,
        years=2, corpus_years=4, designer_provider=designer)
    scientist = {k: clone(getattr(factory,k)) for k in
        ('model','model_digest','corpus_sha256','corpus_years','dataset_identity')}
    scientist['image_id'] = DockerCodeExecutor().image_id
    plan = build_plan(source=source, scientist=scientist, designer=designer,
        runtime_seed=factory.runtime_seed_binding)
    location = args.output/'plan.json'
    if location.exists():
        if json.loads(location.read_text()) != plan:
            raise ValueError('benchmark plan changed')
    else:
        save_new(location,plan)
    return plan


def run_slots(root, plan, factory_builder):
    """Injectable only for scripted software tests; actual CLI binds real factory."""
    root = Path(root)
    rows = []
    for index,name in enumerate(plan['order']):
        directory = root/'controls'/name
        suggestion = Suggestion('control-'+name, plan['systems'][name], index, 'developer-control')
        save_new(directory/'started.json', {'slot': index, 'name': name,
            'candidate_sha256': digest(suggestion.candidate), 'started_utc': datetime.now(timezone.utc).isoformat()})
        observation = evaluate_native_suggestion(suggestion, seeds=[plan['seed']],
            simulation_factory=factory_builder(directory/'worlds'), loss_spec=plan['losses']['throughput'])
        o = observation.to_dict()
        scores = {name: evaluate_loss(loss,o['metadata']['measurements']) for name,loss in plan['losses'].items()}
        save_new(directory/'observation.json',o)
        save_new(directory/'cross-scores.json',scores)
        row = {'name': name, 'slot': index, 'status': o['status'],
            'cross_scores': {key:value['loss'] if o['status']=='complete' else None for key,value in scores.items()}}
        rows.append(row)
        # This is explicitly a replaceable derived heartbeat, not immutable raw evidence.
        progress = {'schema': SCHEMA+'.progress', 'plan_sha256': plan['content_sha256'],
            'rows': rows, 'consumed_slots': len(rows), 'terminal': len(rows)==plan['maximum_worlds']}
        progress['content_sha256'] = digest(progress)
        write_json_atomic(root/'progress.json',progress,sort_keys=True,allow_nan=False)
        print(json.dumps(row),flush=True)
    return 0


def execute(args):
    plan = prepare(args)
    if args.action == 'prepare':
        return 0
    def factory(path):
        return LocalRoleBoundNativeFactory(path,args.data_cache,years=2,corpus_years=4,
            designer_provider=plan['designer_binding_metadata_only'],record_wire=True,record_code=True,
            experiment_binding=plan['experiment'],inference_lock=args.output/'inference.lock')
    return run_slots(args.output,plan,factory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','run'])
    parser.add_argument('--execute-authorized',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--data-cache',type=Path,required=True)
    parser.add_argument('--designer-provider-config',type=Path,required=True)
    args = parser.parse_args(argv)
    args.output = args.output.resolve();args.output.mkdir(parents=True,exist_ok=True)
    source = pinned_revision(ROOT)
    with (args.output/'writer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        prefix = 'writer' if args.action=='run' else 'prepare'
        start = {'schema': SCHEMA+'.writer','source_commit':source,'action':args.action,
            'status':'started','pid':os.getpid(),'started_utc':datetime.now(timezone.utc).isoformat(),
            'environment':{k:os.environ.get(k) for k in
                ('PYTHONHASHSEED','CUDA_VISIBLE_DEVICES','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE')}}
        save_new(args.output/(prefix+'.started.json'),start)
        end = clone(start)
        try:
            result = execute(args)
        except BaseException as error:
            end.update(status='aborted',error_type=type(error).__name__,error=str(error))
            raise
        else:
            end.update(status='exited',exit_code=result)
            return result
        finally:
            end['ended_utc'] = datetime.now(timezone.utc).isoformat()
            save_new(args.output/(prefix+'.ended.json'),end)


if __name__=='__main__':
    raise SystemExit(main())
