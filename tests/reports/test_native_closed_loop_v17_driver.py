"""SCRIPTED launch receipts; no model, data loader, Docker or world calls."""
import json
import sys

import pytest
from scripts import run_native_staged_search_v15 as driver


def setup(monkeypatch, tmp_path, *, resume=False):
    monkeypatch.setattr(driver, 'pinned_revision', lambda root: 'a' * 40)
    monkeypatch.setattr(driver, 'execute', lambda args: 0)
    argv = ['run_native_staged_search_v15.py', '--start-authorized-search', '--output', str(tmp_path),
        '--data-cache', str(tmp_path / 'cache'), '--designer-preflight', str(tmp_path / 'certificate.json')]
    if resume:
        argv.append('--resume-existing-launch')
    monkeypatch.setattr(sys, 'argv', argv)


def test_writer_receipts_preserve_original_and_require_explicit_same_source_resume(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    assert driver.main() == 0
    original = (tmp_path / 'writer.started.json').read_bytes()
    with pytest.raises(ValueError, match='explicit same-source resume'):
        driver.main()
    setup(monkeypatch, tmp_path, resume=True)
    assert driver.main() == 0
    assert (tmp_path / 'writer.started.json').read_bytes() == original
    assert json.loads((tmp_path / 'writer-resume-001.ended.json').read_text())['exit_code'] == 0
    monkeypatch.setattr(driver, 'pinned_revision', lambda root: 'b' * 40)
    with pytest.raises(ValueError, match='same-source resume'):
        driver.main()


def test_aborted_writer_is_not_a_success_receipt(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    def fail(args):
        raise ValueError('SCRIPTED construction failure')
    monkeypatch.setattr(driver, 'execute', fail)
    with pytest.raises(ValueError, match='SCRIPTED construction'):
        driver.main()
    receipt = json.loads((tmp_path / 'writer.ended.json').read_text())
    assert receipt['status'] == 'aborted' and 'exit_code' not in receipt
