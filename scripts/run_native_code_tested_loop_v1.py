"""Finite T/E closed loop with literal post-edit code execution feedback.

Separate source and slots, not a resumption of earlier stopped experiments.
Wait for the existing science/audit chain; never overlap local model roles.
"""
import argparse
from datetime import datetime,timezone
import fcntl
import json
import os
from pathlib import Path
from types import SimpleNamespace

from scripts.finish_native_fixed_evaluation_report_v1 import wait_analysis
from scripts.run_pre_scale_search_v1 import require_environment,ENVIRONMENT,campaign,observe
from scripts.run_native_institution_loop_v1 import readiness
from utopia.optimization.native_benchmark_controls import objective_specs,selection_control
from utopia.optimization.native_bounded_staged_designer import execute
from utopia.optimization.native_causal_design import OPTION,PRESENTATION
from utopia.optimization.native_designer_preflight import runtime_binding,backend_binding
from utopia.optimization.native_designer_roles_v38 import validate_designer_binding
from utopia.optimization.native_fixed_production_domain import allow_review_routing
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory
from utopia.optimization.native_numeric_designer import checked,save
from utopia.optimization.native_post_edit_feedback_v1 import NativePostEditFeedback,OPTION as TEST_OPTION
from utopia.optimization.native_review_routing_controls import routed_control
from utopia.system.design_patch import clone,digest
from utopia.system.native_information_institution import information_system,information_design_space
from utopia.utils.data_utils import file_sha256,write_json_atomic

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='scienceutopia.native-code-tested-loop.v1'
PROTOCOL='research/protocols/campaigns/native-code-tested-loop-v1.md'
BANK_MANIFEST='research/data/native-component-fixtures-v1/summary.json'
SEED=61001
OBJECTIVES=('throughput','efficiency')


def read(path):return checked(json.loads(Path(path).read_text()))
def utc():return datetime.now(timezone.utc).isoformat()


def feedback_for(bank,source,image):
    # No executor is constructed during preparation. The real bounded worker
    # supplies its own pinned Docker executor, never one chosen by a model.
    def forbidden(*args):raise AssertionError('preparation must never execute candidate code')
    return NativePostEditFeedback(bank,executor=SimpleNamespace(image_id=image,timeout=15.,execute=forbidden),
        source_commit=source,maximum_probes=8)


def build_plan(*,operator,source,backend,bank,bank_file_hash,preceding):
    validate_designer_binding(operator['designer'],scientist_binding=operator['scientist'])
    if len(source)!=40 or any(c not in '0123456789abcdef' for c in source):raise ValueError('full clean source required')
    manifest=read(ROOT/BANK_MANIFEST);checked(bank)
    if bank_file_hash!=manifest['bank_file_sha256'] or bank['content_sha256']!=manifest['bank_content_sha256']:
        raise ValueError('exact predeclared developer fixture bank required')
    image=operator['scientist']['image_id'];anchor=information_system(image,seed=SEED)
    if any(r['receipt']['image_id']!=image for r in bank['records']):raise ValueError('developer fixture image differs from fixed native image')
    contract=feedback_for(bank,source,image).contract
    experiment={'protocol':PROTOCOL,'role':'code-tested-native-development-loop'}
    world={**clone(operator['scientist']),'source_commit':source,'years':4,
        'experiment':experiment,'classification':'actual-native-code-tested-loop-v1',
        'runtime_seed_binding':{'python_hash_seed_environment':os.environ.get('PYTHONHASHSEED'),
                              'python_hash_probe':hash('scienceutopia.native-world.v1')}}
    bindings={};assignments={};losses=objective_specs()
    for objective in OBJECTIVES:
        arm=objective+':code-and-graph'
        assignments[arm]={'objective':objective,'method':'code-and-graph','strategy':'local-designer','domain':'code-and-graph'}
        bindings[arm]={'initial_system':anchor.to_dict(),'loss_spec':losses[objective],'seeds':[SEED],
            'world':world,'seed':63001,'design_space':allow_review_routing(anchor,
                information_design_space(anchor,'code-and-graph',fixed_production=True)),
            'strategies':{'local-designer':{'kind':'code-and-graph','protocol':PROTOCOL,
                OPTION:True,PRESENTATION:'inline',TEST_OPTION:contract}}}
    order=list(bindings)
    references={'open-seed':anchor.to_dict(),'reviewed-accept-all':selection_control(anchor,rule='accept-all').to_dict(),
        'routed-one-accept-all':selection_control(routed_control(anchor,reviewers_per_paper=1,
            snapshot_phase=85,producer_phase=87),rule='accept-all').to_dict()}
    return {'schema':SCHEMA+'.plan','source_commit':source,'runtime':runtime_binding(),
        'protocol':PROTOCOL,'protocol_sha256':file_sha256(ROOT/PROTOCOL),'launch_environment':clone(ENVIRONMENT),
        'scientist':clone(operator['scientist']),'designer':clone(operator['designer']),'backend':clone(backend),
        'data_cache':operator['data_cache'],'world':world,'experiment':experiment,'losses':losses,
        'objectives':list(OBJECTIVES),'methods':['code-and-graph'],'arm_order':order,'assignments':assignments,
        'campaign_bindings':{'run-00':bindings},'generations':2,
        'schedule':[{'arm':arm,'generation':g} for g in (0,1) for arm in (order if g==0 else order[::-1])],
        'reference_systems':references,'reference_order':list(references),
        'component_bank':clone(bank),'component_bank_file_sha256':bank_file_hash,
        'fixture_manifest_file_sha256':file_sha256(ROOT/BANK_MANIFEST),'post_edit_contract':contract,
        'preceding_analysis':clone(preceding),'development_seed_reused':True,'evaluation_seeds':[],
        'budget':{'reference_worlds':3,'candidate_slots':4,'native_worlds_upper_bound':7,
            'editor_calibration_sessions':4,'editor_calibration_POSTs_upper_bound':160,
            'editor_generation_POSTs_upper_bound':64,'component_attempts_upper_bound':32,
            'component_timeout_seconds':15.,'proposal_seconds':1800,'calibration_seconds':1200,
            'scientist_HTTP_attempts_per_world':1024,'replace_failed_slots':False},
        'claims':{'publication_ready':False,'original_stopped_study_completed':False,
            'feedback_superiority':False,'new_scientific_truth':False,'independent_search_replication':False}}


def require_plan(root):
    p=read(root/'plan.json')
    if (p['source_commit']!=pinned_revision(ROOT) or p['runtime']!=runtime_binding()
            or p['protocol_sha256']!=file_sha256(ROOT/PROTOCOL)
            or p['fixture_manifest_file_sha256']!=file_sha256(ROOT/BANK_MANIFEST)
            or p['post_edit_contract']!=feedback_for(p['component_bank'],p['source_commit'],p['scientist']['image_id']).contract
            or file_sha256(Path(p['preceding_analysis']['directory'])/'started.json')!=p['preceding_analysis']['start_file_sha256']):
        raise ValueError('code-tested clean source/runtime/bank/preceding analysis changed')
    expected=build_plan(operator=p,source=p['source_commit'],backend=p['backend'],bank=p['component_bank'],
        bank_file_hash=p['component_bank_file_sha256'],preceding=p['preceding_analysis'])
    if expected!={k:v for k,v in p.items() if k!='content_sha256'}:
        raise ValueError('code-tested plan differs from deterministic reconstruction')
    return p


def prepare(args):
    require_environment();source=pinned_revision(ROOT)
    if args.output.exists():raise ValueError('fresh experiment destination required')
    operator=read(args.operator_plan);bank=read(args.bank)
    if not Path(operator['data_cache']).is_dir():raise ValueError('existing offline native corpus required')
    previous=json.loads((args.preceding_analysis/'started.json').read_text())
    if previous['schema']!='scienceutopia.fixed-candidate-evaluation-finish.v1':
        raise ValueError('explicit preceding fixed-evaluation analysis required')
    preceding={'directory':str(args.preceding_analysis.resolve()),
        'start_file_sha256':file_sha256(args.preceding_analysis/'started.json'),
        'scientific_source_commit':previous['scientific_source_commit']}
    p=build_plan(operator=operator,source=source,backend=backend_binding(operator['designer']),
        bank=bank,bank_file_hash=file_sha256(args.bank),preceding=preceding)
    args.output.mkdir(parents=True);save(args.output/'plan.json',p);require_plan(args.output)
    print(json.dumps({'prepared_source':source,'candidate_slots':4,'new_model_calls':0}),flush=True)


def progress(root,stage,active=None):
    write_json_atomic(root/'progress.json',{'stage':stage,'active':active,'observed_utc':utc()},sort_keys=True)
    print(json.dumps({'stage':stage,'active':active}),flush=True)


def selection(root,p,*,frozen_utc=None):
    result={}
    for arm in p['arm_order']:
        c=campaign(root,p,'run-00',arm);c._validate()
        if c.state['pending'] is not None or len(c.state['records'])!=2:raise ValueError('four terminal proposal slots required')
        pool=[o for r in c.state['records'] for o in r['observations'] if o and o['status']=='complete' and o['loss'] is not None]
        best=min((o['loss'] for o in pool),default=None);tied=[o for o in pool if o['loss']==best]
        result[arm]={'loss':best,'all_tied_ids':[o['suggestion_id'] for o in tied],
            'selected_id':tied[0]['suggestion_id'] if tied else None,
            'system':clone(tied[0]['candidate']) if tied else None,'completed_submissions':len(pool)}
    return {'schema':SCHEMA+'.selection','selected':result,'plan_sha256':p['content_sha256'],
        'frozen_utc':utc() if frozen_utc is None else frozen_utc,'baseline_fallback':False,'held_out_evaluation':False}


def run(root):
    require_environment();p=require_plan(root)
    with (root/'writer.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'started.json').exists():raise ValueError('consumed experiment; no redispatch')
        save(root/'started.json',{'schema':SCHEMA+'.start','plan_sha256':p['content_sha256'],
            'pid':os.getpid(),'started_utc':utc()})
        end={'schema':SCHEMA+'.terminal','status':'closed'}
        try:
            progress(root,'waiting-for-preceding-closure')
            closed=wait_analysis(Path(p['preceding_analysis']['directory']))
            save(root/'preceding-closed.json',{'terminal':closed,
                'scope':'closure and exact audit/cost hashes only; evaluation losses are not designer input'})
            p=require_plan(root);p['_output']=str(root)
            for i,slot in enumerate(p['schedule']):
                arm,g=slot['arm'],slot['generation'];c=campaign(root,p,'run-00',arm)
                if c.state['pending'] is not None or len(c.state['records'])!=g:
                    raise ValueError('consumed/pending proposal cannot be redispatched')
                request=c._request(c.state['records'],c._validate(),1)
                directory=root/'search/run-00'/arm.replace(':','--')
                progress(root,'readiness',arm+':g'+str(g))
                cert=readiness(root,p,request=request,numeric=False,target=directory/f'readiness-{g}')
                if i==0:
                    for label in p['reference_order']:
                        progress(root,'references',label)
                        o=observe(root/'references'/label,p,'reference-'+label,p['reference_systems'][label],SEED,'developer-reference')
                        if o['status']!='complete':raise ValueError('reference failed; no later model dispatch')
                # The explicit1800s proposal allowance is passed through a
                # trusted closure, not accepted from candidate JSON.
                def generate(req):
                    return execute(directory/'authoring'/('generation-'+digest(req)),kind='proposal',request=req,
                        provider=p['designer'],source_commit=p['source_commit'],certificate=cert,
                        seconds=1800,inference_lock=root/'inference.lock',post_edit_bank=p['component_bank'])
                factory=LocalRoleBoundNativeFactory(directory/'worlds',Path(p['data_cache']),
                    years=4,corpus_years=4,designer_provider=p['designer'],record_wire=True,record_code=True,
                    maximum_http_attempts=1024,experiment_binding=p['experiment'],inference_lock=root/'inference.lock')
                if (factory.model_digest!=p['scientist']['model_digest']
                        or factory.corpus_sha256!=p['scientist']['corpus_sha256']):
                    raise ValueError('actual researcher/corpus differs before candidate world')
                progress(root,'optimization',arm+':g'+str(g))
                c.advance(simulation_factory=factory,generators={'local-designer':generate},count=1)
                require_plan(root)
            save(root/'selection.json',selection(root,p));progress(root,'closed')
        except BaseException as error:
            end.update(status='stopped',error_type=type(error).__name__,error=str(error))
            progress(root,'stopped',type(error).__name__);raise
        finally:
            end['ended_utc']=utc();save(root/'terminal.json',end)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('stage',choices=('prepare','run'))
    p.add_argument('--output',type=Path,required=True)
    for name in ('operator-plan','bank','preceding-analysis'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();a.output=a.output.resolve()
    if a.stage=='prepare':
        if any(getattr(a,n) is None for n in ('operator_plan','bank','preceding_analysis')):p.error('explicit preparation inputs required')
        prepare(a)
    else:run(a.output)


if __name__=='__main__':main()
