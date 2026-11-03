"""Prevent glued words/numerals in the new manuscript evidence prose."""
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('filename', [
    'main.tex', 'native_objective_structure_v8.tex', 'native_response_fidelity_v8.tex',
    'native_autonomous_search_v14.tex'])
def test_new_evidence_prose_has_spaces_before_numeric_values(filename):
    source = (ROOT/'paper'/filename).read_text()
    glued = re.findall(
        r'\b(?:produce|actual|with|all|have|and|year|mean|after|loss|seed|versus|preserving|pass|from|to|unchanged|selected|Element|element|the|exit|contain|record|preserve|match|matching|passes)[0-9]|\b(?:from|to)-[0-9]',
        source)
    assert not glued, glued
    assert 'error$' not in source and 'mean$' not in source
