"""Pure hand-control tests; not new scientist inference or policy evaluations."""
from copy import deepcopy
from itertools import product
import json
from pathlib import Path

import pytest

from utopia.system import SystemSpec
from utopia.optimization.native_institution_workflow_domain_v6 import require_institution_workflow_candidate
from utopia.system.native_catalog_planning import catalog_contract
from utopia.system.native_legacy_topic_controls import SOURCE as LEGACY_SOURCE
from utopia.system.native_legacy_topic_planning import eligible_topics, validate_legacy_topic_assignment
from utopia.system.native_topic_priority_controls import SOURCE, topic_priority_control

ROOT = Path(__file__).resolve().parents[2]


def base():
    return SystemSpec.from_dict(json.loads((ROOT /
        'research/data/native-terminal-cost-pilot-v1/systems/strong-related-reference.json').read_text()))


def actors():
    # Literal public, retained initial state, not a new synthetic population.
    return json.loads((ROOT /
        'research/results/native-consumer-source-fourth-year1-actuation-prefix-v1.json').read_text()
    )['own']['initial_author_projection']


def producer(spec):
    return next(n for n in spec.mechanisms if n.mechanism_id == 'developer-catalog-agenda')


def output(source, parameters, society, year=1):
    # Trusted developer source only. This is not the generated-code trust boundary.
    namespace = {}; exec(source, namespace)
    context = {'inputs': {'world': [{'payload': {'ecosystem': {'agents': deepcopy(society)}}}]},
               'parameters': deepcopy(parameters), 'period': year, 'state': {}}
    before = deepcopy(context)
    value = namespace['step'](context)
    assert context == before
    return value


def test_zero_priorities_recover_full_literal_control_output_without_new_permissions():
    reference = base(); before = reference.to_dict()
    current = topic_priority_control(reference, priorities={})
    require_institution_workflow_candidate(reference, current)
    assert reference.to_dict() == before
    assert current.connections == reference.connections and current.schedules == reference.schedules
    a, b = current.to_dict(), reference.to_dict()
    node = next(n for n in a['mechanisms'] if n['mechanism_id'] == 'developer-catalog-agenda')
    node['parameters'] = deepcopy(producer(reference).parameters)
    assert a == b
    for year in (1, 2, 4):
        assert output(SOURCE, producer(current).parameters, actors(), year) == output(
            LEGACY_SOURCE, producer(reference).parameters, actors(), year)


def test_all24_initial_shortest_assignments_are_constructible_without_duration_change():
    reference = base(); society = actors(); catalog = catalog_contract()
    directions = {d['topic']: d for d in catalog['directions']}
    choices = []
    for actor in society:
        permitted = eligible_topics(actor, catalog=catalog)
        minimum = min(directions[t]['years'] for t in permitted)
        choices.append([t for t in permitted if directions[t]['years'] == minimum])
    observed = set()
    for selected in product(*choices):
        current = topic_priority_control(reference, priorities={t: 1 for t in selected})
        result = output(SOURCE, producer(current).parameters, society)
        assignments = result['outputs']['agenda'][0]['payload']['assignments']
        assert tuple(a['direction']['topic'] for a in assignments) == selected
        for assignment, actor in zip(assignments, society):
            validate_legacy_topic_assignment(assignment, actor, year=1, catalog=catalog)
        observed.add(selected)
    assert len(observed) == 24  # Static outputs, not24 native evaluations or quality observations.


def test_priority_cannot_override_shortest_duration_or_add_a_topic():
    reference = base(); society = actors()
    current = topic_priority_control(reference, priorities={'complexity_theory': 1000000})
    result = output(SOURCE, producer(current).parameters, society)
    assert result['outputs']['agenda'][0]['payload']['assignments'][0]['direction']['topic'] == 'neural_symbolic_ai'


def test_large_integer_is_finite_without_lossy_float_conversion():
    reference = base()
    priorities = {'complexity_theory': 10 ** 400}
    current = topic_priority_control(reference, priorities=priorities)
    assert producer(current).parameters['topic_priorities'] == priorities


@pytest.mark.parametrize('priorities', [None, [], {'unknown': 1}, {1: 1}, {'logic_in_cs': True},
    {'logic_in_cs': '1'}, {'logic_in_cs': float('nan')}, {'logic_in_cs': float('inf')}])
def test_invalid_constructor_input_is_not_repaired_or_executed(priorities):
    with pytest.raises(ValueError, match='finite numeric priorities'):
        topic_priority_control(base(), priorities=priorities)


def test_helper_does_not_overwrite_arbitrary_authored_source():
    reference = base().to_dict()
    node = next(n for n in reference['mechanisms'] if n['mechanism_id'] == 'developer-catalog-agenda')
    node['parameters']['code_artifact']['source'] += '\n# authored variant\n'
    with pytest.raises(ValueError, match='literal developer'):
        topic_priority_control(SystemSpec.from_dict(reference), priorities={})
