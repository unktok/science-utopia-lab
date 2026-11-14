"""SCRIPTED transport/real compiler tests, not actual designer evidence."""
import json

import pytest

from scripts import diagnose_native_workflow_output_modes_v1 as assay
from tests.optimization.test_native_workflow_designer_v1 import install, control
from tests.optimization.test_native_workflow_submission_v1 import request
from utopia.optimization import native_workflow_designer_v1 as original
from utopia.optimization.native_numeric_designer import save
from utopia.optimization.native_workflow_submission_v1 import control_submission
from utopia.system.design_patch import clone, digest


def identity(body):
    return {'phase_updates': {}, 'remove_connections': [], 'add_connections': [],
        'rationale': 'SCRIPTED explicit retention; no real invention claim'}


def setup(tmp_path, monkeypatch, extra):
    for k, v in assay.ENVIRONMENT.items(): monkeypatch.setenv(k, v)
    monkeypatch.setattr(assay, 'pinned_revision', lambda root: 'a' * 40)
    req = request(tmp_path / 'campaign'); bad = control_submission(req)
    bad['add_connections'] *= 2
    author, calls = install(tmp_path / 'historical', monkeypatch, [control, bad, bad, *extra])
    cert = author.calibrate(req)
    failed = author.execute(req, purpose='proposal', certificate=cert)
    history = clone(req); history['generation'] += 1
    history['history'] = [{'request_sha256': digest(req),
        'generation_error': {'type': 'ValueError', 'message': 'SCRIPTED known invalid graph'},
        'definition': original.generation_definition(failed)}]
    assert author.execute(history, purpose='calibration')['status'] == 'failed'
    frame = author.directory / ('calibration-' + digest(history))
    proposal = author.directory / ('proposal-' + digest(req))
    monkeypatch.setattr(assay, 'run_bounded', original.run_bounded)
    root = tmp_path / 'assay'; root.mkdir()
    save(root / 'plan.json', assay.make_plan(frame, proposal, 'a' * 40))
    return root, calls, bad


def test_three_exact_modes_one_free_proposal_actual_worker_cold_replay(tmp_path, monkeypatch):
    root, calls, _ = setup(tmp_path, monkeypatch, [control, control, control, identity])
    plan = assay.read(root / 'plan.json')
    result = assay.run(root)
    assert result['status'] == 'closed-technical-assay-only'
    assert result['selected_mode'] == 'schema-thinking'
    assert result['free_proposal_status'] == 'submitted'
    assert result['fresh_model_calls_upper_bound'] == 4 and len(calls) == 7
    assert result['new_scientist_worlds'] == 0
    base = plan['frames']['calibration']['intent']['payload']
    for arm, payload in zip(assay.ARMS, calls[3:6]):
        assert payload == assay.changed_payload(plan['frames']['calibration'], arm)
        assert {k: v for k, v in payload.items() if k not in ('format', 'think')} == {
            k: v for k, v in base.items() if k not in ('format', 'think')}
        intent = assay.read(root / arm / 'call.intent.json')
        raw = assay.read(root / arm / 'call.http.json')
        assert raw['transport']['request_wire_utf8'] == intent['request_wire']['request_wire_utf8']
    assert calls[4]['format'] == 'json' and calls[4]['think'] is True
    assert isinstance(calls[3]['format'], dict) and calls[3]['think'] is False
    assert calls[6] == assay.changed_payload(plan['frames']['proposal'], 'schema-thinking')
    assert assay.replay(root) == result and len(calls) == 7
    with pytest.raises(ValueError, match='already attempted'): assay.run(root)
    assert len(calls) == 7


def test_all_known_graph_failures_close_without_free_call_or_repair(tmp_path, monkeypatch):
    root, calls, bad = setup(tmp_path, monkeypatch, [lambda b: {'rationality': 'SCRIPTED wrong key'}] * 3)
    result = assay.run(root)
    assert result['status'] == 'closed-technical-assay-only'
    assert result['selected_mode'] is None and result['fresh_model_calls_upper_bound'] == 3
    assert len(calls) == 6 and not (root / 'free-proposal').exists()
    for arm in assay.ARMS:
        r = assay.read(root / arm / 'result.json')
        assert r['literal_submission'] == {'rationality': 'SCRIPTED wrong key'}
        assert r['definition'] is None and not r['completion_unknown']
    assert assay.replay(root) == result


def test_unknown_http200_stops_all_remaining_arms_and_never_resumes(tmp_path, monkeypatch):
    root, calls, _ = setup(tmp_path, monkeypatch, [{'_envelope_override': {'done': False}}])
    result = assay.run(root)
    assert result['status'] == 'stopped-completion-unknown'
    assert result['fresh_model_calls_upper_bound'] == 1 and len(calls) == 4
    assert not (root / assay.ARMS[1]).exists() and result['selected_mode'] is None
    assert assay.replay(root) == result
    with pytest.raises(ValueError, match='already attempted'): assay.run(root)
    assert len(calls) == 4


def test_bounded_worker_unknown_stops_before_second_post(tmp_path, monkeypatch):
    root, calls, _ = setup(tmp_path, monkeypatch, [])
    monkeypatch.setattr(assay, 'run_bounded', lambda *a, **k: {'timed_out': True, 'returncode': -15})
    result = assay.run(root)
    assert result['status'] == 'stopped-completion-unknown' and len(calls) == 3
    assert assay.replay(root) == result


def test_known_length_failure_does_not_salvage_but_allows_other_arms(tmp_path, monkeypatch):
    root, calls, _ = setup(tmp_path, monkeypatch,
        [{'_envelope_override': {'done_reason': 'length'}}, control,
         lambda b: {'rationality': 'wrong'}, lambda b: {'rationality': 'still wrong'}])
    result = assay.run(root)
    assert result['selected_mode'] == 'json-thinking' and result['free_proposal_status'] == 'failed'
    assert len(calls) == 7 and assay.replay(root) == result
    first = assay.read(root / assay.ARMS[0] / 'result.json')
    assert first['literal_submission'] is None and first['provider_evidence']['done_reason'] == 'length'
    assert not first['completion_unknown']


def test_unsupported_schema_http_error_is_retained_without_fallback(tmp_path, monkeypatch):
    import requests
    root, calls, _ = setup(tmp_path, monkeypatch, [control, control, control, identity])
    previous = requests.Session.post
    def post(self, url, **kw):
        response = previous(self, url, **kw)
        if isinstance(json.loads(kw['data'])['format'], dict):
            response.status_code = 400
            response.text = '{"error":"SCRIPTED schema unsupported"}'
            def fail(): raise requests.HTTPError('SCRIPTED HTTP400 schema unsupported')
            response.raise_for_status = fail
        return response
    monkeypatch.setattr(requests.Session, 'post', post)
    result = assay.run(root)
    assert result['selected_mode'] == 'json-thinking'
    assert len(calls) == 7 and assay.replay(root) == result
    raw = assay.read(root / assay.ARMS[0] / 'call.http.json')
    assert raw['transport']['http_status'] == 400 and raw['error']['type'] == 'HTTPError'
    assert raw['transport']['raw_http_response'] == '{"error":"SCRIPTED schema unsupported"}'


def test_partial_attempt_without_terminal_cannot_resume(tmp_path, monkeypatch):
    root, calls, _ = setup(tmp_path, monkeypatch, [])
    save(root / 'started.json', {'plan_sha256': assay.read(root / 'plan.json')['content_sha256']})
    with pytest.raises(ValueError, match='already attempted'): assay.run(root)
    with pytest.raises(FileNotFoundError): assay.replay(root)
    assert len(calls) == 3


def test_changed_historical_bytes_block_before_dispatch(tmp_path, monkeypatch):
    root, calls, _ = setup(tmp_path, monkeypatch, [])
    plan = assay.read(root / 'plan.json')
    path = root.parent / 'historical' / ('calibration-' + digest(plan['frames']['calibration']['binding']['request'])) / 'call.http.json'
    path.write_bytes(path.read_bytes() + b'\n')  # Deliberate fixture mutation only.
    with pytest.raises(ValueError, match='receipt differs'): assay.run(root)
    assert len(calls) == 3 and not (root / 'started.json').exists()


def test_resealed_literal_tampering_still_fails_public_replay(tmp_path, monkeypatch):
    root, calls, _ = setup(tmp_path, monkeypatch, [control, control, control, identity])
    assay.run(root)
    path = root / assay.ARMS[0] / 'call.http.json'; raw = json.loads(path.read_text())
    raw['literal_submission']['rationale'] = 'SCRIPTED tampered after receiving'
    raw['content_sha256'] = digest({k: v for k, v in raw.items() if k != 'content_sha256'})
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match='literal submission differs'): assay.replay(root)
    assert len(calls) == 7
