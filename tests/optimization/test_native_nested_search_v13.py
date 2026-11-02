"""Finite nesting units and actual original-world SCRIPTED QA, not findings."""
import json

import pytest
import torch

from tests.optimization.test_native_adaptive_search import (
    WORLD, PROVENANCE, tiny_parent, tiny_definition, loss_spec, fail_factory)
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.blackbox import Observation
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign, InboxVocabularyGenerator
from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending, ManifestInbox
from utopia.optimization.native_nested_search import NativeNestedDesignCampaign, STAGES, COUNTS
from utopia.system.design_patch import clone
from utopia.utils.data_utils import write_json_atomic


def create(path, **kwargs):
    return NativeNestedDesignCampaign(path, initial_system=tiny_parent(), loss_spec=loss_spec(),
        world_binding=WORLD, seeds=[42], **kwargs)


def synthetic_costs(monkeypatch, costs):
    """Explicit unit-only costs: never exported as actual native results."""
    values = iter(costs)
    def evaluate(suggestion, **kwargs):
        cost = next(values)
        return Observation('observation-' + suggestion.suggestion_id, suggestion.suggestion_id,
            suggestion.candidate, 'complete' if cost is not None else 'failed', cost,
            {'unit_test_only': True, 'technical_failures': [] if cost is not None else [{'loss': None}]})
    monkeypatch.setattr('utopia.optimization.native_nested_search.evaluate_native_suggestion', evaluate)
    monkeypatch.setattr(NativeNestedDesignCampaign, '_check_observation', lambda *args: None)


def test_exact_two_draw_loo_update_then_fresh_same_distribution_then_free_reset(tmp_path, monkeypatch):
    synthetic_costs(monkeypatch, [1., 4., -2., 3.])
    seen = []
    def author(request):
        seen.append(clone(request))
        definition = tiny_definition()
        if request['generation']:
            assert len(request['observations']) == 3
            assert [r['stage'] for r in request['history']] == list(STAGES[:2])
            assert request['history'][0]['report']['gradient'] is not None
            definition['continuous'][0]['id'] = 'new-meaning-explicit-reset'
            definition['continuous'][0]['mean'] = 1.3
            definition['logits'] = {'code-choice': [-.7]}
        return definition
    first = create(tmp_path).advance(simulation_factory=fail_factory, generator=author)
    assert first['report']['status'] == 'score-updated'
    z = [d['latent'][0] for d in first['draws']]
    expected = ((1.-4.) * (z[0]-.2) + (4.-1.) * (z[1]-.2)) / (2*.7**2)
    assert first['report']['gradient']['continuous_mean'] == pytest.approx([expected])
    assert first['report']['weights_before'] != first['report']['weights_after']
    updated = create(tmp_path).advance(simulation_factory=fail_factory,
        generator=lambda r: pytest.fail('updated forward must not invoke external author'))
    assert updated['definition'] == first['definition']
    assert updated['version_sha256'] == first['version_sha256']
    assert updated['draw_version_sha256'] != first['draw_version_sha256']
    assert updated['report']['weights_before'] == first['report']['weights_after']
    assert updated['report']['weights_after'] == first['report']['weights_after']
    assert updated['report']['gradient'] is None
    singleton = create(tmp_path)._mixed(updated)
    assert singleton.log_probabilities(updated['draws']).item() == pytest.approx(
        updated['draws'][0]['conditional_latent_log_probability'])
    final = create(tmp_path).advance(simulation_factory=fail_factory, generator=author)
    assert len(seen) == 2 and final['request']['based_on_observation_id'] == updated['observations'][0]['observation_id']
    assert final['report']['weights_before'] == {'logits': {'code-choice': [-.7]}, 'continuous_mean': [1.3]}
    assert final['report']['compatibility_sha256'] != first['report']['compatibility_sha256']
    assert final['report']['gradient'] is None
    all_draws = [d for r in create(tmp_path).state['records'] for d in r['draws']]
    assert [d['suggestion']['proposal_index'] for d in all_draws] == [0, 1, 2, 3]
    assert len({d['suggestion']['suggestion_id'] for d in all_draws}) == 4
    with pytest.raises(ValueError, match='budget already exhausted'):
        create(tmp_path).advance(simulation_factory=fail_factory, generator=author)


@pytest.mark.parametrize('costs', [[2., 2., 2., 2.], [None, 2., 2., 2.]])
def test_equal_or_failed_initial_batch_unchanged_no_rerolls_and_all_ties_retained(tmp_path, monkeypatch, costs):
    synthetic_costs(monkeypatch, costs)
    for _ in STAGES:
        create(tmp_path).advance(simulation_factory=fail_factory, generator=lambda r: tiny_definition())
    records = create(tmp_path).state['records']
    first = records[0]
    assert first['report']['weights_before'] == first['report']['weights_after']
    assert sum(len(r['draws']) for r in records) == 4
    assert len(records[2]['request']['incumbent_ties']) == (3 if costs[0] is not None else 2)
    if costs[0] is None:
        assert first['report']['status'] == 'not-updated-technical-failure'
        assert first['report']['gradient'] is None and first['observations'][0]['loss'] is None
    else:
        assert first['report']['gradient']['continuous_mean'] == [0.]


def test_empty_vocabulary_still_has_four_unique_native_slot_ids(tmp_path, monkeypatch):
    synthetic_costs(monkeypatch, [1.] * 4)
    for _ in STAGES:
        create(tmp_path).advance(simulation_factory=fail_factory,
            generator=lambda r: {'base_patch': None, 'factors': [], 'continuous': [], 'provenance': PROVENANCE})
    records = create(tmp_path).state['records']
    assert records[0]['report']['gradient'] is None
    ids = [d['suggestion']['suggestion_id'] for r in records for d in r['draws']]
    assert len(set(ids)) == 4


def test_invalid_g0_consumes_three_slots_then_g1_can_recover_without_replacement(tmp_path):
    first = create(tmp_path).advance(simulation_factory=lambda *a: pytest.fail('invalid cannot execute'),
        generator=lambda r: {'invalid': 'preserved JSON'})
    assert first['request']['count'] == 2 and first['generation_error']['loss'] is None
    updated = create(tmp_path).advance(simulation_factory=lambda *a: pytest.fail('no replacement'),
        generator=lambda r: pytest.fail('no author for unavailable G0 updated slot'))
    assert updated['generation_error']['loss'] is None and updated['request']['count'] == 1
    seen = []
    def recover(request):
        seen.append(request)
        return tiny_definition()
    final = create(tmp_path).advance(simulation_factory=fail_factory, generator=recover)
    assert len(seen[0]['history']) == 2 and seen[0]['observations'] == []
    assert final['observations'][0]['loss'] is None
    assert sum(r['request']['count'] for r in create(tmp_path).state['records']) == 4


def test_failed_native_worlds_stay_null_and_cold_replay_without_mocked_validation(tmp_path):
    for _ in STAGES:
        create(tmp_path).advance(simulation_factory=fail_factory, generator=lambda r: tiny_definition())
    restored = create(tmp_path)
    observations = [o for r in restored.state['records'] for o in r['observations']]
    assert len(observations) == 4 and all(o['loss'] is None and o['status'] == 'failed' for o in observations)
    assert restored.state['records'][0]['report']['status'] == 'not-updated-technical-failure'


def test_saved_external_inbox_wait_has_exact_request_and_no_native_calls(tmp_path):
    campaign = create(tmp_path / 'campaign')
    generator = InboxVocabularyGenerator(ManifestInbox(tmp_path / 'authoring'), instructions='unit-only')
    with pytest.raises(ExternalAuthoringPending) as initial:
        campaign.advance(simulation_factory=lambda *a: pytest.fail('not authored'), generator=generator)
    saved = clone(campaign.state)
    with pytest.raises(ExternalAuthoringPending) as repeat:
        create(tmp_path / 'campaign').advance(simulation_factory=fail_factory, generator=generator)
    assert initial.value.to_dict() == repeat.value.to_dict()
    assert campaign.state == saved and not campaign.state['pending']['generated']
    write_json_atomic(initial.value.response_path, {'request_sha256': initial.value.request_sha256,
        'manifest': tiny_definition(), 'authoring': {'kind': 'external', 'unit_test_only': True}})
    first = create(tmp_path / 'campaign').advance(simulation_factory=fail_factory, generator=generator)
    assert first['generated'] and len(first['observations']) == 2
    assert len(list((tmp_path / 'authoring' / 'consumed').glob('*.json'))) == 1


def test_estimator_exception_is_preserved_and_fresh_forward_uses_unchanged_weights(tmp_path, monkeypatch):
    synthetic_costs(monkeypatch, [1., 2., 3.])
    def broken(*args, **kwargs):
        raise ValueError('synthetic unit-only estimator failure')
    monkeypatch.setattr(GeneratedMixedDesign, 'update', broken)
    first = create(tmp_path).advance(simulation_factory=fail_factory, generator=lambda r: tiny_definition())
    assert first['report']['status'] == 'not-updated-estimator-failure'
    assert first['report']['estimator_error']['loss'] is None
    second = create(tmp_path).advance(simulation_factory=fail_factory, generator=lambda r: pytest.fail('no author'))
    assert second['report']['weights_before'] == first['report']['weights_before']


@pytest.mark.parametrize('path,value', [
    (['records', 0, 'draws', 0, 'conditional_latent_log_probability'], 999.),
    (['records', 0, 'request', 'rng_seed'], 999),
    (['records', 0, 'report', 'weights_after', 'continuous_mean'], [999.]),
    (['records', 1, 'definition', 'continuous', 0, 'id'], 'changed'),
    (['records', 1, 'version_sha256'], 'changed'),
    (['records', 2, 'request', 'incumbent_ties'], []),
    (['records', 2, 'report', 'gradient'], {'continuous_mean': [999.]}),
])
def test_exact_stage_likelihood_weights_definition_update_and_own_history_tampering_rejected(
        tmp_path, monkeypatch, path, value):
    synthetic_costs(monkeypatch, [1., 2., 3., 4.])
    for _ in STAGES:
        create(tmp_path).advance(simulation_factory=fail_factory, generator=lambda r: tiny_definition())
    state = json.loads(create(tmp_path).path.read_text())
    owner = state
    for key in path[:-1]:
        owner = owner[key]
    owner[path[-1]] = value
    write_json_atomic(tmp_path / 'native-nested-state.json', state)
    with pytest.raises(ValueError):
        create(tmp_path)


def test_cold_stop_after_first_committed_draw_never_regenerates_or_repeats_it(tmp_path, monkeypatch):
    from utopia.runtime.checkpointing import PortableStop
    synthetic_costs(monkeypatch, [1., 2.])
    from utopia.optimization import native_nested_search as module
    actual = module.evaluate_native_suggestion
    ids, stopped = [], []
    def stop(suggestion, **kwargs):
        ids.append(suggestion.suggestion_id)
        if len(ids) == 2 and not stopped:
            stopped.append(True)
            raise PortableStop('unit-only cold stop before second actual slot')
        return actual(suggestion, **kwargs)
    monkeypatch.setattr(module, 'evaluate_native_suggestion', stop)
    with pytest.raises(PortableStop):
        create(tmp_path).advance(simulation_factory=fail_factory, generator=lambda r: tiny_definition())
    pending = create(tmp_path).state['pending']
    assert len(pending['observations']) == 1
    first = create(tmp_path).advance(simulation_factory=fail_factory,
        generator=lambda r: pytest.fail('saved definition must not be regenerated'))
    assert len(first['observations']) == 2 and ids[1] == ids[2] and ids[0] != ids[2]


def test_four_original_six_year_worlds_source_vocabulary_update_and_cold_replay(
        tmp_path, fixed_corpus, monkeypatch):
    from tests.optimization.test_native_adaptive_search import evolving_native_generator
    from tests.runtime.test_portable_checkpoint_integration import BINDING, seed
    from tests.system.test_native_science_kernel import make_sim
    from utopia.system.code_mechanisms import DockerCodeExecutor, CodeExecutionError
    from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
    try:
        executor = DockerCodeExecutor()
    except (OSError, CodeExecutionError):
        pytest.skip('existing isolated Docker runtime required')
    world = {'source_commit': 'v13-original-world-scripted-software-QA',
        'model_digest': BINDING['model_revision'], 'corpus_sha256': BINDING['corpus_sha256']}
    seen, runs, replies = [], [], []
    old_author = evolving_native_generator(executor.image_id, seen)
    def author(request):
        # Adapt only the test fixture's historical mixed-report field shape.
        copied = clone(request)
        for r in copied['history']:
            r['report'] = {'mixed': r['report']}
        return old_author(copied)
    def factory(spec, run_seed, run_id):
        runs.append(run_id)
        monkeypatch.setitem(BINDING, 'cell', spec.fingerprint)
        monkeypatch.setitem(BINDING, 'science_config', {**BINDING['science_config'], 'source_commit': world['source_commit']})
        seed()
        sim, calls = make_sim(tmp_path / 'worlds' / run_id, native=NativeScienceKernel(spec))
        replies.append(calls)
        return sim
    def reopen():
        return NativeNestedDesignCampaign(tmp_path / 'campaign', initial_system=legacy_world_system(),
            loss_spec=loss_spec(), world_binding=world, seeds=[42])
    for _ in STAGES:
        reopen().advance(simulation_factory=factory, generator=author)
    records = reopen().state['records']
    assert len(seen) == 2 and len(runs) == len(set(runs)) == 4
    assert len(replies) == 4 and all(replies)
    assert records[1]['version_sha256'] == records[0]['version_sha256']
    assert records[1]['report']['weights_before'] == records[0]['report']['weights_after']
    assert records[2]['version_sha256'] != records[0]['version_sha256']
    assert len(records[2]['definition']['factors'][0]['choices']) == 3
    for record in records:
        for observation in record['observations']:
            assert observation['status'] == 'complete'
            assert observation['metadata']['runs'][0]['checkpoint_path'].endswith('portable_checkpoint_year_6.json.gz')
            assert observation['metadata']['measurements'][0]['metrics']['native.review_records']['value'] > 0
    assert records[1]['report']['gradient'] is None and records[2]['report']['gradient'] is None
