"""SCRIPTED worker/API/compiler checks, no actual model/native/Docker calls."""
import json

import pytest

from tests.optimization.test_native_workflow_designer_v1 import install, PROVIDER, BACKEND
from tests.optimization.test_native_workflow_submission_v1 import request
from tests.optimization.test_native_workflow_feedback_profile_v2 import history_for
from utopia.optimization import native_workflow_designer_v1 as engine
from utopia.optimization import native_open_workflow_submission_v1 as ir
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest


def author_at(path, monkeypatch, replies):
    _, calls = install(path, monkeypatch, replies)
    return engine.WorkflowDesigner(path, provider=PROVIDER, backend=BACKEND,
        inference_lock=path.parent / 'inference.lock', mode=engine.OPEN_IR_MODE), calls


def control(body): return body['control_submission']


def institution(req):
    # Two genuinely code-defined nodes and an explicit new protocol/wire.
    # They extend the original scientist graph, not a substituted number world.
    first = clone(ir.control_submission(req, PROVIDER)['operations'][0]['value'])
    first['mechanism_id'] = 'authored-counting-office'
    first['parameters']['step'] = 3
    first['outputs'] = [{'port_id': 'token', 'channel': 'artifact',
        'artifact_type': 'authored-ledger-token', 'required': True}]
    artifact = first['parameters']['code_artifact']
    artifact['outputs'] = {'token': {'type': 'object', 'required': ['n'],
        'properties': {'n': {'type': 'integer'}}, 'additionalProperties': False}}
    artifact['source'] = "def step(context):\n    n = context['state'].get('n', 0) + context['parameters']['step']\n    return {'outputs': {'token': [{'payload': {'n': n}}]}, 'state': {'n': n}}\n"
    second = clone(ir.control_submission(req, PROVIDER)['operations'][0]['value'])
    second['mechanism_id'] = 'authored-memory-office'
    second['inputs'] = [{'port_id': 'token', 'channel': 'artifact',
        'artifact_type': 'authored-ledger-token', 'required': True}]
    second['parameters']['code_artifact']['inputs'] = clone(artifact['outputs'])
    second['parameters']['code_artifact']['source'] = "def step(context):\n    value = context['inputs']['token'][0]['payload']['n']\n    return {'outputs': {}, 'state': {'observed': value}}\n"
    operations = [{'op': 'add', 'path': '/artifact_types/-',
        'value': {'artifact_type_id': 'authored-ledger-token', 'description': 'SCRIPTED novel institution protocol'}}]
    for phase, node in [(193, first), (194, second)]:
        operations += [{'op': 'add', 'path': '/mechanisms/-', 'value': node},
            {'op': 'add', 'path': '/schedules/-', 'value': {
                'mechanism_id': node['mechanism_id'], 'phase': phase, 'trigger': 'annual'}}]
    operations.append({'op': 'add', 'path': '/connections/-', 'value': {
        'source_mechanism': first['mechanism_id'], 'source_port': 'token',
        'target_mechanism': second['mechanism_id'], 'target_port': 'token',
        'channel': 'artifact', 'latency': 0}})
    return {'operations': operations, 'factors': [], 'continuous': [],
        'rationale': 'SCRIPTED arbitrary two-office design; no scientific gain is claimed'}


def test_actual_worker_certificate_arbitrary_source_nodes_protocol_wire_and_cold_replay(tmp_path, monkeypatch):
    req = request(tmp_path / 'campaign'); literal = institution(req)
    author, calls = author_at(tmp_path / 'author', monkeypatch, [control, literal])
    certificate = author.calibrate(req)
    result = author.execute(req, purpose='proposal', certificate=certificate)
    assert result['status'] == 'submitted' and result['literal_submission'] == literal
    parent = SystemSpec.from_dict(req['parent_system'])
    compiled = GeneratedMixedDesign(parent, result['definition'], loss_spec=req['loss_spec'],
        seed=42, single_draw_blackbox=True).base
    assert len(compiled.mechanisms) == len(parent.mechanisms) + 2
    assert len(compiled.connections) == len(parent.connections) + 1
    assert compiled.initial_state == parent.initial_state
    node = next(n for n in compiled.mechanisms if n.mechanism_id == 'authored-counting-office')
    assert node.parameters['code_artifact']['source'] == literal['operations'][1]['value']['parameters']['code_artifact']['source']
    assert all(p['think'] and isinstance(p['format'], dict) for p in calls)
    for purpose in ('calibration', 'proposal'):
        assert engine.replay_workflow(author.directory / (purpose + '-' + digest(req)))['status'] == 'submitted'
    assert author.execute(req, purpose='proposal', certificate=certificate) == result and len(calls) == 2


def test_known_invalid_ir_survives_actual_campaign_projection_and_next_prompt(tmp_path, monkeypatch):
    req = request(tmp_path / 'campaign')
    bad = {'operations': [{'op': 'replace', 'selector': {'mechanism_id': 'does-not-exist'},
        'path': '/parameters/x', 'value': 1}], 'factors': [], 'continuous': [], 'rationale': 'SCRIPTED invalid ID'}
    author, calls = author_at(tmp_path / 'author', monkeypatch, [control, bad, control,
        {'operations': [], 'factors': [], 'continuous': [], 'rationale': 'SCRIPTED legal retention'}])
    failed = author.execute(req, purpose='proposal', certificate=author.calibrate(req))
    assert failed['status'] == 'failed' and failed['technical_diagnostics']
    later = clone(req); later['generation'] += 1
    later['history'] = [history_for(req, failed)]
    result = author.execute(later, purpose='proposal', certificate=author.calibrate(later))
    assert result['status'] == 'submitted' and result['definition']['base_patch'] is None
    body = json.loads(calls[-1]['messages'][1]['content'])
    feedback = body['own_history']['generation_authoring_failures'][0]
    assert feedback['request_sha256'] == digest(req)
    assert feedback['failed_ir_receipts'][0]['raw_ir_sha256'] == digest(bad)
    assert feedback['technical_errors'][0]['diagnostics'] == failed['technical_diagnostics']
    assert body['parent_system'] == req['parent_system']
    assert body['exact_design_space'] == req['design_space']
    assert 'history_anchor_schedules' not in body


def test_domain_law_edit_is_rejected_not_repaired(tmp_path, monkeypatch):
    req = request(tmp_path / 'campaign')
    bad = {'operations': [{'op': 'replace', 'path': '/initial_state/seed', 'value': 7}],
        'factors': [], 'continuous': [], 'rationale': 'SCRIPTED protected initialization edit'}
    author, calls = author_at(tmp_path / 'author', monkeypatch, [control, bad])
    result = author.execute(req, purpose='proposal', certificate=author.calibrate(req))
    assert result['status'] == 'failed' and result['literal_submission'] == bad
    assert result['definition'] is None and len(calls) == 2
    assert not result['source_repair'] and not result['completion_unknown']


def test_noncopy_valid_calibration_stays_diagnostic_and_legacy_certificate_is_not_reused(tmp_path, monkeypatch):
    req = request(tmp_path / 'campaign')
    retain = {'operations': [], 'factors': [], 'continuous': [], 'rationale': 'SCRIPTED legal noncopy control'}
    author, calls = author_at(tmp_path / 'author', monkeypatch, [retain])
    path = author.calibrate(req)
    cert = engine.require_certificate(path, request=req, provider=PROVIDER, backend=BACKEND, settings=author.settings)
    assert cert['passed'] and not cert['copy_equal_diagnostic']
    assert not cert['copy_is_dispatch_veto'] and not cert['directed_control_is_free_design_evidence']
    with pytest.raises(ValueError, match='mismatched'):
        engine.require_certificate(path, request=req, provider=PROVIDER, backend=BACKEND)
    assert len(calls) == 1


def test_oversize_full_parent_stops_before_http_without_silent_truncation(tmp_path, monkeypatch):
    req = request(tmp_path / 'campaign')
    req['parent_system']['metadata']['large_note'] = 'x' * 150000
    author, calls = author_at(tmp_path / 'author', monkeypatch, [])
    with pytest.raises(ValueError, match='exceeds declared bytes'):
        author.calibrate(req)
    assert calls == [] and not list(author.directory.glob('calibration-*'))


def test_declared_scalar_view_preserves_all_metrics_full_parent_and_raw_measurement_hash(tmp_path):
    req = request(tmp_path / 'campaign')
    measurement = {'metrics': {'native.accepted_decisions': {'status': 'measured', 'value': 7},
        'some-other-observed-metric': {'status': 'unavailable', 'value': None}},
        'native_trace': 'x' * 200000, 'content_details': ['SCRIPTED critic body']}
    req['observations'] = [{'observation': {'status': 'complete', 'loss': -7.,
        'metadata': {'measurements': [measurement]}}, 'suggestion': {'candidate': req['parent_system']}}]
    before = digest(req)
    value, _, wire = ir.payload({'request': req, 'provider': PROVIDER, 'purpose': 'proposal',
        'settings': engine.settings_for(engine.OPEN_IR_MODE)})
    body = json.loads(value['messages'][1]['content'])
    projected = body['own_history']['all_observations'][0]['measurements'][0]
    assert projected['metrics'] == measurement['metrics']
    assert projected['archived_full_measurement_sha256'] == digest(measurement)
    assert projected['omitted_nonmetric_fields'] == ['content_details', 'native_trace']
    assert body['parent_system'] == req['parent_system'] and digest(req) == before
    assert len(wire['request_wire_utf8'].encode()) < 140000
    assert body['prompt_view_metadata']['measurement_access'] == 'all-own-scalars-and-technical-failures-v1'
