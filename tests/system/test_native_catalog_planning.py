"""Real native action and isolated policy execution; no scientific model result."""
from copy import deepcopy
from dataclasses import replace

import pytest

from tests.system.test_native_open_domain import unit_world, command, run_commands, BOOTSTRAP
from utopia.agents.research_direction import AVAILABLE_DIRECTIONS
from utopia.optimization.native_design_space import require_candidate_in_space
from utopia.optimization.native_fixed_production_domain import allow_review_routing, allow_catalog_planning
from utopia.system import SystemSpec
from utopia.system.native_catalog_planning import (
    ACTION, EVENT, SOURCE, catalog_contract, catalog_agenda_control, validate_catalog_assignment,
)
from utopia.system.native_information_institution import information_system, information_design_space
from utopia.system.runtime import GraphRuntimeError

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'
SHORT = next(d for d in AVAILABLE_DIRECTIONS if d.years == 1)
LONG = next(d for d in AVAILABLE_DIRECTIONS if d.years == 3)


def setup():
    kernel, actors, ledger, ctx = unit_world()
    kernel._simulation.is_exploration_experiment = False
    actor = actors['a']
    actor.expertise = [SHORT, LONG]
    actor.project_start_year = actor.project_end_year = 0
    actor.newest_direction = None
    grants = {'bootstrap': [ACTION, 'native.context'], 'roles': {}}
    ctx = replace(ctx, mechanism=replace(ctx.mechanism, parameters={'capabilities': grants}))
    assignment = {'actor_id': 'a', 'direction': deepcopy(LONG.to_dict()), 'detailed_focus': 'Real catalog direction',
                  'reason': 'Arbitrary institution choice, not necessarily shortest',
                  'project_start_year': 1, 'project_end_year': 3}
    return kernel, actors, ctx, assignment


def test_real_atomic_action_accepts_nonshortest_choice_without_merit_veto():
    kernel, actors, ctx, assignment = setup()
    result = run_commands(kernel, ctx, command('project', ACTION, {'assignment': assignment}, BOOTSTRAP))
    actor = actors['a']
    assert actor.newest_direction['direction'].to_dict() == LONG.to_dict()
    assert (actor.project_start_year, actor.project_end_year) == (1, 3)
    proof = next(e for e in result.events if e.event_type == EVENT)
    assert proof.payload['assignment'] == assignment
    assert proof.payload['catalog_sha256'] == catalog_contract()['directions_sha256']
    assert not proof.payload['shortest_or_merit_rule_enforced']
    assert any(e.event_type == 'native.domain.project_applied' for e in result.events)


@pytest.mark.parametrize('bad', ['duration', 'topic', 'content', 'start', 'end', 'ongoing', 'inactive', 'filtered', 'exploration'])
def test_false_completion_or_different_choice_domain_rolls_back_whole_batch(bad):
    kernel, actors, ctx, assignment = setup()
    actor = actors['a']
    if bad == 'duration':
        assignment['direction']['years'] = 1
        assignment['project_end_year'] = 1
    elif bad == 'topic':
        assignment['direction'] = next(d.to_dict() for d in AVAILABLE_DIRECTIONS if d.topic not in (SHORT.topic, LONG.topic))
        assignment['project_end_year'] = assignment['direction']['years']
    elif bad == 'content':
        assignment['direction']['keywords'].append('fabricated native content')
    elif bad == 'start':
        assignment['project_start_year'] = 0
    elif bad == 'end':
        assignment['project_end_year'] = 1
    elif bad == 'ongoing':
        actor.project_end_year = 2
    elif bad == 'inactive':
        actor.is_active = False
    elif bad == 'filtered':
        actor._filtered_candidates = [SHORT]
    else:
        kernel._simulation.is_exploration_experiment = True
    before = (actor.project_start_year, actor.project_end_year, actor.newest_direction, actor.resources)
    with pytest.raises(GraphRuntimeError):
        run_commands(kernel, ctx,
            command('message', 'native.context', {'actor_ids': ['a'], 'content': {'must_not_commit': True}, 'artifact_ids': []}, BOOTSTRAP),
            command('invalid', ACTION, {'assignment': assignment}, BOOTSTRAP))
    assert (actor.project_start_year, actor.project_end_year, actor.newest_direction, actor.resources) == before
    assert not hasattr(actor, 'institutional_context') and kernel.open_domain_state == {}


def test_new_authority_is_explicit_and_cannot_bypass_old_or_new_production_guards():
    anchor = information_system(IMAGE)
    old = information_design_space(anchor, 'code-and-graph', fixed_production=True)
    routing = allow_review_routing(anchor, old)
    planning = allow_catalog_planning(anchor, routing)
    candidate = catalog_agenda_control(anchor, IMAGE, actuation='project')
    for domain in (old, routing):
        with pytest.raises(ValueError, match='catalog project authority'):
            require_candidate_in_space(anchor, candidate, domain)
    require_candidate_in_space(anchor, candidate, planning)
    raw = candidate.to_dict()
    next(n for n in raw['mechanisms'] if n['mechanism_id'] == 'developer-catalog-effects')['parameters']['capabilities']['bootstrap'].append('native.project')
    with pytest.raises(ValueError, match='project reassignment'):
        require_candidate_in_space(anchor, SystemSpec.from_dict(raw), planning)
    raw = candidate.to_dict()
    next(n for n in raw['mechanisms'] if n['mechanism_id'] == 'world.costs')['parameters']['new_fake_cost'] = 0
    with pytest.raises(ValueError, match='production/accounting contract'):
        require_candidate_in_space(anchor, SystemSpec.from_dict(raw), planning)


def test_common_source_catalog_authority_wiring_and_exact_agenda_across_modes():
    anchor = information_system(IMAGE)
    specs = [catalog_agenda_control(anchor, IMAGE, actuation=m) for m in ('cut', 'information', 'project')]
    assert specs[0].connections == specs[1].connections == specs[2].connections
    assert specs[0].schedules == specs[1].schedules == specs[2].schedules
    nodes = [next(n for n in s.mechanisms if n.mechanism_id == 'developer-catalog-agenda') for s in specs]
    assert all(n.parameters['code_artifact']['source'] == SOURCE for n in nodes)
    catalog = catalog_contract()
    actor = {'id': 'a', 'can_author': True, 'is_active': True, 'project_end_year': 0,
             'expertise': [LONG.topic, SHORT.topic]}
    world = {'ecosystem': {'agents': [actor, {**actor, 'id': 'busy', 'project_end_year': 3}]}}
    outputs = []
    # Pure policy unit execution only. Actual trust-boundary execution is
    # exercised with the pinned Docker executor in the native integration.
    namespace = {};exec(SOURCE, namespace)
    for node in nodes:
        result = namespace['step']({'inputs': {'world': [{'payload': deepcopy(world)}]},
            'parameters': deepcopy(node.parameters), 'period': 1, 'state': {}})
        outputs.append(result['outputs'])
    assert outputs[0]['agenda'] == outputs[1]['agenda'] == outputs[2]['agenda']
    assignment = outputs[2]['agenda'][0]['payload']['assignments'][0]
    assert assignment['direction'] == SHORT.to_dict()
    assert not outputs[0]['commands']
    assert outputs[1]['commands'][0]['payload']['action'] == 'native.context'
    assert outputs[2]['commands'][0]['payload']['action'] == ACTION
    validate_catalog_assignment(assignment, actor, year=1, catalog=catalog)
