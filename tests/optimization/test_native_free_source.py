import json
from copy import deepcopy

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_code_trace import RecordingCodeExecutor, parent_context_provider
from utopia.optimization.native_design import NativeDesignCampaign
from utopia.optimization.native_free_source import NativeFreeSourceRevisionProposer, probe_source_trajectory
from utopia.system import SystemSpec
from utopia.system.code_mechanisms import DockerCodeExecutor, sha
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
from utopia.system.native_selection_slot import selection_source_slot


@pytest.fixture
def recorded_selection(tmp_path, fixed_corpus):
    executor = DockerCodeExecutor()
    spec = selection_source_slot(legacy_world_system(), image_id=executor.image_id)
    controller = NativeDesignCampaign(tmp_path / 'campaign', initial_system=spec,
        loss_spec=loss_spec(), seeds=[42], world_binding={'mode': 'scripted-QA-only'})
    def factory(system, run_seed, run_id):
        seed()
        recorder = RecordingCodeExecutor(executor, tmp_path / 'runs' / run_id / 'code-contexts.jsonl',
            binding={'source_commit': 'QA', 'system_fingerprint': system.fingerprint, 'run_id': run_id})
        return make_sim(tmp_path / 'runs' / run_id, native=NativeScienceKernel(system, code_executor=recorder))[0]
    controller.advance(simulation_factory=factory)
    provider = parent_context_provider(tmp_path / 'runs', source_commit='QA')
    return controller, factory, executor, provider


class Model:
    def __init__(self, source):
        self.source, self.prompts = source, []
    def generate(self, **kwargs):
        self.prompts.append(kwargs['prompt'])
        return {'design_reasoning': 'Explicit scripted QA source, not discovery', 'algorithm_name': 'QA source', 'python_code': self.source}, []


def test_actual_selection_ports_probed_and_native_evaluated_without_messages(recorded_selection, tmp_path):
    controller, factory, executor, provider = recorded_selection
    source = next(n for n in controller.initial.mechanisms if n.mechanism_id == 'world.selection').parameters['code_artifact']['source']
    model = Model(source.replace("index < slots", "True"))
    proposer = NativeFreeSourceRevisionProposer(model, executor, node_id='world.selection', context_provider=provider, receipts=tmp_path / 'proposals')
    result = controller.advance(simulation_factory=factory, proposer=proposer)
    assert result['observation']['status'] == 'complete'
    assert 'incumbent_output_ports' in model.prompts[0] and 'submitted_papers' in model.prompts[0]
    assert len(model.prompts[0].encode()) <= 80000 and model.prompts[0].endswith('do not invent native measurements.')
    receipt = json.loads((tmp_path / 'proposals/free-source-1-0.json').read_text())
    assert {'next', 'world', 'decisions'} == set(receipt['probe_results'][0]['result']['outputs'])
    assert any(r['result_changed'] for r in receipt['probe_results'])


def test_same_source_legal_resume_and_loss_binding(recorded_selection, tmp_path):
    controller, _, executor, provider = recorded_selection
    source = next(n for n in controller.initial.mechanisms if n.mechanism_id == 'world.selection').parameters['code_artifact']['source']
    model = Model(source)
    proposer = NativeFreeSourceRevisionProposer(model, executor, node_id='world.selection', context_provider=provider, receipts=tmp_path / 'proposals')
    args = controller.initial, controller.state['records'], 1, loss_spec()
    patch = proposer(*args)
    assert proposer(*args) == patch and len(model.prompts) == 1
    receipt = json.loads((tmp_path / 'proposals/free-source-1-0.json').read_text())
    assert receipt['source_same_as_parent'] is True
    changed = json.loads(json.dumps(loss_spec()))
    changed['version'] = 'different'
    with pytest.raises(ValueError, match='binding/hash changed'):
        proposer(*args[:3], changed)


def test_tampered_actual_context_rejected_before_generation(recorded_selection, tmp_path):
    controller, _, executor, provider = recorded_selection
    rows = provider('world.selection', controller.initial, controller.state['records'])
    rows[0]['context']['period'] += 1
    model = Model('def step(context): pass')
    proposer = NativeFreeSourceRevisionProposer(model, executor, node_id='world.selection',
        context_provider=lambda *a: rows, receipts=tmp_path / 'proposals')
    with pytest.raises(ValueError, match='bundle hash'):
        proposer(controller.initial, controller.state['records'], 1, loss_spec())
    assert not model.prompts


def test_de_novo_mode_really_withholds_parent_source_but_does_not_veto_equal_code(recorded_selection, tmp_path):
    controller, _, executor, provider = recorded_selection
    source = next(n for n in controller.initial.mechanisms if n.mechanism_id == 'world.selection').parameters['code_artifact']['source']
    model = Model(source)
    proposer = NativeFreeSourceRevisionProposer(model, executor, node_id='world.selection', context_provider=provider,
        receipts=tmp_path / 'de-novo', show_parent_source=False)
    proposer(controller.initial, controller.state['records'], 1, loss_spec())
    assert source not in model.prompts[0] and 'implementation withheld' in model.prompts[0]
    receipt = json.loads((tmp_path / 'de-novo/free-source-1-0.json').read_text())
    assert receipt['status'] == 'isolated-probes-passed-not-native-evaluated'
    assert receipt['ast_same_as_parent'] is True
    prompt = json.loads((tmp_path / 'de-novo/free-source-prompt-1-0.json').read_text())
    assert prompt['prompt_sha256'] == receipt['prompt_sha256']


def test_source_probe_carries_candidate_memory_through_all_years_not_prompt_sample(recorded_selection, tmp_path):
    controller, factory, executor, provider = recorded_selection
    node = next(n for n in controller.initial.mechanisms if n.mechanism_id == 'world.selection')
    source = node.parameters['code_artifact']['source'].replace("context['state'].get('cycles', 0) + 1", "context['state'].get('cycles', 0) + 10")
    model = Model(source)
    proposer = NativeFreeSourceRevisionProposer(model, executor, node_id='world.selection',
        context_provider=provider, receipts=tmp_path / 'stateful', max_probe_contexts=2)
    result = controller.advance(simulation_factory=factory, proposer=proposer)
    assert result['observation']['status'] == 'complete'
    receipt = json.loads((tmp_path / 'stateful/free-source-1-0.json').read_text())
    assert len(receipt['binding']['selected_bundle_sha256s']) == 2  # prompt samples only
    assert len(receipt['probe_results']) == 6  # all six exact annual inputs
    assert [r['result']['state']['cycles'] for r in receipt['probe_results']] == [10, 20, 30, 40, 50, 60]
    assert [r['context']['state'].get('cycles', 0) for r in receipt['probe_results']] == [0, 10, 20, 30, 40, 50]
    child = SystemSpec.from_dict(result['suggestion']['candidate'])
    actual = provider('world.selection', child, controller.state['records'])
    assert [r['context']['state'].get('cycles', 0) for r in actual] == [0, 10, 20, 30, 40, 50]
    assert all(r['result']['state'] == q['result']['state'] for r, q in zip(actual, receipt['probe_results']))


def test_source_probe_rejects_missing_early_year_even_if_late_parent_memory_exists(recorded_selection):
    controller, _, executor, provider = recorded_selection
    node = next(n for n in controller.initial.mechanisms if n.mechanism_id == 'world.selection')
    rows = provider('world.selection', controller.initial, controller.state['records'])
    assert rows[1]['context']['state']  # old behavior silently adopted this memory
    with pytest.raises(ValueError, match='contiguous source trajectory'):
        probe_source_trajectory(controller.initial, node, node.parameters['code_artifact'], rows[1:], executor=executor)


def test_source_repair_prompt_is_stable_after_sorted_json_disk_reload(recorded_selection, tmp_path):
    controller, _, executor, provider = recorded_selection
    source = next(n for n in controller.initial.mechanisms if n.mechanism_id == 'world.selection').parameters['code_artifact']['source']
    class Repair(Model):
        def generate(self, **kwargs):
            self.source = 'def step(context):\n    return None' if not self.prompts else source
            return super().generate(**kwargs)
    model = Repair(source)
    proposer = NativeFreeSourceRevisionProposer(model, executor, node_id='world.selection',
        context_provider=provider, receipts=tmp_path / 'repair')
    args = controller.initial, controller.state['records'], 1, loss_spec()
    patch = proposer(*args)
    assert len(model.prompts) == 2
    assert proposer(*args) == patch
    assert len(model.prompts) == 2


def test_source_replay_timing_only_duplicate_preserves_first_receipt(recorded_selection):
    controller, _, executor, provider = recorded_selection
    node = next(n for n in controller.initial.mechanisms if n.mechanism_id == 'world.selection')
    rows = provider('world.selection', controller.initial, controller.state['records'])
    duplicate = deepcopy(rows[0])
    duplicate['receipt']['wall_seconds'] += 1
    duplicate['bundle_sha256'] = sha({k: v for k, v in duplicate.items() if k != 'bundle_sha256'})
    results = probe_source_trajectory(controller.initial, node, node.parameters['code_artifact'], rows + [duplicate], executor=executor)
    assert len(results) == 6 and results[0]['native_bundle_sha256'] == rows[0]['bundle_sha256']
