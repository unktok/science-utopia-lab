"""Finite diagnostic mechanics, no actual backend capacity proof."""
from datetime import datetime, timezone, timedelta
import json
from types import SimpleNamespace

import pytest

from scripts import diagnose_native_longitudinal_frame_capacity_v1 as m
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import digest


def frame(arm='scalar', size=1):
    payload = {'model': 'qwen3.6:35b-mlx-64k', 'stream': False, 'think': False,
        'truncate': False, 'shift': False, 'options': {'num_ctx': 40960, 'num_predict': 8192},
        'messages': [{'role': 'user', 'content': 'literal\\n'+('x'*size)}]}
    wire = json.dumps(payload, ensure_ascii=False)
    return {'arm': arm, 'wire_utf8': wire, 'wire_sha256': digest(wire)}


def response(count=32768, reason='stop', done=True):
    return {'http_status': 200, 'raw_http_response': json.dumps({
        'model': 'qwen3.6:35b-mlx-64k', 'done': done, 'done_reason': reason,
        'prompt_eval_count': count, 'eval_count': 7, 'message': {'content': 'untrusted ignored action'}})}


@pytest.mark.parametrize('count,reason,done,expected', [
    (32768,'stop',True,True), (32769,'stop',True,False),
    (100,'length',True,False), (100,'stop',False,False), (None,'stop',True,False)])
def test_measured_reservation_and_final_stop_are_separate(count, reason, done, expected):
    r = m.result_from_http(frame(), response(count, reason, done))
    assert r['capacity_supported_for_this_literal_frame'] is expected
    assert r['capacity']['observed_prompt_eval_count'] == count
    assert not r['returned_action_executed']


def resources(root, *, ended_utc=None, **changes):
    root.mkdir()
    save(root/'started.json', {'schema': 'scienceutopia.native-feedback-resource-observation.v2', 'new_inference_POSTs': 0})
    save(root/'ended.json', {'status': 'two-observations-ready', 'new_inference_POSTs': 0,
        'ended_utc': ended_utc or datetime.now(timezone.utc).isoformat()})
    for i in (1,2):
        save(root/f'check-{i}.json', {'ready_under_declared_shared_resource_profile': True,
            'unclassified_python_or_model_executables': [], 'loaded_models': {'models': []},
            'total_host_cpu_percent': 150, 'free_plus_inactive_bytes': 40*1024**3, **changes})
    return root


def test_resource_proof_has_no_implicit_shared_hardware_lease(tmp_path):
    root = resources(tmp_path/'good')
    assert len(m.require_resources(root)) == 4
    stale = resources(tmp_path/'stale', ended_utc=(datetime.now(timezone.utc)-timedelta(seconds=121)).isoformat())
    with pytest.raises(ValueError, match='stale'): m.require_resources(stale)


@pytest.mark.parametrize('changes', [
    {'total_host_cpu_percent': 251}, {'free_plus_inactive_bytes': 37*1024**3},
    {'unclassified_python_or_model_executables': [{'pid': 123}]},
    {'loaded_models': {'models': [{'name': 'other-model'}]}}])
def test_resource_profile_not_relaxed_to_make_dispatch_pass(tmp_path, changes):
    with pytest.raises(ValueError, match='not ready'):
        m.require_resources(resources(tmp_path/'bad', **changes))


def test_real_durable_transport_journals_two_literal_frames_without_adopting_action(tmp_path, monkeypatch):
    frames = [frame(a) for a in m.ARMS]; posted = []
    p = {'provider': {'model': 'qwen3.6:35b-mlx-64k'}, 'backend': {'SCRIPTED': True}, 'frames': frames}
    monkeypatch.setattr(m, 'require_plan', lambda root: p)
    monkeypatch.setattr(m, 'backend_binding', lambda *a, **kw: p['backend'])
    monkeypatch.setattr(m, 'load_local_role', lambda *a, **kw: None)
    class Session:
        def post(self, endpoint, **kwargs):
            assert endpoint == 'http://127.0.0.1:11434/api/chat'
            assert kwargs['data'] == frames[len(posted)]['wire_utf8'].encode()
            assert kwargs['timeout'] == (10,900)
            posted.append(kwargs['data'])
            return SimpleNamespace(status_code=200, text=response()['raw_http_response'])
    monkeypatch.setattr('requests.Session', Session)
    m.worker(tmp_path)
    terminal = m.read(tmp_path/'worker-terminal.json')
    assert len(posted) == len(terminal['results']) == 2
    assert terminal['two_literal_frames_supported']
    assert not terminal['production_certificate_issued'] and not terminal['scientific_dispatch_authorized']
    assert len(list((tmp_path/'wire').glob('*.intent.json'))) == 2


def test_incomplete_provider_envelope_stops_before_second_dispatch(tmp_path, monkeypatch):
    frames = [frame(a) for a in m.ARMS]; posted = []
    p = {'provider': {}, 'backend': {}, 'frames': frames}
    monkeypatch.setattr(m, 'require_plan', lambda root: p)
    monkeypatch.setattr(m, 'backend_binding', lambda *a, **kw: {})
    monkeypatch.setattr(m, 'load_local_role', lambda *a, **kw: None)
    class Session:
        def post(self, *a, **kw):
            posted.append(kw['data'])
            return SimpleNamespace(status_code=200, text=response(done=False)['raw_http_response'])
    monkeypatch.setattr('requests.Session', Session)
    with pytest.raises(m.CompletionUnknown): m.worker(tmp_path)
    terminal = m.read(tmp_path/'worker-terminal.json')
    assert len(posted) == 1 and terminal['results'] == []
    assert terminal['completion_unknown'] and terminal['no_retry']


def test_selects_byte_largest_late_frames_not_earlier_or_favorable(tmp_path, monkeypatch):
    root = tmp_path/'raw'; root.mkdir(); source = 'a'*40
    p = save(root/'plan.json', {'designer': {'model': 'qwen3.6:35b-mlx-64k'},
        'source_commit': source, 'origin': {'SCRIPTED': 'upstream fixture'}})
    for arm in m.ARMS:
        for generation, size in [(1,1000), (2,10), (2,20)]:
            directory = root/'search'/arm/'throughput'/'authoring'/f'proposal-{generation}-{size}'/'editor-session'
            save(directory/'intent.json', {'kind': 'proposal', 'request': {'generation': generation,
                'history': [{}]*generation, 'native_longitudinal_evidence_v1': {'access_contract': {'mode': arm}}}})
            save(directory/'wire/dispatch-000.intent.json', {'wire_utf8': frame(arm,size)['wire_utf8'],
                'timeout_seconds': [10,900]})
    inventory = {'SCRIPTED': 'raw snapshot'}
    monkeypatch.setattr(m, '_inventory', lambda root: inventory)
    a = {'schema': 'scienceutopia.native-longitudinal-comparison-audit.v1',
        'plan_sha256': p['content_sha256'], 'source_commit': source,
        'source_proof': {'status': 'verified-exact-source-closure'}, 'raw_inventory_sha256': digest(inventory),
        'closure': {'terminal': {'status': 'closed', 'consumed_slots': 12}}}
    audits = [tmp_path/f'audit-{i}.json' for i in (1,2)]
    for path in audits: save(path,a)
    _, frames, _ = m.late_frames(root,audits)
    assert [r['arm'] for r in frames] == list(m.ARMS)
    assert all('proposal-2-20' in r['source_file'] and r['history_records'] == 2 for r in frames)
