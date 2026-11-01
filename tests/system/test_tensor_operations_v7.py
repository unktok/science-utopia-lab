"""Operational tensor vocabulary, not invented scientific-world dynamics."""
from copy import deepcopy

import pytest
import torch

from utopia.system.tensor_program import SCHEMA, execute_tensor_program, validate_tensor_program


def program(op, inputs, *, attrs=None):
    return {'schema': SCHEMA, 'inputs': {k: list(v.shape) for k, v in inputs.items()},
        'parameters': {}, 'state': {}, 'nodes': [{'id': 'result', 'op': op,
        'args': ['input:' + key for key in inputs], 'attrs': attrs or {}}],
        'outputs': {'result': 'result'}, 'updates': {}}


@pytest.mark.parametrize('op,values,attrs', [
    ('exp', [[.2, -.1]], {}), ('log', [[.7, 1.3]], {}), ('sqrt', [[.7, 1.3]], {}),
    ('abs', [[-.7, 1.3]], {}), ('logsumexp', [[[.2, -.1], [.3, .8]]], {'dim': -1}),
    ('minimum', [[.2, .9], [.8, .1]], {}), ('maximum', [[.2, .9], [.8, .1]], {}),
    ('clip', [[-.3, .4]], {'min': -.2, 'max': .8}),
    ('stack', [[.2, .9], [.8, .1]], {'dim': 0}),
    ('route', [[.9, -.2], [[.3, .8], [.7, -.4]]], {}),
    ('attention', [[.8, .2], [[.9, .1], [.2, .5]], [[.3, .8], [.7, -.4]]], {}),
    ('memory_read', [[.3, .7], [[.3, .8], [.7, -.4]]], {}),
    ('sample', [[.8, -.2], [.1, -.3]], {}),
    ('normal_sample', [[.3, -.2], [.5, .7], [.2, -.8]], {}),
])
def test_composed_operations_have_numerically_correct_conditional_gradients(op, values, attrs):
    inputs = {f'x{i}': torch.tensor(v, dtype=torch.float64, requires_grad=True) for i, v in enumerate(values)}
    definition = program(op, inputs, attrs=attrs)
    def call(*args):
        return execute_tensor_program(definition, dict(zip(inputs, args)), temperature=.7)[0]['result']
    assert torch.autograd.gradcheck(call, tuple(inputs.values()), atol=1e-5)


@pytest.mark.parametrize('op', ['memory_write', 'scatter_add'])
def test_recurrent_addressed_memory_retains_real_gradients(op):
    inputs = {'memory': torch.tensor([[.3, .8], [.7, -.4]], dtype=torch.float64),
        'logits': torch.tensor([.8, -.2], dtype=torch.float64),
        'value': torch.tensor([.2, .9], dtype=torch.float64)}
    definition = {'schema': SCHEMA, 'inputs': {k: list(v.shape) for k, v in inputs.items()},
        'parameters': {}, 'state': {}, 'nodes': [
            {'id': 'address', 'op': 'choose', 'args': ['input:logits'], 'attrs': {}},
            {'id': 'result', 'op': op, 'args': ['input:memory', 'address', 'input:value'], 'attrs': {}}],
        'outputs': {'result': 'result'}, 'updates': {}}
    assert torch.autograd.gradcheck(lambda *a: execute_tensor_program(definition,
        dict(zip(inputs, a)))[0]['result'], tuple(v.requires_grad_() for v in inputs.values()))
    hard = execute_tensor_program(definition, inputs, hard=True)[0]['result']
    expected = inputs['memory'].clone()
    expected[0] = inputs['value'] if op == 'memory_write' else expected[0] + inputs['value']
    assert torch.equal(hard, expected)


def test_exogenous_sample_noise_is_explicit_and_ties_are_not_hidden():
    inputs = {'logits': torch.tensor([1., 1.], dtype=torch.float64), 'noise': torch.tensor([0., 0.], dtype=torch.float64)}
    definition = program('sample', inputs)
    hard = execute_tensor_program(definition, inputs, hard=True)[0]['result']
    soft = execute_tensor_program(definition, inputs, temperature=.01)[0]['result']
    assert hard.tolist() == [1., 0.] and soft.tolist() == [.5, .5]
    inputs['noise'] = torch.tensor([-.3, .3], dtype=torch.float64)
    assert execute_tensor_program(definition, inputs, hard=True)[0]['result'].tolist() == [0., 1.]


def test_resource_bounds_and_invalid_numeric_domains_fail_not_silently_clip():
    values = {'x': torch.tensor([-1.], dtype=torch.float64)}
    with pytest.raises(ValueError, match='nonfinite'):
        execute_tensor_program(program('log', values), values)
    values = {'x': torch.ones(1, dtype=torch.int64)}
    with pytest.raises(ValueError):
        execute_tensor_program(program('exp', values), values)
    values = {'x': torch.ones((128, 128), dtype=torch.float64), 'y': torch.ones((128, 128), dtype=torch.float64)}
    definition = program('matmul', values)
    # A bounded pair of vectors can still request a huge outer product.
    values = {'x': torch.ones((16384, 1), dtype=torch.float64), 'y': torch.ones((1, 16384), dtype=torch.float64)}
    definition = program('matmul', values)
    definition['inputs'] = {'x': [-1, 1], 'y': [1, -1]}
    with pytest.raises(ValueError, match='before allocation'):
        execute_tensor_program(definition, values)
    bad = deepcopy(program('clip', {'x': torch.ones(1)}))
    with pytest.raises(ValueError, match='clip requires'):
        validate_tensor_program(bad)
