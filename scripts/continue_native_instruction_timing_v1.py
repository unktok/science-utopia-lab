"""Wait for original fixed evaluation, run three controls, double-audit/read.

Every stage is finite and one-shot. No existing science is restarted or edited.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.finish_native_fixed_evaluation_report_v1 import wait_analysis
from scripts.finish_native_institution_loop_v1 import git_binding, same_files, sha
from scripts.run_pre_scale_search_v1 import ENVIRONMENT, require_environment
from utopia.optimization.native_numeric_designer import checked, save

ROOT=Path(__file__).resolve().parents[1]


def utc():return datetime.now(timezone.utc).isoformat()


def run(args):
    require_environment();source=git_binding(ROOT)
    raw=args.preceding_run.resolve();prior=args.preceding_analysis.resolve()
    previous_source=args.preceding_source.resolve();science=args.assay_source.resolve()
    assay=args.assay_output.resolve();out=args.output.resolve()
    p=checked(json.loads((raw/'plan.json').read_text()));original_hash=sha(raw/'plan.json')
    if (p['schema']!='scienceutopia.native-objective-fixed-evaluation.v1.plan'
            or git_binding(previous_source)!=p['source_commit'] or git_binding(science)!=source
            or out.exists() or assay.exists() or out==assay
            or any(out.is_relative_to(v) or assay.is_relative_to(v) for v in (raw,prior,previous_source))
            or out.is_relative_to(science) or out.is_relative_to(assay) or assay.is_relative_to(out)):
        raise ValueError('fresh separate continuation, assay and exact frozen sources required')
    out.mkdir(parents=True)
    save(out/'started.json',{'schema':'scienceutopia.native-instruction-timing-continuation.v1',
        'source_commit':source,'preceding_source_commit':p['source_commit'],
        'preceding_plan_file_sha256':original_hash,'preceding_run':str(raw),'preceding_analysis':str(prior),
        'assay_source':str(science),'assay_output':str(assay),'started_utc':utc(),
        'maximum_previous_closure_wait_seconds':86400,'maximum_control_process_seconds':28800,
        'maximum_physical_control_worlds':3,'designer_POSTs':0,'retry_failed_stages':False,
        'replace_failed_slots':False,'new_paid_services_allowed':False})
    stage='await-original-fixed-evaluation-audits';steps=[]
    def exact():
        if (git_binding(ROOT)!=source or git_binding(science)!=source
                or git_binding(previous_source)!=p['source_commit'] or sha(raw/'plan.json')!=original_hash):
            raise ValueError('frozen instruction/previous sources or original plan changed')
    def execute(label,argv,cwd,seconds):
        nonlocal stage
        stage=label;exact()
        save(out/(label+'.started.json'),{'command':argv,'cwd':str(cwd),'started_utc':utc(),'timeout_seconds':seconds})
        with (out/(label+'.log')).open('x') as log:
            result=subprocess.run(argv,cwd=cwd,env={**os.environ,**ENVIRONMENT},stdout=log,
                stderr=subprocess.STDOUT,timeout=seconds,check=False)
        step={'stage':label,'exit_code':result.returncode,'ended_utc':utc()};steps.append(step)
        save(out/(label+'.ended.json'),step);print(json.dumps(step),flush=True)
        if result.returncode:raise ValueError('finite one-shot stage failed; no retry: '+label)
        exact()
    try:
        print(json.dumps({'stage':stage,'new_model_calls':0}),flush=True)
        closed=wait_analysis(prior);exact()
        save(out/'preceding-closed.json',{'analysis_end_file_sha256':sha(prior/'ended.json'),
            'audit_file_sha256':closed['audit_file_sha256'],'cost_file_sha256':closed['cost_file_sha256']})
        argv=[sys.executable,'-m','scripts.run_native_instruction_timing_support_v1','prepare',
            '--output',str(assay),'--preceding-run',str(raw),'--preceding-analysis',str(prior),
            '--preceding-source',str(previous_source)]
        execute('prepare',argv,science,1800)
        execute('controls',[sys.executable,'-m','scripts.run_native_instruction_timing_support_v1',
            'run','--output',str(assay)],science,28800)
        start=checked(json.loads((assay/'started.json').read_text()))
        execute('cold-proof',[sys.executable,'-m','scripts.finish_native_instruction_timing_v1',
            '--run',str(assay),'--frozen-source',str(science),'--output',str(out/'audits'),
            '--writer-pid',str(start['pid'])],ROOT,9000)
        wait_analysis(out/'audits');reports={}
        for label,module in [('choices','native_instruction_timing_v1'),
                             ('effects','native_institution_effect_trace_v1'),
                             ('requests','native_observed_request_classes_v1')]:
            for i in (1,2):
                argv=[sys.executable,'-m','scripts.reports.'+module,'--run',str(assay),
                    '--audit-one',str(out/'audits/audit-1.json'),'--audit-two',str(out/'audits/audit-2.json'),
                    '--output',str(out/(label+'-'+str(i)))]
                if label=='effects':argv+=['--frozen-source',str(science),'--scope','instruction-timing-controls']
                execute(label+'-'+str(i),argv,science,1800)
            reports[label]=same_files(out/(label+'-1'),out/(label+'-2'))
        exact()
        if wait_analysis(prior)!=closed:raise ValueError('preceding original audit/cost closure changed')
    except BaseException as error:
        save(out/'ended.json',{'status':'stopped','stage':stage,'steps':steps,
            'error_type':type(error).__name__,'error':str(error),'science_restarted':False,
            'unknown_completions_refilled':False,'ended_utc':utc()});raise
    save(out/'ended.json',{'status':'closed','steps':steps,'report_files':reports,
        'assay_plan_file_sha256':sha(assay/'plan.json'),'ended_utc':utc(),
        'designer_POSTs':0,'policy_selection':False,'visual_review_complete':False,
        'scientific_improvement_claimed':False,'publication_ready':False})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('preceding-run','preceding-analysis','preceding-source','assay-source','assay-output','output'):
        p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())


if __name__=='__main__':main()
