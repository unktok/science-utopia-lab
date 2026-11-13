import json
from pathlib import Path

import pytest

from scripts import native_workflow_numeric_prerequisite_v2 as guard
from tests.reports.native_workflow_prerequisite_fixture_v2 import scripted_predecessor, rewrite


def test_actual_plain_dispatch_writers_and_sealed_scientific_returns_are_distinct(tmp_path, monkeypatch):
    root = scripted_predecessor(tmp_path)
    monkeypatch.setattr(guard, 'process_identity', lambda pid: None)
    value = guard.binding(root)
    result = guard.require_closed(value)
    assert value['numeric_feedback_imported'] is False and result['old_unknown_resolved'] is False
    assert result['audit_content_sha256'] == guard.read(root / 'audit-1.json')['content_sha256']
    assert 'content_sha256' not in guard.read(root / 'started.json')
    assert 'content_sha256' in guard.read(root / 'audit-1.json')
    assert not list(root.glob('*workflow*'))


@pytest.mark.parametrize('pid_index', [0, 1])
def test_live_or_reused_dispatcher_or_scientific_pid_blocks(tmp_path, monkeypatch, pid_index):
    root = scripted_predecessor(tmp_path); value = guard.binding(root)
    pids = [value['pid'], value['numeric_writer_pid']]
    monkeypatch.setattr(guard, 'process_identity', lambda pid: 'live or reused' if pid == pids[pid_index] else None)
    with pytest.raises(ValueError, match='closed and absent'): guard.require_closed(value)


@pytest.mark.parametrize('case', ['stopped', 'missing-stage', 'failed-stage', 'unknown-resolved',
    'science-restarted', 'unequal-audit', 'wrong-audit-plan', 'wrong-audit-source',
    'missing-world', 'raw-terminal-drift', 'unequal-cost', 'unequal-report', 'missing-ended'])
def test_no_completion_or_equality_is_fabricated(tmp_path, monkeypatch, case):
    root = scripted_predecessor(tmp_path); value = guard.binding(root)
    monkeypatch.setattr(guard, 'process_identity', lambda pid: None)
    if case == 'stopped': rewrite(root / 'ended.json', lambda d: d.update(status='stopped'))
    elif case == 'missing-stage': rewrite(root / 'ended.json', lambda d: d['steps'].pop())
    elif case == 'failed-stage': rewrite(root / 'ended.json', lambda d: d['steps'][2].update(exit_code=1))
    elif case == 'unknown-resolved': rewrite(root / 'ended.json', lambda d: d.update(old_unknown_resolved=True))
    elif case == 'science-restarted': rewrite(root / 'ended.json', lambda d: d.update(science_restarted=True))
    elif case == 'unequal-audit': rewrite(root / 'audit-2.json', lambda d: d.update(SCRIPTED='different'), sealed=True)
    elif case in ('wrong-audit-plan', 'wrong-audit-source', 'missing-world'):
        for i in (1, 2):
            def change(d):
                if case == 'wrong-audit-plan': d['plan_sha256'] = '0' * 64
                elif case == 'wrong-audit-source': d['source_commit'] = '0' * 40
                else: d['worlds'].pop()
            rewrite(root / ('audit-' + str(i) + '.json'), change, sealed=True)
    elif case == 'raw-terminal-drift':
        rewrite(Path(value['numeric_run']) / 'terminal.json',
            lambda d: d.update(consumed_slots=5), sealed=True)
    elif case == 'unequal-cost': (root / 'costs-2.json').write_text('{}')
    elif case == 'unequal-report': (root / 'report-2/all-slots.csv').write_text('different')
    elif case == 'missing-ended': (root / 'ended.json').unlink()
    with pytest.raises((ValueError, FileNotFoundError)): guard.require_closed(value)


@pytest.mark.parametrize('case', ['numeric-plan', 'dispatcher-plan', 'dispatcher-source', 'numeric-source',
    'numeric-start', 'public-plan-check', 'binding-tamper'])
def test_frozen_binding_rechecks_exact_sources_and_bytes(tmp_path, monkeypatch, case):
    root = scripted_predecessor(tmp_path); value = guard.binding(root)
    monkeypatch.setattr(guard, 'process_identity', lambda pid: None)
    if case == 'numeric-plan':
        rewrite(Path(value['numeric_run']) / 'plan.json', lambda d: d.update(SCRIPTED='changed'), sealed=True)
    elif case == 'dispatcher-plan': rewrite(root / 'plan.json', lambda d: d.update(SCRIPTED='changed'))
    elif case == 'dispatcher-source': (root.parents[1] / 'SCRIPTED_SOURCE.txt').write_text('dirty')
    elif case == 'numeric-source':
        source = Path(json.loads((root / 'plan.json').read_text())['frozen_source'])
        (source / 'SCRIPTED_SOURCE.txt').write_text('dirty')
    elif case == 'numeric-start':
        rewrite(Path(value['numeric_run']) / 'started.json', lambda d: d.update(SCRIPTED='changed'), sealed=True)
    elif case == 'public-plan-check':
        rewrite(root / 'original-public-plan-check.json', lambda d: d.update(plan_sha256='0' * 64))
    elif case == 'binding-tamper': value['numeric_feedback_imported'] = True
    with pytest.raises(ValueError): guard.require_closed(value)
