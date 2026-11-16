"""Pure failure diagnostics; no model, generated code or native world execution."""
from copy import deepcopy
from itertools import product

import pytest

from utopia.system.code_mechanisms import sha
from utopia.system.native_catalog_planning import validate_catalog_assignment
from utopia.system.native_legacy_topic_planning import validate_legacy_topic_assignment
from utopia.system.runtime import GraphRuntimeError


def fixture():
    directions = [
        {'topic': 'core', 'years': 3, 'related_topics': ['related'], 'keywords': ['core']},
        {'topic': 'related', 'years': 1, 'related_topics': [], 'keywords': ['related']},
        {'topic': 'unrelated', 'years': 1, 'related_topics': [], 'keywords': ['unrelated']},
    ]
    catalog = {'schema': 'scienceutopia.native-direction-catalog.v1',
               'directions': directions, 'directions_sha256': sha(directions)}
    actor = {'id': 'a', 'can_author': True, 'is_active': True,
             'project_end_year': 0, 'expertise': ['core']}
    assignment = {'actor_id': 'a', 'direction': deepcopy(directions[0]),
                  'detailed_focus': 'An arbitrary nonshortest choice', 'reason': 'No merit gate',
                  'project_start_year': 1, 'project_end_year': 3}
    return assignment, actor, catalog


@pytest.mark.parametrize('case,message', [
    ('shape', 'object with a string topic'),
    ('eligibility', 'outside this actor'),
    ('content', 'displayed canonical topic'),
    ('calendar', 'calendar must start'),
    ('annotation', 'must be strings'),
])
def test_distinct_failed_predicate_and_no_input_repair(case, message):
    assignment, actor, catalog = fixture()
    if case == 'shape':
        assignment['direction'] = None
    elif case == 'eligibility':
        assignment['direction'] = deepcopy(catalog['directions'][2])
        assignment['project_end_year'] = 1
    elif case == 'content':
        assignment['direction']['keywords'].append('invented')
    elif case == 'calendar':
        assignment['project_end_year'] = 1
    else:
        assignment['reason'] = None
    before = deepcopy((assignment, actor, catalog))
    with pytest.raises(GraphRuntimeError, match=message):
        validate_catalog_assignment(assignment, actor, year=1, catalog=catalog)
    assert (assignment, actor, catalog) == before


def test_related_scope_reports_actor_eligibility_not_duration_and_retains_nonshortest():
    assignment, actor, catalog = fixture()
    # The legacy wrapper expands only this actor's own directly related topics.
    validate_legacy_topic_assignment(assignment, actor, year=1, catalog=catalog)
    assignment['direction'] = deepcopy(catalog['directions'][1])
    assignment['project_end_year'] = 1
    validate_legacy_topic_assignment(assignment, actor, year=1, catalog=catalog)
    with pytest.raises(GraphRuntimeError, match='outside this actor'):
        validate_catalog_assignment(assignment, actor, year=1, catalog=catalog)
    assignment['direction'] = deepcopy(catalog['directions'][2])
    with pytest.raises(GraphRuntimeError, match='outside this actor'):
        validate_legacy_topic_assignment(assignment, actor, year=1, catalog=catalog)


@pytest.mark.parametrize('years', [0, -1, True, 1.0, '1'])
def test_even_self_consistent_catalog_cannot_authorize_invalid_duration(years):
    assignment, actor, catalog = fixture()
    catalog['directions'][0]['years'] = years
    catalog['directions_sha256'] = sha(catalog['directions'])
    assignment['direction'] = deepcopy(catalog['directions'][0])
    with pytest.raises(GraphRuntimeError, match='positive integer'):
        validate_catalog_assignment(assignment, actor, year=1, catalog=catalog)


def test_final_predicate_acceptance_matches_previous_compound_guard_on_finite_matrix():
    assignment, actor, catalog = fixture()
    actual = {d['topic']: d for d in catalog['directions']}
    variants = [None, {}, {'topic': None}, {'topic': 'unknown'},
                deepcopy(catalog['directions'][0]), deepcopy(catalog['directions'][1]),
                {**deepcopy(catalog['directions'][0]), 'years': 1},
                {**deepcopy(catalog['directions'][0]), 'keywords': ['fabricated']}]
    accepted = rejected = 0
    for direction, start, end, reason in product(variants, (0, 1, True), (1, 3, True), ('literal', None)):
        current = {**deepcopy(assignment), 'direction': deepcopy(direction),
                   'project_start_year': start, 'project_end_year': end, 'reason': reason}
        # Literal final compound guard from the preceding implementation.
        old_rejected = (not isinstance(direction, dict) or not isinstance(direction.get('topic'), str)
            or direction.get('topic') not in actor['expertise']
            or direction != actual.get(direction.get('topic'))
            or type(direction.get('years')) is not int or direction['years'] < 1
            or start != 1 or type(start) is not int or type(end) is not int
            or end != 1 + direction['years'] - 1
            or any(not isinstance(current[k], str) for k in ('detailed_focus', 'reason')))
        before = deepcopy((current, actor, catalog))
        if old_rejected:
            with pytest.raises(GraphRuntimeError):
                validate_catalog_assignment(current, actor, year=1, catalog=catalog)
            rejected += 1
        else:
            validate_catalog_assignment(current, actor, year=1, catalog=catalog)
            accepted += 1
        assert (current, actor, catalog) == before
    assert accepted == 1 and rejected == 143
