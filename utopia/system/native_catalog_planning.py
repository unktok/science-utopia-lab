"""Catalog-conserving project actuation and explicit developer controls.

This capability validates a submitted choice; it supplies no optimizer or
allocation rule. The optional control below is a separately labelled hand rule.
Existing unrestricted project and fixed-production scopes retain their meaning.
"""
from copy import deepcopy
from dataclasses import replace

from .code_mechanisms import CODE_SCHEMA, sha
from .model import ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from .runtime import GraphRuntimeError, MechanismEvent

ACTION = 'native.catalog-project.v1'
EVENT = 'native.domain.catalog_project_validated'
PROTOCOL = 'native-developer-catalog-agenda-v1'
COMMANDS = 'native-developer-catalog-commands-v1'


def catalog_contract():
    """Exact public native catalog, not an outcome-dependent new task set."""
    from utopia.agents.research_direction import AVAILABLE_DIRECTIONS
    rows = [d.to_dict() for d in AVAILABLE_DIRECTIONS]
    if len({d['topic'] for d in rows}) != len(rows):
        raise ValueError('native direction catalog contains duplicate topics')
    return {'schema': 'scienceutopia.native-direction-catalog.v1',
            'directions': deepcopy(rows), 'directions_sha256': sha(rows)}


def validate_catalog_assignment(assignment, actor, *, year, catalog):
    """Pure identity, eligibility, canonical content and duration validation.

    Choose any displayed expertise topic. Neither shortest duration nor merit
    is enforced here. An ongoing project cannot be relabelled as a new one.
    """
    from .native_activity_contracts import PLAN
    required = {'actor_id', 'direction', 'detailed_focus', 'reason',
                'project_start_year', 'project_end_year'}
    if (not isinstance(assignment, dict) or set(assignment) != required
            or type(year) is not int or year < 1
            or assignment['actor_id'] != actor['id']
            or actor['can_author'] is not True or actor['is_active'] is not True
            or type(actor['project_end_year']) is not int
            or actor['project_end_year'] >= year):
        raise GraphRuntimeError('catalog project requires an actual active idle author and exact assignment')
    direction = assignment['direction']
    rows = catalog['directions']
    if (catalog['schema'] != 'scienceutopia.native-direction-catalog.v1'
            or sha(rows) != catalog['directions_sha256']
            or len({d['topic'] for d in rows}) != len(rows)):
        raise GraphRuntimeError('exact native catalog identity required')
    actual = {d['topic']: d for d in rows}
    if (not isinstance(direction, dict) or not isinstance(direction.get('topic'), str)
            or direction.get('topic') not in actor['expertise']
            or direction != actual.get(direction.get('topic'))
            or type(direction.get('years')) is not int or direction['years'] < 1
            or assignment['project_start_year'] != year
            or type(assignment['project_start_year']) is not int
            or type(assignment['project_end_year']) is not int
            or assignment['project_end_year'] != year + direction['years'] - 1
            or any(not isinstance(assignment[k], str) for k in ('detailed_focus', 'reason'))):
        raise GraphRuntimeError('catalog project must preserve displayed topic content and native duration')
    return {'schema': PLAN, 'year': year, 'assignments': [deepcopy(assignment)], 'submit_actor_ids': []}


def apply_catalog_project(tx, payload, principal):
    """Validate real state, then stage the existing atomic native project effect."""
    from .native_open_domain import _native_project
    simulation = tx.kernel._simulation
    if getattr(simulation, 'is_exploration_experiment', None) is not False:
        raise GraphRuntimeError('catalog project v1 requires explicit native legacy expertise candidates')
    assignment = payload['assignment']
    if not isinstance(assignment, dict) or not isinstance(assignment.get('actor_id'), str):
        raise GraphRuntimeError('catalog project requires an explicit native actor')
    actor = tx.require_native_author(assignment['actor_id'])
    if getattr(actor, '_filtered_candidates', None):
        raise GraphRuntimeError('catalog project v1 cannot substitute for filtered native candidates')
    expertise = getattr(actor, 'expertise', None)
    if not isinstance(expertise, list) or not expertise or any(not hasattr(d, 'to_dict') for d in expertise):
        raise GraphRuntimeError('actual native expertise catalog required')
    catalog = catalog_contract()
    snapshot = {'id': actor.id, 'can_author': actor.can_author, 'is_active': actor.is_active,
                'project_end_year': actor.project_end_year, 'expertise': [d.topic for d in expertise]}
    validate_catalog_assignment(assignment, snapshot, year=tx.context.period, catalog=catalog)
    if not any(d.to_dict() == assignment['direction'] for d in expertise):
        raise GraphRuntimeError('selected native direction differs from actual displayed expertise content')
    _native_project(tx, payload, principal)
    tx.events.append(MechanismEvent(EVENT, actor_ids=(actor.id,), payload={
        'origin_actor_id': principal, 'command_key': tx.command_key,
        'catalog_sha256': catalog['directions_sha256'], 'eligible_actor_before': snapshot,
        'assignment': deepcopy(assignment), 'shortest_or_merit_rule_enforced': False}))


SOURCE = '''def step(context):
    world = context['inputs']['world'][0]['payload']
    year = context['period']
    catalog = {d['topic']: d for d in context['parameters']['catalog']['directions']}
    assignments = []
    commands = []
    mode = context['parameters']['actuation']
    for actor in sorted(world['ecosystem']['agents'], key=lambda a: a['id']):
        if not actor['can_author'] or not actor['is_active'] or actor['project_end_year'] >= year:
            continue
        candidates = [catalog[t] for t in actor['expertise']]
        direction = min(candidates, key=lambda d: (d['years'], d['topic']))
        assignment = {'actor_id': actor['id'], 'direction': direction,
            'detailed_focus': 'Study ' + direction['topic'] + ' within its original catalog duration.',
            'reason': 'Developer catalog agenda: shortest displayed duration, then lexical topic.',
            'project_start_year': year, 'project_end_year': year + direction['years'] - 1}
        assignments.append(assignment)
        if mode == 'cut':
            continue
        if mode == 'information':
            action = 'native.context'
            payload = {'actor_ids': [actor['id']], 'artifact_ids': [], 'content': {
                'schema': 'native-developer-catalog-agenda-v1', 'assignment': assignment,
                'instruction': 'This is an advisory agenda. Consider this permitted topic and its original duration. '
                    'Choose normally; it is not a simulator command or a change to scientific production laws.'}}
        elif mode == 'project':
            action = 'native.catalog-project.v1'
            payload = {'assignment': assignment}
        else:
            raise ValueError('unknown declared developer actuation')
        commands.append({'payload': {'schema': 'native-domain-command-v1',
            'command_id': 'catalog-agenda-' + str(year) + '-' + actor['id'],
            'actor_id': '$mechanism', 'action': action, 'payload': payload}})
    return {'outputs': {'agenda': [{'payload': {'schema': 'native-developer-catalog-agenda-v1',
        'year': year, 'assignments': assignments}}], 'commands': commands},
        'state': {'year': year, 'eligible_authors': len(assignments)}}
'''


def catalog_agenda_control(anchor, image_id, *, actuation):
    """Three same-authority developer diagnostics; not generated institutions."""
    from .native_kernel import WORLD_ARTIFACT
    from .native_open_domain import add_domain_action_receiver
    from .validation import validate_system_spec
    if actuation not in ('cut', 'information', 'project'):
        raise ValueError('explicit cut/information/project actuation required')
    producer, receiver = 'developer-catalog-agenda', 'developer-catalog-effects'
    if any(n.mechanism_id in (producer, receiver) for n in anchor.mechanisms):
        raise ValueError('fresh catalog control identities required')
    node = MechanismSpec(producer, MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('world', ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
        outputs=(PortSpec('agenda', ChannelKind.ARTIFACT, PROTOCOL),
                 PortSpec('commands', ChannelKind.ARTIFACT, COMMANDS, required=False)),
        parameters={'runtime_image_id': image_id, 'actuation': actuation, 'catalog': catalog_contract(),
            'code_artifact': {'schema': CODE_SCHEMA, 'label': 'Developer catalog actuation diagnostic, not invention',
                'source': SOURCE, 'inputs': {'world': {'type': 'object'}},
                'outputs': {'agenda': {'type': 'object'}, 'commands': {'type': 'object'}},
                'state_schema': {'type': 'object'}}})
    result = replace(anchor, mechanisms=(*anchor.mechanisms, node),
        artifact_types=(*anchor.artifact_types, ArtifactTypeSpec(PROTOCOL), ArtifactTypeSpec(COMMANDS)),
        schedules=(*anchor.schedules, ScheduleSpec(producer, 1)),
        connections=(*anchor.connections, ConnectionSpec('world.open', 'world', producer, 'world', ChannelKind.ARTIFACT)))
    result = add_domain_action_receiver(result, source=producer, source_port='commands',
        receiver=receiver, phase=2, capabilities={'bootstrap': ['native.context', ACTION], 'roles': {}})
    validate_system_spec(result).require_valid()
    return result
