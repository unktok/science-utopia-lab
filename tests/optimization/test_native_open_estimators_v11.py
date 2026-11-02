"""V11 estimator integration; scripted native worlds are software QA only."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import fcntl

import pytest

from scripts.run_native_open_estimators_v11 import (
    ARM_IDS, ESTIMATOR_CONFIG, ROOT, advance_arms, load_preregistered_loss, main, summarize)
from tests.optimization.test_native_adaptive_search import (
    PROVENANCE, STRATEGIES, WORLD, create, evolving_native_generator, fail_factory,
    tiny_definition, tiny_mixed, tiny_parent)
from tests.optimization.test_native_world import loss_spec
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_adaptive_search import (
    GeneratedMixedDesign, NativeAdaptiveDesignCampaign, expectation_compatibility)
from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending
from utopia.system.design_patch import clone, digest


def test_compatibility_allows_distribution_changes_but_not_source_coordinate_or_support_transport():
    mixed = tiny_mixed()
    signature = expectation_compatibility(mixed)
    definition = tiny_definition()
    definition['logits']['code-choice'] = [2.]
    definition['continuous'][0]['mean'] = 3.
    parent = replace(tiny_parent(), initial_state={**tiny_parent().initial_state, 'coordinate': 2.})
    other = GeneratedMixedDesign(parent, definition, loss_spec=loss_spec(), seed=91)
    assert expectation_compatibility(other) == signature
    for mutate in (
        lambda d: d['continuous'][0].update(sigma=2.),
        lambda d: d['continuous'][0].update(id='different-meaning'),
        lambda d: d['factors'][0]['choices'][0]['provenance'].update(source='different-choice'),
    ):
        changed = deepcopy(definition)
        mutate(changed)
        assert expectation_compatibility(GeneratedMixedDesign(parent, changed,
            loss_spec=loss_spec(), seed=91)) != signature


def test_v7_default_binding_and_failed_cost_semantics_remain_unchanged(tmp_path):
    old = create(tmp_path / 'old')
    assert 'expectation_estimator' not in old.binding
    with pytest.raises(ValueError, match='score mode'):
        create(tmp_path / 'bad', mode='blackbox', expectation_estimator=ESTIMATOR_CONFIG)
    campaign = create(tmp_path / 'score', mode='score', expectation_estimator=ESTIMATOR_CONFIG)
    record = campaign.advance(simulation_factory=fail_factory,
        generators={s: lambda r: tiny_definition() for s in STRATEGIES}, count=2)
    assert record['report']['mixed']['gradient'] is None
    assert record['report']['mixed']['losses'] == [None, None]
    assert record['report']['strategy_before'] == record['report']['strategy_after']
    assert create(tmp_path / 'score', mode='score', expectation_estimator=ESTIMATOR_CONFIG).state == campaign.state


@pytest.mark.parametrize('change_semantics', [False, True])
def test_prior_fit_is_chronological_and_semantic_changes_reset_to_plain_lr(tmp_path, change_semantics):
    # Estimator/journal formula unit, deliberately not native scientific evidence.
    campaign = create(tmp_path, mode='score', expectation_estimator=ESTIMATOR_CONFIG)
    def record_for(records, state, definition, losses):
        request = campaign._request(records, state, 2)
        record = {'request': request, 'request_sha256': digest(request), 'definition': definition,
            'version_sha256': digest({'request': digest(request), 'definition': definition}),
            'generation_error': None}
        _, draws = campaign._compile(record)
        record.update(draws=draws, observations=[{'loss': cost, 'status': 'complete',
            'observation_id': f'unit-{len(records)}-{i}', 'metadata': {'formula_unit_not_native': True}}
            for i, cost in enumerate(losses)])
        record['report'] = campaign._finish(record, state)
        return record
    initial = campaign._strategy_initial()
    first = record_for([], initial, deepcopy(tiny_definition()), [1., 4.])
    definition = deepcopy(tiny_definition())
    weights = first['report']['mixed']['weights_after']
    definition['logits'] = clone(weights['logits'])
    definition['continuous'][0]['mean'] = weights['continuous_mean'][0]
    if change_semantics:
        definition['factors'][0]['choices'][0]['provenance']['source'] = 'new semantic choice'
    saved = clone(first)
    second = record_for([first], first['report']['strategy_after'], definition, [2., 3.])
    estimate = second['report']['mixed']['expectation_estimator']
    assert first == saved  # fitting cannot revise earlier evidence or weights
    if change_semantics:
        assert estimate['estimator'] == 'plain-likelihood-ratio'
        assert estimate['prior_fit']['sample_ids'] == []
        assert estimate['prior_fit']['incompatible_prior_batches'] == [first['request_sha256']]
    else:
        assert estimate['estimator'] == 'frozen-prior-control-variate-lr'
        assert estimate['prior_fit']['sample_ids'] == ['unit-0-0', 'unit-0-1']
        assert estimate['sample_ids'] == ['unit-1-0', 'unit-1-1']
        assert estimate['prior_fit']['incompatible_prior_batches'] == []
    assert estimate['plain_gradient'] is not None and estimate['loo_gradient'] is not None


def test_v11_runner_exact_loss_and_no_false_live_claim(tmp_path):
    path = ROOT / 'research/objectives/losses/native-joint-v5-net-reviewed-utility.json'
    assert load_preregistered_loss(path)['id'] == path.stem
    with pytest.raises(ValueError, match='exact preregistered'):
        load_preregistered_loss(ROOT / 'research/objectives/losses/native-joint-v5-throughput.json')
    campaigns = {key: SimpleNamespace(binding={}, state={'records': [], 'pending': None}) for key in ARM_IDS}
    value = summarize(tmp_path, {'world': {'classification': 'scripted-fixture-not-native-results',
        'source_commit': 'fixture'}}, campaigns)
    assert value['status'] == 'in-progress' and value['complete_native_worlds'] == 0
    assert not value['claims']['live_fixed_Qwen_researchers']
    assert not value['claims']['variance_reduction_established']


def test_v11_single_writer_rejected_before_factory_access(tmp_path, monkeypatch):
    monkeypatch.setattr('sys.argv', ['runner', '--output', str(tmp_path), '--data-cache', 'absent',
        '--inference-lock', str(tmp_path / 'http.lock'), '--loss', 'absent'])
    monkeypatch.setattr('scripts.run_native_open_estimators_v11.subprocess.check_output', lambda *a, **kw: b'')
    monkeypatch.setattr('scripts.run_native_open_estimators_v11.run',
        lambda *a: pytest.fail('factory must not start before writer ownership'))
    with (tmp_path / 'pilot-writer.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match='another native open-estimator writer'):
            main()


def test_pending_external_manifest_does_not_block_other_method(tmp_path):
    class Campaign:
        def __init__(self, waiting):
            self.state = {'records': []}
            self.waiting, self.calls = waiting, 0
        def advance(self, **kwargs):
            self.calls += 1
            if self.waiting:
                raise ExternalAuthoringPending('exact', tmp_path / 'request', tmp_path / 'response')
            self.state['records'].append({})
    campaigns = {ARM_IDS[0]: Campaign(True), ARM_IDS[1]: Campaign(False)}
    waiting = advance_arms(campaigns, {k: object() for k in ARM_IDS},
        simulation_factory=object(), snapshot=lambda: None)
    assert list(waiting) == [ARM_IDS[0]]
    assert campaigns[ARM_IDS[0]].calls == 1 and campaigns[ARM_IDS[1]].calls == 2


def test_technical_failure_stops_before_other_arm_and_stays_stopped_on_reopen(tmp_path):
    class Campaign:
        def __init__(self):
            self.state = {'records': []}
            self.calls = 0
        def advance(self, **kwargs):
            self.calls += 1
            record = {'generation_error': {'loss': None}, 'draws': [], 'observations': []}
            self.state['records'].append(record)
            return record
    campaigns = {key: Campaign() for key in ARM_IDS}
    for _ in range(2):
        assert advance_arms(campaigns, {k: object() for k in ARM_IDS},
            simulation_factory=object(), snapshot=lambda: None) == {}
    assert campaigns[ARM_IDS[0]].calls == 1 and campaigns[ARM_IDS[1]].calls == 0
    for campaign in campaigns.values():
        campaign.binding = {}
        campaign.state['pending'] = None
    report = summarize(tmp_path, {'world': {'classification': 'scripted-fixture-not-native-results',
        'source_commit': 'fixture'}}, campaigns)
    assert report['status'] == 'technically-stopped'
    assert report['stopped_on_technical_failure'] and not report['budget_terminal']


def test_invalid_estimator_receipt_is_retained_without_inner_or_outer_update(tmp_path, monkeypatch):
    campaign = create(tmp_path, mode='score', expectation_estimator=ESTIMATOR_CONFIG)
    state = campaign._strategy_initial()
    request = campaign._request([], state, 2)
    definition = tiny_definition()
    record = {'request': request, 'request_sha256': digest(request), 'definition': definition,
        'version_sha256': digest({'request': digest(request), 'definition': definition}), 'generation_error': None}
    _, draws = campaign._compile(record)
    record.update(draws=draws, observations=[{'loss': 1., 'status': 'complete',
        'observation_id': 'unit-' + str(i), 'metadata': {}} for i in range(2)])
    monkeypatch.setattr('utopia.optimization.native_expectation_estimators.estimate_expected_loss_gradient',
        lambda *a, **kw: {'status': 'invalid', 'gradient': None, 'reason': 'explicit numerical QA failure'})
    report = campaign._finish(record, state)
    assert report['status'] == 'not-updated-estimator-failure'
    assert report['mixed']['expectation_estimator']['reason'] == 'explicit numerical QA failure'
    assert report['mixed']['gradient'] is None
    assert report['mixed']['weights_before'] == report['mixed']['weights_after']
    assert report['strategy_before'] == report['strategy_after']


def test_original_native_six_year_world_prior_only_estimator_feedback_and_cold_restart(
        tmp_path, fixed_corpus, monkeypatch):
    """Actual Simulation phases, code containers and loss extraction; no Qwen claim."""
    from tests.runtime.test_portable_checkpoint_integration import BINDING, seed
    from tests.system.test_native_science_kernel import make_sim
    from utopia.runtime.checkpointing import PortableStop, read_portable_checkpoint
    from utopia.system.code_mechanisms import CodeExecutionError, DockerCodeExecutor
    from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
    try:
        executor = DockerCodeExecutor()
    except (OSError, CodeExecutionError):
        pytest.skip('isolated runtime required for original-world scripted QA')
    world = {**WORLD, 'model_digest': BINDING['model_revision'], 'corpus_sha256': BINDING['corpus_sha256']}
    seen, runs, calls = [], [], []
    stable = evolving_native_generator(executor.image_id, seen)
    def generator(request):
        authored = stable({**clone(request), 'generation': 0})
        if request['history']:
            weights = request['history'][-1]['report']['mixed']['weights_after']
            authored['logits'] = clone(weights['logits'])
            authored['continuous'][0]['mean'] = weights['continuous_mean'][0]
        return authored
    def factory(spec, run_seed, run_id):
        runs.append(run_id)
        if len(runs) == 2:
            raise PortableStop('cold stop with one native draw committed')
        monkeypatch.setitem(BINDING, 'cell', spec.fingerprint)
        monkeypatch.setitem(BINDING, 'science_config', {**BINDING['science_config'], 'source_commit': world['source_commit']})
        seed()
        sim, replies = make_sim(tmp_path / 'runs' / run_id, native=NativeScienceKernel(spec))
        calls.append(replies)
        return sim
    def reopen():
        return NativeAdaptiveDesignCampaign(tmp_path / 'campaign', initial_system=legacy_world_system(),
            loss_spec=loss_spec(), seeds=[42], world_binding=world, strategies=STRATEGIES,
            mode='score', seed=42, expectation_estimator=ESTIMATOR_CONFIG)
    campaign = reopen()
    with pytest.raises(PortableStop):
        campaign.advance(simulation_factory=factory, generators={s: generator for s in STRATEGIES}, count=2)
    assert len(campaign.state['pending']['observations']) == 1
    first = reopen().advance(simulation_factory=factory,
        generators={s: lambda r: pytest.fail('saved definition must not regenerate') for s in STRATEGIES}, count=2)
    second = reopen().advance(simulation_factory=factory,
        generators={s: generator for s in STRATEGIES}, count=2)
    first_estimate = first['report']['mixed']['expectation_estimator']
    second_estimate = second['report']['mixed']['expectation_estimator']
    assert first_estimate['estimator'] == 'plain-likelihood-ratio'
    assert first_estimate['prior_fit']['sample_ids'] == []
    assert second_estimate['estimator'] == 'frozen-prior-control-variate-lr'
    assert second_estimate['prior_fit']['sample_ids'] == [o['observation_id'] for o in first['observations']]
    assert set(second_estimate['sample_ids']).isdisjoint(second_estimate['prior_sample_ids'])
    assert second_estimate['batch_id'] not in second_estimate['prior_batch_ids']
    assert first_estimate['compatibility_sha256'] == second_estimate['compatibility_sha256']
    assert len(calls) == 4 and all(calls)
    for record in (first, second):
        for observation in record['observations']:
            checkpoint = read_portable_checkpoint(observation['metadata']['runs'][0]['checkpoint_path'])
            stages = [e['payload']['stage'] for e in checkpoint['native_system']['events']
                if e['event_type'] == 'native.system.phase_executed']
            assert stages.count('research') == stages.count('publication') == 6
            assert observation['metadata']['measurements'][0]['metrics']['native.review_records']['value'] > 0
    assert reopen().state['records'] == [first, second]
    tampered = reopen()
    tampered.state['records'][1]['report']['mixed']['expectation_estimator']['prior_fit']['sample_ids'].reverse()
    with pytest.raises(ValueError, match='update history'):
        tampered._validate()
