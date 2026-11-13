"""Original production worlds + actual bounded child/cold proof; SCRIPTED data.

Origin/prerequisite closure are named fixtures, not scientific attestations.
Only HTTP/corpus/retrieval are scripted. No actual endpoint inference or
autonomous discovery is claimed. The known invalid own slot is not refilled.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import pytest

from scripts import run_native_workflow_objective_loop_v1 as driver
from scripts import audit_native_workflow_objective_loop_v1 as audit
from scripts.reports.pre_scale_costs_v1 import analyze as costs
from tests.reports.test_native_planning_objective_loop_v1 import plan, seal
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization import native_workflow_designer_v1 as author_module
from utopia.optimization.common_content_observer import make_contract
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory, SCIENTIST_DIGEST
from utopia.optimization.native_workflow_domain_v4 import post_funding_cost_control
from utopia.runtime.bounded_process import run_bounded
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic, file_sha256

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


@pytest.mark.parametrize('prerequisite_kind', ['legacy-scripted', 'independent-numeric-v2'])
def test_bounded_workflow_designer_seven_native_worlds_known_null_and_double_cold_audit(
        tmp_path, fixed_corpus, monkeypatch, prerequisite_kind):
    original, _, _, _ = plan(tmp_path / 'inputs', monkeypatch, IMAGE)
    install_scripted_provider(tmp_path / 'provider', monkeypatch, 2)
    monkeypatch.setattr('requests.get', lambda *a, **k: SimpleNamespace(raise_for_status=lambda: None,
        json=lambda: {'models': [{'name': 'qwen3:8b', 'digest': SCIENTIST_DIGEST}]}))
    class Response:
        status_code = 200
        def __init__(self, body): self.text = json.dumps(body)
        def raise_for_status(self): pass
    class Loads:
        def get(self, url, **kw):
            assert url.endswith('/api/ps')
            return Response({'models': [{'name': 'qwen3:8b', 'digest': SCIENTIST_DIGEST, 'context_length': 40960}]})
        def post(self, url, **kw):
            assert url.endswith('/api/generate') and json.loads(kw['data'])['prompt'] == ''
            return Response({'model': 'qwen3:8b', 'done': True, 'done_reason': 'load', 'response': '',
                'eval_count': 0, 'prompt_eval_count': 0})
    monkeypatch.setattr('requests.Session', Loads)
    probe = LocalQwenNativeFactory(tmp_path / 'probe', tmp_path / 'cache', years=4, corpus_years=4)
    for key in ('model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'runtime_seed_binding', 'source_commit'):
        original['world'][key] = clone(getattr(probe, key))
        if key in original['scientist']: original['scientist'][key] = clone(getattr(probe, key))
        if key in ('corpus_sha256', 'dataset_identity'): original['designer'][key] = clone(getattr(probe, key))
    original['source_commit'] = probe.source_commit; original['data_cache'] = str(tmp_path / 'cache')
    observer_backend = {k: original['scientist'][k] for k in ('model', 'model_digest')}; observer_backend['ollama_version'] = 'SCRIPTED'
    original['observer_contract'] = make_contract(source_commit=probe.source_commit,
        provider={k: original['scientist'][k] for k in ('model', 'model_digest')},
        backend=observer_backend, maximum_posts=1500, critics=3)
    original['world']['measurement_adapter_contract'] = clone(original['observer_contract']); seal(original)
    upstream = seal({'schema': 'scienceutopia.native-planning-objective-loop-audit.v1',
        'source_commit': probe.source_commit, 'SCRIPTED': 'original upstream closure is a named fixture'})
    prerequisite = {'directory': str(tmp_path / 'SCRIPTED-chain'),
        'SCRIPTED': 'numeric chain closure is mocked; no real closure claim'}
    if prerequisite_kind == 'independent-numeric-v2':
        from tests.reports.native_workflow_prerequisite_fixture_v2 import scripted_predecessor
        directory = scripted_predecessor(tmp_path / 'SCRIPTED-predecessor')
        prerequisite = driver.prerequisite_binding(directory)
    origin = {'SCRIPTED': 'not a real archived-study attestation'}
    backend = {k: original['designer'][k] for k in ('model', 'model_digest')}; backend['ollama_version'] = 'SCRIPTED'
    p = driver.build_plan(original, upstream, source=probe.source_commit, origin=origin,
        backend=backend, observer_backend=observer_backend, prerequisite=prerequisite,
        sources=driver.native_sources(probe.source_commit))
    root = tmp_path / 'run'; root.mkdir(); driver.save(root / 'plan.json', p)
    monkeypatch.setattr(driver, 'origin_evidence', lambda origin: (original, upstream))
    if prerequisite_kind == 'legacy-scripted':
        monkeypatch.setattr(driver, 'prerequisite_binding', lambda directory: clone(prerequisite))
        monkeypatch.setattr(driver, 'require_prerequisite', lambda binding: {'SCRIPTED': 'no actual chain is closed here'})
    real_make = LocalRoleBoundNativeFactory.__call__
    def make(self, *a, **kw):
        sim = real_make(self, *a, **kw); sim.llm.sim = sim; return sim
    monkeypatch.setattr(LocalRoleBoundNativeFactory, '__call__', make)
    class Critics:
        @contextmanager
        def lease(self, contract): yield self
        def __call__(self, wire, timeout):
            body = {'model': json.loads(wire)['model'], 'done': True, 'done_reason': 'stop',
                'prompt_eval_count': 71, 'eval_count': 9,
                'message': {'content': json.dumps({'score': 4, 'rationale': 'SCRIPTED software fixture'})}}
            return {'http_status': 200, 'raw_http_response': json.dumps(body)}
    monkeypatch.setattr(driver, 'LocalObserverBackend', lambda **kw: Critics())
    child_path = tmp_path / 'child-http-fixture'; child_path.mkdir()
    shutil.copyfile(driver.ROOT / 'tests/fixtures/native_workflow_http_sitecustomize.py', child_path / 'sitecustomize.py')
    calls = []
    def child(argv, **kwargs):
        intent = driver.read(argv[-2]); binding = driver.read(Path(argv[-2]).parent / 'binding.json')
        req = binding['request']; parent = SystemSpec.from_dict(req['parent_system'])
        body = json.loads(intent['payload']['messages'][1]['content'])
        if binding['purpose'] == 'calibration':
            submission = body['control_submission']
        elif req['generation'] == 1 and req['loss_spec']['id'] == original['losses']['content-utility']['id']:
            submission = {'phase_updates': {'world.costs': 999}, 'remove_connections': [],
                'add_connections': [], 'rationale': 'SCRIPTED invalid graph; consume exactly once'}
        else:
            anchor = SystemSpec.from_dict(req['design_space_anchor']); target = post_funding_cost_control(anchor)
            phase_by_id = {s.mechanism_id: s.phase for s in parent.schedules}
            submission = {'phase_updates': {s.mechanism_id: s.phase for s in target.schedules
                    if s.phase != phase_by_id[s.mechanism_id]},
                'remove_connections': list(range(len(parent.connections))),
                'add_connections': target.to_dict()['connections'],
                'rationale': 'SCRIPTED timing control, not autonomous optimization'}
        fixture = tmp_path / ('child-http-' + str(len(calls)) + '.json')
        write_json_atomic(fixture, {'provider': p['designer'], 'literal_submission': submission,
            'expected_request_wire_utf8': intent['request_wire']['request_wire_utf8']})
        calls.append({'purpose': binding['purpose'], 'request': clone(req), 'context': body['context'],
            'submission': clone(submission), 'wire_utf8_bytes': len(intent['request_wire']['request_wire_utf8'].encode())})
        return run_bounded(argv, **kwargs, env={**os.environ, 'PYTHONPATH': str(child_path),
            'SCIENCE_UTOPIA_WORKFLOW_HTTP_FIXTURE': str(fixture)})
    monkeypatch.setattr(author_module, 'run_bounded', child)
    # No certificate return, compiler, workflow validation, campaign, factory,
    # role receipt, response journal or physical auditor is mocked.
    p = driver.require_plan(root); driver.run(root)
    terminal = driver.read(root / 'terminal.json')
    assert terminal['status'] == 'closed' and terminal['consumed_slots'] == 6 and terminal['observations'] == 7
    assert len(calls) == 13 and sum(c['purpose'] == 'proposal' for c in calls) == 6
    u2 = [c for c in calls if c['purpose'] == 'proposal' and c['request']['generation'] == 2
        and c['request']['loss_spec']['id'] == original['losses']['content-utility']['id']][0]
    assert u2['context']['consumed_generation_nulls'][0]['literal_submission_failure']['literal_submission']['phase_updates'] == {'world.costs': 999}
    # Explicit --basetemp may be inside ignored source outputs. Original cold
    # auditors correctly forbid writing anywhere in that source worktree.
    # Retain audit exports in a separate temporary directory, not by weakening
    # the production guard or modifying any completed raw journal.
    audit_directory = Path(tempfile.mkdtemp(prefix='science-utopia-workflow-audit-', dir='/private/tmp'))
    audit_paths = [audit_directory / 'audit-one.json', audit_directory / 'audit-two.json']
    from scripts.analyze_native_open_v7 import _inventory
    before = _inventory(root)
    for path in audit_paths: audit.worker(root, path)
    assert audit_paths[0].read_bytes() == audit_paths[1].read_bytes()
    proof = driver.read(audit_paths[0]); assert len(proof['worlds']) == 7
    assert all(len(w['physical_proof']['annual_checkpoints']) == 4 for w in proof['worlds'])
    cost_reports = [costs(root, p, driver.read(path)) for path in audit_paths]
    assert cost_reports[0] == cost_reports[1]
    groups = cost_reports[0]['auxiliary']['groups']
    assert len([e for e in cost_reports[0]['auxiliary']['events'] if e['kind'] == 'workflow-readiness']) == 7
    assert len([e for e in cost_reports[0]['auxiliary']['events'] if e['kind'] == 'workflow-proposal']) == 6
    assert _inventory(root) == before
    write_json_atomic(tmp_path / 'verification.json', {'schema': 'scienceutopia.native-workflow-objective-software-check.v1',
        'classification': 'SCRIPTED-HTTP-corpus-origin-and-prerequisite-fixtures', 'source_commit': probe.source_commit,
        'prerequisite_kind': prerequisite_kind,
        'actual_bounded_HTTP_worker_calls': len(calls), 'new_model_calls': 0, 'native_software_worlds': 7,
        'annual_checkpoints': 28, 'known_invalid_slots_preserved': 1, 'consumed_own_slots': 6,
        'maximum_actual_wire_utf8_bytes': max(c['wire_utf8_bytes'] for c in calls),
        'original_cold_audit_directory': str(audit_directory),
        'matching_original_cold_audit_sha256': file_sha256(audit_paths[0]),
        'matching_cost_content_sha256': cost_reports[0]['content_sha256'],
        'actual_invention_or_scientific_gain_claimed': False}, sort_keys=True)
