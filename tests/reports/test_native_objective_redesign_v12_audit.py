"""Synthetic audit contracts; these tests never supply actual-Qwen evidence."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from scripts.analyze_native_objective_redesign_v12 import (
    ACTUAL, ARM_IDS, EXPERIMENT, RAW_SCHEMA, ROOT, _inventory, _validate_plan, analyze,
    design_change, executable_contracts, objective_specs,
)
from scripts.analyze_native_open_estimators_v11 import incumbent_path
from scripts.analyze_native_objective_structure_v8 import cross_score_measurement
from tests.optimization.test_native_adaptive_search import fail_factory, tiny_definition, tiny_parent
from tests.reports.test_native_objective_structure_v8_audit import system
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign, InboxVocabularyGenerator
from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending, ManifestInbox, audit_manifest_inbox
from utopia.system.design_patch import digest
from utopia.system.native_process import controlled_activity
from utopia.utils.data_utils import write_json_atomic


def save(path, value):
    write_json_atomic(path, value, sort_keys=True, allow_nan=False)


def fixture(root):
    losses = objective_specs()
    world = {'source_commit': 'fixture-source', 'classification': 'scripted-fixture-not-native-results',
        'model_digest': 'fixture-model', 'corpus_sha256': 'fixture-corpus',
        'years': 2, 'corpus_years': 4, 'experiment': EXPERIMENT}
    plan = {'schema': RAW_SCHEMA, 'classification': world['classification'], 'experiment': EXPERIMENT,
        'world': world, 'arm_ids': list(ARM_IDS), 'losses': [losses[k] for k in ARM_IDS],
        'seed': 42, 'generations': 3, 'draws_per_generation': 1, 'mode': 'blackbox',
        'population': {'authors': 5, 'conference_setting': 1},
        'shared_physical_trajectories': False, 'scientific_benefit_required': False,
        'structural_novelty_reward': False, 'external_designer_provider': 'self-reported Codex specialist',
        'instructions': 'Synthetic contract fixture only; no actual researcher or model evidence.',
        'initial_system': tiny_parent().to_dict()}
    save(root / 'plan.json', plan)
    campaigns = {identity: NativeAdaptiveDesignCampaign(root / 'arms' / identity / 'campaign',
        initial_system=tiny_parent(), loss_spec=losses[identity], seeds=[42], world_binding=world,
        strategies={'design': {'kind': 'explicit-software-fixture'}}, mode='blackbox', seed=42)
        for identity in ARM_IDS}
    summarize(root, plan, campaigns)
    return plan, campaigns


def summarize(root, plan, campaigns):
    arms, committed, failures, complete = {}, 0, 0, 0
    for identity, campaign in campaigns.items():
        arms[identity] = {'binding': campaign.binding, 'records': campaign.state['records'],
            'pending': campaign.state['pending'], 'authoring': audit_manifest_inbox(root / 'arms' / identity / 'authoring')}
        for record in campaign.state['records']:
            failures += bool(record['generation_error'])
            for draw, observation in zip(record['draws'], record['observations']):
                committed += 1
                valid = observation and observation['status'] == 'complete' and not observation['metadata'].get('technical_failures')
                complete += bool(valid)
                failures += not bool(valid)
    terminal = all(len(c.state['records']) == 3 and c.state['pending'] is None for c in campaigns.values())
    value = {'schema': RAW_SCHEMA, 'classification': plan['classification'], 'source_commit': 'fixture-source',
        'plan': plan, 'arms': arms, 'status': 'complete' if terminal and complete == 6 and not failures else
            'budget-complete-with-failures' if terminal else 'in-progress',
        'budget_terminal': terminal, 'planned_native_world_budget': 6,
        'committed_draws': committed, 'complete_native_worlds': complete, 'technical_failures': failures,
        'physical_response_caches': [], 'physical_reply_count': 0, 'configured_researcher_provider': 'qwen3:8b',
        'claims': {'live_fixed_Qwen_researchers': False, 'scripted_researcher_HTTP': False,
            'held_out': False, 'causal_institutional_benefit': False, 'scientific_value': False,
            'designer_improvement_established': False, 'full_native_world_pathwise_autograd': False,
            'external_authorship_authenticated': False}}
    value['content_sha256'] = digest(value)
    save(root / 'evidence.json', value)


def failed_generation(root, identity, campaign, instructions, *, invalid_definition=False):
    generator = InboxVocabularyGenerator(ManifestInbox(root / 'arms' / identity / 'authoring'), instructions=instructions)
    try:
        campaign.advance(simulation_factory=fail_factory, generators={'design': generator}, count=1)
    except ExternalAuthoringPending as pending:
        definition = tiny_definition()
        if invalid_definition:
            definition['factors'][0]['kind'] = 'invalid-fixture-kind'
        save(pending.response_path, {'request_sha256': pending.request_sha256, 'manifest': definition,
            'authoring': {'kind': 'external', 'purpose': 'scripted-software-QA'}})
    campaign.advance(simulation_factory=fail_factory, generators={'design': generator}, count=1)


def mutate_raw(root, fn):
    value = json.loads((root / 'evidence.json').read_text())
    fn(value)
    value.pop('content_sha256')
    value['content_sha256'] = digest(value)
    save(root / 'evidence.json', value)


def test_empty_repeated_audit_is_byte_identical_and_read_only(tmp_path):
    fixture(tmp_path)
    before = _inventory(tmp_path)
    first = analyze(tmp_path, expected_source='fixture-source', require_complete=False)
    second = analyze(tmp_path, expected_source='fixture-source', require_complete=False)
    assert _inventory(tmp_path) == before
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first['objective_order'] == list(ARM_IDS)
    assert first['physical_native_worlds'] == 0
    assert first['audit']['new_model_calls'] == first['audit']['new_container_executions'] == 0
    assert first['claims']['scripted_researcher_HTTP']
    with pytest.raises(ValueError, match='terminal'):
        analyze(tmp_path, expected_source='fixture-source')


def test_all_failed_draws_retained_across_three_generations_with_no_numeric_penalty(tmp_path):
    plan, campaigns = fixture(tmp_path)
    for identity, campaign in campaigns.items():
        for generation in range(3):
            failed_generation(tmp_path, identity, campaign, plan['instructions'], invalid_definition=generation == 1)
    summarize(tmp_path, plan, campaigns)
    before = _inventory(tmp_path)
    result = analyze(tmp_path, expected_source='fixture-source')
    assert result['status'] == 'budget-complete-with-failures'
    assert result['physical_native_worlds'] == 0 and _inventory(tmp_path) == before
    for arm in result['arms'].values():
        assert arm['loss_path'] == [None, None, None]
        assert [row['status'] for row in arm['observations']] == ['technical-failure', 'generation-failure', 'technical-failure']
        assert arm['selection']['tie_count'] == 0
        assert all(row['cross_scores'] == {k:None for k in ARM_IDS} for row in arm['observations'])
        assert [proof['generation'] for proof in arm['authoring_proofs']] == [0, 1, 2]


@pytest.mark.parametrize('tamper', ['source', 'status', 'budget', 'replies', 'loss', 'veto', 'claim', 'arm', 'instructions'])
def test_rehashed_summary_and_frozen_plan_tampering_rejected(tmp_path, tamper):
    fixture(tmp_path)
    def change(value):
        if tamper == 'source': value['source_commit'] = 'forged'
        if tamper == 'status': value['status'] = 'complete'
        if tamper == 'budget': value['planned_native_world_budget'] = 7
        if tamper == 'replies': value['physical_reply_count'] = 6
        if tamper == 'claim': value['claims']['held_out'] = True
        if tamper == 'arm': value['arms'][ARM_IDS[0]]['binding']['mode'] = 'score'
        if tamper in ('loss', 'veto', 'instructions'):
            plan = deepcopy(value['plan'])
            if tamper == 'loss': plan['losses'][0]['per_run']['terms'][0]['coefficient'] = -100.
            if tamper == 'veto': plan['scientific_benefit_required'] = True
            if tamper == 'instructions': plan['instructions'] = ''
            value['plan'] = plan
            save(tmp_path / 'plan.json', plan)
    mutate_raw(tmp_path, change)
    with pytest.raises(ValueError):
        analyze(tmp_path, expected_source='fixture-source', require_complete=False)


def test_optimizer_update_tampering_rejected_after_matching_summary(tmp_path):
    plan, campaigns = fixture(tmp_path)
    identity = ARM_IDS[0]
    failed_generation(tmp_path, identity, campaigns[identity], plan['instructions'])
    campaigns[identity].state['records'][0]['report']['strategy_after']['logits'][0] = 9.
    save(campaigns[identity].path, campaigns[identity].state)
    summarize(tmp_path, plan, campaigns)
    with pytest.raises(ValueError, match='update history'):
        analyze(tmp_path, expected_source='fixture-source', require_complete=False)


def test_renaming_source_body_does_not_count_as_new_algorithm():
    before = system()
    node = replace(before.mechanisms[0], mechanism_id='renamed')
    after = replace(before, mechanisms=(node,), connections=())
    result = design_change(before.to_dict(), after.to_dict())
    assert result['source_bodies_added'] == result['source_bodies_removed'] == []
    assert result['counts']['same_source_body_renamed_ids'] == 1
    assert 'do not by themselves establish' in result['scope']
    contract = executable_contracts(after.to_dict())['executable_sources']['renamed']
    assert contract['source'] == before.mechanisms[0].parameters['code_artifact']['source']
    assert contract['source_sha256'] != contract['source_value_sha256']


def test_process_repetition_guard_and_delegate_differences_are_reported_not_inferred():
    before = system()
    first = controlled_activity(before.mechanisms[0], count=1, limit=3)
    second = controlled_activity(before.mechanisms[0], count=2, limit=3)
    one, two = replace(before, mechanisms=(first,), connections=()), replace(before, mechanisms=(second,), connections=())
    change = design_change(one.to_dict(), two.to_dict())
    assert change['counts']['process_contract_changes'] == 1
    assert change['process_contract_changes'][0]['before']['count'] != change['process_contract_changes'][0]['after']['count']
    assert change['source_bodies_added'] == change['source_bodies_removed'] == []


def test_same_checkpoint_crossscore_is_loss_specific_not_heldout():
    metrics = {'native.accepted_decisions': {'status': 'measured', 'value': 2},
        'native.accepted_peer_score_sum': {'status': 'measured', 'value': 7.},
        'native.review_records': {'status': 'measured', 'value': 10}}
    _, cross = cross_score_measurement({'run_id': 'fixture', 'metrics': metrics}, objective_specs(), ARM_IDS[0], -2.)
    assert cross[ARM_IDS[0]] == -2. and cross[ARM_IDS[1]] == 0.


def test_exact_observation_ties_survive_duplicate_systems_and_failed_rows():
    rows = [{'generation': i, 'draw_index': 0, 'loss': loss,
        'observation_id': f'obs-{i}', 'system_fingerprint': 'same-system'} for i, loss in enumerate((2., None, 2.))]
    result = incumbent_path(rows)
    assert [row['observation_id'] for row in result['best_observation_ties']] == ['obs-0', 'obs-2']
    assert result['path'][1]['best_loss_so_far'] == 2.


def test_symlink_and_concurrent_mutation_rejected(tmp_path, monkeypatch):
    fixture(tmp_path)
    before = _inventory(tmp_path)
    calls = []
    def inventory(root):
        calls.append(1)
        return before if len(calls) == 1 else {**before, 'writer': 'changed'}
    monkeypatch.setattr('scripts.analyze_native_objective_redesign_v12._inventory', inventory)
    with pytest.raises(ValueError, match='raw evidence changed'):
        analyze(tmp_path, expected_source='fixture-source', require_complete=False)


def test_undeclared_world_rejected_even_without_response_cache(tmp_path):
    fixture(tmp_path)
    (tmp_path / 'worlds/undeclared-world').mkdir(parents=True)
    with pytest.raises(ValueError, match='undeclared'):
        analyze(tmp_path, expected_source='fixture-source', require_complete=False)


def test_actual_instructions_are_exactly_bound_to_trusted_driver(tmp_path):
    from scripts.run_native_objective_redesign_v12 import INSTRUCTIONS
    plan, _ = fixture(tmp_path)
    plan = deepcopy(plan)
    plan.update(classification=ACTUAL, instructions=INSTRUCTIONS)
    plan['world'].update(classification=ACTUAL, source_commit='a'*40)
    raw = json.loads((tmp_path / 'evidence.json').read_text())
    raw.update(classification=ACTUAL, source_commit='a'*40, plan=plan)
    raw.pop('content_sha256'); raw['content_sha256'] = digest(raw)
    assert _validate_plan(raw, plan, 'a'*40)[1] == ACTUAL
    plan['instructions'] += ' Add a hidden quality veto.'
    raw['plan'] = plan
    raw.pop('content_sha256'); raw['content_sha256'] = digest(raw)
    with pytest.raises(ValueError, match='instructions'):
        _validate_plan(raw, plan, 'a'*40)


def test_raw_symlink_is_rejected(tmp_path):
    fixture(tmp_path)
    (tmp_path / 'linked-plan.json').symlink_to(tmp_path / 'plan.json')
    with pytest.raises(ValueError, match='symlinks'):
        analyze(tmp_path, expected_source='fixture-source', require_complete=False)
