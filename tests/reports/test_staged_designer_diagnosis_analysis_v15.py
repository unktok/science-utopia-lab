import importlib.util
from pathlib import Path
import sys

from jsonschema import Draft202012Validator
from utopia.optimization.native_staged_author_v15 import ACTION_SCHEMA,turn_control

SCRIPTS=Path(__file__).resolve().parents[2]/'scripts';sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('diagnosis_analysis',SCRIPTS/'analyze_staged_designer_diagnosis_v15.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_declared_arbitrary_edit_value_accepts_all_json_types():
    for value in ('text',2,.5,True,None,[],{}):
        action={'tool':'edit','operations':[{'op':'add','path':'/metadata/diagnostic_probe','value':value}]}
        assert not list(Draft202012Validator(ACTION_SCHEMA).iter_errors(action))


def test_top_level_schema_does_not_enforce_per_tool_contract():
    action={'tool':'inspect','selector':{'mechanism_id':'world.review'},'text':'not a valid inspection'}
    assert not list(Draft202012Validator(ACTION_SCHEMA).iter_errors(action))
    # This is a documented interface mismatch, not a test claiming such action is valid.


def test_compiled_rule_extraction_is_literal_not_a_fabricated_language_test():
    assert m.grammar_rules('root ::= "{" value "}"\nvalue ::= object\n')=={'root':'"{" value "}"','value':'object'}


def test_scalar_inside_object_workaround_is_distinct_from_direct_scalar_value():
    direct={'tool':'edit','operations':[{'op':'replace','path':'/metadata/name','value':'x'}]}
    enclosing={'tool':'edit','operations':[{'op':'replace','path':'/metadata','value':{'name':'x'}}]}
    assert not list(Draft202012Validator(ACTION_SCHEMA).iter_errors(direct))
    assert not list(Draft202012Validator(ACTION_SCHEMA).iter_errors(enclosing))
    assert isinstance(enclosing['operations'][0]['value'],dict)
