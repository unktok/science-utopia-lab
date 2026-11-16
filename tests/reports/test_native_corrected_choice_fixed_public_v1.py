"""Opt-in corrected development -> both frozen scopes -> native fixed evaluation.

NOT run during real inference. HTTP/corpus/child supervision are SCRIPTED;
software42/43003/43011 only, no reserved scientific condition consumed.
"""
import os

import pytest

from tests.reports.test_native_priority_fixed_public_v1 import (
    test_public_frozen_bank_prepare_native_run_cold_cost_and_paired_all_label_readouts as public_path)
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_CORRECTED_CHOICE_FIXED_PUBLIC_QA') != '1',
    reason='requires explicit clean-source hardware window without real inference')
def test_corrected_native_fixed_prepare_run_double_cold_cost_and_both_scope_exports(tmp_path, fixed_corpus, monkeypatch):
    public_path(tmp_path, fixed_corpus, monkeypatch, corrected=True)
