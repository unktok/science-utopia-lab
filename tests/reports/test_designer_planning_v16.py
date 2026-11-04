"""Probe status must distinguish a returned failure envelope from a candidate."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('planning_probe_v16',
    Path(__file__).resolve().parents[2] / 'scripts/verify_designer_planning_v16.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


@pytest.mark.parametrize('value', [None, {}, {'generation_failure': {'reason': 'exhausted'}},
    {'base_patch': {}, 'factors': []}, {'generation_failure': {}, 'base_patch': {},
        'factors': [], 'continuous': [], 'provenance': {}}])
def test_returned_failure_or_partial_definition_is_never_finished(value):
    assert not probe.finished_definition(value)


def test_complete_envelope_is_eligible_only_actual_journal_finish_proves_validity():
    assert probe.finished_definition({'base_patch': {}, 'factors': [], 'continuous': [], 'provenance': {}})
