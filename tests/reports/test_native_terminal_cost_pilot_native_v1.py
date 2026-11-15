"""Actual native/SDK/Docker/cold path; corpus/HTTP/critics/upstream are SCRIPTED."""
import os
import pytest

from tests.reports.test_native_legacy_choice_pilot_native_v1 import public_operator_path
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_TERMINAL_COST_PILOT_QA') != '1',
                   reason='opt-in clean committed-source hardware window required')
def test_two_source_controls_execute_native_cost_phase_and_double_cold(tmp_path, fixed_corpus, monkeypatch):
    public_operator_path(tmp_path, monkeypatch, terminal=True)
