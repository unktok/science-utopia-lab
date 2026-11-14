"""SCRIPTED host samples; no real process inspection, HTTP, sleep or inference."""
import json
from types import SimpleNamespace

import pytest

from scripts import observe_native_feedback_resources_v2 as module


@pytest.mark.parametrize('declared', [False, True])
def test_unknown_process_still_stops_unless_exactly_inspected_and_declared(tmp_path, monkeypatch, declared):
    exact = '/SCRIPTED/python /SCRIPTED/residence.py run --root /SCRIPTED'
    argv = ['observer', '--output', str(tmp_path / 'output')]
    if declared: argv += ['--allowed-external-python-argument', exact, '--allowance-note', 'SCRIPTED inspected no-model diagnostic']
    monkeypatch.setattr('sys.argv', argv)
    monkeypatch.setattr(module, 'command', lambda *args:
        '777 0.0 /SCRIPTED/python ' + exact if args[0] == '/bin/ps' else
        'Mach Virtual Memory Statistics: (page size of 16384 bytes)\nPages free: 3000000.\nPages inactive: 3000000.')
    sleeps = []; monkeypatch.setattr(module.time, 'sleep', sleeps.append)
    monkeypatch.setattr(module.requests, 'Session', lambda: SimpleNamespace(trust_env=False,
        get=lambda *args, **kwargs: SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'models': []})))
    if declared:
        module.main()
        assert sleeps == [30]
        assert json.loads((tmp_path / 'output/ended.json').read_text())['status'] == 'two-observations-ready'
        assert json.loads((tmp_path / 'output/started.json').read_text())['additional_exact_argument_allowance_note']
    else:
        with pytest.raises(ValueError, match='resource observation failed'): module.main()
        assert not sleeps and not (tmp_path / 'output/ended.json').exists()


def test_new_allowance_needs_evidence_note_before_any_output(tmp_path, monkeypatch):
    monkeypatch.setattr('sys.argv', ['observer', '--output', str(tmp_path / 'out'),
        '--allowed-external-python-argument', '/SCRIPTED/python'])
    with pytest.raises(ValueError, match='allowance note'): module.main()
    assert not (tmp_path / 'out').exists()
