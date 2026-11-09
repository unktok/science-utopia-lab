"""Finite local continuation: wait for M, audit, then readiness/search/evaluate.

This trusted scheduler does not alter either frozen experiment source. It never
retries a scientific stage or launches another role while the original writer
still exists. Its own polling is not scientific inference or experiment time.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ENVIRONMENT={'PYTHONHASHSEED':'42','CUDA_VISIBLE_DEVICES':'','HF_HUB_OFFLINE':'1',
    'HF_DATASETS_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}


def process_identity(pid):
    result=subprocess.run(['/bin/ps','-p',str(pid),'-o','lstart=','-o','command='],
        capture_output=True,text=True,check=False)
    if result.returncode==1 and not result.stdout.strip():return None
    if result.returncode:raise ValueError('cannot observe original writer safely')
    return result.stdout.strip()


def wait_closed(run,pid,identity,*,seconds=21600,poll=time.sleep,clock=time.monotonic,
                observe=process_identity):
    begin=clock()
    while True:
        current=observe(pid)
        if current is None:
            if not (run/'mechanisms-complete.json').is_file():
                raise ValueError('M writer disappeared without complete scientific closure; no next inference')
            return {'original_writer_absent':True,'original_process_exit_status':None,
                'exit_status_scope':'Not the parent of the original writer; do not invent an exit code.',
                'poll_elapsed_seconds':clock()-begin}
        if current!=identity:raise ValueError('original writer PID identity changed; no next inference')
        if clock()-begin>=seconds:raise ValueError('finite M-wait allowance exhausted; original writer left untouched')
        poll(15)


def save(path,value):
    # Trusted orchestration output, outside both immutable scientific records.
    # Exclusive creation prevents overwriting an unknown previous dispatch.
    with path.open('x') as handle:json.dump(value,handle,sort_keys=True,indent=2,allow_nan=False)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('mechanism-run','mechanism-source','search-run','search-source','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--mechanism-pid',type=int,required=True)
    args=p.parse_args()
    for key in ('mechanism_run','mechanism_source','search_run','search_source','output'):
        setattr(args,key,getattr(args,key).resolve())
    if args.output.exists() or any(args.output.is_relative_to(r) for r in (args.mechanism_source,args.search_source)):
        raise ValueError('fresh independent chain destination required')
    if any((args.search_run/(stage+'.started.json')).exists() for stage in ('readiness','search','evaluation')):
        raise ValueError('next scientific stage already consumed; no redispatch')
    script=Path(__file__).resolve();analysis=script.parent
    hashes={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in
        (script,analysis/'audit_pre_scale_information_v1.py',analysis/'audit_pre_scale_search_v1.py')}
    identity=process_identity(args.mechanism_pid)
    if identity is not None and 'scripts.run_pre_scale_pilot_v1 mechanisms' not in identity:
        raise ValueError('explicit original mechanism writer required')
    args.output.mkdir(parents=True)
    start={'schema':'scienceutopia.pre-scale-completion-chain.v1','pid':os.getpid(),
        'started_utc':datetime.now(timezone.utc).isoformat(),'mechanism_pid':args.mechanism_pid,
        'mechanism_process_identity':identity,'analysis_files':hashes,
        'mechanism_source':str(args.mechanism_source),'search_source':str(args.search_source),
        'maximum_wait_seconds':21600,'retry_scientific_stages':False,'maximum_search_evaluation_worlds':58}
    save(args.output/'started.json',start);environment={**os.environ,**ENVIRONMENT}
    current_stage='waiting-for-M';steps=[]
    def execute(name,command,cwd):
        nonlocal current_stage
        current_stage=name
        for path,expected in hashes.items():
            if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=expected:
                raise ValueError('analysis/scheduler source changed; stop before dispatch')
        save(args.output/(name+'.started.json'),{'command':command,'cwd':str(cwd),
            'started_utc':datetime.now(timezone.utc).isoformat()})
        with (args.output/(name+'.log')).open('x') as log:
            result=subprocess.run(command,cwd=cwd,env=environment,stdout=log,stderr=subprocess.STDOUT,check=False)
        record={'stage':name,'exit_code':result.returncode,'ended_utc':datetime.now(timezone.utc).isoformat()}
        save(args.output/(name+'.ended.json'),record);steps.append(record)
        print(json.dumps(record),flush=True)
        if result.returncode:raise ValueError('finite stage failed; no automatic retry: '+name)
    try:
        waited=wait_closed(args.mechanism_run,args.mechanism_pid,identity)
        save(args.output/'M-writer-absent.json',waited)
        print(json.dumps({'stage':'M-writer-absent',**waited}),flush=True)
        for i in (1,2):
            execute('M-audit-'+str(i),[sys.executable,str(analysis/'audit_pre_scale_information_v1.py'),
                '--run',str(args.mechanism_run),'--frozen-source',str(args.mechanism_source),
                '--output',str(args.output/('M-audit-'+str(i)+'.json'))],args.search_source)
        if (args.output/'M-audit-1.json').read_bytes()!=(args.output/'M-audit-2.json').read_bytes():
            raise ValueError('independent read-only M audits differ; no next inference')
        for stage in ('readiness','search','evaluation'):
            execute('O-E-'+stage,[sys.executable,'-m','scripts.run_pre_scale_search_v1',stage,
                '--output',str(args.search_run)],args.search_source)
        for i in (1,2):
            execute('O-E-audit-'+str(i),[sys.executable,str(analysis/'audit_pre_scale_search_v1.py'),
                '--run',str(args.search_run),'--frozen-source',str(args.search_source),
                '--output',str(args.output/('O-E-audit-'+str(i)+'.json'))],args.search_source)
        if (args.output/'O-E-audit-1.json').read_bytes()!=(args.output/'O-E-audit-2.json').read_bytes():
            raise ValueError('independent read-only O/E audits differ')
    except BaseException as error:
        save(args.output/'ended.json',{'status':'stopped','stage':current_stage,'steps':steps,
            'error_type':type(error).__name__,'error':str(error),'ended_utc':datetime.now(timezone.utc).isoformat()})
        raise
    save(args.output/'ended.json',{'status':'closed','steps':steps,
        'ended_utc':datetime.now(timezone.utc).isoformat(),'research_goal_complete':False,
        'remaining':'Interpret audited results and refresh actual UI, figures, manuscript and final evidence ledger.'})


if __name__=='__main__':main()
