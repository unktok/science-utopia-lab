"""Four prospective original-world controls, no designer or policy selection."""
import argparse
from datetime import datetime,timezone
import fcntl
import json
import os
from pathlib import Path
import time

from scripts.run_pre_scale_search_v1 import require_environment
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_benchmark_controls import objective_specs,selection_control
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory
from utopia.optimization.native_numeric_designer import checked,save
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system.design_patch import clone,digest
from utopia.system.native_information_institution import information_system
from utopia.system.native_liquidity_controls import liquidity_control
from utopia.utils.data_utils import file_sha256,write_json_atomic

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='scienceutopia.native-liquidity-support.v1'
PROTOCOL='research/protocols/campaigns/native-liquidity-support-v1.md'
SEED=61001


def read(path):return checked(json.loads(Path(path).read_text()))
def utc():return datetime.now(timezone.utc).isoformat()


def build_plan(operator,*,source,preceding):
    systems={};jobs=[]
    anchor=selection_control(information_system(operator['scientist']['image_id'],seed=SEED),rule='accept-all')
    for connected in (False,True):
        systems['connected' if connected else 'disconnected']=liquidity_control(anchor,operator['scientist']['image_id'],connected=connected).to_dict()
    for amount,connected in ((30,False),(30,True),(60,True),(60,False)):
        label='connected' if connected else 'disconnected'
        jobs.append({'identity':f'resource-{amount}-{label}','initial_funding':amount,'condition':label,
            'system':clone(systems[label]),'seed':SEED,'world_conditions':{
                'schema':'scienceutopia.native-world-conditions.v1','initial_funding':amount,
                'population_resource_profile':'balanced_two_band','log_resource_ledger':True}})
    experiment={'protocol':PROTOCOL,'role':'native-resource-opportunity-support'}
    world={**clone(operator['scientist']),'source_commit':source,'years':4,'experiment':experiment,
        'classification':'actual-native-liquidity-support-v1','runtime_seed_binding':clone(operator['world']['runtime_seed_binding'])}
    return {'schema':SCHEMA+'.plan','source_commit':source,'protocol_sha256':file_sha256(ROOT/PROTOCOL),
        'scientist':clone(operator['scientist']),'designer':clone(operator['designer']),
        'data_cache':operator['data_cache'],'world':world,'experiment':experiment,'jobs':jobs,
        'losses':objective_specs(),'preceding_observer':clone(preceding),
        'budget':{'worlds_upper_bound':4,'scientist_HTTP_attempts_per_world':1024,
            'scientist_loads_upper_bound':4,'world_wall_seconds':7200,'designer_generation_POSTs':0,
            'replace_failed_slots':False,'repeat_unfavorable_worlds':False},
        'development_seed_reused':True,'held_out_evaluation':False,'policy_selection':False,'publication_ready':False}


def require_plan(root):
    p=read(root/'plan.json')
    if p['source_commit']!=pinned_revision(ROOT):raise ValueError('exact clean liquidity source required')
    expected=build_plan(p,source=p['source_commit'],preceding=p['preceding_observer'])
    if expected!={k:v for k,v in p.items() if k!='content_sha256'}:raise ValueError('liquidity plan reconstruction differs')
    prior=Path(p['preceding_observer']['directory'])
    if (file_sha256(prior/'terminal.json')!=p['preceding_observer']['terminal_file_sha256']
            or file_sha256(prior/'plan.json')!=p['preceding_observer']['plan_file_sha256']
            or read(prior/'terminal.json')['status']!='closed'):
        raise ValueError('original observer closure differs')
    return p


def prepare(args):
    require_environment();source=pinned_revision(ROOT)
    if args.output.exists():raise ValueError('fresh liquidity experiment required')
    prior=args.preceding_observer.resolve();end=read(prior/'terminal.json')
    if end['schema']!='scienceutopia.native-common-content-readout.v1.terminal' or end['status']!='closed':
        raise ValueError('normally closed original observer required')
    if read(prior/'plan.json')['content_sha256']!='b9362297af8622e84ec4ba6b7fc8d778f375ee637d8d541259dfa8e24ad205cb':
        raise ValueError('exact original finite observer plan required')
    preceding={'directory':str(prior),'terminal_file_sha256':file_sha256(prior/'terminal.json'),
        'plan_file_sha256':file_sha256(prior/'plan.json')}
    plan=build_plan(read(args.operator_plan),source=source,preceding=preceding)
    if not Path(plan['data_cache']).is_dir():raise ValueError('existing offline corpus required')
    args.output.mkdir(parents=True);save(args.output/'plan.json',plan);require_plan(args.output)
    print(json.dumps({'source':source,'native_worlds_upper_bound':4,'new_model_calls':0}),flush=True)


def run(root):
    require_environment();p=require_plan(root)
    with (root/'writer.lock').open('a') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'started.json').exists():raise ValueError('consumed assay; no redispatch')
        save(root/'started.json',{'schema':SCHEMA+'.start','plan_sha256':p['content_sha256'],'started_utc':utc(),'pid':os.getpid()})
        stage='preparing';completed=0;failure={};status='stopped'
        try:
            for job in p['jobs']:
                stage=job['identity'];directory=root/'worlds-by-job'/stage
                write_json_atomic(root/'progress.json',{'active':stage,'complete_worlds':completed,'observed_utc':utc()},sort_keys=True)
                save(directory/'started.json',{'job':job,'started_utc':utc()})
                factory=LocalRoleBoundNativeFactory(directory/'worlds',Path(p['data_cache']),years=4,corpus_years=4,
                    designer_provider=p['designer'],record_wire=True,record_code=True,maximum_http_attempts=1024,
                    experiment_binding=p['experiment'],inference_lock=root/'inference.lock',world_conditions=job['world_conditions'])
                if factory.model_digest!=p['scientist']['model_digest'] or factory.corpus_sha256!=p['scientist']['corpus_sha256']:
                    raise ValueError('actual researcher/corpus differs from plan')
                def construct(spec,seed,run_id):
                    sim=factory(spec,seed,run_id)
                    if sim.llm.response_cache.stop is not sim.portable_stop:
                        raise ValueError('scientist cache and simulator must share the same safe points')
                    sim.portable_stop.deadline=time.monotonic()+p['budget']['world_wall_seconds']
                    return sim
                observation=evaluate_native_suggestion(Suggestion(stage,job['system'],0,'developer-liquidity-control'),
                    seeds=[SEED],simulation_factory=construct,loss_spec=p['losses']['throughput']).to_dict()
                save(directory/'observation.json',observation)
                save(directory/'cross-scores.json',{k:evaluate_loss(v,observation['metadata']['measurements']) for k,v in p['losses'].items()})
                if observation['status']!='complete':raise ValueError('control world failed; no later dispatch or replacement')
                completed+=1;require_plan(root)
            status='closed';stage='closed'
        except BaseException as error:
            failure={'error_type':type(error).__name__,'error':str(error)};raise
        finally:
            save(root/'terminal.json',{'schema':SCHEMA+'.terminal','status':status,'stage':stage,
                'complete_worlds':completed,'ended_utc':utc(),'policy_selection':False,'publication_ready':False,**failure})


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=('prepare','run'))
    parser.add_argument('--output',type=Path,required=True)
    for name in ('operator-plan','preceding-observer'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args()
    if args.stage=='prepare':
        if args.operator_plan is None or args.preceding_observer is None:parser.error('explicit operator and closed observer required')
        prepare(args)
    else:run(args.output)


if __name__=='__main__':main()
