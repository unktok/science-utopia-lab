"""SCRIPTED continuation metadata/child orchestration, not native/source proof."""
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from scripts import finish_native_priority_author_outcomes_v1 as r
from utopia.optimization.native_numeric_designer import save
from utopia.utils.data_utils import write_json_atomic


def fixture(tmp_path, monkeypatch, *, closed=True, corrected=False):
    roots = {k: tmp_path / k for k in ('run', 'source', 'analysis', 'readouts', 'reader', 'preceding')}
    for p in roots.values(): p.mkdir()
    monkeypatch.setattr(r, 'ROOT', roots['reader'])
    binding = {roots['reader'].resolve(): 'b' * 40, roots['source'].resolve(): 'a' * 40,
        roots['preceding'].resolve(): 'c' * 40}
    monkeypatch.setattr(r, 'git_binding', lambda p: binding[p.resolve()])
    study = 'scienceutopia.native-corrected-choice-search.v1' if corrected else 'scienceutopia.native-priority-method-comparison.v1'
    save(roots['run'] / 'plan.json', {'schema': study + '.plan',
        'source_commit': 'a' * 40})
    save(roots['readouts'] / 'started.json', {'schema': study + '.readout.finish' if corrected else r.PRECEDING,
        'scientific_source_commit': 'a' * 40, 'analysis_source_commit': 'c' * 40,
        'plan_file_sha256': r.sha(roots['run'] / 'plan.json'), 'preceding_analysis': str(roots['analysis'].resolve())})
    if closed:
        for i in (1, 2):
            out = roots['readouts'] / ('report-' + str(i)); out.mkdir()
            write_json_atomic(out / 'report.json', {'SCRIPTED': 'preceding report metadata'})
            (out / 'slots.csv').write_text('SCRIPTED,not-native\n')
            write_json_atomic(out / 'manifest.json', {'SCRIPTED': 'preceding manifest'})
        save(roots['readouts'] / 'ended.json', {'status': 'closed', 'new_model_calls': 0, 'new_native_worlds': 0,
            'report_files': r.same_files(roots['readouts'] / 'report-1', roots['readouts'] / 'report-2')})
    args = SimpleNamespace(output=tmp_path / 'output', preceding_source=roots['preceding'],
        **{'origin_' + k: roots[k] for k in ('run', 'source', 'analysis', 'readouts')})
    return args, roots, binding


@pytest.mark.parametrize('destination', ['run', 'source', 'analysis', 'readouts', 'reader', 'preceding', 'alias', 'existing'])
def test_actual_child_destination_guard_precedes_waiting_source_reads_or_mkdir(tmp_path, monkeypatch, destination):
    args, roots, _ = fixture(tmp_path, monkeypatch)
    alias = tmp_path / 'external-looking'; alias.symlink_to(roots['reader'])
    args.output = (alias if destination == 'alias' else roots.get(destination, tmp_path / 'existing')) / 'new'
    if destination == 'existing': args.output.mkdir(parents=True)
    def forbidden(*a, **kw): pytest.fail('guard must run before source reads/wait')
    monkeypatch.setattr(r, 'git_binding', forbidden); monkeypatch.setattr(r, 'wait_readouts', forbidden)
    with pytest.raises(ValueError, match='before waiting'): r.run(args)
    assert args.output.exists() is (destination == 'existing')


@pytest.mark.parametrize('field,value', [('analysis_source_commit', 'f' * 40),
    ('plan_file_sha256', 'f' * 64), ('preceding_analysis', '/SCRIPTED-wrong-analysis'),
    ('schema', 'SCRIPTED-foreign')])
def test_foreign_preceding_header_never_starts_the_continuation(tmp_path, monkeypatch, field, value):
    args, roots, _ = fixture(tmp_path, monkeypatch)
    p = roots['readouts'] / 'started.json'; start = r.read(p); start.pop('content_sha256'); start[field] = value
    p.rename(roots['readouts'] / 'original-started.json'); save(p, start)
    with pytest.raises(ValueError, match='exact original'): r.run(args)
    assert not args.output.exists()


@pytest.mark.parametrize('case', ['stopped', 'missing-file', 'changed-bytes', 'timeout'])
def test_preceding_failure_or_timeout_stops_without_export_retry_or_science(tmp_path, monkeypatch, case):
    args, roots, _ = fixture(tmp_path, monkeypatch, closed=case != 'timeout')
    if case == 'stopped':
        p = roots['readouts'] / 'ended.json'; p.rename(roots['readouts'] / 'old-ended.json'); save(p, {'status': 'stopped'})
    elif case == 'missing-file': (roots['readouts'] / 'report-1/slots.csv').rename(roots['readouts'] / 'missing-slots.csv')
    elif case == 'changed-bytes': (roots['readouts'] / 'report-2/slots.csv').write_text('SCRIPTED changed')
    else:
        ticks = iter([0., 2.]); monkeypatch.setattr(r.time, 'monotonic', lambda: next(ticks))
        with pytest.raises(TimeoutError): r.wait_readouts(roots['readouts'], maximum_seconds=1.)
        return
    def forbidden(*a, **kw): pytest.fail('no child export before normal paired readout closure')
    monkeypatch.setattr(r.subprocess, 'run', forbidden)
    with pytest.raises((ValueError, FileNotFoundError)): r.run(args)
    end = r.read(args.output / 'ended.json')
    assert end['status'] == 'stopped' and not end['science_restarted'] and end['steps'] == []


@pytest.mark.parametrize('failure', [None, 'exit', 'timeout', 'reader-source', 'unequal-files'])
def test_both_scripted_children_or_preserved_stop_never_restart_original_science(tmp_path, monkeypatch, failure):
    args, roots, binding = fixture(tmp_path, monkeypatch); calls = []
    def child(command, **kwargs):
        calls.append(command)
        assert command[1:4] == ['-B', '-m', 'scripts.reports.native_priority_author_outcomes_v1']
        assert kwargs['cwd'] == roots['reader'] and kwargs['env']['PYTHONHASHSEED'] == '42'
        assert kwargs['timeout'] == 1800 and kwargs['check'] is False
        if failure == 'exit': return SimpleNamespace(returncode=7)
        if failure == 'timeout': raise subprocess.TimeoutExpired(command, 1800)
        out = Path(command[command.index('--output') + 1]); out.mkdir()
        save(out / 'report.json', {'rows': [{'SCRIPTED': True}] * 8, 'new_model_calls': 0,
            'new_code_executions': 0, 'selection_changed': False,
            'analysis_source_commit': 'b' * 40, 'scientific_source_commit': 'a' * 40})
        (out / 'authors.csv').write_text('SCRIPTED,not-actual-author-data\n'
            + ('different' if failure == 'unequal-files' and len(calls) == 2 else ''))
        write_json_atomic(out / 'manifest.json', {'SCRIPTED': 'child metadata only'})
        if failure == 'reader-source': binding[roots['reader'].resolve()] = 'd' * 40
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(r.subprocess, 'run', child)
    if failure is None: r.run(args)
    else:
        with pytest.raises((ValueError, subprocess.TimeoutExpired)): r.run(args)
    end = r.read(args.output / 'ended.json')
    assert len(calls) == (2 if failure in (None, 'unequal-files') else 1)
    assert end['status'] == ('closed' if failure is None else 'stopped')
    assert (args.output / 'report-1.started.json').exists() and (args.output / 'report-1.log').exists()
    assert not (roots['run'] / 'started.json').exists()  # No scientific dispatch/restart.
    if failure is None:
        assert set(end['report_files']) == {'report.json', 'authors.csv', 'manifest.json'}
        assert end['new_model_calls'] == end['new_native_worlds'] == 0
        assert not end['manuscript_updated'] and not end['publication_ready']
    else: assert end['science_restarted'] is False
