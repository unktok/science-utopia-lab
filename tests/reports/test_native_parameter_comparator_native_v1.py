"""14 native worlds/56 annual checkpoints; all HTTP/data are SCRIPTED.

Eight real reference trajectories create the literal warm-start context, then
the production numeric runner evaluates six full worlds. Production role
factory, explicit load journalling/metadata replay, scalar feedback, Docker
consumers, physical checkpoints, cold critic reconstruction and costs are real
software paths. The original upstream *study audit* is a named fixture; this
does not prove original real-Qwen provenance or a scientific result.
"""
from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace

from scripts import run_native_parameter_comparator_v1 as driver
from scripts import run_native_planning_objective_loop_v1 as original_driver
from scripts import audit_native_parameter_comparator_v1 as audit
from scripts.reports.pre_scale_costs_v1 import analyze as costs
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.reports.test_native_planning_objective_loop_v1 import plan, seal
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.common_content_observer import CommonContentObserver, make_contract
from utopia.optimization.native_development_references import build_context
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory, SCIENTIST_DIGEST
from utopia.system.design_patch import clone
from utopia.utils.data_utils import write_json_atomic

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


def test_original_reference_context_six_numeric_worlds_real_roles_cold_audits_and_costs(tmp_path, fixed_corpus, monkeypatch):
    original, _, _, _ = plan(tmp_path / 'inputs', monkeypatch, IMAGE)
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
            return Response({'model': 'qwen3:8b', 'done': True, 'done_reason': 'load', 'response': '',
                'eval_count': 0, 'prompt_eval_count': 0})
    monkeypatch.setattr('requests.Session', LoadSession)
    probe = LocalQwenNativeFactory(tmp_path / 'probe', tmp_path / 'cache', years=4, corpus_years=4)
    for key in ('model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'runtime_seed_binding', 'source_commit'):
        original['world'][key] = clone(getattr(probe, key))
        if key in original['scientist']: original['scientist'][key] = clone(getattr(probe, key))
    original['source_commit'] = probe.source_commit; original['data_cache'] = str(tmp_path / 'cache')
    original['world']['classification'] = 'SCRIPTED-original-reference-worlds'
    original['observer_contract'] = make_contract(source_commit=probe.source_commit,
        provider={k: original['scientist'][k] for k in ('model', 'model_digest')},
        backend={**{k: original['scientist'][k] for k in ('model', 'model_digest')}, 'ollama_version': 'SCRIPTED'},
        maximum_posts=1500, critics=3)
    original['world']['measurement_adapter_contract'] = clone(original['observer_contract']); seal(original)
    real_make = LocalRoleBoundNativeFactory.__call__
    def make(self, *a, **kw):
        sim = real_make(self, *a, **kw); sim.llm.sim = sim; return sim
    monkeypatch.setattr(LocalRoleBoundNativeFactory, '__call__', make)
    class Critic:
        @contextmanager
        def lease(self, contract): yield self
        def __call__(self, wire, timeout):
            body = {'model': json.loads(wire)['model'], 'done': True, 'done_reason': 'stop',
                'prompt_eval_count': 71, 'eval_count': 9,
                'message': {'content': json.dumps({'score': 4, 'rationale': 'SCRIPTED software fixture'})}}
            return {'http_status': 200, 'raw_http_response': json.dumps(body)}
    prior = tmp_path / 'original'; prior.mkdir(); (prior / 'writer.lock').touch()
    observer = CommonContentObserver(prior / 'observer', original['observer_contract'], backend=Critic())
    pairs = [original_driver.observe(prior, original, label, observer) for label in original['reference_order']]
    context = build_context(pairs, world=original['world'], seeds=[driver.SEED], loss_spec=original['losses']['throughput'])
    driver.save(prior / 'developer-reference-context.json', {k: v for k, v in context.items() if k != 'content_sha256'})
    for objective in original['objectives']:
        # Explicit original-generation null fixture; no fabricated successful
        # model-authored programs are needed for the comparison reader path.
        write_json_atomic(prior / 'search' / objective / 'campaign/native-adaptive-state.json', {
            'pending': None, 'records': [{'request': {'generation': g}, 'draws': [{'suggestion': None}],
                'observations': [None], 'generation_error': 'SCRIPTED original non-submission'} for g in range(3)]})
    upstream = seal({'schema': 'scienceutopia.native-planning-objective-loop-audit.v1',
        'source_commit': original['source_commit'], 'worlds': [],
        'SCRIPTED': 'only original upstream study audit is mocked'})
    origin = {'run': str(prior), 'source': str(driver.ROOT), 'source_commit': original['source_commit'], 'audit_files': {}}
    p = driver.build_plan(original, upstream, context, source=probe.source_commit, origin=origin,
        observer_backend=original['observer_contract']['backend'],
        native_sources=driver.unchanged_native_sources(original['source_commit']))
    root = tmp_path / 'numeric'; root.mkdir(); driver.save(root / 'plan.json', p)
    monkeypatch.setattr(driver, 'origin_evidence', lambda origin: (original, upstream))
    monkeypatch.setattr(driver, 'require_environment', lambda: None)
    monkeypatch.setattr(driver, 'LocalObserverBackend', lambda **kw: Critic())
    # Do not mock require_plan, numeric ask/tell, evaluator, factory, role receipt
    # readers, physical proof, measurement reconstruction or selection.
    p = driver.require_plan(root); driver.run(root)
    assert driver.read(root / 'terminal.json')['status'] == 'closed'
    paths = [tmp_path / 'audit-one.json', tmp_path / 'audit-two.json']
    from scripts.analyze_native_open_v7 import _inventory
    before = _inventory(root)
    for path in paths: audit.worker(root, path)
    assert paths[0].read_bytes() == paths[1].read_bytes()
    proof = driver.read(paths[0]); assert len(proof['worlds']) == 6
    assert all(len(w['physical_proof']['annual_checkpoints']) == 4 and w['loaded']['confirmed'] for w in proof['worlds'])
    projections = [costs(root, p, driver.read(path)) for path in paths]
    assert projections[0] == projections[1]
    assert len(projections[0]['scientist']['physical_response_caches']) == 6
    assert projections[0]['common_content_observer']['physical_requests'] > 0
    assert len(list(root.rglob('role-load-000.json'))) == 6
    assert not list(root.rglob('dispatch-*.intent.json'))
    assert all(len(list((root / 'search' / o).glob('generation-*'))) == 3 for o in p['objectives'])
    from scripts.reports.native_parameter_comparator_v1 import export
    outputs = [tmp_path / 'report-one', tmp_path / 'report-two']
    for out in outputs:
        export(SimpleNamespace(run=root, audit_one=paths[0], audit_two=paths[1], output=out))
    assert {v.name: v.read_bytes() for v in outputs[0].iterdir()} == {v.name: v.read_bytes() for v in outputs[1].iterdir()}
    report = driver.read(outputs[0] / 'report.json')
    assert len(report['references']) == 8 and len(report['slots']) == 12
    assert sum(row['status'] == 'generation-null' for row in report['slots']) == 6
    assert _inventory(root) == before
