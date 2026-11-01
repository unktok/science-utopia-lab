"""Mixed estimator units and original six-year native scripted-HTTP QA.

Numeric costs in unit tests below are NOT native/scientific evidence. Only the
explicit native integration test executes the original Simulation lifecycle.
"""
from copy import deepcopy
from dataclasses import replace
import json
import math

import numpy as np
import pytest
import torch

from tests.optimization.test_native_world import loss_spec
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_adaptive_search import (GeneratedMixedDesign, NativeAdaptiveDesignCampaign,
    PatchProposerGenerator, InboxVocabularyGenerator)
from utopia.optimization.native_manifest_inbox import ManifestInbox, ExternalAuthoringPending
from utopia.runtime.checkpointing import PortableStop
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest, make_patch
from utopia.system.native_kernel import legacy_world_system
from utopia.utils.data_utils import write_json_atomic

PROVENANCE = {'kind': 'scripted-software-QA-not-generated-research', 'source': 'test fixture v1'}
WORLD = {'source_commit': 'adaptive-search-six-year-scripted-QA',
         'model_digest': 'model-test', 'corpus_sha256': 'corpus-test'}
STRATEGIES = {'invent': {**PROVENANCE, 'generator': 'invent'},
              'revise': {**PROVENANCE, 'generator': 'revise'}}


def tiny_definition():
    return {'base_patch': None, 'factors': [{'id': 'code-choice', 'kind': 'bernoulli',
        'choices': [{'id': k, 'operations': [], 'provenance': PROVENANCE} for k in ('left', 'right')]}],
        'continuous': [{'id': 'coordinate', 'path': '/initial_state/coordinate',
            'lower': -2., 'upper': 3., 'mean': .2, 'sigma': .7}],
        'provenance': PROVENANCE, 'logits': {'code-choice': [.4]}}


def tiny_parent():
    p = legacy_world_system()
    return replace(p, initial_state={**p.initial_state, 'coordinate': .5})


def tiny_mixed():
    return GeneratedMixedDesign(tiny_parent(), tiny_definition(), loss_spec=loss_spec(), seed=42)


def test_exact_mixed_latent_likelihood_and_gradient_against_analytic_expectation():
    # Gauss-Hermite integration of a synthetic linear cost, NOT a native result.
    mixed = tiny_mixed()
    nodes, weights = np.polynomial.hermite.hermgauss(24)
    rows, costs, integration = [], [], []
    probabilities = torch.sigmoid(mixed.policy.logits['code-choice'][0]).detach().item()
    mu, sigma = .2, .7
    for action, p in [('left', 1-probabilities), ('right', probabilities)]:
        for node, weight in zip(nodes, weights):
            z = mu + sigma * math.sqrt(2) * node
            rows.append({'assignment': {'code-choice': action}, 'latent': [z]})
            costs.append(2*z + 3*(action == 'right'))
            integration.append(p * weight / math.sqrt(math.pi))
    q = mixed.log_probabilities(rows)
    expected = torch.distributions.Normal(torch.tensor(mu), torch.tensor(sigma)).log_prob(
        torch.tensor([r['latent'][0] for r in rows]))
    expected = expected + torch.tensor([math.log(probabilities if r['assignment']['code-choice'] == 'right'
        else 1-probabilities) for r in rows])
    assert torch.allclose(q, expected.double(), atol=3e-6)
    surrogate = (torch.tensor(integration) * torch.tensor(costs) * q).sum()
    discrete, continuous = torch.autograd.grad(surrogate, (mixed.policy.logits['code-choice'], mixed.mean))
    assert discrete.item() == pytest.approx(3*probabilities*(1-probabilities), abs=1e-12)
    assert continuous.item() == pytest.approx(2., abs=1e-12)


def synthetic_observation(draw, cost):
    return {'loss': cost, 'status': 'complete', 'metadata': {'unit_test_only': True}}


def test_bounded_continuous_mixed_update_and_equal_costs_zero_gradient():
    mixed = tiny_mixed()
    draws = mixed.draw(4, version_sha256='unit-only')
    values = [read['continuous_operations'][0]['value'] for read in draws]
    assert all(-2 < v < 3 for v in values) and len(set(values)) == 4
    costs = [1., 2., 4., 8.]
    report = mixed.update(draws, [synthetic_observation(d, c) for d, c in zip(draws, costs)], score=True)
    latent = [d['latent'][0] for d in draws]
    expected = sum((c-(sum(costs)-c)/3)*(z-.2)/.7**2 for c, z in zip(costs, latent))/4
    assert report['gradient']['continuous_mean'][0] == pytest.approx(expected)
    assert report['weights_after'] != report['weights_before']
    other = tiny_mixed()
    rows = other.draw(4, version_sha256='equal-unit-only')
    equal = other.update(rows, [synthetic_observation(d, -5.) for d in rows], score=True)
    assert equal['all_equal_costs'] and equal['gradient']['continuous_mean'] == [0.]
    assert equal['weights_before'] == equal['weights_after']
    failed_mixed = tiny_mixed()
    rows = failed_mixed.draw(4, version_sha256='failed-unit-only')
    failed = failed_mixed.update(rows, [None, *[synthetic_observation(d, -5.) for d in rows[1:]]], score=True)
    assert failed['status'] == 'not-updated-technical-failure' and failed['losses'][0] is None
    assert failed['gradient'] is None


def test_mixed_direct_api_rejects_changed_weights_choices_and_duplicate_tell():
    mixed = tiny_mixed()
    draws = mixed.draw(2, version_sha256='stale-unit-only')
    with torch.no_grad(): mixed.mean.add_(1.)
    with pytest.raises(ValueError, match='stale'):
        mixed.update(draws, [synthetic_observation(d, 1.) for d in draws], score=True)
    mixed = tiny_mixed()
    draws = mixed.draw(2, version_sha256='stale-choice-unit-only')
    draws[0]['assignment']['code-choice'] = 'right' if draws[0]['assignment']['code-choice'] == 'left' else 'left'
    with pytest.raises(ValueError, match='stale'):
        mixed.update(draws, [synthetic_observation(d, 1.) for d in draws], score=True)
    mixed = tiny_mixed()
    draws = mixed.draw(2, version_sha256='duplicate-tell-unit-only')
    observations = [synthetic_observation(d, 1.) for d in draws]
    mixed.update(draws, observations, score=True)
    with pytest.raises(ValueError, match='stale'):
        mixed.update(draws, observations, score=True)


@pytest.mark.parametrize('mode', ['blackbox', 'score', 'hybrid'])
def test_strategy_selection_and_inner_updates_use_explicit_costs_without_shared_draw_multiplicity(tmp_path, mode):
    # Formula unit test only: costs here are not native observations/evidence.
    campaign = create(tmp_path, mode=mode)
    strategy = campaign._strategy_initial()
    request = campaign._request([], strategy, 2)
    definition = tiny_definition()
    record = {'request': request, 'request_sha256': digest(request), 'definition': definition,
        'version_sha256': digest({'request': digest(request), 'definition': definition}), 'generation_error': None}
    _, draws = campaign._compile(record)
    record.update(draws=draws, observations=[synthetic_observation(d, c) for d, c in zip(draws, [1., 4.])])
    report = campaign._finish(record, strategy)
    assert report['strategy_after'] != report['strategy_before']
    if mode == 'blackbox':
        assert report['mixed']['gradient'] is None and report['strategy_gradient'] is None
        assert report['mixed']['weights_before'] == report['mixed']['weights_after']
    else:
        selected = sorted(STRATEGIES).index(request['strategy_id'])
        expected = [2.5 * (-.45), 2.5 * (-.45)]
        expected[selected] = 2.5 * .45
        assert report['strategy_gradient'] == pytest.approx(expected)
        assert report['mixed']['weights_before'] != report['mixed']['weights_after']
    assert report['batch_joint_latent_log_probability'] == pytest.approx(
        request['strategy_log_probability'] + sum(d['conditional_latent_log_probability'] for d in draws))


def create(path, **kwargs):
    return NativeAdaptiveDesignCampaign(path, initial_system=tiny_parent(), loss_spec=loss_spec(),
        seeds=[42], world_binding=WORLD, strategies=STRATEGIES, **kwargs)


def fail_factory(*args):
    raise RuntimeError('intentional software-QA infrastructure failure; never a cost')


@pytest.mark.parametrize('mode', ['blackbox', 'score', 'hybrid'])
def test_failed_native_costs_remain_null_and_never_change_strategy_or_score_weights(tmp_path, mode):
    campaign = create(tmp_path, mode=mode)
    record = campaign.advance(simulation_factory=fail_factory,
        generators={s: lambda request: tiny_definition() for s in STRATEGIES}, count=2)
    assert record['report']['status'] == 'not-updated-technical-failure'
    assert record['report']['strategy_before'] == record['report']['strategy_after']
    assert record['report']['mixed']['losses'] == [None, None]
    assert all(o['status'] == 'failed' and o['loss'] is None for o in record['observations'])
    assert create(tmp_path, mode=mode).state == campaign.state


def test_invalid_vocabulary_is_preserved_without_filter_repair_or_numeric_penalty(tmp_path):
    campaign = create(tmp_path)
    definition = tiny_definition()
    definition['factors'][0]['choices'][1]['operations'] = [{'op': 'remove', 'path': '/mechanisms/0'}]
    record = campaign.advance(simulation_factory=lambda *a: pytest.fail('no world for invalid grammar'),
        generators={s: lambda request: definition for s in STRATEGIES})
    assert record['generation_error']['loss'] is None
    assert record['report']['status'] == 'invalid-generated-vocabulary'
    assert not record['draws'] and not record['observations']
    assert create(tmp_path).state == campaign.state
    # A new explicit round sees the failure and may invent a different grammar.
    def revised(request):
        assert request['history'][0]['generation_error']['loss'] is None
        return tiny_definition()
    next_record = campaign.advance(simulation_factory=fail_factory, generators={s: revised for s in STRATEGIES})
    assert next_record['request']['generation'] == 1 and next_record['draws']


def test_invalid_continuous_sample_has_null_cost_and_no_posthoc_probability_remap(tmp_path):
    campaign = create(tmp_path)
    definition = tiny_definition()
    definition['continuous'][0]['path'] = '/schedules/0/phase'  # Requires int; logistic values are floats.
    record = campaign.advance(simulation_factory=lambda *a: pytest.fail('invalid design is not executed'),
        generators={s: lambda request: definition for s in STRATEGIES})
    assert all(d['technical_error']['loss'] is None and d['suggestion'] is None for d in record['draws'])
    assert record['observations'] == [None, None]
    assert record['report']['status'] == 'not-updated-technical-failure'
    assert create(tmp_path).state == campaign.state


def test_generation_is_committed_before_compile_and_reopens_without_new_generator_call(tmp_path, monkeypatch):
    campaign = create(tmp_path)
    original = campaign._compile
    def stop(record):
        raise PortableStop('saved raw vocabulary; not yet compiled')
    monkeypatch.setattr(campaign, '_compile', stop)
    with pytest.raises(PortableStop):
        campaign.advance(simulation_factory=fail_factory, generators={s: lambda r: tiny_definition() for s in STRATEGIES})
    resumed = create(tmp_path)
    assert resumed.state['pending']['generated'] and not resumed.state['pending']['compiled']
    record = resumed.advance(simulation_factory=fail_factory,
        generators={s: lambda r: pytest.fail('must reuse saved vocabulary') for s in STRATEGIES})
    assert record['compiled'] and record['report']['mixed']['losses'] == [None, None]


def test_external_inbox_keeps_exact_strategy_request_and_arbitrary_patch_adapter(tmp_path):
    inbox = ManifestInbox(tmp_path / 'inbox')
    generator = InboxVocabularyGenerator(inbox, instructions='ABI-only caller instructions; no algorithm supplied.')
    campaign = create(tmp_path / 'campaign')
    with pytest.raises(ExternalAuthoringPending) as pending:
        campaign.advance(simulation_factory=fail_factory, generators={s: generator for s in STRATEGIES})
    frozen = clone(campaign.state['pending']['request'])
    assert not campaign.state['pending']['generated']
    request = json.loads(pending.value.request_path.read_text())
    assert request['request']['authoring_input'] == frozen
    write_json_atomic(pending.value.response_path, {'request_sha256': pending.value.request_sha256,
        'manifest': tiny_definition(), 'authoring': {'kind': 'external', 'identity': 'scripted-inbox-software-QA'}})
    resumed = create(tmp_path / 'campaign')
    record = resumed.advance(simulation_factory=fail_factory, generators={s: generator for s in STRATEGIES})
    assert record['request'] == frozen
    assert len(list((tmp_path / 'inbox' / 'consumed').glob('*.json'))) == 1
    def proposer(parent, observations, index, loss):
        assert index == 1 and observations == [] and loss == loss_spec()
        return make_patch(parent, [{'op': 'add', 'path': '/metadata/externally-authored', 'value': True}])
    wrapped = PatchProposerGenerator(proposer, provenance=PROVENANCE)
    assert wrapped(frozen)['base_patch']['operations'][0]['path'] == '/metadata/externally-authored'


def test_immutable_source_grammar_weights_choices_likelihood_and_bindings_reject_tamper(tmp_path):
    campaign = create(tmp_path)
    campaign.advance(simulation_factory=fail_factory, generators={s: lambda r: tiny_definition() for s in STRATEGIES})
    original = clone(campaign.state)
    def change(path, value):
        state = clone(original)
        target = state
        for key in path[:-1]: target = target[key]
        target[path[-1]] = value
        write_json_atomic(campaign.path, state)
        with pytest.raises(ValueError): create(tmp_path)
    change(['records', 0, 'definition', 'provenance', 'source'], 'rewritten')
    change(['records', 0, 'definition', 'logits', 'code-choice'], [9.])
    change(['records', 0, 'draws', 0, 'assignment', 'code-choice'], 'missing')
    change(['records', 0, 'draws', 0, 'conditional_latent_log_probability'], 999.)
    change(['records', 0, 'report', 'strategy_after', 'logits'], [99., -99.])
    write_json_atomic(campaign.path, original)
    with pytest.raises(ValueError, match='binding'):
        create(tmp_path, strategy_learning_rate=.3)


def evolving_native_generator(image, seen):
    """Caller-authored changing source/choices; never claimed LLM invention."""
    from tests.optimization.test_native_factorized_gradient import design_definition, choice, edit, OVERRIDE
    def generate(request):
        generation = request['generation']
        seen.append(clone(request))
        base, factors = design_definition(image)
        # The generator authors an entire new producer/consumer graph, not a host code catalogue.
        parent = SystemSpec.from_dict(request['parent_system'])
        base_patch = make_patch(parent, [{'op': 'replace', 'path': '/' + key, 'value': base.to_dict()[key]}
            for key in ('mechanisms', 'connections', 'schedules', 'artifact_types')], rationale='caller-generated native institution')
        factors = [f for f in factors if f['id'] != 'parameter']
        ci = next(i for i, n in enumerate(base.mechanisms) if n.mechanism_id == 'world.selection')
        if generation:
            actual = [o['observation']['loss'] for o in request['observations'] if o['observation']['status'] == 'complete']
            assert actual  # Generation follows actual native losses, not a fabricated reward signal.
            new_source = OVERRIDE.replace("accept = bool(context['inputs']['override']) or paper['score'] >= context['parameters']['threshold']",
                "accept = True  # new caller-authored option after observed native loss " + str(min(actual)))
            factors[0]['choices'].append(choice('new-open-publication-' + str(generation), [
                edit(f'/mechanisms/{ci}/parameters/code_artifact/source', new_source)]))
            factors[1]['support'].append({'when': {'code': 'new-open-publication-' + str(generation)}, 'allow': ['off', 'on']})
        continuous_mean = 0.
        logits = None
        if generation and request['history'][-1]['report']['mixed']:
            weights = request['history'][-1]['report']['mixed']['weights_after']
            continuous_mean = weights['continuous_mean'][0]
            # Explicit caller-authored dimensional transport, not host auto-remapping.
            logits = clone(weights['logits'])
            logits['code'] = [*logits['code'], 0.]
        result = {'base_patch': base_patch, 'factors': factors,
            'continuous': [{'id': 'publication-threshold', 'path': f'/mechanisms/{ci}/parameters/threshold',
                'lower': 1., 'upper': 7., 'mean': continuous_mean, 'sigma': 1.2}],
            'provenance': {**PROVENANCE, 'generation': generation, 'actual_history_sha256': request['history_sha256']}}
        if logits is not None: result['logits'] = logits
        return result
    return generate


def test_six_year_native_generation_evolving_source_structures_continuous_loss_feedback_and_restart(
        tmp_path, fixed_corpus, monkeypatch):
    from tests.runtime.test_portable_checkpoint_integration import BINDING, seed
    from tests.system.test_native_science_kernel import make_sim
    from utopia.system import SystemSpec
    from utopia.system.code_mechanisms import DockerCodeExecutor, CodeExecutionError
    from utopia.system.native_kernel import NativeScienceKernel
    try:
        executor = DockerCodeExecutor()
    except (OSError, CodeExecutionError):
        pytest.skip('isolated local runtime required for actual native scripted-HTTP QA')
    world = {'source_commit': 'adaptive-native-scripted-QA', 'model_digest': BINDING['model_revision'],
        'corpus_sha256': BINDING['corpus_sha256']}
    seen, runs, replies = [], [], []
    def factory(spec, run_seed, run_id):
        runs.append(run_id)
        if len(runs) == 2:
            raise PortableStop('cold stop after first committed actual native draw')
        monkeypatch.setitem(BINDING, 'cell', spec.fingerprint)
        monkeypatch.setitem(BINDING, 'science_config', {**BINDING['science_config'], 'source_commit': world['source_commit']})
        seed()
        sim, calls = make_sim(tmp_path / 'runs' / run_id, native=NativeScienceKernel(spec))
        replies.append(calls)
        return sim
    def reopen():
        return NativeAdaptiveDesignCampaign(tmp_path / 'campaign', initial_system=legacy_world_system(),
            loss_spec=loss_spec(), seeds=[42], world_binding=world, strategies=STRATEGIES, mode='hybrid', seed=42)
    generator = evolving_native_generator(executor.image_id, seen)
    campaign = reopen()
    with pytest.raises(PortableStop):
        campaign.advance(simulation_factory=factory, generators={s: generator for s in STRATEGIES}, count=4)
    assert len(campaign.state['pending']['observations']) == 1
    first = reopen().advance(simulation_factory=factory,
        generators={s: lambda r: pytest.fail('must not regenerate saved source') for s in STRATEGIES}, count=4)
    assert len(seen) == 1 and runs[1] == runs[2] and runs[0] != runs[2]
    assert all(o['status'] == 'complete' for o in first['observations'])
    assert first['report']['status'] == 'score-updated'
    assert first['report']['strategy_before'] != first['report']['strategy_after']
    second = reopen().advance(simulation_factory=factory, generators={s: generator for s in STRATEGIES}, count=2)
    assert len(seen) == 2 and len(second['definition']['factors'][0]['choices']) == 3
    assert second['version_sha256'] != first['version_sha256']
    assert all(o['status'] == 'complete' for o in second['observations'])
    assert any(d['assignment']['code'] == 'new-open-publication-1' for d in second['draws'])
    assert {d['assignment']['edge'] for d in first['draws']} == {'off', 'on'}
    assert {d['assignment']['protocol'] for d in first['draws']} == {'proposals', 'dossier'}
    assert seen[1]['strategy_state'] == first['report']['strategy_after']
    assert seen[1]['history'][0]['definition'] == first['definition']
    assert second['definition']['continuous'][0]['mean'] == first['report']['mixed']['weights_after']['continuous_mean'][0]
    assert [d['suggestion']['proposal_index'] for d in second['draws']] == [4, 5]
    assert first['report']['batch_joint_latent_log_probability'] == pytest.approx(
        first['request']['strategy_log_probability'] + sum(d['conditional_latent_log_probability'] for d in first['draws']))
    assert all(calls for calls in replies) and len(replies) == 6
    for record in (first, second):
        for observation in record['observations']:
            from utopia.runtime.checkpointing import read_portable_checkpoint
            assert observation['metadata']['world_backend'] == 'native-research-world'
            assert observation['metadata']['runs'][0]['checkpoint_path'].endswith('portable_checkpoint_year_6.json.gz')
            assert observation['metadata']['measurements'][0]['metrics']['native.review_records']['value'] > 0
            checkpoint = read_portable_checkpoint(observation['metadata']['runs'][0]['checkpoint_path'])
            stages = [e['payload']['stage'] for e in checkpoint['native_system']['events']
                      if e['event_type'] == 'native.system.phase_executed']
            assert all(stages.count(stage) == 6 for stage in ('open', 'resubmissions', 'research', 'collaboration',
                'submission', 'costs', 'review', 'publication', 'citation-potential', 'funding', 'communication', 'close'))
    assert reopen().state['records'] == [first, second]
    tampered = reopen()
    tampered.state['records'][0]['report']['mixed']['weights_after']['continuous_mean'][0] += 1
    with pytest.raises(ValueError, match='update history'):
        tampered._validate()
