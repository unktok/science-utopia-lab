"""Prospective V44 recovery; original failed artifacts are never rewritten."""
from copy import deepcopy
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from tests.optimization.test_native_authoring_ir import BINDING, IMAGE, request
from tests.optimization.test_native_json_history_v40 import DialogueModel
from tests.optimization.test_native_designer_contract_v16 import ScriptedSession
from utopia.optimization import native_designer_preflight as preflight
from utopia.optimization.native_authoring_recovery_v44 import (
    workflow, backend_format, IMPLEMENT_TASK, SUBMIT_TASK, RECOVER_TASK,
)
from utopia.optimization.native_designer_tools_v25 import (
    AUTHORING_RECOVERY as PROFILE, PLAIN_FUNCTION_DIRECT as OLD, function_data,
)
from utopia.optimization.native_staged_author_v15 import (
    StagedVocabularyGenerator, transition, initial_draft, build_prompt, build_conversation,
    call_task, host_action_schema, replay_staged_generation,
)
from utopia.optimization.native_designer_wire import wire_record
from utopia.system.design_patch import digest


@pytest.fixture(autouse=True)
def forbid_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('recovery tests must not execute generated code')
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)


class Model(DialogueModel):
    conversation_profile = PROFILE

    def generate(self, **kwargs):
        result = super().generate(**kwargs)
        self.last_transport.update(wire_record(self.last_transport['request_payload'], host_action_schema(PROFILE)))
        return result


def generator(model, path, steps=8):
    return StagedVocabularyGenerator(model, path, image_id=IMAGE, provider_binding=BINDING,
        max_steps=steps, max_tokens=8192, conversation_profile=PROFILE)


def apply(state, action, body):
    return transition(state, action, body, binding_sha256='d' * 64,
        provider_binding=BINDING, conversation_profile=PROFILE)


def step(state, action, body, number):
    state, receipt = apply(state, action, body)
    return state, {'step': number, 'status': 'finished' if receipt['definition'] else
        'applied' if receipt['ok'] else 'rejected', 'model_reply': {'output': action},
        'transition': receipt, 'errors': []}


def test_no_explanation_required_only_in_explicit_profile_and_no_typo_repair():
    body = request(); state = initial_draft(body)
    changed, result = apply(state, {'tool': 'finish'}, body)
    assert result['ok'] and result['definition'] is not None and changed == state
    _, old = transition(state, {'tool': 'finish'}, body, binding_sha256='d' * 64, provider_binding=BINDING)
    assert not old['ok']
    for misspelling in ('rationally', 'rationate', 'rationation', 'rationance'):
        raw = {'tool': 'finish', misspelling: 'untrusted explanation'}
        before = deepcopy(raw)
        _, rejected = apply(state, raw, body)
        assert not rejected['ok'] and raw == before and misspelling in rejected['errors'][0]['message']
    assert 'rationale' not in next(b for b in host_action_schema(PROFILE)['oneOf']
        if b['properties']['tool']['const'] == 'finish')['required']


def test_full_current_document_and_hard_implementation_checkpoint_after_alternating_reads():
    body = request(); state = initial_draft(body); steps = []
    actions = [{'tool': 'plan', 'objective_reasoning': 'SCRIPTED', 'design_intent': 'SCRIPTED'},
        {'tool': 'read_file', 'filename': 'system.json'},
        {'tool': 'read_file', 'filename': 'nodes/arbitrary.alpha-identity.json'},
        {'tool': 'read_file', 'filename': 'system.json'}]
    for i, action in enumerate(actions):
        state, receipt = step(state, action, body, i); steps.append(receipt)
    assert workflow(state, steps, max_steps=16)['phase'] == 'implementation'
    prompt = build_prompt(body, state, steps, image_id=IMAGE, binding_sha256='d' * 64,
        settings={'max_steps': 16, 'conversation_profile': PROFILE})
    task = call_task(4, 16, conversation_profile=PROFILE, prompt=prompt)
    assert task == IMPLEMENT_TASK
    messages = build_conversation(prompt, task, native_tools=True, conversation_profile=PROFILE)
    assert json.loads(prompt)['v44_literal_current_system'] == body['parent_system']
    assert 'literal_current_system' in messages[1]['content']
    schema = backend_format(messages)
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(function_data({'tool': 'read_file', 'filename': 'system.json'}))
    for value in (None, True, 9007199254740993, -2.75, '研究者\n"\\<tool_call>', [1, None], {'x': [False, 2]}):
        Draft202012Validator(schema).validate(function_data({'tool': 'edit',
            'operations': [{'op': 'add', 'path': '/metadata/literal', 'value': value}]}))
    state, receipt = step(state, {'tool': 'edit', 'operations': [
        {'op': 'add', 'path': '/metadata/change', 'value': 1}]}, body, 4)
    assert workflow(state, steps + [receipt], max_steps=16)['phase'] == 'general'


def test_large_draft_is_explicit_not_truncated_or_forced_without_supplied_body():
    body = request(); state = initial_draft(body)
    state['document']['metadata']['large'] = 'x' * 70000
    flow = workflow(state, [{'status': 'applied'}], max_steps=16)
    assert flow['literal_current_system_included'] is False and flow['phase'] == 'general'


def test_submission_envelope_prevents_known_typos_and_keeps_optional_notes_literal():
    messages = [{'role': 'system', 'content': 'V44_ACTION_PHASE=submit'}]
    validate = Draft202012Validator(backend_format(messages))
    validate.validate({'name': 'finish', 'arguments': {}})
    validate.validate({'name': 'finish', 'arguments': {'rationale': '研究者\n"\\',
        'provenance': {'untrusted': [9007199254740993, None, True]}}})
    for spelling in ('rationation', 'rationance', 'rationate', 'rationally'):
        assert list(validate.iter_errors({'name': 'finish', 'arguments': {spelling: 'note'}}))
    assert list(validate.iter_errors({'name': 'write_file', 'arguments': {}}))


def test_reserved_submission_repair_and_cold_replay_charge_failed_first_submission(tmp_path):
    # Four-call budget: planner, first explicit submission, repair, final submission.
    body = request()
    model = Model([{'tool': 'plan', 'objective_reasoning': 'SCRIPTED', 'design_intent': 'SCRIPTED'},
        {'tool': 'finish', 'rationation': 'SCRIPTED deliberately violates backend schema'},
        {'tool': 'edit', 'operations': [{'op': 'add', 'path': '/metadata/repair', 'value': True}]},
        {'tool': 'finish'}])
    result = generator(model, tmp_path, steps=4)(body)
    assert len(model.calls) == 4 and 'generation_failure' not in result
    assert [c['system_prompt'] for c in model.calls][1:] == [SUBMIT_TASK, RECOVER_TASK, SUBMIT_TASK]
    cell = next(tmp_path.glob('generation-*'))
    raw = json.loads((cell / 'step-01.completed.json').read_text())
    assert raw['status'] == 'rejected' and raw['model_reply']['output']['rationation']
    before = {p.name: p.read_bytes() for p in cell.glob('*.json')}
    assert replay_staged_generation(cell) == result and len(model.calls) == 4
    assert before == {p.name: p.read_bytes() for p in cell.glob('*.json')}
    from scripts.analyze_native_staged_search_v15 import _transport, ROLE_CLASSIFICATION
    binding = json.loads((cell / 'request.json').read_text())
    for path in sorted(cell.glob('step-*.completed.json')):
        completed = json.loads(path.read_text())
        started = json.loads(path.with_name(path.name.replace('.completed.', '.started.')).read_text())
        assert _transport(completed, started, binding, ROLE_CLASSIFICATION)['known_HTTP_response']


def test_explicit_retention_without_notes_and_invalid_source_still_rejected(tmp_path):
    body = request()
    model = Model([{'tool': 'plan', 'objective_reasoning': 'SCRIPTED', 'design_intent': 'retention'},
        {'tool': 'finish'}])
    result = generator(model, tmp_path)(body)
    assert result['base_patch'] is None
    state = initial_draft(body)
    state['document']['mechanisms'][0]['parameters']['code_artifact']['source'] = 'invalid ! syntax'
    _, record = apply(state, {'tool': 'finish'}, body)
    assert not record['ok'] and record['definition'] is None


def test_fresh_profile_calibration_binds_submission_format_and_rejects_old_certificate(tmp_path, monkeypatch):
    monkeypatch.setattr('requests.Session', ScriptedSession)
    root = tmp_path / 'new'
    certificate = preflight.run_calibration(root, request=request(), provider=BINDING,
        scope=preflight.EXECUTION_SCOPE, conversation_profile=PROFILE)
    assert certificate['all_controls_passed']
    checked = preflight.require_certificate(root / 'certificate.json', BINDING, protocol='staged-v15',
        scope=preflight.EXECUTION_SCOPE, conversation_profile=PROFILE)
    assert checked['controls'] == len(preflight.planned_cases(request(), 'staged-v15', PROFILE))
    last = certificate['records'][-1]['transport']['request_payload']
    assert isinstance(last['format'], dict) and last['think'] is False
    with pytest.raises(ValueError):
        preflight.require_certificate(root / 'certificate.json', BINDING, protocol='staged-v15',
            scope=preflight.EXECUTION_SCOPE, conversation_profile=OLD)


def test_actual_v43_failures_stay_failed_and_all_misspellings_rejected_by_new_envelope():
    location = os.environ.get('UTOPIA_V43_ARCHIVE')
    if not location:
        pytest.skip('optional read-only original V43 archive')
    root = Path(location); before = {str(p): p.read_bytes() for p in root.glob('queue/*/authoring/*/response.json')}
    validate = Draft202012Validator(backend_format([{'role': 'system', 'content': 'V44_ACTION_PHASE=submit'}]))
    failures = 0
    for path in root.glob('queue/*/authoring/*/step-07.completed.json'):
        step_value = json.loads(path.read_text())
        if step_value['status'] == 'rejected':
            assert list(validate.iter_errors(function_data(step_value['model_reply']['output'])))
            failures += 1
    assert failures == 5
    assert before == {str(p): p.read_bytes() for p in root.glob('queue/*/authoring/*/response.json')}


def test_invalid_source_gets_one_explicit_model_repair_then_resubmission(tmp_path):
    source = request()['parent_system']['mechanisms'][0]['parameters']['code_artifact']['source']
    filename = 'code/arbitrary.alpha-identity.py'
    model = Model([{'tool': 'plan', 'objective_reasoning': 'SCRIPTED', 'design_intent': 'SCRIPTED'},
        {'tool': 'write_file', 'filename': filename, 'content': 'invalid ! syntax'},
        {'tool': 'read_file', 'filename': filename}, {'tool': 'finish'},
        {'tool': 'write_file', 'filename': filename, 'content': source}, {'tool': 'finish'}])
    result = generator(model, tmp_path, steps=6)(request())
    assert 'generation_failure' not in result and len(model.calls) == 6
    cell = next(tmp_path.glob('generation-*'))
    assert json.loads((cell / 'step-03.completed.json').read_text())['status'] == 'rejected'
    assert model.calls[4]['system_prompt'] == RECOVER_TASK
    assert replay_staged_generation(cell) == result


def test_all_failed_attempts_remain_charged_and_never_auto_submit(tmp_path):
    model = Model([{'tool': 'plan', 'objective_reasoning': 'SCRIPTED', 'design_intent': 'SCRIPTED'},
        *[{'tool': 'finish', 'rationation': 'known invalid raw action'} for _ in range(3)]])
    result = generator(model, tmp_path, steps=4)(request())
    assert 'generation_failure' in result and len(model.calls) == 4
    cell = next(tmp_path.glob('generation-*'))
    assert len(list(cell.glob('step-*.started.json'))) == 4
    assert replay_staged_generation(cell) == result and len(model.calls) == 4


def test_implementation_stage_can_author_code_after_bounded_inspection(tmp_path):
    original = request()['parent_system']['mechanisms'][0]['parameters']['code_artifact']['source']
    edited = original + '\n# literal model-authored SCRIPTED checkpoint edit\n'
    model = Model([{'tool': 'plan', 'objective_reasoning': 'SCRIPTED', 'design_intent': 'SCRIPTED'},
        {'tool': 'read_file', 'filename': 'system.json'},
        {'tool': 'read_file', 'filename': 'code/arbitrary.alpha-identity.py'},
        {'tool': 'read_file', 'filename': 'system.json'},
        {'tool': 'write_file', 'filename': 'code/arbitrary.alpha-identity.py', 'content': edited},
        {'tool': 'finish'}])
    result = generator(model, tmp_path, steps=8)(request())
    assert 'generation_failure' not in result
    assert model.calls[4]['system_prompt'] == IMPLEMENT_TASK
    cell = next(tmp_path.glob('generation-*'))
    fourth = json.loads((cell / 'step-04.completed.json').read_text())
    assert fourth['model_reply']['transport']['request_payload']['format']['properties']['name']['enum']
    assert fourth['model_reply']['output']['content'] == edited
    assert fourth['transition']['document_before_sha256'] != fourth['transition']['document_after_sha256']
    assert replay_staged_generation(cell) == result


@pytest.mark.parametrize('literal', [None, True, 9007199254740993, -2.75,
    '研究者\n"quoted" \\ literal\\n <tool_call>data</tool_call>', [None, 3], {'x': [True, 9007199254740993]}])
def test_implementation_grammar_keeps_every_literal_json_type(literal):
    action = {'name': 'edit', 'arguments': {'operations': [
        {'op': 'add', 'path': '/metadata/自由', 'value': literal}]}}
    schema = backend_format([{'role': 'system', 'content': 'V44_ACTION_PHASE=implementation'}])
    Draft202012Validator(schema).validate(action)
    assert json.loads(json.dumps(action, ensure_ascii=False)) == action
