"""Wait for original paired readouts, then export all eight author/outcome rows twice.

No inference, native/candidate execution, repair, refill, reselection or rendering.
Failures retain their own output and never restart the original scientific chain.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.finish_native_institution_loop_v1 import git_binding, sha, same_files
from utopia.optimization.native_numeric_designer import checked, save
from utopia.utils.data_utils import decode_json

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-priority-author-outcomes-finish.v1'
PRECEDING = 'scienceutopia.native-priority-method-comparison.v1.readout.finish'
REPORT_FILES = {'report.json', 'slots.csv', 'manifest.json'}


def read(path):
    return checked(decode_json(Path(path).read_text(), strict=True, finite_floats=True))


def wait_readouts(directory, *, maximum_seconds=86400, poll_seconds=10):
    deadline = time.monotonic() + maximum_seconds
    while True:
        ended = directory / 'ended.json'
        if ended.exists():
            result = read(ended)
            if (result['status'] != 'closed' or result['new_model_calls'] or result['new_native_worlds']):
                raise ValueError('normal original readout closure required; no automatic retry')
            files = same_files(directory / 'report-1', directory / 'report-2')
            if set(files) != REPORT_FILES or files != result['report_files']:
                raise ValueError('all three matching original readout files required')
            return result
        if time.monotonic() >= deadline: raise TimeoutError('finite original readout wait expired')
        time.sleep(min(poll_seconds, max(0., deadline - time.monotonic())))


def run(args):
    paths = {k: getattr(args, 'origin_' + k).resolve() for k in ('run', 'source', 'analysis', 'readouts')}
    preceding_source = args.preceding_source.resolve(); out = args.output.resolve()
    roots = (ROOT.resolve(), preceding_source, *paths.values())
    # Preflight actual child destinations before waiting, source reads or mkdir.
    if out.exists() or any(child.is_relative_to(root)
            for child in (out, (out / 'report-1').resolve(), (out / 'report-2').resolve()) for root in roots):
        raise ValueError('fresh child outputs outside reader/all original sources and evidence required before waiting')
    source = git_binding(ROOT); scientific = git_binding(paths['source']); preceding = git_binding(preceding_source)
    plan = read(paths['run'] / 'plan.json'); start = read(paths['readouts'] / 'started.json')
    plan_hash = sha(paths['run'] / 'plan.json'); start_hash = sha(paths['readouts'] / 'started.json')
    if (plan['schema'] != 'scienceutopia.native-priority-method-comparison.v1.plan'
            or plan['source_commit'] != scientific or start['schema'] != PRECEDING
            or start['scientific_source_commit'] != scientific or start['analysis_source_commit'] != preceding
            or start['plan_file_sha256'] != plan_hash or start['preceding_analysis'] != str(paths['analysis'])):
        raise ValueError('exact original scientific/readout source and preceding closure paths required')
    out.mkdir(parents=True)
    save(out / 'started.json', {'schema': SCHEMA, 'analysis_source_commit': source,
        'scientific_source_commit': scientific, 'preceding_readout_source_commit': preceding,
        'preceding_source': str(preceding_source), 'origin': {k: str(v) for k, v in paths.items()},
        'plan_file_sha256': plan_hash, 'preceding_started_file_sha256': start_hash,
        'started_utc': datetime.now(timezone.utc).isoformat(), 'maximum_wait_seconds': 86400,
        'new_inference_allowed': False, 'retry_failed_stages': False})
    stage, steps = 'await-original-paired-readouts', []
    try:
        print('Waiting for original paired readouts; no new model/native work', flush=True)
        closed = wait_readouts(paths['readouts'])
        if (git_binding(ROOT) != source or git_binding(preceding_source) != preceding
                or git_binding(paths['source']) != scientific):
            raise ValueError('reader/original source changed while waiting')
        save(out / 'preceding-closed.json', {'ended_file_sha256': sha(paths['readouts'] / 'ended.json'),
            'report_files': closed['report_files'], 'new_model_calls': 0})
        for i in (1, 2):
            stage = 'report-' + str(i)
            command = [sys.executable, '-B', '-m', 'scripts.reports.native_priority_author_outcomes_v1',
                *[value for k, p in paths.items() for value in ('--origin-' + k, str(p))],
                '--output', str(out / stage)]
            save(out / (stage + '.started.json'), {'command': command})
            with (out / (stage + '.log')).open('x') as log:
                result = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONHASHSEED': '42'},
                    stdout=log, stderr=subprocess.STDOUT, timeout=1800, check=False)
            steps.append({'stage': stage, 'exit_code': result.returncode})
            if result.returncode: raise ValueError('original author/outcome export failed; no automatic retry')
            if git_binding(ROOT) != source: raise ValueError('author/outcome reader source changed')
        files = same_files(out / 'report-1', out / 'report-2')
        if set(files) != {'report.json', 'authors.csv', 'manifest.json'}:
            raise ValueError('all three matching author/outcome files required')
        result = read(out / 'report-1/report.json')
        if (len(result['rows']) != 8 or result['new_model_calls'] or result['new_code_executions']
                or result['selection_changed'] or result['analysis_source_commit'] != source
                or result['scientific_source_commit'] != scientific):
            raise ValueError('all eight original source-bound rows, without new science or selection, required')
        if (sha(paths['run'] / 'plan.json') != plan_hash or sha(paths['readouts'] / 'started.json') != start_hash
                or wait_readouts(paths['readouts']) != closed or git_binding(ROOT) != source
                or git_binding(preceding_source) != preceding or git_binding(paths['source']) != scientific):
            raise ValueError('original plan/readouts or sources changed during joined analysis')
    except BaseException as error:
        save(out / 'ended.json', {'status': 'stopped', 'stage': stage, 'steps': steps,
            'error_type': type(error).__name__, 'error': str(error), 'science_restarted': False})
        raise
    save(out / 'ended.json', {'status': 'closed', 'steps': steps, 'report_files': files,
        'ended_utc': datetime.now(timezone.utc).isoformat(), 'new_model_calls': 0, 'new_native_worlds': 0,
        'manuscript_updated': False, 'visual_review_complete': False, 'publication_ready': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'source', 'analysis', 'readouts'):
        parser.add_argument('--origin-' + key, type=Path, required=True)
    for key in ('preceding-source', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__': main()
