"""Retained limited evidence, not another native run or readiness certificate."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def evidence():
    return checked(json.loads((ROOT/'research/results/native-longitudinal-boundary-light-v1.json').read_text()))


def test_only_the_committed_light_scope_is_proved():
    r = evidence()
    assert r['source_commit'] == '52d343fa6e1c357d91f71808cecf004c5850330a'
    assert r['tests'] == 72 and r['exit_code'] == 0
    assert r['junit_summary']['failures'] == r['junit_summary']['errors'] == r['junit_summary']['skipped'] == '0'
    assert r['earlier_software_attempts'][0]['failed'] == 4
    assert not r['original_scope_guard']['guard_weakened']
    assert 'native_adaptive_search.py' in r['original_scope_guard']['error']
    for key in ('matched_two_arm_scientific_runner_implemented', 'whole_native_cold_integration_complete',
                'backend_token_capacity_proved', 'actual_backend_readiness', 'merged_to_main',
                'applied_to_active_science', 'publication_ready'):
        assert not r[key]
    assert r['new_model_calls'] == r['new_code_executions'] == r['new_native_worlds'] == 0


def test_historical_first_frame_does_not_become_future_token_or_causal_evidence():
    r = evidence()['historical_frame_result']
    rows = r['rows']
    assert [x['mode'] for x in rows] == ['scalar', 'parent-trajectory']
    assert [x['wire_utf8_bytes'] for x in rows] == [84466, 98302]
    assert [x['active_parent_runs'] for x in rows] == [0, 1]
    assert [x['archived_trajectory_runs'] for x in rows] == [0, 2]
    assert all(x['all_original_request_fields_except_new_view_preserved'] for x in rows)
    assert r['original_files_unchanged']
    assert not r['context_token_capacity_proved'] and not r['full_new_production_reconstruction']
    assert not r['actual_backend_readiness'] and not r['publication_ready']
