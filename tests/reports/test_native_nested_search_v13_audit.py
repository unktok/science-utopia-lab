"""Read-only finite nesting contracts, not actual-Qwen evidence."""
from copy import deepcopy
import json

import pytest

from scripts import analyze_native_nested_search_v13 as audit
from scripts.run_native_nested_search_v13 import summarize, INSTRUCTIONS
from tests.optimization.test_native_adaptive_search import tiny_definition, tiny_parent, fail_factory
from utopia.optimization.native_adaptive_search import InboxVocabularyGenerator
from utopia.optimization.native_manifest_inbox import ManifestInbox, ExternalAuthoringPending
from utopia.optimization.native_nested_search import NativeNestedDesignCampaign, STAGES
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def save(path, value):
    write_json_atomic(path, value, sort_keys=True, allow_nan=False)


def fixture(root):
    losses = audit.objective_specs()
    world = {'source_commit': 'fixture-source', 'classification': audit.FIXTURE,
        'model_digest': 'fixture-model', 'corpus_sha256': 'fixture-corpus',
        'years': 2, 'corpus_years': 4, 'experiment': audit.EXPERIMENT}
    plan = {'schema': audit.RAW_SCHEMA, 'classification': audit.FIXTURE,
        'experiment': audit.EXPERIMENT, 'world': world, 'arm_ids': list(audit.ARM_IDS),
        'losses': [losses[k] for k in audit.ARM_IDS], 'seed': 42,
        'stages': list(STAGES), 'stage_counts': [2, 1, 1], 'learning_rate': .1,
        'population': {'authors': 5, 'conference_setting': 1},
        'mode': 'free-vocabulary-LOO-update-forward-free-redesign-forward',
        'scientific_benefit_required': False, 'structural_novelty_reward': False,
        'shared_physical_trajectories': False, 'external_designer_provider': 'self-reported Codex specialist',
        'initial_system': tiny_parent().to_dict(), 'instructions': 'Explicit synthetic software QA; no native results.'}
    save(root/'plan.json', plan)
    campaigns = {identity: NativeNestedDesignCampaign(root/'arms'/identity/'campaign',
        initial_system=tiny_parent(), loss_spec=losses[identity], seeds=[42], world_binding=world)
        for identity in audit.ARM_IDS}
    summarize(root, plan, campaigns)
    return plan, campaigns


def advance(root, identity, campaign, instructions, invalid=False):
    generator = InboxVocabularyGenerator(ManifestInbox(root/'arms'/identity/'authoring'), instructions=instructions)
    try:
        return campaign.advance(simulation_factory=fail_factory, generator=generator)
    except ExternalAuthoringPending as waiting:
        definition = {'invalid': 'unit-only null vocabulary'} if invalid else tiny_definition()
        save(waiting.response_path, {'request_sha256': waiting.request_sha256, 'manifest': definition,
            'authoring': {'kind': 'external', 'purpose': 'scripted-software-QA'}})
    return campaign.advance(simulation_factory=fail_factory, generator=generator)


def test_empty_incomplete_audit_twice_byte_identical_and_read_only(tmp_path):
    fixture(tmp_path)
    before = audit._inventory(tmp_path)
    first = audit.analyze(tmp_path, expected_source='fixture-source', require_complete=False)
    second = audit.analyze(tmp_path, expected_source='fixture-source', require_complete=False)
    assert first == second and audit._inventory(tmp_path) == before
    assert first['consumed_native_slots'] == first['physical_native_worlds'] == 0
    assert first['audit']['new_model_calls'] == first['audit']['new_container_executions'] == 0
    assert first['claims']['scripted_researcher_HTTP'] and not first['claims']['live_fixed_Qwen_researchers']
    with pytest.raises(ValueError, match='terminal'):
        audit.analyze(tmp_path, expected_source='fixture-source')


@pytest.mark.parametrize('invalid_initial', [False, True])
def test_all_failed_actual_or_unavailable_slots_preserved_without_fake_worlds(tmp_path, invalid_initial):
    plan, campaigns = fixture(tmp_path)
    for identity, campaign in campaigns.items():
        for index in range(3):
            advance(tmp_path, identity, campaign, plan['instructions'], invalid=invalid_initial and index == 0)
    summarize(tmp_path, plan, campaigns)
    before = audit._inventory(tmp_path)
    result = audit.analyze(tmp_path, expected_source='fixture-source')
    assert result['status'] == 'budget-complete-with-failures'
    assert result['physical_native_worlds'] == 0 and result['consumed_native_slots'] == 8
    assert audit._inventory(tmp_path) == before
    for arm in result['arms'].values():
        assert len(arm['authoring_proofs']) == 2
        assert arm['selection']['tie_count'] == 0
        assert arm['loss_path'] == [None]*(3 if invalid_initial else 4)
        assert all(row['cross_scores'] == {identity: None for identity in audit.ARM_IDS} for row in arm['observations'])
        if invalid_initial:
            assert [r['status'] for r in arm['observations']] == ['generation-failure', 'generation-failure', 'technical-failure']
            assert arm['observations'][0]['draw_index'] is None
            assert arm['observations'][0]['scheduled_native_slots'] == 2
        else:
            assert [r['stage'] for r in arm['observations']] == ['initial-batch', 'initial-batch', 'updated-proposal', 'redesign']


def test_exact_pending_external_request_audits_without_consumption(tmp_path):
    plan, campaigns = fixture(tmp_path)
    identity = audit.ARM_IDS[0]
    generator = InboxVocabularyGenerator(ManifestInbox(tmp_path/'arms'/identity/'authoring'), instructions=plan['instructions'])
    with pytest.raises(ExternalAuthoringPending):
        campaigns[identity].advance(simulation_factory=fail_factory, generator=generator)
    summarize(tmp_path, plan, campaigns)
    before = audit._inventory(tmp_path)
    result = audit.analyze(tmp_path, expected_source='fixture-source', require_complete=False)
    assert audit._inventory(tmp_path) == before
    assert result['arms'][identity]['authoring_proofs'][0]['status'] == 'awaiting-external-consumption'


@pytest.mark.parametrize('kind', ['source', 'status', 'budget', 'slots', 'replies', 'claim', 'loss', 'veto', 'stage', 'lr'])
def test_rehashed_plan_or_summary_tampering_rejected(tmp_path, kind):
    fixture(tmp_path)
    raw = json.loads((tmp_path/'evidence.json').read_text())
    if kind == 'source': raw['source_commit'] = 'forged'
    if kind == 'status': raw['status'] = 'complete'
    if kind == 'budget': raw['planned_native_world_budget'] = 9
    if kind == 'slots': raw['consumed_native_slots'] = 1
    if kind == 'replies': raw['physical_reply_count'] = 10
    if kind == 'claim': raw['claims']['variance_reduction_established'] = True
    if kind in {'loss', 'veto', 'stage', 'lr'}:
        if kind == 'loss': raw['plan']['losses'][0]['per_run']['terms'][0]['coefficient'] = -999.
        if kind == 'veto': raw['plan']['scientific_benefit_required'] = True
        if kind == 'stage': raw['plan']['stage_counts'] = [2, 2, 1]
        if kind == 'lr': raw['plan']['learning_rate'] = .2
        save(tmp_path/'plan.json', raw['plan'])
    raw.pop('content_sha256'); raw['content_sha256'] = digest(raw)
    save(tmp_path/'evidence.json', raw)
    with pytest.raises(ValueError):
        audit.analyze(tmp_path, expected_source='fixture-source', require_complete=False)


def test_saved_sole_update_forgery_rejected_even_when_summary_agrees(tmp_path):
    plan, campaigns = fixture(tmp_path)
    identity = audit.ARM_IDS[0]
    advance(tmp_path, identity, campaigns[identity], plan['instructions'])
    campaigns[identity].state['records'][0]['report']['weights_after']['continuous_mean'][0] += 1.
    save(campaigns[identity].path, campaigns[identity].state)
    summarize(tmp_path, plan, campaigns)
    with pytest.raises(ValueError):
        audit.analyze(tmp_path, expected_source='fixture-source', require_complete=False)


def test_actual_driver_instructions_bound_exactly(tmp_path):
    plan, _ = fixture(tmp_path)
    plan = deepcopy(plan)
    plan['classification'] = audit.ACTUAL
    plan['instructions'] = INSTRUCTIONS
    plan['world'].update(classification=audit.ACTUAL, source_commit='a'*40)
    plan['world'].update(model_digest='b'*64, corpus_sha256='c'*64,
        runtime_seed_binding={'python_hash_seed_environment': '42', 'python_hash_probe': -42})
    raw = json.loads((tmp_path/'evidence.json').read_text())
    raw.update(plan=plan, classification=audit.ACTUAL, source_commit='a'*40)
    raw.pop('content_sha256'); raw['content_sha256'] = digest(raw)
    assert audit._validate_plan(raw, plan, 'a'*40)[1] == audit.ACTUAL
    plan['instructions'] += ' Hidden veto.'
    raw.pop('content_sha256'); raw['content_sha256'] = digest(raw)
    with pytest.raises(ValueError, match='contract'):
        audit._validate_plan(raw, plan, 'a'*40)


def test_symlink_undeclared_directory_and_concurrent_writer_rejected(tmp_path, monkeypatch):
    fixture(tmp_path)
    (tmp_path/'linked.json').symlink_to(tmp_path/'plan.json')
    with pytest.raises(ValueError, match='symlinks'):
        audit.analyze(tmp_path, expected_source='fixture-source', require_complete=False)
    (tmp_path/'linked.json').unlink()
    (tmp_path/'worlds/undeclared').mkdir(parents=True)
    with pytest.raises(ValueError, match='undeclared'):
        audit.analyze(tmp_path, expected_source='fixture-source', require_complete=False)
    before = audit._inventory(tmp_path)
    calls = []
    def inventory(root):
        calls.append(True)
        return before if len(calls) == 1 else {**before, 'concurrent-writer': 'changed'}
    monkeypatch.setattr(audit, '_inventory', inventory)
    with pytest.raises(ValueError, match='raw evidence changed'):
        audit.analyze(tmp_path, expected_source='fixture-source', require_complete=False)
