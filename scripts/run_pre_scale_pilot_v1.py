"""Finite pre-scale stages on pinned source; never changes a running plan."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import time

from utopia.optimization.blackbox import Suggestion
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_benchmark_controls import objective_specs
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory
from utopia.optimization.native_numeric_designer import NumericDesigner, replay_numeric, save, checked, SCHEMA as NUMERIC
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_scientist_load_v38 import load_local_role
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.optimization.loss import evaluate_loss
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.system.native_information_institution import information_system, information_design_space
from utopia.utils.data_utils import file_sha256, write_json_atomic

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'research/protocols/campaigns/pre-scale-information-v1.md'
SCHEMA = 'scienceutopia.pre-scale-pilot.v1'
SEEDS = (41001, 41011, 41017)


def read(path):
    return checked(json.loads(Path(path).read_text()))


def prepare(args):
    source = pinned_revision(ROOT)
    if args.output.exists():
        raise ValueError('fresh experiment destination required')
    previous = json.loads(args.operator_binding_plan.read_text())
    scientist = previous['scientist']; designer = previous['designer']
    backend = backend_binding(designer)
    systems = {k:information_system(designer['image_id'],condition=k).to_dict() for k in ('M0','M1','M2','M3')}
    plan = {'schema':SCHEMA+'.plan', 'source_commit':source, 'runtime':runtime_binding(),
        'protocol':PROTOCOL, 'protocol_sha256':file_sha256(ROOT/PROTOCOL),
        'scientist':scientist, 'designer':designer, 'backend':backend,
        'data_cache':str(args.data_cache.resolve()), 'systems':systems, 'losses':objective_specs(),
        'mechanism_seeds':list(SEEDS), 'years':4, 'numeric_calibration_cases':['throughput','efficiency'],
        'numeric_settings':{'max_calls':2, 'wall_seconds':1200, 'num_ctx':40960,
            'num_predict':8192,'temperature':.6,'think':False,'http_timeout_seconds':[10,900]},
        'budget':{'M_worlds':12,'D_numeric_sessions':2,'D_numeric_generation_POSTs':4,
            'M_scientist_http_attempts_per_world':1024,'replace_failed_slots':False},
        'claims':{'small_development_mechanism_study':True, 'causal_generalization':False,
            'designer_or_gradient_superiority':False, 'scientific_truth_improvement':False}}
    args.output.mkdir(parents=True)
    save(args.output/'plan.json',plan)
    print(json.dumps({'prepared_source':source,'new_model_calls':0,'M_worlds_upper_bound':12}),flush=True)


def require_plan(root):
    plan=read(root/'plan.json')
    if (plan['source_commit'] != pinned_revision(ROOT) or plan['runtime'] != runtime_binding()
            or file_sha256(ROOT/PROTOCOL) != plan['protocol_sha256']):
        raise ValueError('pre-scale source/protocol changed')
    return plan


def numeric_calibration(root,plan,*,request_factory=None):
    directory=root/'numeric-readiness'
    if directory.exists():
        raise ValueError('finite numeric calibration cannot be redispatched')
    directory.mkdir()
    load_local_role(directory/'designer-load.json',provider=plan['designer'],role='designer',
                    purpose='pre-scale-numeric-readiness')
    author=NumericDesigner(directory/'authoring',provider=plan['designer'],backend=plan['backend'],
        calibration=True,inference_lock=root/'inference.lock')
    rows=[]
    for objective in plan['numeric_calibration_cases']:
        anchor=SystemSpec.from_dict(plan['systems']['M1'])
        c=NativeAdaptiveDesignCampaign(directory/objective,initial_system=anchor,
            loss_spec=plan['losses'][objective],seeds=[42],world_binding={'source_commit':plan['source_commit'],
                **plan['scientist'],'years':4},strategies={'numeric':{'method':'direct-literal-numeric'}},
            mode='blackbox',design_space=information_design_space(anchor,'parameters'))
        request=(request_factory(objective) if request_factory is not None
                 else c._request([],c._strategy_initial(),1))
        definition=author(request)
        path=author.directory/('generation-'+digest(request)); replay=replay_numeric(path)
        valid=definition is not None and replay['definition']==definition
        rows.append({'objective':objective,'request_sha256':digest(request),
            'journal_relative':str(path.relative_to(root)), 'submitted':valid,
            'result_sha256':file_sha256(path/'result.json'), 'scientific_loss_observed':False})
        print(json.dumps({'stage':'numeric-readiness','objective':objective,'submitted':valid}),flush=True)
        # An unknown/cancel-unconfirmed model request must not be followed by
        # another role or generation in this calibration.
        results=[read(p) for p in sorted(path.glob('call-*.result.json'))]
        if any((r.get('error') or {}).get('type')=='CompletionUnknown' for r in results):
            break
    save(directory/'certificate.json',{'schema':NUMERIC+'.certificate','provider':plan['designer'],
        'backend':plan['backend'],'runtime':runtime_binding(),'settings':plan['numeric_settings'],
        'created_unix_seconds':time.time(),'cases':rows,
        'unattempted_cases':plan['numeric_calibration_cases'][len(rows):],
        'passed':len(rows)==len(plan['numeric_calibration_cases']) and all(r['submitted'] for r in rows),
        'scope':'Two literal numeric objective-conditioned submissions; not general code/graph readiness.',
        'new_native_worlds':0})


def mechanisms(root,plan):
    directory=root/'mechanisms';directory.mkdir(exist_ok=True)
    for index,(seed,condition) in enumerate((s,c) for s in SEEDS for c in ('M0','M1','M2','M3')):
        identity=condition+'-s'+str(seed); cell=directory/identity
        if (cell/'started.json').exists():
            if not (cell/'observation.json').exists():
                raise ValueError('unknown prior mechanism world consumes its slot; no redispatch')
            continue
        spec=information_system(plan['scientist']['image_id'],condition=condition,seed=seed)
        save(cell/'started.json',{'schema':SCHEMA+'.mechanism-start','identity':identity,
            'plan_sha256':plan['content_sha256'],'system':spec.to_dict(),'seed':seed,
            'started_utc':datetime.now(timezone.utc).isoformat()})
        factory=LocalRoleBoundNativeFactory(cell/'worlds',plan['data_cache'],years=4,corpus_years=4,
            designer_provider=plan['designer'],record_wire=True,record_code=True,maximum_http_attempts=1024,
            experiment_binding={'protocol':PROTOCOL,'role':'mechanism-development',
                'plan_sha256':plan['content_sha256']},inference_lock=root/'inference.lock')
        if factory.model_digest!=plan['scientist']['model_digest'] or factory.corpus_sha256!=plan['scientist']['corpus_sha256']:
            raise ValueError('actual scientist/corpus differs from frozen operator binding')
        observation=evaluate_native_suggestion(Suggestion(identity,spec.to_dict(),index,'developer-mechanism-control'),
            seeds=[seed],simulation_factory=factory,loss_spec=plan['losses']['throughput']).to_dict()
        save(cell/'observation.json',observation)
        scores={k:evaluate_loss(v,observation['metadata']['measurements']) for k,v in plan['losses'].items()}
        save(cell/'cross-scores.json',scores)
        status={'schema':SCHEMA+'.progress','stage':'M','last_completed':identity,
            'completed_observation_files':len(list(directory.glob('*/observation.json'))),'target_slots':12,
            'last_status':observation['status'],'last_cross_scores':{k:v['loss'] for k,v in scores.items()}}
        write_json_atomic(root/'progress.json',status,sort_keys=True,allow_nan=False)
        print(json.dumps(status),flush=True)
        if observation['status']!='complete':
            raise ValueError('mechanism world failed; retain exact failure and stop this source')
    save(root/'mechanisms-complete.json',{'schema':SCHEMA+'.M-complete','slots':12,
        'plan_sha256':plan['content_sha256'],'all_observation_file_sha256':{
            str(p.relative_to(root)):file_sha256(p) for p in sorted(directory.glob('*/observation.json'))}})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['prepare','numeric-readiness','mechanisms'])
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--operator-binding-plan',type=Path)
    p.add_argument('--data-cache',type=Path)
    args=p.parse_args()
    if args.stage=='prepare':
        prepare(args);return
    plan=require_plan(args.output)
    with (args.output/'writer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if args.stage=='numeric-readiness':numeric_calibration(args.output,plan)
        else:mechanisms(args.output,plan)


if __name__=='__main__':main()
