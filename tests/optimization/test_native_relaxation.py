from copy import deepcopy
from dataclasses import replace

import pytest
import torch

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed, science_snapshot
from tests.system.test_native_science_kernel import make_sim
from utopia.optimization.native_relaxation import native_tensor_trace, replay_tensor_trace, fit_native_tensor_trace
from utopia.optimization.native_world import measure_native_world
from utopia.runtime.checkpointing import PortableStop
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
from utopia.system.native_tensor_examples import tensor_selection_system
from utopia.system.code_mechanisms import DockerCodeExecutor, CodeExecutionError
from utopia.system import MechanismSpec, MechanismFamily, PortSpec, ChannelKind, ScheduleSpec, ConnectionSpec
from utopia.system.tensor_program import IMPLEMENTATION, SCHEMA


def executor():
    try: return DockerCodeExecutor()
    except (OSError, CodeExecutionError): pytest.skip('local isolated code runtime required')


def test_native_tensor_program_relaxes_actual_decisions_and_returns_executable_candidate(tmp_path, fixed_corpus):
    image = executor().image_id
    system = tensor_selection_system(legacy_world_system(), image_id=image)
    sim, _ = make_sim(tmp_path / 'native', native=NativeScienceKernel(system))
    sim.run()
    trace = native_tensor_trace(sim.native_system.events)
    assert len(trace) == 6
    node = next(n for n in system.mechanisms if n.mechanism_id == 'addressed-selection')
    programs = {node.mechanism_id: node.parameters['program']}
    hard = replay_tensor_trace(trace, programs, hard=True, verify_recorded=True)
    counts = measure_native_world(sim, run_id='actual-native')
    accepted = counts['metrics']['native.accepted_decisions']['value']
    assert sum(float(f['outputs']['accept'].sum()) for f in hard) == accepted
    fit = fit_native_tensor_trace(trace, programs, trainable={node.mechanism_id: ['bias']},
        terms=[{'mechanism': node.mechanism_id, 'output': 'accept', 'coefficient': -1.}], steps=30, learning_rate=0.15)
    assert fit['history'][-1]['conditional_soft_loss'] < fit['history'][0]['conditional_soft_loss']
    assert fit['full_native_world_autograd'] is False and fit['requires_fresh_native_evaluation']
    new = replace(node, parameters={**node.parameters, 'program': fit['programs'][node.mechanism_id]})
    candidate = replace(system, mechanisms=tuple(new if n.mechanism_id == node.mechanism_id else n for n in system.mechanisms))
    seed()
    changed, _ = make_sim(tmp_path / 'candidate', native=NativeScienceKernel(candidate))
    changed.run()
    assert measure_native_world(changed, run_id='counterfactual')['metrics']['native.accepted_decisions']['value'] > accepted
    altered = deepcopy(trace)
    altered[-1]['outputs']['accept'][0] = 999.
    with pytest.raises(ValueError, match='hard replay differs'):
        replay_tensor_trace(altered, programs, hard=True, verify_recorded=True)
    sim.llm.response_cache.close()
    changed.llm.response_cache.close()


def test_native_tensor_memory_and_receipts_survive_completed_year_resume(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    system = tensor_selection_system(legacy_world_system(), image_id=executor().image_id)
    reference, _ = make_sim(tmp_path / 'reference', native=NativeScienceKernel(system))
    reference.run()
    expected = science_snapshot(reference)
    seed()
    stopped, _ = make_sim(tmp_path / 'resume', native=NativeScienceKernel(system), after_effects=True)
    with pytest.raises(PortableStop): stopped.run()
    stopped.llm.response_cache.close()
    resumed, _ = make_sim(tmp_path / 'resume', native=NativeScienceKernel(system))
    resumed.run()
    assert science_snapshot(resumed) == expected
    assert resumed.native_system.to_dict() == reference.native_system.to_dict()
    resumed.llm.response_cache.close()
    reference.llm.response_cache.close()


def test_autograd_crosses_two_real_native_institution_nodes_not_only_local_surrogate(tmp_path, fixed_corpus):
    system = tensor_selection_system(legacy_world_system(), image_id=executor().image_id)
    protocol = 'native-tensor-decision-frame'
    program = {'schema': SCHEMA, 'inputs': {'incoming': [-1]}, 'parameters': {'threshold': 0.5}, 'state': {},
        'nodes': [{'id': 'margin', 'op': 'sub', 'args': ['input:incoming', 'parameter:threshold'], 'attrs': {}},
                  {'id': 'action', 'op': 'gate', 'args': ['margin'], 'attrs': {}}],
        'outputs': {'actions': 'action'}, 'updates': {}}
    node = MechanismSpec('collective-router', MechanismFamily.CUSTOM, IMPLEMENTATION,
        inputs=(PortSpec('signal', ChannelKind.ARTIFACT, protocol),),
        outputs=(PortSpec('actions', ChannelKind.ARTIFACT, protocol),),
        parameters={'program': program, 'input_bindings': {'incoming': {'port': 'signal', 'path': '/values'}}})
    system = replace(system, mechanisms=(*system.mechanisms, node), schedules=(*system.schedules, ScheduleSpec(node.mechanism_id, 135)),
        connections=(*(c for c in system.connections if not (c.target_mechanism == 'world.selection' and c.target_port == 'accept')),
            ConnectionSpec('addressed-selection', 'accept', node.mechanism_id, 'signal', ChannelKind.ARTIFACT),
            ConnectionSpec(node.mechanism_id, 'actions', 'world.selection', 'accept', ChannelKind.ARTIFACT)))
    sim, _ = make_sim(tmp_path / 'collective', native=NativeScienceKernel(system))
    sim.run()
    trace = native_tensor_trace(sim.native_system.events)
    programs = {n.mechanism_id: n.parameters['program'] for n in system.mechanisms if n.implementation == IMPLEMENTATION}
    replay_tensor_trace(trace, programs, hard=True, verify_recorded=True)
    parameters = {name: {k: torch.tensor(v, dtype=torch.float64, requires_grad=True) for k, v in p['parameters'].items()} for name, p in programs.items()}
    frames = replay_tensor_trace(trace, programs, parameters=parameters)
    output = sum(f['outputs']['actions'].sum() for f in frames if f['mechanism'] == node.mechanism_id)
    first, second = torch.autograd.grad(output, (parameters['addressed-selection']['bias'], parameters[node.mechanism_id]['threshold']))
    assert abs(first) > 0 and abs(second) > 0
    sim.llm.response_cache.close()
