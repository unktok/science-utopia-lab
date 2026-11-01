"""Externally authored fixture programs; never evidence of model invention."""
from copy import deepcopy
from dataclasses import replace

import pytest
import torch

from tests.optimization.test_native_world import loss_spec
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.blackbox import Observation
from utopia.optimization.native_factorized_gradient import NativeFactorizedDesignSearch, NativeFactorizedGradientCampaign
from utopia.system import ChannelKind, ConnectionSpec, PortSpec
from utopia.system.design_patch import apply_design_patch, digest
from utopia.system.native_design_examples import deliberation_patch
from utopia.system.native_kernel import CONTROL_ARTIFACT, legacy_world_system


PROVENANCE = {'kind': 'scripted-software-QA-not-LLM-invention', 'author': 'test fixture'}
CONSUMER = """def step(context):
    packet = context['inputs']['deliberations'][0]['payload']
    decisions = []
    for paper in packet[context['parameters']['records_key']]:
        accept = paper['score'] >= context['parameters']['threshold']
        decisions.append({'payload': {'paper_id': paper['paper_id'], 'conference_id': paper['conference_id'], 'final_score': paper['score'], 'decision': 'accept' if accept else 'reject'}})
    if not decisions:
        decisions = [{'payload': {'empty_cycle': True}}]
    return {'outputs': {'next': [{'payload': {'year': context['period']}}], 'world': [{'payload': packet['world']}], 'decisions': decisions}, 'state': {}}
"""
OVERRIDE = CONSUMER.replace("accept = paper['score'] >= context['parameters']['threshold']",
    "accept = bool(context['inputs']['override']) or paper['score'] >= context['parameters']['threshold']")


def choice(name, operations):
    return {'id': name, 'operations': operations, 'provenance': deepcopy(PROVENANCE)}


def edit(path, value):
    return {'op': 'replace', 'path': path, 'value': value}


def design_definition(image='sha256:' + 'a' * 64):
    base = apply_design_patch(legacy_world_system(), deliberation_patch(legacy_world_system(), image_id=image))
    ci = next(i for i, n in enumerate(base.mechanisms) if n.mechanism_id == 'world.selection')
    pi = next(i for i, n in enumerate(base.mechanisms) if n.mechanism_id == 'deliberation-assembly')
    ai = next(i for i, a in enumerate(base.artifact_types) if a.artifact_type_id == 'native-deliberation')
    consumer = base.mechanisms[ci]
    artifact = deepcopy(consumer.parameters['code_artifact'])
    artifact['source'], artifact['inputs']['override'] = OVERRIDE, {'type': 'object'}
    consumer = replace(consumer, inputs=(*consumer.inputs, PortSpec('override', ChannelKind.SIGNAL, CONTROL_ARTIFACT, False)),
        parameters={**consumer.parameters, 'records_key': 'proposals', 'code_artifact': artifact})
    base = replace(base, mechanisms=tuple(consumer if i == ci else n for i, n in enumerate(base.mechanisms)))
    path = f'/mechanisms/{ci}'
    edge = ConnectionSpec('world.review', 'next', 'world.selection', 'override', ChannelKind.SIGNAL)
    connected = replace(base, connections=(*base.connections, edge)).to_dict()['connections']
    producer_source = base.mechanisms[pi].parameters['code_artifact']['source']
    factors = [
        {'id': 'code', 'kind': 'categorical', 'choices': [
            choice('threshold', [edit(path + '/parameters/code_artifact/source', CONSUMER),
                {'op': 'remove', 'path': path + '/inputs/2'},
                {'op': 'remove', 'path': path + '/parameters/code_artifact/inputs/override'}]),
            choice('edge-aware', [edit(path + '/parameters/code_artifact/source', OVERRIDE)])]},
        {'id': 'edge', 'kind': 'bernoulli', 'choices': [choice('off', []), choice('on', [edit('/connections', connected)])],
            'support': [{'when': {'code': 'threshold'}, 'allow': ['off']},
                        {'when': {'code': 'edge-aware'}, 'allow': ['off', 'on']}]},
        {'id': 'parameter', 'kind': 'categorical', 'choices': [
            choice('low', [edit(path + '/parameters/threshold', 1.)]),
            choice('high', [edit(path + '/parameters/threshold', 7.)])]},
        {'id': 'protocol', 'kind': 'categorical', 'choices': [choice('proposals', []),
            choice('dossier', [edit(f'/mechanisms/{pi}/parameters/code_artifact/source',
                    producer_source.replace("'proposals': proposals", "'dossier': proposals")),
                edit(path + '/parameters/records_key', 'dossier'),
                edit(f'/mechanisms/{pi}/outputs/0/artifact_type', 'externally-authored-dossier-v6'),
                edit(path + '/inputs/1/artifact_type', 'externally-authored-dossier-v6'),
                edit(f'/artifact_types/{ai}/artifact_type_id', 'externally-authored-dossier-v6')])]},
    ]
    return base, factors


def search(**kwargs):
    base, factors = design_definition()
    return NativeFactorizedDesignSearch(base, factors, loss_spec=loss_spec(), design_provenance=PROVENANCE, **kwargs)


def observation(policy, suggestion, cost=1., status='complete'):
    return Observation('obs-' + suggestion.suggestion_id, suggestion.suggestion_id, suggestion.candidate,
        status, cost if status == 'complete' else None,
        {'world_backend': 'native-research-world', 'loss_spec_sha256': policy.loss_hash})


def costs_for(actions):
    return torch.tensor([2 * (a['code'] == 'edge-aware') - 5 * (a['edge'] == 'on')
        + 3 * (a['parameter'] == 'high') + (a['protocol'] == 'dossier') for a in actions], dtype=torch.float64)


def test_exact_conditional_joint_logprob_gradient_matches_expectation_and_finite_difference():
    policy = search(logits={'code': [.2, -.5], 'edge': [.4], 'parameter': [.7, -.2], 'protocol': [-.3, .8]})
    actions = policy.assignments
    assert len(actions) == 12 and not any(a['code'] == 'threshold' and a['edge'] == 'on' for a in actions)
    logq, costs = policy.action_log_probability(actions), costs_for(actions)
    assert logq.exp().sum().item() == pytest.approx(1., abs=1e-14)
    parameters = tuple(policy.logits.values())
    exact = torch.autograd.grad((logq.exp() * costs).sum(), parameters, retain_graph=True)
    score = torch.autograd.grad((logq.exp().detach() * (costs - 13.) * logq).sum(), parameters)
    assert all(torch.allclose(a, b, atol=1e-13) for a, b in zip(exact, score))
    for (name, parameter), gradient in zip(policy.logits.items(), exact):
        for i in range(len(parameter)):
            saved = float(parameter[i].detach())
            with torch.no_grad(): parameter[i] = saved + 1e-5
            plus = float((policy.action_log_probability(actions).exp() * costs).sum().detach())
            with torch.no_grad(): parameter[i] = saved - 1e-5
            minus = float((policy.action_log_probability(actions).exp() * costs).sum().detach())
            with torch.no_grad(): parameter[i] = saved
            assert float(gradient[i]) == pytest.approx((plus-minus)/2e-5, abs=2e-10)
    threshold_action = next(a for a in actions if a['code'] == 'threshold')
    edge_gradient = torch.autograd.grad(policy.action_log_probability([threshold_action]).sum(), policy.logits['edge'])[0]
    assert edge_gradient.tolist() == [0.]  # Conditional singleton, not an unnormalized Bernoulli score.


def test_atomic_free_source_protocol_wiring_and_parameter_compilation():
    policy = search()
    action = {'code': 'edge-aware', 'edge': 'on', 'parameter': 'high', 'protocol': 'dossier'}
    candidate, patch = policy.compile_assignment(action)
    consumer = next(n for n in candidate.mechanisms if n.mechanism_id == 'world.selection')
    producer = next(n for n in candidate.mechanisms if n.mechanism_id == 'deliberation-assembly')
    assert consumer.parameters['code_artifact']['source'] == OVERRIDE
    assert consumer.parameters['threshold'] == 7 and consumer.parameters['records_key'] == 'dossier'
    assert producer.outputs[0].artifact_type == 'externally-authored-dossier-v6'
    assert any(c.target_port == 'override' for c in candidate.connections)
    assert apply_design_patch(policy.base, patch) == candidate


def test_invalid_grammar_never_filters_resamples_or_assigns_numeric_failure_cost():
    base, factors = design_definition()
    # Removing declared conditioning admits a missing-port edge combination.
    factors[1].pop('support')
    with pytest.raises(ValueError, match='entire factor grammar rejected'):
        NativeFactorizedDesignSearch(base, factors, loss_spec=loss_spec(), design_provenance=PROVENANCE)
    base, factors = design_definition()
    factors[1]['support'].append({'when': {'code': 'edge-aware'}, 'allow': ['on']})
    with pytest.raises(ValueError, match='exactly once'):
        NativeFactorizedDesignSearch(base, factors, loss_spec=loss_spec(), design_provenance=PROVENANCE)
    with pytest.raises(ValueError, match='budget'):
        search(max_assignments=4)
    with pytest.raises(ValueError, match='zero-support'):
        search().action_log_probability([{'code': 'threshold', 'edge': 'on', 'parameter': 'low', 'protocol': 'proposals'}])
    unknown = base.to_dict()
    unknown['silently-discarded-field'] = True
    with pytest.raises(ValueError, match='no silent design remapping'):
        NativeFactorizedDesignSearch(unknown, factors, loss_spec=loss_spec(), design_provenance=PROVENANCE)


@pytest.mark.parametrize('baseline,cost,zero', [(0., 0., True), ('leave-one-out', -3., True), (0., -3., False)])
def test_equal_zero_costs_and_finite_sample_score_noise_are_explicit(baseline, cost, zero):
    policy = search(baseline=baseline)
    suggestions = policy.ask(4)
    report = policy.tell([observation(policy, s, cost) for s in suggestions])
    assert report['all_equal_costs'] and not report['pathwise_native_or_llm_derivative']
    assert report['all_zero_costs'] is (cost == 0.)
    if zero:
        assert all(all(value == 0 for value in gradient) for gradient in report['gradient'].values())
        assert report['logits_before'] == report['logits_after']
    else:
        assert any(any(value != 0 for value in gradient) for gradient in report['gradient'].values())
        assert 'no comparative evidence' in report['sampling_note']


def test_pending_rng_joint_likelihood_provenance_and_next_design_resume():
    policy = search(baseline='leave-one-out')
    suggestions = policy.ask(5)
    state = policy.state_dict()
    resumed = NativeFactorizedDesignSearch.from_state(state, loss_spec=loss_spec())
    assert resumed.state_dict() == state
    costs = costs_for([r['assignment'] for r in policy.pending])
    report = resumed.tell([observation(policy, s, float(cost)) for s, cost in zip(suggestions, costs)])
    assert report['status'] == 'updated'
    before = resumed.state_dict()
    after = NativeFactorizedDesignSearch.from_state(before, loss_spec=loss_spec())
    assert [s.to_dict() for s in resumed.ask(3)] == [s.to_dict() for s in after.ask(3)]
    for field, value in [('joint_log_probability', 999.), ('rng_seed', 9), ('assignment', {'code': 'missing'})]:
        bad = deepcopy(state)
        bad['pending'][0][field] = value
        with pytest.raises(ValueError, match='changed'):
            NativeFactorizedDesignSearch.from_state(bad, loss_spec=loss_spec())
    bad = deepcopy(state)
    bad['design_provenance']['author'] = 'changed'
    with pytest.raises(ValueError, match='provenance'):
        NativeFactorizedDesignSearch.from_state(bad, loss_spec=loss_spec())
    for key, value in [('baseline', 99.), ('learning_rate', .5), ('seed', 91)]:
        bad = deepcopy(state)
        bad[key] = value
        with pytest.raises(ValueError, match='settings'):
            NativeFactorizedDesignSearch.from_state(bad, loss_spec=loss_spec())


def test_many_to_one_actions_keep_original_joint_probabilities_not_design_remapping():
    base = legacy_world_system()
    factors = [{'id': 'alias', 'kind': 'bernoulli', 'choices': [choice('left', []), choice('right', [])]}]
    policy = NativeFactorizedDesignSearch(base, factors, loss_spec=loss_spec(), design_provenance=PROVENANCE,
        logits={'alias': [.5]}, baseline='leave-one-out')
    suggestions = policy.ask(8)
    assert len({digest(s.candidate) for s in suggestions}) == 1
    assert len({digest(r['assignment']) for r in policy.pending}) == 2
    assert len({r['joint_log_probability'] for r in policy.pending}) == 2
    assert len({s.suggestion_id for s in suggestions}) == 8
    report = policy.tell([observation(policy, s, 2.) for s in suggestions])
    assert report['gradient'] == {'alias': [0.]}
    assert report['distinct_sampled_systems'] == 1 and report['distinct_sampled_assignments'] == 2


def test_failed_native_draw_or_partial_replicate_prevents_entire_update():
    policy = search()
    a, b = policy.ask(2)
    report = policy.tell([observation(policy, a, -100.), observation(policy, b, status='failed')])
    assert report['status'] == 'not-updated-technical-failure' and report['losses'] == [-100., None]
    assert report['gradient'] is None and report['logits_before'] == report['logits_after']
    a, b = policy.ask(2)
    partial = observation(policy, a, -100.)
    partial.metadata['technical_failures'] = [{'loss': None}]
    assert policy.tell([partial, observation(policy, b, -3.)])['gradient'] is None


def test_extreme_finite_logits_keep_stable_exact_log_probabilities():
    policy = search(logits={'code': [1000., -1000.], 'edge': [1000.], 'parameter': [0., 0.], 'protocol': [0., 0.]})
    assert torch.isfinite(policy.action_log_probability(policy.assignments)).all()


def test_actual_native_full_losses_factorized_backward_and_campaign_crash_resume(tmp_path, monkeypatch, fixed_corpus):
    # Complete original Simulation years/agents/research/review/publication:
    # only corpus/retrieval/HTTP are scripted. No scientific inference calls.
    from tests.runtime.test_portable_checkpoint_integration import BINDING, seed
    from tests.system.test_native_science_kernel import make_sim
    from utopia.runtime.checkpointing import PortableStop
    from utopia.system.code_mechanisms import DockerCodeExecutor, CodeExecutionError
    from utopia.system.native_kernel import NativeScienceKernel
    try:
        executor = DockerCodeExecutor()
    except (OSError, CodeExecutionError):
        pytest.skip('isolated local Python runtime required for full native QA')
    base, factors = design_definition(executor.image_id)
    world = {'source_commit': 'factorized-native-scripted-QA', 'model_digest': BINDING['model_revision'],
        'corpus_sha256': BINDING['corpus_sha256']}
    calls = []
    def factory(spec, run_seed, run_id):
        calls.append(run_id)
        if len(calls) == 2:
            raise PortableStop('QA interruption after committed first joint draw')
        monkeypatch.setitem(BINDING, 'cell', spec.fingerprint)
        monkeypatch.setitem(BINDING, 'science_config', {**BINDING['science_config'], 'source_commit': world['source_commit']})
        seed()
        return make_sim(tmp_path / 'runs' / run_id, native=NativeScienceKernel(spec))[0]
    def create():
        policy = NativeFactorizedDesignSearch(base, factors, loss_spec=loss_spec(), design_provenance=PROVENANCE,
            baseline='leave-one-out', seed=42)
        return NativeFactorizedGradientCampaign(tmp_path / 'campaign', policy,
            loss_spec=loss_spec(), seeds=[42], world_binding=world)
    campaign = create()
    with pytest.raises(PortableStop):
        campaign.advance(simulation_factory=factory, count=8)
    assert len(campaign.state['observations']) == 1
    resumed = create()
    report = resumed.advance(simulation_factory=factory, count=8)
    assert report['status'] == 'updated' and len(set(report['losses'])) > 1
    assert any(any(value != 0 for value in gradient) for gradient in report['gradient'].values())
    assert all(o['metadata']['world_backend'] == 'native-research-world' for o in report['observations'])
    assert {r['assignment']['edge'] for r in report['draws']} == {'off', 'on'}
    assert {r['assignment']['protocol'] for r in report['draws']} == {'proposals', 'dossier'}
    assert calls[0] != calls[2] and calls[1] == calls[2]
    assert create().state == resumed.state
    next_search = resumed._validate()
    next_draws = next_search.ask(2)
    assert next_draws and report['logits_before'] != report['logits_after']
    resumed.state['reports'][0]['gradient']['code'][0] += 1
    with pytest.raises(ValueError, match='update history changed'):
        resumed._validate()
