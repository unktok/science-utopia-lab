from copy import deepcopy

import pytest
import torch

from utopia.system.native_tensor_examples import addressed_selection_program
from utopia.system.tensor_program import SCHEMA, execute_tensor_program, validate_tensor_program


def one(op, attrs=None):
    return {'schema': SCHEMA, 'inputs': {'x': [-1] if op != 'match' else [-1, 3]},
        'parameters': {}, 'state': {}, 'nodes': [{'id': 'result', 'op': op,
        'args': ['input:x'], 'attrs': attrs or {}}], 'outputs': {'result': 'result'}, 'updates': {}}


@pytest.mark.parametrize('op', ['choose', 'gate', 'sort', 'match'])
def test_discrete_operation_has_real_soft_derivative_and_hard_projection(op):
    p = one(op)
    value = [[4., 1., 0.], [0., 3., 1.], [1., 0., 5.]] if op == 'match' else [3., 1., 2.]
    x = torch.tensor(value, dtype=torch.float64, requires_grad=True)
    def soft(v): return execute_tensor_program(p, {'x': v}, temperature=0.7)[0]['result']
    assert torch.autograd.gradcheck(soft, (x,), atol=1e-5)
    hard = execute_tensor_program(p, {'x': x.detach()}, hard=True)[0]['result']
    cold = execute_tensor_program(p, {'x': x.detach()}, temperature=0.01)[0]['result']
    assert torch.allclose(cold, hard, atol=1e-4)


def test_same_institution_program_addresses_slots_branches_and_carries_memory():
    program = addressed_selection_program()
    features = {'features': torch.tensor([[3., 3.], [5., 3.]], dtype=torch.float64)}
    parameters = {k: torch.tensor(v, dtype=torch.float64, requires_grad=True) for k, v in program['parameters'].items()}
    first, memory = execute_tensor_program(program, features, parameters=parameters)
    second, later = execute_tensor_program(program, features, parameters=parameters, state=memory)
    assert later['accepted_so_far'].grad_fn is not None
    gradients = torch.autograd.grad(second['accept'].sum(), tuple(parameters.values()))
    assert all(torch.isfinite(g).all() and g.abs().sum() > 0 for g in gradients)
    hard, _ = execute_tensor_program(program, features, hard=True)
    assert hard['accept'].tolist() == [0., 1.]
    assert hard['addresses'].tolist() == [[1., 0.], [1., 0.]]


def test_ties_are_not_claimed_to_converge_to_hard_tie_breaking():
    p = one('choose')
    x = torch.tensor([1., 1.], dtype=torch.float64)
    hard = execute_tensor_program(p, {'x': x}, hard=True)[0]['result']
    soft = execute_tensor_program(p, {'x': x}, temperature=0.001)[0]['result']
    assert hard.tolist() == [1., 0.] and soft.tolist() == [0.5, 0.5]


@pytest.mark.parametrize('mutation', ['op', 'reference', 'state', 'boolean', 'nonfinite'])
def test_invalid_or_unsafe_program_fails_without_host_source_execution(mutation):
    p = addressed_selection_program()
    if mutation == 'op': p['nodes'][0]['op'] = '__import__'
    if mutation == 'reference': p['nodes'][0]['args'][0] = 'nonexistent'
    if mutation == 'state': p['updates'] = {}
    if mutation == 'boolean': p['parameters']['bias'] = True
    if mutation == 'nonfinite': p['parameters']['bias'] = float('nan')
    with pytest.raises((ValueError, TypeError)):
        validate_tensor_program(p)
