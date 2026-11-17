"""Opt-in actual native SOFTWARE route, never scientific model performance."""
import os
from pathlib import Path

import pytest

from scripts import run_native_literal_feedback_comparison_v1 as driver
from scripts import audit_native_literal_feedback_comparison_v1 as auditor
from tests.reports.test_native_priority_method_public_v1 import public_mixed_operator_path
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_LITERAL_FEEDBACK_PUBLIC_QA') != '1',
    reason='explicit clean-source native software window, no real inference')
def test_public_native_information_arms_feedback_null_and_double_cold(tmp_path, fixed_corpus, monkeypatch):
    external = os.environ.get('SCIENCE_UTOPIA_LITERAL_FEEDBACK_QA_EXTERNAL')
    public_mixed_operator_path(tmp_path, fixed_corpus, monkeypatch,
        closure_output=None if external is None else Path(external),
        driver_module=driver, auditor_module=auditor, information=True)
