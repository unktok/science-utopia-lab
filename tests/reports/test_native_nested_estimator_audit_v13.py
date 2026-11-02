"""Analytic independent conditional scores, no native/LLM execution."""
from copy import deepcopy

import pytest

from scripts.native_nested_estimator_audit_v13 import analytic_draw, conditional_update_proof
from tests.optimization.test_native_adaptive_search import tiny_definition, tiny_parent, loss_spec, synthetic_observation
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign


def record(costs=(1., 4.), definition=None):
    definition = definition or tiny_definition()
    mixed = GeneratedMixedDesign(tiny_parent(), definition, loss_spec=loss_spec(), seed=42)
    draws = mixed.draw(2, version_sha256='unit-only')
    observations = [synthetic_observation(draw, cost) for draw, cost in zip(draws, costs)]
    return {'stage': 'initial-batch', 'generation_error': None, 'definition': definition,
        'draws': draws, 'observations': observations,
        'report': mixed.update(draws, observations, score=True)}


@pytest.mark.parametrize('costs', [(1., 4.), (2., 2.), (-5., 7.)])
def test_closed_form_bernoulli_gaussian_scores_rederive_autograd_loo_update(costs):
    initial = record(costs)
    result = conditional_update_proof([initial])
    assert result['updates'] == 1
    assert result['independently_derived_gradient']['continuous_mean'] == pytest.approx(
        initial['report']['gradient']['continuous_mean'])


def test_masked_categorical_and_deterministic_conditional_factor_scores():
    definition = tiny_definition()
    definition['factors'][0]['kind'] = 'categorical'
    definition['factors'][0]['choices'].append(deepcopy(definition['factors'][0]['choices'][0]))
    definition['factors'][0]['choices'][-1]['id'] = 'third'
    definition['logits'] = {'code-choice': [.4, -.2, .7], 'dependent': [3., -4.]}
    definition['factors'].append({'id': 'dependent', 'kind': 'categorical',
        'choices': deepcopy(definition['factors'][0]['choices'][:2]),
        'support': [{'when': {'code-choice': choice['id']}, 'allow': ['left']}
            for choice in definition['factors'][0]['choices']]})
    initial = record(definition=definition)
    result = conditional_update_proof([initial])
    assert result['independently_derived_gradient']['logits']['dependent'] == [0., 0.]


@pytest.mark.parametrize('tamper', ['likelihood', 'gradient', 'updated-weight'])
def test_rehashed_runtime_receipts_cannot_override_analytic_identity(tamper):
    initial = record()
    if tamper == 'likelihood': initial['draws'][0]['conditional_latent_log_probability'] += 1.
    elif tamper == 'gradient': initial['report']['gradient']['continuous_mean'][0] += 1.
    else: initial['report']['weights_after']['continuous_mean'][0] += 1.
    with pytest.raises(ValueError, match='derived'):
        conditional_update_proof([initial])


def test_invalid_initial_source_preserves_error_no_estimate():
    error = {'type': 'ValueError', 'message': 'unit-only invalid source', 'loss': None}
    result = conditional_update_proof([{'generation_error': error}])
    assert result['updates'] == 0 and result['error'] == error
