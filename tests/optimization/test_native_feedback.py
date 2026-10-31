import json

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_design import NativeDesignCampaign
from utopia.optimization.native_feedback import NativeSourceRevisionProposer, feedback_from_native_history
from utopia.system import MechanismSpec, MechanismFamily, PortSpec, ChannelKind
from utopia.system.code_mechanisms import CODE_SCHEMA, CODE_IMPLEMENTATION, DockerCodeExecutor
from utopia.system.native_examples import connect_native_institution
from utopia.system.native_kernel import NativeScienceKernel, WORLD_ARTIFACT, legacy_world_system

INERT = "def step(context):\n return {'outputs':{'messages':[]},'state':{}}\n"
ACTIVE = """def step(context):
    world = context['inputs']['observations'][0]['payload']
    messages = [{'payload': {'observed_resources': a['resources'], 'observed_year': world['year']},
                 'actor_ids': [a['id']], 'artifact_ids': []}
                for a in world['ecosystem']['agents'] if a.get('can_author')]
    return {'outputs': {'messages': messages}, 'state': {'cycles': context['state'].get('cycles', 0) + 1}}
"""


@pytest.fixture
def native_case(tmp_path, fixed_corpus):
    executor = DockerCodeExecutor()
    artifact = {'schema': CODE_SCHEMA, 'label': 'Inert QA institution', 'source': INERT,
                'inputs': {'observations': {'type': 'object'}}, 'outputs': {'messages': {'type': 'object'}}, 'state_schema': {'type': 'object'}}
    node = MechanismSpec('qa-observer', MechanismFamily.CUSTOM, CODE_IMPLEMENTATION,
        inputs=(PortSpec('observations', ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
        outputs=(PortSpec('messages', ChannelKind.ARTIFACT, 'qa-message', required=False),),
        parameters={'code_artifact': artifact, 'runtime_image_id': executor.image_id})
    spec = connect_native_institution(legacy_world_system(), node, phase=191, researcher_output='messages')
    controller = NativeDesignCampaign(tmp_path / 'campaign', initial_system=spec, loss_spec=loss_spec(),
        seeds=[42], world_binding={'mode': 'native-phase-scripted-transport-QA'})
    def factory(system, run_seed, run_id):
        seed()
        return make_sim(tmp_path / 'runs' / run_id, native=NativeScienceKernel(system))[0]
    controller.advance(simulation_factory=factory)
    return controller, factory, executor


class Model:
    def __init__(self, sources):
        self.sources, self.prompts = list(sources), []
    def generate(self, **kwargs):
        self.prompts.append(kwargs['prompt'])
        return {'label': 'QA model revision', 'source': self.sources.pop(0), 'rationale': 'Revise from actual feedback'}, []


def test_actual_activity_feedback_then_source_revision_changes_native_inputs(native_case, tmp_path):
    controller, factory, executor = native_case
    feedback = feedback_from_native_history(controller.state['records'])
    assert feedback['observations'][0]['executions'][0]['delivered_messages'] == []
    model = Model([ACTIVE])
    proposer = NativeSourceRevisionProposer(model, executor, node_id='qa-observer', receipts=tmp_path / 'proposals')
    second = controller.advance(simulation_factory=factory, proposer=proposer)
    assert second['observation']['status'] == 'complete'
    assert second['suggestion']['based_on_observation_id'] == controller.state['records'][0]['observation']['observation_id']
    assert 'delivered_messages' in model.prompts[0]
    updated = feedback_from_native_history(controller.state['records'])
    assert len(updated['observations'][1]['executions'][0]['delivered_messages']) > 0
    assert updated['observations'][1]['changed_implementations'][0]['artifact']['source'] == ACTIVE


def test_inert_source_still_valid_and_receipt_resume_does_not_reroll(native_case, tmp_path):
    controller, _, executor = native_case
    model = Model([INERT])
    proposer = NativeSourceRevisionProposer(model, executor, node_id='qa-observer', receipts=tmp_path / 'proposals')
    args = (controller.initial, controller.state['records'], 1, loss_spec())
    patch = proposer(*args)
    assert proposer(*args) == patch
    assert len(model.prompts) == 1
    receipt = json.loads((tmp_path / 'proposals/source-revision-1-0.json').read_text())
    assert receipt['probe_message_count'] == 0 and receipt['loss'] is None


def test_actual_syntax_error_is_repaired_without_scoring(native_case, tmp_path):
    controller, _, executor = native_case
    model = Model(['def step(', ACTIVE])
    proposer = NativeSourceRevisionProposer(model, executor, node_id='qa-observer', receipts=tmp_path / 'proposals')
    proposer(controller.initial, controller.state['records'], 1, loss_spec())
    assert 'ACTUAL TECHNICAL ERROR' in model.prompts[1]
    assert json.loads((tmp_path / 'proposals/source-revision-1-0.json').read_text())['status'] == 'invalid'


def test_checkpoint_tampering_cannot_supply_feedback(native_case):
    controller, _, _ = native_case
    history = json.loads(json.dumps(controller.state['records']))
    history[0]['observation']['metadata']['runs'][0]['checkpoint_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checkpoint hash'):
        feedback_from_native_history(history)
