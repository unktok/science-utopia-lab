import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.optimization.test_native_numeric_designer import PROVIDER as ORIGINAL_PROVIDER
from tests.optimization.test_native_workflow_submission_v1 import request, contrast_submission
from tests.optimization.test_native_workflow_domain_v4 import IMAGE
from utopia.optimization import native_workflow_designer_v1 as module
from utopia.optimization.native_numeric_designer import worker, save
from utopia.optimization.native_workflow_submission_v1 import control_submission
from utopia.system.design_patch import clone, digest

PROVIDER = {**ORIGINAL_PROVIDER, 'image_id': IMAGE}
BACKEND = {'model': PROVIDER['model'], 'model_digest': PROVIDER['model_digest'], 'ollama_version': 'SCRIPTED'}


def install(directory, monkeypatch, replies):
    calls = []
    class Response:
        status_code = 200
        def __init__(self, body): self.body = body; self.text = json.dumps(body)
        def json(self): return self.body
        def raise_for_status(self): pass
    class Session:
        def get(self, url, **kw):
            if url.endswith('/version'): return Response({'version': 'SCRIPTED'})
            assert url.endswith('/tags')
            return Response({'models': [{'name': PROVIDER['model'], 'digest': PROVIDER['model_digest']}]})
        def post(self, url, **kw):
            assert url == 'http://127.0.0.1:11434/api/chat'
            assert kw['timeout'] == (10, 900) and type(kw['data']) is bytes
            payload = json.loads(kw['data']); calls.append(payload)
            reply = replies[len(calls) - 1]
            if callable(reply): reply = reply(json.loads(payload['messages'][1]['content']))
            body = {'done': True, 'done_reason': 'stop', 'model': PROVIDER['model'],
                'prompt_eval_count': 100, 'eval_count': 20,
                'message': {'role': 'assistant', 'content': json.dumps(reply)}}
            if isinstance(reply, dict) and '_envelope_override' in reply:
                body.update(reply['_envelope_override'])
            return Response(body)
    monkeypatch.setattr('requests.Session', Session)
    # The actual production JSON HTTP worker runs in-process only in this unit
    # fixture. Bounded subprocess behavior is separately exercised; no real
    # local inference or original transport certificate is claimed here.
    def execute(argv, **kwargs):
        assert argv[1:4] == ['-m', module.WORKER, '--worker']
        assert kwargs['seconds'] == 1200
        worker(*argv[-2:])
        return {'timed_out': False, 'returncode': 0, 'elapsed_seconds': 0., 'redispatched': False}
    monkeypatch.setattr(module, 'run_bounded', execute)
    author = module.WorkflowDesigner(directory, provider=PROVIDER, backend=BACKEND,
        inference_lock=directory.parent / 'inference.lock')
    return author, calls


def control(body): return body['control_submission']


def test_actual_shared_worker_calibration_submission_cold_replay_and_no_redispatch(tmp_path, monkeypatch):
    req = request(tmp_path / 'campaign')
    author, calls = install(tmp_path / 'author', monkeypatch, [control, contrast_submission(req)])
    certificate = author.calibrate(req)
    assert module.require_certificate(certificate, request=req, provider=PROVIDER, backend=BACKEND)['passed']
    result = author.execute(req, purpose='proposal', certificate=certificate)
    assert result['status'] == 'submitted' and result['shared_raw_transport_schema'].endswith('.http')
    assert result['literal_submission'] == contrast_submission(req)
    assert module.generation_definition(result) == result['definition']
    assert author.execute(req, purpose='proposal', certificate=certificate) == result and len(calls) == 2
    root = author.directory / ('proposal-' + digest(req))
    assert module.replay_workflow(root) == result
    intent = module.checked(json.loads((root / 'call.intent.json').read_text()))
    raw = module.checked(json.loads((root / 'call.http.json').read_text()))
    assert raw['transport']['request_wire_utf8'] == intent['request_wire']['request_wire_utf8']
    assert raw['transport']['response_payload']['prompt_eval_count'] == 100


def test_legal_noncopy_calibration_is_diagnostic_not_a_veto(tmp_path, monkeypatch):
    req = request(tmp_path / 'campaign')
    changed = control_submission(req); changed['rationale'] = 'SCRIPTED valid but not a complete copy'
    author, calls = install(tmp_path / 'author', monkeypatch, [changed])
    cert = module.require_certificate(author.calibrate(req), request=req, provider=PROVIDER, backend=BACKEND)
    assert cert['passed'] and not cert['copy_equal_diagnostic'] and not cert['copy_is_dispatch_veto']
    assert len(calls) == 1


def test_known_invalid_graph_is_one_consumed_failure_not_repaired_or_replaced(tmp_path, monkeypatch):
    req = request(tmp_path / 'campaign'); bad = control_submission(req)
    bad['phase_updates']['world.costs'] = 999
    author, calls = install(tmp_path / 'author', monkeypatch, [control, bad])
    cert = author.calibrate(req); result = author.execute(req, purpose='proposal', certificate=cert)
    assert result['status'] == 'failed' and result['definition'] is None and not result['completion_unknown']
    assert result['literal_submission'] == bad and len(calls) == 2
    failure = module.generation_definition(result)['workflow_submission_failure']
    assert failure['literal_submission'] == bad and failure['error'] == result['technical_error']
    assert module.replay_workflow(author.directory / ('proposal-' + digest(req))) == result


@pytest.mark.parametrize('envelope,unknown', [({'done': False}, True), ({'done_reason': 'length'}, False)])
def test_http200_is_not_completion_or_a_valid_generation(tmp_path, monkeypatch, envelope, unknown):
    req = request(tmp_path / 'campaign')
    author, calls = install(tmp_path / 'author', monkeypatch, [{'_envelope_override': envelope}])
    if unknown:
        with pytest.raises(module.WorkflowCompletionUnknown): author.calibrate(req)
    else:
        with pytest.raises(ValueError, match='calibration failed'): author.calibrate(req)
    assert len(calls) == 1
    root = author.directory / ('calibration-' + digest(req)); result = module.replay_workflow(root)
    assert result['status'] == 'failed' and result['definition'] is None
    assert result['completion_unknown'] is unknown


def test_missing_worker_reply_stops_and_cannot_be_retried(tmp_path, monkeypatch):
    req = request(tmp_path / 'campaign'); author, calls = install(tmp_path / 'author', monkeypatch, [])
    monkeypatch.setattr(module, 'run_bounded', lambda *a, **k: {'timed_out': True, 'returncode': -15})
    for _ in range(2):
        with pytest.raises(module.WorkflowCompletionUnknown): author.calibrate(req)
    assert not calls
    assert len(list(author.directory.rglob('call.intent.json'))) == 1
    assert not list(author.directory.rglob('call.http.json'))


def test_proposal_requires_actual_exact_context_certificate_before_dispatch(tmp_path, monkeypatch):
    req = request(tmp_path / 'campaign'); author, calls = install(tmp_path / 'author', monkeypatch, [control])
    with pytest.raises(ValueError, match='certificate'):
        author.execute(req, purpose='proposal')
    assert not calls and not author.directory.exists()
    cert = author.calibrate(req); changed = clone(req); changed['generation'] += 1
    with pytest.raises(ValueError, match='mismatched'):
        author.execute(changed, purpose='proposal', certificate=cert)
    assert len(calls) == 1


def test_raw_http_tampering_cannot_be_hidden_by_resealing_journals(tmp_path, monkeypatch):
    req = request(tmp_path / 'campaign')
    author, _ = install(tmp_path / 'author', monkeypatch, [control, contrast_submission(req)])
    result = author.execute(req, purpose='proposal', certificate=author.calibrate(req))
    root = author.directory / ('proposal-' + digest(req))
    raw_path = root / 'call.http.json'; raw = json.loads(raw_path.read_text())
    raw['literal_submission']['rationale'] = 'changed after dispatch'
    raw['content_sha256'] = digest({k: v for k, v in raw.items() if k != 'content_sha256'})
    # Mutation is deliberate test input, never an operation on scientific logs.
    raw_path.write_text(json.dumps(raw))
    changed = clone(result); changed['raw_http_file_sha256'] = module.file_sha256(raw_path)
    changed['content_sha256'] = digest({k: v for k, v in changed.items() if k != 'content_sha256'})
    (root / 'result.json').write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='literal submission differs'):
        module.replay_workflow(root)
