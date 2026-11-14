"""Unused-world-seed evaluation of frozen T/U submissions, never new authoring."""
import argparse
import fcntl
import json
import os
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.native_benchmark_seed_usage import usage_inventory
from scripts.run_native_objective_instrument_loop_v1 import factory_for,measure_with,progress
from scripts.run_pre_scale_search_v1 import require_environment,evaluation_jobs
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.common_content_observer import CommonContentObserver,LocalObserverBackend,make_contract
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_designer_preflight import backend_binding,runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked,save
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system.design_patch import clone,digest
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='scienceutopia.native-objective-fixed-evaluation.v1'
PROTOCOL='research/protocols/campaigns/native-objective-fixed-evaluation-v1.md'


def read(path):return checked(json.loads(Path(path).read_text()))


def fixed_selection(original,audit,*,study='count-content-v1'):
    checked(original);checked(audit)
    if study=='count-content-v1':
        plan_schema='scienceutopia.native-objective-instrument-loop.v1.plan'
        audit_schema='scienceutopia.native-objective-instrument-loop-audit.v1'
    elif study=='planning-v1':
        plan_schema='scienceutopia.native-planning-objective-loop.v1.plan'
        audit_schema='scienceutopia.native-planning-objective-loop-audit.v1'
    elif study=='capacity-v1':
        plan_schema='scienceutopia.native-capacity-objective-loop.v1.plan'
        audit_schema='scienceutopia.native-capacity-objective-loop-audit.v1'
    elif study=='parent-presentation-v1':
        plan_schema='scienceutopia.native-parent-presentation-loop.v1.plan'
        audit_schema='scienceutopia.native-parent-presentation-loop-audit.v1'
    elif study=='parameter-comparator-v1':
        plan_schema='scienceutopia.native-parameter-comparator.v1.plan'
        audit_schema='scienceutopia.native-parameter-comparator-audit.v1'
    elif study=='workflow-v1':
        plan_schema='scienceutopia.native-workflow-objective-loop.v1.plan'
        audit_schema='scienceutopia.native-workflow-objective-loop-audit.v1'
    else:raise ValueError('explicit supported fixed-selection study required')
    selection=audit['selection'];checked(selection)
    keys=original['arm_order'] if study=='parent-presentation-v1' else original['objectives']
    if (original['schema']!=plan_schema
            or audit['schema']!=audit_schema
            or audit['source_commit']!=original['source_commit'] or audit['plan_sha256']!=original['content_sha256']
            or audit['closure']['terminal']['status']!='closed'
            or audit['source_proof']['status']!='verified-exact-source-closure'
            or audit['new_model_calls'] or audit['new_code_executions'] or audit['held_out_evaluation']
            or selection['plan_sha256']!=original['content_sha256'] or selection['baseline_fallback']
            or selection['held_out_evaluation'] or set(selection['selected'])!=set(keys)):
        raise ValueError('exact closed development and frozen own-submission selection required')
    for objective,s in selection['selected'].items():
        criterion=original['arms'][objective]['objective'] if study=='parent-presentation-v1' else objective
        def belongs(w):
            return (w['role']=='numeric-own-proposal' and w['objective']==objective
                if study=='parameter-comparator-v1' else
                w['role']=='workflow-own-proposal' and w['objective']==objective
                if study=='workflow-v1' else w['role']=='search:'+objective)
        pool=[w for w in audit['worlds'] if belongs(w) and w['status']=='complete'
            and w['scores'][criterion] is not None]
        # The original full audit proves chronological first-tie selection.
        # Here preserve that sealed result, independently checking its pool.
        # Workflow's literal original selection has no completed_submissions
        # field. Its full audit proves all six slots; validate the exact pool,
        # losses/ties/chosen system below without fabricating a count or
        # amending that historical selection. Other study contracts stay exact.
        if study!='workflow-v1' and len(pool)!=s['completed_submissions']:
            raise ValueError('selected pool differs from original submissions')
        best=min((w['scores'][criterion] for w in pool),default=None)
        ids={w['identity'] for w in pool if w['scores'][criterion]==best}
        chosen=next((w for w in pool if w['identity']==s['selected_id']),None)
        if (s['loss']!=best or set(s['all_tied_ids'])!=ids or len(s['all_tied_ids'])!=len(ids)
                or s['selected_id']!=(s['all_tied_ids'][0] if ids else None)
                or s['system']!=(None if chosen is None else chosen['system'])):
            raise ValueError('selected literal submitted policy/ties differ')
    return clone(selection)


def jobs_for(p):
    projection={k:v for k,v in p.items() if k not in ('jobs','content_sha256')}
    projection['content_sha256']=digest(projection)
    selected_policies=clone(p['fixed_selection']['selected'])
    if p.get('schema') in ('scienceutopia.native-joint-fixed-evaluation.v1.plan',
            'scienceutopia.native-workflow-fixed-evaluation.v1.plan'):
        # JSON object order is not durable. This explicit new-study order also
        # determines label lists on shared physical jobs. Historical studies
        # retain their original source/semantics; do not rewrite their jobs.
        order=p['objectives'] if p['schema']=='scienceutopia.native-workflow-fixed-evaluation.v1.plan' else p['selection_order']
        if len(order)!=len(set(order)) or set(order)!=set(selected_policies):
            raise ValueError('literal unique joint selection order required')
        selected_policies={key:selected_policies[key] for key in order}
    selected={'plan_sha256':projection['content_sha256'],'selected':selected_policies}
    selected['content_sha256']=digest(selected)
    return evaluation_jobs(projection,selected)


def build_plan(original,audit,*,source,origin,usages,observer_backend):
    selection=fixed_selection(original,audit);seeds=original['evaluation']['seeds']
    if (len(source)!=40 or any(c not in '0123456789abcdef' for c in source) or not usages
            or any(not u['valid'] or u['errors'] or u['prior_matching_runs'] or u['seeds']!=seeds for u in usages)):
        raise ValueError('exact evaluation source and declared unused seeds required')
    scientific={k:original['scientist'][k] for k in ('model','model_digest')}
    observer=make_contract(source_commit=source,provider=scientific,backend=observer_backend,maximum_posts=3000,critics=3)
    # Only physical source/cache binding differs; no new judge, rubric, decode,
    # centering or pooling is selected using development or evaluation scores.
    for key in original['observer_contract']:
        if key not in ('source_commit','content_sha256') and original['observer_contract'][key]!=observer[key]:
            raise ValueError('fixed scientific content observer changed')
    experiment={'protocol':PROTOCOL,'role':'selection-frozen-objective-evaluation'}
    world={**clone(original['world']),'source_commit':source,'experiment':experiment,
        'measurement_adapter_contract':observer,'classification':'actual-native-objective-fixed-evaluation-v1'}
    p={'schema':SCHEMA+'.plan','source_commit':source,'runtime':runtime_binding(),'protocol':PROTOCOL,
        'protocol_sha256':file_sha256(ROOT/PROTOCOL),'origin':clone(origin),
        'origin_audit_content_sha256':audit['content_sha256'],'origin_selection_sha256':selection['content_sha256'],
        'scientist':clone(original['scientist']),'designer':clone(original['designer']),
        'data_cache':original['data_cache'],'world':world,'experiment':experiment,'observer_contract':observer,
        'losses':clone(original['losses']),'objectives':clone(original['objectives']),
        'fixed_selection':selection,'reference_systems':clone(original['reference_systems']),
        'evaluation':{'seeds':clone(seeds),'reference_labels':clone(original['reference_order']),
            'maximum_physical_worlds':21,'seed_usage':[u['content_sha256'] for u in usages]},
        'budget':{'scientist_HTTP_attempts_per_world':1024,'world_wall_seconds':7200,
            'observer_POSTs_upper_bound':3000,'designer_generation_POSTs':0,'replace_failed_slots':False},
        'claims':{'independent_optimizer_replications':False,'new_literature':False,'independent_critic_errors':False,
            'scientific_truth':False,'publication_ready':False}}
    p['jobs']=jobs_for(p);return p


def origin_evidence(origin):
    root=Path(origin['run']);source=Path(origin['source'])
    if pinned_revision(source)!=origin['source_commit']:raise ValueError('frozen original source changed')
    audits=[read(path) for path in origin['audit_files']]
    if (len(audits)!=2 or audits[0]!=audits[1]
            or any(file_sha256(Path(path))!=h for path,h in origin['audit_files'].items())):
        raise ValueError('two unchanged matching development audits required')
    a=audits[0];original=read(root/'plan.json')
    if (digest(_inventory(root))!=a['raw_inventory_sha256']
            or read(root/'terminal.json')!=a['closure']['terminal']
            or read(root/'selection.json')!=a['selection']):raise ValueError('audited original selection/raw changed')
    fixed_selection(original,a);return original,a


def require_plan(root):
    p=read(root/'plan.json')
    if p['source_commit']!=pinned_revision(ROOT) or p['runtime']!=runtime_binding():
        raise ValueError('exact fixed-evaluation source/runtime required')
    original,audit=origin_evidence(p['origin'])
    usages=[read(root/f'seed-usage-{i:02d}.json') for i in range(len(p['evaluation']['seed_usage']))]
    expected=build_plan(original,audit,source=p['source_commit'],origin=p['origin'],usages=usages,
        observer_backend=p['observer_contract']['backend'])
    if expected!={k:v for k,v in p.items() if k!='content_sha256'}:raise ValueError('fixed evaluation reconstruction differs')
    return p


def prepare(args):
    require_environment();source=pinned_revision(ROOT)
    if (args.output.exists() or args.output.is_relative_to(args.origin_run.resolve())
            or not args.seed_usage_root):raise ValueError('fresh separate output and explicit seed roots required')
    a=read(args.audit_one)
    origin={'run':str(args.origin_run.resolve()),'source':str(args.origin_source.resolve()),'source_commit':a['source_commit'],
        'audit_files':{str(v.resolve()):file_sha256(v) for v in (args.audit_one,args.audit_two)}}
    with (args.origin_run/'writer.lock').open('r') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB);original,audit=origin_evidence(origin)
        usages=[usage_inventory(v,original['evaluation']['seeds']) for v in args.seed_usage_root]
        p=build_plan(original,audit,source=source,origin=origin,usages=usages,
            observer_backend=backend_binding({k:original['scientist'][k] for k in ('model','model_digest')}))
        args.output.mkdir(parents=True)
        for i,u in enumerate(usages):save(args.output/f'seed-usage-{i:02d}.json',{k:v for k,v in u.items() if k!='content_sha256'})
        save(args.output/'plan.json',p);require_plan(args.output)
    print(json.dumps({'prepared_source':source,'physical_jobs':len(p['jobs']),'designer_POSTs':0}),flush=True)


def observe(root,p,job,observer):
    from scripts.run_native_objective_instrument_loop_v1 import utc
    directory=root/'evaluation'/job['identity']
    if (directory/'started.json').exists():raise ValueError('consumed evaluation job; no redispatch')
    suggestion=Suggestion(job['identity'],job['system'],0,'selection-fixed-evaluation')
    save(directory/'started.json',{**clone(job),'suggestion':suggestion.to_dict(),'started_utc':utc()})
    o=evaluate_native_suggestion(suggestion,seeds=[job['seed']],simulation_factory=factory_for(directory/'worlds',p,root),
        loss_spec=p['losses']['throughput'],measurement_adapter=measure_with(observer,p['observer_contract'])).to_dict()
    save(directory/'observation.json',o)
    save(directory/'cross-scores.json',{k:evaluate_loss(v,o['metadata']['measurements']) for k,v in p['losses'].items()})


def run(root, *, require_plan_fn=None, observe_fn=None, schema=None, inventory_fn=None):
    from scripts.run_native_objective_instrument_loop_v1 import utc
    ensure = require_plan if require_plan_fn is None else require_plan_fn
    dispatch = observe if observe_fn is None else observe_fn
    actual_schema = SCHEMA if schema is None else schema
    inventory = usage_inventory if inventory_fn is None else inventory_fn
    require_environment();p=ensure(root)
    with (root/'writer.lock').open('a') as owner,(Path(p['origin']['run'])/'writer.lock').open('r') as origin_owner:
        for h in (owner,origin_owner):fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'started.json').exists():raise ValueError('consumed evaluation; no redispatch')
        for i in range(len(p['evaluation']['seed_usage'])):
            old=read(root/f'seed-usage-{i:02d}.json');u=inventory(old['root'],p['evaluation']['seeds'])
            if inventory_fn is not None:
                save(root/f'pre-dispatch-seed-usage-{i:02d}.json',{k:v for k,v in u.items() if k!='content_sha256'})
            if not u['valid']:raise ValueError('evaluation seeds consumed after preparation')
            if inventory_fn is None:
                save(root/f'pre-dispatch-seed-usage-{i:02d}.json',{k:v for k,v in u.items() if k!='content_sha256'})
        save(root/'started.json',{'schema':actual_schema+'.start','pid':os.getpid(),'plan_sha256':p['content_sha256'],'started_utc':utc()})
        status='stopped';completed=0;error={}
        try:
            observer=CommonContentObserver(root/'observer',p['observer_contract'],backend=LocalObserverBackend(inference_lock=root/'inference.lock'))
            for job in p['jobs']:
                progress(root,'evaluation',job['identity']);dispatch(root,p,job,observer);completed+=1;ensure(root)
            a=observer.audit();save(root/'observer-audit.json',{k:v for k,v in a.items() if k!='content_sha256'})
            if read(root/'observer-audit.json')!=a:raise ValueError('saved observer audit differs')
            status='closed';progress(root,'closed')
        except BaseException as e:
            error={'error_type':type(e).__name__,'error':str(e)};raise
        finally:
            save(root/'terminal.json',{'schema':actual_schema+'.terminal','status':status,'completed_jobs':completed,
                'ended_utc':utc(),'held_out_world_seeds':True,'publication_ready':False,**error})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=('prepare','run'));p.add_argument('--output',type=Path,required=True)
    for key in ('origin-run','origin-source','audit-one','audit-two'):p.add_argument('--'+key,type=Path)
    p.add_argument('--seed-usage-root',type=Path,action='append');a=p.parse_args();a.output=a.output.resolve()
    if a.stage=='prepare':
        if any(getattr(a,k) is None for k in ('origin_run','origin_source','audit_one','audit_two')):p.error('explicit closed original study required')
        prepare(a)
    else:run(a.output)


if __name__=='__main__':main()
