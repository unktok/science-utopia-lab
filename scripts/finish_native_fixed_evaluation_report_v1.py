"""Finite read-only continuation after the separate audit/cost chain.

Build twice and compare every output byte. No inference, policy selection,
scientific restart, terminal fabrication or publication-ready declaration.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.finish_native_institution_loop_v1 import git_binding,sha,same_files
from utopia.optimization.native_numeric_designer import checked,save

ROOT=Path(__file__).resolve().parents[1]


def wait_analysis(directory,*,clock=time.monotonic,poll=time.sleep,seconds=86400):
    begin=clock()
    while True:
        path=directory/'ended.json'
        if path.exists():
            end=json.loads(path.read_text())
            if end['status']!='closed':raise ValueError('audit/cost chain stopped; no figure build or retry')
            if (sha(directory/'audit-1.json')!=end['audit_file_sha256']
                    or sha(directory/'costs-1.json')!=end['cost_file_sha256']
                    or (directory/'audit-1.json').read_bytes()!=(directory/'audit-2.json').read_bytes()
                    or (directory/'costs-1.json').read_bytes()!=(directory/'costs-2.json').read_bytes()):
                raise ValueError('closed analysis outputs differ from terminal or independent copies')
            return end
        if clock()-begin>=seconds:raise ValueError('finite read-only analysis wait exhausted')
        poll(15)


def run(args):
    out=args.output.resolve();analysis=args.analysis.resolve();source=git_binding(ROOT)
    if (out.exists() or out.is_relative_to(analysis) or out.is_relative_to(args.plan.parent.resolve())):
        raise ValueError('fresh report output outside science and preceding analysis required')
    start=json.loads((analysis/'started.json').read_text());plan=checked(json.loads(args.plan.read_text()))
    if (start['schema']!='scienceutopia.fixed-candidate-evaluation-finish.v1'
            or start['plan_file_sha256']!=sha(args.plan)
            or start['scientific_source_commit']!=plan['source_commit']
            or plan['schema']!='scienceutopia.native-fixed-candidate-evaluation.v1.plan'):
        raise ValueError('exact separate evaluation and original analysis chain required')
    files=[args.plan,args.original_plan,args.origin_audit]
    before={str(p.resolve()):sha(p) for p in files}
    out.mkdir(parents=True)
    save(out/'started.json',{'schema':'scienceutopia.fixed-evaluation-report-finish.v1',
        'analysis_source_commit':source,'scientific_source_commit':plan['source_commit'],
        'started_utc':datetime.now(timezone.utc).isoformat(),'preceding_analysis':str(analysis),
        'maximum_wait_seconds':86400,'inputs':before,'new_inference_allowed':False})
    stage='await-audit-and-cost-closure';steps=[]
    try:
        print(json.dumps({'stage':stage,'new_model_calls':0}),flush=True)
        closed=wait_analysis(analysis)
        if git_binding(ROOT)!=source:raise ValueError('report source changed while awaiting closure')
        save(out/'analysis-closed.json',{'ended_file_sha256':sha(analysis/'ended.json'),
            'audit_file_sha256':closed['audit_file_sha256'],'cost_file_sha256':closed['cost_file_sha256']})
        for i in (1,2):
            stage='report-'+str(i)
            argv=[sys.executable,'-m','scripts.reports.native_fixed_evaluation_v1',
                '--plan',str(args.plan.resolve()),'--audit-one',str(analysis/'audit-1.json'),
                '--audit-two',str(analysis/'audit-2.json'),'--original-plan',str(args.original_plan.resolve()),
                '--origin-audit',str(args.origin_audit.resolve()),'--output',str(out/stage)]
            save(out/(stage+'.started.json'),{'command':argv})
            with (out/(stage+'.log')).open('x') as log:
                response=subprocess.run(argv,cwd=ROOT,env={**os.environ,'PYTHONHASHSEED':'42'},
                    stdout=log,stderr=subprocess.STDOUT,timeout=1800,check=False)
            steps.append({'stage':stage,'exit_code':response.returncode})
            if response.returncode:raise ValueError('read-only report failed; no automatic retry')
            if git_binding(ROOT)!=source:raise ValueError('source changed during report')
        hashes=same_files(out/'report-1',out/'report-2')
        if before!={str(p.resolve()):sha(p) for p in files}:raise ValueError('original inputs changed')
        if wait_analysis(analysis)!=closed:raise ValueError('preceding audit/cost outputs changed')
    except BaseException as error:
        save(out/'ended.json',{'status':'stopped','stage':stage,'steps':steps,
            'error_type':type(error).__name__,'error':str(error),'science_restarted':False})
        raise
    save(out/'ended.json',{'status':'closed','steps':steps,'report_files':hashes,
        'ended_utc':datetime.now(timezone.utc).isoformat(),'new_model_calls':0,'new_native_worlds':0,
        'visual_review_complete':False,'manuscript_updated':False,'publication_ready':False})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('analysis','plan','original-plan','origin-audit','output'):
        p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())


if __name__=='__main__':main()
