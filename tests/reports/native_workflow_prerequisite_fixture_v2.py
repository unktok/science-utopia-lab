"""Explicit SCRIPTED predecessor; never a recovered real numeric experiment."""
import json
from pathlib import Path
import subprocess

from scripts import native_workflow_numeric_prerequisite_v2 as guard
from scripts.run_pre_scale_completion_chain_v1 import save as plain_save
from utopia.optimization.native_numeric_designer import save as scientific_save


def scripted_predecessor(root):
    root = Path(root)
    def source(name):
        path = root / name; path.mkdir(parents=True)
        (path / '.gitignore').write_text('outputs/\n')
        (path / 'SCRIPTED_SOURCE.txt').write_text('Scheduling fixture, not numeric scientific source.\n')
        subprocess.run(['git', '-c', 'init.templateDir=', 'init', '-q', str(path)], check=True)
        subprocess.run(['git', '-C', str(path), 'add', '.gitignore', 'SCRIPTED_SOURCE.txt'], check=True)
        subprocess.run(['git', '-C', str(path), '-c', 'core.hooksPath=/dev/null',
            '-c', 'user.name=SCRIPTED', '-c', 'user.email=scripted@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Explicit scheduling fixture'], check=True)
        return path, guard.revision(path)
    dispatcher_source, dispatch_commit = source('dispatcher-source')
    numeric_source, numeric_commit = source('numeric-source')
    directory = dispatcher_source / 'outputs/dispatch'; directory.mkdir(parents=True)
    numeric = root / 'numeric-raw'; numeric.mkdir()
    p = scientific_save(numeric / 'plan.json', {
        'schema': 'scienceutopia.native-parameter-comparator.v1.plan', 'source_commit': numeric_commit,
        'budget': {'native_worlds_upper_bound': 6}, 'origin': {'run': str(root / 'SCRIPTED-planning')},
        'SCRIPTED': 'fixture plan, not evidence of actual scientific closure'})
    start = scientific_save(numeric / 'started.json', {
        'schema': 'scienceutopia.native-parameter-comparator.v1.start',
        'plan_sha256': p['content_sha256'], 'pid': 800000002, 'SCRIPTED': True})
    terminal = scientific_save(numeric / 'terminal.json', {
        'schema': 'scienceutopia.native-parameter-comparator.v1.terminal',
        'status': 'closed', 'stage': 'closed', 'consumed_slots': 6, 'completed_observations': 6,
        'SCRIPTED': 'not a recovered real terminal'})
    plain_save(directory / 'plan.json', {
        'schema': guard.DISPATCH_SCHEMA + '.plan', 'source_commit': dispatch_commit,
        'numeric_source_commit': numeric_commit, 'run': str(numeric), 'frozen_source': str(numeric_source),
        'numeric_plan_content_sha256': p['content_sha256'],
        'numeric_plan_file_sha256': guard.sha(numeric / 'plan.json'),
        'stopped_run': str(root / 'SCRIPTED-stopped'), 'historical_unknown_resolved': False,
        'old_protocol_criteria_relaxed_in_place': False, 'new_numeric_worlds_upper_bound': 6,
        'new_designer_calls': 0, 'SCRIPTED': 'explicit predecessor fixture'})
    plain_save(directory / 'started.json', {'schema': guard.DISPATCH_SCHEMA,
        'source_commit': dispatch_commit, 'numeric_source_commit': numeric_commit,
        'plan_file_sha256': guard.sha(directory / 'plan.json'), 'pid': 800000001,
        'original_study_restarted': False, 'SCRIPTED': True})
    plain_save(directory / 'original-public-plan-check.json', {
        'source_commit': numeric_commit, 'plan_sha256': p['content_sha256']})
    a = {'schema': 'scienceutopia.native-parameter-comparator-audit.v1',
        'source_commit': numeric_commit, 'plan_sha256': p['content_sha256'],
        'source_proof': {'status': 'verified-exact-source-closure',
            'SCRIPTED': 'shape fixture, NOT an actual scientific source proof'},
        'closure': {'started': start, 'terminal': terminal}, 'worlds': [{'SCRIPTED': i} for i in range(6)]}
    for i in (1, 2):
        scientific_save(directory / ('audit-' + str(i) + '.json'), a)
        plain_save(directory / ('costs-' + str(i) + '.json'), {'SCRIPTED': 'equal cost fixture'})
        report = directory / ('report-' + str(i)); report.mkdir()
        for name in ('report.json', 'all-slots.csv', 'numeric-free-paths.png', 'numeric-free-paths.svg'):
            (report / name).write_text('SCRIPTED file equality, not a scientific figure.\n')
    plain_save(directory / 'ended.json', {
        'status': 'closed', 'steps': [{'stage': s, 'exit_code': 0} for s in guard.STAGES],
        'science_restarted': False, 'old_unknown_resolved': False,
        'report_files': guard.same_files(directory / 'report-1', directory / 'report-2'), 'SCRIPTED': True})
    return directory


def rewrite(path, change, *, sealed=False):
    value = json.loads(path.read_text()); value.pop('content_sha256', None); change(value)
    path.unlink()
    (scientific_save if sealed else plain_save)(path, value)
