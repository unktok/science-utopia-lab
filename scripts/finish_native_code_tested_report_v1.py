"""Wait for the separate closed audit/cost chain, export twice, compare bytes."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.finish_native_fixed_evaluation_report_v1 import wait_analysis
from scripts.finish_native_institution_loop_v1 import git_binding,sha,same_files
from utopia.optimization.native_numeric_designer import checked,save

ROOT=Path(__file__).resolve().parents[1]


def run(args,*,plan_schema='scienceutopia.native-code-tested-loop.v1.plan',
        preceding_schema='scienceutopia.code-tested-loop-finish.v1',
        continuation_schema='scienceutopia.code-tested-report-finish.v1',
        report_module='scripts.reports.native_code_tested_loop_v1'):
    root=args.run.resolve();analysis=args.analysis.resolve();out=args.output.resolve();source=git_binding(ROOT)
    plan=checked(json.loads((root/'plan.json').read_text()));start=json.loads((analysis/'started.json').read_text())
    if (out.exists() or out.is_relative_to(root) or out.is_relative_to(analysis)
            or plan['schema']!=plan_schema
            or start['schema']!=preceding_schema
            or start['scientific_source_commit']!=plan['source_commit']
            or start['plan_file_sha256']!=sha(root/'plan.json')):
        raise ValueError('exact original run/analysis and fresh external output required')
    plan_hash=sha(root/'plan.json');out.mkdir(parents=True)
    save(out/'started.json',{'schema':continuation_schema,
        'analysis_source_commit':source,'scientific_source_commit':plan['source_commit'],
        'preceding_analysis':str(analysis),'plan_file_sha256':plan_hash,
        'started_utc':datetime.now(timezone.utc).isoformat(),'maximum_wait_seconds':86400,
        'new_inference_allowed':False,'retry_failed_stages':False})
    stage='await-audit-and-cost-closure';steps=[]
    try:
        print(json.dumps({'stage':stage,'new_model_calls':0}),flush=True)
        closed=wait_analysis(analysis)
        if git_binding(ROOT)!=source:raise ValueError('report source changed while waiting')
        save(out/'analysis-closed.json',{'ended_file_sha256':sha(analysis/'ended.json'),
            'audit_file_sha256':closed['audit_file_sha256'],'cost_file_sha256':closed['cost_file_sha256']})
        for i in (1,2):
            stage='report-'+str(i)
            argv=[sys.executable,'-m',report_module,'--run',str(root),
                '--audit-one',str(analysis/'audit-1.json'),'--audit-two',str(analysis/'audit-2.json'),
                '--output',str(out/stage)]
            save(out/(stage+'.started.json'),{'command':argv})
            with (out/(stage+'.log')).open('x') as log:
                result=subprocess.run(argv,cwd=ROOT,env={**os.environ,'PYTHONHASHSEED':'42'},
                    stdout=log,stderr=subprocess.STDOUT,timeout=1800,check=False)
            steps.append({'stage':stage,'exit_code':result.returncode})
            if result.returncode:raise ValueError('read-only report failed; no automatic retry')
            if git_binding(ROOT)!=source:raise ValueError('report source changed during export')
        hashes=same_files(out/'report-1',out/'report-2')
        if sha(root/'plan.json')!=plan_hash or wait_analysis(analysis)!=closed:
            raise ValueError('scientific plan or independent analysis changed')
    except BaseException as error:
        save(out/'ended.json',{'status':'stopped','stage':stage,'steps':steps,
            'error_type':type(error).__name__,'error':str(error),'science_restarted':False})
        raise
    save(out/'ended.json',{'status':'closed','steps':steps,'report_files':hashes,
        'ended_utc':datetime.now(timezone.utc).isoformat(),'new_model_calls':0,'new_native_worlds':0,
        'visual_review_complete':False,'manuscript_updated':False,'publication_ready':False})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','analysis','output'):parser.add_argument('--'+key,type=Path,required=True)
    run(parser.parse_args())


if __name__=='__main__':main()
