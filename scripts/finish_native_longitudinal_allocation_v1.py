"""Wait for paired original construction exports, then read search allocation twice.

No model/world dispatch, scientific restart, selection or source modification.
The separate construction continuation may not have started when this starts.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import time

from scripts.finish_native_code_tested_report_v1 import run as finish
from scripts.finish_native_institution_loop_v1 import git_binding,sha,same_files
from utopia.optimization.native_numeric_designer import checked,save

ROOT=Path(__file__).resolve().parents[1]
SCHEMA='scienceutopia.native-longitudinal-allocation-finish.v1'


def read(path):return checked(json.loads(path.read_text()))


def wait_construction(directory,plan_file_sha256,scientific_source,*,preceding_analysis=None,seconds=86400,
        clock=time.monotonic,poll=time.sleep):
    begin=clock()
    while True:
        start=directory/'started.json';end=directory/'ended.json'
        if start.exists():
            value=read(start)
            if (value['schema']!='scienceutopia.native-longitudinal-construction-finish.v1'
                    or value['plan_file_sha256']!=plan_file_sha256
                    or value['scientific_source_commit']!=scientific_source
                    or (preceding_analysis is not None and value.get('preceding_analysis')!=str(preceding_analysis))):
                raise ValueError('exact original construction continuation required')
        if end.exists():
            if not start.exists():raise ValueError('construction terminal without original start')
            terminal=read(end)
            if terminal['status']!='closed':raise ValueError('construction stopped; no automatic retry')
            files=same_files(directory/'report-1',directory/'report-2')
            if terminal['report_files']!=files:raise ValueError('construction terminal/file mismatch')
            return {'started_file_sha256':sha(start),'ended_file_sha256':sha(end),'report_files':files}
        if clock()-begin>=seconds:raise ValueError('finite construction wait exhausted')
        poll(15)


def run(args):
    root=args.run.resolve();analysis=args.analysis.resolve();construction=args.construction.resolve()
    out=args.output.resolve();waiting=out.with_name(out.name+'-wait');source=git_binding(ROOT)
    plan=read(root/'plan.json');plan_hash=sha(root/'plan.json')
    if (plan['schema']!='scienceutopia.native-longitudinal-comparison.v1.plan'
            or out.exists() or waiting.exists()
            or any(x.is_relative_to(p) for x in (out,waiting) for p in (root,analysis,construction))):
        raise ValueError('original matched plan and fresh external allocation outputs required')
    waiting.mkdir(parents=True)
    save(waiting/'started.json',{'schema':SCHEMA+'.wait','analysis_source_commit':source,
        'scientific_source_commit':plan['source_commit'],'plan_file_sha256':plan_hash,
        'run':str(root),'analysis':str(analysis),'construction':str(construction),'output':str(out),
        'started_utc':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),
        'maximum_wait_seconds':86400,'new_inference_allowed':False,'retry_failed_stages':False})
    stage='await-paired-original-construction'
    try:
        print(json.dumps({'stage':stage,'new_model_calls':0}),flush=True)
        evidence=wait_construction(construction,plan_hash,plan['source_commit'],preceding_analysis=analysis)
        if git_binding(ROOT)!=source or sha(root/'plan.json')!=plan_hash:
            raise ValueError('allocation source or original plan changed while waiting')
        save(waiting/'construction-closed.json',evidence)
        stage='paired-allocation-export'
        finish(args,plan_schema='scienceutopia.native-longitudinal-comparison.v1.plan',
            preceding_schema='scienceutopia.native-longitudinal-comparison-finish.v1',
            continuation_schema=SCHEMA,
            report_module='scripts.reports.native_longitudinal_search_allocation_v1',
            report_extra_arguments=('--construction-one',str(construction/'report-1'),
                '--construction-two',str(construction/'report-2')))
        if (git_binding(ROOT)!=source or sha(root/'plan.json')!=plan_hash
                or wait_construction(construction,plan_hash,plan['source_commit'],preceding_analysis=analysis)!=evidence):
            raise ValueError('allocation source/plan/upstream construction changed')
    except BaseException as error:
        save(waiting/'ended.json',{'status':'stopped','stage':stage,'error_type':type(error).__name__,
            'error':str(error),'science_restarted':False,'new_model_calls':0})
        raise
    save(waiting/'ended.json',{'status':'closed','allocation_terminal_file_sha256':sha(out/'ended.json'),
        'ended_utc':datetime.now(timezone.utc).isoformat(),'new_model_calls':0,'new_native_worlds':0,
        'publication_ready':False})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run','analysis','construction','output'):parser.add_argument('--'+name,type=Path,required=True)
    run(parser.parse_args())
