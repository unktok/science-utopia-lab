"""Six-year original-native/real-Docker QA; scripted responsive HTTP, not Qwen findings."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest
import torch

from tests.optimization.test_native_world import loss_spec
from tests.runtime.test_portable_checkpoint_integration import BINDING, FakeHTTPModel, fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from utopia.optimization.native_code_trace import RecordingCodeExecutor
from utopia.optimization.native_hybrid import (
    boundary_coverage, conditional_backward, continuous_coordinates, hybrid_gradient,
    endpoint_input_drift, load_hybrid_report, native_directional_fidelity, native_endpoint, project_continuous, save_hybrid_report,
)
from utopia.optimization.native_relaxation import native_tensor_trace, replay_tensor_trace, trace_objective
from utopia.runtime.checkpointing import PortableStop, read_portable_checkpoint
from utopia.system import ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from utopia.system.code_mechanisms import CodeExecutionError, DockerCodeExecutor
from utopia.system.design_patch import digest
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
from utopia.system.native_tensor_examples import tensor_selection_system
from utopia.system.tensor_program import IMPLEMENTATION, SCHEMA


def recurrent_system(image):
    system = tensor_selection_system(legacy_world_system(), image_id=image)
    nodes = []
    for node in system.mechanisms:
        if node.mechanism_id == 'native-feature-extractor':
            params = deepcopy(node.parameters)
            params['score_offset'] = 0.
            params['code_artifact']['source'] = params['code_artifact']['source'].replace(
                'values.append([score, len(reviews)])', "values.append([score + context['parameters']['score_offset'], len(reviews)])")
            node = replace(node, parameters=params)
        nodes.append(node)
    def op(name, operation, *args, **attrs):
        return {'id': name, 'op': operation, 'args': list(args), 'attrs': attrs}
    program = {'schema': SCHEMA, 'inputs': {'incoming': [-1]},
        'parameters': {'threshold': .5, 'memory_gain': .01, 'write_logits': [2., -1.],
            'query': [1.], 'keys': [[1.], [0.]]}, 'state': {'slots': [[0.], [0.]]},
        'nodes': [op('address', 'choose', 'parameter:write_logits'),
            op('remembered', 'attention', 'parameter:query', 'parameter:keys', 'state:slots'),
            op('penalty', 'mul', 'remembered', 'parameter:memory_gain'),
            op('unbiased', 'sub', 'input:incoming', 'parameter:threshold'),
            op('margin', 'sub', 'unbiased', 'penalty'), op('actions', 'gate', 'margin'),
            op('count', 'sum', 'input:incoming'), op('vector', 'reshape', 'count', shape=[1]),
            op('next-memory', 'memory_write', 'state:slots', 'address', 'vector')],
        'outputs': {'actions': 'actions'}, 'updates': {'slots': 'next-memory'}}
    protocol = 'native-tensor-decision-frame'
    router = MechanismSpec('recurrent-router', MechanismFamily.CUSTOM, IMPLEMENTATION,
        inputs=(PortSpec('signal', ChannelKind.ARTIFACT, protocol),),
        outputs=(PortSpec('actions', ChannelKind.ARTIFACT, protocol),),
        parameters={'program': program, 'input_bindings': {'incoming': {'port': 'signal', 'path': '/values'}}})
    return replace(system, mechanisms=(*nodes, router), schedules=(*system.schedules, ScheduleSpec(router.mechanism_id, 135)),
        connections=(*(c for c in system.connections if not (c.target_mechanism == 'world.selection' and c.target_port == 'accept')),
            ConnectionSpec('addressed-selection', 'accept', router.mechanism_id, 'signal', ChannelKind.ARTIFACT),
            ConnectionSpec(router.mechanism_id, 'actions', 'world.selection', 'accept', ChannelKind.ARTIFACT)))


DECLARATIONS = [
    {'id': 'bias', 'mechanism': 'addressed-selection', 'path': '/program/parameters/bias', 'lower': -2., 'upper': 2., 'quantum': None},
    {'id': 'router', 'mechanism': 'recurrent-router', 'path': '/program/parameters/threshold', 'lower': .05, 'upper': .95, 'quantum': None},
    {'id': 'source-offset', 'mechanism': 'native-feature-extractor', 'path': '/score_offset', 'lower': -.5, 'upper': .5, 'quantum': None},
]
TERMS = [{'mechanism': 'recurrent-router', 'output': 'actions', 'coefficient': -1.}]


class ResponsiveHTTP(FakeHTTPModel):
    """New answers depend on actual evolving society, not replayed text."""
    def reply(self, **payload):
        response = super().reply(**payload)
        if self.context[0][0] == 'phase1_directions':
            accepted = sum(d['decision'] == 'accept' for p in self.sim.paper_tracker.papers_by_id.values() for d in p.review_history)
            resources = sum(a.resources for a in self.sim.ecosystem.agent_population.values() if a.can_author)
            value = json.loads(response.choices[0].message.content)
            value['detailed_focus'] = f'Responsive QA: actual past accepts={accepted}; current resources={resources}'
            response.choices[0].message.content = json.dumps(value)
        return response


def docker():
    try:
        # Explicit QA-only wall budget for concurrent local Docker workloads;
        # production defaults/sandbox/experiment budgets remain unchanged.
        return DockerCodeExecutor(timeout=60.)
    except (OSError, CodeExecutionError):
        pytest.skip('real isolated local code runtime required')


def test_projection_binds_actual_continuous_tensor_and_python_parameters():
    system = recurrent_system('sha256:' + 'a'*64)
    coordinates = continuous_coordinates(system, DECLARATIONS)
    assert [c['derivative_route'] for c in coordinates] == [
        'represented-conditional-autograd', 'represented-conditional-autograd', 'opaque-source-parameter-native-perturbation']
    candidate, projection = project_continuous(system, DECLARATIONS, {'bias': -10., 'router': .4, 'source-offset': .25})
    assert projection['coordinates'][0]['projected'] == -2.
    assert projection['coordinates'][0]['projection_derivative'] == 'clamped-zero'
    assert next(n for n in candidate.mechanisms if n.mechanism_id == 'native-feature-extractor').parameters['score_offset'] == .25
    bad = deepcopy(DECLARATIONS)
    bad[2]['path'] = '/code_artifact/source'
    with pytest.raises(ValueError, match='not source'):
        continuous_coordinates(system, bad)
    quantized = deepcopy(DECLARATIONS)
    quantized[0]['quantum'] = .5
    _, receipt = project_continuous(system, quantized, {'bias': .6, 'router': .5, 'source-offset': 0.})
    assert receipt['coordinates'][0]['projected'] == .5
    assert receipt['coordinates'][0]['projection_derivative'] == 'not-pathwise-quantized'


def test_unrepresented_original_world_still_has_an_honest_boundary_coverage_report():
    coverage = boundary_coverage(legacy_world_system(), [])
    assert not coverage['represented_mechanisms'] and not coverage['verified_represented_mechanisms']
    assert not coverage['full_native_world_autograd']
    assert coverage['edges'] and all(e['derivative_coverage'] == 'opaque-numeric-or-nonnumeric-protocol' for e in coverage['edges'])


def test_original_native_records_recurrent_backward_projection_fresh_reactions_fidelity_and_reload(
        tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    executor = docker()
    system = recurrent_system(executor.image_id)
    world = {'source_commit': 'v7-responsive-scripted-native-QA-not-live', 'model_digest': BINDING['model_revision'],
        'corpus_sha256': BINDING['corpus_sha256'], 'seed': 42, 'classification': 'scripted-fixture-not-native-results'}
    calls, endpoints = {}, []

    def run(name, candidate):
        monkeypatch.setitem(BINDING, 'cell', candidate.fingerprint)
        monkeypatch.setitem(BINDING, 'science_config', {**BINDING['science_config'], 'source_commit': world['source_commit']})
        seed()
        root = tmp_path / name
        recording = RecordingCodeExecutor(executor, root / 'code-contexts.jsonl', binding={
            'source_commit': world['source_commit'], 'system_fingerprint': candidate.fingerprint, 'run_id': name})
        sim, actual_calls = make_sim(root, native=NativeScienceKernel(candidate, code_executor=recording), model_class=ResponsiveHTTP)
        try:
            sim.run()
            assert actual_calls and sim.llm.reused == 0  # Fresh responsive replies, not cached base-world outputs.
            checkpoint = root / 'checkpoints/portable_checkpoint_year_6.json.gz'
            endpoint = native_endpoint(checkpoint, candidate, DECLARATIONS, loss_spec(), world=world,
                code_contexts=root / 'code-contexts.jsonl')
            calls[name] = deepcopy(actual_calls)
            endpoints.append(endpoint)
            return endpoint, list(sim.native_system.events)
        finally:
            sim.llm.response_cache.close()

    base, events = run('base', system)
    programs = {n.mechanism_id: n.parameters['program'] for n in system.mechanisms if n.implementation == IMPLEMENTATION}
    trace = native_tensor_trace(events)
    assert len(trace) == 12  # Two actually executed represented institutions for six original years.
    hard = replay_tensor_trace(trace, programs, hard=True, verify_recorded=True)
    assert float(trace_objective(hard, TERMS)) == base['native_loss']
    coverage = boundary_coverage(system, events)
    assert coverage['represented_numeric_edge_count'] == 1
    assert any(e['derivative_coverage'] == 'conditioned-numeric-input-opaque-upstream' for e in coverage['edges'])
    assert any(e['derivative_coverage'] == 'opaque-consumer-or-native-effect' for e in coverage['edges'])
    backward = conditional_backward(trace, programs, trainable={
        'addressed-selection': ['bias'], 'recurrent-router': ['threshold']}, terms=TERMS)
    assert backward['status'] == 'passed'
    assert all(check['absolute_max_error'] < 1e-5 for check in backward['numerical_checks'])
    assert all(abs(backward['gradient'][name][parameter]) > 0 for name, parameter in (
        ('addressed-selection', 'bias'), ('recurrent-router', 'threshold')))

    tensor_plus, _ = project_continuous(system, DECLARATIONS, {'bias': .75, 'router': .5, 'source-offset': 0.})
    plus, _ = run('tensor-plus', tensor_plus)
    source_plus, _ = project_continuous(system, DECLARATIONS, {'bias': .5, 'router': .5, 'source-offset': .25})
    source, _ = run('source-plus', source_plus)
    hybrid = hybrid_gradient(system, DECLARATIONS, backward, opaque_endpoints={'source-offset': (base, source)})
    assert hybrid['components'][2]['method'] == 'measured-native-partial-secant-not-pathwise'
    wrong = deepcopy(backward)
    wrong['program_sha256s']['recurrent-router'] = 'wrong-program'
    with pytest.raises(ValueError, match='different represented institution'):
        hybrid_gradient(system, DECLARATIONS, wrong, opaque_endpoints={'source-offset': (base, source)})
    wrong = deepcopy(backward)
    wrong['trace_sha256'] = 'wrong-baseline-trace'
    with pytest.raises(ValueError, match='different actual base'):
        hybrid_gradient(system, DECLARATIONS, wrong, opaque_endpoints={'source-offset': (base, source)})
    fidelity = native_directional_fidelity(base, plus, hybrid['gradient'])
    assert fidelity['status'] == 'failed-local-native-fidelity'  # Correct soft autograd is NOT an exact native derivative.
    assert not fidelity['full_native_world_autograd']
    candidate_values = {c['id']: c['value']-.01*hybrid['gradient'][c['id']] for c in continuous_coordinates(system, DECLARATIONS)}
    candidate, projection = project_continuous(system, DECLARATIONS, candidate_values)
    final, _ = run('hybrid-candidate', candidate)
    assert final['native_loss'] < base['native_loss']
    assert calls['base'] != calls['hybrid-candidate']
    drift = endpoint_input_drift(base, final)
    assert drift['conditioning_changed']  # Actual downstream researchers/records are allowed to react.
    assert all(e['opaque_parameter_executions'] for e in endpoints)
    # New recurrent operations survive a real original-native interrupted year
    # and cold replay, rather than only serializing a detached optimizer tensor.
    from types import SimpleNamespace
    from tests.runtime.test_portable_checkpoint_integration import science_snapshot
    monkeypatch.setitem(BINDING, 'cell', system.fingerprint)
    resume_root = tmp_path / 'resume'
    def reopen(interrupt):
        seed()
        recording = RecordingCodeExecutor(executor, resume_root / 'code-contexts.jsonl', binding={
            'source_commit': world['source_commit'], 'system_fingerprint': system.fingerprint, 'run_id': 'resume'})
        return make_sim(resume_root, native=NativeScienceKernel(system, code_executor=recording),
            model_class=ResponsiveHTTP, after_effects=interrupt)[0]
    interrupted = reopen(True)
    try:
        with pytest.raises(PortableStop):
            interrupted.run()
    finally:
        interrupted.llm.response_cache.close()
    resumed = reopen(False)
    try:
        resumed.run()
        assert resumed.llm.reused > 0
        assert science_snapshot(resumed) == science_snapshot(SimpleNamespace(output_dir=tmp_path / 'base/checkpoints'))
        assert resumed.native_system.to_dict()['event_stream_hash'] == base['native_event_stream_hash']
    finally:
        resumed.llm.response_cache.close()
    report = {'classification': 'scripted-fixture-not-native-results', 'declarations': DECLARATIONS,
        'loss_spec': loss_spec(), 'coverage': coverage, 'conditional_backward': backward,
        'hybrid_gradient': hybrid, 'projection': projection, 'native_directional_fidelity': fidelity,
        'endpoint_input_drift': drift, 'endpoints': endpoints}
    path = tmp_path / 'hybrid-report.json'
    save_hybrid_report(path, report)
    assert load_hybrid_report(path) == report  # Recomputes endpoint facts, no model/container calls.
    forged_backward = json.loads(path.read_text())
    forged_backward['report']['conditional_backward']['gradient']['addressed-selection']['bias'] += 1.
    forged_backward['receipt_sha256'] = digest({k: v for k, v in forged_backward.items() if k != 'receipt_sha256'})
    changed_gradient = tmp_path / 'tampered-gradient-report.json'
    changed_gradient.write_text(json.dumps(forged_backward))
    with pytest.raises(ValueError, match='conditional backward/gradient evidence changed'):
        load_hybrid_report(changed_gradient)
    altered = deepcopy(trace)
    altered[3]['inputs']['incoming'][0] += .1
    with pytest.raises(ValueError, match='hard replay differs: inputs'):
        replay_tensor_trace(altered, programs, hard=True, verify_recorded=True)
    altered = deepcopy(trace)
    altered[3]['state_before']['slots'][0][0] += 1.
    with pytest.raises(ValueError, match='hard replay differs: state_before'):
        replay_tensor_trace(altered, programs, hard=True, verify_recorded=True)
    receipt = json.loads(path.read_text())
    receipt['report']['endpoints'][0]['native_loss'] += 1.
    receipt['receipt_sha256'] = digest({k: v for k, v in receipt.items() if k != 'receipt_sha256'})
    tampered = tmp_path / 'tampered-hybrid-report.json'
    tampered.write_text(json.dumps(receipt))  # Deliberate disposable QA corruption, never actual raw evidence.
    with pytest.raises(ValueError, match='semantic facts changed'):
        load_hybrid_report(tampered)
