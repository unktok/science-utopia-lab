"""Opt-in public prepare/run/cold/cost path; all HTTP and corpus are SCRIPTED.

Original five-founder worlds, sandboxed code, role journals, installed SDK,
HTTPX timeout extensions, checkpoints and cold readers remain real. Upstream
historical evidence is an explicitly named fixture, not independently proved.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace

import httpx
from openai import OpenAI
import pytest

from scripts import run_native_legacy_choice_pilot_v1 as driver
from scripts import audit_native_legacy_choice_pilot_v1 as auditor
from scripts.reports.pre_scale_costs_v1 import analyze as costs
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.reports.test_native_legacy_choice_native_v1 import ScriptedCritic
from tests.reports.test_native_longitudinal_comparison_v1 import closed, sealed
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_loaded_roles_v38 import SCIENTIST_DIGEST
from utopia.optimization.native_scientist_transport_v1 import require_cell_transport
from utopia.optimization.common_content_observer import make_contract
from utopia.system import SystemSpec
from utopia.system.native_legacy_choice_controls import PRODUCER, PROTOCOL as ADVICE
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256, write_json_atomic


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_LEGACY_CHOICE_PILOT_QA') != '1',
                    reason='opt-in clean committed-source hardware window required')
def test_public_operator_actual_sdk_profile_three_worlds_and_double_cold(tmp_path, fixed_corpus, monkeypatch):
    public_operator_path(tmp_path, monkeypatch)


def public_operator_path(tmp_path, monkeypatch, *, topic=False, terminal=False):
    base = driver
    operator, cold_reader = driver, auditor
    if topic and terminal:
        raise ValueError('one explicitly named public pilot per software check')
    if terminal:
        from scripts import run_native_terminal_cost_pilot_v1 as operator
        from scripts import audit_native_terminal_cost_pilot_v1 as cold_reader
    elif topic:
        from scripts import run_native_legacy_topic_pilot_v1 as operator
        from scripts import audit_native_legacy_topic_pilot_v1 as cold_reader
    declared = os.environ.get('SCIENCE_UTOPIA_WORKFLOW_PLAN')
    if not declared:
        pytest.skip('explicit original world/provider/observer binding required')
    original = driver.read(declared)
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

    # Keep fixture response generation but use the actual installed OpenAI
    # SDK to construct every recorded HTTP body and timeout extension.
    from utopia.models import models
    scripted_constructor = models.VLLMServerModel
    sent, clients = [], []
    def model(name, **kwargs):
        value = scripted_constructor(name, **kwargs)
        def transport(request):
            payload = json.loads(request.content)
            sent.append({'body': payload, 'timeout': clone(request.extensions['timeout']),
                'read_header': request.headers['x-stainless-read-timeout'],
                'retry_header': request.headers['x-stainless-retry-count']})
            return httpx.Response(200, json=value.reply(**payload).model_dump())
        value.client = OpenAI(api_key='SCRIPTED-not-a-real-key', base_url='http://127.0.0.1:11434/v1',
            max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(transport)))
        clients.append(value.client)
        return value
    monkeypatch.setattr(models, 'VLLMServerModel', model)
    actual = LocalQwenNativeFactory.__call__
    def construct(self, *args, **kwargs):
        sim = actual(self, *args, **kwargs); sim.llm.sim = sim
        return sim
    monkeypatch.setattr(LocalQwenNativeFactory, '__call__', construct)
    monkeypatch.setattr(driver, 'LocalObserverBackend', lambda **kwargs: ScriptedCritic())

    probe = LocalQwenNativeFactory(tmp_path / 'probe', tmp_path / 'cache', years=4, corpus_years=4)
    (tmp_path / 'cache').mkdir(parents=True, exist_ok=True)
    original = {k: deepcopy(v) for k, v in original.items() if k != 'content_sha256'}
    original['source_commit'] = probe.source_commit; original['data_cache'] = str(tmp_path / 'cache')
    for key in ('model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'runtime_seed_binding', 'source_commit'):
        original['world'][key] = clone(getattr(probe, key))
        if key in original['scientist']:
            original['scientist'][key] = clone(getattr(probe, key))
        if key in ('corpus_sha256', 'dataset_identity'):
            original['designer'][key] = clone(getattr(probe, key))
    # Use software seed42, not the scientific pilot's declared61001 or a
    # reserved unused condition. This explicit fixture does not certify seeds.
    monkeypatch.setattr(base, 'SEED', 42)
    monkeypatch.setattr(operator, 'SEED', 42)
    original['initial_system']['initial_state']['seed'] = 42
    for spec in original['reference_systems'].values(): spec['initial_state']['seed'] = 42
    backend = {k: original['scientist'][k] for k in ('model', 'model_digest')}
    backend['ollama_version'] = 'SCRIPTED'
    original['observer_contract'] = make_contract(source_commit=probe.source_commit,
        provider={k: original['scientist'][k] for k in ('model', 'model_digest')},
        backend=backend, maximum_posts=1500, critics=3)
    original = sealed(original); upstream = closed(original)
    fixed = driver.read(driver.ROOT / driver.FIXED_RECEIPT)
    origin = tmp_path / 'SCRIPTED-origin'; origin.mkdir(); (origin / 'writer.lock').touch()
    for i in (1, 2): driver.save(origin / f'audit-{i}.json', {k: v for k, v in upstream.items() if k != 'content_sha256'})
    monkeypatch.setattr(driver, 'preceding_evidence', lambda value: (original, upstream, fixed))
    source_owner = operator if topic or terminal else driver.workflow
    monkeypatch.setattr(source_owner, 'native_sources', lambda source: {'original_source': source,
        'SCRIPTED': 'upstream evidence only, actual execution source checked by cold reader'})
    monkeypatch.setattr(driver, 'backend_binding', lambda provider: clone(backend))
    root = tmp_path / 'pilot'
    operator.prepare(SimpleNamespace(output=root, origin_run=origin, origin_source=driver.ROOT,
        audit_one=origin / 'audit-1.json', audit_two=origin / 'audit-2.json'))
    operator.run(root)
    p = operator.require_plan(root); end = driver.read(root / 'terminal.json')
    count = 2 if topic or terminal else 3
    assert end['status'] == 'closed' and end['completed_jobs'] == count
    assert not end['held_out_world_seeds'] and not end['automatic_invention']
    assert sent and all(v['timeout'] == p['scientist_transport']['http_timeout_seconds'] for v in sent)
    assert all(v['read_header'] == '900' and v['retry_header'] == '0' for v in sent)
    assert all('timeout' not in v['body'] for v in sent)
    directions, advice = [], []
    for job in p['jobs']:
        cell = root / 'controls' / job['identity'] / 'worlds' / (job['identity'] + '-s42')
        require_cell_transport(cell, p, SystemSpec.from_dict(job['system']), seed=42, failed=False)
        wires = [json.loads(line) for line in (cell / 'wire-requests.jsonl').read_text().splitlines()]
        requests = [w for w in wires if w['payload'].get('response_format', {}).get('json_schema', {}).get(
            'name') == 'research_direction_selection']
        directions.append(len(requests)); advice.append(sum(ADVICE in json.dumps(w['payload']) for w in requests))
        if topic or terminal:
            assert not requests
        elif job['condition'] == 'core-assignment': assert not requests
        elif job['condition'] == 'native-choice': assert requests and not advice[-1]
        else: assert requests and advice[-1] == len(requests)
    for client in clients: client.close()
    # Both cold reads must be unable to dispatch any SDK or observer request.
    monkeypatch.setattr(OpenAI, '__init__', lambda *a, **k: pytest.fail('no SDK construction during cold audit'))
    with tempfile.TemporaryDirectory(prefix='legacy-choice-pilot-audit-') as external:
        outputs = [Path(external) / f'audit-{i}.json' for i in (1, 2)]
        for path in outputs: cold_reader.worker(root, path)
        audits = [driver.read(path) for path in outputs]
        assert outputs[0].read_bytes() == outputs[1].read_bytes()
        cost_pair = [costs(root, p, a) for a in audits]
        assert cost_pair[0] == cost_pair[1]
        assert all(w['status'] == 'complete' for w in audits[0]['worlds'])
        assert len({digest(w['physical_proof']['initial_identity']) for w in audits[0]['worlds']}) == 1
        assert all(not audits[0][k] for k in ('held_out_world_seeds', 'automatic_invention', 'policy_selection'))
        assert 'fixed_selection' not in audits[0]
        if topic or terminal:
            from utopia.optimization.native_resource_cost import METRIC, UNCOLLECTED_METRIC
            from utopia.runtime.checkpointing import read_portable_checkpoint
            from utopia.system.native_legacy_topic_planning import EVENT
            outside = []
            for index, world in enumerate(audits[0]['worlds']):
                measurement, = world['measurements']
                expected_cost = 160.0 if terminal and index == 1 else 200.0
                expected_unpaid = 40.0 if terminal and index == 1 else 0.0
                assert measurement['metrics'][METRIC] == {'status': 'measured', 'value': expected_cost}
                assert measurement['metrics'][UNCOLLECTED_METRIC] == {'status': 'measured', 'value': expected_unpaid}
                assert measurement['native_workflow_interval']['effect_witnesses'] == 48
                assignments = world['physical_proof']['native_counts']['project_assignments_verified']
                assert assignments
                checkpoint, = root.glob('controls/' + world['identity'] + '/worlds/**/portable_checkpoint_year_4.json.gz')
                state = read_portable_checkpoint(checkpoint)
                events = [e['payload'] for e in state['native_system']['events'] if e['event_type'] == EVENT]
                assert len(events) == len(assignments)
                outside.append(sum(e['assignment']['direction']['topic'] not in e['eligible_actor_before']['expertise']
                                   for e in events))
                if terminal:
                    actors = [a for a in state['ecosystem_data']['agents'] if a['can_author']]
                    assert sum(a['is_active'] for a in actors) == (1 if index else 5)
                    assert sum(a['resources'] for a in actors) == (70 if index else 30)
                    scores = world['scores']
                    assert scores['resource-aware-content'] == scores['content-utility'] + 0.1 * expected_cost
            if terminal:
                assert all(v > 0 for v in outside)
                left, right = [world['scores'] for world in audits[0]['worlds']]
                assert left['throughput'] == right['throughput']
                assert left['content-utility'] == right['content-utility']
                assert left['resource-aware-content'] - right['resource-aware-content'] == pytest.approx(4)
            else:
                assert outside[0] == 0 and outside[1] > 0
        driver.save(tmp_path / 'audit-retained.json', {k: v for k, v in audits[0].items() if k != 'content_sha256'})
        if topic or terminal:
            driver.save(tmp_path / 'audit-retained-2.json', {k: v for k, v in audits[1].items() if k != 'content_sha256'})
        driver.save(tmp_path / 'cost-retained.json', {k: v for k, v in cost_pair[0].items() if k != 'content_sha256'})
    with pytest.raises(ValueError, match='no redispatch'): operator.run(root)
    write_json_atomic(tmp_path / 'verification.json', {
        'schema': ('scienceutopia.native-terminal-cost-pilot-software.v1' if terminal else
                   'scienceutopia.native-legacy-topic-pilot-software.v1' if topic
                   else 'scienceutopia.native-legacy-choice-pilot-software.v1'),
        'classification': 'SCRIPTED-HTTP-corpus-critics-upstream-not-scientific-feasibility',
        'source_commit': probe.source_commit, 'original_plan_file_sha256': file_sha256(declared),
        'public_prepare_run_and_double_cold': True, 'worlds': count, 'annual_boundaries': 4 * count,
        'scientist_httpx_requests': len(sent), 'all_scientist_read_headers': ['900'],
        'all_scientist_retry_headers': ['0'], 'scientific_request_body_timeout_fields': 0,
        'native_direction_requests': directions, 'advice_delivered_in_direction_prompts': advice,
        **({'outside_core_project_effects': outside} if topic or terminal else {}),
        'paired_audit_content_sha256': audits[0]['content_sha256'],
        'paired_cost_content_sha256': cost_pair[0]['content_sha256'],
        'new_real_model_calls': 0, 'scientific_feasibility_or_gain_claimed': False,
        'publication_ready': False}, sort_keys=True)
    return {'run': root, 'clients': clients, 'scientist_requests': sent,
            'audit_one': tmp_path/'audit-retained.json', 'audit_two': tmp_path/'audit-retained-2.json'}
