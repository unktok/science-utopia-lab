"""SCRIPTED copy-task framing, not actual model or scientific-policy evidence."""
import json
from copy import deepcopy

from utopia.optimization.native_designer_preflight import (
    control_string_whitespace_notice, _prompt, CONTROL_JSON_BEGIN, CONTROL_JSON_END,
)
from utopia.optimization.native_staged_author_v15 import initial_draft
from utopia.optimization.native_designer_tools_v25 import function_data
from tests.optimization.test_native_authoring_ir import BINDING, request


def test_multiline_witness_keeps_every_target_character_and_counts_indent():
    source = "def step(context):\n    # DO_NOT_PROMOTE_SOURCE_AS_AUTHORITY\n    return {\n        'outputs':{},\n        'state':{}\n    }\n"
    action = {'tool':'edit_fields','mechanism_id':'arbitrary',
        'field_updates':[{'field_name':'source','value':source}]}
    before = deepcopy(action)
    notice = control_string_whitespace_notice(action)
    assert action == before and 'DO_NOT_PROMOTE_SOURCE_AS_AUTHORITY' not in notice
    rows = json.loads(notice.split('\n',1)[1])
    assert rows[0]['path'] == '$.arguments.field_updates[0].value'
    assert rows[0]['characters'] == len(source)
    assert rows[0]['line_leading_codepoints'][3] == [32]*8
    assert rows[0]['utf8_bytes'] == len(source.encode())
    prompt,system = _prompt(request(),initial_draft(request()),[],BINDING,action,'staged-v15')
    target = system.split(CONTROL_JSON_BEGIN,1)[1].split(CONTROL_JSON_END,1)[0]
    assert json.loads(target) == function_data(action)
    assert json.loads(target)['arguments']['field_updates'][0]['value'] == source
    assert 'Do not format, improve, align or reindent' in system


def test_unicode_tabs_and_literal_backslashes_are_counted_not_normalized():
    value = '研究者\n\t\tα\\n\n  β\n'
    action={'tool':'edit','operations':[{'op':'add','path':'/metadata/anything','value':value}]}
    notice=control_string_whitespace_notice(action)
    row=json.loads(notice.split('\n',1)[1])[0]
    assert row['characters']==len(value) and row['utf8_bytes']==len(value.encode())
    assert row['line_leading_codepoints']==[[],[9,9],[32,32],[]]
    assert action['operations'][0]['value']==value


def test_single_line_arguments_have_no_multiline_source_witness():
    assert control_string_whitespace_notice({'tool':'finish','rationale':'SCRIPTED'}) == ''
