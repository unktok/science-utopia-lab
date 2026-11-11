"""Actual native/Docker connection checks with scripted original researchers."""
import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from tests.system import test_native_review_routing_information_world as previous
from utopia.optimization.native_review_routing_controls import routed_control
from utopia.system.native_information_institution import information_system


@pytest.mark.parametrize('clock',[1234567890.,1234654290.])
def test_parameterized_developer_routing_source_runs_actual_native_tasks(tmp_path,fixed_corpus,monkeypatch,clock):
    monkeypatch.setattr(previous,'current_routed_system',lambda count:routed_control(
        information_system(previous.IMAGE),reviewers_per_paper=count,snapshot_phase=85,producer_phase=87))
    previous.test_two_routing_rules_execute_in_current_world_with_equal_pre_review_inputs(
        tmp_path,fixed_corpus,monkeypatch,clock)
