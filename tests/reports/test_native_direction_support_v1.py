"""Literal catalog/support arithmetic only, not attained native performance."""
from types import SimpleNamespace

import pytest

from scripts.reports import native_direction_support_v1 as module
from utopia.system.code_mechanisms import sha
from utopia.system.design_patch import clone


def inputs():
    rows = [{'topic': 'core', 'years': 2, 'related_topics': ['fast', 'not-in-catalog']},
        {'topic': 'fast', 'years': 1, 'related_topics': []}]
    snapshot = {'year': 0, 'paper_tracker': {'papers': []}, 'ecosystem_data': {'agents': [
        {'id': 'SCRIPTED-author', 'can_author': True, 'is_active': True,
         'project_start_year': 0, 'project_end_year': 0, 'expertise': ['core']}]}}
    catalog = {'schema': 'scienceutopia.native-direction-catalog.v1',
        'directions': rows, 'directions_sha256': sha(rows)}
    return snapshot, catalog


def test_core_assignment_and_original_related_parser_have_different_support_not_attained_gains():
    s, c = inputs(); before = clone([s, c])
    r = module.support(s, c, years=4, papers_per_project=2)
    assert r['duration_only_output_envelopes'] == {'catalog_assignment': 4, 'legacy_native_parser': 8}
    assert r['initial_authors'][0]['legacy_native_parser']['shortest_topics'] == ['fast']
    assert r['initial_authors'][0]['unresolved_legacy_allowed_topics'] == ['not-in-catalog']
    assert r['conditional_not_global_optimality_proof']
    assert not r['loss_or_selection_changed'] and r['new_model_calls'] == 0
    assert [s, c] == before


@pytest.mark.parametrize('change', ['backlog', 'not-year0', 'boolean-year', 'ongoing', 'inactive',
    'unknown-expertise', 'duplicate-actor', 'duplicate-topic', 'duration', 'catalog-hash', 'output-cap'])
def test_unsupported_initial_conditions_cannot_inherit_the_relaxation(change):
    s, c = inputs(); cap = 2
    if change == 'backlog': s['paper_tracker']['papers'] = [{}]
    elif change == 'not-year0': s['year'] = 1
    elif change == 'boolean-year': s['year'] = False
    elif change == 'ongoing': s['ecosystem_data']['agents'][0]['project_end_year'] = 2
    elif change == 'inactive': s['ecosystem_data']['agents'][0]['is_active'] = False
    elif change == 'unknown-expertise': s['ecosystem_data']['agents'][0]['expertise'] = ['missing']
    elif change == 'duplicate-actor': s['ecosystem_data']['agents'].append(clone(s['ecosystem_data']['agents'][0]))
    elif change == 'duplicate-topic': c['directions'].append(clone(c['directions'][0])); c['directions_sha256'] = sha(c['directions'])
    elif change == 'duration': c['directions'][0]['years'] = 0; c['directions_sha256'] = sha(c['directions'])
    elif change == 'catalog-hash': c['directions_sha256'] = '0'*64
    elif change == 'output-cap': cap = True
    with pytest.raises(ValueError): module.support(s, c, years=4, papers_per_project=cap)


def test_catalog_parser_accepts_only_literal_named_constructor_data():
    text = "AVAILABLE_DIRECTIONS = [ResearchDirection(topic='a',years=2,related_topics=['b'])]"
    assert module.literal_catalog(text) == [{'topic': 'a', 'years': 2, 'related_topics': ['b']}]
    for text in ("AVAILABLE_DIRECTIONS = get_catalog()", "AVAILABLE_DIRECTIONS = [Other(topic='a')]",
        "AVAILABLE_DIRECTIONS = [ResearchDirection('a')]",
        "AVAILABLE_DIRECTIONS = [ResearchDirection(topic=__import__('os').getcwd())]"):
        with pytest.raises(ValueError): module.literal_catalog(text)


def test_reader_cannot_write_into_original_run_or_frozen_source(tmp_path):
    source = tmp_path/'source'; source.mkdir(); raw = tmp_path/'raw'; raw.mkdir()
    for target in (source/'bad.json', raw/'bad.json'):
        args = SimpleNamespace(source=source, plan=raw/'plan.json', checkpoint=raw/'checkpoint.gz', output=target)
        with pytest.raises(ValueError, match='outside original'): module.export(args)
        assert not target.exists()


def test_retained_actual_initial_support_keeps_relaxation_and_unknown_reachability_separate():
    import json
    from utopia.optimization.native_numeric_designer import checked
    r = checked(json.loads((module.ROOT/'research/data/native-direction-support-v1/report.json').read_text()))
    a = r['analysis']
    assert a['duration_only_output_envelopes'] == {'catalog_assignment': 20, 'legacy_native_parser': 36}
    assert len(a['initial_authors']) == 5
    assert [x['catalog_assignment']['minimum_project_years'] for x in a['initial_authors']] == [2]*5
    assert [x['legacy_native_parser']['minimum_project_years'] for x in a['initial_authors']] == [1,1,2,1,1]
    assert all(not x['unresolved_legacy_allowed_topics'] for x in a['initial_authors'])
    assert a['conditional_not_global_optimality_proof'] and a['additional_assumptions_not_automatically_proved']
    assert r['original_bound_inputs_unchanged'] and not r['native_execution_or_whole_study_audit_claimed']
    assert a['new_model_calls'] == a['new_native_worlds'] == a['new_code_executions'] == 0
    assert not a['loss_or_selection_changed'] and not a['publication_ready']
