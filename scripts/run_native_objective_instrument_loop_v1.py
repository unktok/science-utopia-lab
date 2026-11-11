"""Prospective count/content native optimization, finite slots and no fallback."""
import argparse
from datetime import datetime,timezone
import fcntl
import json
import os
from pathlib import Path
from types import SimpleNamespace
import time

from scripts.run_pre_scale_search_v1 import require_environment,ENVIRONMENT
from scripts.run_native_institution_loop_v1 import readiness
from scripts.native_benchmark_seed_usage import usage_inventory
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.common_content_observer import CommonContentObserver,LocalObserverBackend,make_contract
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_benchmark_controls import objective_specs,selection_control,without_review
from utopia.optimization.native_bounded_staged_designer import execute
from utopia.optimization.native_causal_design import OPTION,PRESENTATION
from utopia.optimization.native_development_references import build_context
from utopia.optimization.native_designer_preflight import runtime_binding,backend_binding
from utopia.optimization.native_designer_roles_v38 import validate_designer_binding
from utopia.optimization.native_fixed_production_domain import allow_review_routing
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory
from utopia.optimization.native_numeric_designer import checked,save
from utopia.optimization.native_post_edit_feedback_v1 import NativePostEditFeedback,OPTION as TEST_OPTION
from utopia.optimization.native_review_routing_controls import routed_control
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone,digest
from utopia.system.native_information_institution import information_system,information_design_space
from utopia.system.native_liquidity_controls import liquidity_control
from utopia.utils.data_utils import file_sha256,write_json_atomic

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='scienceutopia.native-objective-instrument-loop.v1'
PROTOCOL='research/protocols/campaigns/native-objective-instrument-loop-v1.md'
BANK_MANIFEST='research/data/native-resource-component-fixtures-v2/summary.json'
CONTENT_LOSS='research/objectives/losses/native-common-content-utility-v1.json'
SEED=61001
EVALUATION_SEEDS=(64101,64107,64113)
OBJECTIVES=('throughput','content-utility')


def read(path):return checked(json.loads(Path(path).read_text()))
def utc():return datetime.now(timezone.utc).isoformat()


def feedback_for(bank,source,image):
    def forbidden(*a):raise AssertionError('preparation cannot execute component code')
    return NativePostEditFeedback(bank,executor=SimpleNamespace(image_id=image,timeout=15.,execute=forbidden),
        source_commit=source,maximum_probes=64)


def build_plan(operator,*,source,backend,observer_backend,bank,bank_file_hash,support,seed_usage):
    validate_designer_binding(operator['designer'],scientist_binding=operator['scientist'])
    if len(source)!=40 or any(c not in '0123456789abcdef' for c in source):raise ValueError('full clean source required')
    if not seed_usage or any(not r['valid'] or r['errors'] or r['prior_matching_runs']
            or r['seeds']!=list(EVALUATION_SEEDS) for r in seed_usage):raise ValueError('explicit unused evaluation world seeds required')
    manifest=read(ROOT/BANK_MANIFEST);checked(bank)
    if bank_file_hash!=manifest['bank_file_sha256'] or bank['content_sha256']!=manifest['bank_content_sha256']:
        raise ValueError('exact actual resource component bank required')
    image=operator['scientist']['image_id']
    if any(r['receipt']['image_id']!=image for r in bank['records']):raise ValueError('resource bank image differs')
    base=selection_control(information_system(image,seed=SEED),rule='accept-all')
    anchor=liquidity_control(base,image)
    references={'reviewed-all-connected':anchor.to_dict(),
        'one-reviewer-all-connected':routed_control(anchor,reviewers_per_paper=1,snapshot_phase=85,producer_phase=87).to_dict(),
        'no-review-all-connected':without_review(anchor).to_dict(),
        'no-review-reject-all-connected':without_review(selection_control(anchor,rule='reject-all')).to_dict(),
        'reviewed-all-disconnected':liquidity_control(base,image,connected=False).to_dict()}
    observer=make_contract(source_commit=source,provider={k:operator['scientist'][k] for k in ('model','model_digest')},
        backend=observer_backend,maximum_posts=3000,critics=3)
    post_edit=feedback_for(bank,source,image).contract
    experiment={'protocol':PROTOCOL,'role':'objective-conditioned-native-content-loop'}
    world={**clone(operator['scientist']),'source_commit':source,'years':4,'experiment':experiment,
        'runtime_seed_binding':clone(operator['world']['runtime_seed_binding']),
        'world_conditions':{'schema':'scienceutopia.native-world-conditions.v1','initial_funding':30,
            'population_resource_profile':'balanced_two_band','log_resource_ledger':True},
        'measurement_adapter_contract':observer,'classification':'actual-native-objective-instrument-loop-v1'}
    return {'schema':SCHEMA+'.plan','source_commit':source,'runtime':runtime_binding(),
        'protocol':PROTOCOL,'protocol_sha256':file_sha256(ROOT/PROTOCOL),'launch_environment':clone(ENVIRONMENT),
        'scientist':clone(operator['scientist']),'designer':clone(operator['designer']),'backend':clone(backend),
        'data_cache':operator['data_cache'],'world':world,'experiment':experiment,'observer_contract':observer,
        'losses':{'throughput':objective_specs()['throughput'],'content-utility':json.loads((ROOT/CONTENT_LOSS).read_text())},
        'reference_systems':references,'reference_order':list(references),'initial_system':anchor.to_dict(),
        'design_space':allow_review_routing(anchor,information_design_space(anchor,'code-and-graph',fixed_production=True)),
        'strategies':{'local-designer':{'kind':'code-and-graph','protocol':PROTOCOL,
            OPTION:True,PRESENTATION:'inline',TEST_OPTION:post_edit}},
        'component_bank':clone(bank),'component_bank_file_sha256':bank_file_hash,
        'fixture_manifest_file_sha256':file_sha256(ROOT/BANK_MANIFEST),'post_edit_contract':post_edit,
        'component_support':clone(support),'objectives':list(OBJECTIVES),'generations':4,'optimizer_seed':65001,
        'schedule':[{'objective':o,'generation':g} for g in range(4) for o in (OBJECTIVES if g%2==0 else OBJECTIVES[::-1])],
        'proposal_feedback':'loss','reference_parent_policy':'best measured developer/own loss; no automatic final baseline fallback',
        'evaluation':{'seeds':list(EVALUATION_SEEDS),'seed_usage':[r['content_sha256'] for r in seed_usage],
            'native_worlds_upper_bound':21,'separate_frozen_evaluation_required':True},
        'budget':{'reference_worlds':5,'candidate_slots':8,'development_native_worlds_upper_bound':13,
            'scientist_HTTP_attempts_per_world':1024,'world_wall_seconds':7200,'observer_POSTs_upper_bound':3000,
            'readiness_sessions':8,'readiness_POSTs_per_session':40,'readiness_seconds':1200,
            'proposal_POSTs_per_session':16,'proposal_seconds':1800,'component_attempts_per_proposal':64,
            'replace_failed_slots':False},'development_seed_reused':True,'publication_ready':False}


def require_plan(root):
    p=read(root/'plan.json');usages=[read(root/f'evaluation-seed-usage-{i:02d}.json') for i in range(len(p['evaluation']['seed_usage']))]
    if p['source_commit']!=pinned_revision(ROOT) or p['runtime']!=runtime_binding():raise ValueError('exact objective-loop source/runtime required')
    expected=build_plan(p,source=p['source_commit'],backend=p['backend'],observer_backend=p['observer_contract']['backend'],
        bank=p['component_bank'],bank_file_hash=p['component_bank_file_sha256'],support=p['component_support'],seed_usage=usages)
    if expected!={k:v for k,v in p.items() if k!='content_sha256'}:raise ValueError('objective-loop plan reconstruction differs')
    support=Path(p['component_support']['directory']);summary=read(support/'summary.json');support_plan=read(support/'plan.json')
    if (file_sha256(support/'summary.json')!=p['component_support']['summary_file_sha256']
            or file_sha256(support/'plan.json')!=p['component_support']['plan_file_sha256']
            or summary['status']!='closed' or len(summary['observations'])!=12
            or not all(o['original_result_matches'] for o in summary['observations'])
            or support_plan['bank_file_sha256']!=p['component_bank_file_sha256']):
        raise ValueError('original twelve-call component support differs')
    return p


def prepare(args):
    require_environment();source=pinned_revision(ROOT)
    if args.output.exists():raise ValueError('fresh objective experiment required')
    operator=read(args.operator_plan);bank=read(args.bank)
    if not Path(operator['data_cache']).is_dir() or not args.seed_usage_root:raise ValueError('existing data and explicit seed-usage roots required')
    support={'directory':str(args.component_support.resolve()),'summary_file_sha256':file_sha256(args.component_support/'summary.json'),
        'plan_file_sha256':file_sha256(args.component_support/'plan.json')}
    usages=[usage_inventory(path,EVALUATION_SEEDS) for path in args.seed_usage_root]
    p=build_plan(operator,source=source,backend=backend_binding(operator['designer']),
        observer_backend=backend_binding({k:operator['scientist'][k] for k in ('model','model_digest')}),
        bank=bank,bank_file_hash=file_sha256(args.bank),support=support,seed_usage=usages)
    args.output.mkdir(parents=True)
    for i,u in enumerate(usages):save(args.output/f'evaluation-seed-usage-{i:02d}.json',{k:v for k,v in u.items() if k!='content_sha256'})
    save(args.output/'plan.json',p);require_plan(args.output)
    print(json.dumps({'prepared_source':source,'development_native_worlds_upper_bound':13,'new_model_calls':0}),flush=True)


def factory_for(directory,p,root):
    factory=LocalRoleBoundNativeFactory(directory,Path(p['data_cache']),years=4,corpus_years=4,
        designer_provider=p['designer'],record_wire=True,record_code=True,maximum_http_attempts=1024,
        experiment_binding=p['experiment'],inference_lock=root/'inference.lock',world_conditions=p['world']['world_conditions'])
    if factory.model_digest!=p['scientist']['model_digest'] or factory.corpus_sha256!=p['scientist']['corpus_sha256']:
        raise ValueError('actual researcher/corpus differs from plan')
    def construct(spec,seed,run_id):
        sim=factory(spec,seed,run_id)
        if sim.llm.response_cache.stop is not sim.portable_stop:raise ValueError('native safe-point binding differs')
        sim.portable_stop.deadline=time.monotonic()+p['budget']['world_wall_seconds'];return sim
    return construct


def measure_with(observer,contract):
    def measure(sim,base):
        return {**observer.measure(sim,base),'measurement_adapter_contract_sha256':digest(contract)}
    return measure


def observe(root,p,label,observer):
    directory=root/'references'/label;identity='reference-'+label
    if (directory/'started.json').exists():raise ValueError('consumed reference; no redispatch')
    suggestion=Suggestion(identity,p['reference_systems'][label],0,'developer-reference')
    save(directory/'started.json',{'suggestion':suggestion.to_dict(),'seed':SEED,'started_utc':utc()})
    result=evaluate_native_suggestion(suggestion,seeds=[SEED],simulation_factory=factory_for(directory/'worlds',p,root),
        loss_spec=p['losses']['throughput'],measurement_adapter=measure_with(observer,p['observer_contract'])).to_dict()
    save(directory/'observation.json',result)
    scores={k:evaluate_loss(v,result['metadata']['measurements']) for k,v in p['losses'].items()}
    save(directory/'cross-scores.json',scores)
    if result['status']!='complete' or any(v['status']!='complete' for v in scores.values()):
        raise ValueError('complete common developer reference required; no replacement')
    return {'suggestion':suggestion.to_dict(),'observation':result}


def campaign(root,p,objective,context):
    return NativeAdaptiveDesignCampaign(root/'search'/objective/'campaign',initial_system=SystemSpec.from_dict(p['initial_system']),
        loss_spec=p['losses'][objective],seeds=[SEED],world_binding=p['world'],strategies=p['strategies'],mode='blackbox',
        seed=p['optimizer_seed'],design_space=p['design_space'],development_references=context)


def selection(root,p,context,*,frozen_utc=None):
    selected={}
    for objective in p['objectives']:
        c=campaign(root,p,objective,context)
        if c.state['pending'] is not None or len(c.state['records'])!=4:raise ValueError('eight terminal proposal slots required')
        pool=[o for r in c.state['records'] for o in r['observations'] if o and o['status']=='complete' and o['loss'] is not None]
        best=min((o['loss'] for o in pool),default=None);ties=[o for o in pool if o['loss']==best]
        selected[objective]={'loss':best,'all_tied_ids':[o['suggestion_id'] for o in ties],
            'selected_id':ties[0]['suggestion_id'] if ties else None,'system':clone(ties[0]['candidate']) if ties else None,
            'completed_submissions':len(pool)}
    return {'schema':SCHEMA+'.selection','plan_sha256':p['content_sha256'],'selected':selected,'baseline_fallback':False,
        'frozen_utc':utc() if frozen_utc is None else frozen_utc,'held_out_evaluation':False}


def progress(root,stage,active=None):
    write_json_atomic(root/'progress.json',{'stage':stage,'active':active,'observed_utc':utc()},sort_keys=True)
    print(json.dumps({'stage':stage,'active':active}),flush=True)


def run(root):
    require_environment();p=require_plan(root)
    with (root/'writer.lock').open('a') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'started.json').exists():raise ValueError('consumed objective study; no redispatch')
        save(root/'started.json',{'schema':SCHEMA+'.start','plan_sha256':p['content_sha256'],'started_utc':utc(),'pid':os.getpid()})
        stage='initializing';status='stopped';failure={};completed=0
        try:
            observer=CommonContentObserver(root/'observer',p['observer_contract'],backend=LocalObserverBackend(inference_lock=root/'inference.lock'))
            pairs=[]
            for label in p['reference_order']:
                stage='references';progress(root,stage,label);pairs.append(observe(root,p,label,observer));completed+=1;require_plan(root)
            context=build_context(pairs,world=p['world'],seeds=[SEED],loss_spec=p['losses']['throughput'])
            save(root/'developer-reference-context.json',{k:v for k,v in context.items() if k!='content_sha256'})
            for slot in p['schedule']:
                objective,g=slot['objective'],slot['generation'];c=campaign(root,p,objective,context)
                if c.state['pending'] is not None or len(c.state['records'])!=g:raise ValueError('consumed/pending proposal cannot be redispatched')
                request=c._request(c.state['records'],c._validate(),1);directory=root/'search'/objective
                stage='readiness';progress(root,stage,objective+':g'+str(g))
                cert=readiness(root,p,request=request,numeric=False,target=directory/f'readiness-{g}')
                def generate(req):
                    return execute(directory/'authoring'/('generation-'+digest(req)),kind='proposal',request=req,
                        provider=p['designer'],source_commit=p['source_commit'],certificate=cert,seconds=1800,
                        inference_lock=root/'inference.lock',post_edit_bank=p['component_bank'])
                stage='optimization';progress(root,stage,objective+':g'+str(g))
                c.advance(simulation_factory=factory_for(directory/'worlds',p,root),generators={'local-designer':generate},count=1,
                    measurement_adapter=observer.measure,measurement_contract=p['observer_contract'])
                require_plan(root)
            save(root/'selection.json',selection(root,p,context));audit=observer.audit()
            save(root/'observer-audit.json',{k:v for k,v in audit.items() if k!='content_sha256'})
            if read(root/'observer-audit.json')!=audit:raise ValueError('retained public observer audit differs')
            status='closed';stage='closed';progress(root,stage)
        except BaseException as error:
            failure={'error_type':type(error).__name__,'error':str(error)};raise
        finally:
            save(root/'terminal.json',{'schema':SCHEMA+'.terminal','status':status,'stage':stage,'ended_utc':utc(),
                'complete_references':completed,'held_out_evaluation':False,'publication_ready':False,**failure})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=('prepare','run'))
    p.add_argument('--output',type=Path,required=True)
    for name in ('operator-plan','bank','component-support'):p.add_argument('--'+name,type=Path)
    p.add_argument('--seed-usage-root',type=Path,action='append');a=p.parse_args();a.output=a.output.resolve()
    if a.stage=='prepare':
        if a.operator_plan is None or a.bank is None or a.component_support is None:p.error('explicit existing inputs required')
        prepare(a)
    else:run(a.output)


if __name__=='__main__':main()
