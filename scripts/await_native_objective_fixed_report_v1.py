"""Wait for the already launched finite evaluation chain, then export twice."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import time

from scripts.finish_native_institution_loop_v1 import git_binding,sha
from scripts.finish_native_objective_fixed_report_v1 import run as finish
from utopia.optimization.native_numeric_designer import checked,save

ROOT=Path(__file__).resolve().parents[1]


def wait_chain(directory,*,clock=time.monotonic,poll=time.sleep,seconds=172800):
    started=clock()
    while True:
        path=directory/'ended.json'
        if path.exists():
            end=json.loads(path.read_text())
            if end['status']!='closed':raise ValueError('evaluation chain stopped; no report or retry')
            return end
        if clock()-started>=seconds:raise ValueError('finite evaluation report wait exhausted')
        poll(15)


def run(args,*,finish_function=None,await_schema='scienceutopia.native-objective-fixed-report-await.v1'):
    out=args.output.resolve();chain=args.continuation.resolve();source=git_binding(ROOT)
    start=checked(json.loads((chain/'started.json').read_text()));run=Path(start['evaluation_output'])
    frozen=Path(start['evaluation_source']);start_hash=sha(chain/'started.json')
    if (out.exists() or out.is_relative_to(chain) or out.is_relative_to(run) or out.is_relative_to(frozen)
            or start['schema']!='scienceutopia.native-objective-evaluation-continuation.v1'
            or git_binding(frozen)!=start['source_commit']):
        raise ValueError('fresh external report and exact existing evaluation continuation required')
    out.mkdir(parents=True);save(out/'started.json',{'schema':await_schema,
        'source_commit':source,'continuation_start_file_sha256':start_hash,'continuation':str(chain),
        'evaluation_source_commit':start['source_commit'],'started_utc':datetime.now(timezone.utc).isoformat(),
        'maximum_wait_seconds':172800,'new_inference_allowed':False,'retry_failed_stages':False})
    stage='await-finite-evaluation-chain'
    try:
        print(json.dumps({'stage':stage,'new_model_calls':0}),flush=True);end=wait_chain(chain)
        if (git_binding(ROOT)!=source or git_binding(frozen)!=start['source_commit']
                or sha(chain/'started.json')!=start_hash or sha(run/'plan.json')!=end['evaluation_plan_file_sha256']):
            raise ValueError('frozen report/evaluation identity changed')
        if checked(json.loads((run/'plan.json').read_text()))['source_commit']!=start['source_commit']:
            raise ValueError('actual evaluation plan has a different source')
        save(out/'evaluation-closed.json',{'ended_file_sha256':sha(chain/'ended.json'),
            'evaluation_plan_file_sha256':end['evaluation_plan_file_sha256']})
        stage='two-independent-exports'
        from types import SimpleNamespace
        callback=finish if finish_function is None else finish_function
        callback(SimpleNamespace(run=run,analysis=chain/'audits',output=out/'exports',
            frozen_source=frozen,scope='fixed-evaluation'))
        if (sha(chain/'started.json')!=start_hash or json.loads((chain/'ended.json').read_text())!=end
                or git_binding(ROOT)!=source or git_binding(frozen)!=start['source_commit']):
            raise ValueError('evaluation or source changed during report')
    except BaseException as error:
        save(out/'ended.json',{'status':'stopped','stage':stage,'error_type':type(error).__name__,
            'error':str(error),'science_restarted':False});raise
    save(out/'ended.json',{'status':'closed','ended_utc':datetime.now(timezone.utc).isoformat(),
        'export_terminal_file_sha256':sha(out/'exports/ended.json'),'new_model_calls':0,'new_native_worlds':0,
        'visual_review_complete':False,'manuscript_updated':False,'publication_ready':False})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('continuation','output'):p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())


if __name__=='__main__':main()
