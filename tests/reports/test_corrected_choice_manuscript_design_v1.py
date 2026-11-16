"""Unbuilt methods/source coherence, not rendered PDF or scientific validation."""
import hashlib
import json
from pathlib import Path
import re

from tests.reports.test_current_manuscript_estimands import bodies
from utopia.optimization.native_numeric_designer import checked

ROOT = Path(__file__).resolve().parents[2]
METHODS = 'paper/integrated/native-corrected-choice-design.tex'


def test_new_methods_are_in_recursive_source_with_unique_resolved_literal_labels():
    sources=bodies(); assert METHODS in sources
    assert sources['paper/integrated.tex'].count(r'\input{integrated/native-corrected-choice-design}')==1
    labels=[k for text in sources.values() for k in re.findall(r'\\label\{([^}]+)\}',text)]
    references={k for text in sources.values() for k in re.findall(r'\\(?:ref|eqref|autoref)\{([^}]+)\}',text)}
    assert len(labels)==len(set(labels))
    assert references<=set(labels), sorted(references-set(labels))
    assert 'sec:native-corrected-choice-design' in labels and 'tab:corrected-choice-design' in labels


def test_finite_design_numbers_are_bound_to_actual_dispatch_not_the_old_two_history_study():
    text=(ROOT/METHODS).read_text()
    dispatch=json.loads((ROOT/'research/results/native-corrected-choice-real-dispatch-v1.json').read_text())
    design=dispatch['declared_design']; budget=dispatch['declared_budget']
    assert design['optimizer_histories_per_method_objective']==1 and design['proposals_per_history']==4
    for value in (design['development_world_seed'], design['optimizer_seed'], design['replication_seeds'][0]):
        assert str(value) in text
    assert f"{budget['designer_POSTs_upper_bound']} combined" in text
    assert f"capped separately at {budget['component_probes_upper_bound']}" in text
    sessions=len(design['objectives'])*design['optimizer_histories_per_method_objective']*design['proposals_per_history']
    assert sessions==8 and budget['readiness_sessions']==sessions+1
    assert budget['readiness_sessions']*budget['readiness_POSTs_per_session']+sessions*budget['proposal_POSTs_per_session']==488
    assert '53 original topic-priority fields' in text
    assert 'same first' in text and 'three opportunities' in text
    assert (f"neither it nor world seed {design['development_world_seed']} is an unused condition or an independent "
            'researcher population.') in ' '.join(text.split())


def test_proposal_context_endpoint_and_unknown_outcome_boundaries_stay_explicit():
    text=(ROOT/METHODS).read_text()
    for phrase in ('full numeric space and parent program','Repeated', 'counterfactual',
                   'current node\'s non-reserved', 'Probe errors do not veto',
                   'Local code return and compatibility','ordered pool of visible measured references',
                   'absent when none completes','charged and journaled before dispatch',
                   'unavailable loss','uncertainty does not authorize redispatch',
                   'not a convergence claim','proposed\nseeds alone are not evidence of unusedness'):
        assert phrase in text, phrase
    assert 'every\nmodel message' in text and 'not proof of model understanding' in text


def test_software_assurance_is_not_real_model_science_or_a_new_complete_manuscript():
    text=(ROOT/METHODS).read_text()
    qa=checked(json.loads((ROOT/'research/results/native-corrected-choice-full-public-qa-v1.json').read_text()))
    assert qa['actual_native_worlds']==27 and qa['actual_exact_source_file_count']==351
    assert qa['actual_model_POSTs']==0 and not qa['subprocess_CLI_routing_verified']
    assert 'scripted' in text and 'outer subprocess-CLI verification' in text
    assert 'original writer is still active when this methods' in text
    assert 'not yet reported' in text and 'Source preparation is not a newly built' in text
    assert r'\includegraphics' not in text


def test_reviewed111_pdf_receipt_remains_its_unchanged_pre_methods_artifact():
    r=checked(json.loads((ROOT/'paper/integrated-priority-method-build-v1.json').read_text()))
    assert METHODS not in r['source_file_sha256']
    assert hashlib.sha256((ROOT/'paper/integrated.tex').read_bytes()).hexdigest()!=r['source_file_sha256']['paper/integrated.tex']
    assert hashlib.sha256((ROOT/r['pdf']).read_bytes()).hexdigest()==r['pdf_sha256']
    assert r['pages']==111 and not r['publication_ready'] and not r['minimal_source_subset_rebuild_verified']
    assert 'unbuilt and\nunrendered' in (ROOT/'paper/integrated-content-map.md').read_text()
