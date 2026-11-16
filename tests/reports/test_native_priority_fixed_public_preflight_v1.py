"""Light tests of the future heavy test's preflight/failure retention only."""
import json
from pathlib import Path
import tempfile

import pytest

from tests.reports import test_native_priority_fixed_public_v1 as module


@pytest.mark.parametrize('case', ['source', 'test-raw', 'existing', 'source-alias'])
def test_invalid_destination_stops_before_any_native_helper(tmp_path, monkeypatch, case):
    monkeypatch.setenv('SCIENCE_UTOPIA_WORKFLOW_PLAN', 'SCRIPTED-not-opened')
    if case == 'source': external = module.driver.ROOT / 'outputs/not-created-by-this-test'
    elif case == 'test-raw': external = tmp_path / 'not-created'
    elif case == 'existing': external = tmp_path
    else:
        alias = tmp_path / 'alias'; alias.symlink_to(module.driver.ROOT, target_is_directory=True)
        external = alias / 'outputs/not-created-by-this-test'
    monkeypatch.setenv('SCIENCE_UTOPIA_PRIORITY_FIXED_QA_EXTERNAL', str(external))
    def forbidden(*a, **kw): raise AssertionError('native helper must not run during preflight test')
    monkeypatch.setattr(module, 'public_mixed_operator_path', forbidden)
    with pytest.raises(ValueError, match='before any native QA'):
        module.test_public_frozen_bank_prepare_native_run_cold_cost_and_paired_all_label_readouts(tmp_path, None, monkeypatch)
    if case != 'existing': assert not external.exists()
    assert not (tmp_path / 'external-locations.json').exists()


def test_forced_helper_failure_retains_locations_and_stopped_metadata_without_models(tmp_path, monkeypatch):
    monkeypatch.setenv('SCIENCE_UTOPIA_WORKFLOW_PLAN', 'SCRIPTED-not-opened')
    class Forced(BaseException): pass
    def stop(directory, corpus, patch, **kwargs):
        (directory / 'SCRIPTED-retained-marker.txt').write_text('not a native world')
        raise Forced('SCRIPTED no native helper executed')
    monkeypatch.setattr(module, 'public_mixed_operator_path', stop)
    # Unit-test container only; a real opt-in run instead receives an explicit
    # persistent destination and never creates this temporary context.
    with tempfile.TemporaryDirectory(prefix='scienceutopia-public-preflight-') as container:
        external = Path(container) / 'retained'; monkeypatch.setenv('SCIENCE_UTOPIA_PRIORITY_FIXED_QA_EXTERNAL', str(external))
        with pytest.raises(Forced):
            module.test_public_frozen_bank_prepare_native_run_cold_cost_and_paired_all_label_readouts(tmp_path, None, monkeypatch)
        end = json.loads((external / 'stopped.json').read_text()); locations = json.loads((tmp_path / 'external-locations.json').read_text())
        assert end['stage'] == 'development-public-path' and end['error_type'] == 'Forced'
        assert end['native_raw_and_external_artifacts_preserved'] and not end['science_restarted']
        assert (tmp_path / 'development/SCRIPTED-retained-marker.txt').is_file()
        assert locations['software_seeds'] == [43003, 43011] and not locations['scientific_reserved_seeds_consumed']
        assert not locations['automatic_cleanup']
