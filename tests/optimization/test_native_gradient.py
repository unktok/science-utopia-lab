from dataclasses import replace

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.blackbox import Observation
from utopia.optimization.native_gradient import NativeScoreFunctionSearch
from utopia.system.native_kernel import legacy_world_system


def design():
    system = legacy_world_system()
    node = replace(system.mechanisms[0], parameters={'free-design-parameter': 0.5})
    return replace(system, mechanisms=(node, *system.mechanisms[1:]))


def optimizer():
    return NativeScoreFunctionSearch(design(), [{'path': '/mechanisms/0/parameters/free-design-parameter', 'lower': 0., 'upper': 1.}],
                                     loss_spec=loss_spec(), seed=42)


def observation(search, suggestion, loss=None, status='complete'):
    return Observation('obs-' + suggestion.suggestion_id, suggestion.suggestion_id, suggestion.candidate, status,
        loss, {'loss_spec_sha256': search.loss_hash, 'world_backend': 'native-research-world'})


def test_score_function_derivative_matches_closed_form_and_resumes_pending():
    search = optimizer()
    suggestions = search.ask(4)
    resumed = NativeScoreFunctionSearch.from_state(search.state_dict(), loss_spec=loss_spec())
    assert resumed.state_dict() == search.state_dict()
    costs = [1., 4., 2., 8.]
    latent = [r['latent'][0] for r in search.pending]
    expected = sum((cost - (sum(costs)-cost)/3) * z / search.sigma**2 for cost, z in zip(costs, latent)) / 4
    report = resumed.tell([observation(search, s, c) for s, c in zip(suggestions, costs)])
    assert report['gradient'][0] == pytest.approx(expected)
    assert report['mean_after'][0] == pytest.approx(-search.learning_rate * expected)
    assert report['end_to_end_native_autograd'] is False


def test_failed_native_sample_prevents_update_not_fabricated_penalty():
    search = optimizer()
    first, second = search.ask(2)
    report = search.tell([observation(search, first, 3.), observation(search, second, status='failed')])
    assert report['status'] == 'not-updated-technical-failure'
    assert report['mean_after'] == report['mean_before']
    assert report['gradient'] is None


def test_partial_replicate_failure_cannot_condition_gradient_on_success():
    search = optimizer()
    first, second = search.ask(2)
    partial = observation(search, first, 3.)
    # A LossSpec may allow a smaller minimum of valid replicates. That does not
    # authorize dropping a failed replicate from a native gradient estimate.
    partial.metadata['technical_failures'] = [{'run_id': 'failed-seed', 'loss': None}]
    report = search.tell([partial, observation(search, second, 2.)])
    assert report['status'] == 'not-updated-technical-failure'
    assert report['gradient'] is None
    assert report['mean_after'] == report['mean_before']


def test_antithetic_estimate_uses_paired_native_losses_without_iid_baseline():
    search = NativeScoreFunctionSearch(design(), [{'path': '/mechanisms/0/parameters/free-design-parameter', 'lower': 0., 'upper': 1.}],
        loss_spec=loss_spec(), seed=42, sampling='antithetic')
    first, second = search.ask(2)
    assert search.pending[0]['latent'][0] == -search.pending[1]['latent'][0]
    resumed = NativeScoreFunctionSearch.from_state(search.state_dict(), loss_spec=loss_spec())
    expected = (1. - 3.) * search.pending[0]['latent'][0] / (2 * search.sigma**2)
    report = resumed.tell([observation(search, first, 1.), observation(search, second, 3.)])
    assert report['gradient'][0] == pytest.approx(expected)
    assert report['method'] == 'native-antithetic-score-function'
    assert 'not pathwise' in report['feedback_scope']


def test_equal_paired_costs_are_zero_gradient_not_rerolled():
    search = NativeScoreFunctionSearch(design(), [{'path': '/mechanisms/0/parameters/free-design-parameter', 'lower': 0., 'upper': 1.}],
        loss_spec=loss_spec(), sampling='antithetic')
    suggestions = search.ask(2)
    report = search.tell([observation(search, s, -3.) for s in suggestions])
    assert report['gradient'] == [0.]
    assert report['mean_before'] == report['mean_after']


def test_paired_draws_require_even_count():
    search = NativeScoreFunctionSearch(design(), [{'path': '/mechanisms/0/parameters/free-design-parameter', 'lower': 0., 'upper': 1.}],
        loss_spec=loss_spec(), sampling='antithetic')
    with pytest.raises(ValueError, match='even'):
        search.ask(3)


def test_mismatched_gradient_evidence_cannot_update():
    search = optimizer()
    first, second = search.ask(2)
    wrong = observation(search, first, 3.)
    wrong.metadata['loss_spec_sha256'] = 'changed'
    with pytest.raises(ValueError, match='binding'):
        search.tell([wrong, observation(search, second, 2.)])


def test_score_function_updates_from_real_native_lifecycle_losses(tmp_path, fixed_corpus):
    from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
    from tests.system.test_native_science_kernel import make_sim
    from utopia.system.native_design_examples import deliberation_patch
    from utopia.system.design_patch import apply_design_patch
    from utopia.system.code_mechanisms import DockerCodeExecutor, CodeExecutionError
    from utopia.system.native_kernel import NativeScienceKernel
    from utopia.optimization.native_world import evaluate_native_suggestion
    try:
        executor = DockerCodeExecutor()
    except (OSError, CodeExecutionError):
        pytest.skip('local isolated Python runtime required')
    system = apply_design_patch(legacy_world_system(), deliberation_patch(legacy_world_system(), image_id=executor.image_id))
    index = next(i for i, n in enumerate(system.mechanisms) if n.mechanism_id == 'world.selection')
    search = NativeScoreFunctionSearch(system, [{'path': f'/mechanisms/{index}/parameters/threshold', 'lower': 1., 'upper': 7.}],
                                     loss_spec=loss_spec(), seed=42, sigma=1.2)
    def factory(spec, run_seed, run_id):
        seed()
        return make_sim(tmp_path / run_id, native=NativeScienceKernel(spec))[0]
    suggestions = search.ask(4)
    observations = [evaluate_native_suggestion(s, seeds=[42], simulation_factory=factory, loss_spec=loss_spec()) for s in suggestions]
    assert all(o.status == 'complete' for o in observations)
    assert len({o.loss for o in observations}) == 2
    report = search.tell(observations)
    assert report['status'] == 'updated'
    assert report['gradient'][0] > 0  # minimizing negative accepted count lowers threshold
    assert report['mean_after'][0] < report['mean_before'][0]


def test_gradient_campaign_retains_completed_draw_across_interruption(tmp_path, fixed_corpus,monkeypatch):
    from tests.runtime.test_portable_checkpoint_integration import seed,BINDING
    from tests.system.test_native_science_kernel import make_sim
    from utopia.system.native_kernel import NativeScienceKernel
    from utopia.optimization.native_gradient import NativeGradientCampaign
    from utopia.runtime.checkpointing import PortableStop
    world={'source_commit':'scripted-continuous-native-QA','model_digest':BINDING['model_revision'],
        'corpus_sha256':BINDING['corpus_sha256'],'years':6}
    calls = []
    def factory(spec, run_seed, run_id):
        calls.append(run_id)
        if len(calls) == 2:
            raise PortableStop('after first committed draw')
        monkeypatch.setitem(BINDING,'cell',spec.fingerprint)
        monkeypatch.setitem(BINDING,'science_config',{**BINDING['science_config'],'source_commit':world['source_commit']})
        seed()
        return make_sim(tmp_path / 'runs' / run_id, native=NativeScienceKernel(spec))[0]
    def create():
        return NativeGradientCampaign(tmp_path / 'campaign', optimizer(), loss_spec=loss_spec(), seeds=[42],
                                      world_binding=world)
    campaign = create()
    with pytest.raises(PortableStop):
        campaign.advance(simulation_factory=factory)
    assert len(campaign.state['observations']) == 1
    # Continuous gradients need the same real receipt checks as discrete ones.
    # Tamper only a local in-memory copy, never the saved original observation.
    from copy import deepcopy
    correct=deepcopy(campaign.state)
    for field,value in [('seed',43),('checkpoint_sha256','0'*64),('system_fingerprint','0'*64)]:
        campaign.state=deepcopy(correct)
        campaign.state['observations'][0]['metadata']['runs'][0][field]=value
        with pytest.raises(ValueError,match='discrete policy'):
            campaign._validate()
    campaign.state=correct
    resumed = create()
    report = resumed.advance(simulation_factory=factory)
    assert report['status'] == 'updated'
    assert calls[0] != calls[2] and calls[1] == calls[2]
    assert create().state == resumed.state
