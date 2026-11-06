"""Finite authoring workflow recovery, not a scientific policy or output repair.

The explicit V44 profile preserves old profiles. Every request/failed reply is
charged and archived. Only a new explicit model finish submits the actual draft.
"""
from __future__ import annotations

import json

from utopia.system.design_patch import clone, digest

MAX_STEPS = 16
SUBMISSION_RESERVE = 3
MAX_FULL_DOCUMENT_BYTES = 65536
IMPLEMENTATION_TOOLS = ('write_file', 'edit', 'edit_fields', 'splice', 'configure', 'finish')
IMPLEMENT_CONTROL_PREFIX = 'TRUSTED V44 IMPLEMENTATION INTERFACE CONTROL\n'
IMPLEMENT_TASK = (
    'IMPLEMENTATION CHECKPOINT. Reading and a written plan have not implemented your institution. '
    'The complete current draft is supplied as literal_current_system, with earlier read results '
    'retained. Now author a concrete literal code/graph/configuration change, or explicitly finish '
    'to retain the parent. Do not claim that a plan or an explanation changed the draft. '
    'This checkpoint is one implementation action, not a policy catalogue or a novelty requirement. '
    'All general editing operations and arbitrary literal JSON/Python operands remain available. ')
SUBMIT_TASK = (
    'EXPLICIT SUBMISSION. Call finish on the exact current draft. No explanation is required: '
    'arguments may be {}. Optional rationale/provenance are archived author notes only. '
    'Static graph/source/ABI/permission validation remains mandatory. Do not claim unexecuted edits. ')
RECOVER_TASK = (
    'BOUNDED SUBMISSION RECOVERY. The preceding explicit submission failed and remains charged. '
    'Read its actual errors and the supplied complete current draft. Author the needed literal '
    'repair, or explicitly finish the unchanged draft if technically valid. A further explicit '
    'finish call is reserved after this action. The host never repairs or submits on your behalf. ')


def action_schema():
    from .native_staged_author_v15 import ACTION_SCHEMA
    schema = clone(ACTION_SCHEMA)
    for branch in schema['oneOf']:
        if branch['properties']['tool'].get('const') == 'finish':
            branch['required'] = ['tool']
    return schema


def workflow(state, steps, *, max_steps):
    remaining = max_steps - len(steps)
    complete = len(json.dumps(state['document'], ensure_ascii=False, allow_nan=False).encode()) <= MAX_FULL_DOCUMENT_BYTES
    inspections = 0
    current = digest(state['document'])
    for step in reversed(steps):
        receipt = step.get('transition') or {}
        if receipt.get('document_after_sha256') != current or receipt.get('document_before_sha256') != current:
            break
        inspections += int(receipt.get('ok') is True and receipt.get('tool') in
            ('read_file', 'inspect', 'inspect_field'))
    if not steps:
        phase = 'planning'
    elif remaining == 1 or remaining == SUBMISSION_RESERVE:
        phase = 'submit'
    elif remaining == 2 and steps[-1]['status'] != 'finished':
        phase = 'recovery'
    elif complete and inspections >= 3:
        phase = 'implementation'
    else:
        phase = 'general'
    return {'schema': 'scienceutopia.authoring-workflow.v44', 'phase': phase,
        'remaining_calls_including_this_one': remaining, 'submission_reserve': SUBMISSION_RESERVE,
        'successful_inspections_since_last_document_change': inspections,
        'literal_current_system_included': complete, 'literal_current_system_byte_cap': MAX_FULL_DOCUMENT_BYTES,
        'all_calls_charged': True, 'host_repair': False, 'host_auto_submit': False}


def task(index, max_steps, prompt, *, planner, general):
    if index == 0 and max_steps > 1:
        return planner
    phase = json.loads(prompt)['000_current_turn']['authoring_workflow']['phase']
    return {'implementation': IMPLEMENT_TASK, 'submit': SUBMIT_TASK,
        'recovery': RECOVER_TASK}.get(phase, general)


def generic_json_value():
    # Explicit recursive types avoid the previously observed empty-schema ->
    # object-only backend conversion. Integers are not cast through native tools.
    return {'anyOf': [{'type': 'null'}, {'type': 'boolean'}, {'type': 'integer'},
        {'type': 'number'}, {'type': 'string'},
        {'type': 'array', 'items': {'$ref': '#/$defs/JSONValue'}},
        {'type': 'object', 'additionalProperties': {'$ref': '#/$defs/JSONValue'}}]}


def backend_format(messages):
    if not messages or messages[0].get('role') != 'system':
        raise ValueError('source-owned V44 system message required')
    marker = messages[0]['content'].splitlines()[-1]
    if not marker.startswith('V44_ACTION_PHASE='):
        raise ValueError('source-owned V44 action phase missing')
    phase = marker.removeprefix('V44_ACTION_PHASE=')
    if phase == 'general':
        return 'json'
    if phase not in ('submit', 'implementation'):
        raise ValueError('unknown V44 output phase')
    arguments = {'type': 'object', 'additionalProperties': {'$ref': '#/$defs/JSONValue'}}
    if phase == 'submit':
        arguments = {'type': 'object', 'properties': {
            'rationale': {'type': 'string', 'minLength': 1, 'maxLength': 4096},
            'provenance': {'type': 'object', 'maxProperties': 16,
                'additionalProperties': {'$ref': '#/$defs/JSONValue'}}}, 'additionalProperties': False}
    return {'type': 'object', 'required': ['name', 'arguments'], 'additionalProperties': False,
        'properties': {'name': {'enum': ['finish'] if phase == 'submit' else list(IMPLEMENTATION_TOOLS)},
            'arguments': arguments}, '$defs': {'JSONValue': generic_json_value()}}
