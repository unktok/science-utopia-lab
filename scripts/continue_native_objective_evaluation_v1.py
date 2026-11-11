"""Finite closed-development gate -> fixed-policy evaluation -> double cold proof."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.finish_native_fixed_evaluation_report_v1 import wait_analysis
from scripts.finish_native_institution_loop_v1 import git_binding,sha
from scripts.run_pre_scale_search_v1 import ENVIRONMENT,require_environment
from utopia.optimization.native_numeric_designer import checked,save

ROOT=Path(__file__).resolve().parents[1]


def utc():return datetime.now(timezone.utc).isoformat()


def run(args):
    require_environment();source=git_binding(ROOT);frozen=args.evaluation_source.resolve()
    raw=args.origin_run.resolve();analysis=args.origin_analysis.resolve();out=args.output.resolve();evaluation=args.evaluation_output.resolve()
    original=checked(json.loads((raw/'plan.json').read_text()));prior=json.loads((analysis/'started.json').read_text())
    if (out.exists() or evaluation.exists() or not args.seed_usage_root or out.is_relative_to(raw)
            or evaluation.is_relative_to(raw) or out.is_relative_to(frozen) or out.is_relative_to(analysis)
            or out==evaluation or out.is_relative_to(evaluation) or evaluation.is_relative_to(out)
            or git_binding(frozen)!=source or git_binding(args.origin_source)!=original['source_commit']
            or original['schema']!='scienceutopia.native-objective-instrument-loop.v1.plan'
            or prior['schema']!='scienceutopia.native-objective-instrument-loop-finish.v1'
            or prior['scientific_source_commit']!=original['source_commit']
            or prior['plan_file_sha256']!=sha(raw/'plan.json')):
        raise ValueError('fresh separate evaluation, exact frozen sources and original analysis required')
    plan_hash=sha(raw/'plan.json');out.mkdir(parents=True)
    save(out/'started.json',{'schema':'scienceutopia.native-objective-evaluation-continuation.v1',
        'source_commit':source,'origin_source_commit':original['source_commit'],'origin_plan_file_sha256':plan_hash,
        'origin_run':str(raw),'origin_analysis':str(analysis),'evaluation_source':str(frozen),
        'evaluation_output':str(evaluation),'started_utc':utc(),'maximum_wait_seconds':86400,
        'maximum_evaluation_process_seconds':86400,'maximum_physical_worlds':21,
        'replace_failed_slots':False,'retry_failed_stages':False,'paid_services_allowed':False})
    stage='await-closed-development-audits';steps=[]
    def exact_sources():
        if (git_binding(ROOT)!=source or git_binding(frozen)!=source
                or git_binding(args.origin_source)!=original['source_commit'] or sha(raw/'plan.json')!=plan_hash):
            raise ValueError('frozen continuation/source/original plan changed')
    def execute(label,argv,cwd,seconds):
        nonlocal stage
        stage=label;exact_sources();save(out/(label+'.started.json'),{'command':argv,'cwd':str(cwd),'started_utc':utc(),'timeout_seconds':seconds})
        with (out/(label+'.log')).open('x') as log:
            result=subprocess.run(argv,cwd=cwd,env={**os.environ,**ENVIRONMENT},stdout=log,stderr=subprocess.STDOUT,timeout=seconds,check=False)
        step={'stage':label,'exit_code':result.returncode,'ended_utc':utc()};steps.append(step);save(out/(label+'.ended.json'),step)
        print(json.dumps(step),flush=True)
        if result.returncode:raise ValueError('finite evaluation stage failed; no retry: '+label)
        exact_sources()
    try:
        print(json.dumps({'stage':stage,'new_model_calls':0}),flush=True);closed=wait_analysis(analysis);exact_sources()
        save(out/'development-closed.json',{'ended_file_sha256':sha(analysis/'ended.json'),
            'audit_file_sha256':closed['audit_file_sha256'],'cost_file_sha256':closed['cost_file_sha256']})
        argv=[sys.executable,'-m','scripts.run_native_objective_fixed_evaluation_v1','prepare','--output',str(evaluation),
            '--origin-run',str(raw),'--origin-source',str(args.origin_source.resolve()),
            '--audit-one',str(analysis/'audit-1.json'),'--audit-two',str(analysis/'audit-2.json')]
        for path in args.seed_usage_root:argv+=['--seed-usage-root',str(path.resolve())]
        execute('prepare',argv,frozen,1800)
        execute('evaluation',[sys.executable,'-m','scripts.run_native_objective_fixed_evaluation_v1','run',
            '--output',str(evaluation)],frozen,86400)
        start=checked(json.loads((evaluation/'started.json').read_text()))
        execute('cold-proof',[sys.executable,'-m','scripts.finish_native_objective_fixed_evaluation_v1',
            '--run',str(evaluation),'--frozen-source',str(frozen),'--output',str(out/'audits'),
            '--writer-pid',str(start['pid'])],ROOT,9000)
        final=wait_analysis(out/'audits');exact_sources()
        if wait_analysis(analysis)!=closed:raise ValueError('original development analysis changed')
    except BaseException as error:
        save(out/'ended.json',{'status':'stopped','stage':stage,'steps':steps,'error_type':type(error).__name__,
            'error':str(error),'science_restarted':False,'unknown_completions_refilled':False});raise
    save(out/'ended.json',{'status':'closed','steps':steps,'ended_utc':utc(),
        'evaluation_plan_file_sha256':sha(evaluation/'plan.json'),'audit_file_sha256':final['audit_file_sha256'],
        'cost_file_sha256':final['cost_file_sha256'],'designer_generation_POSTs':0,
        'candidate_reselection':False,'publication_ready':False})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('origin-run','origin-source','origin-analysis','evaluation-source','evaluation-output','output'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--seed-usage-root',type=Path,action='append',required=True);run(p.parse_args())


if __name__=='__main__':main()
