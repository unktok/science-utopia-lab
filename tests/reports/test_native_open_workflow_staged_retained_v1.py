"""Retained real software evidence, not another component/native/model run."""
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]


def evidence():
    return checked(json.loads((ROOT/'research/results/native-open-workflow-staged-component-connection-v1.json').read_text()))


def test_only_twenty_uniquely_attributed_original_r7_contexts_are_declared():
    r = evidence()
    assert r['references'] == ['R7-original'] and r['recorded_inputs'] == 20
    assert r['original_raw_files_unchanged'] == 469
    assert len(r['fixture_origins']) == len({o['bundle_sha256'] for o in r['fixture_origins']}) == 20
    assert set(r['nodes']) == set(r['node_counts'])
    for node in r['nodes']:
        origins = [o for o in r['fixture_origins'] if o['node_id'] == node]
        assert r['node_counts'][node] == 4 and sorted(o['year'] for o in origins) == [1,2,3,4]
        assert all(o['native_event_id'] and o['reference'] == 'R7-original' and o['seed'] == 61001 for o in origins)


def test_both_failed_fixture_and_passing_real_probes_remain_distinct():
    r = evidence()
    attempts = r['real_probe_attempts_including_failed_software_fixture']
    assert set(attempts) == {'open-workflow-post-edit-v1-a2','open-workflow-post-edit-v1-a3'}
    for attempt in attempts.values():
        assert attempt['terminal_probes'] == len(attempt['file_sha256']) == 12
        assert attempt['statuses'] == {'raised':8,'returned':4}
    assert '2 failed' in r['software_check_results']['full_workflow_a2']
    assert '2 passed' in r['software_check_results']['full_workflow_a3']


def test_scripted_recovery_is_not_relabelled_model_repair_or_world_execution():
    r = evidence()
    assert not r['publication_ready'] and not r['connected_to_actual_free_model_campaign']
    assert r['actual_model_calls'] == r['new_native_worlds'] == 0
    assert not r['host_source_repair'] and not r['original_records_repaired']
    assert not r['automatic_model_repair_or_improvement_claimed']
    assert not r['deadline_supervision_tested'] and not r['new_node_world_execution_claimed']
    cases = sorted((c['verification'] for c in r['software_cases']), key=lambda c:c['scripted_repair'])
    assert len(cases) == 2 and [c['real_component_probes'] for c in cases] == [4,8]
    assert [c['scripted_proposal_posts'] for c in cases] == [3,6]
    assert all(c['scripted_calibration_posts'] == 27 for c in cases)
    assert all(c['public_outer_and_inner_cold_replays_agree'] and not c['failure_veto_on_finish'] for c in cases)
