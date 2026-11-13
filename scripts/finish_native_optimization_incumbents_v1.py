"""Wait for the exact original double readout, then project K/O twice read-only."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.chain_native_parameter_comparator_v1 import wait_analysis
from scripts.finish_native_institution_loop_v1 import git_binding,sha,same_files,utc
from scripts.run_pre_scale_completion_chain_v1 import process_identity,save,ENVIRONMENT
from utopia.optimization.native_numeric_designer import checked

ROOT=Path(__file__).resolve().parents[1]
KINDS={
    'presentation-scores':{'producer':'scripts.finish_native_parent_presentation_report_v1','extra':'--kind scores',
        'start_schema':'scienceutopia.native-parent-presentation-scores-finish.v1',
        'report_schema':'scienceutopia.native-parent-presentation-report.v1','steps':2},
    'numeric-chain':{'producer':'scripts.chain_native_parameter_comparator_v1','extra':'',
        'start_schema':'scienceutopia.native-parameter-comparator-chain.v1',
        'report_schema':'scienceutopia.native-parameter-comparator-report.v1','steps':7}}


def start_binding(args):
    kind=KINDS[args.producer_kind]
    start=json.loads((args.original_output/'started.json').read_text())
    if args.producer_kind=='presentation-scores':checked(start)
    scientific=git_binding(args.scientific_source);producer=git_binding(args.producer_source)
    key='numeric_source_commit' if args.producer_kind=='numeric-chain' else 'scientific_source_commit'
    if (start['schema']!=kind['start_schema'] or start['analysis_source_commit']!=producer or start[key]!=scientific):
        raise ValueError('exact original producer/scientific source and start receipt required')
    return kind,start,scientific,producer


def run(args,*,observe=process_identity,wait=wait_analysis,command=subprocess.run):
    for key in ('original_output','scientific_source','producer_source','output'):
        setattr(args,key,Path(getattr(args,key)).resolve())
    if args.producer_kind not in KINDS:raise ValueError('explicit supported original readout kind required')
    if (args.output.exists() or any(args.output.is_relative_to(p) for p in
            (args.original_output,args.scientific_source,args.producer_source))):
        raise ValueError('fresh independent incumbent projection output required')
    kind,start,scientific,producer=start_binding(args);source=git_binding(ROOT)
    identity=observe(args.producer_pid)
    if identity is not None and (kind['producer'] not in identity or kind['extra'] not in identity):
        raise ValueError('original producer PID belongs to a different task')
    args.output.mkdir(parents=True)
    save(args.output/'started.json',{'schema':'scienceutopia.native-optimization-incumbents-finish.v1',
        'pid':os.getpid(),'analysis_source_commit':source,'scientific_source_commit':scientific,
        'producer_source_commit':producer,'producer_kind':args.producer_kind,'producer_pid':args.producer_pid,
        'producer_identity':identity,'original_start_file_sha256':sha(args.original_output/'started.json'),
        'started_utc':utc(),'maximum_wait_seconds':86400,'new_inference_allowed':False,'automatic_retries':False})
    stage,steps='wait-original-readout',[]
    def sources():
        if (git_binding(ROOT)!=source or git_binding(args.scientific_source)!=scientific
                or git_binding(args.producer_source)!=producer
                or json.loads((args.original_output/'started.json').read_text())!=start):
            raise ValueError('original/analysis source or producer start changed')
    try:
        print(json.dumps({'stage':stage,'new_model_calls':0}),flush=True)
        save(args.output/'producer-absent.json',wait(args.original_output,args.producer_pid,identity,observe=observe))
        sources();end=json.loads((args.original_output/'ended.json').read_text())
        if args.producer_kind=='presentation-scores':checked(end)
        if (end['status']!='closed' or len(end['steps'])!=kind['steps']
                or any(s['exit_code']!=0 for s in end['steps'])
                or end['report_files']!=same_files(args.original_output/'report-1',args.original_output/'report-2')):
            raise ValueError('normal matching complete original report exports required')
        inputs=[args.original_output/('report-'+str(i)+'/report.json') for i in (1,2)]
        for path in inputs:
            report=checked(json.loads(path.read_text()))
            if report['schema']!=kind['report_schema'] or report['source_commit']!=scientific:
                raise ValueError('original report source/type differs')
        save(args.output/'original-verified.json',{'ended_file_sha256':sha(args.original_output/'ended.json'),
            'report_files':{str(p):sha(p) for p in inputs},'raw_audit_reexecuted':False})
        for i in (1,2):
            sources();stage='report-'+str(i)
            cmd=[sys.executable,'-m','scripts.reports.native_optimization_incumbents_v1','--report-one',str(inputs[0]),
                '--report-two',str(inputs[1]),'--output',str(args.output/stage)]
            save(args.output/(stage+'.started.json'),{'command':cmd,'cwd':str(ROOT)})
            with (args.output/(stage+'.log')).open('x') as log:
                result=command(cmd,cwd=ROOT,env={**os.environ,**ENVIRONMENT},stdout=log,
                    stderr=subprocess.STDOUT,timeout=1800,check=False)
            steps.append({'stage':stage,'exit_code':result.returncode});save(args.output/(stage+'.ended.json'),steps[-1])
            if result.returncode:raise ValueError('read-only projection failed; no retry')
        sources();files=same_files(args.output/'report-1',args.output/'report-2')
    except BaseException as error:
        save(args.output/'ended.json',{'status':'stopped','stage':stage,'steps':steps,'error_type':type(error).__name__,
            'error':str(error),'ended_utc':utc(),'science_restarted':False});raise
    save(args.output/'ended.json',{'status':'closed','steps':steps,'report_files':files,'ended_utc':utc(),
        'new_model_calls':0,'new_native_worlds':0,'original_selection_changed':False,'publication_ready':False})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('original-output','scientific-source','producer-source','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--producer-pid',type=int,required=True)
    parser.add_argument('--producer-kind',choices=tuple(KINDS),required=True);run(parser.parse_args())


if __name__=='__main__':main()
