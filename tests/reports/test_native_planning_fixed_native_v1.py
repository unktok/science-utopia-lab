"""Sixteen native forwards and all cold readouts, with SCRIPTED HTTP/corpus.

Development-origin, seed-inventory and model-load attestations are explicitly
mocked. Forward execution, original checkpoints, observer public API and cold
reconstruction, source/physical proof, reports and costs are not mocked.
These fixture seeds are software data, not a declared scientific evaluation.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from scripts import run_native_planning_fixed_evaluation_v1 as driver
from scripts import audit_native_planning_fixed_evaluation_v1 as audit
from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.pre_scale_costs_v1 import analyze as cost_projection
from scripts.reports.native_planning_fixed_evaluation_v1 import export as score_export
from tests.reports.test_native_planning_fixed_evaluation_v1 import evidence, usage, seal
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.common_content_observer import make_contract
from utopia.system.design_patch import clone


def test_sixteen_native_worlds_same_observer_double_audit_and_all_cold_readers(tmp_path, fixed_corpus, monkeypatch):
    seeds = [72101, 72107]
    original, origin_audit, _ = evidence(tmp_path / 'inputs', monkeypatch, seeds=seeds,
        image_override='sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833')
    install_scripted_provider(tmp_path / 'provider', monkeypatch, 2)
    probe = LocalQwenNativeFactory(tmp_path / 'probe', tmp_path / 'cache', years=4, corpus_years=4, allow_dirty=True)
    for key in ('model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'runtime_seed_binding', 'source_commit'):
        original['world'][key] = clone(getattr(probe, key))
        if key in original['scientist']: original['scientist'][key] = clone(getattr(probe, key))
    original['source_commit'] = probe.source_commit
    original['world']['classification'] = 'SCRIPTED-planning-fixed-native-integration'
    original['observer_contract'] = make_contract(source_commit=probe.source_commit,
        provider={k: original['scientist'][k] for k in ('model', 'model_digest')},
        backend={**{k: original['scientist'][k] for k in ('model', 'model_digest')}, 'ollama_version': 'SCRIPTED'},
        maximum_posts=1500, critics=3)
    original['world']['measurement_adapter_contract'] = clone(original['observer_contract']); seal(original)
    origin_audit.update(source_commit=original['source_commit'], plan_sha256=original['content_sha256'])
    origin_audit['selection']['plan_sha256'] = original['content_sha256']; seal(origin_audit['selection']); seal(origin_audit)
    origin = tmp_path / 'SCRIPTED-origin'; origin.mkdir(); (origin / 'writer.lock').touch()
    inventory = tmp_path / 'SCRIPTED-unused-root'; inventory.mkdir()
    u = usage(seeds); u['root'] = str(inventory); seal(u)
    p = seal(driver.build_plan(original, origin_audit, source=probe.source_commit,
        origin={'run': str(origin), 'SCRIPTED': 'not actual development closure'}, usages=[u], seeds=seeds,
        observer_backend=original['observer_contract']['backend']))
    root = tmp_path / 'evaluation'; root.mkdir()
    driver.save(root / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    driver.save(root / 'seed-usage-00.json', {k: v for k, v in u.items() if k != 'content_sha256'})
    monkeypatch.setattr(driver, 'origin_evidence', lambda origin: (original, origin_audit))
    monkeypatch.setattr(driver, 'require_environment', lambda: None)
    monkeypatch.setattr(driver, 'usage_inventory', lambda *a: u)
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
    driver.run(root)
    assert driver.require_plan(root) == p and driver.read(root / 'terminal.json')['status'] == 'closed'
    assert driver.read(root / 'terminal.json')['completed_jobs'] == 16
    monkeypatch.setattr('scripts.analyze_native_design_benchmark.loaded', lambda *a, **k: {
        'confirmed': True, 'SCRIPTED': 'not an actual-model load attestation',
        'context': str(Path(a[0]).parent / 'SCRIPTED-role-context.json')})
    paths = [tmp_path / 'audit-one.json', tmp_path / 'audit-two.json']
    for path in paths: audit.worker(root, path)
    assert paths[0].read_bytes() == paths[1].read_bytes()
    proof = driver.read(paths[0]); assert len(proof['worlds']) == 16
    assert proof['source_proof']['status'] == 'verified-exact-source-closure'
    assert all(w['status'] == 'complete' and len(w['physical_proof']['annual_checkpoints']) == 4 for w in proof['worlds'])
    assert proof['observer']['dispatch_intents'] > 0
    assert not proof['new_model_calls'] and not proof['new_code_executions']
    before = _inventory(root); outputs = [tmp_path / 'scores-one', tmp_path / 'scores-two']
    for out in outputs:
        score_export(SimpleNamespace(run=root, audit_one=paths[0], audit_two=paths[1], output=out))
    assert {f.name: f.read_bytes() for f in outputs[0].iterdir()} == {f.name: f.read_bytes() for f in outputs[1].iterdir()}
    report = driver.read(outputs[0] / 'report.json')
    assert len(report['logical_rows']) == 20 and len(report['paired_differences']) == 32
    assert report['fixed_selection'] == p['fixed_selection']
    for name, extra in (
            ('native_planning_choice_trace_v1', ('--frozen-source', str(driver.ROOT), '--study', 'fixed-evaluation')),
            ('native_institution_effect_trace_v1', ('--frozen-source', str(driver.ROOT), '--scope', 'planning-fixed-evaluation')),
            ('native_observed_request_classes_v1', ())):
        copies = [tmp_path / (name + '-one'), tmp_path / (name + '-two')]
        for out in copies:
            subprocess.run([sys.executable, '-m', 'scripts.reports.' + name, '--run', str(root),
                '--audit-one', str(paths[0]), '--audit-two', str(paths[1]), '--output', str(out), *extra],
                cwd=driver.ROOT, check=True, capture_output=True, text=True, timeout=1800)
        assert {f.name: f.read_bytes() for f in copies[0].iterdir()} == {f.name: f.read_bytes() for f in copies[1].iterdir()}
        assert len(driver.read(copies[0] / 'report.json')['worlds']) == 16
    costs = [cost_projection(root, p, proof), cost_projection(root, p, proof)]
    assert costs[0] == costs[1] and len(costs[0]['scientist']['physical_response_caches']) == 16
    assert costs[0]['common_content_observer']['physical_requests'] == proof['observer']['dispatch_intents']
    assert _inventory(root) == before
