"""Zero-code original-world evidence QA; no actual Qwen inference."""
import shutil

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus


def test_lawful_removal_of_all_code_nodes_needs_no_fabricated_code_journal(
        tmp_path, fixed_corpus, monkeypatch):
    from tests.runtime.test_portable_checkpoint_integration import BINDING, seed
    from tests.system.test_native_science_kernel import make_sim
    from tests.optimization.test_native_adaptive_search import loss_spec
    from scripts.native_physical_evidence_v13 import audit_native_run_v13, FIXTURE
    from utopia.optimization.blackbox import Suggestion
    from utopia.optimization.native_factory import record_native_http
    from utopia.optimization.native_world import evaluate_native_suggestion
    from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
    from utopia.utils.data_utils import write_json_atomic
    spec = legacy_world_system()
    monkeypatch.setitem(BINDING, 'cell', spec.fingerprint)
    monkeypatch.setitem(BINDING, 'science_config', {**BINDING['science_config'],
        'years': 2, 'source_commit': 'scripted-v13-no-code'})
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    suggestion = Suggestion('scripted-no-code', spec.to_dict(), 0, 'unit-only')
    def factory(candidate, world_seed, run_id):
        cell = tmp_path/'worlds'/run_id
        seed()
        sim, calls = make_sim(cell, native=NativeScienceKernel(candidate))
        sim.num_years = 2
        sim.enable_portable_checkpoints(BINDING)
        record_native_http(sim.llm, sim, cell/'wire-requests.jsonl')
        write_json_atomic(cell/'system.json', spec.to_dict())
        return sim
    observation = evaluate_native_suggestion(suggestion, seeds=[42], simulation_factory=factory,
        loss_spec=loss_spec()).to_dict()
    assert observation['status'] == 'complete'
    run = observation['metadata']['runs'][0]
    cell = tmp_path/'worlds'/run['run_id']
    (cell/'replies').mkdir()
    shutil.copyfile(cell/'cache/responses.sqlite', cell/'replies/responses.sqlite')
    assert not (cell/'code-contexts.jsonl').exists()
    proof = audit_native_run_v13(tmp_path, {'suggestion': suggestion.to_dict()}, observation, run,
        {'source_commit': 'scripted-v13-no-code', 'model_digest': BINDING['model_revision'],
            'corpus_sha256': BINDING['corpus_sha256']}, FIXTURE, expected_loss=loss_spec())
    assert proof['native_loss'] == observation['loss']
    assert proof['code_proof']['recorded_executions'] == 0
