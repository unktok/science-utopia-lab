"""Lossless Qwen Hermes tool envelopes for the existing institutional editor.

These are general editing tools, not an institution catalogue. The adapter
only separates a model-authored function name from its literal arguments.
It never fills fields, repairs source, executes a candidate or reads reasoning
as an action. Actual-backend readiness is a separate requirement.
"""
import json
import re

from utopia.system.design_patch import clone

CHANNEL = 'scienceutopia.hermes-designer-tools.v25'
TOOL_RESPONSE_ONLY = (
    'Call exactly one supplied function for the next action. '
    'Use the Qwen Hermes tool-call envelope in final response content: '
    '<tool_call>{"name":"FUNCTION_NAME","arguments":{...}}</tool_call>. '
    'Return only that one envelope, without prose, Markdown or a bare JSON action. '
    'The function name is the action tool; arguments contain the remaining action fields, '
    'without a tool field. Preserve exact JSON types and string code points, '
    'including real line feeds, quotes and literal backslashes. '
    'Do not add an extra JSON encoding layer. Separate reasoning and ordinary '
    'prose are not executable actions. Only finish submits a candidate.')

DESCRIPTIONS = {
    'plan': 'Store your own institutional design hypothesis; this does not implement or execute it.',
    'inspect': 'Read an exact current draft JSON address or a trusted capability ABI. No candidate mutation.',
    'edit': 'Apply your literal atomic add/remove/replace edits to arbitrary system JSON, code and wiring.',
    'splice': 'Edit any existing string by Unicode codepoints, including arbitrary literal Python source.',
    'configure': 'Set an optional distribution over authored literal edits, not institutional behavior by itself.',
    'validate': 'Check the current graph/source/ABI statically. Does not measure a scientific loss.',
    'finish': 'Submit the current candidate if technically valid, with your rationale. Retention is legal.',
}


def tool_specifications():
    """Derive all seven parameter schemas from the authoritative host contract.

    No hand-maintained copy of operation/value schemas and no backend grammar
    that would narrow arbitrary JSON operands. Every host-valid action remains
    expressible, including retention and every optional author annotation.
    """
    from .native_staged_author_v15 import ACTION_FIELDS, TOOL_FIELDS, _tool_schema
    result = []
    for name, fields in TOOL_FIELDS.items():
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


def action_from_message(message):
    """Decode one complete Hermes call; never salvage prefixes/thinking/code.

    Host action validation remains in the existing interpreter, so invalid
    literal arguments can receive its normal charged technical feedback.
    Multiple calls are rejected as a whole, not silently tail-dropped or
    executed as extra unbudgeted steps.
    """
    if not isinstance(message, dict) or message.get('role') != 'assistant':
        raise ValueError('native designer response is not an assistant message')
    if message.get('tool_calls'):
        raise ValueError('backend-parsed tool calls are not the lossless Hermes response channel')
    content = message.get('content')
    match = re.fullmatch(r'\s*<tool_call>\s*([\s\S]+?)\s*</tool_call>\s*', content) if isinstance(content, str) else None
    if match is None:
        raise ValueError('designer must return exactly one Hermes tool-call envelope; no content fallback')
    from .native_search_generator_v14 import _strict_json
    function = _strict_json(match.group(1))
    if not isinstance(function, dict) or set(function) != {'name', 'arguments'}:
        raise ValueError('Hermes tool call must contain exactly name and arguments')
    if (not isinstance(function, dict) or not isinstance(function.get('name'), str)
            or function['name'] not in DESCRIPTIONS):
        raise ValueError('native designer function name is unknown')
    arguments = function.get('arguments')
    if not isinstance(arguments, dict) or 'tool' in arguments:
        raise ValueError('native designer arguments must be a literal object without tool')
    # clone rejects non-JSON/nonfinite Python values without coercion.
    return {'tool': function['name'], **clone(arguments)}


def message_from_action(action):
    """Represent a completed literal action as native tool-call history.

    This is a history serialization, never a second dispatch or a generated
    replacement response. The original provider body must stay archived.
    """
    if (not isinstance(action, dict) or not isinstance(action.get('tool'), str)
            or action['tool'] not in DESCRIPTIONS):
        raise ValueError('cannot serialize an action with an unknown native function')
    function = {'name': action['tool'],
        'arguments': clone({key: value for key, value in action.items() if key != 'tool'})}
    return {'role': 'assistant', 'content': '<tool_call>\n'
        + json.dumps(function, ensure_ascii=False, allow_nan=False) + '\n</tool_call>'}


def tool_system_prompt():
    """Use the model's trained Hermes syntax without Ollama's lossy argument map.

    Ollama0.33.3's native argument-map JSON decoding has float64 round-trip
    risk above2**53, including previous assistant calls sent as history. Here
    schemas, actions and receipts remain strings, without entering that map.
    The existing strict JSON decoder owns all nested numbers.
    This does not install/alter a backend template or execute generated code.
    """
    return ('\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\n'
        'You are provided with function signatures within <tools></tools> XML tags:\n<tools>\n'
        + '\n'.join(json.dumps(tool, ensure_ascii=False, allow_nan=False) for tool in tool_specifications())
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
    return action_from_message(body['message'])
