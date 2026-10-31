import json

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_design import NativeDesignCampaign, LLMNativeDesignProposer
from utopia.runtime.checkpointing import PortableStop
from utopia.system.design_patch import make_patch
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system


def campaign(path):
    return NativeDesignCampaign(path, initial_system=legacy_world_system(), loss_spec=loss_spec(),
        seeds=[42], world_binding={'mode': 'real-native-phases-scripted-HTTP-and-corpus-QA'})


def factory(root):
    def create(system, run_seed, run_id):
        seed()
        return make_sim(root / run_id, native=NativeScienceKernel(system))[0]
    return create


def test_native_closed_loop_uses_actual_loss_and_result_conditioned_graph_edit(tmp_path, fixed_corpus):
    controller = campaign(tmp_path / 'campaign')
    first = controller.advance(simulation_factory=factory(tmp_path / 'runs'))
    assert first['observation']['status'] == 'complete'
    def propose(parent, history, index, declared_loss):
        assert index == 1 and history[0]['observation']['loss'] < 0
        assert declared_loss == loss_spec()
        # Remove an optional native lifecycle stage AND its incident control
        # edges, replacing the route. Real research/selection/funding remain.
        document = parent.to_dict()
        nodes = [n for n in document['mechanisms'] if n['mechanism_id'] != 'world.communication']
        edges = [e for e in document['connections'] if 'world.communication' not in (e['source_mechanism'], e['target_mechanism'])]
        edges.append({'source_mechanism': 'world.funding', 'source_port': 'next', 'target_mechanism': 'world.close',
                      'target_port': 'after', 'channel': 'signal', 'latency': 0})
        return make_patch(parent, [
            {'op': 'replace', 'path': '/mechanisms', 'value': nodes},
            {'op': 'replace', 'path': '/connections', 'value': edges},
            {'op': 'replace', 'path': '/schedules', 'value': [s for s in document['schedules'] if s['mechanism_id'] != 'world.communication']},
        ])
    second = controller.advance(simulation_factory=factory(tmp_path / 'runs'), proposer=propose)
    assert second['observation']['status'] == 'complete'
    assert second['difference']['nodes_removed'] == ['world.communication']
    assert second['suggestion']['based_on_observation_id'] == first['observation']['observation_id']
    assert campaign(tmp_path / 'campaign').state == controller.state


def test_interrupted_pending_proposal_resumes_without_regeneration(tmp_path, fixed_corpus):
    controller = campaign(tmp_path / 'campaign')
    def interrupted(*args):
        raise PortableStop('explicit interruption')
    with pytest.raises(PortableStop):
        controller.advance(simulation_factory=interrupted)
    pending = controller.state['pending']
    resumed = campaign(tmp_path / 'campaign')
    record = resumed.advance(simulation_factory=factory(tmp_path / 'runs'),
                             proposer=lambda *a: pytest.fail('must reuse pending'))
    assert record['suggestion'] == pending['suggestion']
    state_before = resumed.path.read_bytes()
    assert campaign(tmp_path / 'campaign').path.read_bytes() == state_before


def test_model_proposes_code_wiring_and_rules_with_actual_validation_repairs(tmp_path):
    parent = legacy_world_system()
    patches = [{'wrong': 1}, make_patch(parent, [{'op': 'add', 'path': '/mechanisms/0/parameters/new-rule', 'value': {'free': True}}])]
    class Model:
        def generate(self, **kwargs):
            if len(patches) == 1:
                assert 'ACTUAL VALIDATION ERROR' in kwargs['prompt']
            return patches.pop(0), []
    proposer = LLMNativeDesignProposer(Model(), instructions='Test explicit protocol editing.', receipts=tmp_path)
    result = proposer(parent, [], 1, loss_spec())
    assert result['operations'][0]['value'] == {'free': True}
    assert json.loads((tmp_path / 'proposal-1-0.json').read_text())['loss'] is None


def test_changed_objective_or_world_cannot_resume_same_campaign(tmp_path):
    campaign(tmp_path)
    with pytest.raises(ValueError, match='binding'):
        NativeDesignCampaign(tmp_path, initial_system=legacy_world_system(), loss_spec=loss_spec(coefficient=1.),
            seeds=[42], world_binding={'mode': 'real-native-phases-scripted-HTTP-and-corpus-QA'})


def test_joint_code_protocol_and_wiring_edit_executes_in_native_world(tmp_path, fixed_corpus):
    from utopia.system.code_mechanisms import DockerCodeExecutor, CodeExecutionError
    from utopia.system.native_design_examples import deliberation_patch
    try:
        executor = DockerCodeExecutor()
    except (OSError, CodeExecutionError):
        pytest.skip('local isolated Python runtime required')
    controller = campaign(tmp_path / 'campaign')
    first = controller.advance(simulation_factory=factory(tmp_path / 'runs'))
    def proposer(parent, history, index, objective):
        assert history[0]['observation']['loss'] == first['observation']['loss']
        return deliberation_patch(parent, image_id=executor.image_id, threshold=3.)
    second = controller.advance(simulation_factory=factory(tmp_path / 'runs'), proposer=proposer)
    assert second['observation']['status'] == 'complete'
    assert second['observation']['loss'] < first['observation']['loss']
    assert second['difference']['nodes_added'] == ['deliberation-assembly']
    assert second['difference']['nodes_changed'] == ['world.selection']
    assert campaign(tmp_path / 'campaign').state == controller.state


def test_saved_loss_tamper_is_rejected(tmp_path, fixed_corpus):
    controller = campaign(tmp_path / 'campaign')
    controller.advance(simulation_factory=factory(tmp_path / 'runs'))
    changed = json.loads(controller.path.read_text())
    changed['records'][0]['observation']['loss'] -= 10
    # Test input tampering only; source files are not edited this way.
    from utopia.utils.data_utils import write_json_atomic
    write_json_atomic(controller.path, changed)
    with pytest.raises(ValueError, match='measurements'):
        campaign(tmp_path / 'campaign')
