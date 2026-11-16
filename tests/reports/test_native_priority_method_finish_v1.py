"""Metadata-only continuation tests; never start or repeat scientific inference."""
from types import SimpleNamespace
from pathlib import Path
import pytest

from scripts import finish_native_priority_method_comparison_v1 as f
from utopia.optimization.native_numeric_designer import save


def records(root, *, code=0):
    plan = save(root / 'plan.json', {'source_commit': 'a' * 40})
    save(root / 'writer-supervision-start.json', {
        'schema': 'scienceutopia.native-priority-method-writer-supervision.v1',
        'source_commit': plan['source_commit'], 'plan_content_sha256': plan['content_sha256'], 'supervisor_pid': 22})
    save(root / 'terminal.json', {'status': 'closed', 'ended_utc': '2026-11-16T00:00:00+00:00'})
    return {'schema': 'scienceutopia.native-priority-method-writer-exit.v1',
        'source_commit': plan['source_commit'], 'plan_content_sha256': plan['content_sha256'],
        'exit_code': code, 'ended_utc': '2026-11-16T00:00:01+00:00'}


def test_scientist_exit_does_not_race_supervisor_final_inventory_append(tmp_path):
    exit_record = records(tmp_path); ticks, polls = [0], []
    def poll(seconds):
        polls.append(seconds); ticks[0] += seconds
        save(tmp_path / 'writer-exit.json', exit_record)
    def observe(pid): return 'SCRIPTED-original-supervisor' if ticks[0] == 0 else None
    value = f.wait_supervised(tmp_path, 11, 'SCRIPTED-writer',
        wait=lambda *a: {'original_writer_absent': True}, observe=observe,
        clock=lambda: ticks[0], poll=poll)
    assert polls == [1] and value['original_process_exit_status'] == 0
    assert value['writer_exit_file_sha256'] == f.sha(tmp_path / 'writer-exit.json')


@pytest.mark.parametrize('code', [1, -9, True])
def test_bad_supervisor_exit_never_authorizes_cold_analysis(tmp_path, code):
    result = records(tmp_path, code=code); save(tmp_path / 'writer-exit.json', result)
    with pytest.raises(ValueError, match='successful closure'):
        f.wait_supervised(tmp_path, 11, None, wait=lambda *a: {}, observe=lambda pid: None)


def test_missing_exit_journal_has_finite_wait_without_restarting_any_process(tmp_path):
    records(tmp_path); ticks = [0]
    with pytest.raises(ValueError, match='finite grace'):
        f.wait_supervised(tmp_path, 11, None, wait=lambda *a: {}, observe=lambda pid: None,
            clock=lambda: ticks[0], poll=lambda seconds: ticks.__setitem__(0, ticks[0] + seconds),
            supervisor_grace_seconds=2)
    assert ticks[0] == 2 and not (tmp_path / 'writer-exit.json').exists()


def test_output_preflight_rejects_reader_local_resolved_symlink_before_waiting(tmp_path, monkeypatch):
    reader = tmp_path / 'reader'; reader.mkdir(); link = tmp_path / 'external-looking'; link.symlink_to(reader)
    monkeypatch.setattr(f, 'ROOT', reader)
    monkeypatch.setattr(f, 'finish', lambda *a, **kw: pytest.fail('invalid destination must not reach waiting'))
    for out in (reader / 'out', link / 'out', tmp_path / 'science/out', tmp_path / 'raw/out'):
        args = SimpleNamespace(output=out, run=tmp_path / 'raw', frozen_source=tmp_path / 'science', writer_pid=11)
        with pytest.raises(ValueError, match='outside reader'): f.run(args)
        assert not out.exists()
