"""Finite T/E search with direct numeric and free staged code/graph proposals.

Prepare at a clean source before inference. This pilot is not a superiority
study. Complete/null slots, original losses and all ties remain visible.
"""
import argparse
from datetime import datetime,timezone
import fcntl
import json
import os
from pathlib import Path

from scripts.run_native_design_benchmark import selection_payload
from scripts.native_design_benchmark_plan import policy_identity
from scripts.native_benchmark_seed_usage import usage_inventory
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_benchmark_controls import objective_specs,selection_control,without_review
from utopia.optimization.native_bounded_staged_designer import BoundedStagedDesigner,execute as bounded_editor
from utopia.optimization.native_designer_preflight import runtime_binding,backend_binding,planned_cases
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.optimization.native_design_space import random_parameter_definition
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory
from utopia.optimization.native_numeric_designer import NumericDesigner,save,checked
from utopia.optimization.native_scientist_load_v38 import load_local_role
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.loss import evaluate_loss
from utopia.system import SystemSpec
from utopia.system.native_information_institution import information_system,information_design_space
from utopia.system.native_kernel import legacy_world_system
from utopia.system.design_patch import clone,digest
from utopia.utils.data_utils import file_sha256,write_json_atomic

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL='research/protocols/campaigns/pre-scale-search-v1.md'
SCHEMA='scienceutopia.pre-scale-search.v1'
OBJECTIVES=('throughput','efficiency')
METHODS=('parameters','code-fixed-graph','code-and-graph','random')
EVALUATION_SEEDS=(51001,51011,51017)
SEED=41001


def campaign(root,plan,run,arm):
    b=plan['campaign_bindings'][run][arm]
    return NativeAdaptiveDesignCampaign(Path(root)/'search'/run/arm.replace(':','--')/'campaign',
        initial_system=SystemSpec.from_dict(b['initial_system']),loss_spec=b['loss_spec'],seeds=b['seeds'],
        world_binding=b['world'],strategies=b['strategies'],mode='blackbox',seed=b['seed'],
        proposal_feedback='matched-loss',design_space=b['design_space'])


def build_plan(*,source,scientist,designer,backend,data_cache,seed_usage):
    from utopia.optimization.native_designer_roles_v38 import validate_designer_binding
    validate_designer_binding(designer,scientist_binding=scientist)
    if len(source)!=40 or any(c not in '0123456789abcdef' for c in source):
        raise ValueError('full clean source revision required')
    if any(not r['valid'] or r['errors'] or r['prior_matching_runs'] for r in seed_usage):
        raise ValueError('evaluation seed usage is nonempty or unknown in checked project roots')
    anchor=information_system(scientist['image_id'],seed=SEED)
    references={'open-seed':anchor.to_dict(),'legacy':legacy_world_system(seed=SEED).to_dict(),
        'reviewed-accept-all':selection_control(anchor,rule='accept-all').to_dict(),
        'no-review-accept-all':without_review(selection_control(anchor,rule='accept-all')).to_dict(),
        'no-review-reject-all':without_review(selection_control(anchor,rule='reject-all')).to_dict(),
        'information-disconnected':information_system(scientist['image_id'],condition='M0',seed=SEED).to_dict()}
    experiment={'protocol':PROTOCOL,'role':'purpose-conditioned-pre-scale-search'}
    world={**clone(scientist),'source_commit':source,'years':4,'experiment':experiment,
        'runtime_seed_binding':{'python_hash_seed_environment':os.environ.get('PYTHONHASHSEED'),
            'python_hash_probe':hash('scienceutopia.native-world.v1')},
        'classification':'actual-pre-scale-search-v1'}
    bindings={};assignments={};losses=objective_specs()
    for method in METHODS:
        for objective in OBJECTIVES:
            arm=objective+':'+method;strategy='uniform-numeric' if method=='random' else 'local-designer'
            domain='parameters' if method=='random' else method
            assignments[arm]={'method':method,'objective':objective,'strategy':strategy,'domain':domain}
            bindings[arm]={'initial_system':anchor.to_dict(),'loss_spec':losses[objective],
                'seeds':[SEED],'world':world,'strategies':{strategy:{'kind':method,'protocol':PROTOCOL}},
                'seed':42001,'design_space':information_design_space(anchor,domain,fixed_production=True)}
    order=list(bindings);schedule=[]
    for g in range(2):
        schedule.extend({'arm':arm,'generation':g} for arm in order[g:]+order[:g])
    return {'schema':SCHEMA+'.plan','source_commit':source,'runtime':runtime_binding(),
        'protocol':PROTOCOL,'protocol_sha256':file_sha256(ROOT/PROTOCOL),'scientist':clone(scientist),
        'designer':clone(designer),'backend':clone(backend),'data_cache':str(Path(data_cache).resolve()),
        'world':world,'experiment':experiment,'losses':losses,'objectives':list(OBJECTIVES),
        'methods':list(METHODS),'assignments':assignments,'campaign_bindings':{'run-00':bindings},
        'schedule':schedule,'generations':2,'reference_systems':references,
        'evaluation':{'seeds':list(EVALUATION_SEEDS),'years':4,'maximum_physical_worlds':36,
            'reference_labels':['open-seed','reviewed-accept-all','no-review-accept-all','no-review-reject-all'],
            'seed_usage':[r['content_sha256'] for r in seed_usage]},
        'budget':{'reference_worlds':6,'candidate_slots':16,'evaluation_worlds_upper_bound':36,
            'total_native_worlds_upper_bound':58,'readiness_numeric_sessions':2,
            'readiness_numeric_generation_POSTs_upper_bound':4,'readiness_editor_POSTs_upper_bound':40,
            'production_numeric_sessions':4,'production_numeric_POSTs_upper_bound':8,
            'production_editor_sessions':8,'production_editor_POSTs_upper_bound':128,
            'wall_seconds_per_readiness_or_proposal_session':1200,'HTTP_attempts_per_world':1024,
            'replace_failed_slots':False},
        'selection':{'criterion':'minimum assigned loss including common fresh initial',
            'ties':'retain every exact ID; first in frozen arrival order physically evaluated',
            'evaluation_feedback_to_search':False},
        'claims':{'fresh_initial_loss_exposed_before_first_proposal':False,
            'different_objective_winners_required':False,'method_superiority':False,
            'scientific_truth':False,'whole_world_autograd':False}}


def prepare(args):
    source=pinned_revision(ROOT)
    if args.output.exists():raise ValueError('fresh output destination required')
    old=checked(json.loads(args.operator_binding_plan.read_text()))
    usages=[usage_inventory(p,EVALUATION_SEEDS) for p in args.seed_usage_root]
    plan=build_plan(source=source,scientist=old['scientist'],designer=old['designer'],
        backend=backend_binding(old['designer']),data_cache=old['data_cache'],seed_usage=usages)
    args.output.mkdir(parents=True)
    for i,row in enumerate(usages):save(args.output/f'evaluation-seed-usage-{i}.json',{k:v for k,v in row.items() if k!='content_sha256'})
    save(args.output/'plan.json',plan)
    print(json.dumps({'prepared_source':source,'new_generation_calls':0,'native_worlds_upper_bound':58}),flush=True)


def require_plan(root):
    plan=checked(json.loads((root/'plan.json').read_text()))
    if (plan['source_commit']!=pinned_revision(ROOT) or plan['runtime']!=runtime_binding()
            or plan['protocol_sha256']!=file_sha256(ROOT/PROTOCOL)):
        raise ValueError('search source/protocol changed')
    return plan


def readiness(root,plan):
    from scripts.run_pre_scale_pilot_v1 import numeric_calibration
    # Same actual worlds/domain as production, not the old source certificate.
    numeric_plan={**clone(plan),'numeric_calibration_cases':list(OBJECTIVES),
        'systems':{'M1':plan['reference_systems']['open-seed']},
        'numeric_settings':{'max_calls':2,'wall_seconds':1200,'num_ctx':40960,'num_predict':8192,
            'temperature':.6,'think':False,'http_timeout_seconds':[10,900]}}
    def numeric_request(objective):
        c=campaign(root,plan,'run-00',objective+':parameters')
        return c._request([],c._strategy_initial(),1)
    numeric_calibration(root,numeric_plan,request_factory=numeric_request)
    if not checked(json.loads((root/'numeric-readiness/certificate.json').read_text()))['passed']:
        raise ValueError('numeric readiness failed; stop this source without replacement')
    c=campaign(root,plan,'run-00','throughput:code-and-graph')
    req=c._request([],c._strategy_initial(),1)
    count=len(planned_cases(req,'staged-v15',BOUNDED_AUTHORING))
    if count>40:raise ValueError('declared editor calibration call budget exceeded')
    result=bounded_editor(root/'editor-readiness',kind='calibration',request=req,provider=plan['designer'],
        source_commit=plan['source_commit'],maximum_posts=count,inference_lock=root/'inference.lock')
    if not result['passed']:raise ValueError('editor readiness failed; no production or replacement')


def observe(root,plan,identity,system,seed,role):
    root=Path(root)
    if (root/'started.json').exists():raise ValueError('world slot already consumed; no redispatch')
    save(root/'started.json',{'schema':SCHEMA+'.world-start','identity':identity,'seed':seed,
        'role':role,'system':system,'started_utc':datetime.now(timezone.utc).isoformat()})
    factory=LocalRoleBoundNativeFactory(root/'worlds',Path(plan['data_cache']),years=4,corpus_years=4,
        designer_provider=plan['designer'],record_wire=True,record_code=True,maximum_http_attempts=1024,
        experiment_binding=plan['experiment'],inference_lock=Path(plan['_output'])/'inference.lock')
    if factory.model_digest!=plan['scientist']['model_digest'] or factory.corpus_sha256!=plan['scientist']['corpus_sha256']:
        raise ValueError('actual researcher/corpus differs from plan')
    observation=evaluate_native_suggestion(Suggestion(identity,system,0,role),seeds=[seed],
        simulation_factory=factory,loss_spec=plan['losses']['throughput']).to_dict()
    save(root/'observation.json',observation)
    save(root/'cross-scores.json',{k:evaluate_loss(v,observation['metadata']['measurements']) for k,v in plan['losses'].items()})
    return observation


def progress(root,plan,stage,active=None):
    rows=[]
    for arm in plan['assignments']:
        c=campaign(root,plan,'run-00',arm)
        for g,r in enumerate(c.state['records']):
            o=r['observations'][0] if r['observations'] else None
            rows.append({'arm':arm,'generation':g,'status':'generation-failure' if r['generation_error'] else o['status'] if o else 'unknown',
                'loss':o['loss'] if o else None})
    payload={'schema':SCHEMA+'.progress','stage':stage,'active':active,'search_slots':rows,
        'reference_observations':len(list((root/'references').glob('*/observation.json'))),
        'evaluation_observations':len(list((root/'evaluation').glob('*/observation.json')))}
    write_json_atomic(root/'progress.json',payload,sort_keys=True,allow_nan=False)
    print(json.dumps({k:v for k,v in payload.items() if k!='search_slots'}),flush=True)


def search(root,plan):
    for name,system in plan['reference_systems'].items():
        o=observe(root/'references'/name,plan,'reference-'+name,system,SEED,'developer-reference')
        progress(root,plan,'references',name)
        if o['status']!='complete':raise ValueError('reference failed; stop and preserve this source')
    for slot in plan['schedule']:
        arm=slot['arm'];g=slot['generation'];c=campaign(root,plan,'run-00',arm)
        if c.state['pending'] is not None or len(c.state['records'])!=g:
            raise ValueError('no pending proposal retry or failed-slot refill')
        directory=root/'search'/'run-00'/arm.replace(':','--')
        method=plan['assignments'][arm]['method']
        if method=='random':author=random_parameter_definition
        elif method=='parameters':
            load_local_role(directory/f'designer-load-{g}.json',provider=plan['designer'],role='designer',purpose='pre-scale-numeric-search')
            author=NumericDesigner(directory/'authoring',provider=plan['designer'],backend=plan['backend'],
                certificate=root/'numeric-readiness/certificate.json',inference_lock=root/'inference.lock')
        else:
            author=BoundedStagedDesigner(directory/'authoring',provider=plan['designer'],source_commit=plan['source_commit'],
                certificate=root/'editor-readiness/calibration/certificate.json',inference_lock=root/'inference.lock')
        factory=LocalRoleBoundNativeFactory(directory/'worlds',Path(plan['data_cache']),years=4,corpus_years=4,
            designer_provider=plan['designer'],record_wire=True,record_code=True,maximum_http_attempts=1024,
            experiment_binding=plan['experiment'],inference_lock=root/'inference.lock')
        c.advance(simulation_factory=factory,generators={plan['assignments'][arm]['strategy']:author},count=1)
        progress(root,plan,'search',arm+':g'+str(g))
    selection=selection_payload(root,plan,frozen_utc=datetime.now(timezone.utc).isoformat(),campaign_loader=campaign)
    save(root/'selection.json',{k:v for k,v in selection.items() if k!='content_sha256'})
    progress(root,plan,'selection-fixed')


def evaluation_jobs(plan,selection):
    checked(selection)
    if selection['plan_sha256']!=plan['content_sha256']:raise ValueError('selection plan differs')
    policies={}
    labels={**{'reference:'+k:plan['reference_systems'][k] for k in plan['evaluation']['reference_labels']},
        **{'selected:'+k:v['system'] for k,v in selection['selected'].items()}}
    for label,system in labels.items():
        if system is None:continue
        identity=policy_identity(system)
        policies.setdefault(identity,{'system':clone(system),'labels':[]})['labels'].append(label)
    jobs=[]
    for identity,entry in policies.items():
        for seed in plan['evaluation']['seeds']:
            system=clone(entry['system']);system['initial_state']['seed']=seed
            if policy_identity(system)!=identity:raise ValueError('evaluation changes policy')
            jobs.append({'identity':'evaluation-'+str(len(jobs)).zfill(3),'policy_sha256':identity,
                'system':system,'labels':entry['labels'],'seed':seed})
    if len(jobs)>plan['evaluation']['maximum_physical_worlds']:raise ValueError('evaluation budget exceeded')
    return jobs


def evaluate(root,plan):
    selection=checked(json.loads((root/'selection.json').read_text()))
    jobs=evaluation_jobs(plan,selection)
    save(root/'evaluation-plan.json',{'schema':SCHEMA+'.evaluation-plan',
        'selection_sha256':selection['content_sha256'],'jobs':jobs})
    for job in jobs:
        observe(root/'evaluation'/job['identity'],plan,job['identity'],job['system'],job['seed'],'selection-fixed-evaluation')
        progress(root,plan,'evaluation',job['identity'])
    save(root/'complete.json',{'schema':SCHEMA+'.complete','plan_sha256':plan['content_sha256'],
        'selection_sha256':selection['content_sha256'],'evaluation_physical_worlds':len(jobs),
        'closed_utc':datetime.now(timezone.utc).isoformat()})
    progress(root,plan,'closed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','readiness','search','evaluation'])
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--operator-binding-plan',type=Path)
    parser.add_argument('--seed-usage-root',type=Path,action='append',default=[])
    args=parser.parse_args();args.output=args.output.resolve()
    if args.stage=='prepare':
        if not args.seed_usage_root:raise ValueError('explicit project raw roots required for unused-seed check')
        prepare(args);return
    plan=require_plan(args.output);plan['_output']=str(args.output)
    with (args.output/'writer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        start={'schema':SCHEMA+'.stage-start','stage':args.stage,'pid':os.getpid(),
            'plan_sha256':plan['content_sha256'],'started_utc':datetime.now(timezone.utc).isoformat()}
        save(args.output/(args.stage+'.started.json'),start)
        end=clone(start)
        try:{'readiness':readiness,'search':search,'evaluation':evaluate}[args.stage](args.output,plan)
        except BaseException as error:
            end.update(status='stopped',error_type=type(error).__name__,error=str(error));raise
        else:end.update(status='closed')
        finally:
            end['ended_utc']=datetime.now(timezone.utc).isoformat()
            save(args.output/(args.stage+'.ended.json'),end)


if __name__=='__main__':main()
