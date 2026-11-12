"""Fourteen original native worlds and the real bounded editor/cold interfaces.

Researcher/designer/critic HTTP, corpus, process launch and role loads are
SCRIPTED. Actual prototype/history requests, calibration API, role factory,
outer execute/replay, Docker native mechanisms, observations, cold audit and
cost projection are exercised. Identity submissions are software QA, not LLM
invention, actual-Qwen results or readiness for the real provider.
"""
from contextlib import contextmanager
import json
from pathlib import Path

from scripts import run_native_planning_objective_loop_v1 as driver
from scripts import audit_native_planning_objective_loop_v1 as audit
from scripts.reports.pre_scale_costs_v1 import analyze as cost_projection
from tests.reports.test_native_planning_objective_loop_v1 import plan, seal
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from tests.optimization.test_native_designer_contract_v16 import ScriptedSession, Response
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.common_content_observer import make_contract
from utopia.system.design_patch import clone

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


def test_full_original_world_controller_bounded_editor_cold_audit_and_costs(tmp_path, fixed_corpus, monkeypatch):
    p, _, _, _ = plan(tmp_path / 'inputs', monkeypatch, IMAGE)
    install_scripted_provider(tmp_path / 'provider', monkeypatch, 2)
    probe = LocalQwenNativeFactory(tmp_path / 'probe', tmp_path / 'cache', years=4, corpus_years=4, allow_dirty=True)
    for key in ('model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'runtime_seed_binding', 'source_commit'):
        p['world'][key] = clone(getattr(probe, key))
        if key in p['scientist']: p['scientist'][key] = clone(getattr(probe, key))
    p['source_commit'] = probe.source_commit
    p['world']['classification'] = 'SCRIPTED-fourteen-native-world-planning-integration'
    p['observer_contract'] = make_contract(source_commit=p['source_commit'],
        provider={k: p['scientist'][k] for k in ('model', 'model_digest')},
        backend={**{k: p['scientist'][k] for k in ('model', 'model_digest')}, 'ollama_version': 'SCRIPTED'},
        maximum_posts=1500, critics=3)
    p['world']['measurement_adapter_contract'] = clone(p['observer_contract']); seal(p)
    origin = Path(p['origin']['run']); origin.mkdir(); (origin / 'writer.lock').touch()
    root = tmp_path / 'study'; root.mkdir()
    driver.save(root / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    monkeypatch.setattr(driver, 'require_environment', lambda: None)
    monkeypatch.setattr(driver, 'require_plan', lambda root: p)
    def factory(directory, p, root):
        f = LocalQwenNativeFactory(directory, tmp_path / 'cache', years=4, corpus_years=4,
            record_wire=True, record_code=True, maximum_http_attempts=1024, allow_dirty=True,
            inference_lock=root / 'inference.lock', world_conditions=p['world']['world_conditions'],
            experiment_binding=p['experiment'])
        def make(spec, seed, run_id):
            sim = f(spec, seed, run_id); sim.llm.sim = sim; return sim
        return make
    monkeypatch.setattr(driver, 'factory_for', factory)
    class Critic:
        @contextmanager
        def lease(self, contract): yield self
        def __call__(self, wire, timeout):
            body = {'model': json.loads(wire)['model'], 'done': True, 'done_reason': 'stop',
                'prompt_eval_count': 71, 'eval_count': 9,
                'message': {'content': json.dumps({'score': 4, 'rationale': 'SCRIPTED content preference'})}}
            return {'http_status': 200, 'raw_http_response': json.dumps(body)}
    monkeypatch.setattr(driver, 'LocalObserverBackend', lambda **kw: Critic())
    from utopia.optimization import native_bounded_staged_designer as bounded
    from utopia.optimization.native_designer_tools_v25 import function_data
    original_execute = bounded.execute
    def execute(directory, **kw):
        actions = [{'tool': 'plan', 'objective_reasoning': 'SCRIPTED identity QA',
            'design_intent': 'Retain the literal parent for integration only'}, {'tool': 'finish'}]
        class Session(ScriptedSession):
            calls = []; production = []
            def get(self, url, **kwargs):
                if url.endswith('/version'): return Response({'version': p['backend']['ollama_version']})
                return Response({'models': [{'name': p['designer']['model'], 'digest': p['designer']['model_digest']}]})
            def post(self, url, **kwargs):
                payload = json.loads(kwargs['data']); system = payload['messages'][0]['content']
                if 'TRUSTED INTERFACE CALIBRATION TASK' in system:
                    result = super().post(url, **kwargs).json(); result['model'] = p['designer']['model']; return Response(result)
                action = actions[len(self.production)]; self.production.append(payload); self.calls.append(payload)
                return Response({'model': p['designer']['model'], 'done': True, 'done_reason': 'stop',
                    'prompt_eval_count': 120, 'eval_count': 12,
                    'message': {'role': 'assistant', 'content': json.dumps(function_data(action)),
                        **({'thinking': 'SCRIPTED planning evidence'} if payload['think'] else {})}})
        def inline_worker(argv, **kwargs):
            bounded.worker(argv[-2], argv[-1]); return {'timed_out': False, 'returncode': 0}
        with monkeypatch.context() as scoped:
            scoped.setattr('requests.Session', Session)
            scoped.setattr('utopia.optimization.native_scientist_load_v38.load_local_role', lambda *a, **k: None)
            scoped.setattr(bounded, 'run_bounded', inline_worker)
            return original_execute(directory, **kw)
    # Both readiness and proposals use the real bounded public API. Only its
    # subprocess transport runs inline, under the scoped scripted HTTP above.
    monkeypatch.setattr('scripts.run_native_institution_loop_v1.execute', execute)
    monkeypatch.setattr(driver, 'execute', execute)
    driver.run(root)
    assert driver.read(root / 'terminal.json')['status'] == 'closed'
    assert driver.read(root / 'terminal.json')['complete_references'] == 8
    selection = driver.read(root / 'selection.json')
    assert all(v['completed_submissions'] == 3 for v in selection['selected'].values())
    # Explicit fixture-only scientist role attestation; not actual model load.
    monkeypatch.setattr('scripts.analyze_native_design_benchmark.loaded', lambda *a, **k: {
        'confirmed': True, 'SCRIPTED': 'not a real model-load attestation',
        'context': str(Path(a[0]).parent / 'SCRIPTED-loaded-context.json')})
    paths = [tmp_path / 'audit-one.json', tmp_path / 'audit-two.json']
    for path in paths: audit.worker(root, path)
    assert paths[0].read_bytes() == paths[1].read_bytes()
    proof = driver.read(paths[0]); assert len(proof['worlds']) == 14
    assert len(proof['readiness']) == 6 and proof['initial_readiness']
    assert all(w['status'] == 'complete' for w in proof['worlds'])
    assert all(len(w['physical_proof']['annual_checkpoints']) == 4 for w in proof['worlds'])
    costs = cost_projection(root, p, proof)
    assert len(costs['scientist']['physical_response_caches']) == 14
    assert costs['common_content_observer']['physical_requests'] == proof['observer']['dispatch_intents']
    assert costs['common_content_observer']['physical_requests'] > 0
