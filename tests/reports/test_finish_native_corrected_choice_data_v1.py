"""SCRIPTED continuation metadata, not original world/cold/source evidence."""
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from scripts import finish_native_corrected_choice_data_v1 as r
from tests.reports.test_finish_native_priority_author_outcomes_v1 import fixture as original_fixture
from utopia.optimization.native_numeric_designer import save


def fixture(tmp_path, monkeypatch, *, kind='loss-paths', closed=True):
    args, roots, binding = original_fixture(tmp_path, monkeypatch, corrected=True, closed=False)
    monkeypatch.setattr(r, 'ROOT', roots['reader'])
    monkeypatch.setattr(r, 'pinned_revision', lambda p: binding[p.resolve()])
    args.kind = kind
    original = {'schema': 'scienceutopia.native-corrected-choice-readout.v1',
        'input_audit_content_sha256': 'd' * 64, 'plan_content_sha256': 'e' * 64,
        'frozen_selection_content_sha256': 'f' * 64}
    if closed:
        for i in (1, 2):
            out = roots['readouts'] / ('report-' + str(i)); out.mkdir()
            original = save(out / 'report.json', {k:v for k,v in original.items() if k != 'content_sha256'})
            (out / 'slots.csv').write_text('SCRIPTED,not-native\n')
            save(out / 'manifest.json', {'SCRIPTED': 'not original scientific proof'})
        save(roots['readouts'] / 'ended.json', {'status': 'closed', 'new_model_calls': 0, 'new_native_worlds': 0,
            'report_files': r.same_files(roots['readouts'] / 'report-1', roots['readouts'] / 'report-2')})
    return args, roots, binding, original


def child_report(kind, original):
    common = {'schema': r.KINDS[kind][1], 'analysis_source_commit': 'b' * 40,
        'scientific_source_commit': 'a' * 40, 'new_model_calls': 0, 'new_native_worlds': 0,
        'selection_changed': False, 'publication_ready': False,
        'frozen_selection_content_sha256': original['frozen_selection_content_sha256']}
    if kind == 'loss-paths':
        return {**common, 'original_readout_content_sha256': original['content_sha256'],
            'paths': [{'points': [{'SCRIPTED': 'not scientific data'}] * 4}] * 6}
    return {**common, 'new_code_executions': 0, 'loss_changed': False,
        'rows': [{'SCRIPTED': 'not scientific data'}] * 27,
        'input_audit_content_sha256': original['input_audit_content_sha256'],
        'plan_content_sha256': original['plan_content_sha256']}


@pytest.mark.parametrize('kind', tuple(r.KINDS))
@pytest.mark.parametrize('place', ['reader', 'source', 'run', 'analysis', 'readouts', 'preceding', 'alias', 'existing'])
def test_actual_child_path_preflight_precedes_source_wait_or_mkdir(tmp_path, monkeypatch, kind, place):
    args, roots, _, _ = fixture(tmp_path, monkeypatch, kind=kind)
    alias = tmp_path / 'external-looking'; alias.symlink_to(roots['reader'])
    if place == 'existing': args.output = roots['readouts']
    else: args.output = (alias if place == 'alias' else roots[place]) / 'not-created'
    def forbidden(*a, **kw): pytest.fail('preflight must precede source reads/wait')
    monkeypatch.setattr(r, 'pinned_revision', forbidden); monkeypatch.setattr(r, 'wait_readouts', forbidden)
    with pytest.raises(ValueError, match='before waiting'): r.run(args)
    assert args.output.exists() is (place == 'existing')


@pytest.mark.parametrize('kind', tuple(r.KINDS))
@pytest.mark.parametrize('failure', [None, 'exit', 'timeout', 'source', 'different-files', 'render-file', 'selection', 'new-world'])
def test_paired_data_only_children_or_explicit_stop_never_restart_science(tmp_path, monkeypatch, kind, failure):
    args, roots, binding, original = fixture(tmp_path, monkeypatch, kind=kind); calls = []
    def child(command, **kwargs):
        calls.append(command)
        assert command[1:4] == ['-B', '-m', r.KINDS[kind][0]] and '--render' not in command
        assert kwargs['cwd'] == roots['reader'] and kwargs['timeout'] == 1800
        assert kwargs['env']['PYTHONHASHSEED'] == '42' and kwargs['check'] is False
        if failure == 'exit': return SimpleNamespace(returncode=7)
        if failure == 'timeout': raise subprocess.TimeoutExpired(command, 1800)
        out = Path(command[command.index('--output') + 1]); out.mkdir()
        value = child_report(kind, original)
        if failure == 'selection': value['frozen_selection_content_sha256'] = 'SCRIPTED foreign'
        if failure == 'new-world': value['new_native_worlds'] = 1
        save(out / 'report.json', value)
        (out / r.KINDS[kind][2]).write_text('SCRIPTED,not-native\n' + (
            'different' if failure == 'different-files' and len(calls) == 2 else ''))
        save(out / 'manifest.json', {'SCRIPTED': 'not original scientific proof'})
        if failure == 'source': binding[roots['reader'].resolve()] = 'SCRIPTED source changed'
        if failure == 'render-file': (out / 'unexpected.png').write_bytes(b'SCRIPTED not an image')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(r.subprocess, 'run', child)
    if failure is None: r.run(args)
    else:
        with pytest.raises((ValueError, subprocess.TimeoutExpired)): r.run(args)
    end = r.read(args.output / 'ended.json')
    assert len(calls) == (2 if failure in (None, 'different-files', 'render-file') else 1)
    assert end['status'] == ('closed' if failure is None else 'stopped')
    assert not (roots['run'] / 'started.json').exists()
    if failure is None:
        assert set(end['report_files']) == {'report.json', 'manifest.json', r.KINDS[kind][2]}
        assert end['new_model_calls'] == end['new_native_worlds'] == 0
        assert all(end[k] is False for k in ('render_requested', 'manuscript_updated', 'visual_review_complete', 'publication_ready'))
    else: assert end['science_restarted'] is False


def test_upstream_stop_or_source_preflight_failure_does_not_dispatch_children(tmp_path, monkeypatch):
    args, roots, _, _ = fixture(tmp_path, monkeypatch, closed=False)
    save(roots['readouts'] / 'ended.json', {'status': 'stopped'})
    monkeypatch.setattr(r.subprocess, 'run', lambda *a, **kw: pytest.fail('no downstream command'))
    with pytest.raises(ValueError): r.run(args)
    assert r.read(args.output / 'ended.json')['steps'] == []


@pytest.mark.parametrize('kind,field', [('loss-paths', 'paths'), ('signed-content', 'rows')])
def test_partial_shape_is_not_a_complete_data_result(tmp_path, monkeypatch, kind, field):
    _, _, _, original = fixture(tmp_path, monkeypatch, kind=kind)
    value = child_report(kind, original); value[field] = value[field][:-1]
    with pytest.raises(ValueError):
        r.validate_result(kind, value, reader='b' * 40, scientific='a' * 40, original=original)


def test_wrong_original_header_is_rejected_before_output_or_wait(tmp_path, monkeypatch):
    args, roots, binding, _ = fixture(tmp_path, monkeypatch)
    binding[roots['preceding'].resolve()] = 'SCRIPTED foreign commit'
    monkeypatch.setattr(r, 'wait_readouts', lambda *a, **kw: pytest.fail('wrong binding must stop before waiting'))
    with pytest.raises(ValueError, match='exact original'): r.run(args)
    assert not args.output.exists()
