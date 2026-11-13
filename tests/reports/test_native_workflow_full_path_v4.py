"""Production five-founder world, three four-year runs, SCRIPTED HTTP/corpus.

This is software evidence, not new Qwen inference, optimization, invention,
held-out evaluation or a scientific effect estimate. Native implementations,
factory, role-load journals, sandbox code, checkpoints and cold physical audit
are real. The hand-designed contrast changes only three phases/five edges.
"""
import json
from pathlib import Path
from types import SimpleNamespace

from scripts.native_benchmark_physical import physical_proof
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.reports.test_native_planning_objective_loop_v1 import plan
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_loaded_roles_v38 import (
    LocalRoleBoundNativeFactory, SCIENTIST_DIGEST, replay_loaded_context)
from utopia.optimization.native_world import measure_native_world
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_workflow_domain_v4 import (
    edit_workflow, execution_order, post_funding_cost_control, verify_workflow_interval, workflow_design_space)
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest, make_patch
from utopia.utils.data_utils import file_sha256, write_json_atomic

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


def test_original_instance_noop_and_reordered_native_world_with_cold_proofs(tmp_path, fixed_corpus, monkeypatch):
    p, _, _, _ = plan(tmp_path / 'inputs', monkeypatch, IMAGE)
    install_scripted_provider(tmp_path / 'provider', monkeypatch, 2)
    monkeypatch.setattr('requests.get', lambda *a, **k: SimpleNamespace(raise_for_status=lambda: None,
        json=lambda: {'models': [{'name': 'qwen3:8b', 'digest': SCIENTIST_DIGEST}]}))
    class Response:
        status_code = 200
        def __init__(self, body): self.text = json.dumps(body)
        def raise_for_status(self): pass
    class LoadSession:
        def get(self, url, **kw):
            assert url.endswith('/api/ps')
            return Response({'models': [{'name': 'qwen3:8b', 'digest': SCIENTIST_DIGEST, 'context_length': 40960}]})
        def post(self, url, **kw):
            body = json.loads(kw['data']); assert url.endswith('/api/generate') and body['prompt'] == ''
            return Response({'model': 'qwen3:8b', 'done': True, 'done_reason': 'load',
                'response': '', 'eval_count': 0, 'prompt_eval_count': 0})
    monkeypatch.setattr('requests.Session', LoadSession)
    probe = LocalQwenNativeFactory(tmp_path / 'probe', tmp_path / 'cache', years=4, corpus_years=4)
    provider = clone(p['designer'])
    for key in ('corpus_sha256', 'dataset_identity'):
        provider[key] = clone(getattr(probe, key))
    experiment = {'protocol': 'SCRIPTED-native-workflow-v4-full-path',
        'scientific_inference': False, 'hand_designed_control': True}
    factory = LocalRoleBoundNativeFactory(tmp_path / 'worlds', tmp_path / 'cache', years=4, corpus_years=4,
        designer_provider=provider, record_wire=True, record_code=True, maximum_http_attempts=1024,
        inference_lock=tmp_path / 'inference.lock', world_conditions=p['world']['world_conditions'],
        experiment_binding=experiment)
    anchor = SystemSpec.from_dict(p['reference_systems']['assignment-reserve21-no-review-all'])
    unchanged = edit_workflow(anchor, phase_updates={}, rewires=[])
    reordered = post_funding_cost_control(anchor)
    assert unchanged == anchor and reordered.mechanisms == anchor.mechanisms
    source_before = {path: file_sha256(path) for path in (factory.source_root / 'utopia').rglob('*.py')}
    summaries, requests = {}, {}
    world = {'model': factory.model, 'model_digest': factory.model_digest,
        'source_commit': factory.source_commit, 'corpus_sha256': factory.corpus_sha256,
        'runtime_seed_binding': factory.runtime_seed_binding, 'experiment': experiment,
        'world_conditions': factory.world_conditions, 'image_id': IMAGE, 'years': 4}
    settings = dict(initial_system=anchor, loss_spec=p['losses']['throughput'], seeds=[61001],
        world_binding=world, strategies={'scripted': {'kind': 'SCRIPTED-software-QA'}},
        mode='blackbox', seed=68011, design_space=workflow_design_space(anchor))
    campaign = NativeAdaptiveDesignCampaign(tmp_path / 'campaign', **settings)
    feedback = []
    for generation, (label, spec) in enumerate((('original', anchor), ('literal-noop', unchanged), ('post-funding-cost', reordered))):
        captured = {}
        def generate(request):
            feedback.append(clone(request))
            assert len(request['observations']) == generation
            parent = SystemSpec.from_dict(request['parent_system'])
            patch = None if parent == spec else make_patch(parent, [
                {'op': 'replace', 'path': '/' + key, 'value': spec.to_dict()[key]}
                for key in ('connections', 'schedules')], rationale='SCRIPTED exact hand-designed timing control')
            return {'base_patch': patch, 'factors': [], 'continuous': [],
                'provenance': {'SCRIPTED': 'fixed software sequence, not an optimizing inventor'}}
        def make(candidate, seed, run_id):
            assert candidate == spec and seed == 61001
            sim = factory(candidate, seed, run_id); sim.llm.sim = sim
            captured.update(sim=sim, run_id=run_id)
            return sim
        record = campaign.advance(simulation_factory=make, generators={'scripted': generate}, count=1)
        assert not record['generation_error']
        observation = record['observations'][0]
        assert observation['status'] == 'complete', observation['metadata']['technical_failures']
        sim, run_id = captured['sim'], captured['run_id']
        try:
            assert len(sim.yearly_results) == 4 and sim.native_system.last_year == 4
            interval = verify_workflow_interval(anchor, spec, sim.native_system.events, years=4)
            assert interval['effect_witnesses'] == 48
            sim.resource_ledger.reconcile(4, sim.ecosystem.agent_population, require_closed=True)
            budgets = [row['funding_budget'] for row in sim.yearly_results if 'funding_budget' in row]
            assert budgets and all(b['total_slots'] == 1 and sum(b['slots_by_program'].values()) == 1 for b in budgets)
            path = Path(sim.output_dir) / 'portable_checkpoint_year_4.json.gz'
            evidence = {'run_id': run_id, 'seed': 61001, 'system_fingerprint': spec.fingerprint,
                'checkpoint_path': str(path), 'checkpoint_sha256': file_sha256(path),
                'event_stream_hash': sim.native_system.to_dict()['event_stream_hash']}
            cell = tmp_path / 'worlds' / run_id
            proof1 = physical_proof(cell, spec, world=world, seed=61001, years=4, evidence=evidence)
            proof2 = physical_proof(cell, spec, world=world, seed=61001, years=4, evidence=evidence)
            assert proof1 == proof2 and proof1['status'] == 'complete'
            assert len(proof1['annual_checkpoints']) == 4
            assert proof1['measurement'] == measure_native_world(sim, run_id=run_id)
            context = json.loads((cell / 'loaded-role-context-000.json').read_text())
            assert replay_loaded_context(context, expected={'scientist': factory.scientist_provider},
                purpose='before-native-world:' + run_id)
            requests[label] = [json.loads(line)['payload'] for line in (cell / 'wire-requests.jsonl').read_text().splitlines()]
            # Trust actual event ordering, not metadata.native_process.order.
            stages = {e.payload.get('stage'): e.sequence for e in sim.native_system.events
                if e.event_type == 'native.system.phase_executed' and e.year == 1}
            assert (stages['funding'] < stages['costs']) == (label == 'post-funding-cost')
            summaries[label] = {'SCRIPTED': True, 'physical_proof': proof1, 'interval': interval,
                'evidence': evidence, 'system_fingerprint': spec.fingerprint,
                'scientist_requests_sha256': digest(requests[label]),
                'scientist_request_count': len(requests[label]), 'execution_order': list(execution_order(spec)),
                'funding_budgets': budgets, 'world': world, 'assigned_loss': observation['loss'],
                'observation': observation, 'next_request_history_length': generation}
        finally:
            sim.llm.response_cache.close()
    assert requests['original'] == requests['literal-noop']
    reopened = NativeAdaptiveDesignCampaign(tmp_path / 'campaign', **settings)
    assert reopened.state == campaign.state and len(reopened.state['records']) == 3
    assert [o['observation']['loss'] for o in feedback[2]['observations']] == [
        summaries[label]['assigned_loss'] for label in ('original', 'literal-noop')]
    assert source_before == {path: file_sha256(path) for path in source_before}
    write_json_atomic(tmp_path / 'verification.json', {'schema': 'scienceutopia.native-workflow-full-path.v4',
        'classification': 'SCRIPTED-production-factory-software-check', 'source_commit': factory.source_commit,
        'new_model_calls': 0, 'native_software_worlds': 3, 'annual_checkpoints': 12,
        'original_and_noop_full_scientist_payloads_equal': True, 'native_source_bytes_unchanged': True,
        'losses_replayed_and_visible_in_next_request': True,
        'original_blackbox_campaign_cold_reopens': True,
        'reordered_implementations_and_numeric_parameters_unchanged': True,
        'automatic_invention_or_scientific_improvement_claimed': False, 'runs': summaries}, sort_keys=True)
