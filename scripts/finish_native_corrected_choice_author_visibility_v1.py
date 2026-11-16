"""After exact paired author closure, export all8 visibility traces twice.

No inference, generated-code execution, restart, retry, loss/selection edits or
rendering. Output and source preflight precedes waiting or directory creation.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys

from scripts.finish_native_institution_loop_v1 import git_binding, sha, same_files
from scripts.finish_native_priority_author_outcomes_v1 import wait_readouts, read

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-corrected-choice-author-visibility-finish.v1'
PRECEDING = 'scienceutopia.native-corrected-choice-author-outcomes-finish.v1'
AUTHOR_FILES = {'report.json', 'authors.csv', 'manifest.json'}
FILES = {'report.json', 'steps.csv', 'manifest.json'}


def run(args):
    raw, author, author_source, science, out = (getattr(args, key).resolve()
        for key in ('run', 'author_outcomes', 'author_source', 'scientific_source', 'output'))
    roots = (ROOT.resolve(), raw, author, author_source, science)
    def external(extra=()):
        if out.exists() or any(child.is_relative_to(root) for root in (*roots, *extra)
                for child in (out, (out / 'report-1').resolve(), (out / 'report-2').resolve())):
            raise ValueError('fresh child outputs outside all source/evidence required before waiting')
    external()
    source, author_head, scientific = git_binding(ROOT), git_binding(author_source), git_binding(science)
    start = read(author / 'started.json'); plan = read(raw / 'plan.json')
    if set(start['origin']) != {'run', 'source', 'analysis', 'readouts'}:
        raise ValueError('exact original origin paths required before waiting')
    origin = {key: Path(value).resolve() for key, value in start['origin'].items()}
    external(tuple(origin.values()))
    plan_hash, header_hash = sha(raw / 'plan.json'), sha(author / 'started.json')
    if (start['schema'] != PRECEDING or start['analysis_source_commit'] != author_head
            or start['scientific_source_commit'] != scientific or start['plan_file_sha256'] != plan_hash
            or start['new_inference_allowed'] or start['retry_failed_stages']
            or origin['run'] != raw or origin['source'] != science
            or plan['schema'] != 'scienceutopia.native-corrected-choice-search.v1.plan'
            or plan['source_commit'] != scientific):
        raise ValueError('exact corrected author/source/plan continuation required before waiting')
    out.mkdir(parents=True)
    from utopia.optimization.native_numeric_designer import save
    save(out / 'started.json', {'schema': SCHEMA, 'analysis_source_commit': source,
        'scientific_source_commit': scientific, 'author_source_commit': author_head,
        'author_outcomes': str(author), 'plan_file_sha256': plan_hash,
        'author_started_file_sha256': header_hash, 'started_utc': datetime.now(timezone.utc).isoformat(),
        'maximum_wait_seconds': 86400, 'new_inference_allowed': False, 'retry_failed_stages': False})
    stage, steps = 'await-original-paired-authors', []
    def unchanged():
        if (git_binding(ROOT) != source or git_binding(author_source) != author_head
                or git_binding(science) != scientific or sha(raw / 'plan.json') != plan_hash
                or sha(author / 'started.json') != header_hash):
            raise ValueError('reader/author/scientific source or exact original header changed')
    try:
        print('Waiting for original paired author/outcome exports; no new model/native work', flush=True)
        closed = wait_readouts(author, report_files=AUTHOR_FILES)
        unchanged(); save(out / 'preceding-closed.json', {'ended_file_sha256': sha(author / 'ended.json'),
            'report_files': closed['report_files'], 'new_model_calls': 0})
        for index in (1, 2):
            stage = 'report-' + str(index)
            command = [sys.executable, '-B', '-m', 'scripts.reports.export_native_corrected_choice_author_visibility_v1',
                '--run', str(raw), '--author-outcomes', str(author), '--author-source', str(author_source),
                '--scientific-source', str(science), '--output', str(out / stage)]
            save(out / (stage + '.started.json'), {'command': command})
            with (out / (stage + '.log')).open('x') as log:
                result = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONHASHSEED': '42'},
                    stdout=log, stderr=subprocess.STDOUT, timeout=1800, check=False)
            steps.append({'stage': stage, 'exit_code': result.returncode})
            if result.returncode: raise ValueError('visibility export failed; no automatic retry')
            unchanged()
        files = same_files(out / 'report-1', out / 'report-2')
        report = read(out / 'report-1/report.json')
        if (set(files) != FILES or report['schema'] != 'scienceutopia.native-corrected-choice-author-visibility.v1.all8-join'
                or len(report['rows']) != 8 or report['analysis_source_commit'] != source
                or report['scientific_source_commit'] != scientific or report['new_model_calls']
                or report['new_generated_code_executions'] or report['scientific_losses_rewritten']):
            raise ValueError('all8 exact original cells and three matching no-new-science files required')
        unchanged()
        if wait_readouts(author, report_files=AUTHOR_FILES) != closed:
            raise ValueError('original author exports changed during visibility export')
    except BaseException as error:
        save(out / 'ended.json', {'status': 'stopped', 'stage': stage, 'steps': steps,
            'error_type': type(error).__name__, 'error': str(error), 'science_restarted': False})
        raise
    save(out / 'ended.json', {'status': 'closed', 'steps': steps, 'report_files': files,
        'ended_utc': datetime.now(timezone.utc).isoformat(), 'new_model_calls': 0, 'new_native_worlds': 0,
        'scientific_losses_rewritten': False, 'manuscript_updated': False, 'publication_ready': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'author-outcomes', 'author-source', 'scientific-source', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    run(parser.parse_args())
