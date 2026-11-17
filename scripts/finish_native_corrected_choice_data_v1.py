"""After original normal readouts, export paired loss-path or signed-content data.

No rendering, new world, model call, source execution, repair or reselection.
An upstream/child failure stops this continuation, never the original science.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys

from scripts.finish_native_institution_loop_v1 import sha, same_files
from scripts.finish_native_priority_author_outcomes_v1 import read, wait_readouts
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import save

ROOT = Path(__file__).resolve().parents[1]
STUDY = 'scienceutopia.native-corrected-choice-search.v1'
KINDS = {
    'loss-paths': ('scripts.reports.native_corrected_choice_figures_v1',
        'scienceutopia.native-corrected-choice-figures.v1', 'points.csv'),
    'signed-content': ('scripts.reports.native_corrected_choice_content_v1',
        'scienceutopia.native-corrected-choice-content.v1', 'accepted-records.csv')}


def validate_result(kind, result, *, reader, scientific, original):
    if (result['schema'] != KINDS[kind][1] or result['analysis_source_commit'] != reader
            or result['scientific_source_commit'] != scientific or result['new_model_calls'] != 0
            or result['new_native_worlds'] != 0 or result['selection_changed'] is not False
            or result['publication_ready'] is not False):
        raise ValueError('exact source-bound data-only result required')
    if kind == 'loss-paths':
        if (result['original_readout_content_sha256'] != original['content_sha256']
                or len(result['paths']) != 6 or any(len(p['points']) != 4 for p in result['paths'])):
            raise ValueError('complete six original four-step paths required')
    else:
        if (result['new_code_executions'] != 0 or result['loss_changed'] is not False
                or len(result['rows']) != 27
                or result['input_audit_content_sha256'] != original['input_audit_content_sha256']
                or result['plan_content_sha256'] != original['plan_content_sha256']):
            raise ValueError('all27 original rows and unchanged signed-content arithmetic required')
    if result['frozen_selection_content_sha256'] != original['frozen_selection_content_sha256']:
        raise ValueError('literal original frozen selection must remain unchanged')


def run(args):
    kind = args.kind
    if kind not in KINDS:
        raise ValueError('explicit loss-paths or signed-content kind required')
    paths = {k: getattr(args, 'origin_' + k).resolve() for k in ('run', 'source', 'analysis', 'readouts')}
    preceding = args.preceding_source.resolve(); out = args.output.resolve()
    roots = (ROOT.resolve(), preceding, *paths.values())
    if out.exists() or any(child.is_relative_to(root)
            for child in (out, (out / 'report-1').resolve(), (out / 'report-2').resolve()) for root in roots):
        raise ValueError('fresh child outputs outside reader/all original sources and evidence required before waiting')
    source = pinned_revision(ROOT); scientific = pinned_revision(paths['source'])
    preceding_commit = pinned_revision(preceding)
    plan = read(paths['run'] / 'plan.json'); started = read(paths['readouts'] / 'started.json')
    plan_hash = sha(paths['run'] / 'plan.json'); start_hash = sha(paths['readouts'] / 'started.json')
    if (plan['schema'] != STUDY + '.plan' or plan['source_commit'] != scientific
            or started['schema'] != STUDY + '.readout.finish'
            or started['scientific_source_commit'] != scientific
            or started['analysis_source_commit'] != preceding_commit
            or started['plan_file_sha256'] != plan_hash
            or started['preceding_analysis'] != str(paths['analysis'])):
        raise ValueError('exact original plan/source/readout closure binding required')
    out.mkdir(parents=True)
    save(out / 'started.json', {'schema': STUDY + '.data.finish.v1', 'kind': kind, 'pid': os.getpid(),
        'analysis_source_commit': source, 'scientific_source_commit': scientific,
        'preceding_readout_source_commit': preceding_commit, 'preceding_source': str(preceding),
        'origin': {k: str(v) for k, v in paths.items()}, 'plan_file_sha256': plan_hash,
        'preceding_started_file_sha256': start_hash, 'started_utc': datetime.now(timezone.utc).isoformat(),
        'maximum_wait_seconds': 86400, 'new_inference_allowed': False, 'render_allowed': False,
        'retry_failed_stages': False})
    stage, steps = 'await-original-paired-readouts', []
    def stable():
        if ([pinned_revision(p) for p in (ROOT, paths['source'], preceding)]
                != [source, scientific, preceding_commit]
                or sha(paths['run'] / 'plan.json') != plan_hash
                or sha(paths['readouts'] / 'started.json') != start_hash):
            raise ValueError('reader/original source or plan/readout header changed')
    try:
        print('Waiting for original paired readouts; data only, no render/model/native work', flush=True)
        closed = wait_readouts(paths['readouts']); stable()
        original = read(paths['readouts'] / 'report-1/report.json')
        save(out / 'preceding-closed.json', {'ended_file_sha256': sha(paths['readouts'] / 'ended.json'),
            'report_files': closed['report_files'], 'new_model_calls': 0})
        for i in (1, 2):
            stage = 'report-' + str(i)
            command = [sys.executable, '-B', '-m', KINDS[kind][0],
                *[value for k, p in paths.items() for value in ('--origin-' + k, str(p))],
                '--output', str(out / stage)]
            save(out / (stage + '.started.json'), {'command': command, 'render_requested': False})
            with (out / (stage + '.log')).open('x') as log:
                child = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONHASHSEED': '42'},
                    stdout=log, stderr=subprocess.STDOUT, timeout=1800, check=False)
            steps.append({'stage': stage, 'exit_code': child.returncode})
            if child.returncode:
                raise ValueError('original data export failed; no retry or scientific restart')
            stable()
            validate_result(kind, read(out / stage / 'report.json'),
                reader=source, scientific=scientific, original=original)
        files = same_files(out / 'report-1', out / 'report-2')
        if set(files) != {'report.json', 'manifest.json', KINDS[kind][2]}:
            raise ValueError('exact paired data files required; no rendering')
        if wait_readouts(paths['readouts']) != closed:
            raise ValueError('original paired closure changed')
        stable()
    except BaseException as error:
        save(out / 'ended.json', {'status': 'stopped', 'stage': stage, 'steps': steps,
            'error_type': type(error).__name__, 'error': str(error), 'science_restarted': False})
        raise
    save(out / 'ended.json', {'status': 'closed', 'kind': kind, 'steps': steps, 'report_files': files,
        'ended_utc': datetime.now(timezone.utc).isoformat(), 'new_model_calls': 0, 'new_native_worlds': 0,
        'render_requested': False, 'manuscript_updated': False, 'visual_review_complete': False,
        'publication_ready': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'source', 'analysis', 'readouts'):
        parser.add_argument('--origin-' + key, type=Path, required=True)
    for key in ('preceding-source', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--kind', choices=tuple(KINDS), required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
