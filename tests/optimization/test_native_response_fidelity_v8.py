"""Response-boundary mathematics and original six-year scripted-native QA.

No real model/API calls. Seven native worlds per integration test, real pinned
networkless Docker. This must never be presented as Qwen or scientific benefit.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess

import pytest
import torch

from tests.runtime.test_portable_checkpoint_integration import BINDING, FakeHTTPModel, fixed_corpus, seed
from tests.system.test_native_science_kernel import make_sim
from tests.optimization.test_native_hybrid_v7 import recurrent_system
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.native_code_trace import RecordingCodeExecutor
from utopia.optimization.native_factory import record_native_http
from utopia.optimization.native_hybrid import conditional_backward, native_endpoint, project_continuous
from utopia.optimization.native_response_fidelity import (
    BoundaryUnsupported, NativeResponseOperator, boundary_layout, endpoint_decomposition,
    project_response, raw_review_projection, make_response_completion_receipt,
)
from utopia.runtime.checkpointing import canonical_json, write_portable_checkpoint
from utopia.system import ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from utopia.system.code_mechanisms import CodeExecutionError, DockerCodeExecutor
from utopia.system.design_patch import digest
from utopia.system.native_kernel import NativeScienceKernel, add_context_receiver
from utopia.system.native_review_context import enable_review_context, register_review_context
from utopia.system.tensor_program import execute_tensor_program
from utopia.utils.data_utils import file_sha256, write_json_atomic

ROOT = Path(__file__).resolve().parents[2]
CLASSIFICATION = 'scripted-fixture-not-native-results'


def numerical_endpoint_not_native(theta, *, response=4.25, native=None):
    """Pure unit-test fixture; checkpoint verifier is explicitly patched below."""
    program = {'schema': 'scienceutopia.tensor-program.v1', 'inputs': {'features': [-1, 2]},
        'parameters': {}, 'state': {}, 'nodes': [{'id': 'score', 'op': 'column', 'args': ['input:features'], 'attrs': {'index': 0}}],
        'outputs': {'utility': 'score'}, 'updates': {}}
    values = [[response, 2.]]
    outputs, state = execute_tensor_program(program, {'features': torch.tensor(values, dtype=torch.float64)}, hard=True)
    spec = {'system_id': 'numerical-fixture-not-native', 'version': 1, 'mechanisms': [{
        'mechanism_id': 'math', 'family': 'custom', 'implementation': 'program.tensor.v1', 'parameters': {'program': program}}]}
    return {'checkpoint': 'fixture-only-'+str(theta), 'checkpoint_sha256': digest(['fixture-only', theta]),
        'system': spec, 'system_fingerprint': digest(spec), 'world': {'classification': CLASSIFICATION},
        'physical_initial_identity': 'unit-initial', 'noncoordinate_system_sha256': 'unit-system',
        'coordinates_sha256': 'unit-coordinates', 'loss_spec_sha256': 'unit-loss', 'coordinate_values': {'advice': theta},
        'native_loss': -response if native is None else native,
        'trace': [{'year': 1, 'mechanism': 'math', 'event_id': digest(theta), 'program_sha256': digest(program),
            'inputs': {'features': values}, 'input_sources': {'features': {'mechanism': 'opaque', 'port': 'raw', 'period': 1, 'path': '/values'}},
            'state_before': {}, 'state_after': state, 'outputs': {k: v.tolist() for k, v in outputs.items()},
            'records': [{'paper_id': 'paper-1', 'conference_id': 'conference-1'}]}]}


DECLARATIONS_UNIT = [{'id': 'advice', 'mechanism': 'opaque', 'path': '/advice', 'lower': -1., 'upper': 1., 'quantum': None}]
TERMS_UNIT = [{'mechanism': 'math', 'output': 'utility', 'coefficient': -1.}]


def test_learned_response_chain_rule_and_unused_finite_path_are_not_frozen_input_derivatives(monkeypatch):
    monkeypatch.setattr('utopia.optimization.native_response_fidelity.verify_endpoint', lambda *a: None)
    points = [numerical_endpoint_not_native(x, response=4.25+2*x) for x in (-.25, 0., .25)]
    model = NativeResponseOperator.fit(points, DECLARATIONS_UNIT, {}, TERMS_UNIT, temperatures=[1., .2])
    assert model.state['temperature_selection']['unused_endpoints_seen'] == 0
    assert model.state['temperature'] == 1.  # training-only tie preserves declared order
    result = model.backward([.1])
    assert result['gradient'] == pytest.approx([-2.])
    assert result['frozen_boundary_gradient'] == [0.]
    assert not result['native_derivative_verified'] and not result['full_native_world_autograd']
    left, right = [numerical_endpoint_not_native(x, response=4.25+2*x) for x in (-.2, .1)]
    check = model.integrated_check(left, right, quadrature=16, atol=1e-10)
    assert check['status'] == 'passed-unused-native-finite-path-check'
    assert check['predicted_finite_delta'] == pytest.approx(-.6)
    assert check['frozen_boundary_native_error'] == pytest.approx(.6)
    assert check['response_aware_native_error'] < 1e-12
    assert type(check['predicted_average_directional_derivative']) is float
    with pytest.raises(ValueError, match='calibration data'):
        model.validate_unused(points[0])
    beyond = numerical_endpoint_not_native(.6, response=5.45)
    assert model.validate_unused(beyond)['status'] == 'unsupported-native-calibration-query'
    model.state['weights'][1][0] = 999.
    with pytest.raises(ValueError, match='changed'):
        model.backward([0.])


def test_native_endpoint_decomposition_is_exact_and_record_changes_are_not_padded():
    a = numerical_endpoint_not_native(0., response=4.)
    b = numerical_endpoint_not_native(.1, response=5.)
    result = endpoint_decomposition(a, b, DECLARATIONS_UNIT, TERMS_UNIT, temperature=.2)
    assert result['accounting_error'] == pytest.approx(0.)
    assert result['components']['response_drift_soft'] == pytest.approx(-1.)
    assert result['components']['direct_soft'] == 0.
    b['trace'][0]['records'][0]['paper_id'] = 'another-actual-paper'
    result = endpoint_decomposition(a, b, DECLARATIONS_UNIT, TERMS_UNIT, temperature=.2)
    assert result['status'] == 'unsupported-record-routing-or-shape-change'
    a['trace'][0]['records'] = []
    with pytest.raises(BoundaryUnsupported, match='semantic IDs'):
        boundary_layout(a)


def numeric_journal(tmp_path, scores, *, nonreview=False):
    endpoint = numerical_endpoint_not_native(0., response=3., native=-3.)
    endpoint['world'].update(source_commit='scripted-unit', model_digest='scripted-model', corpus_sha256='scripted-corpus', seed=42)
    binding = {'cell': endpoint['system_fingerprint'], 'seed': 42, 'model': 'scripted', 'model_revision': 'scripted-model',
        'corpus_sha256': 'scripted-corpus', 'science_config': {'source_commit': 'scripted-unit'}}
    from utopia.agents.base_agent import PaperReview
    from utopia.utils.seeding import derive_seed
    (tmp_path/'cache').mkdir()
    journal, wire = tmp_path/'cache/responses.sqlite', tmp_path/'wire.jsonl'
    checkpoint = tmp_path/'checkpoints/portable_checkpoint_year_1.json.gz'
    write_portable_checkpoint(checkpoint, {'portable': {'contract': {'binding': binding},
        'response_cache_count': len(scores)+int(nonreview)}})
    endpoint.update(checkpoint=str(checkpoint), checkpoint_sha256=file_sha256(checkpoint), response_cache_count=len(scores)+int(nonreview))
    wires = []
    with sqlite3.connect(journal) as db:
        db.execute('CREATE TABLE metadata(binding TEXT)')
        db.execute('INSERT INTO metadata VALUES (?)', (canonical_json(binding),))
        db.execute('CREATE TABLE replies(identity TEXT,payload_sha TEXT,outcome TEXT,data TEXT,data_sha TEXT)')
        for i, score in enumerate(scores):
            request_seed = derive_seed(binding['seed'], 'phase3_reviews', 1, i, 0)
            payload = {'model': 'scripted', 'seed': request_seed, 'messages': [],
                'extra_body': {'structured_outputs': {'json': PaperReview.model_json_schema()}}}
            identity = hashlib.sha256(canonical_json({'binding': binding, 'seed_ctx': ('phase3_reviews', 1),
                'item_index': i, 'attempt': 0, 'seed': request_seed}).encode()).hexdigest()
            payload_sha = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
            data = canonical_json({'model': 'scripted', 'choices': [{'message': {'content': json.dumps({'overall_score': score})}}]})
            db.execute('INSERT INTO replies VALUES (?,?,?,?,?)', (identity, payload_sha, 'response', data, hashlib.sha256(data.encode()).hexdigest()))
            wires.append({'year': 1, 'payload_sha256': payload_sha, 'payload': payload})
        if nonreview:
            payload = {'model': 'scripted', 'seed': 0, 'messages': []}
            sha = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
            data = canonical_json({'model': 'scripted', 'choices': [{'message': {'content': '{"not_a_review":true}'}}]})
            db.execute('INSERT INTO replies VALUES (?,?,?,?,?)', (hashlib.sha256(b'nonreview-identity').hexdigest(), sha, 'response', data,
                hashlib.sha256(data.encode()).hexdigest()))
            wires.append({'year': 1, 'payload_sha256': sha, 'payload': payload})
    wire.write_text(''.join(json.dumps(row)+'\n' for row in wires))
    return endpoint, journal, wire


def test_raw_reply_projection_retains_native_integer_boundary_and_rejects_heterogeneity(tmp_path):
    endpoint, journal, wire = numeric_journal(tmp_path, [3.75, 3.75])
    layout, z, _ = boundary_layout(endpoint)
    raw, projection = raw_review_projection(endpoint, layout, z, journal=journal, wire=wire, mechanism='math', input_name='features')
    assert raw.tolist() == [3.75, 2.]
    assert project_response(raw, projection, hard=True, temperature=.1).tolist() == z.tolist()
    raw.requires_grad_()
    soft = project_response(raw, projection, hard=False, temperature=.05)
    derivative, = torch.autograd.grad(soft.sum(), (raw,))
    assert derivative[0] > 0
    with sqlite3.connect(journal) as db:
        data = canonical_json({'model': 'scripted', 'choices': [{'message': {'content': '{"overall_score":3.5}'}}]})
        db.execute('UPDATE replies SET data=?,data_sha=? WHERE rowid=2', (data, hashlib.sha256(data.encode()).hexdigest()))
    with pytest.raises(BoundaryUnsupported, match='heterogeneous'):
        raw_review_projection(endpoint, layout, z, journal=journal, wire=wire, mechanism='math', input_name='features')


@pytest.mark.parametrize('tamper', ['full-binding', 'truncate-nonreview', 'wrong-task-score', 'wrong-schema', 'foreign-path'])
def test_raw_review_proof_rejects_truncation_foreign_binding_task_and_schema(tmp_path, tamper):
    endpoint, journal, wire = numeric_journal(tmp_path, [3.75, 3.75], nonreview=True)
    layout, z, _ = boundary_layout(endpoint)
    raw_review_projection(endpoint, layout, z, journal=journal, wire=wire, mechanism='math', input_name='features')
    if tamper == 'foreign-path':
        import shutil
        foreign = tmp_path/'foreign.sqlite'
        shutil.copy2(journal, foreign)
        journal = foreign
    else:
        with sqlite3.connect(journal) as db:
            if tamper == 'full-binding':
                binding = json.loads(db.execute('SELECT binding FROM metadata').fetchone()[0])
                binding['protocol'] = 'foreign-protocol-with-same-source-model-cell'
                db.execute('UPDATE metadata SET binding=?', (canonical_json(binding),))
            elif tamper == 'truncate-nonreview':
                db.execute('DELETE FROM replies WHERE rowid=3')
            elif tamper == 'wrong-task-score':
                db.execute('UPDATE replies SET identity=? WHERE rowid=1',
                    (hashlib.sha256(b'nonreview-task-identity').hexdigest(),))
            else:
                wires = [json.loads(line) for line in wire.read_text().splitlines()]
                wires[0]['payload']['extra_body']['structured_outputs']['json'] = {'type': 'object'}
                sha = hashlib.sha256(canonical_json(wires[0]['payload']).encode()).hexdigest()
                wires[0]['payload_sha256'] = sha
                db.execute('UPDATE replies SET payload_sha=? WHERE rowid=1', (sha,))
                wire.write_text(''.join(json.dumps(r)+'\n' for r in wires))
    with pytest.raises((ValueError, BoundaryUnsupported)):
        raw_review_projection(endpoint, layout, z, journal=journal, wire=wire, mechanism='math', input_name='features')


@pytest.mark.parametrize('change', ['upper', 'columns', 'mechanism', 'input_name'])
def test_calibration_requires_full_projection_contract_not_just_equal_indices(monkeypatch, change):
    monkeypatch.setattr('utopia.optimization.native_response_fidelity.verify_endpoint', lambda *a: None)
    points = [numerical_endpoint_not_native(x, response=4.25+2*x) for x in (-.25, 0., .25)]
    evidence = {p['checkpoint_sha256']: {'changed': i == 2} for i, p in enumerate(points)}
    def projection(endpoint, layout, numeric, *, changed):
        contract = {'upper': 10, 'score_column': 0, 'count_column': 1, 'mechanism': 'math', 'input_name': 'features'}
        if changed:
            if change == 'upper': contract['upper'] = 5
            elif change == 'columns': contract.update(score_column=1, count_column=0)
            else: contract[change] = 'other'
        return numeric, {'kind': 'fixture', 'indices': [0], 'contract': contract}
    monkeypatch.setattr('utopia.optimization.native_response_fidelity.raw_review_projection', projection)
    with pytest.raises(BoundaryUnsupported, match='correspondence changes'):
        NativeResponseOperator.fit(points, DECLARATIONS_UNIT, {}, TERMS_UNIT, numeric_response_evidence=evidence)


@pytest.mark.parametrize('change', ['extra-unused', 'missing'])
def test_numeric_response_evidence_is_exactly_calibration_set_before_selection(monkeypatch, change):
    monkeypatch.setattr('utopia.optimization.native_response_fidelity.verify_endpoint', lambda *a: None)
    points = [numerical_endpoint_not_native(x, response=4.25+2*x) for x in (-.25, 0., .25)]
    evidence = {p['checkpoint_sha256']: {} for p in points}
    if change == 'extra-unused': evidence[numerical_endpoint_not_native(.1)['checkpoint_sha256']] = {}
    else: evidence.pop(points[0]['checkpoint_sha256'])
    with pytest.raises(ValueError, match='exactly the calibration'):
        NativeResponseOperator.fit(points, DECLARATIONS_UNIT, {}, TERMS_UNIT, numeric_response_evidence=evidence)


@pytest.mark.parametrize('atol,rtol', [(float('nan'), 0.), (0., -1.), (float('inf'), 0.), (True, 0.)])
def test_fidelity_tolerances_are_finite_nonnegative_and_not_bool(monkeypatch, atol, rtol):
    monkeypatch.setattr('utopia.optimization.native_response_fidelity.verify_endpoint', lambda *a: None)
    points = [numerical_endpoint_not_native(x, response=4.25+2*x) for x in (-.25, 0., .25)]
    model = NativeResponseOperator.fit(points, DECLARATIONS_UNIT, {}, TERMS_UNIT)
    a, b = [numerical_endpoint_not_native(x, response=4.25+2*x) for x in (-.2, .1)]
    with pytest.raises(ValueError, match='finite nonnegative'):
        model.validate_unused(a, atol=atol, rtol=rtol)
    with pytest.raises(ValueError, match='finite nonnegative'):
        model.integrated_check(a, b, atol=atol, rtol=rtol)


def test_finite_delta_agreement_does_not_hide_absolute_endpoint_offset(monkeypatch):
    monkeypatch.setattr('utopia.optimization.native_response_fidelity.verify_endpoint', lambda *a: None)
    points = [numerical_endpoint_not_native(x, response=4.25+2*x) for x in (-.25, 0., .25)]
    model = NativeResponseOperator.fit(points, DECLARATIONS_UNIT, {}, TERMS_UNIT)
    a, b = [numerical_endpoint_not_native(x, response=4.25+2*x, native=10-(4.25+2*x)) for x in (-.2, .1)]
    check = model.integrated_check(a, b, quadrature=16)
    assert check['finite_delta_agreement'] and not check['absolute_endpoint_fidelity']
    assert check['status'] == 'failed-unused-native-finite-path-fidelity'


def test_future_owner_completion_receipt_is_explicit_hashbound_not_retroactive_authentication(tmp_path):
    from types import SimpleNamespace
    from utopia.models.response_cache import CompletedResponseCache
    endpoint, journal, wire = numeric_journal(tmp_path, [3.75, 3.75])
    layout, z, _ = boundary_layout(endpoint)
    args = dict(journal=journal, wire=wire, mechanism='math', input_name='features')
    _, initial = raw_review_projection(endpoint, layout, z, **args)
    assert initial['completion_provenance']['status'] == 'no-run-completion-receipt'
    with sqlite3.connect(journal.resolve().as_uri()+'?mode=ro', uri=True) as db:
        owner = SimpleNamespace(path=journal, _db=db, binding=json.loads(db.execute('SELECT binding FROM metadata').fetchone()[0]),
            committed_count=lambda: db.execute('SELECT count(*) FROM replies').fetchone()[0])
        owner.committed_prefix_identity = lambda: CompletedResponseCache.committed_prefix_identity(owner)
        receipt = make_response_completion_receipt(endpoint, owner, wire, run_manifest_sha256='a'*64)
    _, verified = raw_review_projection(endpoint, layout, z, completion_receipt=receipt, **args)
    assert verified['completion_provenance']['status'] == 'hashbound-caller-supplied-completion-assertion'
    assert not verified['completion_provenance']['timing_authenticated']
    receipt['response_prefix']['rows_sha256'] = 'b'*64
    receipt['content_sha256'] = digest({k: v for k, v in receipt.items() if k != 'content_sha256'})
    with pytest.raises(ValueError, match='completion receipt differs'):
        raw_review_projection(endpoint, layout, z, completion_receipt=receipt, **args)


SIGNAL_SOURCE = """def step(context):
    world = context['inputs']['world'][0]['payload']
    authors = [a['id'] for a in world['ecosystem']['agents'] if a['can_author']]
    return {'outputs': {'messages': [{'payload': {
        'response_fidelity_signal': context['parameters']['advice'],
        'native_year': context['period']}, 'actor_ids': authors}]},
        'state': {'cycles': context['state'].get('cycles', 0) + 1}}
"""


def response_system(image):
    system = recurrent_system(image)
    nodes = []
    for node in system.mechanisms:
        p = deepcopy(node.parameters)
        if node.mechanism_id == 'addressed-selection':
            p['program']['parameters']['bias'] = -2.  # fixed stable-decision regime, not a new native law
        if node.mechanism_id == 'recurrent-router':
            p['program']['inputs']['scores'] = [-1]
            p['input_bindings']['scores'] = {'port': 'scores', 'path': '/values'}
            p['program']['nodes'].append({'id': 'actual-utility', 'op': 'mul', 'args': ['input:scores', 'actions'], 'attrs': {}})
            p['program']['outputs']['utility'] = 'actual-utility'
            protocol = node.inputs[0].artifact_type
            node = replace(node, inputs=(*node.inputs, PortSpec('scores', ChannelKind.ARTIFACT, protocol)),
                outputs=(*node.outputs, PortSpec('utility', ChannelKind.ARTIFACT, protocol)))
        nodes.append(replace(node, parameters=p))
    artifact = {'schema': 'scienceutopia.code-mechanism.v1', 'label': 'Scripted response-fidelity QA signal; not invented policy',
        'source': SIGNAL_SOURCE, 'inputs': {'world': {'type': 'object'}}, 'outputs': {'messages': {'type': 'object'}},
        'state_schema': {'type': 'object'}}
    signal = MechanismSpec('response-signal', MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('world', ChannelKind.ARTIFACT, 'native-world-observation'),),
        outputs=(PortSpec('messages', ChannelKind.ARTIFACT, 'native-response-signal'),),
        parameters={'code_artifact': artifact, 'runtime_image_id': image, 'advice': 0.})
    system = replace(system, mechanisms=(*nodes, signal), artifact_types=(*system.artifact_types, ArtifactTypeSpec('native-response-signal')),
        schedules=(*system.schedules, ScheduleSpec('response-signal', 10)), connections=(*system.connections,
            ConnectionSpec('world.open', 'world', 'response-signal', 'world', ChannelKind.ARTIFACT),
            ConnectionSpec('addressed-selection', 'scores', 'recurrent-router', 'scores', ChannelKind.ARTIFACT)))
    system = add_context_receiver(system, source='response-signal', source_port='messages', receiver='response-delivery', phase=15)
    return enable_review_context(system, receiver='response-delivery')


class ResponseAwareScriptedHTTP(FakeHTTPModel):
    """Fixed scripted weights/rules, actual changing native inputs and replies."""
    def reply(self, **payload):
        response = super().reply(**payload)
        phase = self.context[0][0]
        prompt = '\n'.join(m.get('content', '') for m in payload['messages'] if isinstance(m.get('content'), str))
        matches = re.findall(r'"response_fidelity_signal":\s*([-+0-9.eE]+)', prompt)
        if phase in {'phase1_directions', 'phase3_reviews'}:
            assert matches, 'actual native HTTP input must contain the institution signal'
            advice = float(matches[-1])
            accepted = sum(d['decision'] == 'accept' for p in self.sim.paper_tracker.papers_by_id.values() for d in p.review_history)
            resources = sum(a.resources for a in self.sim.ecosystem.agent_population.values() if a.can_author)
            data = json.loads(response.choices[0].message.content)
            if phase == 'phase3_reviews':
                data['overall_score'] = 4.25+2*advice + .001*accepted + .00001*(resources-4000.)
                data['justification'] = f'Scripted response to actual native advice={advice}; accepts={accepted}; resources={resources}'
            else:
                data['detailed_focus'] = f'Actual institution signal={advice}; native accepts={accepted}; native resources={resources}'
            response.choices[0].message.content = json.dumps(data)
        return response


DECLARATIONS = [{'id': 'advice', 'mechanism': 'response-signal', 'path': '/advice', 'lower': -1., 'upper': 1., 'quantum': None}]
TERMS = [{'mechanism': 'recurrent-router', 'output': 'utility', 'coefficient': -1.}]


def test_seven_original_native_worlds_response_boundary_backward_unused_validation_and_reload(tmp_path, fixed_corpus, monkeypatch):
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    try:
        executor = DockerCodeExecutor(timeout=60.)
    except (CodeExecutionError, OSError):
        pytest.skip('real pinned networkless Docker required for original-native QA')
    system = response_system(executor.image_id)
    objective = loss_spec('native.accepted_peer_score_sum')
    world = {'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'model_digest': BINDING['model_revision'], 'corpus_sha256': BINDING['corpus_sha256'], 'seed': 42,
        'classification': CLASSIFICATION}
    endpoints, response_evidence, calls, failures = [], {}, {}, []
    def run(name, value):
        candidate, projection = project_continuous(system, DECLARATIONS, {'advice': value})
        monkeypatch.setitem(BINDING, 'cell', candidate.fingerprint)
        monkeypatch.setitem(BINDING, 'science_config', {**BINDING['science_config'], 'source_commit': world['source_commit']})
        seed()
        root = tmp_path/name
        recorder = RecordingCodeExecutor(executor, root/'code-contexts.jsonl', binding={
            'source_commit': world['source_commit'], 'system_fingerprint': candidate.fingerprint, 'run_id': name})
        # Production registry, no caller-only extension: arbitrary sandbox
        # institution output reaches the original native review HTTP inputs.
        sim, actual_calls = make_sim(root, native=NativeScienceKernel(candidate, code_executor=recorder),
            model_class=ResponseAwareScriptedHTTP)
        record_native_http(sim.llm, sim, root/'wire.jsonl')
        try:
            sim.run()
            assert sim.llm.reused == 0
            endpoint = native_endpoint(root/'checkpoints/portable_checkpoint_year_6.json.gz', candidate, DECLARATIONS,
                objective, world=world, code_contexts=root/'code-contexts.jsonl')
            calls[name] = deepcopy(actual_calls)
            endpoints.append(endpoint)
            response_evidence[endpoint['checkpoint_sha256']] = {'journal': str(root/'cache/responses.sqlite'),
                'wire': str(root/'wire.jsonl'), 'mechanism': 'addressed-selection', 'input_name': 'features'}
            write_json_atomic(tmp_path/'completed-native-endpoints.json', endpoints, sort_keys=True, allow_nan=False)
            return endpoint
        except BaseException as error:
            failures.append({'world': name, 'control': value, 'error': str(error), 'loss': None})
            raise  # No success-conditioned replacement world.
        finally:
            sim.llm.response_cache.close()
    calibration = [run('calibration-'+str(i), value) for i, value in enumerate((-.25, 0., .25))]
    model = NativeResponseOperator.fit(calibration, DECLARATIONS, objective, TERMS,
        temperatures=[1., .2, .05, .01], numeric_response_evidence=response_evidence)
    frozen = model._hash
    assert model.state['temperature_selection']['unused_endpoints_seen'] == 0
    native_left, native_right = [run('unused-'+str(i), value) for i, value in enumerate((-.20, .10))]
    assert model._hash == frozen
    checks = [model.validate_unused(p) for p in (native_left, native_right)]
    finite = model.integrated_check(native_left, native_right, quadrature=128)
    decomposition = endpoint_decomposition(native_left, native_right, DECLARATIONS, TERMS,
        temperature=model.state['temperature'])
    assert abs(decomposition['accounting_error']) < 1e-10
    assert decomposition['boundary_numeric_max_drift'] > 0
    assert finite['response_aware_native_error'] < finite['frozen_boundary_native_error']
    assert finite['status'] == 'passed-unused-native-finite-path-check', finite
    assert all(c['status'] == 'passed-unused-native-endpoint' for c in checks), checks
    point = model.backward([0.])
    # Real autograd through both recurrent institutions and learned response;
    # this is not an opaque-source finite secant installed as custom backward.
    conditional = conditional_backward(calibration[1]['trace'], {
        n['mechanism_id']: n['parameters']['program'] for n in calibration[1]['system']['mechanisms'] if n['implementation'] == 'program.tensor.v1'},
        trainable={'addressed-selection': ['bias'], 'recurrent-router': ['threshold']}, terms=TERMS,
        temperature=model.state['temperature'])
    proposed = min(.20, max(-.20, -.002*finite['predicted_average_directional_derivative']))
    candidate = run('gradient-projected-candidate', proposed)
    outside = run('outside-support', .6)
    outside_check = model.validate_unused(outside)
    assert outside_check['status'] == 'unsupported-native-calibration-query'
    assert outside_check['gradient'] is None and outside_check['predicted_loss'] is None
    assert len(endpoints) == 7 and not failures
    assert calls['calibration-0'] != calls['unused-1']
    model.save(tmp_path/'response-operator.json', verification_endpoints=[native_left, native_right, candidate, outside])
    loaded = NativeResponseOperator.load(tmp_path/'response-operator.json')
    assert loaded.backward([0.]) == point
    assert loaded.integrated_check(native_left, native_right, quadrature=128) == finite
    # Outer hash recomputation cannot legitimize a forged learned response.
    saved = json.loads((tmp_path/'response-operator.json').read_text())
    saved['model']['weights'][1][0] += 1.
    saved['representation_sha256'] = digest(saved['model'])
    saved['content_sha256'] = digest({k: v for k, v in saved.items() if k != 'content_sha256'})
    write_json_atomic(tmp_path/'forged-operator.json', saved, allow_nan=False)
    with pytest.raises(ValueError, match='reconstruct'):
        NativeResponseOperator.load(tmp_path/'forged-operator.json')
    compact = {'schema': 'scienceutopia.native-response-fidelity-qa.v8', 'classification': CLASSIFICATION,
        'new_live_Qwen_calls': 0, 'native_worlds': 7, 'native_years': 6, 'original_researchers': 4,
        'source_commit': world['source_commit'], 'fixture_source_sha256': file_sha256(Path(__file__)),
        'module_source_sha256': file_sha256(ROOT/'utopia/optimization/native_response_fidelity.py'),
        'signal_source_sha256': digest(SIGNAL_SOURCE),
        'review_ingress_source_sha256': file_sha256(ROOT/'utopia/system/native_review_context.py'),
        'production_registry_without_extension': True,
        'prior_failed_physical_attempts': [{'source_commit': '84701f3', 'world': 'calibration-0',
            'completed_worlds': 0, 'loss': None, 'reason': 'actual original review prompt omitted delivered institution signal',
            'raw_available': False, 'raw_retention_failure': 'shared pytest temporary retention removed partial-world raw',
            'raw_path': '/private/var/folders/ry/w663wy7n4j52rjwfmd7rxbl40000gn/T/pytest-of-shiro/pytest-756/test_seven_original_native_wor0'}],
        'prior_incomplete_batches': [{'source_commit': '01992cd', 'completed_native_worlds': 5,
            'controls': [-.25, 0., .25, -.20, .10], 'remaining_native_worlds_not_started': 2,
            'reason': 'np.float64 finite integral output rejected by strict native-coordinate API before candidate execution',
            'native_world_failures': 0, 'diagnostic_batch_complete': False,
            'raw_path': str(ROOT/'outputs/response-fidelity-v8-qa2/test_seven_original_native_wor0')}],
        'endpoints': [{k: p[k] for k in ('checkpoint_sha256', 'system_fingerprint', 'coordinate_values', 'native_loss',
            'physical_initial_identity', 'native_event_stream_hash', 'response_cache_count', 'code_contexts_sha256')} for p in endpoints],
        'raw_response_proofs': model.state['raw_response_proofs'], 'temperature_selection': model.state['temperature_selection'],
        'raw_fit_rmse': model.state['raw_fit_rmse'], 'point_backward': point, 'conditional_multi_node_backward': conditional,
        'unused_endpoint_checks': checks, 'native_finite_path': finite, 'endpoint_decomposition': decomposition,
        'projected_control': proposed, 'candidate_native_loss': candidate['native_loss'],
        'outside_support': outside_check, 'failures': failures, 'semantic_reload_verified': True,
        'full_native_world_autograd': False, 'native_LLM_Jacobian_verified': False,
        'limits': ['Scripted fixed-response rule, NOT actual Qwen fidelity or science-policy evidence.',
            'Uniform reply cohort adapter refuses heterogeneous unmapped replies.',
            'Finite path-integrated comparison is not a native point Jacobian.',
            'Original integer parser and hard native execution are unchanged.']}
    compact['content_sha256'] = digest(compact)
    write_json_atomic(tmp_path/'compact-response-fidelity-v8.json', compact, sort_keys=True, allow_nan=False)
