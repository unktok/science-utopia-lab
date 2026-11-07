#!/usr/bin/env python3
"""Finite V2 study: references, matched search, frozen selection, evaluation."""
import argparse
from datetime import datetime,timezone
import fcntl
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from scripts import native_design_benchmark_plan as spec
from scripts.run_native_benchmark_controls import save_new
from scripts.run_native_warmstart_v45 import campaign_from_binding
from scripts.native_benchmark_seed_usage import usage_inventory
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory,record_loaded_context
from utopia.optimization.native_scientist_load_v38 import load_local_role
from utopia.optimization.native_designer_preflight import (
    EXECUTION_SCOPE,run_calibration,require_certificate,planned_cases,backend_binding)
from utopia.optimization.native_designer_roles_v38 import make_local_role_bound_generator
from utopia.optimization.native_design_space import random_parameter_definition
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system.design_patch import clone,digest
from utopia.utils.data_utils import write_json_atomic


def campaign(root,plan,run,arm):
    return campaign_from_binding(Path(root)/'search'/run/'arms'/arm.replace(':','--')/'campaign',
        plan['campaign_bindings'][run][arm])


def evaluate(root,plan,*,identity,system,seed,years,role,data_cache,inference_lock):
    directory=Path(root)
    save_new(directory/'started.json',{'identity':identity,'seed':seed,'years':years,
        'candidate_sha256':digest(system),'role':role,'started_utc':datetime.now(timezone.utc).isoformat()})
    factory=LocalRoleBoundNativeFactory(directory/'worlds',data_cache,years=years,corpus_years=4,
        designer_provider=plan['designer'],record_wire=True,record_code=True,
        maximum_http_attempts=512 if years==2 else 1024,experiment_binding=plan['experiment'],
        inference_lock=inference_lock)
    o=evaluate_native_suggestion(Suggestion(identity,system,0,role),seeds=[seed],
        simulation_factory=factory,loss_spec=plan['losses']['throughput']).to_dict()
    save_new(directory/'observation.json',o)
    save_new(directory/'cross-scores.json',{k:evaluate_loss(v,o['metadata']['measurements']) for k,v in plan['losses'].items()})
    return o


def calibration(root,plan,run):
    directory=Path(root)/'search'/run
    # The largest freedom uses the same literal interface; capacity/domain
    # regressions for all other profiles precede dispatch separately.
    c=campaign(root,plan,run,'throughput:code-and-graph')
    request=c._request([],c._strategy_initial(),1);settings=plan['designer_settings']
    if len(planned_cases(request,'staged-v15',settings['conversation_profile']))>40:
        raise ValueError('predeclared calibration budget exceeded')
    purpose='before-design-study-calibration:'+run
    load_local_role(directory/'calibration-load.json',provider=plan['designer'],role='designer',purpose=purpose)
    record_loaded_context(directory/'calibration-context.json',expected={'designer':plan['designer']},purpose=purpose)
    cert=run_calibration(directory/'preflight',request=request,provider=plan['designer'],
        source_commit=plan['source_commit'],scope=EXECUTION_SCOPE,conversation_profile=settings['conversation_profile'])
    if not cert['all_controls_passed']:raise ValueError('finite calibration failed; no replacement or production dispatch')
    return directory/'preflight/certificate.json'


def search_run(root,plan,run,certificate,*,data_cache):
    settings=plan['designer_settings']
    for slot in plan['schedules'][run]:
        arm,g=slot['arm'],slot['generation'];c=campaign(root,plan,run,arm)
        if c.state['pending'] is not None or len(c.state['records'])!=g:
            raise ValueError('no hidden pending retry, refill or redispatch')
        directory=Path(root)/'search'/run/'arms'/arm.replace(':','--')
        method=plan['assignments'][arm]['method']
        if method=='random':author=random_parameter_definition
        else:
            require_certificate(certificate,plan['designer'],protocol='staged-v15',scope=EXECUTION_SCOPE,
                conversation_profile=settings['conversation_profile'])
            purpose='before-design-study-proposal:'+run+':'+arm+':g'+str(g)
            load_local_role(directory/f'designer-load-{g}.json',provider=plan['designer'],role='designer',purpose=purpose)
            record_loaded_context(directory/f'designer-context-{g}.json',expected={'designer':plan['designer']},purpose=purpose)
            author=make_local_role_bound_generator(directory/'authoring',image_id=plan['scientist']['image_id'],
                provider_binding=plan['designer'],max_steps=settings['max_steps'],max_tokens=settings['max_tokens'],
                inference_lock=Path(root)/'inference.lock',preflight_certificate=certificate,
                readiness_scope=EXECUTION_SCOPE,conversation_profile=settings['conversation_profile'])
        factory=LocalRoleBoundNativeFactory(directory/'worlds',data_cache,years=2,corpus_years=4,
            designer_provider=plan['designer'],record_wire=True,record_code=True,maximum_http_attempts=512,
            experiment_binding=plan['experiment'],inference_lock=Path(root)/'inference.lock')
        c.advance(simulation_factory=factory,generators={plan['assignments'][arm]['strategy']:author},count=1)
        progress(root,plan,stage='search',active=run+':'+arm+':g'+str(g))


def progress(root,plan,*,stage,active=None):
    rows=[]
    for run,bindings in plan['campaign_bindings'].items():
        for arm in bindings:
            c=campaign(root,plan,run,arm)
            for g,r in enumerate(c.state['records']):
                o=r['observations'][0] if r['observations'] else None
                rows.append({'run':run,'arm':arm,'generation':g,
                    'status':'generation-failure' if r['generation_error'] else o['status'] if o else 'unknown',
                    'loss':o['loss'] if o else None})
    result={'schema':spec.SCHEMA+'.progress','plan_sha256':plan['content_sha256'],'stage':stage,
        'active':active,'consumed_search_slots':len(rows),'rows':rows,
        'consumed_reference_slots':len(list((Path(root)/'references').glob('*/observation.json'))),
        'consumed_evaluation_slots':len(list((Path(root)/'evaluation').glob('*/observation.json')))}
    result['content_sha256']=digest(result)
    write_json_atomic(Path(root)/'progress.json',result,sort_keys=True,allow_nan=False)
    print(json.dumps({k:result[k] for k in ['stage','active','consumed_reference_slots',
        'consumed_search_slots','consumed_evaluation_slots']}),flush=True)
    return result


def selection_payload(root,plan,*,frozen_utc,campaign_loader=None):
    root=Path(root);rows=[]
    loader=campaign if campaign_loader is None else campaign_loader
    for name,system in plan['reference_systems'].items():
        o=json.loads((root/'references'/name/'observation.json').read_text())
        rows.append({'row_id':'reference:'+name,'arm':None,'system':system,'status':o['status'],
            'cross_scores':{k:evaluate_loss(loss,o['metadata']['measurements'])['loss']
                if o['status']=='complete' else None for k,loss in plan['losses'].items()}})
    for run,bindings in plan['campaign_bindings'].items():
        for arm in bindings:
            c=loader(root,plan,run,arm)
            if c.state['pending'] or len(c.state['records'])!=plan['generations']:
                raise ValueError('selection cannot precede every declared search slot')
            for g,r in enumerate(c.state['records']):
                o=r['observations'][0] if r['observations'] else None
                rows.append({'row_id':run+':'+arm+':g'+str(g),'arm':arm,
                    'system':o['candidate'] if o else None,'status':o['status'] if o else 'generation-failure',
                    'cross_scores':{k:evaluate_loss(loss,o['metadata']['measurements'])['loss']
                        if o and o['status']=='complete' else None for k,loss in plan['losses'].items()}})
    def choose(pool,objective):
        valid=[r for r in pool if r['status']=='complete' and r['cross_scores'][objective] is not None]
        value=min((r['cross_scores'][objective] for r in valid),default=None)
        tied=[r for r in valid if r['cross_scores'][objective]==value]
        return {'loss':value,'all_tied_row_ids':[r['row_id'] for r in tied],
            'selected_row_id':tied[0]['row_id'] if tied else None,
            'system':clone(tied[0]['system']) if tied else None,
            'policy_sha256':spec.policy_identity(tied[0]['system']) if tied else None}
    selected={arm:choose([r for r in rows if r['arm']==arm or r['row_id']=='reference:open-seed'],
        assignment['objective']) for arm,assignment in plan['assignments'].items()}
    result={'schema':spec.SCHEMA+'.selection','plan_sha256':plan['content_sha256'],
        'selected':selected,'pooled':{k:choose(rows,k) for k in plan['objectives']},
        'all_rows':rows,'reference_systems':plan['reference_systems'],
        'frozen_utc':frozen_utc}
    result['content_sha256']=digest(result)
    return result


def freeze_selection(root,plan):
    result=selection_payload(root,plan,frozen_utc=datetime.now(timezone.utc).isoformat())
    save_new(Path(root)/'selection.json',result)
    return result


def evaluation_jobs(plan,selection):
    if selection['plan_sha256']!=plan['content_sha256'] or selection['content_sha256']!=digest(
            {k:v for k,v in selection.items() if k!='content_sha256'}):
        raise ValueError('evaluation requires the exact frozen selection')
    policies={}
    labels={**{'reference:'+k:v for k,v in plan['reference_systems'].items()},
        **{'selected:'+k:v['system'] for k,v in selection['selected'].items()}}
    for label,system in labels.items():
        if system is None:continue
        identity=spec.policy_identity(system)
        policies.setdefault(identity,{'system':clone(system),'labels':[]})['labels'].append(label)
    conditions=[{'seed':s,'years':y} for s in plan['evaluation']['seeds'] for y in plan['evaluation']['years']]
    conditions+=plan['evaluation']['extended'];jobs=[]
    for identity,p in policies.items():
        for condition in conditions:
            jobs.append({'job_id':f'evaluation-{len(jobs):04d}','policy_sha256':identity,
                'labels':p['labels'],'system':spec.evaluation_design(p['system'],condition['seed']).to_dict(),**condition})
    if len(jobs)>plan['evaluation']['maximum_physical_worlds']:
        raise ValueError('evaluation budget exceeded')
    return jobs


def prepare(args):
    from utopia.system.code_mechanisms import DockerCodeExecutor
    source=pinned_revision(ROOT)
    config=json.loads(args.designer_provider_config.read_text())
    if set(config)!={'provider_binding'}:raise ValueError('exact approved operator binding required')
    designer=config['provider_binding']
    factory=LocalRoleBoundNativeFactory(args.output/'binding-only-no-worlds',args.data_cache,
        years=2,corpus_years=4,designer_provider=designer)
    scientist={k:clone(getattr(factory,k)) for k in ('model','model_digest','corpus_sha256','corpus_years','dataset_identity')}
    scientist['image_id']=DockerCodeExecutor().image_id
    usage_path=args.output/'evaluation-seed-usage.json'
    if usage_path.exists():
        usage=json.loads(usage_path.read_text())
    else:
        usage=usage_inventory(args.output.parent,spec.EVALUATION_SEEDS)
        save_new(usage_path,usage)
    if (usage['content_sha256']!=digest({k:v for k,v in usage.items() if k!='content_sha256'})
            or usage['valid'] is not True or usage['seeds']!=list(spec.EVALUATION_SEEDS)
            or usage['errors'] or usage['prior_matching_runs']):
        raise ValueError('evaluation seeds are previously used or unknown in the checked project journals')
    plan=spec.build_plan(source=source,scientist=scientist,designer=designer,
        runtime_seed=factory.runtime_seed_binding,backend=backend_binding(designer),seed_usage_sha256=usage['content_sha256'])
    if (args.output/'plan.json').exists():
        if json.loads((args.output/'plan.json').read_text())!=plan:raise ValueError('frozen study plan changed')
    else:save_new(args.output/'plan.json',plan)
    for run,bindings in plan['campaign_bindings'].items():
        for arm in bindings:campaign(args.output,plan,run,arm)
    return plan


def execute(args):
    plan=prepare(args)
    if args.action=='prepare':return 0
    first_run=next(iter(plan['campaign_bindings']))
    first_certificate=calibration(args.output,plan,first_run)
    for name,system in plan['reference_systems'].items():
        evaluate(args.output/'references'/name,plan,identity='reference-'+name,
            system=system,seed=42,years=2,role='developer-reference',data_cache=args.data_cache,
            inference_lock=args.output/'inference.lock')
        progress(args.output,plan,stage='references',active=name)
    for run in plan['campaign_bindings']:
        certificate=first_certificate if run==first_run else calibration(args.output,plan,run)
        search_run(args.output,plan,run,certificate,data_cache=args.data_cache)
    selection=freeze_selection(args.output,plan)
    jobs=evaluation_jobs(plan,selection)
    save_new(args.output/'evaluation-plan.json',{'schema':spec.SCHEMA+'.evaluation-plan',
        'selection_sha256':selection['content_sha256'],'jobs':jobs})
    for job in jobs:
        evaluate(args.output/'evaluation'/job['job_id'],plan,identity=job['job_id'],system=job['system'],
            seed=job['seed'],years=job['years'],role='selection-fixed-evaluation',data_cache=args.data_cache,
            inference_lock=args.output/'inference.lock')
        progress(args.output,plan,stage='evaluation',active=job['job_id'])
    progress(args.output,plan,stage='closed',active=None)
    return 0


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','all'])
    p.add_argument('--execute-authorized',action='store_true',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--data-cache',type=Path,required=True)
    p.add_argument('--designer-provider-config',type=Path,required=True)
    a=p.parse_args(argv);a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=True)
    with (a.output/'study.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        prefix='writer' if a.action=='all' else 'prepare'
        start={'schema':spec.SCHEMA+'.writer','source_commit':pinned_revision(ROOT),'action':a.action,
            'pid':os.getpid(),'status':'started','started_utc':datetime.now(timezone.utc).isoformat(),
            'environment':{k:os.environ.get(k) for k in ['CUDA_VISIBLE_DEVICES','PYTHONHASHSEED','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE']}}
        save_new(a.output/(prefix+'.started.json'),start);end=clone(start)
        try:result=execute(a)
        except BaseException as error:
            end.update(status='aborted',error_type=type(error).__name__,error=str(error));raise
        else:end.update(status='exited',exit_code=result);return result
        finally:
            end['ended_utc']=datetime.now(timezone.utc).isoformat();save_new(a.output/(prefix+'.ended.json'),end)


if __name__=='__main__':raise SystemExit(main())
