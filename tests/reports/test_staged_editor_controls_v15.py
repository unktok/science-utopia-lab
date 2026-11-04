import importlib.util
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

SCRIPTS=Path(__file__).resolve().parents[2]/'scripts'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('editor_control',SCRIPTS/'diagnose_staged_editor_controls_v15.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_expected_edit_fits_minimal_schema():
    assert not list(Draft202012Validator(m.MINIMAL).iter_errors(m.EXPECTED))


def test_minimal_schema_rejects_selector_and_rationale():
    for extra in ('selector','rationale'):
        assert list(Draft202012Validator(m.MINIMAL).iter_errors({**m.EXPECTED,extra:'not allowed'}))


def test_control_explicitly_separates_syntax_from_scientific_optimization():
    assert 'NOT scientific optimization' in m.INSTRUCTION
    assert 'Do not use replace' in m.INSTRUCTION
    assert 'Do not include selector, rationale' in m.INSTRUCTION
