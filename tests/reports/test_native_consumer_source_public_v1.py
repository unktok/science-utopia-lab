"""Actual public native/Docker/SDK/cold software path; all model input SCRIPTED."""
import os
import pytest

from tests.reports import test_native_topic_free_public_path_v1 as shared
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from scripts import run_native_consumer_source_comparison_v1 as driver
from scripts import audit_native_consumer_source_comparison_v1 as auditor


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_CONSUMER_PUBLIC_QA') != '1',
                   reason='explicit clean-source hardware window, no real inference active')
def test_matched_source_visibility_native_worlds_and_paired_original_cold(tmp_path,fixed_corpus,monkeypatch):
    monkeypatch.setattr(shared,'driver',driver)
    monkeypatch.setattr(shared,'auditor',auditor)
    shared.test_actual_bounded_editor_feedback_native_objectives_and_double_cold(
        tmp_path,fixed_corpus,monkeypatch,matched=True)
