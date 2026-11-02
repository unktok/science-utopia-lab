"""Analytic/quadrature checks; none of these fixtures is native-world evidence."""
from dataclasses import replace
import json
import math

import numpy as np
import pytest
import torch

from utopia.optimization.native_expectation_estimators import (
    FrozenDesignControlVariate, estimate_expected_loss_gradient,
)


def gaussian(mean=.3, sigma=.7):
    return (torch.tensor([mean], dtype=torch.float64, requires_grad=True),
            torch.tensor([sigma], dtype=torch.float64))


def report(draws, losses, **kwargs):
    return estimate_expected_loss_gradient(draws, losses,
        sample_ids=[f'current-{i}' for i in range(len(draws))], batch_id='current', **kwargs)


def prior_model(assignments=None, latent_dim=1):
    assignments = assignments or [{}]
    rows = [{'assignment': a, 'latent': [z] if latent_dim else []}
            for a in assignments for z in (-2., -.5, 0., 1., 2.)]
    losses = [2 + (3*r['latent'][0]+.4*r['latent'][0]**2 if latent_dim else 0)
              + 2*('b' in r['assignment'].values()) for r in rows]
    return FrozenDesignControlVariate.fit(rows, losses,
        sample_ids=[f'prior-{i}' for i in range(len(rows))], batch_ids=['prior']*len(rows),
        assignments=assignments, latent_dim=latent_dim)


def conditional_policy():
    # Second factor's support depends on the first: A=left forces B=off.
    logits = {'a': torch.tensor([-.4, .8], dtype=torch.float64, requires_grad=True),
              'b': torch.tensor([.3], dtype=torch.float64, requires_grad=True)}
    assignments = [{'a': 'left', 'b': 'off'}, {'a': 'right', 'b': 'off'}, {'a': 'right', 'b': 'on'}]

    def likelihood(rows):
        a = torch.log_softmax(logits['a'], dim=0)
        return torch.stack([a[int(r['a'] == 'right')] +
            (torch.nn.functional.logsigmoid(logits['b'][0] if r['b'] == 'on' else -logits['b'][0])
                if r['a'] == 'right' else logits['b'][0]*0) for r in rows])
    return logits, assignments, likelihood


@pytest.mark.parametrize('controlled', [False, True])
def test_exact_conditional_discrete_gradient_by_enumeration(controlled):
    logits, assignments, likelihood = conditional_policy()
    mean = torch.empty(0, dtype=torch.float64, requires_grad=True)
    sigma = torch.empty(0, dtype=torch.float64)
    probabilities = likelihood(assignments).exp()
    costs = [1.2, -.7, 3.]
    expected = torch.autograd.grad((probabilities*torch.tensor(costs, dtype=torch.float64)).sum(), tuple(logits.values()), retain_graph=True)
    model = prior_model(assignments, 0) if controlled else None
    estimates = []
    for a, loss in zip(assignments, costs):
        r = report([{'assignment': a, 'latent': []}], [loss], logits=logits, mean=mean,
            sigma=sigma, assignments=assignments, discrete_log_probability=likelihood, control_variate=model)
        assert r['status'] == 'valid', r
        estimates.append(r['gradient']['logits'])
    for key, analytic in zip(logits, expected):
        weighted = sum(p*torch.tensor(g[key], dtype=torch.float64) for p, g in zip(probabilities.detach(), estimates))
        assert torch.allclose(weighted, analytic, atol=1e-12, rtol=1e-12)


@pytest.mark.parametrize('controlled', [False, True])
def test_mixed_gaussian_quadratic_gradient_analytic_quadrature(controlled):
    logits, assignments, likelihood = conditional_policy()
    mean, sigma = gaussian()
    probabilities = likelihood(assignments).exp().detach().tolist()
    nodes, weights = np.polynomial.hermite.hermgauss(12)
    model = prior_model(assignments) if controlled else None
    weighted_mean_gradient = 0.
    weighted_logits = {key: np.zeros(len(v)) for key, v in logits.items()}
    for a, p in zip(assignments, probabilities):
        for node, weight in zip(nodes, weights):
            z = mean.item() + math.sqrt(2)*sigma.item()*node
            # Interaction deliberately lies outside the additive fitted model.
            cost = 2+3*z+.4*z*z+(2+1.3*z)*(a['b'] == 'on')
            r = report([{'assignment': a, 'latent': [float(z)]}], [float(cost)], logits=logits,
                mean=mean, sigma=sigma, assignments=assignments,
                discrete_log_probability=likelihood, control_variate=model)
            assert r['status'] == 'valid', r
            integration_weight = p*weight/math.sqrt(math.pi)
            weighted_mean_gradient += integration_weight*r['gradient']['continuous_mean'][0]
            for key in logits:
                weighted_logits[key] += integration_weight*np.asarray(r['gradient']['logits'][key])
    probability_on = sum(p for a, p in zip(assignments, probabilities) if a['b'] == 'on')
    assert weighted_mean_gradient == pytest.approx(3+.8*mean.item()+1.3*probability_on, abs=1e-11)
    exact_discrete = torch.autograd.grad((likelihood(assignments).exp()*torch.tensor(
        [(2+1.3*mean.item())*int(a['b']=='on') for a in assignments], dtype=torch.float64)).sum(), tuple(logits.values()))
    for key, gradient in zip(logits, exact_discrete):
        assert weighted_logits[key] == pytest.approx(gradient.tolist(), abs=1e-11)


def test_frozen_quadratic_control_has_exact_correction_and_near_zero_residual():
    mean, sigma = gaussian()
    model = prior_model()
    r = report([{'assignment': {}, 'latent': [z]} for z in (-.4, .7, 2.)],
        [2+3*z+.4*z*z for z in (-.4, .7, 2.)], logits={}, mean=mean, sigma=sigma,
        control_variate=model)
    assert r['status'] == 'valid', r
    assert r['gradient']['continuous_mean'] == pytest.approx([3.24], abs=3e-6)
    assert r['correction_gradient']['continuous_mean'] == pytest.approx([3.24], abs=3e-6)
    assert r['estimated_gradient_standard_error']['continuous_mean'][0] < 3e-6
    assert model == FrozenDesignControlVariate.from_dict(json.loads(json.dumps(model.to_dict())))
    assert mean.item() == .3 and mean.grad is None


def test_equal_costs_not_rerolled_or_forced_nonzero_and_batch_one():
    mean, sigma = gaussian(0., 1.)
    rows = [{'assignment': {}, 'latent': [z]} for z in (1., 2.)]
    r = report(rows, [5., 5.], logits={}, mean=mean, sigma=sigma)
    assert r['status'] == 'valid' and r['all_equal_costs']
    assert r['gradient']['continuous_mean'] == [7.5]  # Ordinary LR sample noise.
    assert r['loo_gradient']['continuous_mean'] == [0.]
    decimal = report(rows, [.1, .1], logits={}, mean=mean, sigma=sigma)
    assert decimal['loo_gradient']['continuous_mean'] == [0.]
    zero = report(rows, [0., 0.], logits={}, mean=mean, sigma=sigma)
    assert zero['gradient']['continuous_mean'] == [0.]
    single = report(rows[:1], [2.], logits={}, mean=mean, sigma=sigma)
    assert single['gradient']['continuous_mean'] == [2.]
    assert single['loo_gradient'] is None and single['estimated_gradient_standard_error'] is None


def test_control_removes_known_category_function_without_suppressing_true_gradient():
    logits, assignments, likelihood = conditional_policy()
    model = FrozenDesignControlVariate(
        tuple(sorted(json.dumps(a, sort_keys=True, separators=(',', ':')) for a in assignments)),
        0, (0., 1., 2., 4.), ('prior',), ('old',), 1e-6)
    mean = sigma = torch.empty(0, dtype=torch.float64)
    # Even a singleton draw receives exact E[c] discrete derivative.
    draw = {'assignment': assignments[0], 'latent': []}
    c = model.values([(json.dumps(assignments[0], sort_keys=True, separators=(',', ':')), ())]).item()
    r = report([draw], [c], logits=logits, mean=mean, sigma=sigma, assignments=assignments,
        discrete_log_probability=likelihood, control_variate=model)
    assert r['status'] == 'valid', r
    assert r['gradient'] == r['correction_gradient']
    assert any(abs(v) > 0 for values in r['gradient']['logits'].values() for v in values)


@pytest.mark.parametrize('change', ['loss-null', 'loss-nan', 'failed', 'latent-nan', 'sigma-zero',
    'overlap-sample', 'overlap-batch', 'support-mismatch', 'empty'])
def test_invalid_batches_return_null_without_filtering(change):
    mean, sigma = gaussian()
    draws, losses = [{'assignment': {}, 'latent': [.1]}], [2.]
    model = prior_model()
    ids, batch = ['current'], 'current'
    if change == 'loss-null': losses[0] = None
    if change == 'loss-nan': losses[0] = float('nan')
    if change == 'failed': draws[0]['technical_error'] = {'type': 'native-failure'}
    if change == 'latent-nan': draws[0]['latent'] = [float('nan')]
    if change == 'sigma-zero': sigma = torch.tensor([0.], dtype=torch.float64)
    if change == 'overlap-sample': ids = [model.sample_ids[0]]
    if change == 'overlap-batch': batch = 'prior'
    if change == 'support-mismatch': model = replace(model, latent_dim=0, coefficients=(0., 1.))
    if change == 'empty': draws, losses, ids = [], [], []
    r = estimate_expected_loss_gradient(draws, losses, logits={}, mean=mean, sigma=sigma,
        control_variate=model, sample_ids=ids, batch_id=batch)
    assert r['status'] == 'invalid' and r['gradient'] is None
    assert not r['failures_filtered'] and 'reason' in r


def test_prior_fit_rejects_invalid_data_and_model_serialization():
    with pytest.raises(ValueError):
        FrozenDesignControlVariate.fit([{'assignment': {}, 'latent': [0.]}], [None],
            sample_ids=['prior'], batch_ids=['old'], assignments=[{}], latent_dim=1)
    record = prior_model().to_dict()
    record['unknown'] = True
    with pytest.raises(ValueError): FrozenDesignControlVariate.from_dict(record)


def test_incomplete_discrete_support_not_renormalized():
    logits, assignments, likelihood = conditional_policy()
    r = report([{'assignment': assignments[0], 'latent': []}], [1.], logits=logits,
        mean=torch.empty(0, dtype=torch.float64), sigma=torch.empty(0, dtype=torch.float64),
        assignments=assignments[:1], discrete_log_probability=likelihood)
    assert r['status'] == 'invalid' and 'total probability one' in r['reason']


def test_no_parameters_is_legal_identity_estimator():
    r = report([{'assignment': {}, 'latent': []}], [1.], logits={},
        mean=torch.empty(0, dtype=torch.float64), sigma=torch.empty(0, dtype=torch.float64))
    assert r['status'] == 'valid' and r['gradient'] == {'logits': {}, 'continuous_mean': []}


def test_prior_fit_and_estimator_restart_byte_identical():
    model = prior_model()
    second = prior_model()
    assert json.dumps(model.to_dict(), sort_keys=True) == json.dumps(second.to_dict(), sort_keys=True)
    mean, sigma = gaussian()
    draws = [{'assignment': {}, 'latent': [.2]}, {'assignment': {}, 'latent': [.7]}]
    first = report(draws, [1., 2.], logits={}, mean=mean, sigma=sigma, control_variate=model)
    second = report(draws, [1., 2.], logits={}, mean=mean, sigma=sigma,
        control_variate=FrozenDesignControlVariate.from_dict(model.to_dict()))
    assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(second, sort_keys=True, allow_nan=False)


def test_detached_discrete_likelihood_rejected_even_when_continuous_graph_exists():
    logits, assignments, likelihood = conditional_policy()
    mean, sigma = gaussian()
    r = report([{'assignment': assignments[0], 'latent': [.2]}], [1.], logits=logits,
        mean=mean, sigma=sigma, assignments=assignments,
        discrete_log_probability=lambda rows: likelihood(rows).detach())
    assert r['status'] == 'invalid' and 'detached' in r['reason']


def test_overflow_diagnostics_fail_closed():
    mean, sigma = gaussian(0., 1.)
    r = report([{'assignment': {}, 'latent': [1.]}, {'assignment': {}, 'latent': [2.]}],
        [1e308, 1e308], logits={}, mean=mean, sigma=sigma)
    assert r['status'] == 'invalid' and r['gradient'] is None
    json.dumps(r, allow_nan=False)
