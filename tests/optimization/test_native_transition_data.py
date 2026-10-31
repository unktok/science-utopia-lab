from copy import deepcopy
import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed, BINDING
from tests.system.test_native_science_kernel import make_sim
from tests.optimization.test_native_world import loss_spec
from utopia.models.response_cache import CompletedResponseCache
from utopia.optimization.native_code_trace import RecordingCodeExecutor
from utopia.optimization.native_design import NativeDesignCampaign
from utopia.optimization.native_transition_data import extract_trajectory, compile_terminal_loss, STATE_NAMES
from utopia.system.code_mechanisms import DockerCodeExecutor
from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
from utopia.system.native_selection_slot import selection_source_slot


def test_actual_native_checkpoints_controls_and_tensor_loss_are_independently_bound(tmp_path, fixed_corpus):
    executor = DockerCodeExecutor()
    rates = [.2, .8, .2]
    spec = selection_source_slot(legacy_world_system(), image_id=executor.image_id, annual_rates=rates)
    campaign = NativeDesignCampaign(tmp_path / 'campaign', initial_system=spec, loss_spec=loss_spec(),
        seeds=[42], world_binding={'mode': 'native-world-scripted-HTTP-QA-not-experiment'})
    def factory(system, run_seed, run_id):
        seed()
        root = tmp_path / 'runs' / run_id
        recorder = RecordingCodeExecutor(executor, root / 'code-contexts.jsonl', binding={
            'source_commit': 'QA-source', 'system_fingerprint': system.fingerprint, 'run_id': run_id})
        sim, _ = make_sim(root, native=NativeScienceKernel(system, code_executor=recorder))
        sim.num_years = 3
        binding = deepcopy(BINDING)
        binding['cell'] = system.fingerprint
        binding['science_config']['source_commit'] = 'QA-source'
        sim.llm.response_cache.close()
        sim.llm.response_cache = CompletedResponseCache(root / 'bound-replies.sqlite', binding=binding)
        sim.enable_portable_checkpoints(binding)
        return sim
    record = campaign.advance(simulation_factory=factory)
    assert record['observation']['status'] == 'complete'
    kwargs = dict(run_directory=tmp_path / 'runs', source_commit='QA-source',
        model_digest=BINDING['model_revision'], corpus_sha256=BINDING['corpus_sha256'], controls=rates, loss_spec=loss_spec())
    trajectory, evidence = extract_trajectory(record, **kwargs)
    assert len(trajectory.states) == len(trajectory.checkpoint_sha256) == 4
    assert trajectory.binding.state_names == STATE_NAMES
    assert evidence['actual_control_executions'][1]['actual_rate'] == .8
    assert all(len(x) == 64 for x in trajectory.checkpoint_sha256)
    trajectory.validate(trajectory.binding, compile_terminal_loss(loss_spec()))
    with pytest.raises(ValueError, match='installed native annual rates'):
        extract_trajectory(record, **{**kwargs, 'controls': [.5] * 3})
    with pytest.raises(ValueError, match='source/model/corpus/system'):
        extract_trajectory(record, **{**kwargs, 'model_digest': 'different-model'})
