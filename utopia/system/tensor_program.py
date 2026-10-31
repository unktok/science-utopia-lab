"""Composable hard/soft institution programs; no replacement world dynamics.

This is a bounded tensor dataflow IR, not generated Python evaluation. The
existing isolated Python/LLM routes remain unrestricted by this vocabulary.
Only explicitly represented operations are differentiable; arbitrary source,
native researcher transitions and token generation are not compiled magically.
"""
from __future__ import annotations

import math
import re
from typing import Mapping

import torch

from .design_patch import digest

SCHEMA = 'scienceutopia.tensor-program.v1'
IMPLEMENTATION = 'program.tensor.v1'
NAME = re.compile(r'^[a-z][a-z0-9_-]{0,63}$')
ARITY = {'add': 2, 'sub': 2, 'mul': 2, 'div': 2, 'matmul': 2,
         'neg': 1, 'tanh': 1, 'sigmoid': 1, 'relu': 1, 'sum': 1,
         'mean': 1, 'transpose': 1, 'reshape': 1, 'column': 1,
         'softmax': 1, 'choose': 1, 'gate': 1, 'branch': 3,
         'sort': 1, 'match': 1, 'concat': 2}
ATTRS = {'sum': {'dim', 'keepdim'}, 'mean': {'dim', 'keepdim'},
         'transpose': {'dims'}, 'reshape': {'shape'}, 'column': {'index'},
         'softmax': {'dim'}, 'choose': {'dim'}, 'concat': {'dim'},
         'match': {'iterations'}}


def _literal(value):
    if isinstance(value, list):
        return sum((_literal(v) for v in value), 0)
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('tensor literals must be finite numbers, not booleans')
    return 1


def validate_tensor_program(program):
    if not isinstance(program, dict) or set(program) != {'schema', 'inputs', 'parameters', 'state', 'nodes', 'outputs', 'updates'} or program['schema'] != SCHEMA:
        raise ValueError('invalid tensor program schema/fields')
    if len(__import__('json').dumps(program, allow_nan=False).encode()) > 262_144:
        raise ValueError('tensor program exceeds byte limit')
    refs = set()
    for group in ('inputs', 'parameters', 'state'):
        entries = program[group]
        if not isinstance(entries, dict) or len(entries) > 32:
            raise ValueError('tensor program group must be a bounded object')
        for name, value in entries.items():
            if not isinstance(name, str) or not NAME.fullmatch(name):
                raise ValueError('invalid tensor program identifier')
            refs.add(group.rstrip('s') + ':' + name if group != 'state' else 'state:' + name)
            if group == 'inputs':
                if not isinstance(value, list) or len(value) > 3 or any(type(d) is not int or d == 0 or d < -1 or d > 256 for d in value) or value.count(-1) > 1:
                    raise ValueError('input shape requires <=3 dimensions and at most one dynamic axis')
            elif _literal(value) > 16_384:
                raise ValueError('tensor initializer exceeds element limit')
    nodes = program['nodes']
    if not isinstance(nodes, list) or len(nodes) > 256:
        raise ValueError('tensor graph exceeds node limit')
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {'id', 'op', 'args', 'attrs'}:
            raise ValueError('tensor node fields differ')
        name, op, args, attrs = node['id'], node['op'], node['args'], node['attrs']
        if not isinstance(name, str) or not NAME.fullmatch(name) or name in refs:
            raise ValueError('invalid or duplicate tensor node identifier')
        if not isinstance(op, str) or op not in ARITY or not isinstance(args, list) or len(args) != ARITY[op] or any(not isinstance(r, str) or r not in refs for r in args):
            raise ValueError('invalid tensor operation or forward/unresolved reference')
        if not isinstance(attrs, dict) or not set(attrs) <= ATTRS.get(op, set()):
            raise ValueError('invalid tensor operation attributes')
        if 'dim' in attrs and (type(attrs['dim']) is not int or not -3 <= attrs['dim'] <= 2):
            raise ValueError('tensor dimension outside supported rank')
        if 'keepdim' in attrs and type(attrs['keepdim']) is not bool:
            raise ValueError('keepdim must be boolean')
        if 'index' in attrs and (type(attrs['index']) is not int or not 0 <= attrs['index'] < 256):
            raise ValueError('invalid column index')
        if 'iterations' in attrs and (type(attrs['iterations']) is not int or not 1 <= attrs['iterations'] <= 200):
            raise ValueError('invalid Sinkhorn iteration count')
        if op in ('column', 'reshape', 'transpose') and not attrs:
            raise ValueError('missing tensor operation attributes')
        if 'shape' in attrs and (not isinstance(attrs['shape'], list) or len(attrs['shape']) > 3 or any(type(d) is not int or d == 0 or d < -1 or d > 256 for d in attrs['shape']) or attrs['shape'].count(-1) > 1):
            raise ValueError('invalid reshape dimensions')
        if 'dims' in attrs and (not isinstance(attrs['dims'], list) or len(attrs['dims']) != 2 or any(type(d) is not int or not -3 <= d <= 2 for d in attrs['dims'])):
            raise ValueError('transpose needs two dimensions')
        refs.add(name)
    for group in ('outputs', 'updates'):
        if not isinstance(program[group], dict) or len(program[group]) > 32 or any(not isinstance(k, str) or not NAME.fullmatch(k) or not isinstance(v, str) or v not in refs for k, v in program[group].items()):
            raise ValueError('invalid tensor output/state reference')
    if set(program['updates']) != set(program['state']):
        raise ValueError('updates must cover exactly tensor memory slots')


def _bounded(value):
    if value.ndim > 3 or value.numel() > 16_384 or not torch.isfinite(value).all():
        raise ValueError('tensor result exceeds rank/element limit or is nonfinite')
    return value


def _sort(scores, *, hard, temperature):
    if scores.ndim != 1 or scores.numel() > 64:
        raise ValueError('sort expects a vector of at most 64 scores')
    n = len(scores)
    if hard:
        return torch.eye(n, dtype=scores.dtype, device=scores.device)[torch.argsort(scores, descending=True, stable=True)]
    # NeuralSort: rows are soft ranks, not independent ad-hoc sigmoid ranks.
    pair_distance = (scores[:, None] - scores[None, :]).abs().sum(-1)
    scaling = n + 1 - 2 * torch.arange(1, n + 1, dtype=scores.dtype, device=scores.device)
    return ((scaling[:, None] * scores[None, :] - pair_distance[None, :]) / temperature).softmax(-1)


def _match(scores, *, hard, temperature, iterations):
    if scores.ndim != 2 or scores.shape[0] != scores.shape[1] or scores.shape[0] > 64:
        raise ValueError('match expects a square score matrix of size <=64')
    if hard:
        from scipy.optimize import linear_sum_assignment
        row, col = linear_sum_assignment(scores.detach().cpu().numpy(), maximize=True)
        result = torch.zeros_like(scores)
        result[row, col] = 1
        return result
    value = scores / temperature
    for _ in range(iterations):
        value = value - value.logsumexp(-1, keepdim=True)
        value = value - value.logsumexp(-2, keepdim=True)
    return value.exp()


def execute_tensor_program(program, inputs: Mapping[str, torch.Tensor], *, parameters=None,
                           state=None, hard=False, temperature=1.0):
    """One program, hard operational interpretation or explicit soft relaxation.

    Does not normalize/tanh every output or impose institution-specific laws.
    Soft ties need not converge to deterministic hard tie-breaking. Matching
    requires a unique assignment for the usual zero-temperature limit.
    """
    validate_tensor_program(program)
    if type(hard) is not bool or not math.isfinite(temperature) or temperature <= 0:
        raise ValueError('invalid execution mode/temperature')
    if set(inputs) != set(program['inputs']):
        raise ValueError('tensor input names differ')
    anchor = next(iter(inputs.values()), torch.tensor(0., dtype=torch.float64))
    env = {}
    for name, shape in program['inputs'].items():
        value = _bounded(inputs[name])
        if value.ndim != len(shape) or any(d != -1 and d != actual for d, actual in zip(shape, value.shape)):
            raise ValueError('tensor input shape differs: ' + name)
        env['input:' + name] = value
    for group, supplied in (('parameters', parameters), ('state', state)):
        if supplied is not None and set(supplied) != set(program[group]):
            raise ValueError('tensor parameter/state names differ')
        for name, initial in program[group].items():
            reference = torch.as_tensor(initial, dtype=anchor.dtype, device=anchor.device)
            value = supplied[name] if supplied is not None else reference
            if value.shape != reference.shape:
                raise ValueError('tensor parameter/state shape changed')
            env[('parameter:' if group == 'parameters' else 'state:') + name] = _bounded(value)
    for node in program['nodes']:
        args, attrs, op = [env[k] for k in node['args']], node['attrs'], node['op']
        if op == 'add': value = args[0] + args[1]
        elif op == 'sub': value = args[0] - args[1]
        elif op == 'mul': value = args[0] * args[1]
        elif op == 'div': value = args[0] / args[1]
        elif op == 'matmul': value = args[0] @ args[1]
        elif op == 'neg': value = -args[0]
        elif op == 'tanh': value = args[0].tanh()
        elif op == 'sigmoid': value = args[0].sigmoid()
        elif op == 'relu': value = args[0].relu()
        elif op in ('sum', 'mean'): value = getattr(args[0], op)(**attrs)
        elif op == 'transpose': value = args[0].transpose(*attrs['dims'])
        elif op == 'reshape': value = args[0].reshape(attrs['shape'])
        elif op == 'column': value = args[0][:, attrs['index']]
        elif op == 'concat': value = torch.cat(args, dim=attrs.get('dim', -1))
        elif op == 'softmax': value = args[0].softmax(dim=attrs.get('dim', -1))
        elif op == 'gate': value = (args[0] >= 0).to(anchor.dtype) if hard else (args[0] / temperature).sigmoid()
        elif op == 'choose':
            dim = attrs.get('dim', -1)
            if args[0].shape[dim] == 0: raise ValueError('cannot choose from an empty address axis')
            value = (torch.zeros_like(args[0]).scatter(dim, args[0].argmax(dim=dim, keepdim=True), 1.)
                     if hard else (args[0] / temperature).softmax(dim=dim))
        elif op == 'branch': value = args[0] * args[1] + (1 - args[0]) * args[2]
        elif op == 'sort': value = _sort(args[0], hard=hard, temperature=temperature)
        elif op == 'match': value = _match(args[0], hard=hard, temperature=temperature, iterations=attrs.get('iterations', 40))
        else: raise AssertionError(op)
        env[node['id']] = _bounded(value)
    outputs = {name: env[ref] for name, ref in program['outputs'].items()}
    updates = {name: env[ref] for name, ref in program['updates'].items()}
    if any(updates[name].shape != env['state:' + name].shape for name in updates):
        raise ValueError('tensor state shape changed during update')
    return outputs, updates


def tensor_handler(context):
    """Generic native-graph adapter: incoming numeric protocol -> tensor ports.

    Python/LLM producers can define features/protocols; downstream consumers
    decide how tensors affect native actions. Saved trace marks this boundary.
    """
    from .runtime import MechanismEvent, MechanismResult, MechanismValue
    program = context.mechanism.parameters['program']
    bindings = context.mechanism.parameters['input_bindings']
    if set(bindings) != set(program['inputs']) or set(program['outputs']) != {p.port_id for p in context.mechanism.outputs}:
        raise ValueError('tensor program and graph bindings differ')
    inputs, records, actor_ids, artifact_ids, sources = {}, None, [], [], {}
    from .design_patch import read_pointer
    for name, binding in bindings.items():
        delivered = context.inputs[binding['port']]
        if len(delivered) != 1:
            raise ValueError('tensor input requires exactly one frame; aggregate explicitly upstream')
        item = delivered[0]
        value = torch.tensor(read_pointer(item.payload, binding['path']), dtype=torch.float64)
        shape = program['inputs'][name]
        if value.numel() == 0 and -1 in shape:
            value = value.reshape([0 if d == -1 else d for d in shape])
        inputs[name] = value
        sources[name] = {'mechanism': item.source_mechanism, 'port': item.source_port,
                         'period': item.emitted_period, 'path': binding['path']}
        incoming_records = item.payload.get('records', [])
        if records is not None and incoming_records != records:
            raise ValueError('tensor inputs need explicit record alignment')
        records = incoming_records
        actor_ids.extend(item.actor_ids)
        artifact_ids.extend(item.artifact_ids)
    saved = context.state.get('tensors', program['state'])
    state = {k: torch.tensor(v, dtype=torch.float64) for k, v in saved.items()}
    outputs, updates = execute_tensor_program(program, inputs, state=state, hard=True)
    def values(items): return {k: v.detach().tolist() for k, v in items.items()}
    trace = {'program_sha256': digest(program), 'mode': 'hard', 'inputs': values(inputs),
             'state_before': values(state), 'outputs': values(outputs), 'state_after': values(updates),
             'records': records or [], 'input_sources': sources,
             'boundary': 'only represented tensor operations carry gradients; native/code/LLM transitions are opaque'}
    result = {port: (MechanismValue({'values': value.detach().tolist(), 'records': records or []},
        actor_ids=tuple(dict.fromkeys(actor_ids)), artifact_ids=tuple(dict.fromkeys(artifact_ids))),) for port, value in outputs.items()}
    return MechanismResult(outputs=result, next_state={'tensors': values(updates)},
        events=(MechanismEvent('native.tensor.executed', payload=trace),))
