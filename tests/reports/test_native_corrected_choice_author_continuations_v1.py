"""SCRIPTED sources/children; real journals, path guards and stop retention."""
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from scripts import finish_native_corrected_choice_author_outcomes_v1 as authors
from scripts import finish_native_priority_author_outcomes_v1 as base
from scripts import finish_native_corrected_choice_author_visibility_v1 as visibility
from tests.reports.test_finish_native_priority_author_outcomes_v1 import fixture
from utopia.optimization.native_numeric_designer import save
from utopia.utils.data_utils import write_json_atomic


def author_child(command, **kwargs):
    assert command[3] == 'scripts.reports.native_corrected_choice_author_outcomes_v1'
    out = Path(command[command.index('--output') + 1]); out.mkdir()
    save(out / 'report.json', {'schema': 'scienceutopia.native-corrected-choice-author-outcomes.v1',
        'rows': [{'SCRIPTED': 'no actual model/native data'}] * 8, 'new_model_calls': 0,
        'new_code_executions': 0, 'selection_changed': False, 'analysis_source_commit': 'b' * 40,
        'scientific_source_commit': 'a' * 40})
    (out / 'authors.csv').write_text('SCRIPTED,not-actual-science\n')
    write_json_atomic(out / 'manifest.json', {'SCRIPTED': 'child metadata'})
    return SimpleNamespace(returncode=0)


def prepared_author(tmp_path, monkeypatch):
    args, roots, binding = fixture(tmp_path, monkeypatch, corrected=True)
    monkeypatch.setattr(base.subprocess, 'run', author_child); authors.run(args)
    assert base.read(args.output / 'started.json')['schema'] == authors.SCHEMA
    assert base.read(args.output / 'ended.json')['status'] == 'closed'
    return args, roots, binding


def test_actual_corrected_continuation_contract_exports_both_children(tmp_path, monkeypatch):
    args, _, _ = prepared_author(tmp_path, monkeypatch)
    assert set(base.same_files(args.output / 'report-1', args.output / 'report-2')) == {'report.json', 'authors.csv', 'manifest.json'}


@pytest.mark.parametrize('place', ['run', 'source', 'analysis', 'readouts', 'reader', 'preceding', 'alias', 'existing'])
def test_corrected_author_output_preflight_precedes_wait_or_source_reads(tmp_path, monkeypatch, place):
    args, roots, _ = fixture(tmp_path, monkeypatch, corrected=True)
    if place == 'alias':
        alias = tmp_path / 'alias'; alias.symlink_to(roots['reader']); args.output = alias / 'not-created'
    elif place == 'existing': args.output = roots['analysis']
    else: args.output = roots[place] / 'not-created'
    monkeypatch.setattr(base, 'git_binding', lambda *a: pytest.fail('preflight must precede source/wait'))
    with pytest.raises(ValueError, match='before waiting'): authors.run(args)


def visibility_args(tmp_path, monkeypatch):
    a, roots, binding = prepared_author(tmp_path, monkeypatch)
    monkeypatch.setattr(visibility, 'ROOT', roots['reader'])
    monkeypatch.setattr(visibility, 'git_binding', base.git_binding)
    return SimpleNamespace(run=roots['run'], author_outcomes=a.output, author_source=roots['reader'],
        scientific_source=roots['source'], output=tmp_path / 'visibility'), roots, binding


@pytest.mark.parametrize('failure', [None, 'exit', 'timeout', 'source', 'unequal'])
def test_visibility_after_actual_parent_format_or_preserved_stop_never_restarts(tmp_path, monkeypatch, failure):
    args, roots, binding = visibility_args(tmp_path, monkeypatch); calls = []
    def child(command, **kwargs):
        calls.append(command)
        assert command[3] == 'scripts.reports.export_native_corrected_choice_author_visibility_v1'
        assert kwargs['timeout'] == 1800 and kwargs['cwd'] == roots['reader']
        if failure == 'exit': return SimpleNamespace(returncode=5)
        if failure == 'timeout': raise subprocess.TimeoutExpired(command, 1800)
        out = Path(command[command.index('--output') + 1]); out.mkdir()
        save(out / 'report.json', {'schema': 'scienceutopia.native-corrected-choice-author-visibility.v1.all8-join',
            'rows': [{'SCRIPTED': 'metadata only'}] * 8, 'analysis_source_commit': 'b' * 40,
            'scientific_source_commit': 'a' * 40, 'new_model_calls': 0, 'new_generated_code_executions': 0,
            'scientific_losses_rewritten': False})
        (out / 'steps.csv').write_text('SCRIPTED,not-real-world\n' + ('changed' if failure == 'unequal' and len(calls) == 2 else ''))
        write_json_atomic(out / 'manifest.json', {'SCRIPTED': 'manifest'})
        if failure == 'source': binding[roots['reader'].resolve()] = 'd' * 40
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(visibility.subprocess, 'run', child)
    if failure is None: visibility.run(args)
    else:
        with pytest.raises((ValueError, subprocess.TimeoutExpired)): visibility.run(args)
    end = base.read(args.output / 'ended.json')
    assert end['status'] == ('closed' if failure is None else 'stopped')
    assert len(calls) == (2 if failure in (None, 'unequal') else 1)
    assert not (roots['run'] / 'started.json').exists()
    if failure is None: assert not end['publication_ready'] and not end['scientific_losses_rewritten']
    else: assert end['science_restarted'] is False


@pytest.mark.parametrize('place', ['run', 'source', 'reader', 'author', 'analysis', 'readouts', 'alias', 'existing'])
def test_visibility_child_preflight_includes_original_analysis_and_readouts(tmp_path, monkeypatch, place):
    args, roots, _ = visibility_args(tmp_path, monkeypatch)
    if place == 'alias':
        alias = tmp_path / 'alias'; alias.symlink_to(roots['reader']); args.output = alias / 'not-created'
    elif place == 'existing': args.output = roots['analysis']
    elif place == 'author': args.output = args.author_outcomes / 'not-created'
    else: args.output = roots[place] / 'not-created'
    monkeypatch.setattr(visibility, 'wait_readouts', lambda *a, **kw: pytest.fail('preflight must precede waiting'))
    with pytest.raises(ValueError, match='before waiting'): visibility.run(args)
