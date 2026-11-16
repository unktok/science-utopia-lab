"""Preflight only: prohibit native helper/model work in every test below."""
import json
from pathlib import Path
import tempfile

import pytest

from scripts import audit_native_corrected_choice_fixed_evaluation_v1 as auditor
from scripts import run_native_corrected_choice_fixed_evaluation_v1 as driver
from scripts.reports import native_corrected_choice_fixed_evaluation_v1 as readout
from tests.reports import test_native_priority_fixed_public_v1 as public


@pytest.mark.parametrize('case', ['source', 'test-raw', 'existing', 'source-alias'])
def test_new_profile_public_preflight_rejects_before_native_work(tmp_path, monkeypatch, case):
    monkeypatch.setenv('SCIENCE_UTOPIA_WORKFLOW_PLAN', 'SCRIPTED-not-opened')
    if case == 'source': external = driver.ROOT / 'outputs/not-created-by-test'
    elif case == 'test-raw': external = tmp_path / 'not-created'
    elif case == 'existing': external = tmp_path
    else:
        alias = tmp_path / 'alias'; alias.symlink_to(driver.ROOT, target_is_directory=True)
        external = alias / 'outputs/not-created-by-test'
    monkeypatch.setenv('SCIENCE_UTOPIA_CORRECTED_CHOICE_FIXED_QA_EXTERNAL', str(external))
    def forbidden(*args, **kwargs): raise AssertionError('native helper forbidden in metadata-only test')
    monkeypatch.setattr(public, 'public_mixed_operator_path', forbidden)
    with pytest.raises(ValueError, match='before any native QA'):
        public.test_public_frozen_bank_prepare_native_run_cold_cost_and_paired_all_label_readouts(
            tmp_path, None, monkeypatch, corrected=True)
    if case != 'existing': assert not external.exists()


def test_corrected_scope_is_forwarded_and_failed_native_check_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv('SCIENCE_UTOPIA_WORKFLOW_PLAN', 'SCRIPTED-not-opened')
    class Forced(BaseException): pass
    calls = []
    def stop(directory, corpus, patch, **kwargs):
        calls.append(kwargs); (directory / 'retained.txt').write_text('SCRIPTED no native execution')
        raise Forced('SCRIPTED stop before native work')
    monkeypatch.setattr(public, 'public_mixed_operator_path', stop)
    with tempfile.TemporaryDirectory(prefix='scienceutopia-corrected-fixed-preflight-') as container:
        out = Path(container) / 'external'
        monkeypatch.setenv('SCIENCE_UTOPIA_CORRECTED_CHOICE_FIXED_QA_EXTERNAL', str(out))
        with pytest.raises(Forced):
            public.test_public_frozen_bank_prepare_native_run_cold_cost_and_paired_all_label_readouts(
                tmp_path, None, monkeypatch, corrected=True)
        assert calls[0]['corrected'] is True
        assert calls[0]['driver_module'].__name__.endswith('run_native_corrected_choice_search_v1')
        end = json.loads((out / 'stopped.json').read_text())
        assert end['stage'] == 'development-public-path' and end['native_raw_and_external_artifacts_preserved']
        assert not end['science_restarted']


def test_named_cold_worker_routes_to_new_source_bound_auditor(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(auditor, 'common_worker', lambda *args, **kw: calls.append((args, kw)))
    auditor.worker(tmp_path / 'raw', tmp_path / 'audit.json')
    assert calls == [((tmp_path / 'raw', tmp_path / 'audit.json'), {'study': 'corrected-choice-fixed-v1'})]


def test_readout_subprocess_keeps_corrected_wrapper_path(monkeypatch, tmp_path):
    import sys
    from types import SimpleNamespace
    base = readout.base; calls = []
    monkeypatch.delenv('SCIENCE_UTOPIA_PRIORITY_FIXED_READOUT_WORKER', raising=False)
    keys = ('run', 'frozen-source', 'audit-one', 'audit-two', 'cost-one', 'cost-two', 'output')
    monkeypatch.setattr(sys, 'argv', ['SCRIPTED-readout', *[v for k in keys for v in ('--' + k, str(tmp_path / k))]])
    monkeypatch.setattr(base.subprocess, 'run', lambda argv, **kwargs: calls.append((argv, kwargs)) or SimpleNamespace(returncode=0))
    base.main(profile=driver.PROFILE, worker_path=Path(readout.__file__))
    argv, kwargs = calls[0]
    assert str(Path(readout.__file__).resolve()) in argv
    assert kwargs['env']['SCIENCE_UTOPIA_PRIORITY_FIXED_READOUT_WORKER'] == '1'
    assert kwargs['cwd'] == tmp_path / 'frozen-source'
