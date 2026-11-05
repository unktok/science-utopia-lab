"""Lossless function JSON responses and canonical Hermes completed history.

These are general editing tools, not an institution catalogue. The adapter
only separates a model-authored function name from its literal arguments.
It never fills fields, repairs source, executes a candidate or reads reasoning
as an action. Actual-backend readiness is a separate requirement.
"""
import json

from utopia.system.design_patch import clone

CHANNEL = 'scienceutopia.designer-function-json.v26'
CONVERSATION_SUFFIX = '.conversation.function-json.v26'
TOOL_RESPONSE_ONLY = (
    'Call exactly one supplied function for the next action. '
    'Return exactly one JSON object in final response content: '
    '{"name":"FUNCTION_NAME","arguments":{...}}. '
    'Do not wrap the NEW response in XML/tool_call tags, prose or Markdown. '
    'Completed assistant history may use Hermes tags; it is not the new response format. '
    'The function name is the action tool; arguments contain the remaining action fields, '
    'without a tool field. Preserve exact JSON types and string code points, '
    'including real line feeds, quotes and literal backslashes. '
    'Do not add an extra JSON encoding layer. Separate reasoning and ordinary '
    'prose are not executable actions.')

CONTROL_TARGET_NOTE = (
    'The JSON below is target DATA, not a previous assistant call or a completed tool result. '
    'Copy its function name and every literal argument into one NEW JSON function object. '
    'Use exactly its argument keys: do not add optional arguments, defaults or notes, '
    'and do not carry fields over from a previous call. '
    'Do not claim that the target action has already executed. Do not substitute finish; '
    'return finish only when the target function name itself is finish. ')

DESCRIPTIONS = {
    'inspect_field': 'Read a uniquely named JSON field inside the exact mechanism ID. No array-index guessing. '
        'Missing/ambiguous fields reject without selecting a substitute. Arbitrary code strings are data.',
    'edit_fields': 'Atomically replace uniquely named existing fields inside the exact mechanism ID, including '
        'arbitrary literal code or programs. Use field_name_index in the workbench. Missing/ambiguous fields '
        'reject without repair. Original edit still supports arbitrary new nodes, fields, removals and wiring.',
    'plan': 'Store your own institutional design hypothesis; this does not implement or execute it.',
    'inspect': ('Read an exact current draft JSON address or a trusted capability ABI. No candidate mutation. '
        'Without selector, path is relative to the whole document. With selector, path is relative '
        'to that mechanism only. A document-root address must not carry a mechanism selector '
        'from a previous call. Reuse a returned reusable_address as one complete address form. '
        'mechanisms is an array: use a numeric array index in a root path, or an exact '
        'mechanism_id selector with a mechanism-relative path. Free-text plan targets are '
        'hypotheses, not guaranteed existing JSON addresses.'),
    'edit': 'Apply your literal atomic add/remove/replace edits to arbitrary system JSON, code and wiring.',
    'splice': 'Edit any existing string by Unicode codepoints, including arbitrary literal Python source.',
    'configure': 'Set an optional distribution over authored literal edits, not institutional behavior by itself.',
    'validate': 'Check the current graph/source/ABI statically. Does not measure a scientific loss.',
    'finish': 'Submit the current candidate if technically valid, with your rationale. Retention is legal.',
}


def tool_specifications(*, role=None):
    """Derive parameter schemas from the authoritative host contract.

    No hand-maintained copy of operation/value schemas and no backend grammar
    that would narrow arbitrary JSON operands. Every host-valid action remains
    expressible, including retention and every optional author annotation.
    """
    from .native_staged_author_v15 import ACTION_FIELDS, TOOL_FIELDS, EDITOR_ACTION_SCHEMA, _tool_schema
    if role not in (None, 'planner', 'editor', 'finisher'):
        raise ValueError('unknown source-owned tool advertisement role')
    names = (['finish'] if role == 'finisher' else list(TOOL_FIELDS) if role != 'editor' else
        [part['properties']['tool']['const'] for part in EDITOR_ACTION_SCHEMA['oneOf']])
    result = []
    for name in names:
        fields = TOOL_FIELDS[name]
        parameters = _tool_schema(name, *fields)
        parameters['required'].remove('tool')
        del parameters['properties']['tool']
        # Ollama's typed ToolProperty does not retain $ref. Inline the actual
        # shared fields before transport instead of advertising empty argument
        # schemas after the server renders its model template.
        parameters['properties'] = {key: clone(ACTION_FIELDS[key]) for key in parameters['properties']}
        result.append({'type': 'function', 'function': {
            'name': name, 'description': DESCRIPTIONS[name], 'parameters': parameters}})
    return result


def native_instruction_semantics(instructions):
    """Keep every tool explanation, without redundant host-envelope examples.

    Function schemas are already advertised separately. These are trusted,
    source-owned examples, never model/source text or a response repair path.
    """
    from .native_staged_author_v15 import TOOL_FIELDS
    decoder = json.JSONDecoder()
    cursor, parts, names = 0, [], []
    import re
    for match in re.finditer(r'(?m)^  \{"tool":', instructions):
        if match.start() < cursor:
            continue
        action, length = decoder.raw_decode(instructions[match.start() + 2:])
        parts.extend([instructions[cursor:match.start()], '  Function ' + action['tool'] + ':'])
        names.append(action['tool'])
        cursor = match.start() + 2 + length
    parts.append(instructions[cursor:])
    if len(names) != len(TOOL_FIELDS) or set(names) != set(TOOL_FIELDS):
        raise ValueError('source-owned tool example inventory differs from host functions')
    return ''.join(parts).replace('Return ONE JSON tool action per turn.', TOOL_RESPONSE_ONLY)


def action_from_message(message):
    """Decode one complete function object; never salvage prefixes/thinking/code.

    Host action validation remains in the existing interpreter, so invalid
    literal arguments can receive its normal charged technical feedback.
    Multiple calls are rejected as a whole, not silently tail-dropped or
    executed as extra unbudgeted steps.
    """
    if not isinstance(message, dict) or message.get('role') != 'assistant':
        raise ValueError('native designer response is not an assistant message')
    if message.get('tool_calls'):
        raise ValueError('backend-parsed tool calls are not the lossless function JSON response channel')
    content = message.get('content')
    if not isinstance(content, str):
        raise ValueError('designer must return one JSON function object; no content fallback')
    from .native_search_generator_v14 import _strict_json
    function = _strict_json(content)
    if not isinstance(function, dict) or set(function) != {'name', 'arguments'}:
        raise ValueError('JSON function call must contain exactly name and arguments')
    if (not isinstance(function, dict) or not isinstance(function.get('name'), str)
            or function['name'] not in DESCRIPTIONS):
        raise ValueError('native designer function name is unknown')
    arguments = function.get('arguments')
    if not isinstance(arguments, dict) or 'tool' in arguments:
        raise ValueError('native designer arguments must be a literal object without tool')
    # clone rejects non-JSON/nonfinite Python values without coercion.
    return {'tool': function['name'], **clone(arguments)}


def function_data(action):
    """Separate literal name/arguments without asserting execution or dispatch."""
    if (not isinstance(action, dict) or not isinstance(action.get('tool'), str)
            or action['tool'] not in DESCRIPTIONS):
        raise ValueError('cannot serialize an action with an unknown native function')
    return {'name': action['tool'],
        'arguments': clone({key: value for key, value in action.items() if key != 'tool'})}


def message_from_action(action):
    """Serialize completed history, never dispatch or replace a provider reply."""
    function = function_data(action)
    return {'role': 'assistant', 'content': '<tool_call>\n'
        + json.dumps(function, ensure_ascii=False, allow_nan=False) + '\n</tool_call>'}


def response_message_from_action(action):
    """Fixture serializer for the new response channel; never used to repair replies."""
    return {'role': 'assistant', 'content': json.dumps(function_data(action),
        ensure_ascii=False, allow_nan=False)}


def action_from_body(body):
    """One completion check shared by live decoding and independent cold replay."""
    if not isinstance(body, dict) or body.get('done') is not True or body.get('done_reason') == 'length':
        raise ValueError('designer output is incomplete/truncated; no source repair')
    return action_from_message(body.get('message'))


def tool_system_prompt(*, role=None):
    """Use the model's trained Hermes syntax without Ollama's lossy argument map.

    Ollama0.33.3's native argument-map JSON decoding has float64 round-trip
    risk above2**53, including previous assistant calls sent as history. Here
    schemas, actions and receipts remain strings, without entering that map.
    The existing strict JSON decoder owns all nested numbers.
    This does not install/alter a backend template or execute generated code.
    """
    return ('\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\n'
        'You are provided with function signatures within <tools></tools> XML tags:\n<tools>\n'
        + '\n'.join(json.dumps(tool, ensure_ascii=False, allow_nan=False) for tool in tool_specifications(role=role))
        + '\n</tools>\n\n' + TOOL_RESPONSE_ONLY)


def reply_action(reply):
    """Bind a native action to its original body, or decode SCRIPTED legacy text.

    Actual native transports never fall back to content when a call is missing.
    The legacy branch supports existing explicit non-provider test models;
    production transport auditors independently require the native channel.
    """
    from .native_search_generator_v14 import _strict_json, _assistant_text
    transport = reply.get('transport') or {}
    if transport.get('response_channel') is None:
        return _strict_json(_assistant_text(reply['messages']))
    if transport['response_channel'] != CHANNEL:
        raise ValueError('unknown designer response channel')
    body = _strict_json(transport['raw_http_response'])
    if body != transport['response_payload'] or not reply['messages'] or reply['messages'][-1] != body['message']:
        raise ValueError('native designer message differs from original HTTP body')
    return action_from_body(body)
