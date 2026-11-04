"""Portable publication consistency, not fresh raw/model execution evidence."""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / 'research/results'


def read(name):
    return json.loads((RESULTS / name).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


@pytest.mark.parametrize('revision', ['a1', 'a2', 'a3'])
def test_published_audit_matches_its_own_exact_source_and_receipt(revision):
    receipt = read('native-closed-loop-v17-verification.json')
    entry = next(row for row in receipt['pilots'] if row['revision'] == revision)
    report = read('native-closed-loop-v17-' + revision + '.json')
    assert report['content_sha256'] == digest({k: v for k, v in report.items() if k != 'content_sha256'})
    assert entry['compact_content_sha256'] == report['content_sha256']
    assert entry['source_commit'] == report['source_commit']
    assert report['status'] == 'budget-complete-with-failures'
    assert report['consumed_native_slots'] == 4
    assert entry['designer_POSTs'] == report['designer_costs']['recorded_POST_attempts'] <= 64
    assert entry['completed_worlds'] == report['physical_native_worlds']
    assert entry['partial_worlds'] == report['physical_world_directory_count'] - report['physical_native_worlds']
    audit = report['audit']
    assert entry['unchanged_raw_files'] == audit['raw_files_verified_unchanged'] == len(audit['raw_input_sha256s'])
    assert entry['matching_source_files'] == len(audit['source_proofs']['files'])
    assert all(row['actual_source_sha256'] == row['analysis_source_sha256']
        for row in audit['source_proofs']['files'].values())


def test_aggregate_costs_do_not_promote_failed_slots_or_nulls_to_completed_worlds():
    receipt = read('native-closed-loop-v17-verification.json')
    reports = [read('native-closed-loop-v17-' + revision + '.json') for revision in ('a1', 'a2', 'a3')]
    totals = receipt['aggregate_resource_accounting_not_a_method_comparison']
    assert totals['charged_slots'] == sum(row['consumed_native_slots'] for row in reports) == 12
    assert totals['completed_native_worlds'] == sum(row['physical_native_worlds'] for row in reports) == 5
    assert totals['partial_native_worlds'] == sum(row['physical_world_directory_count'] - row['physical_native_worlds']
        for row in reports) == 1
    assert totals['designer_POSTs_and_known_replies'] == sum(row['designer_costs']['recorded_POST_attempts']
        for row in reports) == 146
    assert totals['scientist_replies'] == sum(row['physical_researcher_responses'] for row in reports) == 479
    assert totals['recorded_code_executions_including_partial'] == sum(row['recorded_code_executions_including_partial']
        for row in reports) == 43
    observations = [obs for report in reports for run in report['runs'].values() for obs in run['observations']]
    assert sum(row['status'] == 'generation-failure' for row in observations) == totals['generation_failures'] == 6
    assert sum(row['status'] == 'technical-failure' for row in observations) == totals['runtime_failures'] == 1
    assert all((row['loss'] is None) == (row['status'] != 'complete') for row in observations)
    assert not receipt['operational_two_objective_two_generation_goal_achieved']
    assert not any(all(len(run['observations']) == 2 and all(row['status'] == 'complete'
        for row in run['observations']) for run in report['runs'].values()) for report in reports)
    assert all(report['runs'][name]['loss_spec'] == reports[0]['runs'][name]['loss_spec']
        for report in reports for name in ('throughput', 'efficiency'))
    assert not receipt['comparison_is_controlled'] and not totals['missing_costs_imputed_as_zero']


def test_publication_does_not_claim_unobserved_invention_training_or_new_provider():
    receipt = read('native-closed-loop-v17-verification.json')
    assert not any(receipt['claims'].values())
    assert not receipt['overlapping_test_scopes_added']
    assert receipt['handoff']['goal_remains_unmet']
    assert not receipt['handoff']['alternate_provider_track_started']
    assert not receipt['handoff']['additional_trials_started_by_this_report']
    for revision in ('a1', 'a2', 'a3'):
        report = read('native-closed-loop-v17-' + revision + '.json')
        for run in report['runs'].values():
            for row in run['generations']:
                if row['status'] == 'generated':
                    changes = row['authoring_change']['literal_change_counts']
                    assert changes['source_changes'] == changes['source_bodies_added'] == changes['nodes_added'] == 0
