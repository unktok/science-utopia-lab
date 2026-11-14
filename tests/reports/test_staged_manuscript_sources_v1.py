"""Source/citation scope checks, not PDF layout or new scientific evidence."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_both_bibliography_inputs_are_considered_without_duplicate_amd_llm():
    entry = (ROOT/'paper/integrated.tex').read_text()
    assert r'\bibliography{references,submission-sources}' in entry
    bodies = [(ROOT/'paper'/name).read_text() for name in ('references.bib','submission-sources.bib')]
    assert sum(body.count('{liu2025mechanism,') for body in bodies)==1
    assert sum(body.count('{narayanaswami2022programmatic,') for body in bodies)==1
    related = (ROOT/'paper/integrated/discussion.tex').read_text()
    assert r'\citep{liu2025mechanism}' in related
    assert r'\citep{narayanaswami2022programmatic}' in related
    assert 'neither representing institutions as programs' in related


def test_new_staged_paragraph_is_software_scope_not_a_repaired_real_experiment():
    body = (ROOT/'paper/integrated/native-workflow-feedback.tex').read_text()
    assert 'ten SCRIPTED native worlds and 48 real' in body
    assert 'zero actual model calls' in body
    assert '20 uniquely attributed historical R7' in body
    assert 'has\nnot passed the shared-resource gate' in body
    assert 'No model-authored repair' in body
    assert '16 designer calls and 64 component probes' in body


def test_reference_absence_correction_is_explicit_and_old_receipt_preserved():
    note = (ROOT/'research/publication/novelty-addendum-programmatic-institutions-v1.md').read_text()
    assert 'AMD-LLM already appears' in note and 'earlier statement' in note
    assert 'both `.bib` files' in note
    assert (ROOT/'paper/integrated-open-institutions-build-v1.json').is_file()
