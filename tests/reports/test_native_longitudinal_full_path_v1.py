"""Opt-in original native/worker/cold/fixed SOFTWARE path; all HTTP is SCRIPTED.

Real component attribution, bounded subprocesses, generated-code containers,
native checkpoints and cold proofs stay real. Upstream closure/corpus/model
replies are named fixtures, never an autonomous invention or model benchmark.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace

import pytest

from scripts import run_native_longitudinal_comparison_v1 as driver
from scripts import audit_native_longitudinal_comparison_v1 as auditor
from scripts import run_native_longitudinal_fixed_evaluation_v1 as fixed
from scripts import audit_native_longitudinal_fixed_evaluation_v1 as fixed_auditor
from scripts import run_native_objective_fixed_evaluation_v1 as common_fixed
from scripts.analyze_native_open_v7 import _inventory
from scripts.native_benchmark_seed_usage import usage_inventory
from scripts.reports.pre_scale_costs_v1 import analyze as costs
from tests.reports.test_native_planning_objective_loop_v1 import plan, seal
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.reports.native_workflow_prerequisite_fixture_v2 import scripted_predecessor
from tests.reports.native_open_workflow_fixture_v1 import authored_program
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory, SCIENTIST_DIGEST
from utopia.optimization.native_longitudinal_feedback_v1 import KEY, VIEW
from utopia.optimization.native_scientist_transport_v1 import contract as scientist_transport_contract
from utopia.optimization.common_content_observer import make_contract
from utopia.runtime.bounded_process import run_bounded
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


def test_actual_native_access_worker_certificate_cold_costs_and_fixed_handoff(tmp_path, fixed_corpus, monkeypatch):
    declared = os.environ.get('SCIENCE_UTOPIA_WORKFLOW_PLAN')
    if declared is None:
        pytest.skip('opt-in original staged plan/component-bank evidence required')
    bank_source = driver.read(declared)
    original, _, _, _ = plan(tmp_path/'inputs', monkeypatch, IMAGE)
    install_scripted_provider(tmp_path/'provider', monkeypatch, 2)
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
    probe = LocalQwenNativeFactory(tmp_path/'probe', tmp_path/'cache', years=4, corpus_years=4)
    for key in ('model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'runtime_seed_binding', 'source_commit'):
        original['world'][key] = clone(getattr(probe, key))
        if key in original['scientist']: original['scientist'][key] = clone(getattr(probe, key))
        if key in ('corpus_sha256', 'dataset_identity'): original['designer'][key] = clone(getattr(probe, key))
    original['source_commit'] = probe.source_commit; original['data_cache'] = str(tmp_path/'cache')
    observer_backend = {k: original['scientist'][k] for k in ('model', 'model_digest')}
    observer_backend['ollama_version'] = 'SCRIPTED'
    original['observer_contract'] = make_contract(source_commit=probe.source_commit,
        provider={k: original['scientist'][k] for k in ('model', 'model_digest')},
        backend=observer_backend, maximum_posts=1500, critics=3)
    original['world']['measurement_adapter_contract'] = clone(original['observer_contract']); seal(original)
    upstream = seal({'schema': 'scienceutopia.native-planning-objective-loop-audit.v1',
        'source_commit': probe.source_commit, 'SCRIPTED': 'upstream closure is an explicit fixture'})
    prerequisite = driver.base.prerequisite_binding(scripted_predecessor(tmp_path/'SCRIPTED-predecessor'))
    backend = {k: original['designer'][k] for k in ('model', 'model_digest')}; backend['ollama_version'] = 'SCRIPTED'
    # Do not consume the scientific reserved unused seed in a software fixture.
    monkeypatch.setattr(driver, 'RESERVED_UNUSED_SEED', 72101)
    p = driver.build_plan(original, upstream, source=probe.source_commit, origin={'SCRIPTED': 'upstream fixture'},
        backend=backend, observer_backend=observer_backend, prerequisite=prerequisite,
        declaration=driver.source_scope(driver.ROOT, source_commit=probe.source_commit),
        component_bank=bank_source['component_bank'], component_evidence=bank_source['component_evidence'],
        scientist_transport=scientist_transport_contract(read_seconds=900))
    root = tmp_path/'development'; root.mkdir(); driver.save(root/'plan.json', p)
    monkeypatch.setattr(driver.base, 'origin_evidence', lambda origin: (original, upstream))
    real_factory = LocalRoleBoundNativeFactory.__call__
    def factory(self, *args, **kw):
        sim = real_factory(self, *args, **kw); sim.llm.sim = sim
        sim.llm.client.max_retries = 0
        sim.llm.client.base_url = 'http://127.0.0.1:11434/v1'
        sim.llm.client.timeout = 120
        return sim
    monkeypatch.setattr(LocalRoleBoundNativeFactory, '__call__', factory)
    class Critics:
        @contextmanager
        def lease(self, contract): yield self
        def __call__(self, wire, timeout):
            return {'http_status': 200, 'raw_http_response': json.dumps({'model': json.loads(wire)['model'],
                'done': True, 'done_reason': 'stop', 'prompt_eval_count': 71, 'eval_count': 9,
                'message': {'content': json.dumps({'score': 4, 'rationale': 'SCRIPTED software critic'})}})}
    monkeypatch.setattr(driver, 'LocalObserverBackend', lambda **kw: Critics())
    monkeypatch.setattr(common_fixed, 'LocalObserverBackend', lambda **kw: Critics())
    child_path = tmp_path/'child-http'; child_path.mkdir()
    shutil.copyfile(driver.ROOT/'tests/fixtures/native_workflow_staged_http_sitecustomize.py', child_path/'sitecustomize.py')
    calls = []
    def child(argv, **kwargs):
        intent = driver.read(argv[-2]); req, purpose = intent['request'], intent['kind']
        mode = req[VIEW]['access_contract']['mode']
        source = next(n['parameters']['code_artifact']['source'] for n in req['parent_system']['mechanisms']
            if n['mechanism_id'] == 'world.selection')
        invalid = (mode == 'parent-trajectory' and req['generation'] == 1
            and req['loss_spec']['id'] == original['losses']['content-utility']['id'])
        operations = authored_program(req)['operations']
        if invalid:
            index = next(i for i, s in enumerate(req['parent_system']['schedules']) if s['mechanism_id'] == 'world.costs')
            operations = [{'op': 'replace', 'path': '/schedules/'+str(index)+'/phase', 'value': 999}]
        write = lambda value: {'tool': 'write_file', 'filename': 'code/world.selection.py', 'content': value}
        actions = [{'tool': 'plan', 'objective_reasoning': 'SCRIPTED interface proof, not optimization',
            'design_intent': 'Exercise additional trace access and literal code/graph execution'},
            write("def step(context):\n    raise TypeError('SCRIPTED-longitudinal-probe')\n"), write(source),
            {'tool': 'edit', 'operations': operations}]
        actions += [{'tool': 'finish', 'rationale': 'SCRIPTED explicit finish'}]*(12 if invalid else 1)
        fixture = tmp_path/('child-http-'+str(len(calls))+'.json')
        write_json_atomic(fixture, {'provider': p['designer'], 'purpose': purpose, 'actions': actions})
        execution = run_bounded(argv, **kwargs, env={**os.environ, 'PYTHONPATH': str(child_path),
            'SCIENCE_UTOPIA_STAGED_WORKFLOW_HTTP_FIXTURE': str(fixture)})
        wires = [driver.read(path) for path in sorted((Path(argv[-2]).parent/'wire').glob('dispatch-*.intent.json'))]
        calls.append({'purpose': purpose, 'request': clone(req), 'mode': mode, 'posts': len(wires),
            'maximum_wire_bytes': max((len(w['wire_utf8'].encode()) for w in wires), default=0),
            'payloads': [json.loads(w['wire_utf8']) for w in wires]})
        return execution
    from utopia.optimization import native_bounded_staged_designer
    monkeypatch.setattr(native_bounded_staged_designer, 'run_bounded', child)
    p = driver.require_plan(root); driver.run(root)
    terminal = driver.read(root/'terminal.json')
    assert terminal['status'] == 'closed' and terminal['consumed_slots'] == 12 and terminal['observations'] == 13
    assert len(calls) == 25 and sum(c['purpose'] == 'proposal' for c in calls) == 12
    proposals = [c for c in calls if c['purpose'] == 'proposal']
    for call in proposals:
        req = call['request']; view = req[VIEW]
        assert all(pair['suggestion']['suggestion_id'] != 'workflow-reference-post-funding-cost' for pair in req['observations'])
        assert 'SCRIPTED-longitudinal-probe' in json.dumps(call['payloads'][2])
        if call['mode'] == 'scalar':
            assert view['active_parent'] == view['archive_items'] == []
            assert KEY not in json.dumps(req)
        else:
            assert len(view['active_parent']) == 1
            assert len(view['archive_items']) >= 1
            assert all(e['observation_id'] == req['based_on_observation_id'] for e in view['active_parent'])
    g2 = next(c for c in proposals if c['mode'] == 'parent-trajectory' and c['request']['generation'] == 2
        and c['request']['loss_spec']['id'] == original['losses']['content-utility']['id'])
    assert len(g2['request']['history']) == 2
    assert sum(bool(r['generation_error']) for r in g2['request']['history']) == 1
    # Every real stored observation keeps the trace even for the baseline arm.
    for key in driver.history_keys(p):
        c = driver.campaign(root, p, key, driver.read(root/'developer-reference-context.json'))
        for record in c.state['records']:
            for observation in record['observations']:
                if observation and observation['status'] == 'complete':
                    assert KEY in observation['metadata']['measurements'][0]
    external = Path(tempfile.mkdtemp(prefix='science-utopia-longitudinal-cold-', dir='/private/tmp'))
    audits = [external/'audit-one.json', external/'audit-two.json']; before = _inventory(root)
    for path in audits: auditor.worker(root, path)
    assert audits[0].read_bytes() == audits[1].read_bytes()
    a = driver.read(audits[0]); assert len(a['worlds']) == 13
    # An actual container wall-time failure is a charged unavailable world,
    # not a reason to refill it or weaken the physical/time guard. Require
    # successful repeated worlds in every history, not impossible immunity
    # to host/container timing. Other failure types still fail this fixture.
    complete = [w for w in a['worlds'] if w['status'] == 'complete']
    failed = [w for w in a['worlds'] if w['status'] == 'failed']
    assert len(complete) + len(failed) == 13
    assert all(len(w['physical_proof']['annual_checkpoints']) == 4 for w in complete)
    for arm, objective in driver.history_keys(p):
        assert sum(w['arm'] == arm and w['objective'] == objective
            for w in complete if w['role'] == 'workflow-own-proposal') >= 2
    for w in failed:
        assert all(value is None for value in w['scores'].values())
        key = (w['arm'], w['objective']); c = driver.campaign(root, p, key, driver.read(root/'developer-reference-context.json'))
        o = next(o for r in c.state['records'] for o in r['observations'] if o and o['suggestion_id'] == w['identity'])
        assert o['metadata']['measurements'] == []
        assert [(e['error_type'], e['error']) for e in o['metadata']['technical_failures']] == [
            ('CodeExecutionError', 'container wall-time limit exceeded')]
    values = [costs(root, p, driver.read(path)) for path in audits]
    assert values[0] == values[1]
    readiness = sum(c['posts'] for c in calls if c['purpose'] == 'calibration')
    proposal_posts = sum(c['posts'] for c in proposals)
    assert values[0]['auxiliary']['groups']['editor-readiness']['recorded_POST_attempt'] == readiness
    assert values[0]['auxiliary']['groups']['staged-proposal']['recorded_POST_attempt'] == proposal_posts
    from scripts.reports.native_instruction_timing_v1 import completed_pairs
    first_inputs = []
    for arm in driver.ARMS:
        own = next(w for w in a['worlds'] if w['role'] == 'workflow-own-proposal'
            and w['arm'] == arm and w['objective'] == 'throughput')
        cell = driver.history_directory(root, (arm, 'throughput'))/'worlds'/(own['identity']+'-s61001')
        wires, _ = completed_pairs(cell); first_inputs.append([w['payload'] for w in wires])
    assert first_inputs[0] == first_inputs[1]  # Same prescribed policy, different opaque arm identities.
    assert _inventory(root) == before
    origin = {'run': str(root), 'source': str(driver.ROOT), 'source_commit': p['source_commit'],
        'audit_files': {str(path): file_sha256(path) for path in audits}}
    old, cold = fixed.origin_evidence(origin)
    usages = [usage_inventory(root, [72101])]
    frozen = fixed.build_plan(old, cold, source=p['source_commit'], origin=origin, usages=usages, seeds=[72101],
        observer_backend=p['observer_contract']['backend'], source_proof=driver.base.native_sources(p['source_commit']))
    evaluation = tmp_path/'evaluation'; evaluation.mkdir()
    for i, u in enumerate(usages): fixed.save(evaluation/f'seed-usage-{i:02}.json', {k: v for k, v in u.items() if k != 'content_sha256'})
    fixed.save(evaluation/'plan.json', frozen); fixed.run(evaluation)
    assert fixed.read(evaluation/'terminal.json')['completed_jobs'] == len(frozen['jobs'])
    fixed_audits = [external/'fixed-one.json', external/'fixed-two.json']
    for path in fixed_audits: fixed_auditor.worker(evaluation, path)
    assert fixed_audits[0].read_bytes() == fixed_audits[1].read_bytes()
    f = fixed.read(fixed_audits[0]); assert f['fixed_selection'] == a['selection']
    fixed_costs = [costs(evaluation, fixed.read(evaluation/'plan.json'), fixed.read(path)) for path in fixed_audits]
    assert fixed_costs[0] == fixed_costs[1]
    assert not any(e['kind'] in ('editor-readiness', 'staged-proposal') for e in fixed_costs[0]['auxiliary']['events'])
    from scripts.finish_native_institution_loop_v1 import same_files
    from scripts.reports.native_workflow_objective_loop_v1 import export as development_report
    from scripts.reports.native_longitudinal_fixed_evaluation_v1 import export as fixed_report
    from scripts.reports.native_observed_request_classes_v1 import export as request_report
    from scripts.reports.native_institution_effect_trace_v1 import export as effect_report
    from scripts.reports.native_planning_choice_trace_v1 import export as choice_report
    readouts = {}
    for stage, raw, pair in (('development',root,audits),('fixed',evaluation,fixed_audits)):
        for name, exporter, extra in (
                ('scores',development_report if stage=='development' else fixed_report,{}),
                ('requests',request_report,{}),
                ('effects',effect_report,{'frozen_source':driver.ROOT,'scope':
                    'longitudinal-objective-development' if stage=='development' else 'longitudinal-fixed-evaluation'}),
                ('choices',choice_report,{'frozen_source':driver.ROOT,'study':
                    'longitudinal-development' if stage=='development' else 'longitudinal-fixed-evaluation'})):
            for i in (1,2):
                exporter(SimpleNamespace(run=raw,audit_one=pair[0],audit_two=pair[1],
                    output=external/(stage+'-'+name+'-'+str(i)),**extra))
            readouts[stage+'-'+name] = same_files(external/(stage+'-'+name+'-1'),external/(stage+'-'+name+'-2'))
    final_scores = fixed.read(external/'fixed-scores-1/report.json')
    assert len(final_scores['logical_rows']) == 6 and len(final_scores['paired_differences']) == 8
    assert len(final_scores['objective_choice_differences']) == len(final_scores['information_access_differences']) == 2
    write_json_atomic(tmp_path/'verification.json', {
        'schema': 'scienceutopia.native-longitudinal-full-path-software.v1',
        'classification': 'SCRIPTED-HTTP-corpus-and-upstream-closure-not-real-model-or-scientific-comparison',
        'source_commit': p['source_commit'], 'development_native_worlds': 13, 'own_slots': 12,
        'development_annual_checkpoints': sum(len(w['physical_proof']['annual_checkpoints']) for w in a['worlds']),
        'completed_development_native_worlds': len(complete), 'native_timeout_failures_preserved': len(failed),
        'known_invalid_slot_preserved': 1,
        'fixed_native_worlds': len(frozen['jobs']), 'fixed_fixture_seed': 72101,
        'scientific_reserved_seed_used': False, 'actual_bounded_sessions': len(calls),
        'scripted_readiness_posts': readiness, 'scripted_proposal_posts': proposal_posts,
        'maximum_actual_wire_bytes': max(c['maximum_wire_bytes'] for c in calls),
        'scalar_archive_embargo_checked': True, 'next_feedback_bearing_trace_request_checked': True,
        'same_policy_full_scientist_payloads_equal_across_arm_ids': True,
        'development_run': str(root), 'fixed_run': str(evaluation), 'audit_directory': str(external),
        'development_audit_sha256': file_sha256(audits[0]), 'fixed_audit_sha256': file_sha256(fixed_audits[0]),
        'development_cost_content_sha256': values[0]['content_sha256'],
        'fixed_cost_content_sha256': fixed_costs[0]['content_sha256'],
        'paired_readout_files': readouts,
        'new_model_calls': 0, 'real_backend_readiness_proved': False, 'scientific_gain_claimed': False,
        'publication_ready': False}, sort_keys=True)
