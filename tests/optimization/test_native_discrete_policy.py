from dataclasses import replace

import pytest
import torch

from tests.optimization.test_native_world import loss_spec
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.blackbox import Observation
from utopia.optimization.native_discrete_policy import NativeDiscretePolicySearch
from utopia.system.native_kernel import legacy_world_system


def designs(count=3):
    base = legacy_world_system()
    return [replace(base, mechanisms=(replace(base.mechanisms[0],
        parameters={'qa-design-choice': index}), *base.mechanisms[1:])) for index in range(count)]


def observation(search, suggestion, cost=1., status='complete'):
    return Observation('obs-' + suggestion.suggestion_id, suggestion.suggestion_id,
        suggestion.candidate, status, cost if status == 'complete' else None,
        {'world_backend': 'native-research-world', 'loss_spec_sha256': search.loss_hash})


@pytest.mark.parametrize('distribution,count,logits', [
    ('categorical', 3, [0.2, -0.5, 0.7]), ('bernoulli', 2, [0.7])])
def test_exact_enumerated_policy_scores_match_expected_cost_derivative(distribution, count, logits):
    search = NativeDiscretePolicySearch(designs(count), loss_spec=loss_spec(), distribution=distribution, logits=logits)
    costs = torch.tensor([2., -3., 5.][:count], dtype=torch.float64)
    actions = torch.arange(count)
    log_probs = search.action_log_probability(actions)
    probabilities = log_probs.exp()
    exact_gradient, = torch.autograd.grad((probabilities * costs).sum(), search.logits, retain_graph=True)
    score_gradient, = torch.autograd.grad((probabilities.detach() * (costs - 9.) * log_probs).sum(), search.logits)
    assert torch.allclose(score_gradient, exact_gradient, atol=1e-14)
    if distribution == 'categorical':
        expected = probabilities.detach() * (costs - (probabilities.detach() * costs).sum())
    else:
        p = probabilities.detach()[1]
        expected = (p * (1-p) * (costs[1] - costs[0])).reshape(1)
    assert torch.allclose(exact_gradient, expected, atol=1e-14)


@pytest.mark.parametrize('distribution,count', [('categorical', 3), ('bernoulli', 2)])
def test_sampled_exact_logprob_autograd_and_rng_pending_checkpoint(distribution, count):
    search = NativeDiscretePolicySearch(designs(count), loss_spec=loss_spec(), distribution=distribution)
    suggestions = search.ask(9)
    state = search.state_dict()
    resumed = NativeDiscretePolicySearch.from_state(state, loss_spec=loss_spec())
    assert resumed.state_dict() == state
    costs = torch.tensor([float(r['action'] - 1) for r in search.pending], dtype=torch.float64)
    log_probs = search.action_log_probability([r['action'] for r in search.pending])
    expected, = torch.autograd.grad((costs * log_probs).mean(), search.logits)
    report = resumed.tell([observation(search, s, float(c)) for s, c in zip(suggestions, costs)])
    assert report['gradient'] == pytest.approx(expected.tolist())
    assert report['end_to_end_native_autograd'] is False
    assert report['logits_after'] == pytest.approx((-search.learning_rate * expected).tolist())


def test_failure_cannot_be_dropped_or_receive_numeric_penalty():
    search = NativeDiscretePolicySearch(designs(), loss_spec=loss_spec())
    a, b = search.ask(2)
    report = search.tell([observation(search, a, -100.), observation(search, b, status='failed')])
    assert report['gradient'] is None
    assert report['logits_before'] == report['logits_after']
    assert report['status'] == 'not-updated-technical-failure'


def test_state_rejects_changed_action_rng_and_logprobability():
    search = NativeDiscretePolicySearch(designs(), loss_spec=loss_spec())
    search.ask(4)
    for key, value in [('action', 99), ('rng_seed', 99), ('log_probability', 99.)]:
        state = search.state_dict()
        state['pending'][0][key] = value
        with pytest.raises(ValueError, match='changed'):
            NativeDiscretePolicySearch.from_state(state, loss_spec=loss_spec())


def test_observation_binding_and_duplicate_receipts_rejected():
    search = NativeDiscretePolicySearch(designs(), loss_spec=loss_spec())
    a, b = search.ask(2)
    changed = observation(search, a)
    changed.metadata['loss_spec_sha256'] = 'changed'
    with pytest.raises(ValueError, match='binding'):
        search.tell([changed, observation(search, b)])
    with pytest.raises(ValueError, match='duplicate'):
        search.tell([observation(search, a), observation(search, a)])


def test_native_checkpoint_world_and_seed_are_bound(tmp_path, monkeypatch):
    from utopia.optimization.native_discrete_policy import verify_native_observation
    from utopia.utils.data_utils import file_sha256
    search = NativeDiscretePolicySearch(designs(), loss_spec=loss_spec())
    suggestion, = search.ask(1)
    obs = observation(search, suggestion)
    checkpoint = tmp_path / 'checkpoint.json'
    checkpoint.write_text('fixture')
    world = {'source_commit': 'pinned', 'model_digest': 'fixed', 'corpus_sha256': 'corpus'}
    binding = {'cell': search.designs[search.pending[0]['action']].fingerprint,
        'seed': 42, 'model_revision': 'fixed', 'corpus_sha256': 'corpus', 'science_config': {'source_commit': 'pinned'}}
    monkeypatch.setattr('utopia.runtime.checkpointing.read_portable_checkpoint',
        lambda path: {'portable': {'contract': {'binding': binding}}})
    obs.metadata['runs'] = [{'seed': 42, 'checkpoint_path': str(checkpoint), 'checkpoint_sha256': file_sha256(checkpoint)}]
    verify_native_observation(obs, world, [42])
    binding['seed'] = 43
    with pytest.raises(ValueError, match='RNG binding'):
        verify_native_observation(obs, world, [42])


def test_existing_campaign_restores_discrete_pending_definition(tmp_path):
    from utopia.optimization.native_gradient import NativeGradientCampaign
    search = NativeDiscretePolicySearch(designs(), loss_spec=loss_spec())
    campaign = NativeGradientCampaign(tmp_path, search, loss_spec=loss_spec(), seeds=[42],
        world_binding={'source_commit': 'qa-not-live'})
    replay = campaign._validate()
    replay.ask(3)
    campaign.state['search'] = replay.state_dict()
    campaign._save()
    assert campaign._validate().state_dict() == replay.state_dict()


def test_full_native_lifecycle_costs_update_discrete_policy_and_resume(tmp_path, monkeypatch, fixed_corpus):
    # Actual Simulation phases, agent histories and losses; scripted corpus and
    # model transport only. This is engineering QA, not a live-Qwen result.
    from tests.runtime.test_portable_checkpoint_integration import BINDING, seed
    from tests.system.test_native_science_kernel import make_sim
    from utopia.optimization.native_gradient import NativeGradientCampaign
    from utopia.runtime.checkpointing import PortableStop
    from utopia.system.code_mechanisms import DockerCodeExecutor, CodeExecutionError
    from utopia.system.design_patch import apply_design_patch
    from utopia.system.native_design_examples import deliberation_patch
    from utopia.system.native_kernel import NativeScienceKernel
    try:
        executor = DockerCodeExecutor()
    except (OSError, CodeExecutionError):
        pytest.skip('local isolated Python runtime required')
    base = legacy_world_system()
    system = apply_design_patch(base, deliberation_patch(base, image_id=executor.image_id))
    index = next(i for i, n in enumerate(system.mechanisms) if n.mechanism_id == 'world.selection')
    options = []
    for threshold in (1., 7.):
        nodes = list(system.mechanisms)
        nodes[index] = replace(nodes[index], parameters={**nodes[index].parameters, 'threshold': threshold})
        options.append(replace(system, mechanisms=tuple(nodes)))
    world = {'source_commit': 'scripted-native-QA', 'model_digest': BINDING['model_revision'],
             'corpus_sha256': BINDING['corpus_sha256']}
    calls = []
    def factory(spec, run_seed, run_id):
        calls.append(run_id)
        if len(calls) == 2:
            raise PortableStop('QA interruption after first committed draw')
        monkeypatch.setitem(BINDING, 'cell', spec.fingerprint)
        monkeypatch.setitem(BINDING, 'science_config', {**BINDING['science_config'], 'source_commit': world['source_commit']})
        seed()
        return make_sim(tmp_path / 'runs' / run_id, native=NativeScienceKernel(spec))[0]
    def create():
        return NativeGradientCampaign(tmp_path / 'campaign',
            NativeDiscretePolicySearch(options, loss_spec=loss_spec(), distribution='bernoulli', seed=42),
            loss_spec=loss_spec(), seeds=[42], world_binding=world)
    campaign = create()
    with pytest.raises(PortableStop):
        campaign.advance(simulation_factory=factory, count=4)
    assert len(campaign.state['observations']) == 1
    resumed = create()
    report = resumed.advance(simulation_factory=factory, count=4)
    assert report['status'] == 'updated'
    assert len(set(report['losses'])) == 2
    assert report['gradient'][0] > 0  # rejecting threshold choice should become less probable
    assert report['logits_after'][0] < report['logits_before'][0]
    assert calls[0] != calls[2] and calls[1] == calls[2]
    assert create().state == resumed.state
