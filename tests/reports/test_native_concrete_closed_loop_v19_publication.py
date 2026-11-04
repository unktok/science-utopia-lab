"""Portable evidence consistency; no new model/world or performance claim."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_search_v15 import NativeStagedSearchController
from utopia.system.design_patch import digest

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / 'research/results'
SOURCE = '6b53841b89618bd9ce6ebed3e52b43c3b22c9fe1'


def read(name):
    return json.loads((RESULTS / name).read_text())


def report():
    return read('native-concrete-closed-loop-v19-a1.json')


def receipt():
    return read('native-concrete-closed-loop-v19-verification.json')


def test_complete_audit_is_bound_to_exact_source_and_unchanged_inventory():
    result, evidence = report(), receipt()
    assert result['content_sha256'] == digest({k: v for k, v in result.items() if k != 'content_sha256'})
    assert evidence['compact_audit_content_sha256'] == result['content_sha256']
    assert evidence['full_audit_content_sha256'] == result['exact_full_audit_content_sha256']
    assert result['source_commit'] == evidence['actual_source_commit'] == SOURCE
    assert result['classification'] == 'actual-local-qwen-staged-native-closed-loop-development-v19'
    assert result['engineering_revision'] == 'v19-a1'
    assert result['status'] == 'complete'
    assert result['queue_terminal'] and result['budget_terminal']
    assert result['planned_native_slots'] == result['consumed_native_slots'] == 4
    assert result['technical_failures'] == 0
    audit = result['audit']
    assert evidence['raw_inventory_sha256'] == audit['raw_inventory_sha256'] == digest(audit['raw_input_sha256s'])
    assert evidence['raw_files_verified_unchanged'] == audit['raw_files_verified_unchanged'] == len(audit['raw_input_sha256s']) == 128
    assert evidence['matching_source_files'] == len(audit['source_proofs']['files']) == 247
    assert all(row['actual_source_sha256'] == row['analysis_source_sha256']
        for row in audit['source_proofs']['files'].values())
    assert audit['new_model_calls'] == audit['new_container_executions'] == 0
    assert audit['exact_raw_tools_draft_source_definition_replayed']
    assert audit['own_history_loss_and_all_ties_replayed']


@pytest.mark.parametrize('arm,losses,calls', [
    ('throughput', [-1.0, -1.0], [4, 8]), ('efficiency', [8.0, 8.0], [4, 7])])
def test_both_arms_have_two_real_observations_and_exact_own_loss_feedback(arm, losses, calls):
    run, evidence = report()['runs'][arm], receipt()
    observations, generations = run['observations'], run['generations']
    assert len(observations) == len(generations) == 2
    assert run['terminal'] and run['consumed_native_slots'] == 2
    assert [o['loss'] for o in observations] == evidence['loss_paths'][arm] == losses
    assert all(o['status'] == o['original_observation_status'] == 'complete' for o in observations)
    assert [g['counts']['recorded_POST_attempts'] for g in generations] == evidence['generations'][arm]['calls'] == calls
    assert all(g['status'] == 'generated' and g['counts']['valid_finished_generations'] == 1 for g in generations)
    assert all(g['step_receipts'][-1]['status'] == 'finished' and g['tool_counts']['finish'] == 1 for g in generations)
    assert all(g['exact_raw_tools_draft_finish_replayed'] and g['own_history_and_loss_prompt_replayed'] for g in generations)
    assert generations[0]['own_scalar_outcomes_received'] == []
    assert generations[1]['own_scalar_outcomes_received'] == [{
        'loss': observations[0]['loss'], 'observation_id': observations[0]['observation_id'], 'status': 'complete'}]
    assert generations[1]['based_on_observation_id'] == evidence['generations'][arm]['G1_based_on'] == observations[0]['observation_id']
    assert generations[1]['authoring_change']['parent_document_sha256'] == observations[0]['system_fingerprint']


@pytest.mark.parametrize('arm', ['throughput', 'efficiency'])
def test_original_loss_specs_recompute_from_measured_original_world_metrics(arm):
    run = report()['runs'][arm]
    spec = run['loss_spec']
    assert spec == json.loads((ROOT / 'research/objectives/losses' / (spec['id'] + '.json')).read_text())
    names = {'A': 'native.accepted_decisions', 'Q': 'native.accepted_peer_score_sum', 'R': 'native.review_records'}
    for observation in run['observations']:
        measured = observation['native_A_Q_R']
        assert {k: v['value'] for k, v in measured.items()} == {'A': 1, 'Q': 4, 'R': 24}
        evaluation = {'run_id': observation['observation_id'], 'metrics': {names[k]: v for k, v in measured.items()}}
        result = evaluate_loss(spec, [evaluation])
        assert result['status'] == 'complete'
        assert result['loss'] == observation['loss'] == observation['original_observation_loss']


def test_physical_costs_are_fresh_not_success_labels_or_copied_baselines():
    result, evidence = report(), receipt()
    observations = [o for run in result['runs'].values() for o in run['observations']]
    generations = [g for run in result['runs'].values() for g in run['generations']]
    assert len({o['checkpoint_sha256'] for o in observations}) == len({o['observation_id'] for o in observations}) == 4
    assert len([path for path in result['audit']['raw_input_sha256s'] if path.endswith('/replies/responses.sqlite')]) == 4
    assert result['physical_native_worlds'] == result['physical_world_directory_count'] == evidence['accounting']['completed_native_worlds'] == 4
    costs = result['designer_costs']
    assert costs['recorded_POST_attempts'] == costs['dispatch_intents'] == costs['known_HTTP_responses'] == costs['known_designer_responses'] == 23
    assert costs['interrupted_response_unknown'] == evidence['accounting']['unknown_interrupted_replies'] == 0
    rejected = sum(step['status'] == 'rejected' for g in generations for step in g['step_receipts'])
    assert rejected == evidence['accounting']['rejected_tool_actions'] == 7
    assert sum(g['authoring_change']['successful_edit_or_splice_steps'] for g in generations) == evidence['accounting']['accepted_noop_edits'] == 1
    assert all(o['native_physical_counts']['scientist_responses'] > 0 and o['native_physical_counts']['recorded_code_executions'] > 0 for o in observations)
    assert sum(o['native_physical_counts']['scientist_responses'] for o in observations) == result['completed_researcher_responses'] == evidence['accounting']['scientist_replies_and_wire_requests'] == 368
    assert sum(o['native_physical_counts']['recorded_code_executions'] for o in observations) == result['completed_code_executions'] == evidence['accounting']['sandboxed_inherited_code_executions'] == 32
    assert result['designer_cost_measurements']['model_call_seconds']['recorded_sum'] == evidence['accounting']['designer_adapter_seconds']
    assert result['completed_researcher_model_call_seconds'] == evidence['accounting']['completed_scientist_adapter_seconds']
    assert not evidence['accounting']['parallel_test_and_nested_transport_times_added_to_wall']


def test_retention_is_not_relabelled_invention_or_an_exercised_final_call_fix():
    result, evidence = report(), receipt()
    for run in result['runs'].values():
        for generation in run['generations']:
            change = generation['authoring_change']
            assert change['explicit_exact_parent_retention'] and change['valid_explicit_finish']
            assert not change['exact_document_changed']
            assert set(change['literal_change_counts'].values()) == {0}
            assert change['compiled_base_nodes'] == 19 and change['compiled_base_wires'] == 27
            assert generation['counts']['recorded_POST_attempts'] < 16
    assert evidence['completion_audit_passed'] and all(evidence['requirements_proven'].values())
    assert evidence['claims']['operational_two_objective_feedback_demonstrated']
    assert not any(value for key, value in evidence['claims'].items()
        if key != 'operational_two_objective_feedback_demonstrated')
    assert not any(evidence['history'][key] for key in (
        'alternate_provider_started', 'new_paid_API_configuration', 'remote_push_performed', 'paper_or_game_updated'))
    assert evidence['full_SCRIPTED_suite']['source_commit'] == SOURCE
    assert not evidence['full_SCRIPTED_suite']['overlapping_focused_counts_added']
    # Historical failed trials retain their source-scoped unmet-goal receipt.
    assert not read('native-closed-loop-v17-verification.json')['operational_two_objective_two_generation_goal_achieved']


def test_scripted_projection_keeps_worse_measurements_separate_from_best():
    """Software policy check, not an observed worse-world V19 result."""
    controller = NativeStagedSearchController.__new__(NativeStagedSearchController)
    controller.request = {'method': 'blackbox', 'native_budget': 2}
    controller.plan = {'request_sha256': 'fixture', 'source_commit': SOURCE,
        'stage_counts': [1, 1], 'maximum_designer_provider_attempts': 32}
    controller.plan_sha256 = digest(controller.plan)
    controller.campaign = SimpleNamespace(state={'pending': None, 'records': [
        {'request': {'count': 1}, 'generation_error': None,
         'draws': [{'suggestion': {'id': str(i)}, 'technical_error': None}],
         'observations': [{'status': 'complete', 'loss': loss, 'metadata': {}}]}
        for i, loss in enumerate([-1.0, 8.0])]})
    projection = controller.projection(search_id='SCRIPTED-policy-not-a-native-run', status='complete')
    assert [row['observation']['loss'] for row in projection['observations']] == [-1.0, 8.0]
    assert projection['current']['observation']['loss'] == 8.0
    assert projection['best']['loss'] == -1.0
    assert projection['errors'] == [] and projection['budget']['consumed'] == 2
