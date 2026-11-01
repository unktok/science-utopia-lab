"""Wrapped-program migration units and original six-year cold-restart QA."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest
from jsonschema import ValidationError

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from utopia.runtime.checkpointing import PortableStop
from utopia.system import (ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily,
    MechanismSpec, PortSpec, ScheduleSpec, SystemSpec)
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system, _hash, add_context_receiver
from utopia.system.native_migration import (migrate_native_design, native_execution_nodes,
    checkpoint_native_bootstrap, commit_native_design, _validate_programs)
from utopia.system.native_process import controlled_activity, register_native_process, CONTROL
from utopia.system.runtime import (DeterministicGraphRunner, GraphRuntimeError, MechanismEvent,
    MechanismResult, MechanismValue)

A, B = 'sha256:' + 'a'*64, 'sha256:' + 'b'*64
SOURCE = """def step(context):
    n = context['state'].get('n', 0) + 1
    return {'outputs': {'result': [{'payload': {'value': n}}]}, 'state': {'n': n}}
"""


class NoExecution:
    """Graph/image-resolution unit stub; NOT native/source-execution evidence."""
    def __init__(self, image): self.image_id = image
    def execute(self, *args): pytest.fail('migration validation must not execute source')


def wrapper(image=A):
    node = MechanismSpec('worker', MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('data', ChannelKind.ARTIFACT, 'datum'),),
        outputs=(PortSpec('result', ChannelKind.ARTIFACT, 'datum'),),
        parameters={'runtime_image_id': image, 'code_artifact': {'schema': 'scienceutopia.code-mechanism.v1',
            'label': 'migration-unit-only', 'source': SOURCE,
            'inputs': {'data': {'type': 'object', 'required': ['value'], 'properties': {'value': {'type': 'number'}}}},
            'outputs': {'result': {'type': 'object'}},
            'state_schema': {'type': 'object', 'required': ['n'], 'properties': {'n': {'type': 'integer'}}}}})
    return controlled_activity(node, count=0, initial_state={'n': 0})


def register(kernel, registry):
    registry.register('test.process-producer.v1', 1, lambda context: MechanismResult(
        outputs={'data': (MechanismValue({'value': 1}),)}, events=(MechanismEvent('test.actual_message'),)))
    if ('native.process.activity.v1', 1) not in registry.registered:
        register_native_process(kernel, registry)


def graph_kernel():
    """Real graph queue fixture, no scientific-world claim; delegate count=0."""
    producer = MechanismSpec('producer', MechanismFamily.CUSTOM, 'test.process-producer.v1',
        outputs=(PortSpec('data', ChannelKind.ARTIFACT, 'datum'),))
    spec = SystemSpec('process-migration-unit', 1,
        artifact_types=(ArtifactTypeSpec('datum'), ArtifactTypeSpec(CONTROL)),
        mechanisms=(producer, wrapper()), schedules=(ScheduleSpec('producer', 0), ScheduleSpec('worker', 1)),
        connections=(ConnectionSpec('producer', 'data', 'worker', 'data', ChannelKind.ARTIFACT, latency=2),))
    kernel = NativeScienceKernel(spec, registry_extension=register, code_executor=NoExecution(A))
    result = DeterministicGraphRunner(spec, kernel._registry()).run(periods=1, start_period=1)
    kernel.graph_checkpoint, kernel.events, kernel.last_year = result.checkpoint.to_dict(), list(result.events), 1
    return kernel


def edited(kernel, edit):
    document = kernel.spec.to_dict()
    edit(document['mechanisms'][1])
    return SystemSpec.from_dict(document)


def test_wrapped_only_image_change_rebuilds_before_adoption_and_cold_bootstrap(monkeypatch):
    kernel = graph_kernel()
    before = kernel.to_dict()
    built = []
    def executor(image):
        built.append(image)
        return NoExecution(image)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor', executor)
    candidate = edited(kernel, lambda n: n['parameters']['delegate']['parameters'].update(runtime_image_id=B))
    assert not any(n.implementation == 'code.python.v1' for n in candidate.mechanisms)
    assert [n.implementation for n in native_execution_nodes(candidate)] == ['test.process-producer.v1', 'code.python.v1']
    assert _validate_programs(candidate) == B
    migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(before), state_actions={'worker': 'preserve'})
    assert built == [B] and kernel.code_executor.image_id == B
    assert kernel.graph_checkpoint['queued_deliveries'] == before['graph_checkpoint']['queued_deliveries']
    configured = NativeScienceKernel(SystemSpec.from_dict(before['spec']), registry_extension=register, code_executor=NoExecution(A))
    reopened = checkpoint_native_bootstrap(configured, kernel.to_dict())
    assert reopened.code_executor is None  # Old executor is not silently retained.
    reopened._registry()
    assert reopened.code_executor.image_id == B and built == [B, B]
    assert reopened.to_dict() == kernel.to_dict()


@pytest.mark.parametrize('change,exception', [
    (lambda n: n['parameters']['delegate']['parameters']['code_artifact'].update(source='invalid python !!'), SyntaxError),
    (lambda n: n['parameters']['delegate']['parameters'].update(runtime_image_id='python:latest'), GraphRuntimeError),
    (lambda n: n['parameters']['delegate']['parameters']['code_artifact']['state_schema'].update({'$ref': 'https://invalid'}), ValueError),
    (lambda n: n['parameters']['delegate']['parameters']['code_artifact']['inputs'].update(other={'type': 'object'}), GraphRuntimeError),
    (lambda n: n['parameters']['delegate']['inputs'][0].update(artifact_type=CONTROL), GraphRuntimeError),
    (lambda n: n['parameters']['delegate'].update(unrecognized='not silently ignored'), GraphRuntimeError),
])
def test_invalid_wrapped_source_image_contract_rejects_atomically(change, exception):
    kernel = graph_kernel()
    before = kernel.to_dict()
    candidate = edited(kernel, change)
    with pytest.raises(exception):
        migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(before), state_actions={'worker': 'preserve'})
    assert kernel.to_dict() == before


@pytest.mark.parametrize('bad', [{'delegate_state': {'n': 'invalid'}}, {'delegate_state': []},
                               {'delegate_state': {'n': 0}, 'total_invocations': -1}])
def test_nested_delegate_memory_rejects_before_receipt_or_state_mutation(bad):
    kernel = graph_kernel()
    before = kernel.to_dict()
    with pytest.raises((GraphRuntimeError, ValidationError)):
        migrate_native_design(kernel, kernel.spec, expected_checkpoint_sha256=_hash(before),
            state_actions={'worker': {'replace': bad}})
    assert kernel.to_dict() == before


def test_queued_delegate_schema_change_requires_explicit_discard_and_reopens():
    kernel = graph_kernel()
    before = kernel.to_dict()
    def narrow(node):
        node['parameters']['delegate']['parameters']['code_artifact']['inputs']['data']['properties']['value'] = {'type': 'string'}
    candidate = edited(kernel, narrow)
    with pytest.raises(ValidationError):
        migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(before), state_actions={'worker': 'preserve'})
    assert kernel.to_dict() == before
    order = str(kernel.graph_checkpoint['queued_deliveries'][0]['order'])
    receipt = migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(before),
        state_actions={'worker': 'preserve'}, discard_deliveries={order: 'explicitly retire incompatible old datum'})
    assert receipt['source_graph']['queued_deliveries'] and not receipt['target_graph']['queued_deliveries']
    reopened = NativeScienceKernel(candidate, checkpoint=kernel.to_dict(), registry_extension=register, code_executor=NoExecution(A))
    assert reopened.to_dict() == kernel.to_dict()
    forged = deepcopy(kernel.to_dict())
    forged['design_history'][0]['target_graph']['mechanism_states']['worker']['delegate_state']['n'] = 'tampered'
    with pytest.raises(GraphRuntimeError):
        NativeScienceKernel(candidate, checkpoint=forged)


def test_cold_bootstrap_rejects_current_delegate_state_and_pending_payload_tamper():
    kernel = graph_kernel()
    founding = kernel.spec
    before = kernel.to_dict()
    candidate = replace(founding, metadata={'explicit-revision': 1})
    migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(before))
    configured = NativeScienceKernel(founding, registry_extension=register, code_executor=NoExecution(A))
    bad_memory = deepcopy(kernel.to_dict())
    bad_memory['graph_checkpoint']['mechanism_states']['worker']['delegate_state']['n'] = 'bad'
    with pytest.raises(ValidationError): checkpoint_native_bootstrap(configured, bad_memory)
    bad_queue = deepcopy(kernel.to_dict())
    bad_queue['graph_checkpoint']['queued_deliveries'][0]['value']['payload']['value'] = 'bad'
    with pytest.raises(ValidationError): checkpoint_native_bootstrap(configured, bad_queue)


def tensor_wrapper():
    program = {'schema': 'scienceutopia.tensor-program.v1', 'inputs': {'x': [1]}, 'parameters': {},
        'state': {'memory': [0.]}, 'nodes': [], 'outputs': {'result': 'input:x'}, 'updates': {'memory': 'state:memory'}}
    node = MechanismSpec('worker', MechanismFamily.CUSTOM, 'program.tensor.v1',
        inputs=(PortSpec('data', ChannelKind.ARTIFACT, 'datum'),), outputs=(PortSpec('result', ChannelKind.ARTIFACT, 'datum'),),
        parameters={'program': program, 'input_bindings': {'x': {'port': 'data', 'path': '/value'}}})
    return controlled_activity(node, count=0)


def test_wrapped_tensor_program_memory_and_queued_shapes_are_validated():
    kernel = graph_kernel()
    document = kernel.spec.to_dict()
    document['mechanisms'][1] = SystemSpec('dummy', 1, mechanisms=(tensor_wrapper(),)).to_dict()['mechanisms'][0]
    candidate = SystemSpec.from_dict(document)
    before = kernel.to_dict()
    with pytest.raises(GraphRuntimeError, match='tensor input shape'):
        migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(before), state_actions={'worker': 'reset'})
    bad = deepcopy(document)
    bad['mechanisms'][1]['parameters']['delegate']['parameters']['program']['nodes'] = [
        {'id': 'bad', 'op': 'not-an-op', 'args': [], 'attrs': {}}]
    with pytest.raises(ValueError, match='tensor operation'):
        migrate_native_design(kernel, SystemSpec.from_dict(bad), expected_checkpoint_sha256=_hash(before), state_actions={'worker': 'reset'})
    order = str(before['graph_checkpoint']['queued_deliveries'][0]['order'])
    with pytest.raises(GraphRuntimeError, match='memory shape'):
        migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(before),
            state_actions={'worker': {'replace': {'delegate_state': {'tensors': {'memory': [1., 2.]}}}}},
            discard_deliveries={order: 'unit test explicit discard'})
    assert kernel.to_dict() == before


def test_wrapped_llm_first_empty_memory_is_legal_but_explicit_bad_memory_is_rejected():
    kernel = graph_kernel()
    before = kernel.to_dict()
    def llm(node):
        node['parameters']['delegate']['implementation'] = 'native.world.llm-institution.v1'
        node['parameters']['delegate']['parameters'] = {'instruction': 'Caller-authored institution; no invocation in this unit.',
            'output_schemas': {'result': {'type': 'object'}},
            'state_schema': {'type': 'object', 'required': ['n'], 'properties': {'n': {'type': 'integer'}}}}
        node['parameters']['initial_delegate_state'] = {}
    candidate = edited(kernel, llm)
    with pytest.raises(ValidationError):
        migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(before),
            state_actions={'worker': {'replace': {'delegate_state': {'n': 'invalid'}}}})
    assert kernel.to_dict() == before
    migrate_native_design(kernel, candidate, expected_checkpoint_sha256=_hash(before), state_actions={'worker': 'reset'})
    assert kernel.graph_checkpoint['mechanism_states']['worker'] == {}


@pytest.mark.parametrize('implementation', ['code.python.v1', 'native.world.llm-institution.v1'])
def test_empty_first_call_exception_cannot_erase_required_memory_after_execution(implementation):
    from utopia.system.native_migration import _validate_saved_state
    node=next(n for n in graph_kernel().spec.mechanisms if n.mechanism_id=='worker')
    if implementation != 'code.python.v1':
        data=node.parameters.copy()
        delegate=deepcopy(data['delegate'])
        delegate['implementation']=implementation
        delegate['parameters']={'instruction':'test','output_schemas':{'result':{'type':'object'}},
            'state_schema':{'type':'object','required':['n'],'properties':{'n':{'type':'integer'}}}}
        data['delegate']=delegate
        node=replace(node,parameters=data)
    with pytest.raises(ValidationError):
        _validate_saved_state(node,{'total_invocations':1,'delegate_state':{}})


ADVISORY = """def step(context):
    observation = context['inputs']['world'][0]['payload']
    ids = [a['id'] for a in observation['ecosystem']['agents'] if a['can_author']]
    n = context['state'].get('n', 0) + 1
    return {'outputs': {'message': [{'payload': {'text': 'WRAPPED_ONLY_MIGRATION_' + str(n)}, 'actor_ids': ids}]}, 'state': {'n': n}}
"""


def wrapped_society(parent, image):
    node = MechanismSpec('wrapped-advisor', MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('world', ChannelKind.ARTIFACT, 'native-world-observation'),),
        outputs=(PortSpec('message', ChannelKind.ARTIFACT, 'advisory'),),
        parameters={'runtime_image_id': image, 'code_artifact': {'schema': 'scienceutopia.code-mechanism.v1',
            'label': 'Real native wrapped-only migration software QA', 'source': ADVISORY,
            'inputs': {'world': {'type': 'object'}}, 'outputs': {'message': {'type': 'object'}},
            'state_schema': {'type': 'object', 'required': ['n'], 'properties': {'n': {'type': 'integer'}}}}})
    wrapped = controlled_activity(node, count=2, initial_state={'n': 0})
    spec = replace(parent, mechanisms=(*parent.mechanisms, wrapped),
        artifact_types=(*parent.artifact_types, ArtifactTypeSpec('advisory'), ArtifactTypeSpec(CONTROL)),
        schedules=(*parent.schedules, ScheduleSpec(wrapped.mechanism_id, 230)),
        connections=(*parent.connections, ConnectionSpec('world.funding', 'world', wrapped.mechanism_id, 'world', ChannelKind.ARTIFACT)))
    return add_context_receiver(spec, source=wrapped.mechanism_id, source_port='message')


def test_actual_wrapped_only_code_adoption_and_original_six_year_cold_restart(tmp_path, fixed_corpus):
    from utopia.system.code_mechanisms import DockerCodeExecutor, CodeExecutionError
    try:
        executor = DockerCodeExecutor()
    except (CodeExecutionError, OSError):
        pytest.skip('local isolated runtime required for native scientific QA')
    founding = legacy_world_system()
    def extension(kernel, registry):
        if ('native.process.activity.v1', 1) not in registry.registered:
            register_native_process(kernel, registry)
    sim, _ = make_sim(tmp_path / 'society', native=NativeScienceKernel(founding, registry_extension=extension))
    original_callback = sim.checkpoint_callback
    adopted = []
    def boundary(path):
        original_callback(path)
        if sim.native_system.last_year == 1:
            candidate = wrapped_society(sim.native_system.spec, executor.image_id)
            assert not any(n.implementation == 'code.python.v1' for n in candidate.mechanisms)
            result = commit_native_design(sim, candidate, expected_checkpoint_sha256=_hash(sim.native_system.to_dict()),
                state_actions={'wrapped-advisor': 'reset'})
            adopted.append(result)
            assert sim.native_system.code_executor.image_id == executor.image_id
            raise PortableStop('cold shutdown after wrapped-only code adoption')
    sim.checkpoint_callback = boundary
    try:
        with pytest.raises(PortableStop): sim.run()
    finally:
        sim.llm.response_cache.close()
    assert len(adopted) == 1
    seed()
    resumed, calls = make_sim(tmp_path / 'society', native=NativeScienceKernel(founding, registry_extension=extension))
    try:
        resumed.run()
        assert resumed.native_system.last_year == 6
        saved = resumed.native_system.graph_checkpoint['mechanism_states']['wrapped-advisor']
        assert saved['total_invocations'] == 10 and saved['delegate_state']['n'] == 10
        assert any('WRAPPED_ONLY_MIGRATION_' in json.dumps(payload) for _, payload in calls)
        assert len(resumed.native_system.design_history) == 1
        assert _validate_programs(resumed.native_system.spec) == executor.image_id
    finally:
        resumed.llm.response_cache.close()
