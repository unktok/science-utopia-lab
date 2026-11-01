"""Opt-in native research activities as explicit, data-only graph contracts.

This bridge supplies domain effects, not institution algorithms. Free sandboxed
Python/LLM mechanisms can write plans and amendments; the host checks identities
and native project consistency, not research merit. The legacy graph is intact.
"""
from copy import deepcopy
from dataclasses import replace

from utopia.agents.research_direction import ResearchDirection
from .code_mechanisms import sha, canonical
from .model import ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from .runtime import GraphRuntimeError, MechanismEvent, MechanismResult, MechanismValue

PLAN = 'native-research-plan-v1'
PAPERS = 'native-paper-batch-v1'
AMENDMENT = 'native-research-amendment-v1'
PREFIX = 'native.activity.'
EFFECT = 'native.system.research_plan_applied'


def activity_world_system(spec=None, *, seed=42):
    """Contain the original world, replacing only its private activity plumbing.

    No scientific phase is omitted. To invent a different process, edit the
    resulting ordinary SystemSpec and explicitly wire its typed capabilities.
    """
    from .native_kernel import legacy_world_system
    spec = spec or legacy_world_system(seed=seed)
    stages = {'resubmissions', 'research', 'collaboration', 'submission', 'funding'}
    by_id = {n.mechanism_id: n for n in spec.mechanisms}
    if any('world.' + stage not in by_id or by_id['world.' + stage].implementation !=
           'native.phase.' + stage + '.v1' for stage in stages):
        raise GraphRuntimeError('activity adapter requires the five declared original native stage interfaces')
    modified = []
    for node in spec.mechanisms:
        stage = node.mechanism_id.removeprefix('world.')
        if stage not in stages:
            modified.append(node)
            continue
        inputs, outputs = node.inputs, node.outputs
        if stage in {'collaboration', 'submission'}:
            inputs += (PortSpec('plans', ChannelKind.ARTIFACT, PLAN),)
        if stage in {'submission', 'funding'}:
            inputs += (PortSpec('papers', ChannelKind.ARTIFACT, PAPERS),)
        if stage in {'research', 'collaboration'}:
            outputs += (PortSpec('plans' if stage == 'research' else 'planned', ChannelKind.ARTIFACT, PLAN),)
        if stage in {'resubmissions', 'submission'}:
            outputs += (PortSpec('papers' if stage == 'resubmissions' else 'submitted', ChannelKind.ARTIFACT, PAPERS),)
        modified.append(replace(node, implementation=PREFIX + stage + '.v1', inputs=inputs, outputs=outputs))
    effect = MechanismSpec('research-plan-effects', MechanismFamily.CUSTOM, PREFIX + 'plan-effects.v1',
        inputs=(PortSpec('plans', ChannelKind.ARTIFACT, PLAN),
                PortSpec('amendments', ChannelKind.ARTIFACT, AMENDMENT, required=False)),
        outputs=(PortSpec('applied', ChannelKind.ARTIFACT, PLAN),))
    edges = [('world.research', 'plans', effect.mechanism_id, 'plans'),
             (effect.mechanism_id, 'applied', 'world.collaboration', 'plans'),
             ('world.collaboration', 'planned', 'world.submission', 'plans'),
             ('world.resubmissions', 'papers', 'world.submission', 'papers'),
             ('world.submission', 'submitted', 'world.funding', 'papers')]
    types = {a.artifact_type_id for a in spec.artifact_types}
    return replace(spec, mechanisms=(*modified, effect),
        artifact_types=(*spec.artifact_types, *(ArtifactTypeSpec(t) for t in (PLAN, PAPERS, AMENDMENT) if t not in types)),
        schedules=(*spec.schedules, ScheduleSpec(effect.mechanism_id, 50)),
        connections=(*spec.connections, *(ConnectionSpec(*e, ChannelKind.ARTIFACT) for e in edges)))


def add_activity_plan_authority(spec, *, source, source_port, latency=0):
    """Explicitly grant an arbitrary producer the research-plan effect input."""
    return replace(spec, connections=(*spec.connections, ConnectionSpec(source, source_port,
        'research-plan-effects', 'amendments', ChannelKind.ARTIFACT, latency=latency)))


def _one(context, port, schema):
    values = context.inputs.get(port, ())
    if len(values) != 1 or values[0].payload.get('schema') != schema:
        raise GraphRuntimeError('native activity requires exactly one explicit ' + port + ' bundle')
    value = values[0]
    if not value.lineage_event_ids or value.emitted_period != context.period:
        raise GraphRuntimeError('native activity bundle must have current-year causal provenance')
    return deepcopy(dict(value.payload))


def _actors(kernel):
    return {a.id: a for a in kernel._simulation.ecosystem.get_available_authors()}


def _plan(year, directions, authors, actors):
    return {'schema': PLAN, 'year': year, 'assignments': [dict(actor_id=aid,
        direction=d['direction'].to_dict(), detailed_focus=d['detailed_focus'], reason=d['reason'],
        project_start_year=actors[aid].project_start_year, project_end_year=actors[aid].project_end_year)
        for aid, d in directions.items()], 'submit_actor_ids': [a.id for a in authors]}


def _validate_plan(kernel, payload, year):
    actors = _actors(kernel)
    if (set(payload) != {'schema', 'year', 'assignments', 'submit_actor_ids'} or payload['schema'] != PLAN
            or type(payload['year']) is not int or payload['year'] != year
            or not isinstance(payload['assignments'], list) or not isinstance(payload['submit_actor_ids'], list)):
        raise GraphRuntimeError('invalid native research plan shape/year')
    try:
        canonical(payload)  # finite JSON only
    except (TypeError, ValueError) as error:
        raise GraphRuntimeError('native research plan must be finite JSON') from error
    if len(payload['assignments']) > len(actors):
        raise GraphRuntimeError('native plan repeats or invents actors')
    directions, staged = {}, {}
    for item in payload['assignments']:
        if (not isinstance(item, dict) or set(item) != {'actor_id', 'direction', 'detailed_focus', 'reason',
                'project_start_year', 'project_end_year'} or not isinstance(item['actor_id'], str)
                or item['actor_id'] not in actors or item['actor_id'] in directions):
            raise GraphRuntimeError('native plan must reference unique existing author IDs')
        d = item['direction']
        if (not isinstance(d, dict) or set(d) != {'topic', 'focus_areas', 'years', 'keywords', 'related_topics'}
                or not isinstance(d['topic'], str) or not d['topic'].strip()
                or type(d['years']) is not int or d['years'] < 1
                or not isinstance(d['focus_areas'], list)
                or any(not isinstance(s, str) for s in d['focus_areas'])
                or not isinstance(d['keywords'], list) or any(not isinstance(s, str) for s in d['keywords'])
                or (d['related_topics'] is not None and (not isinstance(d['related_topics'], list)
                    or any(not isinstance(s, str) for s in d['related_topics'])))
                or any(not isinstance(item[k], str) for k in ('detailed_focus', 'reason'))):
            raise GraphRuntimeError('native research direction requires explicit free-text/list/duration fields')
        start, end = item['project_start_year'], item['project_end_year']
        if (type(start) is not int or type(end) is not int or not 1 <= start <= year
                or end != start + d['years'] - 1):
            raise GraphRuntimeError('native project timeline must match its declared positive duration')
        aid = item['actor_id']
        directions[aid] = {'direction': ResearchDirection.from_dict(deepcopy(d)),
            'detailed_focus': item['detailed_focus'], 'reason': item['reason']}
        staged[aid] = (start, end)
    ids = payload['submit_actor_ids']
    if any(not isinstance(aid, str) for aid in ids) or len(ids) != len(set(ids)):
        raise GraphRuntimeError('native submitter IDs must be unique strings')
    if any(aid not in staged or not actors[aid].is_active or staged[aid][1] != year for aid in ids):
        raise GraphRuntimeError('native submitters require real active actors and projects completing this year')
    return directions, [actors[aid] for aid in ids], staged


def apply_research_plans(kernel, context):
    """Commit complete typed plans/optional code-authored patches atomically.

    Delayed amendments explicitly name their target year, unlike the current-year
    base bundle. No research ranking, fairness threshold, or topic catalog exists.
    """
    payload = _one(context, 'plans', PLAN)
    year = context.period
    # Validate the base before using its IDs to address amendments.
    _validate_plan(kernel, payload, year)
    items = {i['actor_id']: i for i in payload['assignments']}
    touched, origins = set(), []
    for value in context.inputs.get('amendments', ()):
        command = deepcopy(dict(value.payload))
        if (set(command) != {'schema', 'target_year', 'assignment', 'submit'} or command['schema'] != AMENDMENT
                or type(command['target_year']) is not int or command['target_year'] != year
                or type(command['submit']) is not bool or not isinstance(command['assignment'], dict)
                or value.emitted_period > year or not value.lineage_event_ids):
            raise GraphRuntimeError('native amendment requires exact target year, assignment, submit and causal source')
        aid = command['assignment'].get('actor_id')
        if not isinstance(aid, str) or aid not in items or aid in touched:
            raise GraphRuntimeError('native amendment actors must be existing plan IDs without conflicting writers')
        touched.add(aid)
        items[aid].clear()
        items[aid].update(command['assignment'])
        ids = payload['submit_actor_ids']
        if command['submit'] and aid not in ids:
            ids.append(aid)
        elif not command['submit'] and aid in ids:
            ids.remove(aid)
        origins.append({'source_mechanism': value.source_mechanism, 'source_port': value.source_port,
            'emitted_period': value.emitted_period, 'input_event_ids': list(value.lineage_event_ids),
            'command_sha256': sha(command), 'command': command})
    directions, authors, staged = _validate_plan(kernel, payload, year)
    actors = _actors(kernel)
    before = {aid: (actors[aid].newest_direction, actors[aid].project_start_year, actors[aid].project_end_year)
              for aid in directions}
    try:
        for aid, d in directions.items():
            actors[aid].newest_direction = d
            actors[aid].project_start_year, actors[aid].project_end_year = staged[aid]
    except BaseException:
        for aid, (d, start, end) in before.items():
            actors[aid].newest_direction, actors[aid].project_start_year, actors[aid].project_end_year = d, start, end
        raise
    return MechanismResult(outputs={'applied': (MechanismValue(payload, actor_ids=tuple(directions)),)},
        events=(MechanismEvent(EFFECT, actor_ids=tuple(directions), payload={
            'year': year, 'plan_sha256': sha(payload), 'submit_actor_ids': [a.id for a in authors],
            'amendments': origins}),))


def _read_plan(kernel, context):
    payload = _one(context, 'plans', PLAN)
    directions, authors, staged = _validate_plan(kernel, payload, context.period)
    for aid, (start, end) in staged.items():
        actor = _actors(kernel)[aid]
        actual = actor.newest_direction
        if (actor.project_start_year, actor.project_end_year) != (start, end) or (
                actual['direction'].to_dict() != directions[aid]['direction'].to_dict()
                or actual['detailed_focus'] != directions[aid]['detailed_focus'] or actual['reason'] != directions[aid]['reason']):
            raise GraphRuntimeError('native plan was not applied through its explicit effect capability')
    return payload, directions, authors


def _paper_bundle(year, kind, papers):
    return {'schema': PAPERS, 'year': year, 'kind': kind, 'papers': deepcopy(papers)}


def _read_papers(kernel, context, kind):
    payload = _one(context, 'papers', PAPERS)
    if (set(payload) != {'schema', 'year', 'kind', 'papers'} or type(payload['year']) is not int
            or payload['year'] != context.period
            or payload['kind'] != kind or not isinstance(payload['papers'], list)):
        raise GraphRuntimeError('native paper batch has wrong shape/year/kind')
    papers, seen = payload['papers'], set()
    archive = kernel._simulation.paper_tracker.papers_by_id
    for paper in papers:
        if not isinstance(paper, dict) or not isinstance(paper.get('id'), str) or paper['id'] in seen:
            raise GraphRuntimeError('native paper batch must reference unique actual paper IDs')
        seen.add(paper['id'])
        actual = archive.get(paper['id'])
        if actual is None or actual.year != context.period:
            raise GraphRuntimeError('native paper batch references absent/stale actual artifacts')
        # Native publication can have updated status after a submission bundle.
        for key, value in actual.to_dict().items():
            if key in {'status', 'review_history'} and kind == 'submission':
                continue
            if paper.get(key, [] if key == 'review_history' else None) != value:
                raise GraphRuntimeError('native paper content differs from actual archive: ' + key)
        if paper.get('type') != kind:
            raise GraphRuntimeError('native paper batch changes its submission identity')
    if kind == 'submission':
        live = {p['id']: p for c in kernel._simulation.conference_system.conferences
                for p in (*c.submitted_papers, *c.decisions['accept'], *c.decisions['reject'])}
        if any(p['id'] not in live for p in papers):
            raise GraphRuntimeError('native funding batch needs real registered submissions')
        return [live[p['id']] for p in papers]
    # Resolve checked IDs back to native archive-backed values. In particular,
    # native review_history aliases are intentional: later review appends must
    # remain visible to the archive and earlier venue records exactly as before.
    return [{**archive[p['id']].to_dict(), 'type': 'resubmission'} for p in papers]


def _stage(kernel, stage, context):
    sim, frame = kernel._simulation, kernel._frame
    year, results = frame['year'], frame['results']
    sim.portable_safe_point()
    extra = {}
    if stage == 'resubmissions':
        papers = sim._run_phase_0_resubmissions(year, results)
        sim.wandb_logger.log_phase(year, 0, results, sim, num_resubmissions=len(papers))
        extra['papers'] = (MechanismValue(_paper_bundle(year, 'resubmission', papers),
            artifact_ids=tuple(p['id'] for p in papers)),)
    elif stage == 'research':
        directions, authors, average = sim._run_phase_1_research_directions(year, results)
        sim.wandb_logger.log_phase(year, 1, results, sim, num_active_authors=len(authors), avg_funding=average)
        extra['plans'] = (MechanismValue(_plan(year, directions, authors, _actors(kernel)), actor_ids=tuple(directions)),)
    elif stage == 'collaboration':
        payload, directions, authors = _read_plan(kernel, context)
        sim._run_phase_1_5_collaboration_formation(year, directions, authors, results)
        extra['planned'] = (MechanismValue(payload, actor_ids=tuple(directions)),)
    elif stage == 'submission':
        _, directions, authors = _read_plan(kernel, context)
        resubmissions = _read_papers(kernel, context, 'resubmission')
        papers = sim._run_phase_2_submit_papers(year, directions, authors, resubmissions, results)
        sim._record_paper_metadata_batch(year)
        sim.wandb_logger.log_phase(year, 2, results, sim)
        extra['submitted'] = (MechanismValue(_paper_bundle(year, 'submission', papers),
            artifact_ids=tuple(p['id'] for p in papers)),)
    elif stage == 'funding':
        sim._run_phase_5_update_funding(year, _read_papers(kernel, context, 'submission'), results)
    from .native_kernel import _hash
    world = kernel.observation()
    return MechanismResult(outputs={'next': (MechanismValue({'year': year}),),
        'world': (MechanismValue(world),), **extra}, events=(MechanismEvent(
            'native.system.phase_executed', payload={'stage': stage, 'observation_sha256': _hash(world),
                'activity_contract': 'v1'}),))


def register_activity_contracts(kernel, registry):
    for stage in ('resubmissions', 'research', 'collaboration', 'submission', 'funding'):
        registry.register(PREFIX + stage + '.v1', 1, lambda context, stage=stage: _stage(kernel, stage, context))
    registry.register(PREFIX + 'plan-effects.v1', 1, lambda context: apply_research_plans(kernel, context))
