"""Continue closed SCRIPTED a2 at its unchanged source, never redo own slots.

The original pytest failure stays failed. This separately verifies its
unreached cost/frozen-evaluation/readout path, including the exact native null.
"""
from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from scripts import run_native_longitudinal_comparison_v1 as driver
from scripts import run_native_longitudinal_fixed_evaluation_v1 as fixed
from scripts import audit_native_longitudinal_fixed_evaluation_v1 as fixed_auditor
from scripts import run_native_objective_fixed_evaluation_v1 as common_fixed
from scripts.analyze_native_open_v7 import _inventory
from scripts.native_benchmark_seed_usage import usage_inventory
from scripts.reports.pre_scale_costs_v1 import analyze as costs
from utopia.optimization.native_loaded_roles_v38 import LocalRoleBoundNativeFactory, SCIENTIST_DIGEST
from utopia.optimization.native_bounded_staged_designer import replay as replay_author
from utopia.utils.data_utils import file_sha256, write_json_atomic

RAW = driver.ROOT/'outputs/native-longitudinal-full-path-v1-a2/tmp/test_actual_native_access_work0/development'
COLD = Path('/private/tmp/science-utopia-longitudinal-cold-ledtg_yh')
SOURCE = '85520c4dac89c33a9c5f41bc7407737a7af83500'


def test_closed_original_a2_costs_fixed_handoff_and_all_double_readouts(tmp_path, fixed_corpus, monkeypatch):
    from utopia.optimization.native_jobs import pinned_revision
    assert pinned_revision(driver.ROOT) == SOURCE
    before = _inventory(RAW)
    audits = [COLD/'audit-one.json', COLD/'audit-two.json']
    assert audits[0].read_bytes() == audits[1].read_bytes()
    p, a = driver.read(RAW/'plan.json'), driver.read(audits[0])
    assert p['source_commit'] == a['source_commit'] == SOURCE
    assert driver.read(RAW/'terminal.json')['consumed_slots'] == 12
    assert len(a['worlds']) == 13
    complete = [w for w in a['worlds'] if w['status'] == 'complete']
    failed = [w for w in a['worlds'] if w['status'] == 'failed']
    assert len(complete) == 12 and len(failed) == 1
    assert all(len(w['physical_proof']['annual_checkpoints']) == 4 for w in complete)
    context = driver.read(RAW/'developer-reference-context.json')
    for arm, objective in driver.history_keys(p):
        c = driver.campaign(RAW, p, (arm, objective), context)
        assert len(c.state['records']) == 3 and c.state['pending'] is None
        attempts = [w for w in a['worlds'] if w.get('arm') == arm and w.get('objective') == objective]
        # The deliberate generation null consumes one of this history's slots.
        assert len(attempts) == (2 if (arm, objective) == ('parent-trajectory', 'content-utility') else 3)
        assert any(w['status'] == 'complete' for w in attempts)
    w = failed[0]
    assert (w['arm'], w['objective']) == ('parent-trajectory', 'content-utility')
    c = driver.campaign(RAW, p, (w['arm'], w['objective']), context)
    o = next(o for r in c.state['records'] for o in r['observations'] if o and o['suggestion_id'] == w['identity'])
    assert o['metadata']['measurements'] == [] and all(x is None for x in w['scores'].values())
    assert [(e['error_type'], e['error']) for e in o['metadata']['technical_failures']] == [
        ('CodeExecutionError', 'container wall-time limit exceeded')]
    sessions = []
    for path in RAW.rglob('intent.json'):
        d = json.loads(path.read_text())
        if d.get('schema') == 'scienceutopia.bounded-staged-designer.v1.intent':
            replay_author(path.parent)
            wires = sorted((path.parent/'wire').glob('dispatch-*.intent.json'))
            sessions.append((d, wires))
    assert len(sessions) == 25
    readiness = sum(len(ws) for d, ws in sessions if d['kind'] == 'calibration')
    proposal_posts = sum(len(ws) for d, ws in sessions if d['kind'] == 'proposal')
    values = [costs(RAW, p, driver.read(path)) for path in audits]
    assert values[0] == values[1]
    assert values[0]['auxiliary']['groups']['editor-readiness']['recorded_POST_attempt'] == readiness
    assert values[0]['auxiliary']['groups']['staged-proposal']['recorded_POST_attempt'] == proposal_posts
    from scripts.reports.native_instruction_timing_v1 import completed_pairs
    full_inputs = []
    for arm in driver.ARMS:
        own = next(w for w in a['worlds'] if w['role'] == 'workflow-own-proposal'
            and w['arm'] == arm and w['objective'] == 'throughput')
        cell = driver.history_directory(RAW, (arm, 'throughput'))/'worlds'/(own['identity']+'-s61001')
        wires, _ = completed_pairs(cell)
        full_inputs.append([v['payload'] for v in wires])
    assert full_inputs[0] == full_inputs[1]

    # Same named SCRIPTED HTTP/corpus fixtures as the closed first phase.
    install_scripted_provider(tmp_path/'provider', monkeypatch, 2)
    monkeypatch.setattr('requests.get', lambda *args, **kw: SimpleNamespace(
        raise_for_status=lambda: None, json=lambda: {'models': [{'name': 'qwen3:8b', 'digest': SCIENTIST_DIGEST}]}))
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
    monkeypatch.setattr(common_fixed, 'LocalObserverBackend', lambda **kw: Critics())
    origin = {'run': str(RAW), 'source': str(driver.ROOT), 'source_commit': SOURCE,
        'audit_files': {str(path): file_sha256(path) for path in audits}}
    old, cold = fixed.origin_evidence(origin)
    usages = [usage_inventory(RAW, [72101])]
    frozen = fixed.build_plan(old, cold, source=SOURCE, origin=origin, usages=usages, seeds=[72101],
        observer_backend=p['observer_contract']['backend'], source_proof=driver.base.native_sources(SOURCE))
    evaluation = tmp_path/'evaluation'; evaluation.mkdir()
    for i, u in enumerate(usages):
        fixed.save(evaluation/f'seed-usage-{i:02}.json', {k: v for k, v in u.items() if k != 'content_sha256'})
    fixed.save(evaluation/'plan.json', frozen)
    fixed.run(evaluation)
    assert fixed.read(evaluation/'terminal.json')['completed_jobs'] == len(frozen['jobs'])
    fixed_audits = [tmp_path/'fixed-one.json', tmp_path/'fixed-two.json']
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
    for stage, raw, pair in (('development', RAW, audits), ('fixed', evaluation, fixed_audits)):
        for name, exporter, extra in (
                ('scores', development_report if stage == 'development' else fixed_report, {}),
                ('requests', request_report, {}),
                ('effects', effect_report, {'frozen_source': driver.ROOT, 'scope':
                    'longitudinal-objective-development' if stage == 'development' else 'longitudinal-fixed-evaluation'}),
                ('choices', choice_report, {'frozen_source': driver.ROOT, 'study':
                    'longitudinal-development' if stage == 'development' else 'longitudinal-fixed-evaluation'})):
            for i in (1, 2):
                exporter(SimpleNamespace(run=raw, audit_one=pair[0], audit_two=pair[1],
                    output=tmp_path/(stage+'-'+name+'-'+str(i)), **extra))
            readouts[stage+'-'+name] = same_files(tmp_path/(stage+'-'+name+'-1'), tmp_path/(stage+'-'+name+'-2'))
    scores = fixed.read(tmp_path/'fixed-scores-1/report.json')
    assert len(scores['logical_rows']) == 6 and len(scores['paired_differences']) == 8
    assert len(scores['objective_choice_differences']) == len(scores['information_access_differences']) == 2
    assert _inventory(RAW) == before
    write_json_atomic(tmp_path/'verification.json', {
        'schema': 'scienceutopia.native-longitudinal-closed-handoff-software.v1',
        'classification': 'SCRIPTED-HTTP-corpus-upstream-not-real-model-or-scientific-result',
        'source_commit': SOURCE, 'original_development_pytest_failed': True,
        'original_development_reopened_or_refilled': False,
        'development_run': str(RAW), 'development_audits': [str(p) for p in audits],
        'development_audit_sha256': file_sha256(audits[0]),
        'actual_bounded_sessions_replayed': len(sessions), 'readiness_POSTs': readiness,
        'proposal_POSTs': proposal_posts, 'own_slots': 12, 'native_development_worlds': 13,
        'complete_development_worlds': 12, 'native_timeout_nulls_preserved': 1,
        'known_invalid_generation_nulls_preserved': 1,
        'all_observed_annual_checkpoints_including_partial_failed_world': 50,
        'same_policy_full_scientist_payloads_equal_across_arm_ids': True,
        'development_cost_content_sha256': values[0]['content_sha256'],
        'fixed_run': str(evaluation), 'fixed_native_worlds': len(frozen['jobs']),
        'fixed_fixture_seed': 72101, 'scientific_reserved_seed_used': False,
        'fixed_audits': [str(p) for p in fixed_audits], 'fixed_audit_sha256': file_sha256(fixed_audits[0]),
        'fixed_cost_content_sha256': fixed_costs[0]['content_sha256'],
        'paired_readout_files': readouts, 'new_model_calls': 0,
        'real_backend_readiness_proved': False, 'scientific_gain_claimed': False,
        'publication_ready': False}, sort_keys=True)
