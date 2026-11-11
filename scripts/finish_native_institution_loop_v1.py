"""Finite read-only continuation: await the native writer, audit twice, report.

Never starts/restarts science or contacts a model. A stopped or disappeared
writer without normal closure stops this chain. Publication readiness is not
inferred from successful postprocessing.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.run_pre_scale_completion_chain_v1 import process_identity, save


def utc(): return datetime.now(timezone.utc).isoformat()


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_binding(source):
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    status = subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=source,text=True)
    if status.strip(): raise ValueError('clean committed analysis/scientific source required')
    return revision


def wait_closed(run, pid, identity, *, seconds=86400, poll=time.sleep, clock=time.monotonic, observe=process_identity):
    begin = clock()
    while True:
        current = observe(pid)
        terminal = run/'terminal.json'
        if terminal.is_file():
            value = json.loads(terminal.read_text())
            if value.get('status') != 'closed': raise ValueError('science stopped; no fabricated closure or retry')
            if current is None:
                return {'original_writer_absent':True, 'terminal_file_sha256':sha(terminal),
                    'poll_elapsed_seconds':clock()-begin, 'original_process_exit_status':None}
        if current is None: raise ValueError('writer disappeared without normal closure; leave science untouched')
        if current != identity: raise ValueError('writer PID identity changed; no next action')
        if clock()-begin >= seconds: raise ValueError('finite wait exhausted; original writer left untouched')
        poll(15)


def same_files(left, right):
    inventory = lambda root:{str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
    a, b = inventory(left), inventory(right)
    if not a or a != b: raise ValueError('independent deterministic postprocessing outputs differ')
    return a


def run(args):
    analysis = Path(__file__).resolve().parents[1]
    run, frozen, output = args.run.resolve(), args.frozen_source.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(run) or output.is_relative_to(frozen):
        raise ValueError('fresh output outside scientific source/raw required')
    source, frozen_commit = git_binding(analysis), git_binding(frozen)
    plan = json.loads((run/'plan.json').read_text())
    if plan.get('schema') != 'scienceutopia.native-institution-loop.v1.plan' or plan['source_commit'] != frozen_commit:
        raise ValueError('exact original native loop source/plan required')
    start = json.loads((run/'started.json').read_text())
    if start['pid'] != args.writer_pid or start['plan_sha256'] != plan['content_sha256']:
        raise ValueError('explicit original writer/plan required')
    identity = process_identity(args.writer_pid)
    if identity is not None and 'scripts.run_native_institution_loop_v1 run' not in identity:
        raise ValueError('different process is not the declared science writer')
    output.mkdir(parents=True)
    save(output/'started.json', {'schema':'scienceutopia.native-institution-loop-finish.v1',
        'started_utc':utc(), 'pid':os.getpid(), 'writer_pid':args.writer_pid, 'writer_identity':identity,
        'analysis_source_commit':source, 'scientific_source_commit':frozen_commit,
        'run':str(run), 'frozen_source':str(frozen), 'plan_file_sha256':sha(run/'plan.json'),
        'maximum_wait_seconds':86400, 'new_inference_allowed':False, 'retry_failed_stages':False})
    current = 'await-scientific-closure'; steps = []
    environment = {**os.environ, 'PYTHONHASHSEED':'42', 'HF_HUB_OFFLINE':'1',
        'HF_DATASETS_OFFLINE':'1', 'TRANSFORMERS_OFFLINE':'1', 'CUDA_VISIBLE_DEVICES':''}
    def execute(name, command):
        nonlocal current
        current = name
        if git_binding(analysis) != source or git_binding(frozen) != frozen_commit:
            raise ValueError('source changed before read-only analysis')
        save(output/(name+'.started.json'), {'command':command, 'cwd':str(analysis), 'started_utc':utc()})
        with (output/(name+'.log')).open('x') as log:
            result = subprocess.run(command,cwd=analysis,env=environment,stdout=log,
                stderr=subprocess.STDOUT,timeout=1800,check=False)
        step = {'stage':name, 'exit_code':result.returncode, 'ended_utc':utc()}
        save(output/(name+'.ended.json'),step);steps.append(step)
        print(json.dumps(step),flush=True)
        if result.returncode: raise ValueError('postprocessing failed; no automatic retry: '+name)
    try:
        print(json.dumps({'stage':current,'writer_pid':args.writer_pid,'new_model_calls':0}),flush=True)
        save(output/'writer-absent.json', wait_closed(run,args.writer_pid,identity))
        for i in (1,2):
            execute('audit-'+str(i),[sys.executable,'-m','scripts.audit_native_institution_loop_v1',
                '--run',str(run),'--frozen-source',str(frozen),'--output',str(output/f'audit-{i}.json')])
        if (output/'audit-1.json').read_bytes() != (output/'audit-2.json').read_bytes():
            raise ValueError('original-source cold audits differ')
        for i in (1,2):
            execute('costs-'+str(i),[sys.executable,'-m','scripts.reports.pre_scale_costs_v1',
                '--run',str(run),'--plan',str(run/'plan.json'),'--audit',str(output/'audit-1.json'),
                '--output',str(output/f'costs-{i}.json')])
            execute('report-'+str(i),[sys.executable,'-m','scripts.reports.pre_scale_search_v1',
                '--plan',str(run/'plan.json'),'--audit',str(output/'audit-1.json'),
                '--output',str(output/f'report-{i}')])
        if (output/'costs-1.json').read_bytes() != (output/'costs-2.json').read_bytes():
            raise ValueError('independent cost projections differ')
        files = same_files(output/'report-1',output/'report-2')
    except BaseException as error:
        save(output/'ended.json',{'status':'stopped','stage':current,'steps':steps,'ended_utc':utc(),
            'error_type':type(error).__name__,'error':str(error),'science_restarted':False})
        raise
    save(output/'ended.json',{'status':'closed','steps':steps,'ended_utc':utc(),
        'audit_file_sha256':sha(output/'audit-1.json'),'costs_file_sha256':sha(output/'costs-1.json'),
        'report_files':files,'research_goal_complete':False,'new_model_calls':0,'new_native_worlds':0,
        'remaining':'Interpret effects and importance, choose finite main-study contrasts, update/verify manuscripts and readiness judgment.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run','frozen-source','output'): parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--writer-pid',type=int,required=True)
    run(parser.parse_args())


if __name__ == '__main__': main()
