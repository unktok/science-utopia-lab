"""SCRIPTED exact response-text controls, never repair a real failed response."""
import json

from tests.optimization.test_native_authoring_ir import BINDING, request
from utopia.optimization import native_designer_preflight as p
from utopia.optimization.native_staged_author_v15 import initial_draft
from utopia.optimization.native_designer_tools_v25 import function_data, action_from_message
from utopia.system.design_patch import digest


def test_every_nonplanning_control_marks_one_complete_once_serialized_exact_response():
    body = request(); state = initial_draft(body)
    for case in p.planned_cases(body, 'staged-v15'):
        expected = case['expected']
        if expected['tool'] == 'plan':
            continue  # The separate original planning-role control is unchanged.
        _, system = p._prompt(body, state, [], BINDING, expected, 'staged-v15')
        assert system.count(p.CONTROL_JSON_BEGIN) == system.count(p.CONTROL_JSON_END) == 1
        text = system.split(p.CONTROL_JSON_BEGIN, 1)[1].split(p.CONTROL_JSON_END, 1)[0]
        assert text == json.dumps(function_data(expected), ensure_ascii=False, allow_nan=False, separators=(',', ':'))
        assert '\n' not in text  # Logical line feeds remain JSON escapes, not new physical lines.
        assert action_from_message({'role': 'assistant', 'content': text}) == expected


def test_wrong_model_escaping_stays_wrong_after_one_strict_decode_and_cannot_pass_by_normalization():
    expected = p.cases('staged-v15')[6]['expected']
    wrong = function_data(expected)
    wrong['arguments']['operations'][0]['value'] = wrong['arguments']['operations'][0]['value'].replace('\n', '\\n', 1)
    output = action_from_message({'role': 'assistant', 'content': json.dumps(wrong, ensure_ascii=False)})
    assert digest(output) != digest(expected)
    assert output['operations'][0]['value'][3:5] == '\\n'
    assert expected['operations'][0]['value'][3] == '\n'
