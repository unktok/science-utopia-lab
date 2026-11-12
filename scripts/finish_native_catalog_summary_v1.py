"""Wait for original choice double export; create tables and figures twice."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.finish_native_institution_loop_v1 import git_binding, same_files, sha
from utopia.optimization.native_numeric_designer import checked, save

ROOT = Path(__file__).resolve().parents[1]


def wait_reports(chain, *, seconds=86400, clock=time.monotonic, poll=time.sleep):
    begin = clock()
    while True:
        path = chain / 'ended.json'
        if path.exists():
            end = checked(json.loads(path.read_text()))
            if (end['status'] != 'closed' or end['steps'] != [
                    {'stage': 'report-1', 'exit_code': 0}, {'stage': 'report-2', 'exit_code': 0}]):
                raise ValueError('choice double export stopped; no inference retry')
            if same_files(chain / 'report-1', chain / 'report-2') != end['report_files']:
                raise ValueError('original choice double export differs')
            return end
        if clock() - begin >= seconds: raise ValueError('finite summary wait exhausted; science unchanged')
        poll(15)


def run(args):
    chain, out = args.chain.resolve(), args.output.resolve(); source = git_binding(ROOT)
    start = checked(json.loads((chain / 'started.json').read_text()))
    if (out.exists() or out.is_relative_to(chain) or chain.is_relative_to(out)
            or start['schema'] != 'scienceutopia.native-catalog-choices-finish.v1'
            or start['new_inference_allowed'] is not False):
        raise ValueError('actual original choice continuation and fresh output required')
    start_hash = sha(chain / 'started.json'); out.mkdir(parents=True)
    save(out / 'started.json', {'schema': 'scienceutopia.native-catalog-summary-finish.v1',
        'analysis_source_commit': source, 'scientific_source_commit': start['scientific_source_commit'],
        'original_choice_chain': str(chain), 'original_chain_start_file_sha256': start_hash,
        'started_utc': datetime.now(timezone.utc).isoformat(), 'maximum_wait_seconds': 86400,
        'new_inference_allowed': False, 'retry_failed_stages': False})
    stage, steps = 'await-choice-double-export', []
    try:
        print(json.dumps({'stage': stage, 'new_model_calls': 0}), flush=True)
        closed = wait_reports(chain)
        def exact():
            if git_binding(ROOT) != source or sha(chain / 'started.json') != start_hash:
                raise ValueError('summary source or original choice binding changed')
        exact()
        save(out / 'original-closed.json', {'end_file_sha256': sha(chain / 'ended.json'),
            'report_files': closed['report_files']})
        for i in (1, 2):
            stage = 'summary-' + str(i); exact()
            argv = [sys.executable, '-m', 'scripts.reports.native_catalog_actuation_summary_v1',
                '--one', str(chain / 'report-1/report.json'), '--two', str(chain / 'report-2/report.json'),
                '--output', str(out / stage)]
            save(out / (stage + '.started.json'), {'command': argv, 'timeout_seconds': 1800})
            with (out / (stage + '.log')).open('x') as log:
                result = subprocess.run(argv, cwd=ROOT, env={**os.environ, 'PYTHONHASHSEED': '42'},
                    stdout=log, stderr=subprocess.STDOUT, timeout=1800, check=False)
            steps.append({'stage': stage, 'exit_code': result.returncode})
            print(json.dumps(steps[-1]), flush=True)
            if result.returncode: raise ValueError('one-shot summary export failed; no retry')
        exact(); hashes = same_files(out / 'summary-1', out / 'summary-2')
        if wait_reports(chain, seconds=1) != closed: raise ValueError('original choice closure changed')
    except BaseException as error:
        save(out / 'ended.json', {'status': 'stopped', 'stage': stage, 'steps': steps,
            'error_type': type(error).__name__, 'error': str(error), 'science_restarted': False}); raise
    save(out / 'ended.json', {'status': 'closed', 'steps': steps, 'files': hashes,
        'ended_utc': datetime.now(timezone.utc).isoformat(), 'new_model_calls': 0, 'new_native_worlds': 0,
        'visual_review_complete': False, 'publication_ready': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('chain', 'output'): parser.add_argument('--' + name, type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__': main()
