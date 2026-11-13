"""Twenty native worlds through real APIs, with SCRIPTED HTTP/data/load only.

This is not actual model calibration or scientific institution effectiveness.
"""
from scripts import run_native_parent_presentation_loop_v1 as driver
from scripts import audit_native_parent_presentation_loop_v1 as audit
from tests.reports.test_native_parent_presentation_loop_v1 import plan
from tests.reports.test_native_planning_controller_native_v1 import run_native_controller_case
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus


def test_twenty_worlds_two_presentations_real_role_worker_replay_audit_costs_and_readers(tmp_path, fixed_corpus, monkeypatch):
    return run_native_controller_case(tmp_path, fixed_corpus, monkeypatch,
        driver=driver, audit=audit, plan=plan, presentation=True)
