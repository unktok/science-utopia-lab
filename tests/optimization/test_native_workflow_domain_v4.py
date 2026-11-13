"""Finite workflow-domain checks, not scientific gain or world evidence."""
from copy import deepcopy
from dataclasses import replace

import pytest

from utopia.optimization.native_fixed_production_domain import (
    CATALOG_PLANNING_SCOPE, require_fixed_production)
from utopia.optimization.native_workflow_domain_v4 import (
    CORE_STAGES, PHASE_EVENT, PLAN_EVENT, edit_workflow, execution_order,
    post_funding_cost_control, require_workflow_candidate, verify_workflow_interval)
from utopia.replay.events import EventEnvelope
from utopia.system import ScheduleSpec, SystemSpec
from utopia.system.native_planning_controls import planning_controls
from utopia.system.native_process import controlled_activity

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


@pytest.fixture
def anchor():
    return planning_controls(IMAGE, seed=61001)['assignment-reserve21-no-review-all']


def test_original_instance_literal_noop_and_real_three_phase_five_edge_contrast(anchor):
    assert require_workflow_candidate(anchor, anchor)
    assert edit_workflow(anchor, phase_updates={}, rewires=[]) == anchor
    changed = post_funding_cost_control(anchor)
    assert require_workflow_candidate(anchor, changed, structure_only=True)
    assert anchor.mechanisms == changed.mechanisms
    assert anchor.metadata == changed.metadata and anchor.initial_state == changed.initial_state
    assert sum(a != b for a, b in zip(anchor.schedules, changed.schedules)) == 3
    assert sum(a != b for a, b in zip(anchor.connections, changed.connections)) == 5
    order = execution_order(changed)
    assert order.index('world.funding') < order.index('developer-liquidity-director')
    assert order.index('developer-liquidity-effects') < order.index('world.costs') < order.index('world.communication')
    assert any(e.source_mechanism == 'world.funding' and e.target_mechanism == 'developer-liquidity-director'
        and e.source_port == 'world' for e in changed.connections)
    # Old domain must remain fixed-calendar, not be relabelled retrospectively.
    with pytest.raises(ValueError, match='schedule'):
        require_fixed_production(anchor, changed, scope=CATALOG_PLANNING_SCOPE)


def test_whole_graph_accepts_new_institution_and_source_but_not_as_structure_only(anchor):
    data = anchor.to_dict()
    node = deepcopy(next(n for n in data['mechanisms'] if n['mechanism_id'] == 'information-office'))
    node['mechanism_id'] = 'new-research-institution'
    node['parameters']['code_artifact']['source'] += '\n# Independently authored institutional algorithm\n'
    data['mechanisms'].append(node)
    data['schedules'].append({'mechanism_id': node['mechanism_id'], 'phase': 191, 'trigger': 'annual'})
    edge = deepcopy(next(e for e in data['connections'] if e['target_mechanism'] == 'information-office'))
    edge['target_mechanism'] = node['mechanism_id']; data['connections'].append(edge)
    changed = SystemSpec.from_dict(data)
    assert require_workflow_candidate(anchor, changed)
    with pytest.raises(ValueError, match='structure-only'):
        require_workflow_candidate(anchor, changed, structure_only=True)


@pytest.mark.parametrize('mutation', ['drop', 'repeat-schedule', 'missing-schedule', 'nonannual',
    'duplicate', 'wrapped-copy', 'replace', 'seed', 'plan-origin', 'paper-origin',
    'backward-edge', 'late-cost', 'late-mutator', 'early-node', 'image', 'capability', 'extra-production'])
def test_invalid_effect_or_causality_is_a_technical_error_not_a_penalty(anchor, mutation):
    data = anchor.to_dict()
    node = lambda identity: next(n for n in data['mechanisms'] if n['mechanism_id'] == identity)
    schedule = lambda identity: next(s for s in data['schedules'] if s['mechanism_id'] == identity)
    if mutation == 'drop':
        data['mechanisms'].remove(node('world.costs'))
    elif mutation == 'repeat-schedule':
        data['schedules'].append(deepcopy(schedule('world.costs')))
    elif mutation == 'missing-schedule':
        data['schedules'].remove(schedule('world.costs'))
    elif mutation == 'nonannual':
        schedule('world.costs')['trigger'] = 'never'
    elif mutation == 'duplicate':
        copy = deepcopy(node('world.costs')); copy['mechanism_id'] = 'extra-cost'
        data['mechanisms'].append(copy); data['schedules'].append({'mechanism_id': 'extra-cost', 'phase': 81})
    elif mutation == 'wrapped-copy':
        delegate = next(n for n in anchor.mechanisms if n.mechanism_id == 'world.costs')
        # Delegate ID is deliberately equal to the protected ID: counting must
        # catch this even when a mere contract equality lookup would pass.
        wrapped = replace(controlled_activity(delegate, count=1, limit=1), mechanism_id='wrapped-cost')
        spec = replace(anchor, mechanisms=(*anchor.mechanisms, wrapped),
            schedules=(*anchor.schedules, ScheduleSpec('wrapped-cost', 81)),
            connections=(*anchor.connections, replace(next(e for e in anchor.connections
                if e.target_mechanism == 'world.costs'), target_mechanism='wrapped-cost')))
        with pytest.raises(ValueError, match='duplicated/wrapped'):
            require_workflow_candidate(anchor, spec)
        return
    elif mutation == 'replace':
        node('world.costs')['parameters']['changed'] = True
    elif mutation == 'seed':
        data['initial_state']['seed'] += 1
    elif mutation in ('plan-origin', 'paper-origin'):
        target = 'world.funding' if mutation == 'paper-origin' else 'research-plan-effects'
        edge = next(e for e in data['connections'] if e['target_mechanism'] == target and e['channel'] == 'artifact')
        edge['latency'] = 1
    elif mutation == 'backward-edge':
        schedule('native-feature-extractor')['phase'] = 71
    elif mutation == 'late-cost':
        schedule('world.costs')['phase'] = 200
    elif mutation == 'late-mutator':
        schedule('developer-liquidity-effects')['phase'] = 200
    elif mutation == 'early-node':
        schedule('developer-catalog-agenda')['phase'] = 0
    elif mutation == 'image':
        node('information-office')['parameters']['runtime_image_id'] = 'sha256:' + 'a' * 64
    elif mutation == 'capability':
        node('open-domain-actions')['parameters']['capabilities']['bootstrap'].append('native.project')
    else:
        node('information-office')['implementation'] = 'native.researcher.work.v15'
    with pytest.raises(ValueError):
        require_workflow_candidate(anchor, SystemSpec.from_dict(data))


@pytest.mark.parametrize('updates,rewires', [({'unknown': 5}, []), ({'world.costs': True}, []),
    ({'world.costs': -1}, [])])
def test_literal_editor_rejects_unknown_or_noninteger_phase(anchor, updates, rewires):
    with pytest.raises(ValueError):
        edit_workflow(anchor, phase_updates=updates, rewires=rewires)


def test_editor_never_guesses_missing_or_repeated_edges_or_rescales(anchor):
    edge = anchor.connections[0]
    for rewires in ([(replace(edge, latency=1), edge)], [(edge, edge), (edge, edge)]):
        with pytest.raises(ValueError, match='exact unused'):
            edit_workflow(anchor, phase_updates={}, rewires=rewires)
    cramped = replace(anchor, schedules=tuple(replace(s, phase=163)
        if s.mechanism_id == 'world.communication' else s for s in anchor.schedules))
    with pytest.raises(ValueError, match='never rescale'):
        post_funding_cost_control(cramped)


def witness_fixture(spec, years=2):
    result = []
    nodes = {n.mechanism_id: n for n in spec.mechanisms}
    schedules = {s.mechanism_id: s for s in spec.schedules}
    for year in range(1, years + 1):
        for identity in execution_order(spec):
            n = nodes[identity]
            if not n.implementation.startswith(('native.phase.', 'native.activity.')):
                continue
            stage = n.implementation.split('.')[2]
            if stage not in CORE_STAGES: continue
            result.append(EventEnvelope.create(sequence=len(result), year=year, phase=schedules[identity].phase,
                event_type=PLAN_EVENT if stage == 'plan-effects' else PHASE_EVENT, payload={'stage': stage},
                provenance={'mechanism_id': identity, 'implementation': n.implementation,
                    'implementation_version': n.version, 'system_id': spec.system_id,
                    'system_fingerprint': spec.fingerprint, 'period': year, 'trigger': 'annual'}))
    return result


def test_synthetic_witness_reader_counts_every_effect_and_uses_actual_schedules(anchor):
    changed = post_funding_cost_control(anchor)
    events = witness_fixture(changed)
    proof = verify_workflow_interval(anchor, changed, events, years=2)
    assert proof['native_effects_per_year'] == 12 and proof['effect_witnesses'] == 24
    assert not proof['cold_audit_replaced']
    # A forged event name under an institutional owner is not a native witness.
    forged = replace(events[0], provenance={**events[0].provenance, 'mechanism_id': 'information-office'})
    with pytest.raises(ValueError, match='missing or duplicated'):
        verify_workflow_interval(anchor, changed, [forged, *events[1:]], years=2)


@pytest.mark.parametrize('mutation', ['missing', 'duplicated', 'wrong-phase', 'wrong-source', 'wrong-stage', 'wrong-order'])
def test_witness_reader_rejects_incomplete_or_mismatched_execution(anchor, mutation):
    events = witness_fixture(anchor)
    if mutation == 'missing': events.pop()
    elif mutation == 'duplicated': events.append(events[0])
    elif mutation == 'wrong-phase': events[0] = replace(events[0], phase=100)
    elif mutation == 'wrong-source':
        events[0] = replace(events[0], provenance={**events[0].provenance, 'system_fingerprint': '0' * 64})
    elif mutation == 'wrong-stage': events[0] = replace(events[0], payload={'stage': 'close'})
    else: events[0] = replace(events[0], sequence=10000)
    with pytest.raises(ValueError):
        verify_workflow_interval(anchor, anchor, events, years=2)
