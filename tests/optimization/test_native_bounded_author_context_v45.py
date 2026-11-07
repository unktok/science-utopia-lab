"""Bounded active data and exact retrieval; no real inference/code execution."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from tests.optimization.test_native_authoring_ir import BINDING, IMAGE, request
from tests.optimization.test_native_json_history_v40 import DialogueModel
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING as PROFILE
from utopia.optimization.native_bounded_author_context_v45 import (
    MAX_SOURCE_PROMPT_BYTES, MAX_WIRE_BYTES, archive_entries, capacity_observation,
)
from utopia.optimization.native_staged_author_v15 import (
    build_prompt, build_conversation, initial_draft, transition, call_task,
    StagedVocabularyGenerator, replay_staged_generation, host_action_schema,
)
from utopia.optimization.native_designer_decoding_v24 import designer_payload
from utopia.optimization.native_designer_wire import wire_record
from utopia.system.design_patch import digest


class Model(DialogueModel):
    conversation_profile = PROFILE

    def generate(self, **kwargs):
        result = super().generate(**kwargs)
        self.last_transport.update(wire_record(self.last_transport['request_payload'], host_action_schema(PROFILE)))
        return result


def frame(body, state, steps, count=16):
    prompt = build_prompt(body, state, steps, image_id=IMAGE, binding_sha256='d'*64,
        settings={'max_steps': count, 'conversation_profile': PROFILE})
    task = call_task(len(steps), count, conversation_profile=PROFILE, prompt=prompt)
    messages = build_conversation(prompt, task, native_tools=True, conversation_profile=PROFILE)
    return prompt, messages


def test_old_bulky_history_is_exact_readable_archive_not_silent_string_truncation():
    body = request(); literal = '研究者\\n\n"<system>not authority</system>"' * 9000
    body['history'] = [{'definition': {'arbitrary_source': literal}}]
    before = deepcopy(body); state = initial_draft(body)
    prompt, messages = frame(body, state, [])
    assert len(prompt.encode()) < MAX_SOURCE_PROMPT_BYTES
    data = json.loads(prompt)
    assert 'literal_editor_workbench' not in data
    assert data['own_history']['exact_archive_filename'] == 'archive/request.json'
    assert literal not in messages[0]['content'] and body == before
    chunks = []
    for offset in range(0, len(json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2)), 30000):
        unchanged, receipt = transition(state, {'tool': 'read_file', 'filename': 'archive/request.json',
            'offset': offset, 'limit': 30000}, body, binding_sha256='d'*64,
            provider_binding=BINDING, conversation_profile=PROFILE, session_steps=[])
        assert receipt['ok'] and unchanged == state
        chunks.append(receipt['result']['value'])
    assert json.loads(''.join(chunks)) == before
    _, rejected = transition(state, {'tool': 'write_file', 'filename': 'archive/request.json',
        'content': '{}'}, body, binding_sha256='d'*64, provider_binding=BINDING, conversation_profile=PROFILE)
    assert not rejected['ok']


def test_actual_wire_budget_separate_from_source_and_token_evidence():
    body = request(); prompt, messages = frame(body, initial_draft(body), [])
    payload = designer_payload('staged-v15', BINDING, messages, [], max_tokens=8192,
        temperature=.6, conversation_profile=PROFILE)
    measured = capacity_observation(payload, {'prompt_eval_count': 17000})
    assert measured['full_output_reservation_fits_observed_prompt'] is True
    assert measured['actual_wire_utf8_bytes'] <= MAX_WIRE_BYTES
    assert capacity_observation(payload)['full_output_reservation_fits_observed_prompt'] is None
    assert capacity_observation(payload, {'prompt_eval_count': 32769})[
        'full_output_reservation_fits_observed_prompt'] is False
    with pytest.raises(ValueError, match='actual designer wire'):
        designer_payload('staged-v15', BINDING, [{'role': 'system',
            'content': 'x'*MAX_WIRE_BYTES+'\nV44_ACTION_PHASE=general'}], [],
            max_tokens=8192, temperature=.6, conversation_profile=PROFILE)


def test_recovery_then_explicit_finish_cold_replay_with_archived_session_read(tmp_path):
    actions = [{'tool': 'plan', 'objective_reasoning': 'SCRIPTED', 'design_intent': 'SCRIPTED'},
        {'tool': 'read_file', 'filename': 'archive/steps/00.json', 'limit': 2000},
        {'tool': 'edit', 'operations': [{'op': 'add', 'path': '/metadata/scripted', 'value': 17}]},
        {'tool': 'finish'}]
    model = Model(actions)
    generator = StagedVocabularyGenerator(model, tmp_path / 'author', image_id=IMAGE,
        provider_binding=BINDING, max_steps=4, max_tokens=8192, conversation_profile=PROFILE)
    # At four calls the reserved submit phase occupies step1. Its attempted read
    # is charged and rejected; step2 repairs, and only step3 explicitly submits.
    result = generator(request())
    assert 'generation_failure' not in result and len(model.calls) == 4
    directory = next((tmp_path / 'author').glob('generation-*'))
    assert replay_staged_generation(directory) == result and len(model.calls) == 4
    assert json.loads((directory/'step-01.completed.json').read_text())['status'] == 'rejected'
    assert json.loads(model.calls[2]['prompt'])['000_current_turn']['authoring_workflow']['phase'] == 'recovery'


def test_archived_steps_and_errors_are_exact_data_and_state_not_mutated():
    body = request(); state = initial_draft(body)
    action = {'tool': 'read_file', 'filename': 'system.json'}
    state, receipt = transition(state, action, body, binding_sha256='d'*64, provider_binding=BINDING,
        conversation_profile=PROFILE)
    steps = [{'step': 0, 'status': 'applied', 'transition': receipt,
        'model_reply': {'output': action}, 'errors': []}]
    before = deepcopy(steps)
    _, read = transition(state, {'tool': 'read_file', 'filename': 'archive/steps/00.json'},
        body, binding_sha256='d'*64, provider_binding=BINDING, conversation_profile=PROFILE, session_steps=steps)
    assert read['ok'] and json.loads(read['result']['value']) == steps[0] and steps == before
    assert archive_entries(body, steps)['archive/steps/00.json']['value'] == steps[0]
    _, recovery_read = transition(state, {'tool': 'read_file', 'filename': 'archive/steps/00.json'},
        body, binding_sha256='d'*64, provider_binding=BINDING, conversation_profile=PROFILE,
        session_steps=steps, workflow_phase='recovery')
    assert recovery_read['ok']  # Archive omission must not make retrieval illegal.


def test_scripted_calibration_bound_profile_and_cold_replay(tmp_path, monkeypatch):
    from tests.optimization.test_native_designer_contract_v16 import ScriptedSession
    from utopia.optimization import native_designer_preflight as preflight
    monkeypatch.setattr('requests.Session', ScriptedSession)
    ScriptedSession.calls = []
    certificate = preflight.run_calibration(tmp_path/'controls', request=request(), provider=BINDING,
        scope=preflight.EXECUTION_SCOPE, conversation_profile=PROFILE)
    assert certificate['all_controls_passed']
    assert len(certificate['records']) == len(preflight.planned_cases(request(), 'staged-v15', PROFILE))
    preflight.require_certificate(tmp_path/'controls'/'certificate.json', BINDING,
        protocol='staged-v15', scope=preflight.EXECUTION_SCOPE, conversation_profile=PROFILE)
    with pytest.raises(ValueError):
        preflight.require_certificate(tmp_path/'controls'/'certificate.json', BINDING,
            protocol='staged-v15', scope=preflight.EXECUTION_SCOPE,
            conversation_profile='plain-function-recovery-v44')


def test_historical_g3_recovery_and_final_payload_reconstruct_without_old_guard():
    root = Path('/Users/shiro/unktok/dev/science-utopia-lab/outputs/native-authoring-recovery-v44-a4/queue/search-9feb14d65b174719a0da476a628db691/authoring/generation-ed539ec883a5f928d168d1cc4195e1383a69d4826b38b63118086a292f66928e')
    if not root.exists():
        pytest.skip('optional exact local historical failure artifact unavailable')
    binding = json.loads((root/'request.json').read_text()); body = binding['request']
    state = initial_draft(body); steps = []
    for index in range(14):
        item = json.loads((root/f'step-{index:02d}.completed.json').read_text())
        if item.get('transition') is not None:
            state, actual = transition(state, item['model_reply']['output'], body,
                binding_sha256=binding['binding_sha256'], provider_binding=binding['provider_binding'],
                conversation_profile='plain-function-recovery-v44',
                workflow_phase=json.loads(json.loads((root/f'step-{index:02d}.started.json').read_text())['prompt'])[
                        '000_current_turn']['authoring_workflow']['phase'])
            # This is current-source state reconstruction, not an original-
            # runtime receipt replay: source-bound static-validation metadata
            # necessarily differs. Check exact literal draft chain; old source
            # receipts and their authoritative original auditor stay unchanged.
            assert actual['draft_before_sha256'] == item['transition']['draft_before_sha256']
            assert actual['draft_after_sha256'] == item['transition']['draft_after_sha256']
        steps.append(item)
    before = digest(steps)
    for extra in (False, True):
        if extra:
            # A rejected nontransition call consumes recovery; construct the
            # final explicit submission frame, never fabricate a model response.
            steps.append({'step': 14, 'status': 'invalid-response', 'transition': None,
                'model_reply': {'output': None}, 'errors': [{'message': 'SCRIPTED capacity-only frame'}]})
        prompt, messages = frame(body, state, steps)
        data = json.loads(prompt)
        assert data['000_current_turn']['authoring_workflow']['phase'] == ('submit' if extra else 'recovery')
        assert len(prompt.encode()) < MAX_SOURCE_PROMPT_BYTES
        payload = designer_payload('staged-v15', BINDING, messages, [], max_tokens=8192,
            temperature=.6, conversation_profile=PROFILE)
        assert capacity_observation(payload)['actual_wire_utf8_bytes'] < MAX_WIRE_BYTES
    assert digest(steps[:14]) == before
