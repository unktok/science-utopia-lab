"""SCRIPTED reporting adapter checks; no native/model execution."""
import hashlib
from pathlib import Path

import pytest

from scripts import audit_frozen_v25_protocol_adapter as adapter


def test_protocol_extension_preserves_original_source_verifier_and_checks_actual_protocol(tmp_path, monkeypatch):
    protocol = sorted(adapter.PROTOCOLS)[-1]
    path = tmp_path / protocol
    path.parent.mkdir(parents=True)
    path.write_text('SCRIPTED exact protocol')
    monkeypatch.setattr(adapter.subprocess, 'check_output', lambda *args, **kwargs: path.read_bytes())
    calls = []
    def original(source, classification):
        calls.append((source, classification))
        return {'files': {'original-runtime': {'verified': True}}}
    proof = adapter.protocol_proof(original, tmp_path, 'a' * 40, 'SCRIPTED', protocol_path=protocol)
    assert calls == [('a' * 40, 'SCRIPTED')]
    assert proof['files']['original-runtime'] == {'verified': True}
    assert proof['files'][protocol]['actual_source_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert proof['protocol_allowlist_extension']['original_unmodified_audit_claimed'] is False
    monkeypatch.setattr(adapter.subprocess, 'check_output', lambda *args, **kwargs: b'different frozen bytes')
    with pytest.raises(ValueError, match='differs from frozen source'):
        adapter.protocol_proof(original, tmp_path, 'a' * 40, 'SCRIPTED', protocol_path=protocol)


def test_no_unlisted_protocol_or_original_verifier_failure_is_waived(tmp_path):
    def failed(*args):
        raise ValueError('original source check failed')
    with pytest.raises(ValueError, match='three declared V25'):
        adapter.protocol_proof(failed, tmp_path, 'a' * 40, 'SCRIPTED', protocol_path='arbitrary.md')
    with pytest.raises(ValueError, match='original source check failed'):
        adapter.protocol_proof(failed, tmp_path, 'a' * 40, 'SCRIPTED', protocol_path=sorted(adapter.PROTOCOLS)[0])


@pytest.mark.parametrize('source', ['main', 'a' * 39, 'G' * 40])
def test_loading_requires_exact_commit_before_any_import_or_execution(tmp_path, source):
    with pytest.raises(ValueError, match='exact 40-character'):
        adapter.load_frozen_auditor(tmp_path, source)
