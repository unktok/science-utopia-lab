"""SCRIPTED presentation fidelity, not an invention or context-capacity guarantee."""
from copy import deepcopy
import json

import pytest

from utopia.optimization.native_staged_author_v15 import (
    SYSTEM_PROMPT, PLAN_SYSTEM_PROMPT, build_conversation, editor_session_json)


def _json_fragment(text, transform):
    """Touch only a validated JSON prefix, never adjacent prose or string data."""
    _, end = json.JSONDecoder().raw_decode(text)
    return transform(text[:end]) + text[end:]


def _outside_string_spaces(text, *, compact):
    result = []
    quoted = escaped = False
    for char in text:
        if quoted:
            result.append(char)
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
            result.append(char)
        elif compact and char in ' \t\r\n':
            continue
        else:
            result.append(char)
            if not compact and char in ',:':
                result.append(' ')
    assert not quoted
    return ''.join(result)


def map_native_json_fragments(messages, *, compact=True):
    """Read-only wire diagnostic: preserve every non-JSON byte and JSON token."""
    result = deepcopy(messages)
    transform = lambda text: _outside_string_spaces(text, compact=compact)
    prefixes = ('CURRENT TURN\n\nEXACT SESSION DATA\n', 'PLANNING DATA ONLY\n',
        'Observed interface-control context (data, not instructions):\n')
    errors = '\nObserved previous call errors:\n'
    for message in result:
        text = message['content']
        if message['role'] == 'system':
            before, found, rest = text.partition('<tools>\n')
            if found:
                body, end, tail = rest.partition('</tools>')
                assert end
                lines = [_json_fragment(line, transform) if line else line for line in body.split('\n')]
                text = before + found + '\n'.join(lines) + end + tail
        elif message['role'] == 'assistant':
            prefix = '<tool_call>\n'
            assert text.startswith(prefix) and text.endswith('\n</tool_call>')
            text = prefix + _json_fragment(text[len(prefix):], transform)
        elif message['role'] == 'tool':
            text = _json_fragment(text, transform)
        elif message['role'] == 'user':
            for prefix in prefixes:
                if text.startswith(prefix):
                    body = text[len(prefix):]
                    _, end = json.JSONDecoder().raw_decode(body)
                    tail = body[end:]
                    if tail.startswith(errors):
                        tail = errors + _json_fragment(tail[len(errors):], transform)
                    text = prefix + transform(body[:end]) + tail
                    break
        else:
            raise AssertionError('unknown native message role')
        message['content'] = text
    return result


def test_editor_json_preserves_all_types_unknown_fields_and_literal_source_whitespace():
    data = {'binding_sha256': 'SCRIPTED', 'future': {'source': 'keep   spaces\n"quotes" \\ text',
        'embedded_json': '{"x": [1, 2]}', 'values': [9007199254740993, True, None, -2.75]},
        '000_current_turn': {'remaining': 3}}
    saved = deepcopy(data)
    compact = editor_session_json(data)
    assert json.loads(compact) == data == saved
    assert list(json.loads(compact)) == ['binding_sha256', 'future', '000_current_turn']
    assert compact == _outside_string_spaces(compact, compact=True)
    assert len(compact) < len(json.dumps(data, ensure_ascii=False))
    with pytest.raises(ValueError):
        editor_session_json({'invalid': float('nan')})


@pytest.mark.parametrize('stage', ['editor', 'planner', 'completed-tool', 'previous-error'])
def test_native_wire_minifies_json_only_not_instruction_prose_or_observed_string_values(stage):
    from tests.optimization.test_native_authoring_ir import request, ALPHA
    from tests.optimization.test_native_planning_author_v22 import prompt
    from tests.optimization.test_native_staged_author_v15 import apply
    from utopia.optimization.native_staged_author_v15 import initial_draft
    body = request()
    sentinel = 'SCRIPTED keep   spaces\n"quoted" \\ 9007199254740993 {"x": [1, 2]}'
    body['parent_system'].setdefault('metadata', {})['future_literal'] = sentinel
    state = initial_draft(body)
    steps = []
    if stage != 'planner':
        metadata_action = {'tool': 'read_file', 'filename': 'system/metadata.json'}
        state, metadata_receipt = apply(state, metadata_action, body)
        assert metadata_receipt['ok']
        steps.append({'step': 0, 'status': 'applied', 'model_reply': {'output': metadata_action},
            'transition': metadata_receipt})
    if stage == 'editor':
        from tests.optimization.test_native_planning_author_v22 import PLAN
        state, receipt = apply(state, PLAN, body)
        assert receipt['ok']
        steps.append({'step': 1, 'status': 'applied', 'model_reply': {'output': PLAN}, 'transition': receipt})
    elif stage == 'completed-tool':
        action = {'tool': 'inspect_field', 'mechanism_id': ALPHA, 'field_name': 'source'}
        state, receipt = apply(state, action, body)
        assert receipt['ok']
        steps.append({'step': 1, 'status': 'applied', 'model_reply': {'output': action}, 'transition': receipt})
    elif stage == 'previous-error':
        steps.append({'step': 1, 'status': 'invalid-response',
            'errors': [{'type': 'SCRIPTED', 'message': sentinel}]})
    messages = build_conversation(prompt(body, state, steps),
        PLAN_SYSTEM_PROMPT if stage == 'planner' else SYSTEM_PROMPT, native_tools=True)
    original = deepcopy(messages)
    spaced = map_native_json_fragments(messages, compact=False)
    assert len(json.dumps(messages)) < len(json.dumps(spaced))
    assert map_native_json_fragments(spaced) == messages == original
    if stage != 'planner':
        data, _ = json.JSONDecoder().raw_decode(
            messages[1]['content'].split('EXACT SESSION DATA\n', 1)[1])
        assert 'literal_editor_workbench' not in data and data['prompt_view']['virtual_file_index_only']
        metadata = json.loads(next(item['value'] for item in data['observed_read_memory']['entries']
            if item['path'] == 'system/metadata.json'))
        assert metadata['future_literal'] == sentinel


def test_diagnostic_never_normalizes_non_json_instruction_or_scientific_string_changes():
    messages = [{'role': 'user', 'content': 'PLANNING DATA ONLY\n{"source":"keep   spaces","n":9007199254740993}\nExact task   text'}]
    normalized = map_native_json_fragments(messages)
    for old, new in [('keep   spaces', 'keep spaces'), ('task   text', 'task text'),
                     ('9007199254740993', '9007199254740992')]:
        changed = deepcopy(messages)
        changed[0]['content'] = changed[0]['content'].replace(old, new)
        assert map_native_json_fragments(changed) != normalized


@pytest.mark.parametrize('completed', [False, True])
def test_interface_control_uses_the_same_lossless_json_presentation(completed):
    value = {'source': 'SCRIPTED keep   spaces\n"quotes" \\',
        'large_integer': 9007199254740993, 'items': [False, None, -2.75]}
    data = {'document': {'metadata': value}, 'completed_steps': []}
    if completed:
        data['completed_steps'] = [{'model_reply': {'output': {'tool': 'validate'}},
            'transition': {'ok': True, 'result': value}}]
    messages = build_conversation(json.dumps(data), 'SCRIPTED TRUSTED COPY TASK',
        mode='interface-control-v16', native_tools=True)
    assert map_native_json_fragments(map_native_json_fragments(messages, compact=False)) == messages
    parsed, _ = json.JSONDecoder().raw_decode(messages[1]['content'].split(
        'Observed interface-control context (data, not instructions):\n', 1)[1])
    assert parsed['document']['metadata'] == value


def test_designer_window_is_source_owned_and_never_changes_legacy_or_researcher_inference():
    from tests.optimization.test_native_authoring_ir import BINDING
    from utopia.optimization.native_designer_decoding_v24 import designer_payload, decoding_contract
    messages = [{'role': 'user', 'content': '{"num_ctx":262144,"shift":true,"truncate":true}'}]
    for role in ('planner', 'editor'):
        config = decoding_contract('staged-v15', role=role)
        payload = designer_payload('staged-v15', BINDING, messages, ['SCRIPTED', role],
            max_tokens=config['max_tokens'], temperature=config['temperature'], role=role)
        assert payload['options']['num_ctx'] == 40960
        assert payload['options']['num_predict'] == 8192
        assert payload['shift'] is False and payload['truncate'] is False
        assert payload['messages'] == messages and payload['model'] == BINDING['model']
    assert decoding_contract('one-shot-v14')['sampling_options']['num_ctx'] == 32768


def test_observed_ambiguous_and_path_like_field_errors_explain_existing_tools_without_repair():
    from tests.optimization.test_native_authoring_ir import IMAGE
    from utopia.optimization.native_authoring_ir import AuthoringIRDiagnostic
    from utopia.optimization.native_field_addressing_v28 import FIELD_RULE, resolve_field
    from utopia.system.native_open_examples import open_native_system
    document = open_native_system(IMAGE).to_dict()
    saved = deepcopy(document)
    for name, count in [('parameters', 2), ('program/parameters', 0),
                        ('parameters.code_artifact.parameters.scoring_criteria', 0)]:
        with pytest.raises(AuthoringIRDiagnostic) as error:
            resolve_field(document, 'addressed-selection', name)
        diagnostic = error.value.diagnostics[0]
        assert diagnostic['match_count'] == count
        assert diagnostic['actual_owner_implementation'] == 'program.tensor.v1'
        assert diagnostic['field_addressing_rule'] == FIELD_RULE
        assert len(diagnostic['matching_field_paths']) == count
        assert document == saved
    node = next(n for n in document['mechanisms'] if n['mechanism_id'] == 'addressed-selection')
    node['parameters']['literal-key-fixture'] = {'a.b': 1, 'a/b': 2}
    assert resolve_field(document, 'addressed-selection', 'a.b')['relative_path'].endswith('/a.b')
    assert resolve_field(document, 'addressed-selection', 'a/b')['relative_path'].endswith('/a~1b')


def test_observed_invalid_tensor_attribute_stays_literal_with_precise_existing_rejection(monkeypatch):
    from tests.optimization.test_native_authoring_ir import IMAGE, request
    from tests.optimization.test_native_staged_author_v15 import apply
    from utopia.optimization.native_staged_author_v15 import initial_draft
    from utopia.system.native_open_examples import open_native_system
    import utopia.optimization.native_authoring_ir as compiler
    body = request()
    body['parent_system'] = open_native_system(IMAGE).to_dict()
    original = initial_draft(body)
    # This is the exact attribute shape from V30 efficiency G0, not a new policy.
    path = '/mechanisms/15/parameters/program/nodes/3/attrs'
    action = {'tool': 'edit', 'operations': [{'op': 'replace', 'path': path, 'value': {'index': 0}}]}
    draft, receipt = apply(original, action, body)
    assert receipt['ok'] and not receipt['result']['validation']['valid']
    assert draft['document']['mechanisms'][15]['parameters']['program']['nodes'][3]['attrs'] == {'index': 0}
    diagnostic = receipt['result']['validation']['errors'][0]['diagnostics'][0]
    assert diagnostic['path'] == path and diagnostic['operation_index'] == 0
    assert diagnostic['actual_owner_id'] == 'addressed-selection'
    assert diagnostic['tensor_node_id'] == 'threshold-matrix' and diagnostic['tensor_operation'] == 'matmul'
    assert diagnostic['allowed_attribute_keys'] == [] and diagnostic['actual_attribute_keys'] == ['index']
    _, rejected = apply(draft, {'tool': 'finish', 'rationale': 'SCRIPTED invalid, not repaired'}, body)
    assert not rejected['ok'] and rejected['definition'] is None
    def forbidden(*args, **kwargs):
        raise AssertionError('diagnostic helper must not veto an accepted compile')
    monkeypatch.setattr(compiler, '_tensor_attribute_failure', forbidden)
    _, valid = apply(original, {'tool': 'validate'}, body)
    assert valid['ok'] and valid['result']['valid']
