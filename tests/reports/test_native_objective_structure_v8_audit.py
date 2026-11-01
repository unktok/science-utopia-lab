"""Synthetic contract tests only; no native/Qwen result is created here."""
from copy import deepcopy
from dataclasses import replace

import pytest

from scripts.analyze_native_objective_structure_v8 import (
    ARM_IDS, EXPERIMENT, RAW_SCHEMA, _validate_binding, _validate_plan, analyze,
    compact_attempt_report, cross_score_measurement,
    graph_change, objective_specs, select_representative,
)
from scripts.analyze_native_open_v7 import audit_native_run
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign, InboxVocabularyGenerator
from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending, ManifestInbox, audit_manifest_inbox
from utopia.system import ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, SystemSpec
from utopia.system.code_mechanisms import CODE_SCHEMA
from utopia.system.design_patch import digest
from utopia.system.native_kernel import legacy_world_system
from utopia.utils.data_utils import write_json_atomic


def system(source='def step(context):\n return {"outputs": {}, "state": {}}\n'):
    port = PortSpec('out', ChannelKind.ARTIFACT, 'x')
    node = MechanismSpec('source', MechanismFamily.CUSTOM, 'code.python.v1', outputs=(port,),
        parameters={'runtime_image_id': 'fixture-image', 'code_artifact': {'schema': CODE_SCHEMA,
            'label': 'synthetic fixture', 'source': source, 'inputs': {},
            'outputs': {'out': {'type': 'object'}}, 'state_schema': {'type': 'object'}}})
    sink = MechanismSpec('sink', MechanismFamily.CUSTOM, 'fixture.sink.v1',
        inputs=(PortSpec('in', ChannelKind.ARTIFACT, 'x'),))
    edge = ConnectionSpec('source', 'out', 'sink', 'in', ChannelKind.ARTIFACT)
    return SystemSpec('fixture', 1, mechanisms=(node, sink), connections=(edge,),
                      initial_state={'coordinate': 0.})


def plan():
    losses = objective_specs()
    initial = system().to_dict()
    world = {'source_commit': 'a'*40, 'model_digest': 'fixture-model',
        'corpus_sha256': 'fixture-corpus', 'years': 2, 'corpus_years': 4,
        'runtime_seed_binding': {}, 'experiment': EXPERIMENT, 'image_id': 'fixture-image',
        'classification': 'scripted-fixture-not-native-results'}
    return {'schema': RAW_SCHEMA, 'classification': 'scripted-fixture-not-native-results',
        'experiment': EXPERIMENT, 'world': world,
        'arm_ids': list(ARM_IDS), 'losses': [losses[key] for key in ARM_IDS], 'seed': 42,
        'generations': 2, 'draws_per_generation': 2,
        'population': {'authors': 5, 'conference_setting': 1}, 'mode': 'hybrid',
        'initial_system': initial, 'instructions': 'synthetic fixture only',
        'scientific_benefit_required': False, 'structural_novelty_reward': False,
        'shared_physical_trajectories': False,
        'external_designer_provider': 'self-reported Codex specialist'}


def test_frozen_plan_and_each_bound_loss_are_separate_from_metrics_and_promotion(monkeypatch):
    import scripts.analyze_native_objective_structure_v8 as audit
    value = plan(); losses = objective_specs()
    monkeypatch.setattr(audit, 'INSTRUCTIONS_SHA256', audit.digest(value['instructions']))
    _validate_plan(value, losses)
    binding = {'initial_system': value['initial_system'], 'loss_spec': losses[ARM_IDS[0]],
        'seeds': [42], 'world': value['world'], 'strategies': {}, 'mode': 'hybrid', 'seed': 42}
    assert _validate_binding(ARM_IDS[0], binding, 'a'*40, losses) == value['world']
    changed = dict(value, scientific_benefit_required=True)
    with pytest.raises(ValueError, match='plan differs'):
        _validate_plan(changed, losses)
    binding = {**binding, 'loss_spec': losses[ARM_IDS[1]]}
    with pytest.raises(ValueError, match='loss/source'):
        _validate_binding(ARM_IDS[0], binding, 'a'*40, losses)


def test_graph_change_reports_literal_node_edge_rewire_and_source_sets():
    before = system()
    changed_source = replace(before.mechanisms[0], parameters={**before.mechanisms[0].parameters,
        'code_artifact': {**before.mechanisms[0].parameters['code_artifact'],
            'source': before.mechanisms[0].parameters['code_artifact']['source'] + '# changed\n'}})
    extra = MechanismSpec('extra', MechanismFamily.CUSTOM, 'fixture.extra.v1')
    after = replace(before, mechanisms=(changed_source, before.mechanisms[1], extra),
        connections=(ConnectionSpec('source', 'out', 'sink', 'in', ChannelKind.ARTIFACT, latency=1),))
    diff = graph_change(before.to_dict(), after.to_dict())
    assert diff['nodes_added'] == ['extra'] and diff['nodes_removed'] == []
    assert diff['counts'] == {'nodes_added': 1, 'nodes_removed': 0, 'edges_added': 1,
        'edges_removed': 1, 'rewired_endpoint_pairs': 1, 'source_changes': 1,
        'source_bodies_added': 1, 'source_bodies_removed': 1,
        'same_source_body_renamed_ids': 0, 'protocol_changes': 0,
        'mechanism_configuration_changes': 1, 'schedules_added': 0, 'schedules_removed': 0,
        'initial_state_changes': 0}
    assert diff['source_changes'][0]['mechanism_id'] == 'source'


def test_source_id_rename_and_state_change_are_not_mislabeled_new_algorithm():
    before = system()
    renamed = replace(before.mechanisms[0], mechanism_id='renamed-source')
    after = replace(before, mechanisms=(renamed, before.mechanisms[1]),
        connections=(ConnectionSpec('renamed-source', 'out', 'sink', 'in', ChannelKind.ARTIFACT),),
        initial_state={'coordinate': .5})
    diff = graph_change(before.to_dict(), after.to_dict())
    assert diff['source_bodies_added'] == diff['source_bodies_removed'] == []
    assert diff['counts']['same_source_body_renamed_ids'] == 1
    assert diff['same_source_body_renamed_ids'][0]['before_mechanism_id'] == 'source'
    assert diff['initial_state_change']['changed']
    assert not diff['initial_state_change']['counts_as_new_algorithm']


def test_v7_shared_audit_defaults_remain_exact_and_new_parameters_are_keyword_only():
    # API-shape regression: old six positional arguments still bind exactly;
    # v8 bindings cannot silently displace the old classification argument.
    import inspect
    signature = inspect.signature(audit_native_run)
    assert signature.parameters['expected_experiment'].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters['expected_loss'].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters['expected_experiment'].default is None
    assert signature.parameters['expected_loss'].default is None


def test_missing_other_objective_metric_is_null_with_reason_not_dropped_or_penalized():
    losses = objective_specs()
    measurement = {'run_id': 'synthetic-cross-score-fixture', 'metrics': {
        'native.accepted_decisions': {'status': 'measured', 'value': 2},
        'native.review_records': {'status': 'measured', 'value': 3},
        'native.accepted_peer_score_sum': {'status': 'unavailable', 'reason': 'synthetic fixture missing'}}}
    scores, values = cross_score_measurement(measurement, losses, ARM_IDS[0], -2.)
    assert scores[ARM_IDS[0]]['status'] == 'complete' and values[ARM_IDS[0]] == -2.
    assert scores[ARM_IDS[1]]['status'] != 'complete' and values[ARM_IDS[1]] is None
    assert scores[ARM_IDS[1]]['rejected_runs'][0]['reason']


def selection_row(candidate, observation_id, suggestion_id, own_loss, other_loss):
    return {'status': 'complete',
        'draw': {'suggestion': {'suggestion_id': suggestion_id, 'candidate': candidate}},
        'observation': {'observation_id': observation_id, 'suggestion_id': suggestion_id},
        'cross_objective_losses': {ARM_IDS[0]: own_loss, ARM_IDS[1]: other_loss}}


def test_representative_is_exact_minimum_observation_not_first_matching_system_fingerprint():
    candidate = system().to_dict()
    rows = [selection_row(candidate, 'observation-first', 'suggestion-first', 4., 40.),
            selection_row(candidate, 'observation-best', 'suggestion-best', 1., 10.)]
    selection, representative = select_representative(rows, ARM_IDS[0])
    assert len(set(selection['tied_system_fingerprints'])) == 1
    assert selection['representative_observation_id'] == 'observation-best'
    assert selection['representative_suggestion_id'] == 'suggestion-best'
    assert representative is rows[1]
    assert representative['cross_objective_losses'][ARM_IDS[1]] == 10.


def test_equal_loss_duplicate_system_draws_preserve_both_tie_identities_and_earliest_row():
    candidate = system().to_dict()
    rows = [selection_row(candidate, 'observation-first', 'suggestion-first', 1., 40.),
            selection_row(candidate, 'observation-second', 'suggestion-second', 1., 10.)]
    selection, representative = select_representative(rows, ARM_IDS[0])
    assert selection['tie_count'] == 2
    assert selection['tied_system_fingerprints'] == [
        SystemSpec.from_dict(candidate).fingerprint, SystemSpec.from_dict(candidate).fingerprint]
    assert selection['tied_observation_ids'] == ['observation-first', 'observation-second']
    assert selection['tied_suggestion_ids'] == ['suggestion-first', 'suggestion-second']
    assert selection['representative_observation_id'] == 'observation-first'
    assert selection['representative_suggestion_id'] == 'suggestion-first'
    assert representative is rows[0]


@pytest.mark.parametrize('duplicate', ['observation', 'suggestion'])
def test_representative_selection_rejects_reused_exact_row_identity(duplicate):
    candidate = system().to_dict()
    rows = [selection_row(candidate, 'observation-1', 'suggestion-1', 2., 20.),
            selection_row(candidate, 'observation-2', 'suggestion-2', 1., 10.)]
    if duplicate == 'observation':
        rows[1]['observation']['observation_id'] = 'observation-1'
    else:
        rows[1]['draw']['suggestion']['suggestion_id'] = 'suggestion-1'
        rows[1]['observation']['suggestion_id'] = 'suggestion-1'
    with pytest.raises(ValueError, match='reuse'):
        select_representative(rows, ARM_IDS[0])


def test_full_failed_fixture_replays_read_only_without_fabricating_losses(tmp_path, monkeypatch):
    """Complete declared budget with generation/draw failures, not empirical evidence."""
    import json
    import scripts.analyze_native_objective_structure_v8 as audit
    raw = tmp_path / 'raw'; raw.mkdir()
    value = plan()
    parent = replace(legacy_world_system(), initial_state={'coordinate': 0.})
    value['initial_system'] = parent.to_dict()
    value['instructions'] = 'Synthetic fixture instructions; no model or native result.'
    monkeypatch.setattr(audit, 'INSTRUCTIONS_SHA256', digest(value['instructions']))
    write_json_atomic(raw / 'plan.json', value, sort_keys=True, allow_nan=False)
    losses = objective_specs()
    strategies = {name: {'kind': 'synthetic-fixture', 'scope': name} for name in ('invent', 'revise')}

    def definition(generation):
        factors = ([{'id': 'invalid-choice', 'kind': 'bernoulli', 'choices': [
            {'id': 'left', 'operations': [], 'provenance': {'kind': 'synthetic-fixture'}},
            {'id': 'right', 'operations': [{'op': 'remove', 'path': '/mechanisms/0'}],
             'provenance': {'kind': 'synthetic-fixture'}}]}] if generation == 0 else [])
        return {'base_patch': None, 'factors': factors, 'continuous': [{'id': 'coordinate',
            'path': '/initial_state/coordinate', 'lower': -1., 'upper': 1., 'mean': 0., 'sigma': .2}],
            'provenance': {'kind': 'synthetic-fixture-not-native-result'}}

    def failed_factory(*_args):
        raise RuntimeError('intentional synthetic fixture infrastructure failure')

    campaigns = {}
    for identity in ARM_IDS:
        directory = raw / 'arms' / identity
        kwargs = {'initial_system': parent, 'loss_spec': losses[identity], 'seeds': [42],
            'world_binding': value['world'], 'strategies': strategies, 'mode': 'hybrid', 'seed': 42}
        campaign = NativeAdaptiveDesignCampaign(directory / 'campaign', **kwargs)
        generator = InboxVocabularyGenerator(ManifestInbox(directory / 'authoring'),
                                              instructions=value['instructions'])
        for _generation in range(2):
            try:
                campaign.advance(simulation_factory=failed_factory,
                    generators={key: generator for key in strategies}, count=2)
            except ExternalAuthoringPending as pending:
                request = json.loads(pending.request_path.read_text())
                write_json_atomic(pending.response_path, {'request_sha256': pending.request_sha256,
                    'manifest': definition(request['request']['authoring_input']['generation']),
                    'authoring': {'kind': 'external', 'fixture': True}},
                    sort_keys=True, allow_nan=False)
                campaign = NativeAdaptiveDesignCampaign(directory / 'campaign', **kwargs)
                campaign.advance(simulation_factory=failed_factory,
                    generators={key: generator for key in strategies}, count=2)
        campaigns[identity] = campaign

    arms = {identity: {'binding': campaign.binding, 'records': campaign.state['records'],
        'pending': campaign.state['pending'],
        'authoring': audit_manifest_inbox(raw / 'arms' / identity / 'authoring')}
        for identity, campaign in campaigns.items()}
    # Preserve an interrupted declared physical attempt that reached system.json
    # but never opened a response journal. It remains null, not a ninth result.
    draw = campaigns[ARM_IDS[0]].state['records'][1]['draws'][0]
    partial = raw / 'worlds' / (draw['suggestion']['suggestion_id'] + '-s42')
    partial.mkdir(parents=True)
    write_json_atomic(partial / 'system.json', draw['suggestion']['candidate'],
                      sort_keys=True, allow_nan=False)
    evidence = {'schema': RAW_SCHEMA, 'classification': value['classification'],
        'source_commit': 'a'*40, 'plan': value, 'status': 'budget-complete-with-failures',
        'budget_terminal': True, 'planned_native_world_budget': 8, 'committed_draws': 4,
        'complete_native_worlds': 0, 'technical_failures': 6,
        'configured_researcher_provider': 'qwen3:8b', 'physical_reply_count': 0,
        'physical_response_caches': [], 'arms': arms,
        'claims': {'live_fixed_Qwen_researchers': False, 'scripted_researcher_HTTP': False,
            'held_out': False, 'causal_institutional_benefit': False, 'scientific_value': False,
            'designer_improvement_established': False, 'full_native_world_pathwise_autograd': False,
            'external_authorship_authenticated': False}}
    evidence['content_sha256'] = digest(evidence)
    write_json_atomic(raw / 'evidence.json', evidence, sort_keys=True, allow_nan=False)
    report = analyze(raw, expected_source='a'*40)
    assert report['status'] == 'budget-complete-with-failures'
    assert report['completed_physical_worlds'] == 0 and report['new_model_calls'] == 0
    assert report['physical_world_directory_count'] == 1
    assert report['partial_physical_worlds'][0]['status'] == 'partial-before-response-journal'
    assert all(len(arm['generation_failures']) == 1 for arm in report['arms'].values())
    assert all(row['status'] in {'generation-failure', 'technical-failure'}
        and row['cross_objective_losses'] == {ARM_IDS[0]: None, ARM_IDS[1]: None}
        for arm in report['arms'].values() for row in arm['rows'])
    from scripts.figures.native_objective_structure_v8 import figure_data
    plotted = figure_data(report)
    assert all(any(row['status'] == 'generation-failure' for row in arm['rows'])
               for arm in plotted['arms'].values())
    assert report['held_out_metrics'] == {'status': 'not-defined-or-measured'}
    compact = compact_attempt_report(report, attempt_id='fixture-complete')
    assert compact['schema'].endswith('attempt-audit.v8')
    assert compact['full_audit_content_sha256'] == report['content_sha256']
    assert compact['raw_file_hashes'] == report['raw_file_hashes']
    assert compact['execution_accounting']['budget_terminal'] is True

    # Exercise the strict aborted-preflight receipt contract separately.  The
    # invalid-vocabulary records above still come from the real controller;
    # this copy only models the earlier freeze point before generation 1 was
    # externally answered.
    frozen = deepcopy(report)
    frozen['status'] = 'in-progress'
    frozen['physical_world_directory_count'] = 0
    frozen['partial_physical_worlds'] = []
    frozen['raw_campaign_summary'].update(committed_draws=0, technical_failures=2,
        budget_terminal=False, status='in-progress', physical_reply_count=0)
    for arm in frozen['arms'].values():
        arm['records'] = arm['records'][:1]
        arm['rows'] = arm['rows'][:1]
        arm['loss_path'] = arm['loss_path'][:1]
        arm['pending'] = deepcopy(report['arms'][ARM_IDS[0]]['records'][1])
        arm['pending']['generated'] = False
        arm['pending']['compiled'] = False
        arm['pending']['version_sha256'] = None
        arm['pending']['generation_error'] = None
        arm['pending']['draws'] = []
        arm['pending']['observations'] = []
        arm['selection'] = {**arm['selection'], 'best_loss': None, 'tie_count': 0,
            'tied_system_fingerprints': [], 'representative_system_fingerprint': None}
    frozen['selected_cross_objective_matrix'] = {identity: None for identity in ARM_IDS}
    frozen['content_sha256'] = digest({key: value for key, value in frozen.items()
                                       if key != 'content_sha256'})
    aborted = compact_attempt_report(frozen, attempt_id='fixture-a1',
                                     aborted_technical_preflight=True)
    assert aborted['attempt_status'] == 'aborted-technical-preflight-incomplete-budget'
    assert all(arm['records'][0]['draw_count'] == 0 for arm in aborted['arms'].values())
    assert all(arm['pending']['generation'] == 1 for arm in aborted['arms'].values())
    assert aborted['execution_accounting']['complete_native_worlds'] == 0
