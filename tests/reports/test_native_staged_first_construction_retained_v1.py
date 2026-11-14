"""Retained terminal proposal scope, not a live heartbeat or new native result."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def test_actual_staged_proposal_keeps_all_steps_probes_and_known_rejection():
    r = checked(json.loads((ROOT/'research/results/native-open-staged-first-construction-v1.json').read_text()))
    assert r['model_steps'] == 14 and r['selected_step'] == 13 and r['proposal_status'] == 'generated'
    assert r['step_status_counts'] == {'applied': 12, 'rejected': 1, 'finished': 1}
    assert r['tool_counts'] == {'plan': 1, 'read_file': 9, 'write_file': 3, 'finish': 1}
    error, = r['technical_rejections']; assert error['step'] == 12
    assert 'rationale' in error['errors'][0]['message'] and 'maxLength' in error['errors'][0]['message']
    t = r['component_trace']; assert t['component_testing']['probe_attempts'] == 8
    assert t['component_testing']['returned'] == 8 and t['component_testing']['raised'] == 0
    assert len(t['same_fixture_later_code_comparisons']) == 4
    assert all(x['transition'] == 'returned-to-returned' for x in t['same_fixture_later_code_comparisons'])
    assert r['same_fixture_outputs_equal_between_two_tested_versions']
    assert all(x['matches_current_successful_edit'] for x in r['literal_source_readbacks'])
    assert not r['component_error_repair_demonstrated'] and not r['host_source_repair']


def test_source_change_and_native_start_do_not_become_an_improvement_claim():
    r = checked(json.loads((ROOT/'research/results/native-open-staged-first-construction-v1.json').read_text()))
    g = r['literal_graph_change']
    assert set(g['source_edits']) == {'world.selection'}
    for key in ('added_nodes', 'removed_nodes', 'added_connections', 'removed_connections', 'phase_updates'):
        assert not g[key]
    assert r['native_world_entered'] and not r['own_native_observation_complete'] and r['own_loss'] is None
    assert not r['whole_study_cold_audit_complete'] and not r['new_institutional_advantage_claimed']
    assert not r['publication_ready']
    assert [c['scores']['throughput'] for c in r['completed_controls']] == [-18., -20.]
