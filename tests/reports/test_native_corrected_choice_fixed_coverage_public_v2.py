"""Opt-in actual native fixed-evaluation path with positive fixture provenance.

All HTTP/corpus/supervision is SCRIPTED. Only42/43003/43011 software seeds;
not real-model science or consumption of the83003/83011 research conditions.
"""
import os

import pytest

from tests.reports.test_native_priority_fixed_public_v1 import (
    test_public_frozen_bank_prepare_native_run_cold_cost_and_paired_all_label_readouts as public_path)
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_CORRECTED_CHOICE_FIXED_COVERAGE_V2_QA') != '1',
    reason='explicit clean-source hardware window without real inference required')
def test_corrected_native_fixed_path_preserves_and_classifies_exact_software_metadata(tmp_path, fixed_corpus, monkeypatch):
    public_path(tmp_path, fixed_corpus, monkeypatch, corrected=True, coverage_policy_v2=True)
