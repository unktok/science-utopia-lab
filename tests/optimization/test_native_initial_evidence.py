"""Pure historical-evidence/ask-tell tests; synthetic fixtures are not research."""
from copy import deepcopy
from pathlib import Path
import json

import pytest

from tests.optimization.test_native_world import loss_spec
from utopia.optimization.blackbox import Observation, Suggestion
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_initial_evidence import (build_initial_evidence,
    objective_view, select_incumbent, validate_initial_evidence)
from utopia.system.design_patch import digest
from utopia.system.native_kernel import legacy_world_system

WORLD = {'source_commit': 'historical-test-source', 'model': 'test-model', 'model_digest': 'test-model-id',
    'corpus_sha256': 'test-corpus', 'corpus_years': 4, 'dataset_identity': {'dataset': 'test-only'},
    'image_id': 'test-image', 'years': 2, 'population': 'five-scripted-test-researchers'}
TARGET = {**WORLD, 'source_commit': 'new-source-no-equivalence-claim'}
STRATEGIES = {'llm': {'kind': 'scripted-test-not-inference'}}


def hashed(value):
    value['content_sha256'] = digest({k: v for k, v in value.items() if k != 'content_sha256'})
    return value


def donor():
    system = legacy_world_system()
    candidate = system.to_dict()
    records = []
    for index, count in enumerate([2, 7, 7, None]):
        suggestion = Suggestion(f'suggestion-{index}', candidate, index, 'initial').to_dict()
        measurements = [] if count is None else [{'run_id': 'shared-cached-run' if count == 7 else f'run-{index}',
            'system_fingerprint': system.fingerprint,
            'metrics': {'native.accepted_decisions': {'status': 'measured', 'value': count}}}]
        evaluated = evaluate_loss(loss_spec(), measurements)
        observed = Observation(f'observation-{index}', suggestion['suggestion_id'], candidate,
            'failed' if count is None else 'complete', evaluated['loss'],
            {'world_backend': 'native-research-world', 'system_fingerprint': system.fingerprint,
             'loss_spec_sha256': loss_spec_sha256(loss_spec()), 'loss_evaluation': evaluated,
             'measurements': measurements, 'technical_failures': [{'error': 'test-failure'}] if count is None else [],
             'runs': [] if count is None else [{'seed': 42, 'system_fingerprint': system.fingerprint,
                'run_id': measurements[0]['run_id'], 'checkpoint_sha256': 'test-checkpoint'}]}).to_dict()
        records.append({'draws': [{'suggestion': suggestion, 'technical_error': None}],
            'observations': [observed], 'request_sha256': f'request-{index}', 'definition': {'test': index},
            'version_sha256': f'version-{index}', 'generation_error': None})
    records.append({'draws': [], 'observations': [], 'request_sha256': 'failed-request',
        'definition': {'generation_failure': 'test-only'}, 'version_sha256': 'failed-version',
        'generation_error': {'type': 'TestGenerationFailure', 'loss': None}})
    return hashed({'schema': 'scienceutopia.native-staged-search-audit.v15',
        'source_commit': WORLD['source_commit'], 'queue_terminal': True, 'budget_terminal': True,
        'audit': {'exact_raw_tools_draft_source_definition_replayed': True,
                  'own_history_loss_and_all_ties_replayed': True}, 'role_bindings': {'scientist': WORLD},
        'runs': {'fixture-arm': {'terminal': True, 'binding': {'world': WORLD, 'seeds': [42],
            'loss_spec': loss_spec()}, 'records': records}}})


def bank():
    audit = donor()
    return build_initial_evidence(audit, expected_audit_content_sha256=audit['content_sha256'],
                                 expected_source_commit=WORLD['source_commit'])


def campaign(path, evidence, objective=None):
    return NativeAdaptiveDesignCampaign(path, initial_system=legacy_world_system(),
        loss_spec=objective or loss_spec(), seeds=[42], world_binding=TARGET,
        strategies=STRATEGIES, mode='blackbox', initial_evidence=evidence)


def test_common_measurements_all_ties_technical_null_and_physical_identity_preserved():
    evidence = bank()
    before = deepcopy(evidence)
    first = objective_view(evidence, loss_spec())
    second = objective_view(evidence, loss_spec(coefficient=1.))
    assert evidence == before
    assert len(evidence['entries']) == 5 and len(first['observations']) == 4
    assert [p['observation']['loss'] for p in first['observations']] == [-2., -7., -7., None]
    assert second['selection']['loss'] == 2.
    assert len(first['selection']['tied_observation_ids']) == 2
    assert len(first['unobserved_slots']) == 1 and first['unobserved_slots'][0]['loss'] is None
    assert first['observations'][1]['observation']['metadata']['runs'] == first['observations'][2]['observation']['metadata']['runs']
    assert len({p['observation']['observation_id'] for p in first['observations']}) == 4
    assert first['observations'][0]['observation']['metadata']['historical_initial_evidence']['source_commit'] == WORLD['source_commit']
    assert not evidence['claims']['physical_cache_reuse_allowed']


def test_missing_objective_metric_is_null_not_zero_or_penalty():
    result = objective_view(bank(), loss_spec(metric='native.unmeasured'))
    assert all(p['observation']['loss'] is None for p in result['observations'])
    assert result['selection'] == {'loss': None, 'selected_observation_id': None, 'tied_observation_ids': []}
    assert [p['observation']['status'] for p in result['observations']] == ['invalid'] * 3 + ['failed']


@pytest.mark.parametrize('field', ['loss', 'candidate', 'metadata'])
def test_archived_observation_corruption_rejected_even_after_bank_rehash(field):
    evidence = bank()
    observed = evidence['entries'][0]['observation']
    if field == 'loss': observed['loss'] = -999.
    elif field == 'candidate': observed['candidate']['version'] += 1
    else: observed['metadata']['runs'][0]['checkpoint_sha256'] = 'forged-checkpoint'
    with pytest.raises(ValueError, match='archived'):
        validate_initial_evidence(hashed(evidence))


@pytest.mark.parametrize('field', ['model_digest', 'corpus_sha256', 'years', 'image_id', 'population'])
def test_non_source_world_mismatch_is_not_claimed_equivalent(field):
    target = {**TARGET, field: 'different'}
    with pytest.raises(ValueError, match='differs'):
        validate_initial_evidence(bank(), target_world=target, target_seeds=[42])
    with pytest.raises(ValueError, match='seeds'):
        validate_initial_evidence(bank(), target_world=TARGET, target_seeds=[43])


def test_donor_pin_and_duplicate_entry_rejected():
    audit = donor()
    with pytest.raises(ValueError, match='pinned'):
        build_initial_evidence(audit, expected_audit_content_sha256='wrong', expected_source_commit=WORLD['source_commit'])
    evidence = bank()
    evidence['entries'].append(deepcopy(evidence['entries'][0]))
    with pytest.raises(ValueError, match='repeated'):
        validate_initial_evidence(hashed(evidence))


def test_campaign_common_initial_evidence_objective_specific_selection_and_restart(tmp_path):
    evidence = bank()
    minimize_count = campaign(tmp_path / 'min', evidence, loss_spec(coefficient=1.))
    maximize_count = campaign(tmp_path / 'max', evidence)
    left = minimize_count._request([], minimize_count._strategy_initial(), 1)
    right = maximize_count._request([], maximize_count._strategy_initial(), 1)
    assert left['initial_evidence']['bank_sha256'] == right['initial_evidence']['bank_sha256']
    assert left['selection']['loss'] == 2. and right['selection']['loss'] == -7.
    assert left['history'] == right['history'] == []
    assert left['generation'] == right['generation'] == 0
    assert all(v['batches'] == 0 for v in maximize_count._strategy_initial()['statistics'].values())
    assert campaign(tmp_path / 'max', evidence).state == maximize_count.state
    changed = bank()
    changed['entries'].pop()
    with pytest.raises(ValueError, match='binding changed'):
        campaign(tmp_path / 'max', hashed(changed))
    assert left['initial_evidence']['source_equivalence_established'] is False
    assert left['initial_evidence']['physical_cache_reuse_allowed'] is False


def test_new_same_candidate_slot_is_not_deduplicated_or_replaced_by_historical_cache(tmp_path):
    evidence = bank()
    search = campaign(tmp_path, evidence)
    calls = []
    def unavailable_factory(*args):
        calls.append(args)
        raise RuntimeError('software-QA no native backend')
    def retain(request):
        assert len(request['observations']) == 4 and request['generation'] == 0
        return {'base_patch': None, 'factors': [], 'continuous': [], 'provenance': {'kind': 'test-retention'}}
    record = search.advance(simulation_factory=unavailable_factory, generators={'llm': retain}, count=1)
    assert len(calls) == 1
    assert len(search.state['records']) == 1 and len(record['draws']) == 1
    assert record['observations'][0]['loss'] is None
    request = search._request(search.state['records'], search._validate(), 1)
    assert len(request['observations']) == 5 and len(request['history']) == 1
    assert request['selection']['loss'] == -7.
    assert campaign(tmp_path, evidence).state == search.state


def test_new_complete_observation_competes_with_historical_incumbent_without_other_arm(tmp_path):
    search = campaign(tmp_path, bank())
    initial = search._request([], search._strategy_initial(), 1)
    pair = deepcopy(initial['observations'][0])
    pair['observation']['observation_id'] = 'new-own-only'
    pair['observation']['loss'] = -10.
    record = {'draws': [{'suggestion': pair['suggestion']}], 'observations': [pair['observation']],
        'request_sha256': 'unit-only', 'version_sha256': 'unit-only', 'definition': None,
        'generation_error': None, 'report': None}
    request = search._request([record], search._strategy_initial(), 1)
    assert request['based_on_observation_id'] == 'new-own-only'
    assert request['selection']['loss'] == -10.
    assert len(request['history']) == 1
    assert select_incumbent(initial['observations'])['loss'] == -7.


def test_optional_historical_audit_regression_keeps_all_eight_original_slots():
    path = Path('/Users/shiro/unktok/dev/science-utopia-lab/outputs/native-authoring-recovery-v44-a4-audit.json')
    if not path.exists(): pytest.skip('operator-local historical archive is intentionally outside Git')
    audit = json.loads(path.read_text())
    evidence = build_initial_evidence(audit,
        expected_audit_content_sha256='18ba247752ad258b6661091c254ef7f4383ea176eee0146fdd8a82fab9ca3366',
        expected_source_commit='60ef56ca2e32634c72817676b8bcc55bc9fcaa45')
    view = objective_view(evidence, audit['runs']['efficiency']['loss_spec'])
    assert len(evidence['entries']) == 8 and len(view['observations']) == 7
    assert len(view['unobserved_slots']) == 1
    assert view['selection']['loss'] == pytest.approx(-11.833333333333336)
    assert len(view['selection']['tied_observation_ids']) == 4
    assert [p['observation']['loss'] for p in view['observations']][:3] == [12., 12., None]
