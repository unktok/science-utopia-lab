"""SCRIPTED submission guidance; no policy menu or autonomous invention claim."""
import json

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from tests.optimization.test_native_authoring_ir import request, BINDING
from utopia.optimization.native_staged_author_v15 import (
    ACTION_SCHEMA, INSTRUCTIONS, build_conversation, build_prompt, initial_draft,
    transition, turn_response_schema,
)


def test_nonfinal_calls_preserve_the_entire_existing_tool_and_system_space():
    advertised = turn_response_schema(16)
    assert advertised == turn_response_schema(2)
    # oneOf branch order is presentation, not JSON-Schema acceptance. Preserve
    # every full tool contract while allowing implementation-first ordering.
    by_tool = lambda schema: {part['properties']['tool']['const']: part for part in schema['oneOf']}
    assert by_tool(advertised) == by_tool(ACTION_SCHEMA)
    assert advertised['$defs'] == ACTION_SCHEMA['$defs']
    assert 'arbitrary literal Python' in INSTRUCTIONS
    assert 'new institutions' in INSTRUCTIONS
    assert 'Factor IDs and' in INSTRUCTIONS and 'choice names do not create native variables' in INSTRUCTIONS
    assert 'Schema edits are legal' in INSTRUCTIONS


@pytest.mark.parametrize('rationale', ['Explicit retention is legal', 'New model-authored mechanism', 'x' * 4096])
def test_every_legal_finish_form_is_still_legal_in_last_call_guidance(rationale):
    action = {'tool': 'finish', 'rationale': rationale}
    Draft202012Validator(ACTION_SCHEMA).validate(action)
    Draft202012Validator(turn_response_schema(1)).validate(action)
    with pytest.raises(ValidationError):
        Draft202012Validator(turn_response_schema(1)).validate({'tool': 'inspect', 'path': ''})


def test_last_call_schema_does_not_supply_a_candidate_or_relax_host_validation():
    body = request(); state = initial_draft(body)
    prompt = build_prompt(body, state, [], image_id=BINDING['image_id'], binding_sha256='d' * 64,
        settings={'max_steps': 1})
    payload = json.loads(prompt)
    assert payload['response_schema'] == turn_response_schema(1)
    assert payload['remaining_calls_including_this_one'] == 1
    assert payload['draft_index']['applied_operation_count'] == 0
    messages = build_conversation(prompt, 'Return the next tool action')
    assert 'DISTINGUISH THE SCIENTIFIC SYSTEM' in messages[0]['content']
    # Last-call guidance is not an implicit finish/fallback. A literal inspect
    # remains interpreted as inspect and carries no candidate definition.
    after, receipt = transition(state, {'tool': 'inspect', 'path': ''}, body,
        binding_sha256='d' * 64, provider_binding=BINDING)
    assert receipt['ok'] and receipt['definition'] is None and after == state
    _, receipt = transition(state, {'tool': 'finish', 'rationale': ''}, body,
        binding_sha256='d' * 64, provider_binding=BINDING)
    assert not receipt['ok'] and receipt['definition'] is None
