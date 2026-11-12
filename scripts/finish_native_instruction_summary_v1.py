"""Wait once for the closed three-control chain, then export its figures twice."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.finish_native_fixed_evaluation_report_v1 import wait_analysis
from scripts.finish_native_institution_loop_v1 import git_binding, same_files, sha
from utopia.optimization.native_numeric_designer import checked, save

ROOT = Path(__file__).resolve().parents[1]
STAGES = ['prepare', 'controls', 'cold-proof', 'choices-1', 'choices-2',
          'effects-1', 'effects-2', 'requests-1', 'requests-2']


def wait_reports(chain, *, seconds=86400, clock=time.monotonic, poll=time.sleep):
    begin = clock()
    while True:
        path = chain/'ended.json'
        if path.exists():
            end = checked(json.loads(path.read_text()))
            if end['status'] != 'closed':
                raise ValueError('control chain stopped; no summaries or scientific retry')
            if ([s['stage'] for s in end['steps']] != STAGES
                    or any(s['exit_code'] != 0 for s in end['steps'])
                    or end['designer_POSTs'] != 0 or end['policy_selection'] is not False):
                raise ValueError('complete literal finite control chain required')
            for label in ('choices', 'effects', 'requests'):
                if same_files(chain/(label+'-1'), chain/(label+'-2')) != end['report_files'][label]:
                    raise ValueError('original double exports differ from chain closure')
            wait_analysis(chain/'audits', seconds=1)
            return end
        if clock()-begin >= seconds:
            raise ValueError('finite summary wait exhausted; science left untouched')
        poll(15)


def run(args):
    chain, output = args.chain.resolve(), args.output.resolve()
    source = git_binding(ROOT)
    started = checked(json.loads((chain/'started.json').read_text()))
    science = Path(started['assay_source']).resolve()
    raw = Path(started['assay_output']).resolve()
    if (started['schema'] != 'scienceutopia.native-instruction-timing-continuation.v1'
            or git_binding(science) != started['source_commit']
            or output.exists() or any(output.is_relative_to(p) or p.is_relative_to(output)
                                     for p in (chain, raw, science))):
        raise ValueError('literal existing control chain and fresh separate summary output required')
    original = sha(chain/'started.json')
    output.mkdir(parents=True)
    save(output/'started.json', {'schema': 'scienceutopia.native-instruction-summary-finish.v1',
        'analysis_source_commit': source, 'scientific_source_commit': started['source_commit'],
        'original_chain': str(chain), 'original_chain_start_file_sha256': original,
        'started_utc': datetime.now(timezone.utc).isoformat(), 'maximum_wait_seconds': 86400,
        'maximum_each_export_seconds': 1800, 'new_inference_allowed': False,
        'retry_failed_stages': False})
    stage, steps = 'await-closed-control-exports', []
    def exact():
        if (git_binding(ROOT) != source or git_binding(science) != started['source_commit']
                or sha(chain/'started.json') != original):
            raise ValueError('frozen reader/science/chain binding changed')
    try:
        print(json.dumps({'stage': stage, 'new_model_calls': 0}), flush=True)
        closed = wait_reports(chain); exact()
        if sha(raw/'plan.json') != closed['assay_plan_file_sha256']:
            raise ValueError('original control plan differs from closure')
        save(output/'original-closed.json', {'end_file_sha256': sha(chain/'ended.json'),
            'assay_plan_file_sha256': closed['assay_plan_file_sha256'],
            'choice_report_file_sha256': sha(chain/'choices-1/report.json')})
        for i in (1, 2):
            stage = 'summary-'+str(i); exact()
            argv = [sys.executable, '-m', 'scripts.reports.native_instruction_timing_summary_v1',
                '--one', str(chain/'choices-1/report.json'), '--two', str(chain/'choices-2/report.json'),
                '--output', str(output/stage)]
            save(output/(stage+'.started.json'), {'command': argv, 'timeout_seconds': 1800})
            with (output/(stage+'.log')).open('x') as log:
                response = subprocess.run(argv, cwd=ROOT, env={**os.environ, 'PYTHONHASHSEED': '42'},
                    stdout=log, stderr=subprocess.STDOUT, timeout=1800, check=False)
            steps.append({'stage': stage, 'exit_code': response.returncode})
            print(json.dumps(steps[-1]), flush=True)
            if response.returncode:
                raise ValueError('one-shot summary failed; no automatic retry')
        files = same_files(output/'summary-1', output/'summary-2'); exact()
        if wait_reports(chain, seconds=1) != closed:
            raise ValueError('original closed control reports changed')
    except BaseException as error:
        save(output/'ended.json', {'status': 'stopped', 'stage': stage, 'steps': steps,
            'error_type': type(error).__name__, 'error': str(error), 'science_restarted': False})
        raise
    save(output/'ended.json', {'status': 'closed', 'steps': steps, 'files': files,
        'ended_utc': datetime.now(timezone.utc).isoformat(), 'new_model_calls': 0,
        'new_native_worlds': 0, 'policy_selection': False,
        'visual_review_complete': False, 'publication_ready': False})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('chain', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    run(p.parse_args())


if __name__ == '__main__':
    main()
