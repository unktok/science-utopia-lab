"""First world-originated design proposal -> separately evaluated next world."""
from copy import deepcopy
from dataclasses import replace

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_design import NativeDesignCampaign, propose_from_native_world
from utopia.system import ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from utopia.system.code_mechanisms import DockerCodeExecutor, CodeExecutionError
from utopia.system.design_patch import apply_design_patch
from utopia.system.native_design_examples import deliberation_patch
from utopia.system.native_kernel import DESIGN_PROPOSALS, NativeScienceKernel, legacy_world_system


def reflective_system(image_id):
    original = legacy_world_system()
    system = apply_design_patch(original, deliberation_patch(original, image_id=image_id, threshold=5.))
    consumer = next(n for n in system.mechanisms if n.mechanism_id == 'world.selection')
    parameters = deepcopy(consumer.parameters)
    artifact = parameters['code_artifact']
    artifact['outputs']['design-proposals'] = {'type': 'object'}
    # This source runs INSIDE the native institution, not in the outer proposer.
    artifact['source'] = artifact['source'].replace('    if not decisions:', """    proposals = []
    world = deliberation['world']
    if any(d['payload']['decision'] == 'reject' for d in decisions) and context['parameters']['threshold'] > 1:
        index = next(i for i,n in enumerate(world['system_spec']['mechanisms']) if n['mechanism_id'] == 'world.selection')
        proposals = [{'payload': {'schema': 'scienceutopia.system-design-patch.v1',
            'parent_fingerprint': world['system_fingerprint'],
            'operations': [{'op': 'replace', 'path': '/mechanisms/%s/parameters/threshold' % index,
                            'value': context['parameters']['threshold'] - 1.0}],
            'rationale': 'Observed rejections motivate a prospective revision of my own selection rule'}}]
    if not decisions:""").replace("'decisions': decisions}", "'decisions': decisions, 'design-proposals': proposals}")
    consumer = replace(consumer, outputs=(*consumer.outputs, PortSpec('design-proposals', ChannelKind.ARTIFACT, 'system-design-proposal', required=False)),
                       parameters=parameters)
    sink = MechanismSpec('design-proposal-journal', MechanismFamily.CUSTOM, DESIGN_PROPOSALS,
        inputs=(PortSpec('proposals', ChannelKind.ARTIFACT, 'system-design-proposal', required=False),))
    return replace(system, metadata={**system.metadata, 'expose_system_spec': True},
        artifact_types=(*system.artifact_types, ArtifactTypeSpec('system-design-proposal')),
        mechanisms=(*(consumer if n.mechanism_id == consumer.mechanism_id else n for n in system.mechanisms), sink),
        connections=(*system.connections, ConnectionSpec(consumer.mechanism_id, 'design-proposals', sink.mechanism_id, 'proposals', ChannelKind.ARTIFACT)),
        schedules=(*system.schedules, ScheduleSpec(sink.mechanism_id, 195)))


def test_native_institution_proposes_its_own_rule_then_outer_loop_evaluates_revision(tmp_path, fixed_corpus):
    try:
        executor = DockerCodeExecutor()
    except (OSError, CodeExecutionError):
        pytest.skip('isolated local source execution required')
    system = reflective_system(executor.image_id)
    controller = NativeDesignCampaign(tmp_path / 'campaign', initial_system=system, loss_spec=loss_spec(),
        seeds=[42], world_binding={'mode': 'native-domain-phases-with-scripted-HTTP-and-corpus'})
    def factory(spec, run_seed, run_id):
        seed()
        return make_sim(tmp_path / 'runs' / run_id, native=NativeScienceKernel(spec))[0]
    first = controller.advance(simulation_factory=factory)
    assert first['observation']['status'] == 'complete'
    assert first['observation']['loss'] == 0
    altered = deepcopy(controller.state['records'])
    altered[0]['observation']['metadata']['runs'][0]['checkpoint_sha256'] = 'changed'
    with pytest.raises(ValueError, match='checkpoint hash'):
        propose_from_native_world(system, altered, 1, loss_spec())
    second = controller.advance(simulation_factory=factory, proposer=propose_from_native_world)
    assert second['observation']['status'] == 'complete', second['observation']['metadata']['technical_failures']
    assert second['observation']['loss'] == -24
    assert second['patch']['operations'][0]['value'] == 4.
    assert second['suggestion']['based_on_observation_id'] == first['observation']['observation_id']
    index = next(i for i,n in enumerate(system.mechanisms) if n.mechanism_id == 'world.selection')
    assert system.mechanisms[index].parameters['threshold'] == 5.  # no hot mutation


def test_invalid_world_proposal_is_recorded_not_installed_or_scored():
    from types import SimpleNamespace
    from utopia.system.runtime import DeliveredValue
    system = legacy_world_system()
    kernel = NativeScienceKernel(system)
    value = DeliveredValue(ChannelKind.ARTIFACT, 'system-design-proposal',
        {'schema': 'scienceutopia.system-design-patch.v1', 'parent_fingerprint': 'stale',
         'operations': [], 'rationale': 'invalid idea'}, (), (), (), 'institution', 'proposal', 1, 1)
    result = kernel._record_design_proposals(SimpleNamespace(state={}, inputs={'proposals': (value,)}, period=1))
    proposal = result.next_state['proposals'][0]
    assert proposal['status'] == 'technically_invalid'
    assert proposal['loss'] is None
    assert result.events[0].event_type == 'native.system.design_proposed'
    assert kernel.spec.fingerprint == system.fingerprint
