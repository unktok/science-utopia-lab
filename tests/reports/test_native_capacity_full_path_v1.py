"""Original five-founder factory and cold primitive with SCRIPTED HTTP/corpus.

No real-Qwen condition effect, optimizer or scientific improvement is tested.
"""
import json
from pathlib import Path

import pytest

from tests.optimization.test_native_factory import install_transport, capacity_conditions
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, FakeHTTPModel
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_active_founders import measure, measure_from_checkpoints, METRIC
from utopia.optimization.native_world import measure_native_world
from utopia.system.native_kernel import legacy_world_system
from utopia.system.native_capacity_controls import capacity_allocation_control
from utopia.system.native_resource_transfers import EVENT
from utopia.utils.data_utils import file_sha256


@pytest.mark.parametrize('papers', [1, 2])
@pytest.mark.parametrize('allocation', [None, 'reserve-proximity', 'completion-priority'])
def test_actual_capacity_factory_four_years_measurement_and_original_cold_proof(
        tmp_path, fixed_corpus, monkeypatch, papers, allocation):
    install_transport(monkeypatch); calls = []
    class Provider(FakeHTTPModel):
        def batch_completions(self, executor, requests, *, seed_ctx, attempt):
            # Actual Ollama requests retain top-level seed throughout the
            # production cache/audit. Only this scripted provider's context
            # lookup adapts the older vLLM-only fixture convention.
            for idx, payload in requests:
                self.contexts[payload['seed']] = (seed_ctx, idx, attempt)
            return super(FakeHTTPModel, self).batch_completions(
                executor, requests, seed_ctx=seed_ctx, attempt=attempt)

        def reply(self, **payload):
            fixture_payload = dict(payload, extra_body={'seed': payload['seed']})
            result = super().reply(**fixture_payload)
            if self.context[0][0] == 'phase2_submissions' and papers == 2:
                # The scripted provider emits a legal partial list, not host
                # repair of an actual model reply or forced use of the cap.
                content = json.loads(result.choices[0].message.content)
                result.choices[0].message.content = json.dumps({'submissions': [content]})
            return result
    def model(name, **kwargs):
        value = Provider(tmp_path/'scripted-provider', calls)
        value.response_cache.close()  # factory installs its actual bound cache
        value.model_name = name; value.model_revision = kwargs['model_revision']
        value.run_seed = kwargs['run_seed']; value.max_tokens_override = kwargs['max_tokens_override']
        value.thinking_override = False; value.enable_thinking = False; value.server_backend = 'ollama'
        return value
    monkeypatch.setattr('utopia.models.models.VLLMServerModel', model)
    conditions = capacity_conditions(papers_per_project=papers)
    experiment = {'protocol': 'SCRIPTED-capacity-full-native-path'}
    factory = LocalQwenNativeFactory(tmp_path/'runs', tmp_path/'cache', years=4, corpus_years=4,
        record_wire=True, record_code=True, maximum_http_attempts=1024, inference_lock=tmp_path/'inference.lock',
        allow_dirty=True, world_conditions=conditions, experiment_binding=experiment)
    spec = legacy_world_system(seed=42)
    if allocation is not None:
        spec = capacity_allocation_control(spec,
            'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833', rule=allocation)
    sim = factory(spec, 42, 'scripted-capacity-forward')
    sim.llm.sim = sim
    try:
        sim.run()
        base = measure_native_world(sim, run_id='scripted-capacity-forward')
        measured = measure(sim, base)
        assert 0 <= measured['metrics'][METRIC]['value'] <= 20
        assert len(measured['active_founder_boundary_instrument']['initial_founder_ids']) == 5
        assert len(sim.yearly_results) == 4 and sim.papers_per_project == papers
        budgets = [s['funding_budget'] for s in sim.yearly_results if 'funding_budget' in s]
        assert budgets and all(b['total_slots'] == 1 and sum(b['slots_by_program'].values()) == 1 for b in budgets)
        from scripts.native_benchmark_physical import physical_proof
        path = Path(sim.output_dir)/'portable_checkpoint_year_4.json.gz'
        evidence = {'run_id': 'scripted-capacity-forward', 'seed': 42,
            'system_fingerprint': spec.fingerprint, 'checkpoint_path': str(path),
            'checkpoint_sha256': file_sha256(path),
            'event_stream_hash': sim.native_system.to_dict()['event_stream_hash']}
        world = {'model': factory.model, 'model_digest': factory.model_digest,
            'source_commit': factory.source_commit, 'corpus_sha256': factory.corpus_sha256,
            'runtime_seed_binding': factory.runtime_seed_binding, 'experiment': experiment,
            'world_conditions': conditions,
            'image_id': 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'}
        proof = physical_proof(tmp_path/'runs'/'scripted-capacity-forward', spec,
            world=world, seed=42, years=4, evidence=evidence)
        assert proof['status'] == 'complete' and len(proof['annual_checkpoints']) == 4
        assert proof['world_conditions_proof']['fixed_annual_slot_cap'] == 1
        assert proof['measurement'] == base
        annual_paths = [Path(sim.output_dir)/f'portable_checkpoint_year_{y}.json.gz' for y in range(5)]
        assert measure_from_checkpoints(proof['measurement'], annual_paths) == measured
        transfers = [e for e in sim.native_system.events if e.event_type == EVENT]
        if allocation is not None:
            assert transfers
        for event in transfers:
            p = event.payload
            assert sum(p['balances_before'].values()) == sum(p['balances_after'].values())
            assert p['actual_debit'] == p['actual_credit'] > 0
        sim.resource_ledger.reconcile(4, sim.ecosystem.agent_population, require_closed=True)
    finally:
        sim.llm.response_cache.close()
