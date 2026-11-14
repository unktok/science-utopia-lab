import json

import pytest

from tests.optimization.test_native_workflow_designer_v1 import install, control, PROVIDER, BACKEND
from tests.optimization.test_native_workflow_submission_v1 import request
from utopia.optimization import native_workflow_designer_v1 as module
from utopia.optimization.native_workflow_submission_v1 import control_submission
from utopia.optimization.native_workflow_domain_v4 import post_funding_cost_control
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest


def identity(body):
    return {'phase_updates': {}, 'remove_connections': [], 'add_connections': [],
        'rationale': 'SCRIPTED explicit parent retention; no merit or novelty requirement'}


def author_at(path, monkeypatch, replies):
    _, calls = install(path, monkeypatch, replies)
    return module.WorkflowDesigner(path, provider=PROVIDER, backend=BACKEND,
        inference_lock=path.parent / 'inference.lock', mode=module.FEEDBACK_MODE), calls


def history_for(req, result):
    return {'request': clone(req), 'request_sha256': digest(req),
        'generation_error': {'type': 'ValueError', 'message': 'SCRIPTED consumed null', 'loss': None},
        'definition': module.generation_definition(result)}


def test_profile_actual_worker_certificate_failed_slot_next_parent_feedback_and_replay(tmp_path, monkeypatch):
    req = request(tmp_path / 'c')
    req['parent_system'] = post_funding_cost_control(SystemSpec.from_dict(req['parent_system'])).to_dict()
    bad = control_submission(req); bad['phase_updates']['world.selection'] = 40
    author, calls = author_at(tmp_path / 'author', monkeypatch, [control, bad, control, identity])
    cert = author.calibrate(req)
    actual = module.require_certificate(cert, request=req, provider=PROVIDER, backend=BACKEND, settings=author.settings)
    assert actual['passed'] and actual['copy_is_dispatch_veto'] is False
    failed = author.execute(req, purpose='proposal', certificate=cert)
    assert failed['status'] == 'failed' and failed['literal_submission'] == bad
    next_req = clone(req); next_req['generation'] += 1
    next_req['parent_system'] = clone(req['design_space_anchor'])  # Deliberately different parent.
    next_req['history'] = [history_for(req, failed)]
    cert2 = author.calibrate(next_req)
    result = author.execute(next_req, purpose='proposal', certificate=cert2)
    assert result['status'] == 'submitted' and result['definition']['provenance']['retained_parent_explicitly']
    assert len(calls) == 4 and all(p['think'] is True and isinstance(p['format'], dict) for p in calls)
    assert all(p['options']['num_ctx'] == 57344 and p['options']['num_predict'] == 16384 for p in calls)
    body = json.loads(calls[-1]['messages'][1]['content'])
    feedback = body['consumed_proposal_compiler_feedback'][0]
    assert feedback['recorded_submission_failure']['literal_submission'] == bad
    assert [r['source_phase'] for r in feedback['compiler_feedback']['causal_order_witnesses']] == [70, 100, 110, 120]
    assert not feedback['compiler_feedback']['graph_repaired']
    assert body['context']['consumed_generation_nulls'][0]['literal_submission_failure']['literal_submission'] == bad
    for r in (req, next_req):
        for purpose in ('calibration', 'proposal'):
            root = author.directory / (purpose + '-' + digest(r))
            assert module.replay_workflow(root)['completion_unknown'] is False
    assert author.execute(next_req, purpose='proposal', certificate=cert2) == result and len(calls) == 4


def test_profile_certificate_cannot_be_used_as_legacy_or_different_request(tmp_path, monkeypatch):
    req = request(tmp_path / 'c'); author, calls = author_at(tmp_path / 'author', monkeypatch, [control])
    cert = author.calibrate(req)
    with pytest.raises(ValueError, match='mismatched'):
        module.require_certificate(cert, request=req, provider=PROVIDER, backend=BACKEND)
    changed = clone(req); changed['generation'] += 1
    with pytest.raises(ValueError, match='mismatched'):
        author.execute(changed, purpose='proposal', certificate=cert)
    assert len(calls) == 1


@pytest.mark.parametrize('literal', [None, {'phase_updates': []}, {'rationality': 'wrong'}, 9])
def test_next_prompt_keeps_malformed_or_missing_literal_without_inventing_a_graph(tmp_path, literal):
    req = request(tmp_path / 'c'); next_req = clone(req); next_req['generation'] += 1
    next_req['history'] = [{'request': clone(req), 'request_sha256': digest(req),
        'generation_error': {'type': 'ValueError', 'message': 'SCRIPTED consumed failure'},
        'definition': {'workflow_submission_failure': {'literal_submission': literal,
            'error': {'type': 'ValueError', 'message': 'SCRIPTED exact original error'}, 'journal_sha256': 'a' * 64}}}]
    p, _, _ = module._payload({'request': next_req, 'purpose': 'proposal',
        'provider': PROVIDER, 'settings': module.settings_for(module.FEEDBACK_MODE)})
    row = json.loads(p['messages'][1]['content'])['consumed_proposal_compiler_feedback'][0]
    assert row['recorded_submission_failure']['literal_submission'] == literal
    assert (row['compiler_feedback'] is None) == (literal is None)


def test_oversize_feedback_stops_before_any_worker_without_truncation(tmp_path, monkeypatch):
    req = request(tmp_path / 'c'); req['history'] = [{'request': {}, 'request_sha256': digest({}),
        'generation_error': {'message': 'SCRIPTED oversized exact error' + 'x' * 150000},
        'definition': {'workflow_submission_failure': {'literal_submission': None, 'error': None}}}]
    author, calls = author_at(tmp_path / 'author', monkeypatch, [])
    with pytest.raises(ValueError, match='wire allowance'): author.calibrate(req)
    assert not calls and not author.directory.exists()


def test_legacy_payload_uses_original_json_nonthinking_budget(tmp_path):
    p, _, _ = module._payload({'request': request(tmp_path / 'c'), 'purpose': 'proposal',
        'provider': PROVIDER, 'settings': module.SETTINGS})
    assert p['format'] == 'json' and p['think'] is False
    assert p['options']['num_ctx'] == 40960 and p['options']['num_predict'] == 8192
    assert 'consumed_proposal_compiler_feedback' not in json.loads(p['messages'][1]['content'])
