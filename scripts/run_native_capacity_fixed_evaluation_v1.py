"""Prospective unused-seed T/P evaluation, literal frozen selection, no design."""
import argparse
import fcntl
import json
import os
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.native_benchmark_seed_usage import usage_inventory
from scripts.run_native_capacity_objective_loop_v1 import measured, SEED, OBJECTIVES
from scripts.run_native_objective_fixed_evaluation_v1 import fixed_selection, jobs_for
from scripts.run_native_objective_instrument_loop_v1 import factory_for, progress, utc
from scripts.run_pre_scale_search_v1 import require_environment
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_designer_preflight import runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='scienceutopia.native-capacity-fixed-evaluation.v1'
PROTOCOL='research/protocols/campaigns/native-capacity-fixed-evaluation-v1.md'
INSTRUMENT='utopia/optimization/native_active_founders.py'


def read(path):return checked(json.loads(Path(path).read_text()))


def build_plan(original,audit,*,source,origin,usages,seeds):
    selection=fixed_selection(original,audit,study='capacity-v1')
    if (original['objectives']!=list(OBJECTIVES) or original['held_out_evaluation']
            or not isinstance(seeds,list) or not 1<=len(seeds)<=3
            or any(type(s) is not int or not 0<=s<2**31 or s==SEED for s in seeds)
            or len(set(seeds))!=len(seeds) or len(source)!=40
            or any(c not in '0123456789abcdef' for c in source) or not usages
            or any(not u['valid'] or u['errors'] or u['prior_matching_runs'] or u['seeds']!=seeds for u in usages)):
        raise ValueError('exact closed T/P study and one to three explicit unused seeds required')
    contract=clone(original['measurement_contract'])
    if (contract['source_commit']!=original['source_commit']
            or contract['instrument_sha256']!=file_sha256(ROOT/INSTRUMENT)
            or contract['new_model_calls'] or contract['adoption_constraint']):
        raise ValueError('unchanged original P instrument bytes and measurement scope required')
    contract['source_commit']=source
    experiment={'protocol':PROTOCOL,'role':'selection-frozen-capacity-evaluation'}
    world={**clone(original['world']),'source_commit':source,'experiment':experiment,
        'measurement_adapter_contract':contract,'classification':'actual-native-capacity-fixed-evaluation-v1'}
    p={'schema':SCHEMA+'.plan','source_commit':source,'runtime':runtime_binding(),
        'protocol':PROTOCOL,'protocol_sha256':file_sha256(ROOT/PROTOCOL),'origin':clone(origin),
        'origin_audit_content_sha256':audit['content_sha256'],'origin_selection_sha256':selection['content_sha256'],
        'scientist':clone(original['scientist']),'designer':clone(original['designer']),
        'data_cache':original['data_cache'],'world':world,'experiment':experiment,'measurement_contract':contract,
        'losses':clone(original['losses']),'objectives':clone(original['objectives']),
        'fixed_selection':selection,'reference_systems':clone(original['reference_systems']),
        'evaluation':{'seeds':clone(seeds),'reference_labels':clone(original['reference_order']),
            'maximum_physical_worlds':(len(original['reference_order'])+len(OBJECTIVES))*len(seeds),
            'seed_usage':[u['content_sha256'] for u in usages]},
        'budget':{'scientist_HTTP_attempts_per_world':1024,'world_wall_seconds':7200,
            'designer_generation_POSTs':0,'critic_POSTs':0,'replace_failed_slots':False},
        'claims':{'independent_optimizer_replications':False,'scientific_truth':False,'publication_ready':False}}
    p['jobs']=jobs_for(p);return p


def origin_evidence(origin):
    root,source=Path(origin['run']),Path(origin['source'])
    if pinned_revision(source)!=origin['source_commit']:
        raise ValueError('frozen original source changed')
    audits=[read(path) for path in origin['audit_files']]
    if (len(audits)!=2 or audits[0]!=audits[1]
            or any(file_sha256(Path(path))!=h for path,h in origin['audit_files'].items())):
        raise ValueError('two unchanged matching original development audits required')
    audit=audits[0];original=read(root/'plan.json')
    if (digest(_inventory(root))!=audit['raw_inventory_sha256']
            or read(root/'terminal.json')!=audit['closure']['terminal']
            or read(root/'selection.json')!=audit['selection']):
        raise ValueError('audited original selection/raw changed')
    fixed_selection(original,audit,study='capacity-v1');return original,audit


def require_plan(root):
    p=read(root/'plan.json')
    if p['source_commit']!=pinned_revision(ROOT) or p['runtime']!=runtime_binding():
        raise ValueError('exact fixed-evaluation source/runtime required')
    original,audit=origin_evidence(p['origin'])
    usages=[read(root/f'seed-usage-{i:02d}.json') for i in range(len(p['evaluation']['seed_usage']))]
    expected=build_plan(original,audit,source=p['source_commit'],origin=p['origin'],usages=usages,
        seeds=p['evaluation']['seeds'])
    if expected!={k:v for k,v in p.items() if k!='content_sha256'}:
        raise ValueError('fixed capacity evaluation reconstruction differs')
    return p


def prepare(args):
    require_environment();source=pinned_revision(ROOT)
    if (args.output.exists() or args.output.is_relative_to(args.origin_run.resolve())
            or not args.seed_usage_root):
        raise ValueError('fresh separate output and explicit seed roots required')
    audit=read(args.audit_one)
    origin={'run':str(args.origin_run.resolve()),'source':str(args.origin_source.resolve()),
        'source_commit':audit['source_commit'],
        'audit_files':{str(path.resolve()):file_sha256(path) for path in (args.audit_one,args.audit_two)}}
    with (args.origin_run/'writer.lock').open('r') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB);original,audit=origin_evidence(origin)
        usages=[usage_inventory(path,args.evaluation_seed) for path in args.seed_usage_root]
        p=build_plan(original,audit,source=source,origin=origin,usages=usages,seeds=args.evaluation_seed)
        args.output.mkdir(parents=True)
        for i,u in enumerate(usages):save(args.output/f'seed-usage-{i:02d}.json',{k:v for k,v in u.items() if k!='content_sha256'})
        save(args.output/'plan.json',p);require_plan(args.output)
    print(json.dumps({'prepared_source':source,'physical_jobs':len(p['jobs']),'designer_POSTs':0,'critic_POSTs':0}),flush=True)


def observe(root,p,job):
    directory=root/'evaluation'/job['identity']
    if (directory/'started.json').exists():
        raise ValueError('consumed evaluation job; no redispatch')
    suggestion=Suggestion(job['identity'],job['system'],0,'selection-fixed-evaluation')
    save(directory/'started.json',{**clone(job),'suggestion':suggestion.to_dict(),'started_utc':utc()})
    observation=evaluate_native_suggestion(suggestion,seeds=[job['seed']],
        simulation_factory=factory_for(directory/'worlds',p,root),loss_spec=p['losses']['throughput'],
        measurement_adapter=measured(p)).to_dict()
    save(directory/'observation.json',observation)
    save(directory/'cross-scores.json',
        {k:evaluate_loss(loss,observation['metadata']['measurements']) for k,loss in p['losses'].items()})


def run(root):
    require_environment();p=require_plan(root)
    with (root/'writer.lock').open('a') as owner,(Path(p['origin']['run'])/'writer.lock').open('r') as origin_owner:
        for handle in (owner,origin_owner):fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'started.json').exists():raise ValueError('consumed evaluation; no redispatch')
        for i in range(len(p['evaluation']['seed_usage'])):
            old=read(root/f'seed-usage-{i:02d}.json');usage=usage_inventory(old['root'],p['evaluation']['seeds'])
            if not usage['valid']:raise ValueError('evaluation seed consumed after preparation')
            save(root/f'pre-dispatch-seed-usage-{i:02d}.json',{k:v for k,v in usage.items() if k!='content_sha256'})
        save(root/'started.json',{'schema':SCHEMA+'.start','pid':os.getpid(),
            'plan_sha256':p['content_sha256'],'started_utc':utc()})
        status='stopped';completed=0;failure={}
        try:
            for job in p['jobs']:
                progress(root,'evaluation',job['identity']);observe(root,p,job);completed+=1;require_plan(root)
            status='closed';progress(root,'closed')
        except BaseException as error:
            failure={'error_type':type(error).__name__,'error':str(error)};raise
        finally:
            save(root/'terminal.json',{'schema':SCHEMA+'.terminal','status':status,'completed_jobs':completed,
                'ended_utc':utc(),'held_out_world_seeds':True,'publication_ready':False,**failure})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','run'));parser.add_argument('--output',type=Path,required=True)
    for key in ('origin-run','origin-source','audit-one','audit-two'):parser.add_argument('--'+key,type=Path)
    parser.add_argument('--seed-usage-root',type=Path,action='append')
    parser.add_argument('--evaluation-seed',type=int,action='append')
    args=parser.parse_args();args.output=args.output.resolve()
    if args.stage=='prepare':
        if any(getattr(args,k) is None for k in ('origin_run','origin_source','audit_one','audit_two','evaluation_seed')):
            parser.error('closed original study and explicit unused seed list required')
        prepare(args)
    else:run(args.output)


if __name__=='__main__':main()
