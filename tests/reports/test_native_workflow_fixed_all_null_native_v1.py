"""Native evaluation when an explicitly SCRIPTED upstream selection is all-null.

Upstream closure is a named fixture, not a claimed actual designer result.
Researcher HTTP/corpus are scripted. Role/transport factories, forwards,
checkpoints, observer, source proof, double cold audits/costs/reports stay real.
Deferred hardware-window test: collection is not execution evidence.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

from scripts import run_native_workflow_fixed_evaluation_v1 as driver
from scripts import run_native_objective_fixed_evaluation_v1 as common
from scripts import audit_native_workflow_fixed_evaluation_v1 as auditor
from scripts.analyze_native_open_v7 import _inventory
from scripts.finish_native_institution_loop_v1 import same_files
from scripts.native_benchmark_seed_usage import usage_inventory
from scripts.reports.native_workflow_fixed_evaluation_v1 import export
from scripts.reports.pre_scale_costs_v1 import analyze as costs
from tests.reports.test_native_workflow_fixed_evaluation_v1 import evidence, seal
from tests.reports.test_native_workflow_objective_loop_native_v1 import IMAGE
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.common_content_observer import make_contract
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory, SCIENTIST_DIGEST
from utopia.system.design_patch import clone
from utopia.utils.data_utils import file_sha256, write_json_atomic


def test_all_null_own_selection_runs_only_controls_and_never_fabricates_an_own_policy(tmp_path, fixed_corpus, monkeypatch):
    original, old_audit, _, _, _ = evidence(tmp_path / 'inputs', monkeypatch,
        all_null=True, transport=True, image_override=IMAGE)
    install_scripted_provider(tmp_path / 'provider', monkeypatch, 2)
    monkeypatch.setattr('requests.get', lambda *a, **k: SimpleNamespace(raise_for_status=lambda: None,
        json=lambda: {'models': [{'name': 'qwen3:8b', 'digest': SCIENTIST_DIGEST}]}))
    class Response:
        status_code = 200
        def __init__(self, body): self.text = json.dumps(body)
        def raise_for_status(self): pass
    class Loads:
        def get(self, url, **kwargs):
            assert url.endswith('/api/ps')
            return Response({'models': [{'name': 'qwen3:8b', 'digest': SCIENTIST_DIGEST, 'context_length': 40960}]})
        def post(self, url, **kwargs):
            assert url.endswith('/api/generate') and json.loads(kwargs['data'])['prompt'] == ''
            return Response({'model': 'qwen3:8b', 'done': True, 'done_reason': 'load', 'response': '',
                'eval_count': 0, 'prompt_eval_count': 0})
    monkeypatch.setattr('requests.Session', Loads)
    probe = LocalQwenNativeFactory(tmp_path / 'probe', tmp_path / 'cache', years=4, corpus_years=4)
    for key in ('model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'runtime_seed_binding', 'source_commit'):
        original['world'][key] = clone(getattr(probe, key))
        if key in original['scientist']: original['scientist'][key] = clone(getattr(probe, key))
        if key in ('corpus_sha256', 'dataset_identity'): original['designer'][key] = clone(getattr(probe, key))
    original['source_commit'] = probe.source_commit; original['data_cache'] = str(tmp_path / 'cache')
    provider = {k: original['scientist'][k] for k in ('model', 'model_digest')}
    original['observer_contract'] = make_contract(source_commit=probe.source_commit,
        provider=provider, backend={**provider, 'ollama_version': 'SCRIPTED'}, maximum_posts=1500, critics=3)
    original['world']['measurement_adapter_contract'] = clone(original['observer_contract']); seal(original)
    # Rebind this named fixture before dispatch, never amend real old data.
    old_audit.update(source_commit=original['source_commit'], plan_sha256=original['content_sha256'])
    old_audit['selection']['plan_sha256'] = original['content_sha256']; seal(old_audit['selection']); seal(old_audit)
    origin = tmp_path / 'SCRIPTED-origin'; origin.mkdir(); (origin / 'writer.lock').touch()
    inventory = tmp_path / 'SCRIPTED-unused-root'; inventory.mkdir()
    seeds = [72101]; usage = usage_inventory(inventory, seeds)
    p = driver.build_plan(original, old_audit, source=original['source_commit'],
        origin={'run': str(origin), 'SCRIPTED': 'upstream all-null closure is mocked'}, usages=[usage], seeds=seeds,
        observer_backend=original['observer_contract']['backend'], source_proof=driver.native_sources(original['source_commit']))
    root = tmp_path / 'evaluation'; root.mkdir()
    driver.save(root / 'seed-usage-00.json', {k: v for k, v in usage.items() if k != 'content_sha256'})
    driver.save(root / 'plan.json', p)
    monkeypatch.setattr(driver, 'origin_evidence', lambda origin: (original, old_audit))
    real_make = LocalRoleBoundNativeFactory.__call__
    def make(self, *args, **kwargs):
        sim = real_make(self, *args, **kwargs); sim.llm.sim = sim
        sim.llm.client.max_retries = 0; sim.llm.client.base_url = 'http://127.0.0.1:11434/v1'; sim.llm.client.timeout = 120
        return sim
    monkeypatch.setattr(LocalRoleBoundNativeFactory, '__call__', make)
    class Critics:
        @contextmanager
        def lease(self, contract): yield self
        def __call__(self, wire, timeout):
            body = {'model': json.loads(wire)['model'], 'done': True, 'done_reason': 'stop',
                'prompt_eval_count': 71, 'eval_count': 9,
                'message': {'content': json.dumps({'score': 4, 'rationale': 'SCRIPTED software fixture'})}}
            return {'http_status': 200, 'raw_http_response': json.dumps(body)}
    monkeypatch.setattr(common, 'LocalObserverBackend', lambda **kwargs: Critics())
    p = driver.require_plan(root); driver.run(root)
    assert driver.read(root / 'terminal.json')['status'] == 'closed' and len(p['jobs']) == 2
    assert all(all(label.startswith('reference:') for label in j['labels']) for j in p['jobs'])
    external = Path(tempfile.mkdtemp(prefix='science-utopia-workflow-null-cold-', dir='/private/tmp'))
    paths = [external / 'audit-one.json', external / 'audit-two.json']; before = _inventory(root)
    for path in paths: auditor.worker(root, path)
    assert paths[0].read_bytes() == paths[1].read_bytes(); proof = driver.read(paths[0])
    assert len(proof['worlds']) == 2 and all(w['status'] == 'complete' for w in proof['worlds'])
    assert all(len(w['physical_proof']['annual_checkpoints']) == 4 for w in proof['worlds'])
    projections = [costs(root, p, driver.read(path)) for path in paths]; assert projections[0] == projections[1]
    for i in (1, 2):
        export(SimpleNamespace(run=root, audit_one=paths[0], audit_two=paths[1], output=external / ('report-' + str(i))))
    files = same_files(external / 'report-1', external / 'report-2'); report = driver.read(external / 'report-1/report.json')
    missing = [r for r in report['logical_rows'] if r['label'].startswith('selected:')]
    assert len(missing) == 2 and all(r['physical_job'] is None and r['status'] == 'no-completed-submission' for r in missing)
    assert all(all(v is None for v in r['differences'].values()) for r in report['paired_differences'])
    assert report['fixed_selection'] == old_audit['selection'] and _inventory(root) == before
    write_json_atomic(tmp_path / 'verification.json', {
        'schema': 'scienceutopia.native-workflow-all-null-software-check.v1',
        'classification': 'SCRIPTED-upstream-all-null-origin-HTTP-and-corpus-not-scientific-evaluation',
        'source_commit': p['source_commit'], 'new_model_calls': 0, 'native_software_worlds': 2,
        'annual_checkpoints': 8, 'own_policy_worlds': 0, 'missing_own_labels_preserved': 2,
        'transport_application_records': len(list(root.rglob('scientist-transport.json'))),
        'matching_audit_sha256': file_sha256(paths[0]), 'matching_cost_content_sha256': projections[0]['content_sha256'],
        'matching_report_files': files, 'original_cold_audit_directory': str(external),
        'baseline_fallback': False, 'publication_ready': False}, sort_keys=True)
