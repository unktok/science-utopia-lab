"""SCRIPTED file-primary advertising, complete legacy API and immutable references."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_authoring_ir import ALPHA, IMAGE, request
from tests.optimization.test_native_planning_author_v22 import PLAN
from tests.optimization.test_native_staged_author_v15 import apply
from utopia.optimization.native_designer_tools_v25 import tool_specifications
from utopia.optimization.native_file_workspace_v35 import file_catalog, read_file, write_file_operations
from utopia.optimization.native_staged_author_v15 import (
    TOOL_FIELDS, FILE_EDITOR_INSTRUCTIONS, SYSTEM_PROMPT, build_prompt, build_conversation, initial_draft)


def test_default_role_advertisements_are_small_but_all_host_functions_remain_documented():
    names = lambda role: [t['function']['name'] for t in tool_specifications(role=role)]
    assert names('planner') == ['plan']
    assert names('editor') == ['read_file', 'write_file', 'finish']
    assert names('finisher') == ['finish']
    all_tools = tool_specifications()
    assert set(names(None)) == set(TOOL_FIELDS)
    by_name = {t['function']['name']: t for t in all_tools}
    assert all(t == by_name[t['function']['name']] for t in tool_specifications(role='editor'))
    doc = request()['parent_system']
    result = read_file(doc, 'reference/tools.json')
    assert result['read_only'] and result['complete']
    assert json.loads(result['content']) == all_tools


@pytest.mark.parametrize('filename', ['reference/tools.json', 'reference/capabilities.json'])
def test_reference_files_are_explicitly_readonly_not_candidate_or_host_files(filename):
    doc = request()['parent_system']; before = deepcopy(doc)
    catalog = {x['filename']: x for x in file_catalog(doc)['files']}
    assert catalog[filename]['read_only']
    read = read_file(doc, filename, limit=1024)
    assert read['read_only'] and read['content']
    with pytest.raises(ValueError, match='read-only'):
        write_file_operations(doc, filename, 'THIS IS NOT EXECUTED OR WRITTEN')
    assert doc == before


def test_nonadvertised_legacy_edit_remains_legal_and_is_not_a_new_policy_veto():
    body = request(); state = initial_draft(body)
    changed, receipt = apply(state, {'tool': 'edit_fields', 'mechanism_id': ALPHA,
        'field_updates': [{'field_name': 'gain', 'value': .8}]}, body)
    assert receipt['ok'] and changed['document']['mechanisms'][0]['parameters']['gain'] == .8
    _, configured = apply(changed, {'tool': 'configure', 'factors': [], 'continuous': [], 'logits': {}}, body)
    assert configured['ok']


def test_native_editor_uses_file_instructions_not_conflicting_flat_field_tutorial():
    body = request(); state, receipt = apply(initial_draft(body), PLAN, body)
    steps = [{'step': 0, 'status': 'applied', 'model_reply': {'output': PLAN}, 'transition': receipt}]
    raw = build_prompt(body, state, steps, image_id=IMAGE, binding_sha256='d' * 64, settings={'max_steps': 8})
    messages = build_conversation(raw, SYSTEM_PROMPT, native_tools=True)
    system = messages[0]['content']
    assert FILE_EDITOR_INSTRUCTIONS in system
    assert 'Function edit_fields:' not in system and 'workbench lists unique names' not in system
    assert 'reference/tools.json' in system and 'filename is NOT a SystemSpec JSON pointer' in system
    assert '"name":"edit_fields"' not in system
    context = json.loads(messages[1]['content'].split('EXACT SESSION DATA\n', 1)[1])
    assert {f['filename'] for f in context['virtual_editor_workspace']['files']} >= {
        'reference/tools.json', 'reference/capabilities.json', 'system.json', 'nodes/' + ALPHA + '.json'}
