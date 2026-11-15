"""Original native actuation with explicit new authority; no model-quality claim."""
from copy import deepcopy
from dataclasses import replace

import pytest

from tests.system.test_native_catalog_planning import setup, IMAGE
from tests.system.test_native_open_domain import run_commands, command, BOOTSTRAP
from utopia.agents.research_direction import AVAILABLE_DIRECTIONS
from utopia.optimization.native_design_space import require_candidate_in_space
from utopia.optimization.native_fixed_production_domain import (
    SCOPE, ROUTING_SCOPE, CATALOG_PLANNING_SCOPE, require_fixed_production)
from utopia.optimization.native_workflow_domain_v4 import require_workflow_candidate
from utopia.optimization.native_workflow_domain_v5 import (
    legacy_topic_workflow_design_space, require_legacy_topic_workflow_candidate)
from utopia.system import SystemSpec
from utopia.system.native_catalog_planning import ACTION as CORE_ACTION, catalog_contract, validate_catalog_assignment
from utopia.system.native_legacy_topic_planning import (
    ACTION, EVENT, eligible_topics, validate_legacy_topic_assignment)
from utopia.system.runtime import GraphRuntimeError


def example():
    kernel, actors, ctx, assignment = setup()
    core = next(d for d in AVAILABLE_DIRECTIONS if d.topic == 'logic_in_cs')
    related = next(d for d in AVAILABLE_DIRECTIONS if d.topic == 'neural_symbolic_ai')
    actors['a'].expertise = [core]
    ctx = replace(ctx, mechanism=replace(ctx.mechanism,
        parameters={'capabilities': {'bootstrap': [ACTION, CORE_ACTION, 'native.context'], 'roles': {}}}))
    assignment['direction'] = deepcopy(related.to_dict())
    assignment['project_end_year'] = related.years
    return kernel, actors, ctx, assignment


@pytest.fixture(autouse=True)
def original_catalog_is_never_modified_by_test_payloads():
    before = catalog_contract()
    yield
    assert catalog_contract() == before


def snapshot(actor):
    return {'id': actor.id, 'can_author': actor.can_author, 'is_active': actor.is_active,
            'project_end_year': actor.project_end_year, 'expertise': [d.topic for d in actor.expertise]}


def test_related_topic_uses_original_content_duration_and_native_project_consumer():
    kernel, actors, ctx, assignment = example()
    before = deepcopy(assignment)
    result = run_commands(kernel, ctx, command('new', ACTION, {'assignment': assignment}, BOOTSTRAP))
    actual = actors['a'].newest_direction['direction'].to_dict()
    assert actual == before['direction'] and assignment == before
    assert actors['a'].project_end_year == 1 and actors['a'].project_start_year == 1
    assert actors['a'].resources == 20 and [d.topic for d in actors['a'].expertise] == ['logic_in_cs']
    proof = next(e for e in result.events if e.event_type == EVENT)
    assert proof.payload['eligible_actor_before']['expertise'] == ['logic_in_cs']
    assert 'neural_symbolic_ai' in proof.payload['eligible_topics']
    assert not proof.payload['shortest_or_merit_rule_enforced']
    assert any(e.event_type == 'native.domain.project_applied' for e in result.events)


def test_historical_core_action_does_not_silently_gain_related_topic_authority():
    kernel, actors, ctx, assignment = example()
    with pytest.raises(GraphRuntimeError, match='displayed topic'):
        run_commands(kernel, ctx, command('old', CORE_ACTION, {'assignment': assignment}, BOOTSTRAP))
    assert actors['a'].newest_direction is None


def test_pure_union_is_one_hop_and_all_eligible_nonshortest_choices_are_legal():
    _, actors, _, _ = example()
    actor = snapshot(actors['a']); catalog = catalog_contract()
    core = actors['a'].expertise[0]
    actual = {d.topic: d for d in AVAILABLE_DIRECTIONS}
    expected = sorted(({core.topic} | set(core.related_topics)) & actual.keys())
    assert eligible_topics(actor, catalog=catalog) == expected
    second_hop_only = {t for topic in expected for t in actual[topic].related_topics} - set(expected)
    assert second_hop_only & actual.keys()
    for topic in expected:
        d = actual[topic]
        assignment = {'actor_id': actor['id'], 'direction': d.to_dict(), 'detailed_focus': 'SCRIPTED',
            'reason': 'Any eligible choice, including longer ones', 'project_start_year': 1,
            'project_end_year': d.years}
        validate_legacy_topic_assignment(assignment, actor, year=1, catalog=catalog)
        if topic != core.topic:
            with pytest.raises(GraphRuntimeError):
                validate_catalog_assignment(assignment, actor, year=1, catalog=catalog)


@pytest.mark.parametrize('bad', ['unrelated', 'two-hops', 'shortened', 'content', 'ongoing',
    'inactive', 'exploration', 'filtered', 'mutated-expertise', 'no-grant'])
def test_unknown_or_changed_native_laws_fail_atomically_without_context_commit(bad):
    kernel, actors, ctx, assignment = example(); actor = actors['a']
    if bad in ('unrelated', 'two-hops'):
        topics = set(eligible_topics(snapshot(actor), catalog=catalog_contract()))
        if bad == 'two-hops':
            by = {d.topic: d for d in AVAILABLE_DIRECTIONS}
            options = {t for topic in topics for t in by[topic].related_topics} - topics
        else:
            options = {d.topic for d in AVAILABLE_DIRECTIONS} - topics
        direction = next(d for d in AVAILABLE_DIRECTIONS if d.topic in options)
        assignment['direction'] = direction.to_dict(); assignment['project_end_year'] = direction.years
    if bad == 'shortened':
        assignment['direction']['years'] = 0; assignment['project_end_year'] = 0
    if bad == 'content': assignment['direction']['keywords'].append('invented physics')
    if bad == 'ongoing': actor.project_end_year = 2
    if bad == 'inactive': actor.is_active = False
    if bad == 'exploration': kernel._simulation.is_exploration_experiment = True
    if bad == 'filtered': actor._filtered_candidates = [actor.expertise[0]]
    if bad == 'mutated-expertise':
        actor.expertise = deepcopy(actor.expertise); actor.expertise[0].years = 1
    if bad == 'no-grant':
        ctx = replace(ctx, mechanism=replace(ctx.mechanism,
            parameters={'capabilities': {'bootstrap': ['native.context'], 'roles': {}}}))
    before = (actor.project_start_year, actor.project_end_year, actor.newest_direction, actor.resources)
    with pytest.raises(GraphRuntimeError):
        run_commands(kernel, ctx,
            command('advice', 'native.context', {'actor_ids': ['a'], 'content': {'not_committed': True},
                                               'artifact_ids': []}, BOOTSTRAP),
            command('invalid', ACTION, {'assignment': assignment}, BOOTSTRAP))
    assert (actor.project_start_year, actor.project_end_year, actor.newest_direction, actor.resources) == before
    assert not hasattr(actor, 'institutional_context') and not kernel.open_domain_state


def test_new_authority_requires_explicit_v5_and_keeps_code_graph_and_workflow_freedom():
    from utopia.system.native_planning_controls import planning_controls
    anchor = planning_controls(IMAGE, seed=61001)['assignment-reserve21-no-review-all']
    raw = anchor.to_dict()
    node = next(n for n in raw['mechanisms'] if n['mechanism_id'] == 'developer-catalog-effects')
    node['parameters']['capabilities']['bootstrap'].append(ACTION)
    candidate = SystemSpec.from_dict(raw)
    for scope in (SCOPE, ROUTING_SCOPE, CATALOG_PLANNING_SCOPE):
        with pytest.raises(ValueError): require_fixed_production(anchor, candidate, scope=scope)
    with pytest.raises(ValueError, match='workflow-v5'): require_workflow_candidate(anchor, candidate)
    space = legacy_topic_workflow_design_space(anchor)
    require_candidate_in_space(anchor, candidate, space)
    assert require_legacy_topic_workflow_candidate(anchor, candidate)
    # A new institutional source/node and new wire are not a predefined menu.
    added = deepcopy(next(n for n in raw['mechanisms'] if n['mechanism_id'] == 'information-office'))
    added['mechanism_id'] = 'scripted-new-commons'
    added['parameters']['code_artifact']['source'] += '\n# Different authored institution\n'
    raw['mechanisms'].append(added)
    raw['schedules'].append({'mechanism_id': added['mechanism_id'], 'phase': 191, 'trigger': 'annual'})
    edge = deepcopy(next(e for e in raw['connections'] if e['target_mechanism'] == 'information-office'))
    edge['target_mechanism'] = added['mechanism_id']; raw['connections'].append(edge)
    require_candidate_in_space(anchor, SystemSpec.from_dict(raw), space)
    next(n for n in raw['mechanisms'] if n['mechanism_id'] == 'world.costs')['parameters']['scripted-change-native-effect'] = True
    with pytest.raises(ValueError): require_candidate_in_space(anchor, SystemSpec.from_dict(raw), space)
