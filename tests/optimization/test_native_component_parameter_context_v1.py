"""SCRIPTED current-parameter contexts; no actual model, Docker or native loss."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from tests.optimization.test_native_component_lab_v1 import fixture as legacy_lab
from tests.optimization.test_native_post_edit_feedback_v1 import fixture, source_action, finish, directory, GOOD
from tests.optimization.test_native_authoring_ir import edit, ALPHA
from utopia.optimization.native_component_lab_v1 import NativeComponentLab
from utopia.optimization.native_component_parameter_context_v1 import SCOPE, OPTION, binding, parameters, project
from utopia.optimization.native_post_edit_feedback_v1 import NativePostEditFeedback, persistent_diagnostics
from utopia.optimization.native_staged_author_v15 import replay_staged_generation
from utopia.system.code_mechanisms import CodeExecution, register_code_mechanisms, sha
from utopia.system import SystemSpec
from utopia.system.runtime import MechanismRegistry
from utopia.system.design_patch import digest


def optional_lab(tmp_path, maximum_probes=2):
    old, artifact, context, record, seen = legacy_lab(tmp_path, maximum_probes=maximum_probes)
    lab = NativeComponentLab(tmp_path / 'current', records=[record], provenance={'SCRIPTED': True},
        executor=old.executor, source_commit='a' * 40, maximum_probes=maximum_probes,
        parameter_context_scope=SCOPE)
    value = {'scope': SCOPE, 'node_id': 'SCRIPTED-node', 'document_sha256': 'b' * 64,
        'parameters': {'topic_priorities': {'SCRIPTED-topic': 1.}}}
    return lab, artifact, context, record, seen, value


def test_only_explicit_current_parameters_change_and_original_bundle_stays_literal(tmp_path):
    lab, artifact, context, record, seen, value = optional_lab(tmp_path)
    before = deepcopy(record); expected = project(context, value)
    reply = lab.probe(artifact, next(iter(lab.fixtures)), parameter_context=value)
    assert reply['status'] == 'returned' and seen == [(artifact, expected)]
    assert expected['parameters'] == value['parameters'] and record == before
    assert {k: v for k, v in expected.items() if k != 'parameters'} == {k: v for k, v in context.items() if k != 'parameters'}
    row = lab.replay()[0]
    assert row['intent']['parameter_context'] == value
    assert row['intent']['derived_context_sha256'] == digest(expected)
    assert lab.context_for(row['intent']) == expected
    assert reply['new_model_calls'] == reply['new_native_worlds'] == 0


def test_legacy_scope_cannot_gain_rebinding_authority_or_silently_change_contract(tmp_path):
    old, a, c, record, seen = legacy_lab(tmp_path)
    with pytest.raises(ValueError, match='authority'): old.probe(a, next(iter(old.fixtures)), parameter_context={})
    assert not old.replay() and not seen
    with pytest.raises(ValueError, match='budget changed'):
        NativeComponentLab(old.directory, records=[record], provenance={'kind':'scripted fixture, NOT a native audit'},
            executor=old.executor, source_commit='a' * 40, maximum_probes=2, parameter_context_scope=SCOPE)


@pytest.mark.parametrize('problem', ['missing', 'scope', 'reserved', 'extra', 'hash', 'type'])
def test_malformed_counterfactual_consumes_a_known_failed_probe_not_a_repair(tmp_path, problem):
    lab, a, c, record, seen, value = optional_lab(tmp_path, maximum_probes=1)
    if problem == 'missing': value = None
    elif problem == 'scope': value['scope'] = 'unknown'
    elif problem == 'reserved': value['parameters']['code_artifact'] = a
    elif problem == 'extra': value['inputs'] = {'forbidden': []}
    elif problem == 'hash': value['document_sha256'] = 'x' * 64
    else: value['parameters'] = []
    reply = lab.probe(a, next(iter(lab.fixtures)), parameter_context=value)
    assert reply['status'] == 'raised' and not seen and not reply['remote_completion_inferred']
    assert len(lab.replay()) == 1
    with pytest.raises(ValueError, match='budget exhausted'): lab.probe(a, next(iter(lab.fixtures)), parameter_context=value)


def test_literal_projection_matches_actual_native_handler_not_a_guessed_parameter_filter(tmp_path):
    from tests.optimization.test_native_authoring_ir import request
    document = request()['parent_system']; node = document['mechanisms'][0]
    node['parameters']['topic_priorities'] = {'SCRIPTED': 2.}
    spec = SystemSpec.from_dict(document); mechanism = spec.mechanisms[0]; calls = []
    def execute(a, c):
        calls.append(deepcopy(c))
        return CodeExecution({'outputs': {}, 'state': {}}, {})
    registry = MechanismRegistry(); register_code_mechanisms(registry,
        SimpleNamespace(image_id=node['parameters']['runtime_image_id'], execute=execute))
    registry.resolve(mechanism)(SimpleNamespace(mechanism=mechanism, period=1, phase=1,
        initial_state={'seed': 42}, state={}, inputs={}))
    assert calls[0]['parameters'] == parameters(document, node['mechanism_id'])
    assert 'topic_priorities' in calls[0]['parameters']
    assert not {'code_artifact', 'runtime_image_id'} & calls[0]['parameters'].keys()


def test_after_edit_current_parameters_reach_executor_archive_and_cold_replay(tmp_path):
    change = {'tool': 'edit', 'operations': [{'op': 'add', 'selector': {'mechanism_id': ALPHA},
        'path': '/parameters/topic_priorities', 'value': {'SCRIPTED': 1.}}]}
    gen, model, body, calls = fixture(tmp_path, [change, source_action(GOOD), finish()], parameter_context=True)
    result = gen(body)
    assert len(calls) == 8 and all(c['parameters']['topic_priorities'] == {'SCRIPTED': 1.} for a, c in calls)
    root = directory(tmp_path)
    step = json.loads((root / 'step-00.completed.json').read_text())
    notice = step['transition']['result']['component_feedback']
    assert notice['probe_attempts'] == 4 and notice['tests'][0]['parameter_context']['parameters']['topic_priorities'] == {'SCRIPTED': 1.}
    assert all(v['context']['parameters']['topic_priorities'] == {'SCRIPTED': 1.}
        for v in step['component_probe_records'])
    assert replay_staged_generation(root) == result and len(calls) == 8
    assert SCOPE in json.dumps(gen.edit_feedback.contract) and OPTION in gen.edit_feedback.bank


def test_parameter_only_changes_do_not_inherit_a_previous_artifact_pass(tmp_path):
    first = {'tool': 'edit', 'operations': [edit(path='/parameters/gain', value=2.)]}
    second = {'tool': 'edit', 'operations': [edit(path='/parameters/gain', value=3.)]}
    gen, model, body, calls = fixture(tmp_path, [first, second, finish()], parameter_context=True, maximum_probes=4)
    gen(body)
    assert len(calls) == 4 and all(c['parameters']['gain'] == 2. for a, c in calls)
    steps = [json.loads(p.read_text()) for p in sorted(directory(tmp_path).glob('step-*.completed.json'))]
    after = deepcopy(body['parent_system']); after['mechanisms'][0]['parameters']['gain'] = 3.
    row = persistent_diagnostics(after, steps)['components'][0]
    assert row['test_applicability'] == 'current-artifact-untested'
    assert row['current_artifact_observed_suite'] is None
    assert row['most_recent_executed_suite']['parameter_context']['parameters_sha256'] == digest({'gain': 2.})
    assert row['latest_component_notice']['status'] == 'not-run-budget-exhausted'
    assert row['latest_component_notice']['parameter_context']['parameters_sha256'] == digest({'gain': 3.})


def test_reverted_parameters_can_reuse_only_their_own_recorded_suite_without_probe_refill(tmp_path):
    actions = [{'tool': 'edit', 'operations': [edit(path='/parameters/gain', value=value)]} for value in (2., 3., 2.)]
    gen, model, body, calls = fixture(tmp_path, [*actions, finish()], parameter_context=True, maximum_probes=4)
    result = gen(body)
    after = deepcopy(body['parent_system']); after['mechanisms'][0]['parameters']['gain'] = 2.
    steps = [json.loads(p.read_text()) for p in sorted(directory(tmp_path).glob('step-*.completed.json'))]
    row = persistent_diagnostics(after, steps)['components'][0]
    assert row['test_applicability'] == 'same-current-artifact'
    assert row['current_artifact_observed_suite']['parameter_context']['parameters_sha256'] == digest({'gain': 2.})
    assert row['latest_component_notice']['status'] == 'not-run-budget-exhausted'
    assert len(calls) == 4 and replay_staged_generation(directory(tmp_path)) == result


def test_new_scope_traverses_actual_public_path_certificate_role_next_prompt_and_cold(tmp_path, monkeypatch):
    """HTTP/executor/supervision/source identity are SCRIPTED, not native proof."""
    from tests.reports.test_native_corrected_author_assay_v1 import example
    from tests.optimization.test_native_designer_contract_v16 import ScriptedSession, Response
    from tests.optimization.test_native_designer_roles_v38 import designer_binding
    from utopia.optimization import native_workflow_staged_designer_v1 as authoring
    from utopia.optimization import native_bounded_staged_designer as bounded
    from utopia.optimization.native_designer_tools_v25 import function_data
    from utopia.optimization.native_numeric_designer import checked
    from utopia.system.design_patch import clone
    body, document = example('parent-zero')
    node = next(n for n in document['mechanisms'] if n['mechanism_id'] == 'developer-catalog-agenda')
    artifact = node['parameters']['code_artifact']; provider = designer_binding()
    provider['image_id'] = node['parameters']['runtime_image_id']
    bank = {'nodes': [node['mechanism_id']], 'records': [], 'origins': [], OPTION: SCOPE,
        'post_edit_probe_scope': 'declared-sixtyfour-v2'}
    for year in range(1, 5):
        context = {'period': year, 'phase': 101, 'random_seed': 42, 'state': {},
            'parameters': {k: v for k, v in parameters(document, node['mechanism_id']).items()
                if k != 'topic_priorities'}, 'inputs': {'world': []}}
        result = {'outputs': {k: [] for k in artifact['outputs']}, 'state': {}}
        record = {'schema': 'scienceutopia.native-code-input.v1',
            'binding': {'source_commit': 'SCRIPTED', 'system_fingerprint': 'SCRIPTED', 'run_id': 'SCRIPTED'},
            'artifact': clone(artifact), 'context': context, 'result': result,
            'receipt': {'image_id': provider['image_id'], 'artifact_sha256': sha(artifact),
                'context_sha256': sha(context), 'result_sha256': sha(result)}}
        record['bundle_sha256'] = sha(record); bank['records'].append(record)
        bank['origins'].append({'node_id': node['mechanism_id'], 'year': year,
            'reference': 'open-seed', 'bundle_sha256': record['bundle_sha256']})
    bank['content_sha256'] = digest(bank); probes = []
    def execute(a, c):
        probes.append((clone(a), clone(c)))
        assert c['parameters']['topic_priorities'] == parameters(document, node['mechanism_id'])['topic_priorities']
        value = {'outputs': {k: [] for k in a['outputs']}, 'state': {}}
        return CodeExecution(value, {'image_id': provider['image_id'], 'artifact_sha256': sha(a),
            'context_sha256': sha(c), 'result_sha256': sha(value)})
    executor = SimpleNamespace(image_id=provider['image_id'], timeout=15., execute=execute)
    actions = [{'tool': 'plan', 'objective_reasoning': 'SCRIPTED interface only', 'design_intent': 'SCRIPTED'},
        {'tool': 'write_file', 'filename': 'code/developer-catalog-agenda.py',
            'content': artifact['source'] + '\n# SCRIPTED current-parameter public path\n'}, finish()]
    class Session(ScriptedSession):
        calls = []; production = []
        def get(self, url, **kw):
            return Response({'version': 'SCRIPTED-backend'} if url.endswith('/version') else {
                'models': [{'name': provider['model'], 'digest': provider['model_digest']}]})
        def post(self, url, **kw):
            payload = json.loads(kw['data'])
            if 'TRUSTED INTERFACE CALIBRATION TASK' in payload['messages'][0]['content']:
                value = super().post(url, **kw).json(); value['model'] = provider['model']; return Response(value)
            if payload['messages'][0]['content'].startswith('INSTRUCTED PLANNING INTERFACE CONTROL'):
                from utopia.optimization.native_staged_author_v15 import PLAN_CONTROL
                return Response({'model': provider['model'], 'done': True, 'done_reason': 'stop',
                    'prompt_eval_count': 120, 'eval_count': 12, 'message': {'role': 'assistant',
                        'content': json.dumps(function_data(PLAN_CONTROL))}})
            action = actions[len(self.production)]; self.production.append(payload)
            return Response({'model': provider['model'], 'done': True, 'done_reason': 'stop',
                'prompt_eval_count': 120, 'eval_count': 12, 'message': {'role': 'assistant',
                    'content': json.dumps(function_data(action)),
                    **({'thinking': 'SCRIPTED'} if payload['think'] else {})}})
    monkeypatch.setattr('requests.Session', Session)
    monkeypatch.setattr('utopia.optimization.native_jobs.pinned_revision', lambda root: 'c' * 40)
    monkeypatch.setattr('utopia.optimization.native_scientist_load_v38.load_local_role', lambda *a, **kw: None)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor', lambda **kw: executor)
    def child(argv, **kw):
        bounded.worker(argv[-2], argv[-1]); return {'timed_out': False, 'returncode': 0}
    monkeypatch.setattr(bounded, 'run_bounded', child)
    author = authoring.StagedWorkflowDesigner(tmp_path / 'public', provider=provider,
        backend={'model': provider['model'], 'model_digest': provider['model_digest'], 'ollama_version': 'SCRIPTED-backend'},
        inference_lock=tmp_path / 'SCRIPTED-inference.lock', source_commit='c' * 40, bank=bank)
    body = author.feedback.declare_request(body)
    certificate = author.calibrate(body)
    assert certificate.is_file()  # Actual public API returns Path, not a mock certificate dictionary.
    assert not Session.production, [p['messages'][0]['content'][:100] for p in Session.production]
    result = author.execute(body, purpose='proposal', certificate=certificate)
    assert 'generation_failure' not in result['definition'] and len(probes) == 4 and len(Session.production) == 3
    assert SCOPE in json.dumps(Session.production[-1]) and 'topic_priorities' in json.dumps(Session.production[-1])
    for purpose in ('calibration', 'proposal'):
        replayed = authoring.replay(author.directory / (purpose + '-' + digest(body)), request=body,
            provider=provider, backend=author.backend, source_commit='c' * 40, bank=bank, purpose=purpose)
        if purpose == 'proposal': assert replayed == result
    assert len(probes) == 4 and len(Session.production) == 3


def test_parameter_overlay_requires_explicit_evidence_and_preserves_exact_original_bank(tmp_path, monkeypatch):
    from tests.optimization.test_native_authoring_ir import request
    from utopia.optimization import native_workflow_staged_designer_v1 as authoring
    from utopia.utils.data_utils import file_sha256
    anchor = request()['parent_system']; path = tmp_path / 'SCRIPTED-audit.json'
    path.write_text('{}')  # Test input, never a retained audit or original failure.
    original = {'records': [{'binding': {'system_fingerprint': SystemSpec.from_dict(anchor).fingerprint}}]}
    # collect's native attribution is explicitly SCRIPTED here; the production
    # overlay must still reconstruct and compare the ENTIRE returned bank.
    monkeypatch.setattr('scripts.reports.stage_native_component_fixtures_v1.collect', lambda *a, **kw: deepcopy(original))
    evidence = {'run': 'SCRIPTED', 'source': 'SCRIPTED', 'audit': str(path), 'audit_file_sha256': file_sha256(path),
        'parameter_context_scope': SCOPE}
    bank = {**deepcopy(original), OPTION: SCOPE}; bank['content_sha256'] = digest(bank)
    assert authoring.require_bank(bank, evidence, anchor) == bank
    del evidence['parameter_context_scope']
    with pytest.raises(ValueError, match='differs'): authoring.require_bank(bank, evidence, anchor)
