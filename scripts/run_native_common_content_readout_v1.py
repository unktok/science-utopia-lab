"""Finite real-backend check + all historical contents, no new native world."""
import argparse
from datetime import datetime,timezone
import fcntl
import json
from pathlib import Path
import time

from scripts.finish_native_institution_loop_v1 import git_binding,sha,same_files
from scripts.run_pre_scale_search_v1 import require_environment
from utopia.optimization.common_content_observer import CommonContentObserver,LocalObserverBackend,make_contract,content,request_for
from utopia.optimization.native_designer_preflight import backend_binding
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system.design_patch import clone,digest

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='scienceutopia.native-common-content-readout.v1'
PROTOCOL='research/protocols/campaigns/native-common-content-readout-v1.md'
INPUT_SHA='498e84d713ab9ba4e23636a98618d58e9e97ab8741c6350c0f0e44f590bca419'


def read(path):return checked(json.loads(Path(path).read_text()))


def content_set(inputs):
    checked(inputs)
    if (inputs['scientific_source_commit']!='62388a74d071a3a4fdc8cc309c2807422f96223f'
            or len(inputs['worlds'])!=44 or len(inputs['skipped_partial_worlds'])!=5
            or len(inputs['accepted_decisions'])!=263):
        raise ValueError('exact predeclared historical staging required')
    values={}
    for row in inputs['accepted_decisions']:
        item=content(row['content']);values[digest(item)]=item
    if len(values)!=76:raise ValueError('all76 original unique contents required')
    return {k:values[k] for k in sorted(values)}


def wait_report(directory,*,clock=time.monotonic,poll=time.sleep):
    begin=clock()
    while True:
        if (directory/'ended.json').exists():
            terminal=read(directory/'ended.json')
            if terminal['status']!='closed':raise ValueError('preceding report stopped; no observer dispatch')
            if same_files(directory/'report-1',directory/'report-2')!=terminal['report_files']:
                raise ValueError('preceding reports differ from closed terminal')
            return terminal
        if clock()-begin>=86400:raise ValueError('finite preceding-report wait exhausted')
        poll(15)


def build_plan(*,source,inputs_path,preceding_report,inference_lock,provider,backend):
    if sha(inputs_path)!=INPUT_SHA:raise ValueError('historical raw contents differ from retained preparation')
    inputs=read(inputs_path);values=content_set(inputs);start=read(preceding_report/'started.json')
    if start['schema']!='scienceutopia.code-tested-report-finish.v1' or start['scientific_source_commit']!='93076b477b023a6bcb78cac5568fcbe795fa9a52':
        raise ValueError('exact preceding current code-tested report required')
    contract=make_contract(source_commit=source,provider=provider,backend=backend,maximum_posts=228,critics=3)
    for value in values.values():
        for critic in range(3):request_for(contract,value,critic)
    return {'schema':SCHEMA+'.plan','source_commit':source,'protocol':PROTOCOL,'protocol_sha256':sha(ROOT/PROTOCOL),
        'inputs_path':str(inputs_path.resolve()),'inputs_file_sha256':INPUT_SHA,'inputs_content_sha256':inputs['content_sha256'],
        'preceding_report':str(preceding_report.resolve()),'preceding_start_file_sha256':sha(preceding_report/'started.json'),
        'inference_lock':str(inference_lock.resolve()),'contract':contract,'content_order':list(values),
        'initial_interface_check_content_hashes':list(values)[:3],'maximum_posts':228,
        'new_native_worlds':0,'retrospective_development_only':True,'reselect_policies':False}


def prepare(args):
    require_environment();source=git_binding(ROOT)
    if args.output.exists():raise ValueError('fresh observer output required')
    from utopia.optimization.native_scientist_load_v38 import SCIENTIST_DIGEST
    provider={'model':'qwen3:8b','model_digest':SCIENTIST_DIGEST}
    plan=build_plan(source=source,inputs_path=args.inputs,preceding_report=args.preceding_report,
        inference_lock=args.inference_lock,provider=provider,backend=backend_binding(provider))
    if git_binding(ROOT)!=source:raise ValueError('source changed during preparation')
    args.output.mkdir(parents=True);save(args.output/'plan.json',plan)
    print(json.dumps({'prepared_source':source,'contents':76,'maximum_posts':228,'new_model_calls':0}))


def require_plan(root):
    plan=read(root/'plan.json')
    expected=build_plan(source=git_binding(ROOT),inputs_path=Path(plan['inputs_path']),
        preceding_report=Path(plan['preceding_report']),inference_lock=Path(plan['inference_lock']),
        provider=plan['contract']['provider'],backend=plan['contract']['backend'])
    if expected!={k:v for k,v in plan.items() if k!='content_sha256'}:raise ValueError('observer plan/source/input reconstruction differs')
    return plan


def run(root):
    require_environment();plan=require_plan(root)
    with (root/'writer.lock').open('a') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'started.json').exists():raise ValueError('consumed observer run; no redispatch')
        save(root/'started.json',{'schema':SCHEMA+'.start','plan_sha256':plan['content_sha256'],
            'started_utc':datetime.now(timezone.utc).isoformat()})
        stage='await-code-tested-report';status='stopped';failure={}
        try:
            print(json.dumps({'stage':stage,'new_model_calls':0}),flush=True)
            prior=wait_report(Path(plan['preceding_report']));save(root/'preceding-closed.json',{'terminal':prior})
            plan=require_plan(root);inputs=read(plan['inputs_path']);values=content_set(inputs)
            backend=LocalObserverBackend(inference_lock=plan['inference_lock'])
            observer=CommonContentObserver(root/'observer',plan['contract'],backend=backend);ratings={}
            stage='initial-real-interface-check'
            for index,(key,value) in enumerate(values.items()):
                rating=observer.rate(value);ratings[key]=rating
                save(root/'ratings'/(key+'.json'),{'paper_content_sha256':key,'rating':rating})
                print(json.dumps({'stage':stage,'content_index':index,'status':rating['status']}),flush=True)
                if index<3 and rating['status']!='measured':raise ValueError('initial real interface check failed; no refill')
                if index==2:
                    save(root/'interface-check.json',{'contents':list(values)[:3],'ratings':clone(ratings),
                        'all_literal_panels_complete':True,'maximum_check_POSTs':9,'desired_scores_required':False})
                    stage='all-historical-contents'
            require_plan(root)
            save(root/'ratings.json',{'schema':SCHEMA+'.ratings','plan_sha256':plan['content_sha256'],
                'ratings':ratings,'native_worlds':clone(inputs['worlds']),
                'accepted_decisions':[{k:clone(v) for k,v in row.items() if k!='content'} |
                    {'content_sha256':digest(content(row['content']))} for row in inputs['accepted_decisions']],
                'missing_imputed':False,'new_native_worlds':0})
            cold=checked(observer.audit())
            retained=save(root/'audit.json',{k:v for k,v in cold.items() if k!='content_sha256'})
            if retained!=cold:raise ValueError('retained observer audit differs from cold result')
            require_plan(root);status='closed';stage='closed'
        except BaseException as error:
            failure={'error_type':type(error).__name__,'error':str(error)}
            raise
        finally:
            save(root/'terminal.json',{'schema':SCHEMA+'.terminal','status':status,'stage':stage,
                'ended_utc':datetime.now(timezone.utc).isoformat(),'new_native_worlds':0,'publication_ready':False,**failure})


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=('prepare','run'))
    parser.add_argument('--output',type=Path,required=True)
    for name in ('inputs','preceding-report','inference-lock'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args()
    if args.stage=='prepare':
        if any(getattr(args,n) is None for n in ('inputs','preceding_report','inference_lock')):parser.error('explicit preparation inputs required')
        prepare(args)
    else:run(args.output)


if __name__=='__main__':main()
