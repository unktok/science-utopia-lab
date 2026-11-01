"""Opt-in, causally addressed institutional information in original review inputs.

No original prompt or parser is changed. A SystemSpec must explicitly select
both capabilities, and the host must register this trusted adapter. The receiver
first uses the original context-delivery operation; its typed output authorizes
only those exact delivered messages for the original review stage.
"""
from dataclasses import replace
import json

from .model import ArtifactTypeSpec, ChannelKind, ConnectionSpec, PortSpec
from .native_kernel import CONTEXT_RECEIVER, _clone, _hash, _json
from .runtime import GraphRuntimeError, MechanismEvent, MechanismResult, MechanismValue
from .validation import validate_system_spec

RECEIVER = 'native.world.review-context-delivery.v1'
REVIEW = 'native.phase.review.with-delivered-context.v1'
PROTOCOL = 'native-delivered-review-context.v1'
SCHEMA = 'scienceutopia.delivered-review-context.v1'
PORT = 'institutional-review-context'


def enable_review_context(spec, *, receiver, review='world.review'):
    """Authorize one existing original context receiver as review information.

    Delivery precedes review in the same annual graph. Other receivers' context
    is deliberately NOT included, even if present in an agent's durable memory.
    """
    nodes = {n.mechanism_id: n for n in spec.mechanisms}
    if (receiver not in nodes or review not in nodes
            or nodes[receiver].implementation != CONTEXT_RECEIVER
            or nodes[receiver].outputs
            or nodes[review].implementation != 'native.phase.review.v1'):
        raise GraphRuntimeError('review context requires original receiver and original review stage')
    phases = {s.mechanism_id: s.phase for s in spec.schedules}
    if phases.get(receiver, float('inf')) >= phases.get(review, -1):
        raise GraphRuntimeError('review context must be delivered before review')
    if any(p.port_id == PORT for p in nodes[review].inputs):
        raise GraphRuntimeError('review context input already exists')
    updated = []
    for node in spec.mechanisms:
        if node.mechanism_id == receiver:
            node = replace(node, implementation=RECEIVER,
                outputs=(PortSpec('authorization', ChannelKind.ARTIFACT, PROTOCOL),))
        if node.mechanism_id == review:
            node = replace(node, implementation=REVIEW,
                inputs=(*node.inputs, PortSpec(PORT, ChannelKind.ARTIFACT, PROTOCOL)),
                parameters={**node.parameters, 'review_context_receiver': receiver})
        updated.append(node)
    result = replace(spec, mechanisms=tuple(updated),
        artifact_types=(*spec.artifact_types, ArtifactTypeSpec(PROTOCOL)),
        connections=(*spec.connections, ConnectionSpec(receiver, 'authorization', review, PORT, ChannelKind.ARTIFACT)))
    validate_system_spec(result).require_valid()
    return result


def _records(value, population):
    if not isinstance(value, list):
        raise GraphRuntimeError('review context records must be a list')
    seen = set()
    for record in value:
        if not isinstance(record, dict) or set(record) != {'actor_id', 'message'}:
            raise GraphRuntimeError('invalid review context record')
        aid, message = record['actor_id'], record['message']
        if (not isinstance(aid, str) or aid not in population or not population[aid].can_author
                or not isinstance(message, dict) or set(message) != {
                    'message_id', 'source', 'received_year', 'emitted_year', 'payload', 'input_event_ids'}
                or not isinstance(message['message_id'], str) or len(message['message_id']) != 64
                or not isinstance(message['source'], str) or not message['source']
                or type(message['received_year']) is not int or message['received_year'] < 1
                or type(message['emitted_year']) is not int
                or not 1 <= message['emitted_year'] <= message['received_year']
                or not isinstance(message['payload'], dict)
                or not isinstance(message['input_event_ids'], list) or not message['input_event_ids']
                or any(not isinstance(x, str) or not x for x in message['input_event_ids'])
                or len(set(message['input_event_ids'])) != len(message['input_event_ids'])):
            raise GraphRuntimeError('invalid addressed review context identity/lineage')
        key = aid, message['message_id']
        if key in seen:
            raise GraphRuntimeError('duplicate addressed review context')
        seen.add(key)
        actual = [m for m in getattr(population[aid], 'institutional_context', ())
                  if m.get('message_id') == message['message_id']]
        if actual != [message]:
            raise GraphRuntimeError('review context was not delivered exactly once to this actor')
    return _clone(value)


def register_review_context(kernel, registry):
    """Optional registry extension; registering alone changes no default bytes."""
    def receive(context):
        population = kernel._simulation.ecosystem.agent_population
        state = dict(context.state)
        if state:
            if (set(state) != {'schema', 'last_period', 'records'} or state['schema'] != SCHEMA
                    or type(state['last_period']) is not int or not 0 < state['last_period'] < context.period):
                raise GraphRuntimeError('invalid or repeated review context delivery state')
        prior = _records(state.get('records', []), population)
        if any(r['message']['received_year'] >= context.period for r in prior):
            raise GraphRuntimeError('review context delivery state contains a future/repeated message')
        # Preflight the WHOLE batch before the original delivery mutates actors.
        planned, seen = [], {(r['actor_id'], r['message']['message_id']) for r in prior}
        for port, values in context.inputs.items():
            for index, value in enumerate(values):
                if (not value.actor_ids or len(set(value.actor_ids)) != len(value.actor_ids)
                        or not value.lineage_event_ids or not 1 <= value.emitted_period <= context.period):
                    raise GraphRuntimeError('review context needs addressed causal delivery')
                message = {'message_id': _hash({'source': value.source_mechanism, 'port': port,
                    'index': index, 'year': context.period, 'payload': value.payload, 'lineage': value.lineage_event_ids}),
                    'source': value.source_mechanism, 'received_year': context.period,
                    'emitted_year': value.emitted_period, 'payload': dict(value.payload),
                    'input_event_ids': list(value.lineage_event_ids)}
                _clone(message)  # reject non-finite / non-JSON before mutation
                for aid in value.actor_ids:
                    if aid not in population or not population[aid].can_author:
                        raise GraphRuntimeError('review context recipient must be an actual author')
                    key = aid, message['message_id']
                    if key in seen or any(m.get('message_id') == key[1]
                                          for m in getattr(population[aid], 'institutional_context', ())):
                        raise GraphRuntimeError('duplicate review context delivery')
                    seen.add(key)
                    planned.append({'actor_id': aid, 'message': message})
        delivered = kernel._receive_context(context)
        actual = [{'actor_id': event.actor_ids[0], 'message': dict(event.payload['message'])}
                  for event in delivered.events]
        if actual != planned:
            raise GraphRuntimeError('original review context delivery disagrees with preflight')
        records = _records([*prior, *actual], population)
        payload = {'schema': SCHEMA, 'receiver': context.mechanism.mechanism_id,
                   'through_year': context.period, 'records': records}
        lineage = tuple(dict.fromkeys(e for r in records for e in r['message']['input_event_ids']))
        return MechanismResult(outputs={'authorization': (MechanismValue(payload, lineage_event_ids=lineage),)},
            events=(*delivered.events, MechanismEvent('native.system.review_context_authorized',
                payload={'records_sha256': _hash(records), 'records': len(records)})),
            next_state={'schema': SCHEMA, 'last_period': context.period, 'records': records})

    def review(context):
        population = kernel._simulation.ecosystem.agent_population
        receiver = context.mechanism.parameters.get('review_context_receiver')
        source = next((n for n in kernel.spec.mechanisms if n.mechanism_id == receiver), None)
        values = context.inputs.get(PORT, ())
        if (source is None or source.implementation != RECEIVER or len(values) != 1
                or values[0].source_mechanism != receiver or values[0].source_port != 'authorization'
                or values[0].emitted_period != context.period or not values[0].lineage_event_ids):
            raise GraphRuntimeError('review context authorization has the wrong source or period')
        payload = dict(values[0].payload)
        if (set(payload) != {'schema', 'receiver', 'through_year', 'records'} or payload['schema'] != SCHEMA
                or payload['receiver'] != receiver or payload['through_year'] != context.period):
            raise GraphRuntimeError('invalid review context authorization payload')
        records = _records(payload['records'], population)
        if any(r['message']['received_year'] > context.period
               or not set(r['message']['input_event_ids']) <= set(values[0].lineage_event_ids) for r in records):
            raise GraphRuntimeError('review context has future or missing source lineage')
        state = dict(context.state)
        if state and (set(state) != {'schema', 'last_period', 'uses'} or state['schema'] != SCHEMA
                      or type(state['last_period']) is not int or state['last_period'] != context.period-1
                      or not isinstance(state['uses'], list)):
            raise GraphRuntimeError('invalid or repeated review context consumption state')
        by_actor, originals, uses = {}, [], []
        for record in records:
            by_actor.setdefault(record['actor_id'], []).append(record['message'])
        try:
            for aid, messages in by_actor.items():
                agent = population[aid]
                had_instance = 'get_review_prompt' in vars(agent)
                old_instance = vars(agent).get('get_review_prompt')
                original = agent.get_review_prompt
                originals.append((agent, had_instance, old_instance))
                suffix = '\n## Information received from scientific institutions\n' + '\n'.join(
                    json.dumps(m, ensure_ascii=False, sort_keys=True, allow_nan=False) for m in messages) + '\n'
                def prompt(*args, _original=original, _suffix=suffix, _aid=aid, _messages=messages, **kwargs):
                    text, response_format = _original(*args, **kwargs)
                    text += _suffix
                    uses.append({'actor_id': _aid, 'paper_sha256': _hash(_json(args[0] if args else kwargs['paper'])),
                        'prompt_sha256': _hash(text), 'message_ids': [m['message_id'] for m in _messages]})
                    return text, response_format
                agent.get_review_prompt = prompt
            result = kernel._stage('review', context)  # original model calls, int parser and state transitions
        finally:
            for agent, had_instance, old_instance in originals:
                if had_instance:
                    agent.get_review_prompt = old_instance
                else:
                    vars(agent).pop('get_review_prompt', None)
        uses.sort(key=lambda item: (item['actor_id'], item['paper_sha256'], item['prompt_sha256']))
        return replace(result, events=(*result.events, MechanismEvent('native.system.review_context_used',
            payload={'authorization_sha256': _hash(payload), 'uses': uses})),
            next_state={'schema': SCHEMA, 'last_period': context.period, 'uses': [*state.get('uses', []), *uses]})

    registry.register(RECEIVER, 1, receive)
    registry.register(REVIEW, 1, review)
