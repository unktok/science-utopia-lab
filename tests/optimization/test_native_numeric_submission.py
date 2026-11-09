from copy import deepcopy

import pytest

from utopia.optimization.native_numeric_submission import numeric_context, submission_schema, compile_submission
from tests.optimization.test_native_design_space import campaign


@pytest.fixture
def design_request(tmp_path):
    c = campaign(tmp_path)
    return c._request([], c._strategy_initial(), 1)


def literal(design_request):
    return {'values': {c['id']: c['current_value'] for c in numeric_context(design_request)['coordinates']},
            'rationale': 'SCRIPTED explicit values, not a scientific claim'}


def test_six_literal_coordinates_are_not_whole_code_editor(design_request):
    ctx = numeric_context(design_request)
    assert len(ctx['coordinates']) == 6
    schema = submission_schema(ctx)
    assert schema['additionalProperties'] is False
    assert 'code' not in schema['properties'] and 'operations' not in schema['properties']


def test_explicit_retention_is_not_an_implicit_fallback(design_request):
    result = compile_submission(design_request, literal(design_request))
    assert result['base_patch'] is None and result['provenance']['retained_parent_explicitly']
    with pytest.raises(ValueError):
        compile_submission(design_request, {})


def test_exact_model_values_compile_into_existing_coordinate_patch(design_request):
    before = deepcopy(design_request); value = literal(design_request)
    value['values']['coordinate-2'] = .875
    result = compile_submission(design_request, value)
    assert result['base_patch']['operations'] == [{'op': 'replace',
        'path': '/mechanisms/15/parameters/program/parameters/bias', 'value': .875}]
    assert not result['provenance']['raw_values_changed_by_host']
    assert design_request == before


@pytest.mark.parametrize('value', [True, None, float('nan'), float('inf'), 99., '0.7'])
def test_bad_values_are_never_clipped_or_coerced(design_request, value):
    body = literal(design_request); body['values']['coordinate-2'] = value
    with pytest.raises(ValueError):
        compile_submission(design_request, body)


def test_integer_count_rejects_integral_float(design_request):
    body = literal(design_request); body['values']['coordinate-5'] = 2.
    with pytest.raises(ValueError):
        compile_submission(design_request, body)


@pytest.mark.parametrize('mutation', ['extra', 'missing', 'source', 'empty-rationale'])
def test_schema_violations_do_not_become_retention(design_request, mutation):
    body = literal(design_request)
    if mutation == 'extra': body['values']['invented'] = 0
    if mutation == 'missing': body['values'].pop('coordinate-0')
    if mutation == 'source': body['source'] = 'def step(context): return {}'
    if mutation == 'empty-rationale': body['rationale'] = ' '
    with pytest.raises(ValueError):
        compile_submission(design_request, body)


def test_wrong_domain_or_changed_parent_rejects_before_dispatch(design_request):
    changed = deepcopy(design_request); changed['design_space']['kind'] = 'code-and-graph'
    with pytest.raises(ValueError, match='parameter-only'):
        numeric_context(changed)
    changed = deepcopy(design_request); changed['parent_system']['metadata']['extra'] = 'not a coordinate'
    with pytest.raises(ValueError, match='exceeds'):
        numeric_context(changed)
