"""Developer controls using original native choice, not a new assignment API."""
from copy import deepcopy
from dataclasses import replace

from . import (ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily,
               MechanismSpec, PortSpec, ScheduleSpec, validate_system_spec)
from .code_mechanisms import CODE_SCHEMA
from .native_catalog_planning import SOURCE as CATALOG_SOURCE, catalog_contract
from .native_kernel import WORLD_ARTIFACT, add_context_receiver

PROTOCOL = 'native-developer-legacy-choice-advice-v1'
PRODUCER = 'developer-legacy-choice-office'
RECEIVER = 'developer-legacy-choice-receiver'
SOURCE = '''def step(context):
    world = context['inputs']['world'][0]['payload']
    year = context['period']
    catalog = {d['topic']: d for d in context['parameters']['catalog']['directions']}
    messages = []
    for actor in sorted(world['ecosystem']['agents'], key=lambda a: a['id']):
        if not actor['can_author'] or not actor['is_active'] or actor['project_end_year'] >= year:
            continue
        topics = set(actor['expertise'])
        for topic in actor['expertise']:
            topics.update(catalog[topic]['related_topics'])
        eligible = [catalog[t] for t in sorted(topics) if t in catalog]
        recommended = min(eligible, key=lambda d: (d['years'], d['topic']))
        messages.append({'actor_ids': [actor['id']], 'payload': {
            'schema': 'native-developer-legacy-choice-advice-v1', 'effective_year': year,
            'eligible_topics': [{'topic': d['topic'], 'years': d['years']} for d in eligible],
            'recommended_topic': recommended['topic'],
            'recommended_original_duration': recommended['years'],
            'instruction': 'For your next native research-direction selection in the effective year, '
                'consider choosing the recommended shortest original-duration topic; lexical topic '
                'breaks ties. Core and related expertise are both original permitted choices. '
                'Use the normal research-direction response format. This is advice, not a host '
                'assignment, a change to project duration, an acceptance guarantee or scientific truth.'}})
    return {'outputs': {'messages': messages},
            'state': {'year': year, 'recommendations': len(messages)}}
'''


def controls(post_funding_anchor):
    """Three same-world hand policies; neither execute nor select a policy.

    The caller supplies the already declared post-funding anchor. This builder
    does not reorder funding/costs, change the world, inspect outcomes or add an
    optimizer menu. A later free author remains able to edit arbitrary systems.
    """
    validate_system_spec(post_funding_anchor).require_valid()
    phases = {s.mechanism_id: s.phase for s in post_funding_anchor.schedules}
    if not (phases['world.funding'] < phases['developer-liquidity-director']
            < phases['developer-liquidity-effects'] < phases['world.costs']
            < phases['world.communication']):
        raise ValueError('explicit post-funding liquidity/cost anchor required')
    director = next(n for n in post_funding_anchor.mechanisms
                    if n.mechanism_id == 'developer-catalog-agenda')
    if (director.implementation != 'code.python.v1'
            or director.parameters['actuation'] != 'project'
            or director.parameters['code_artifact']['source'] != CATALOG_SOURCE
            or director.parameters['catalog'] != catalog_contract()):
        raise ValueError('literal original core-catalog assignment control required')
    params = deepcopy(director.parameters); params['actuation'] = 'cut'
    unforced = replace(post_funding_anchor, mechanisms=tuple(
        replace(n, parameters=params) if n.mechanism_id == director.mechanism_id else n
        for n in post_funding_anchor.mechanisms))
    if any(n.mechanism_id in (PRODUCER, RECEIVER) for n in unforced.mechanisms):
        raise ValueError('fresh advice mechanism identities required')
    emit, deliver = phases['world.open'] + 1, phases['world.research'] - 1
    if emit >= deliver:
        raise ValueError('advice must be emitted and delivered before native research')
    node = MechanismSpec(PRODUCER, MechanismFamily.CUSTOM, 'code.python.v1',
        inputs=(PortSpec('world', ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
        outputs=(PortSpec('messages', ChannelKind.ARTIFACT, PROTOCOL, required=False),),
        parameters={'runtime_image_id': params['runtime_image_id'],
            'catalog': deepcopy(params['catalog']), 'code_artifact': {
                'schema': CODE_SCHEMA, 'label': 'Developer native-choice advice control, not invention',
                'source': SOURCE, 'inputs': {'world': {'type': 'object'}},
                'outputs': {'messages': {'type': 'object'}}, 'state_schema': {'type': 'object'}}})
    advice = replace(unforced,
        mechanisms=(*unforced.mechanisms, node),
        artifact_types=(*unforced.artifact_types, ArtifactTypeSpec(PROTOCOL)),
        schedules=(*unforced.schedules, ScheduleSpec(PRODUCER, emit)),
        connections=(*unforced.connections, ConnectionSpec('world.open', 'world',
            PRODUCER, 'world', ChannelKind.ARTIFACT)))
    advice = add_context_receiver(advice, source=PRODUCER, source_port='messages',
                                 receiver=RECEIVER, phase=deliver)
    result = {'core-assignment': post_funding_anchor,
              'native-choice': unforced, 'native-choice-advice': advice}
    for system in result.values():
        validate_system_spec(system).require_valid()
    return result
