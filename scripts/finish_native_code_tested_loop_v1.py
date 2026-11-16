"""Read-only normal-closure -> two original-source audits -> two cost readouts."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.finish_native_institution_loop_v1 import git_binding,sha,wait_closed
from scripts.run_pre_scale_completion_chain_v1 import process_identity,save

ROOT=Path(__file__).resolve().parents[1]


def run(args,*,plan_schema='scienceutopia.native-code-tested-loop.v1.plan',
        audit_module='scripts.audit_native_code_tested_loop_v1',
        continuation_schema='scienceutopia.code-tested-loop-finish.v1',
        writer_command='scripts.run_native_code_tested_loop_v1 run',
        waiting_stage='await-code-tested-normal-closure',next_steps=None,writer_wait=None):
    root,frozen,out=args.run.resolve(),args.frozen_source.resolve(),args.output.resolve()
    source,scientific=git_binding(ROOT),git_binding(frozen)
    plan=json.loads((root/'plan.json').read_text());start=json.loads((root/'started.json').read_text())
    if (out.exists() or out.is_relative_to(root) or out.is_relative_to(frozen)
            or plan['schema']!=plan_schema
            or plan['source_commit']!=scientific or start['pid']!=args.writer_pid
            or start['plan_sha256']!=plan['content_sha256']):
        raise ValueError('exact original code-tested run/source/writer and fresh output required')
    identity=process_identity(args.writer_pid)
    if identity is not None and writer_command not in identity:
        raise ValueError('writer PID belongs to a different task')
    out.mkdir(parents=True)
    save(out/'started.json',{'schema':continuation_schema,
        'analysis_source_commit':source,'scientific_source_commit':scientific,'writer_pid':args.writer_pid,
        'writer_identity':identity,'plan_file_sha256':sha(root/'plan.json'),
        'started_utc':datetime.now(timezone.utc).isoformat(),'maximum_wait_seconds':86400,
        'new_inference_allowed':False,'retry_failed_stages':False})
    stage=waiting_stage;steps=[]
    try:
        print(json.dumps({'stage':stage,'new_model_calls':0}),flush=True)
        wait = wait_closed if writer_wait is None else writer_wait
        save(out/'writer-absent.json',wait(root,args.writer_pid,identity))
        for kind in ('audit','costs'):
            for i in (1,2):
                stage=kind+'-'+str(i)
                if git_binding(ROOT)!=source or git_binding(frozen)!=scientific:raise ValueError('source changed before analysis')
                argv=([sys.executable,'-m',audit_module,'--run',str(root),
                    '--frozen-source',str(frozen),'--output',str(out/(stage+'.json'))] if kind=='audit' else
                    [sys.executable,'-m','scripts.reports.pre_scale_costs_v1','--run',str(root),
                     '--plan',str(root/'plan.json'),'--audit',str(out/'audit-1.json'),'--output',str(out/(stage+'.json'))])
                save(out/(stage+'.started.json'),{'command':argv})
                with (out/(stage+'.log')).open('x') as log:
                    result=subprocess.run(argv,cwd=ROOT,env={**os.environ,'PYTHONHASHSEED':'42'},
                        stdout=log,stderr=subprocess.STDOUT,timeout=1800,check=False)
                steps.append({'stage':stage,'exit_code':result.returncode})
                save(out/(stage+'.ended.json'),steps[-1])
                print(json.dumps(steps[-1]),flush=True)
                if result.returncode:raise ValueError('read-only stage failed; no retry')
                if git_binding(ROOT)!=source or git_binding(frozen)!=scientific:raise ValueError('source changed during analysis')
            if (out/(kind+'-1.json')).read_bytes()!=(out/(kind+'-2.json')).read_bytes():
                raise ValueError('independent '+kind+' outputs differ')
    except BaseException as error:
        save(out/'ended.json',{'status':'stopped','stage':stage,'steps':steps,
            'error_type':type(error).__name__,'error':str(error),'science_restarted':False})
        raise
    save(out/'ended.json',{'status':'closed','steps':steps,'audit_file_sha256':sha(out/'audit-1.json'),
        'cost_file_sha256':sha(out/'costs-1.json'),'ended_utc':datetime.now(timezone.utc).isoformat(),
        'new_model_calls':0,'new_native_worlds':0,'publication_ready':False,
        'remaining':next_steps if next_steps is not None else 'Interpret all proposals, actual execution feedback and effects; build and review figures; '
            'update the manuscript and determine the important identified main-study result.'})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--writer-pid',type=int,required=True);run(p.parse_args())


if __name__=='__main__':main()
