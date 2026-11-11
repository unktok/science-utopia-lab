"""Finite read-only wait -> two original-source audits -> two cost projections.

Never dispatches inference, restarts science, retries a failed stage, generates
an absent terminal, or declares publication readiness. Interpret results next.
"""
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


def utc():return datetime.now(timezone.utc).isoformat()


def run(args):
    root,frozen,out=args.run.resolve(),args.frozen_source.resolve(),args.output.resolve()
    if out.exists() or out.is_relative_to(root) or out.is_relative_to(frozen):
        raise ValueError('fresh analysis output outside scientific source/raw required')
    source,frozen_commit=git_binding(ROOT),git_binding(frozen)
    plan=json.loads((root/'plan.json').read_text());start=json.loads((root/'started.json').read_text())
    if (plan['schema']!='scienceutopia.native-fixed-candidate-evaluation.v1.plan'
            or plan['source_commit']!=frozen_commit or start['pid']!=args.writer_pid
            or start['plan_sha256']!=plan['content_sha256']):
        raise ValueError('exact separate evaluation source/plan/writer required')
    identity=process_identity(args.writer_pid)
    if identity is not None and 'scripts.run_native_fixed_candidate_evaluation_v1 run' not in identity:
        raise ValueError('different process is not the declared fixed-evaluation writer')
    out.mkdir(parents=True)
    save(out/'started.json',{'schema':'scienceutopia.fixed-candidate-evaluation-finish.v1',
        'analysis_source_commit':source,'scientific_source_commit':frozen_commit,
        'run':str(root),'frozen_source':str(frozen),'writer_pid':args.writer_pid,'writer_identity':identity,
        'plan_file_sha256':sha(root/'plan.json'),'started_utc':utc(),
        'maximum_wait_seconds':86400,'new_inference_allowed':False,'retry_failed_stages':False})
    environment={**os.environ,'PYTHONHASHSEED':'42','CUDA_VISIBLE_DEVICES':'',
        'HF_HUB_OFFLINE':'1','HF_DATASETS_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
    stage='await-scientific-closure';steps=[]
    def execute(name,command):
        nonlocal stage
        stage=name
        if git_binding(ROOT)!=source or git_binding(frozen)!=frozen_commit:
            raise ValueError('analysis/scientific source changed before read-only stage')
        save(out/(name+'.started.json'),{'command':command,'cwd':str(ROOT),'started_utc':utc()})
        with (out/(name+'.log')).open('x') as log:
            result=subprocess.run(command,cwd=ROOT,env=environment,stdout=log,
                stderr=subprocess.STDOUT,timeout=1800,check=False)
        step={'stage':name,'exit_code':result.returncode,'ended_utc':utc()};steps.append(step)
        save(out/(name+'.ended.json'),step);print(json.dumps(step),flush=True)
        if result.returncode:raise ValueError('read-only stage failed; no retry: '+name)
        if git_binding(ROOT)!=source or git_binding(frozen)!=frozen_commit:
            raise ValueError('source changed during read-only stage')
    try:
        print(json.dumps({'stage':stage,'writer_pid':args.writer_pid,'new_model_calls':0}),flush=True)
        save(out/'writer-absent.json',wait_closed(root,args.writer_pid,identity))
        for i in (1,2):
            execute('audit-'+str(i),[sys.executable,'-m','scripts.audit_native_fixed_candidate_evaluation_v1',
                '--run',str(root),'--frozen-source',str(frozen),'--output',str(out/f'audit-{i}.json')])
        if (out/'audit-1.json').read_bytes()!=(out/'audit-2.json').read_bytes():
            raise ValueError('independent original-source evaluation audits differ')
        for i in (1,2):
            execute('costs-'+str(i),[sys.executable,'-m','scripts.reports.pre_scale_costs_v1',
                '--run',str(root),'--plan',str(root/'plan.json'),'--audit',str(out/'audit-1.json'),
                '--output',str(out/f'costs-{i}.json')])
        if (out/'costs-1.json').read_bytes()!=(out/'costs-2.json').read_bytes():
            raise ValueError('independent evaluation cost projections differ')
    except BaseException as error:
        save(out/'ended.json',{'status':'stopped','stage':stage,'steps':steps,'ended_utc':utc(),
            'error_type':type(error).__name__,'error':str(error),'science_restarted':False})
        raise
    save(out/'ended.json',{'status':'closed','steps':steps,'ended_utc':utc(),
        'audit_file_sha256':sha(out/'audit-1.json'),'cost_file_sha256':sha(out/'costs-1.json'),
        'new_model_calls':0,'new_native_worlds':0,'publication_ready':False,
        'remaining':'Interpret fixed-policy native comparisons, all failed/missing search slots and costs; '
            'build/review figures; complete model-facing component tests and important identified main study; '
            'update and critically review full manuscript/submission package.'})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','frozen-source','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--writer-pid',type=int,required=True);run(p.parse_args())


if __name__=='__main__':main()
