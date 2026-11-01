"""Autograd through represented institutions on an authoritative native trace.

Opaque native observations are frozen conditioning data, not invented world
laws. Tensor-to-tensor edges and tensor memory remain in the autograd graph.
This is not an exact gradient through the full counterfactual native world.
"""
from __future__ import annotations

from copy import deepcopy
import torch

from utopia.system.design_patch import digest
from utopia.system.tensor_program import execute_tensor_program


def native_tensor_trace(events):
    result = []
    for event in events:
        value = event.to_dict() if hasattr(event, 'to_dict') else event
        if value['event_type'] == 'native.tensor.executed':
            result.append({'year': value['year'], 'mechanism': value['provenance']['mechanism_id'],
                           'event_id': value['event_id'], **deepcopy(value['payload'])})
    if not result:
        raise ValueError('no actual native tensor events; a fabricated feature world is not a substitute')
    return result


def replay_tensor_trace(trace, programs, *, parameters=None, hard=False, temperature=1.0,
                        verify_recorded=False):
    """Replay recorded inputs while carrying soft memory and represented edges."""
    if not trace:
        raise ValueError('nonempty native tensor trace required')
    parameters = parameters or {}
    if verify_recorded and (not hard or parameters):
        raise ValueError('recorded verification requires unmodified hard execution')
    memory, produced, result = {}, {}, []
    for frame in trace:
        name = frame['mechanism']
        program = programs[name]
        if digest(program) != frame['program_sha256']:
            raise ValueError('native tensor trace program fingerprint changed')
        inputs = {}
        for key, value in frame['inputs'].items():
            source = frame['input_sources'][key]
            dependency = (source['mechanism'], source['port'], source['period'])
            if source['path'] == '/values' and source['mechanism'] in programs:
                if dependency not in produced:
                    raise ValueError('tensor trace missing a represented upstream dependency')
                inputs[key] = produced[dependency]
            else:
                inputs[key] = torch.tensor(value, dtype=torch.float64)
                shape = program['inputs'][key]
                if inputs[key].numel() == 0 and -1 in shape:
                    inputs[key] = inputs[key].reshape([0 if d == -1 else d for d in shape])
        if name not in memory:
            memory[name] = {k: torch.tensor(v, dtype=torch.float64) for k, v in frame['state_before'].items()}
        if verify_recorded:
            for group, actual_values in (('inputs', inputs), ('state_before', memory[name])):
                if set(actual_values) != set(frame[group]):
                    raise ValueError('native tensor hard replay fields differ: ' + group)
                for key, tensor in actual_values.items():
                    expected = torch.tensor(frame[group][key], dtype=tensor.dtype).reshape(tensor.shape)
                    if not torch.allclose(tensor, expected, rtol=0., atol=1e-12):
                        raise ValueError('native tensor hard replay differs: ' + group + '/' + key)
        outputs, memory[name] = execute_tensor_program(program, inputs, parameters=parameters.get(name),
            state=memory[name], hard=hard, temperature=temperature)
        if verify_recorded:
            for group, actual in (('outputs', outputs), ('state_after', memory[name])):
                for key, tensor in actual.items():
                    expected = torch.tensor(frame[group][key], dtype=tensor.dtype).reshape(tensor.shape)
                    if not torch.allclose(tensor, expected, rtol=0., atol=1e-12):
                        raise ValueError('native tensor hard replay differs: ' + group + '/' + key)
        for port, value in outputs.items():
            produced[(name, port, frame['year'])] = value
        result.append({'year': frame['year'], 'mechanism': name, 'event_id': frame['event_id'], 'outputs': outputs})
    return result


def trace_objective(frames, terms):
    """Explicit conditional objective; never substitute for native LossSpec."""
    if not terms:
        raise ValueError('explicit relaxation objective terms required')
    total = torch.tensor(0., dtype=torch.float64)
    for term in terms:
        if set(term) != {'mechanism', 'output', 'coefficient'} or not isinstance(term['coefficient'], (int, float)):
            raise ValueError('invalid trace objective term')
        selected = [f for f in frames if f['mechanism'] == term['mechanism']]
        if not selected:
            raise ValueError('relaxation objective has no recorded mechanism')
        for frame in selected:
            total = total + term['coefficient'] * frame['outputs'][term['output']].sum()
    if not torch.isfinite(total):
        raise ValueError('nonfinite relaxation objective')
    return total


def fit_native_tensor_trace(trace, programs, *, trainable, terms, steps=20, learning_rate=0.1, temperature=1.0):
    """Short Adam fit on frozen native traces; all proposals need native rerun."""
    if type(steps) is not int or not 1 <= steps <= 200 or not 0 < learning_rate <= 1:
        raise ValueError('bounded positive fit settings required')
    replay_tensor_trace(trace, programs, hard=True, verify_recorded=True)
    parameters, leaves = {}, []
    for mechanism, program in programs.items():
        parameters[mechanism] = {}
        for key, value in program['parameters'].items():
            tensor = torch.tensor(value, dtype=torch.float64, requires_grad=key in trainable.get(mechanism, []))
            parameters[mechanism][key] = tensor
            if tensor.requires_grad:
                leaves.append(tensor)
        if set(trainable.get(mechanism, [])) - set(program['parameters']):
            raise ValueError('unknown trainable tensor parameter')
    if not leaves:
        raise ValueError('no trainable tensor parameter')
    optimizer = torch.optim.Adam(leaves, lr=learning_rate)
    history = []
    for step in range(steps + 1):
        optimizer.zero_grad()
        frames = replay_tensor_trace(trace, programs, parameters=parameters, temperature=temperature)
        loss = trace_objective(frames, terms)
        record = {'step': step, 'conditional_soft_loss': float(loss.detach()), 'parameters': {
            name: {k: v.detach().tolist() for k, v in values.items()} for name, values in parameters.items()}}
        if step < steps:
            loss.backward()
            if any(t.grad is None or not torch.isfinite(t.grad).all() for t in leaves):
                raise ValueError('missing/nonfinite represented gradient; no surrogate gradient fabricated')
            record['gradient_l2'] = float(torch.stack([t.grad.square().sum() for t in leaves]).sum().sqrt())
            optimizer.step()
        history.append(record)
    fitted = deepcopy(programs)
    for name, program in fitted.items():
        program['parameters'] = {k: v.detach().tolist() for k, v in parameters[name].items()}
    hard_frames = replay_tensor_trace(trace, programs, parameters=parameters, hard=True)
    return {'schema': 'scienceutopia.native-trace-relaxation.v1', 'programs': fitted,
        'trace_sha256': digest(trace), 'terms': deepcopy(terms), 'history': history,
        'conditional_hard_loss_after': float(trace_objective(hard_frames, terms)),
        'temperature': temperature, 'scope': 'frozen native observations; autograd through represented institutions, tensor edges and memory only',
        'full_native_world_autograd': False, 'requires_fresh_native_evaluation': True}
