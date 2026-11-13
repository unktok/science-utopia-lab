"""Selection-fixed common-seed evaluation of three normally audited studies.

All eight controls and eight own-selection labels remain. Only literal policy
identity (apart from supported world-seed binding) may share physical jobs.
No authoring, re-selection, failed-slot refill or implicit fallback.
"""
import argparse
from contextlib import ExitStack
import fcntl
import json
import os
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.native_benchmark_seed_usage import usage_inventory
from scripts.run_native_objective_fixed_evaluation_v1 import fixed_selection, jobs_for
from scripts.run_native_objective_instrument_loop_v1 import factory_for, measure_with, progress, utc
from scripts.run_pre_scale_search_v1 import require_environment
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.common_content_observer import CommonContentObserver, LocalObserverBackend, make_contract
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system.design_patch import clone, digest
from utopia.system.native_planning_controls import ORDER
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='scienceutopia.native-joint-fixed-evaluation.v1'
PROTOCOL='research/protocols/campaigns/native-joint-fixed-evaluation-v1.md'
STUDIES={'planning':'planning-v1','presentation':'parent-presentation-v1','numeric':'parameter-comparator-v1'}


def read(path):return checked(json.loads(Path(path).read_text()))


def origin_evidence(origin, kind):
    root,source=Path(origin['run']),Path(origin['source'])
    if pinned_revision(source)!=origin['source_commit']:raise ValueError('original '+kind+' source changed')
    audits=[read(path) for path in origin['audit_files']]
    if (len(audits)!=2 or audits[0]!=audits[1]
            or any(file_sha256(Path(path))!=h for path,h in origin['audit_files'].items())):
        raise ValueError('two unchanged matching original '+kind+' audits required')
    a=audits[0];p=read(root/'plan.json')
    inventory=_inventory(root)
    if (digest(inventory)!=a['raw_inventory_sha256'] or len(inventory)!=a['raw_files']
            or read(root/'started.json')!=a['closure']['started']
            or read(root/'terminal.json')!=a['closure']['terminal'] or read(root/'selection.json')!=a['selection']):
        raise ValueError('original '+kind+' raw/closure/selection changed')
    fixed_selection(p,a,study=STUDIES[kind]);return p,a


def shared_science(p):
    excluded={'source_commit','classification','experiment','measurement_adapter_contract'}
    observer_excluded={'source_commit','content_sha256','maximum_posts'}
    return {'scientist':clone(p['scientist']),'designer':clone(p['designer']),'data_cache':p['data_cache'],
        'losses':clone(p['losses']),'catalog':clone(p['catalog']),
        'world':{k:v for k,v in p['world'].items() if k not in excluded},
        'observer':{k:v for k,v in p['observer_contract'].items() if k not in observer_excluded}}


def combined_selection(evidence):
    selected={};sources={};order=[];definitions={}
    for kind in STUDIES:
        p,a=evidence[kind];frozen=fixed_selection(p,a,study=STUDIES[kind]);sources[kind]=clone(frozen)
        keys=p['arm_order'] if kind=='presentation' else p['objectives']
        for key in keys:
            label=kind+':'+key;order.append(label);selected[label]=clone(frozen['selected'][key])
            objective=p['arms'][key]['objective'] if kind=='presentation' else key
            definitions[label]={'origin_study':kind,'origin_key':key,'objective':objective,
                'origin_selection_sha256':frozen['content_sha256']}
    if len(selected)!=8:raise ValueError('exact two prior/free, four presentation and two numeric own pools required')
    selection={'schema':SCHEMA+'.policy-bank','selected':selected,'original_selections':sources,
        'baseline_fallback':False,'candidate_reselection':False,'held_out_evaluation':False}
    selection['content_sha256']=digest(selection)
    return selection,order,definitions


def contrasts_for():
    result=[]
    for objective in ('throughput','content-utility'):
        result.extend([
            {'id':'presentation-'+objective,'left':'presentation:'+objective+'-literal',
                'right':'presentation:'+objective+'-control','kind':'fixed-presentation-selected-policies'},
            {'id':'numeric-versus-free-'+objective,'left':'numeric:'+objective,
                'right':'planning:'+objective,'kind':'posthoc-fixed-numeric-versus-prior-free'}])
    for family,suffix in [('planning',''),('numeric',''),('presentation','-control'),('presentation','-literal')]:
        result.append({'id':'objective-choice-'+family+suffix,'left':family+':throughput'+suffix,
            'right':family+':content-utility'+suffix,'kind':'fixed-objective-conditioned-selected-policies'})
    return result


def build_plan(evidence,*,source,origins,usages,seeds,observer_backend,native_sources):
    if (set(evidence)!=set(STUDIES) or set(origins)!=set(STUDIES)
            or len(source)!=40 or any(c not in '0123456789abcdef' for c in source)
            or not isinstance(seeds,list) or not 1<=len(seeds)<=3
            or len(set(seeds))!=len(seeds) or any(type(v) is not int or not 0<=v<2**31 or v==61001 for v in seeds)
            or not usages or any(not u['valid'] or u['errors'] or u['prior_matching_runs'] or u['seeds']!=seeds for u in usages)):
        raise ValueError('three exact origins, explicit finite unused seeds and inventories required')
    original,prior=evidence['planning'];presentation,_=evidence['presentation'];numeric,_=evidence['numeric']
    if (original['objectives']!=['throughput','content-utility'] or original['generations']!=3
            or original['reference_order']!=list(ORDER) or presentation['reference_order']!=list(ORDER)
            or original['reference_systems']!=presentation['reference_systems']
            or any(shared_science(p)!=shared_science(original) for p,_ in evidence.values())
            or numeric['origin_audit_content_sha256']!=prior['content_sha256']
            or numeric['reference_context_sha256']!=prior['developer_references']['content_sha256']
            or native_sources['original_source']!=original['source_commit']):
        raise ValueError('same literal controls, science, objectives and numeric common-bank origin required')
    selection,order,definitions=combined_selection(evidence)
    observer=make_contract(source_commit=source,provider={k:original['scientist'][k] for k in ('model','model_digest')},
        backend=observer_backend,maximum_posts=6000,critics=3)
    ignore={'source_commit','content_sha256','maximum_posts'}
    if {k:v for k,v in observer.items() if k not in ignore}!=shared_science(original)['observer']:
        raise ValueError('fixed common-content instrument changed')
    experiment={'protocol':PROTOCOL,'role':'selection-fixed-common-world-evaluation'}
    p={'schema':SCHEMA+'.plan','source_commit':source,'runtime':runtime_binding(),'protocol':PROTOCOL,
        'protocol_sha256':file_sha256(ROOT/PROTOCOL),'origins':clone(origins),
        'origin_audit_content_sha256':{k:a['content_sha256'] for k,(_,a) in evidence.items()},
        'original_native_sources':clone(native_sources),
        **{k:clone(original[k]) for k in ('scientist','designer','data_cache','losses','catalog','objectives')},
        'world':{**clone(original['world']),'source_commit':source,'experiment':experiment,
            'measurement_adapter_contract':observer,'classification':'actual-native-joint-fixed-evaluation-v1'},
        'experiment':experiment,'observer_contract':observer,'fixed_selection':selection,
        'selection_order':order,'selection_definitions':definitions,'contrasts':contrasts_for(),
        'reference_systems':clone(original['reference_systems']),
        'evaluation':{'seeds':clone(seeds),'reference_labels':list(ORDER),
            'maximum_physical_worlds':16*len(seeds),'seed_usage':[u['content_sha256'] for u in usages]},
        'budget':{'scientist_HTTP_attempts_per_world':1024,'world_wall_seconds':7200,
            'observer_POSTs_upper_bound':6000,'designer_generation_POSTs':0,'replace_failed_slots':False},
        'claims':{'independent_optimizer_replications':False,'new_literature':False,'independent_critic_errors':False,
            'scientific_truth':False,'publication_ready':False,'candidate_reselection':False}}
    p['jobs']=jobs_for(p);return p


def require_plan(root):
    from scripts.run_native_parameter_comparator_v1 import unchanged_native_sources
    p=read(root/'plan.json')
    if p['source_commit']!=pinned_revision(ROOT) or p['runtime']!=runtime_binding():
        raise ValueError('exact joint-evaluation source/runtime required')
    evidence={k:origin_evidence(p['origins'][k],k) for k in STUDIES}
    usages=[read(root/f'seed-usage-{i:02d}.json') for i in range(len(p['evaluation']['seed_usage']))]
    expected=build_plan(evidence,source=p['source_commit'],origins=p['origins'],usages=usages,
        seeds=p['evaluation']['seeds'],observer_backend=p['observer_contract']['backend'],
        native_sources=unchanged_native_sources(evidence['planning'][0]['source_commit']))
    if expected!={k:v for k,v in p.items() if k!='content_sha256'}:raise ValueError('literal joint evaluation reconstruction differs')
    return p


def observe(root,p,job,observer):
    directory=root/'evaluation'/job['identity']
    if (directory/'started.json').exists():raise ValueError('consumed joint evaluation job; no redispatch')
    s=Suggestion(job['identity'],job['system'],0,'selection-fixed-evaluation')
    save(directory/'started.json',{**clone(job),'suggestion':s.to_dict(),'started_utc':utc()})
    o=evaluate_native_suggestion(s,seeds=[job['seed']],simulation_factory=factory_for(directory/'worlds',p,root),
        loss_spec=p['losses']['throughput'],measurement_adapter=measure_with(observer,p['observer_contract'])).to_dict()
    save(directory/'observation.json',o)
    save(directory/'cross-scores.json',{k:evaluate_loss(v,o['metadata']['measurements']) for k,v in p['losses'].items()})


def run(root):
    require_environment();p=require_plan(root)
    with ExitStack() as stack:
        paths={root/'writer.lock',*(Path(v['run'])/'writer.lock' for v in p['origins'].values())}
        for path in sorted(paths):
            h=stack.enter_context(path.open('a' if path==root/'writer.lock' else 'r'))
            fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'started.json').exists():raise ValueError('consumed joint evaluation; no redispatch')
        for i in range(len(p['evaluation']['seed_usage'])):
            old=read(root/f'seed-usage-{i:02d}.json')
            if not Path(old['root']).is_dir():raise ValueError('declared seed-inventory root disappeared before dispatch')
            u=usage_inventory(old['root'],p['evaluation']['seeds'])
            if not u['valid'] or u['errors'] or u['prior_matching_runs']:raise ValueError('evaluation seeds consumed after preparation')
            save(root/f'pre-dispatch-seed-usage-{i:02d}.json',{k:v for k,v in u.items() if k!='content_sha256'})
        save(root/'started.json',{'schema':SCHEMA+'.start','pid':os.getpid(),
            'plan_sha256':p['content_sha256'],'started_utc':utc()})
        status,completed,error='stopped',0,{}
        try:
            observer=CommonContentObserver(root/'observer',p['observer_contract'],
                backend=LocalObserverBackend(inference_lock=root/'inference.lock'))
            for job in p['jobs']:
                progress(root,'evaluation',job['identity']);observe(root,p,job,observer);completed+=1;require_plan(root)
            a=observer.audit();save(root/'observer-audit.json',{k:v for k,v in a.items() if k!='content_sha256'})
            if read(root/'observer-audit.json')!=a:raise ValueError('literal common observer retention differs')
            status='closed';progress(root,'closed')
        except BaseException as e:
            error={'error_type':type(e).__name__,'error':str(e)};raise
        finally:
            save(root/'terminal.json',{'schema':SCHEMA+'.terminal','status':status,'completed_jobs':completed,
                'ended_utc':utc(),'held_out_world_seeds':True,'publication_ready':False,**error})


def prepare(args):
    from scripts.run_native_parameter_comparator_v1 import unchanged_native_sources
    require_environment();source=pinned_revision(ROOT)
    origins={}
    for kind in STUDIES:
        spec=getattr(args,kind+'_origin');run,source_root,one,two=map(Path,spec)
        a=read(one);origins[kind]={'run':str(run.resolve()),'source':str(source_root.resolve()),
            'source_commit':a['source_commit'],'audit_files':{str(v.resolve()):file_sha256(v) for v in (one,two)}}
    if (args.output.exists() or any(args.output.is_relative_to(Path(v['run'])) for v in origins.values())
            or not args.seed_usage_root or any(not p.is_dir() for p in args.seed_usage_root)):
        raise ValueError('fresh separate output and existing explicit seed roots required')
    with ExitStack() as stack:
        for path in sorted({Path(v['run'])/'writer.lock' for v in origins.values()}):
            h=stack.enter_context(path.open('r'));fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        evidence={k:origin_evidence(origins[k],k) for k in STUDIES}
        usages=[usage_inventory(v,args.evaluation_seed) for v in args.seed_usage_root]
        original=evidence['planning'][0]
        p=build_plan(evidence,source=source,origins=origins,usages=usages,seeds=args.evaluation_seed,
            observer_backend=backend_binding({k:original['scientist'][k] for k in ('model','model_digest')}),
            native_sources=unchanged_native_sources(original['source_commit']))
        args.output.mkdir(parents=True)
        for i,u in enumerate(usages):save(args.output/f'seed-usage-{i:02d}.json',{k:v for k,v in u.items() if k!='content_sha256'})
        save(args.output/'plan.json',p);require_plan(args.output)
    print(json.dumps({'prepared_source':source,'physical_jobs':len(p['jobs']),'designer_POSTs':0,'new_model_calls':0}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=('prepare','run'))
    parser.add_argument('--output',type=Path,required=True)
    for kind in STUDIES:parser.add_argument('--'+kind+'-origin',nargs=4,metavar=('RUN','SOURCE','AUDIT_ONE','AUDIT_TWO'))
    parser.add_argument('--seed-usage-root',type=Path,action='append')
    parser.add_argument('--evaluation-seed',type=int,action='append');args=parser.parse_args();args.output=args.output.resolve()
    if args.stage=='prepare':
        if any(getattr(args,k+'_origin') is None for k in STUDIES) or not args.evaluation_seed:
            parser.error('all three normally closed origins and explicit unused evaluation seeds required')
        prepare(args)
    else:run(args.output)


if __name__=='__main__':main()
