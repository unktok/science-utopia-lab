"""Typed authority to choose real native review work, not a review policy.

Institution code runs only in its existing isolated executor. This capability
checks exact identities/accounting and delegates all actual work to phase 3.
"""
from copy import deepcopy
from dataclasses import replace

from .code_mechanisms import sha
from .model import ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from .runtime import GraphRuntimeError, MechanismEvent, MechanismResult, MechanismValue

BATCH = 'native-review-input-batch-v13'
PLAN = 'native-review-routing-plan-v13'
SNAPSHOT = 'native.world.review-inputs.v13'
REVIEW = 'native.phase.review.with-routing.v13'
EVENT = 'native.system.review_routing_applied'
STATE = 'scienceutopia.native-review-routing-state.v13'


def enable_review_routing(spec, *, source, source_port, snapshot='review-task-inputs',
                          source_input='batch', review='world.review', snapshot_phase=105):
    """Wire an existing arbitrary producer between native input and review.

    The caller supplies its own source, port contracts and algorithm. No source
    or routing decision is manufactured here. The default original graph uses
    costs at 100, producer must run between snapshot 105 and review 120.
    """
    nodes = {n.mechanism_id: n for n in spec.mechanisms}
    phases = {s.mechanism_id: s.phase for s in spec.schedules}
    if (source not in nodes or review not in nodes or snapshot in nodes
            or nodes[review].implementation != 'native.phase.review.v1'
            or 'world.costs' not in nodes
            or not phases['world.costs'] < snapshot_phase < phases[source] < phases[review]):
        raise GraphRuntimeError('review routing needs explicit original review/costs and ordered input/producer/review')
    if (not any(p.port_id == source_input and p.channel == ChannelKind.ARTIFACT and p.artifact_type == BATCH
                for p in nodes[source].inputs)
            or not any(p.port_id == source_port and p.channel == ChannelKind.ARTIFACT and p.artifact_type == PLAN
                       for p in nodes[source].outputs)):
        raise GraphRuntimeError('routing producer must explicitly declare native batch/plan ports')
    snapshot_node = MechanismSpec(snapshot, MechanismFamily.CUSTOM, SNAPSHOT,
        inputs=(PortSpec('world', ChannelKind.ARTIFACT, 'native-world-observation'),),
        outputs=(PortSpec('batch', ChannelKind.ARTIFACT, BATCH),))
    updated = tuple(replace(n, implementation=REVIEW,
        inputs=(*n.inputs, PortSpec('batch', ChannelKind.ARTIFACT, BATCH),
                PortSpec('routing', ChannelKind.ARTIFACT, PLAN))) if n.mechanism_id == review else n
        for n in spec.mechanisms)
    existing_types = {a.artifact_type_id for a in spec.artifact_types}
    return replace(spec, mechanisms=(*updated, snapshot_node),
        artifact_types=(*spec.artifact_types, *(ArtifactTypeSpec(a) for a in (BATCH, PLAN) if a not in existing_types)),
        schedules=(*spec.schedules, ScheduleSpec(snapshot, snapshot_phase)),
        connections=(*spec.connections,
            ConnectionSpec('world.costs', 'world', snapshot, 'world', ChannelKind.ARTIFACT),
            ConnectionSpec(snapshot, 'batch', source, source_input, ChannelKind.ARTIFACT),
            ConnectionSpec(snapshot, 'batch', review, 'batch', ChannelKind.ARTIFACT),
            ConnectionSpec(source, source_port, review, 'routing', ChannelKind.ARTIFACT)))


def review_input_batch(simulation, year):
    """Exact current submissions and ORIGINAL per-paper reviewer eligibility.

    Original eligibility is can_review plus paper-author/COI exclusions, not an
    invented active-status/fairness rule. No RNG, prompt or model is touched.
    """
    papers, seen = [], set()
    for conference in simulation.conference_system.conferences:
        for paper in conference.submitted_papers:
            key = (conference.conference_id, paper['id'])
            if key in seen or paper.get('conference') != key[0] or paper.get('year') != year:
                raise GraphRuntimeError('native review batch has duplicate/foreign/stale submission identity')
            seen.add(key)
            author_ids = simulation._get_all_author_ids(paper)
            excluded = set(author_ids)
            for aid in author_ids:
                excluded.update(simulation.ecosystem.get_agent_by_id(aid).conflict_of_interest)
            eligible = simulation.ecosystem.get_available_reviewers(exclude_agent_ids=list(excluded))
            papers.append({'conference_id': key[0], 'paper_id': key[1], 'paper': deepcopy(paper),
                'eligible_reviewer_ids': [a.id for a in eligible]})
    result = {'schema': BATCH, 'year': year, 'papers': papers}
    sha(result)  # finite JSON preflight
    return result


def _one(context, port, schema):
    values = context.inputs.get(port, ())
    if (len(values) != 1 or not values[0].lineage_event_ids
            or values[0].emitted_period != context.period
            or values[0].payload.get('schema') != schema):
        raise GraphRuntimeError('review routing requires one current causally bound ' + port)
    value = values[0]
    payload = deepcopy(dict(value.payload))
    sha(payload)
    origin = {'source_mechanism': value.source_mechanism, 'source_port': value.source_port,
        'emitted_period': value.emitted_period, 'input_event_ids': list(value.lineage_event_ids)}
    return payload, origin


def validate_routing_plan(simulation, year, batch, plan):
    """Preflight the complete command before any native review mutation/call."""
    actual = review_input_batch(simulation, year)
    if batch != actual:
        raise GraphRuntimeError('routing input batch differs from actual native submissions/eligibility')
    if (not isinstance(plan, dict) or set(plan) != {'schema', 'year', 'batch_sha256', 'tasks'}
            or plan['schema'] != PLAN or type(plan['year']) is not int or plan['year'] != year
            or plan['batch_sha256'] != sha(batch) or not isinstance(plan['tasks'], list)):
        raise GraphRuntimeError('routing command shape/year/input batch hash differs')
    sha(plan)
    available = {(p['conference_id'], p['paper_id']): p for p in batch['papers']}
    population = simulation.ecosystem.agent_population
    assignment = {p['paper_id']: [] for p in batch['papers']}
    if len(assignment) != len(available):
        raise GraphRuntimeError('original native assignment requires globally unique paper IDs')
    seen = set()
    for task in plan['tasks']:
        if (not isinstance(task, dict) or set(task) != {'conference_id', 'paper_id', 'reviewer_id'}
                or any(not isinstance(v, str) or not v for v in task.values())):
            raise GraphRuntimeError('routing task requires exact conference/paper/reviewer string identities')
        key = task['conference_id'], task['paper_id']
        identity = (*key, task['reviewer_id'])
        if key not in available or task['reviewer_id'] not in available[key]['eligible_reviewer_ids']:
            raise GraphRuntimeError('routing task references unknown/ineligible actual paper or reviewer')
        if identity in seen:
            raise GraphRuntimeError('routing task duplicates an actual paper/reviewer pair')
        seen.add(identity)
        assignment[task['paper_id']].append(population[task['reviewer_id']])
    # Empty plans and zero-reviewed papers are valid. Native phase3 retains its
    # original internal fallback, NOT a fabricated raw review. Original legacy
    # selection rejects absent reviews; a complete such design must explicitly
    # choose a compatible selection source rather than receive an implicit rule.
    return assignment


def validate_routing_state(state, events, mechanism_id):
    expected = [e for e in events if e.event_type == EVENT
        and e.provenance.get('mechanism_id') == mechanism_id]
    if not state and not expected:
        return
    if (not expected or set(state) != {'schema', 'last_period', 'receipt_sha256'}
            or state['schema'] != STATE or state['last_period'] != expected[-1].year
            or state['receipt_sha256'] != sha(expected[-1].payload)):
        raise GraphRuntimeError('native routing persistent state differs from committed receipt')


def validate_routing_receipt(receipt):
    """Check saved command/native-work hashes without executing any source."""
    if (sha(receipt['batch']) != receipt['batch_sha256']
            or sha(receipt['command']) != receipt['command_sha256']
            or receipt['command']['batch_sha256'] != receipt['batch_sha256']
            or sha(receipt['native_tasks']) != receipt['native_tasks_sha256']
            or receipt['actual_review_count'] != len(receipt['native_tasks'])
            or not receipt['batch_origin']['input_event_ids']
            or not receipt['command_origin']['input_event_ids']):
        raise GraphRuntimeError('saved native review routing receipt hash/identity differs')
    requested = {(t['conference_id'], t['paper_id'], t['reviewer_id']) for t in receipt['command']['tasks']}
    executed = [(t['conference_id'], t['paper_id'], t['reviewer_id']) for t in receipt['native_tasks']]
    if len(requested) != len(receipt['command']['tasks']) or set(executed) != requested or len(executed) != len(requested):
        raise GraphRuntimeError('saved native routing tasks differ from actual execution identities')


def register_review_routing(kernel, registry):
    def snapshot(context):
        batch = review_input_batch(kernel._simulation, context.period)
        return MechanismResult(outputs={'batch': (MechanismValue(batch,
            artifact_ids=tuple(p['paper_id'] for p in batch['papers'])),)},
            events=(MechanismEvent('native.system.review_inputs_bound',
                payload={'batch_sha256': sha(batch), 'batch': batch}),))

    def review(context):
        sim = kernel._simulation
        if not hasattr(sim.llm, 'generate_batch'):
            raise GraphRuntimeError('native routing requires original batched model interface')
        validate_routing_state(dict(context.state), kernel.events, context.mechanism.mechanism_id)
        if context.state and context.state['last_period'] >= context.period:
            raise GraphRuntimeError('native routing cannot repeat or rewind a committed year')
        batch, batch_origin = _one(context, 'batch', BATCH)
        plan, plan_origin = _one(context, 'routing', PLAN)
        assignment = validate_routing_plan(sim, context.period, batch, plan)
        result = kernel._stage('review', context, review_assignment=assignment, force_review_identity=True)
        bound = next(e.payload for e in result.events if e.event_type == 'native.system.review_tasks_bound')
        expected = [(p['conference_id'], p['paper_id'], reviewer.id)
                    for p in batch['papers'] for reviewer in assignment[p['paper_id']]]
        actual = [(t['conference_id'], t['paper_id'], t['reviewer_id']) for t in bound['tasks']]
        if actual != expected:
            raise GraphRuntimeError('executed native review work differs from validated routing plan')
        receipt = {'schema': PLAN, 'year': context.period, 'batch': batch,
            'batch_sha256': sha(batch), 'batch_origin': batch_origin,
            'command': plan, 'command_sha256': sha(plan), 'command_origin': plan_origin,
            'native_tasks': deepcopy(bound['tasks']), 'native_tasks_sha256': bound['tasks_sha256'],
            'actual_review_count': len(bound['tasks'])}
        return replace(result, events=(*result.events, MechanismEvent(EVENT,
            actor_ids=tuple(dict.fromkeys(t['reviewer_id'] for t in plan['tasks'])),
            artifact_ids=tuple(p['paper_id'] for p in batch['papers']), payload=receipt)),
            next_state={'schema': STATE, 'last_period': context.period, 'receipt_sha256': sha(receipt)})

    for identity, handler in ((SNAPSHOT, snapshot), (REVIEW, review)):
        registry.register(identity, 1, handler)
