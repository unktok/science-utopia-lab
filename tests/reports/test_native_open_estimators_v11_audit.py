"""Read-only audit guards; fabricated fixtures are never Qwen result evidence."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.analyze_native_open_estimators_v11 import (
    ROOT, _inventory, _without_provenance, analyze, incumbent_path,
    matched_initial_definitions, replay_source_proofs,
)
from scripts.run_native_open_estimators_v11 import (
    ARM_IDS, ESTIMATOR_CONFIG, EXPERIMENT, SCHEMA, summarize,
)
from tests.optimization.test_native_adaptive_search import fail_factory, tiny_definition, tiny_parent
from utopia.optimization.loss import load_loss_spec
from utopia.optimization.native_adaptive_search import InboxVocabularyGenerator, NativeAdaptiveDesignCampaign
from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending, ManifestInbox
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def fixture(tmp_path):
    loss = load_loss_spec(ROOT / 'research/objectives/losses/native-joint-v5-net-reviewed-utility.json')
    world = {'source_commit': 'fixture-source', 'model_digest': 'fixture-model',
        'corpus_sha256': 'fixture-corpus', 'years': 2, 'corpus_years': 4,
        'classification': 'scripted-fixture-not-native-results'}
    methods = {'blackbox': {'mode': 'blackbox', 'expectation_estimator': None},
        'score-control-variate': {'mode': 'score', 'expectation_estimator': ESTIMATOR_CONFIG}}
    plan = {'schema': SCHEMA, 'world': world, 'loss_spec': loss, 'seed': 42,
        'generations': 2, 'draws_per_generation': 2, 'arm_ids': list(ARM_IDS), 'methods': methods,
        'population': {'authors': 5, 'conference_setting': 1}, 'shared_physical_trajectories': False,
        'scientific_benefit_required': False, 'structural_novelty_reward': False,
        'experiment': EXPERIMENT, 'initial_system': tiny_parent().to_dict()}
    campaigns = {arm: NativeAdaptiveDesignCampaign(tmp_path / 'arms' / arm / 'campaign',
        initial_system=tiny_parent(), loss_spec=loss, seeds=[42], world_binding=world,
        strategies={'design': {'kind': 'explicit-software-fixture'}}, seed=42, **methods[arm]) for arm in ARM_IDS}
    write_json_atomic(tmp_path / 'plan.json', plan, sort_keys=True, allow_nan=False)
    summarize(tmp_path, plan, campaigns)
    return plan, campaigns


def rewrite_raw(tmp_path, mutate):
    path = tmp_path / 'evidence.json'
    raw = json.loads(path.read_text())
    mutate(raw)
    raw.pop('content_sha256')
    raw['content_sha256'] = digest(raw)
    write_json_atomic(path, raw, sort_keys=True, allow_nan=False)


def complete_failed_batch(tmp_path, arm, campaign):
    inbox = ManifestInbox(tmp_path / 'arms' / arm / 'authoring')
    generator = InboxVocabularyGenerator(inbox, instructions='Scripted audit fixture; no live research claim.')
    try:
        campaign.advance(simulation_factory=fail_factory, generators={'design': generator}, count=2)
    except ExternalAuthoringPending as pending:
        write_json_atomic(pending.response_path, {'request_sha256': pending.request_sha256,
            'manifest': tiny_definition(), 'authoring': {'kind': 'external', 'purpose': 'software-fixture'}},
            sort_keys=True, allow_nan=False)
    return campaign.advance(simulation_factory=fail_factory, generators={'design': generator}, count=2)


def test_empty_incomplete_audit_is_byte_identical_and_read_only(tmp_path):
    fixture(tmp_path)
    before = _inventory(tmp_path)
    first = analyze(tmp_path, expected_source='fixture-source', require_complete=False)
    second = analyze(tmp_path, expected_source='fixture-source', require_complete=False)
    assert _inventory(tmp_path) == before
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first['status'] == 'in-progress' and first['physical_native_worlds'] == 0
    assert not first['claims']['live_fixed_Qwen_researchers']
    assert first['claims']['scripted_researcher_HTTP']
    assert first['audit']['new_model_calls'] == first['audit']['new_container_executions'] == 0
    with pytest.raises(ValueError, match='eight complete'):
        analyze(tmp_path, expected_source='fixture-source')


def test_failed_batches_keep_null_losses_and_exact_external_authoring(tmp_path):
    plan, campaigns = fixture(tmp_path)
    for arm in ARM_IDS:
        complete_failed_batch(tmp_path, arm, campaigns[arm])
    summarize(tmp_path, plan, campaigns)
    before = _inventory(tmp_path)
    audit = analyze(tmp_path, expected_source='fixture-source', require_complete=False)
    assert _inventory(tmp_path) == before
    assert audit['matched_initial_definitions']['matched']
    for arm in ARM_IDS:
        result = audit['arms'][arm]
        assert result['loss_path'] == [None, None]
        assert result['incumbents']['best_loss'] is None
        assert result['authoring_proofs'][0]['status'] == 'consumed'


@pytest.mark.parametrize('tamper', ['source', 'status', 'replies', 'claims', 'budget', 'arm'])
def test_rehashed_summary_tampering_is_rejected(tmp_path, tamper):
    fixture(tmp_path)
    def change(raw):
        if tamper == 'source': raw['source_commit'] = 'forged'
        if tamper == 'status': raw['status'] = 'complete'
        if tamper == 'replies': raw['physical_reply_count'] = 8
        if tamper == 'claims': raw['claims']['variance_reduction_established'] = True
        if tamper == 'budget': raw['planned_native_world_budget'] = 9
        if tamper == 'arm': raw['arms']['blackbox']['binding']['mode'] = 'score'
    rewrite_raw(tmp_path, change)
    with pytest.raises(ValueError): analyze(tmp_path, expected_source='fixture-source', require_complete=False)


def test_canonical_campaign_update_tampering_rejected_even_when_summary_matches(tmp_path):
    plan, campaigns = fixture(tmp_path)
    complete_failed_batch(tmp_path, ARM_IDS[0], campaigns[ARM_IDS[0]])
    state = campaigns[ARM_IDS[0]].state
    state['records'][0]['report']['strategy_after']['logits'][0] = 10.
    write_json_atomic(campaigns[ARM_IDS[0]].path, state, sort_keys=True, allow_nan=False)
    summarize(tmp_path, plan, campaigns)
    with pytest.raises(ValueError, match='update history'):
        analyze(tmp_path, expected_source='fixture-source', require_complete=False)


def test_all_best_ties_retained_and_failed_draws_not_scored():
    rows = [{'generation': i//2, 'draw_index': i%2, 'loss': loss,
        'observation_id': f'obs-{i}', 'system_fingerprint': f'system-{i}'}
        for i, loss in enumerate((2., None, 1., 1.))]
    result = incumbent_path(rows)
    assert result['best_loss'] == 1.
    assert [r['observation_id'] for r in result['best_observation_ties']] == ['obs-2', 'obs-3']
    assert result['path'][1]['best_loss_so_far'] == 2.
    assert not result['initial_unevaluated_system_scored']


def test_matching_initial_definition_does_not_erase_code_or_wiring():
    first = {'base_patch': {'operations': [{'code': 'exact source'}]},
        'provenance': {'arm': 'a'}, 'factors': [{'provenance': {'arm': 'a'}, 'id': 'same'}]}
    second = deepcopy(first)
    second['provenance'] = {'arm': 'b'}
    second['factors'][0]['provenance'] = {'arm': 'b'}
    arms = {ARM_IDS[0]: {'records': [{'definition': first}]}, ARM_IDS[1]: {'records': [{'definition': second}]}}
    assert matched_initial_definitions(arms)['matched']
    second['base_patch']['operations'][0]['code'] = 'changed source'
    with pytest.raises(ValueError, match='initial arm definitions differ'):
        matched_initial_definitions(arms)
    assert _without_provenance({'metadata': {'arm': 'a'}}) == {'metadata': {'arm': 'a'}}


def test_symlink_raw_rejected(tmp_path):
    fixture(tmp_path)
    (tmp_path / 'linked-plan.json').symlink_to(tmp_path / 'plan.json')
    with pytest.raises(ValueError, match='symlinks'):
        analyze(tmp_path, expected_source='fixture-source', require_complete=False)


def test_concurrent_raw_changes_fail_closed(tmp_path, monkeypatch):
    fixture(tmp_path)
    original = _inventory(tmp_path)
    calls = []
    def inventory(root):
        calls.append(1)
        return original if len(calls) == 1 else {**original, 'new-writer': 'modified'}
    monkeypatch.setattr('scripts.analyze_native_open_estimators_v11._inventory', inventory)
    with pytest.raises(ValueError, match='raw evidence changed'):
        analyze(tmp_path, expected_source='fixture-source', require_complete=False)


def test_replay_critical_source_matches_actual_pin_without_pinning_new_auditor(monkeypatch):
    monkeypatch.setattr('scripts.analyze_native_open_estimators_v11.subprocess.check_output',
        lambda argv, **kwargs: (ROOT / argv[-1].split(':', 1)[1]).read_bytes())
    result = replay_source_proofs('actual-source', 'actual-native-qwen-open-estimators-development-v11')
    assert result['status'] == 'verified-exact-replay-source-blobs'
    monkeypatch.setattr('scripts.analyze_native_open_estimators_v11.subprocess.check_output', lambda *a, **kw: b'changed')
    with pytest.raises(ValueError, match='replay-critical'):
        replay_source_proofs('actual-source', 'actual-native-qwen-open-estimators-development-v11')
