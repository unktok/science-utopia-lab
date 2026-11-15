"""Extensible, data-defined actors/artifacts with atomic original-world effects.

Institution algorithms live in sandboxed source/LLM nodes. These registered
typed actions are domain capabilities, not a catalogue of institution policies.
"""
from copy import deepcopy
from dataclasses import replace
from types import MethodType, SimpleNamespace

from jsonschema import Draft202012Validator

from .code_mechanisms import _schema, canonical, sha
from .model import ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from .runtime import DeliveredValue, GraphRuntimeError, MechanismEvent, MechanismResult, MechanismValue, _validate_result

STATE_SCHEMA = 'scienceutopia.native-open-domain-state.v1'
COMMAND_SCHEMA = 'native-domain-command-v1'
STATE_ARTIFACT = 'native-open-domain-state-v1'
IMPLEMENTATION = 'native.domain.commands.v1'
OBSERVER = 'native.domain.observe.v1'
EVENT = 'native.domain.command_committed'
BOOTSTRAP = '$mechanism'
_STATE_KEYS = {'schema', 'actors', 'artifacts', 'values', 'actor_types', 'artifact_types', 'receipts', 'last_receipt_key'}


def empty_domain():
    return {'schema': STATE_SCHEMA, 'actors': {}, 'artifacts': {}, 'values': {},
        'actor_types': {}, 'artifact_types': {}, 'receipts': {}, 'last_receipt_key': None}


def _content_hash(state):
    return sha({k: v for k, v in state.items() if k not in {'receipts', 'last_receipt_key'}})


def _identity(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 200 or value == BOOTSTRAP:
        raise GraphRuntimeError('native domain identity must be a nonempty bounded explicit string')
    return value


def _strings(values):
    if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values) or len(values) != len(set(values)):
        raise GraphRuntimeError('native domain references/roles must be unique strings')
    return values


def _validate(schema, value):
    _schema(schema)
    try:
        canonical(value)
        Draft202012Validator(schema).validate(value)
    except Exception as error:
        raise GraphRuntimeError('native domain payload/schema differs: ' + str(error)[:500]) from error


def validate_domain_state(state, *, events=None):
    """Check snapshots independently of a live Simulation/host class registry."""
    if state == {}:
        if events is not None and any(e.event_type == EVENT for e in events):
            raise GraphRuntimeError('committed domain history is missing its persistent state')
        return
    if not isinstance(state, dict) or set(state) != _STATE_KEYS or state['schema'] != STATE_SCHEMA:
        raise GraphRuntimeError('invalid native open-domain checkpoint schema')
    canonical(state)
    if any(not isinstance(state[k], dict) for k in _STATE_KEYS - {'schema', 'last_receipt_key'}):
        raise GraphRuntimeError('native open-domain stores must be explicit dictionaries')
    for type_id, declaration in state['actor_types'].items():
        _identity(type_id)
        if not isinstance(declaration, dict) or set(declaration) != {'roles', 'state_schema'}:
            raise GraphRuntimeError('invalid persistent actor type declaration')
        _strings(declaration['roles'])
        _schema(declaration['state_schema'])
    for type_id, schema in state['artifact_types'].items():
        _identity(type_id)
        _schema(schema)
    for aid, record in state['actors'].items():
        _identity(aid)
        if (set(record) != {'id', 'type', 'roles', 'state', 'revision', 'created_year', 'updated_year'}
                or record['id'] != aid or record['type'] not in state['actor_types']
                or type(record['revision']) is not int or record['revision'] < 0
                or any(type(record[k]) is not int or record[k] < 1 for k in ('created_year', 'updated_year'))
                or record['updated_year'] < record['created_year']):
            raise GraphRuntimeError('invalid persistent custom actor identity/type/revision')
        declaration = state['actor_types'][record['type']]
        if set(declaration) != {'roles', 'state_schema'} or not set(_strings(record['roles'])) <= set(_strings(declaration['roles'])):
            raise GraphRuntimeError('custom actor role declaration differs')
        _validate(declaration['state_schema'], record['state'])
    for aid, record in state['artifacts'].items():
        _identity(aid)
        if (set(record) != {'id', 'type', 'owner_actor', 'content', 'actor_ids', 'artifact_ids',
                'native_paper_ids', 'revision', 'created_year', 'updated_year'}
                or record['id'] != aid or record['type'] not in state['artifact_types']
                or type(record['revision']) is not int or record['revision'] < 0
                or any(type(record[k]) is not int or record[k] < 1 for k in ('created_year', 'updated_year'))
                or record['updated_year'] < record['created_year']):
            raise GraphRuntimeError('invalid persistent scientific artifact identity/type/revision')
        for key in ('actor_ids', 'artifact_ids', 'native_paper_ids'):
            _strings(record[key])
        _validate(state['artifact_types'][record['type']], record['content'])
    for key, value in state['values'].items():
        if (set(value) != {'owner_actor', 'key', 'value', 'revision'} or value['owner_actor'] not in state['actors']
                or key != sha([value['owner_actor'], value['key']]) or type(value['revision']) is not int
                or value['revision'] < 0):
            raise GraphRuntimeError('invalid persistent custom state ownership/revision')
    receipts = sorted(state['receipts'].items(), key=lambda kv: kv[1]['index'])
    previous = None
    for index, (key, receipt) in enumerate(receipts):
        if (set(receipt) != {'index', 'command_key', 'origin', 'command_sha256', 'command', 'received_year',
                'input_event_ids', 'previous_receipt_sha256', 'domain_content_sha256'}
                or receipt['index'] != index or receipt['command_key'] != key or key != sha(receipt['origin'])
                or receipt['command_sha256'] != sha(receipt['command'])
                or receipt['previous_receipt_sha256'] != previous):
            raise GraphRuntimeError('native domain command receipt chain differs')
        previous = sha(receipt)
    if (not receipts or state['last_receipt_key'] != receipts[-1][0]
            or receipts[-1][1]['domain_content_sha256'] != _content_hash(state)):
        raise GraphRuntimeError('native domain content differs from final committed receipt')
    if events is not None:
        history = [e for e in events if e.event_type == EVENT]
        committed = {e.payload['command_key']: dict(e.payload) for e in history}
        if len(committed) != len(history) or committed != state['receipts']:
            raise GraphRuntimeError('native domain state differs from committed source-event history')


class NativeActionRegistry:
    """Trusted typed capability plugins; never registers generated host source.

    A prepare handler receives (transaction, payload, principal). It may stage
    record/effect changes and events but must not mutate external host objects.
    Extra handlers are developer plugins bound by the experiment source pin.
    """
    def __init__(self):
        self.actions = {}

    def register(self, name, payload_schema, prepare):
        _identity(name)
        _schema(payload_schema)
        if name in self.actions or not callable(prepare):
            raise GraphRuntimeError('native action already registered or handler is not callable')
        self.actions[name] = (deepcopy(payload_schema), prepare)


def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def default_actions():
    from .native_catalog_planning import ACTION as CATALOG_PROJECT, apply_catalog_project
    from .native_legacy_topic_planning import ACTION as LEGACY_TOPIC_PROJECT, apply_legacy_topic_project
    registry = NativeActionRegistry()
    string, obj, refs = {'type': 'string'}, {'type': 'object'}, {'type': 'array', 'items': {'type': 'string'}}
    revision = {'type': 'integer', 'minimum': 0}
    actions = {
        'actor.create': (_object({'id': string, 'type': string, 'roles': refs, 'state': obj}), _create_actor),
        'actor.update': (_object({'id': string, 'expected_revision': revision, 'roles': refs, 'state': obj}), _update_actor),
        'artifact.create': (_object({'id': string, 'type': string, 'owner_actor': string, 'content': obj,
            'actor_ids': refs, 'artifact_ids': refs, 'native_paper_ids': refs}), _create_artifact),
        'artifact.update': (_object({'id': string, 'expected_revision': revision, 'content': obj,
            'actor_ids': refs, 'artifact_ids': refs, 'native_paper_ids': refs}), _update_artifact),
        'state.put': (_object({'key': string, 'value': {}, 'expected_revision': {'type': ['integer', 'null'], 'minimum': 0}}), _put_state),
        'native.context': (_object({'actor_ids': refs, 'content': obj, 'artifact_ids': refs}), _native_context),
        'native.project': (_object({'assignment': obj}), _native_project),
        CATALOG_PROJECT: (_object({'assignment': obj}), apply_catalog_project),
        LEGACY_TOPIC_PROJECT: (_object({'assignment': obj}), apply_legacy_topic_project),
        'native.transfer': (_object({'from_actor': string, 'to_actor': string, 'amount': {'type': 'number'}}), _native_transfer),
    }
    for name, (schema, handler) in actions.items():
        registry.register(name, schema, handler)
    return registry


class DomainTransaction:
    """Staged data/effects, providing an extensible atomic command preparation API."""
    def __init__(self, kernel, context):
        self.kernel, self.context = kernel, context
        self.state = deepcopy(kernel.open_domain_state) if kernel.open_domain_state else empty_domain()
        self.native = kernel._simulation.ecosystem.agent_population
        self.context_updates, self.project_updates, self.transfers, self.events = {}, {}, [], []
        self.command_key = None
        self.value = None

    def require_native_author(self, aid):
        if aid not in self.native or not getattr(self.native[aid], 'can_author', False):
            raise GraphRuntimeError('native action requires an existing real author-capable actor')
        return self.native[aid]

    def deliver_context(self, actor_ids, content, *, principal, artifact_ids=()):
        """Plugin API: stage a real native researcher-input effect, not a log."""
        _native_context(self, {'actor_ids': list(actor_ids), 'content': content,
            'artifact_ids': list(artifact_ids)}, principal)

    def set_project(self, assignment, *, principal):
        """Plugin API: stage an actual original-world project assignment."""
        _native_project(self, {'assignment': assignment}, principal)

    def transfer(self, from_actor, to_actor, amount, *, principal):
        """Plugin API: stage the existing conserving native accounting bridge."""
        _native_transfer(self, {'from_actor': from_actor, 'to_actor': to_actor, 'amount': amount}, principal)

    def put_state(self, key, value, *, principal, expected_revision=None):
        """Plugin API: arbitrary persistent JSON state owned by a custom actor."""
        _put_state(self, {'key': key, 'value': value, 'expected_revision': expected_revision}, principal)

    def actor_exists(self, aid):
        return aid in self.state['actors'] or aid in self.native

    def require_artifacts(self, ids):
        known = set(self.state['artifacts']) | set(self.kernel._simulation.paper_tracker.papers_by_id)
        for node in (self.kernel.graph_checkpoint or {}).get('mechanism_states', {}).values():
            known.update(node.get('declared_artifacts', {}))
        known.update(self.kernel._frame.get('artifact_owners', {}))
        if not set(_strings(ids)) <= known:
            raise GraphRuntimeError('custom artifact references absent real/domain artifacts')

    def validate_links(self):
        papers = self.kernel._simulation.paper_tracker.papers_by_id
        for record in self.state['artifacts'].values():
            if not self.actor_exists(record['owner_actor']) or any(not self.actor_exists(a) for a in record['actor_ids']):
                raise GraphRuntimeError('scientific artifact refers to absent native/custom actors')
            self.require_artifacts(record['artifact_ids'])
            if not set(record['native_paper_ids']) <= set(papers):
                raise GraphRuntimeError('scientific artifact refers to absent actual native papers')

    def authorize(self, principal, action):
        capabilities = self.context.mechanism.parameters.get('capabilities', {})
        if set(capabilities) != {'bootstrap', 'roles'} or not isinstance(capabilities['roles'], dict):
            raise GraphRuntimeError('explicit bootstrap/role action capabilities required')
        allowed = _strings(capabilities['bootstrap']) if principal == BOOTSTRAP else []
        if principal != BOOTSTRAP:
            if principal not in self.state['actors']:
                raise GraphRuntimeError('command principal must be an existing persistent custom actor')
            for role in self.state['actors'][principal]['roles']:
                allowed += _strings(capabilities['roles'].get(role, []))
        if action not in allowed:
            raise GraphRuntimeError('actor/source has not been granted this action capability')

    def _transfer_context(self):
        return replace(self.context, inputs={'transfers': tuple(self.transfers)}, state={})

    def preflight_transfers(self):
        if not self.transfers:
            return
        from utopia.agents.base_agent import SimulationAgent
        from .native_resource_transfers import apply_native_resource_transfers
        simulation = self.kernel._simulation
        ledger = deepcopy(getattr(simulation, 'resource_ledger', None))
        actors = {}
        for aid, actor in self.native.items():
            if not getattr(actor, 'can_author', False):
                continue
            shadow = SimpleNamespace(id=aid, resources=actor.resources, is_active=actor.is_active,
                can_author=True, resource_ledger=ledger, get_type=lambda actor=actor: actor.get_type())
            shadow.update_resources = MethodType(SimulationAgent.update_resources, shadow)
            actors[aid] = shadow
        shadow_kernel = SimpleNamespace(_simulation=SimpleNamespace(
            ecosystem=SimpleNamespace(agent_population=actors), resource_ledger=ledger),
            _frame=deepcopy({'native_resource_transactions': self.kernel._frame.get('native_resource_transactions', {})}),
            events=self.kernel.events)
        apply_native_resource_transfers(shadow_kernel, self._transfer_context())

    def commit(self):
        self.validate_links()
        self.preflight_transfers()
        simulation = self.kernel._simulation
        ledger = getattr(simulation, 'resource_ledger', None)
        ledger_before = deepcopy(ledger.__dict__) if ledger is not None else None
        transfer_before = deepcopy(self.kernel._frame.get('native_resource_transactions'))
        touched = set(self.context_updates) | set(self.project_updates)
        touched.update(aid for value in self.transfers for aid in (value.payload['from_actor'], value.payload['to_actor']))
        fields = ('resources', 'is_active', 'institutional_context', 'newest_direction', 'project_start_year', 'project_end_year')
        before = {aid: {key: (hasattr(self.native[aid], key), getattr(self.native[aid], key, None)) for key in fields} for aid in touched}
        resource_events = ()
        try:
            if self.transfers:
                from .native_resource_transfers import apply_native_resource_transfers
                resource_events = apply_native_resource_transfers(self.kernel, self._transfer_context()).events
            for aid, value in self.context_updates.items():
                self.native[aid].institutional_context = value
            for aid, value in self.project_updates.items():
                self.native[aid].newest_direction = value['direction']
                self.native[aid].project_start_year = value['start']
                self.native[aid].project_end_year = value['end']
        except BaseException:
            for aid, attributes in before.items():
                for key, (existed, value) in attributes.items():
                    if existed:
                        setattr(self.native[aid], key, value)
                    elif hasattr(self.native[aid], key):
                        delattr(self.native[aid], key)
            if ledger is not None:
                ledger.__dict__.clear()
                ledger.__dict__.update(ledger_before)
            if transfer_before is None:
                self.kernel._frame.pop('native_resource_transactions', None)
            else:
                self.kernel._frame['native_resource_transactions'] = transfer_before
            raise
        self.kernel.open_domain_state = self.state
        return tuple(resource_events)


def _declare_type(tx, category, type_id):
    if category == 'actor':
        types = {t.agent_type_id: t for t in tx.kernel.spec.agent_types}
        if type_id not in types:
            raise GraphRuntimeError('custom actor type must be explicitly data-declared in SystemSpec')
        declaration = {'roles': list(types[type_id].roles), 'state_schema':
            tx.context.mechanism.parameters.get('actor_schemas', {}).get(type_id, {'type': 'object'})}
        _schema(declaration['state_schema'])
    else:
        if type_id not in {t.artifact_type_id for t in tx.kernel.spec.artifact_types}:
            raise GraphRuntimeError('custom scientific artifact type must be explicitly data-declared')
        declaration = tx.context.mechanism.parameters.get('artifact_schemas', {}).get(type_id, {'type': 'object'})
        _schema(declaration)
    store = tx.state[category + '_types']
    if type_id in store and store[type_id] != declaration:
        raise GraphRuntimeError('persistent type declaration changed; explicitly version the type')
    store[type_id] = deepcopy(declaration)


def _create_actor(tx, p, principal):
    aid = _identity(p['id'])
    if tx.actor_exists(aid):
        raise GraphRuntimeError('new actor identity collides with an actual native/custom actor')
    _declare_type(tx, 'actor', p['type'])
    declaration = tx.state['actor_types'][p['type']]
    if not set(_strings(p['roles'])) <= set(declaration['roles']):
        raise GraphRuntimeError('assigned actor roles were not data-declared')
    _validate(declaration['state_schema'], p['state'])
    tx.state['actors'][aid] = {**deepcopy(p), 'revision': 0,
        'created_year': tx.context.period, 'updated_year': tx.context.period}
    tx.events.append(MechanismEvent('agent.registered', actor_ids=(aid,), payload={
        'agent_type': p['type'], 'roles': p['roles'], 'display_name': aid, 'custom_domain_actor': True}))


def _update_actor(tx, p, principal):
    old = tx.state['actors'].get(p['id'])
    if old is None or p['expected_revision'] != old['revision']:
        raise GraphRuntimeError('custom actor expected revision/identity differs')
    declaration = tx.state['actor_types'][old['type']]
    if not set(_strings(p['roles'])) <= set(declaration['roles']):
        raise GraphRuntimeError('assigned actor roles were not data-declared')
    _validate(declaration['state_schema'], p['state'])
    tx.state['actors'][p['id']] = {**old, 'roles': deepcopy(p['roles']), 'state': deepcopy(p['state']),
        'revision': old['revision'] + 1, 'updated_year': tx.context.period}


def _create_artifact(tx, p, principal):
    aid = _identity(p['id'])
    known = set(tx.state['artifacts']) | set(tx.kernel._simulation.paper_tracker.papers_by_id)
    for node in (tx.kernel.graph_checkpoint or {}).get('mechanism_states', {}).values():
        known.update(node.get('declared_artifacts', {}))
    known.update(tx.kernel._frame.get('artifact_owners', {}))
    if aid in known:
        raise GraphRuntimeError('new scientific artifact collides with another actual artifact')
    _declare_type(tx, 'artifact', p['type'])
    _validate(tx.state['artifact_types'][p['type']], p['content'])
    tx.state['artifacts'][aid] = {**deepcopy(p), 'revision': 0,
        'created_year': tx.context.period, 'updated_year': tx.context.period}
    tx.events.append(MechanismEvent('artifact.created', actor_ids=(p['owner_actor'],), artifact_ids=(aid,),
        payload={'artifact_type': p['type'], 'content': deepcopy(p['content'])}))


def _update_artifact(tx, p, principal):
    old = tx.state['artifacts'].get(p['id'])
    if old is None or p['expected_revision'] != old['revision']:
        raise GraphRuntimeError('scientific artifact expected revision/identity differs')
    _validate(tx.state['artifact_types'][old['type']], p['content'])
    tx.state['artifacts'][p['id']] = {**old, **{k: deepcopy(v) for k, v in p.items() if k != 'expected_revision'},
        'revision': old['revision'] + 1, 'updated_year': tx.context.period}
    tx.events.append(MechanismEvent('artifact.updated', actor_ids=(old['owner_actor'],), artifact_ids=(p['id'],),
        payload={'artifact_type': old['type'], 'content': deepcopy(p['content'])}))


def _put_state(tx, p, principal):
    if principal not in tx.state['actors']:
        raise GraphRuntimeError('custom persistent state needs an existing actor owner')
    _identity(p['key'])
    key = sha([principal, p['key']])
    old = tx.state['values'].get(key)
    if p['expected_revision'] != (old['revision'] if old else None):
        raise GraphRuntimeError('custom state expected revision differs')
    tx.state['values'][key] = {'owner_actor': principal, 'key': p['key'], 'value': deepcopy(p['value']),
        'revision': old['revision'] + 1 if old else 0}


def _native_context(tx, p, principal):
    tx.require_artifacts(p['artifact_ids'])
    for aid in _strings(p['actor_ids']):
        actor = tx.require_native_author(aid)
        current = tx.context_updates.setdefault(aid, deepcopy(getattr(actor, 'institutional_context', [])))
        message = {'message_id': 'native-domain-' + tx.command_key, 'origin_actor_id': principal,
            'received_year': tx.context.period, 'emitted_year': tx.value.emitted_period,
            'payload': deepcopy(p['content']), 'artifact_ids': deepcopy(p['artifact_ids']),
            'artifact_records': [deepcopy(tx.state['artifacts'][i]) for i in p['artifact_ids'] if i in tx.state['artifacts']],
            'input_event_ids': list(tx.value.lineage_event_ids)}
        current.append(message)
        # Preserve the existing measurement/replay meaning: one actual delivered
        # researcher-input event per recipient, regardless of institution type.
        tx.events.append(MechanismEvent('native.system.context_delivered', actor_ids=(aid,),
            artifact_ids=tuple(p['artifact_ids']), payload={'message': deepcopy(message)}))


def _native_project(tx, p, principal):
    from .native_activity_contracts import PLAN, _validate_plan
    assignment = p['assignment']
    payload = {'schema': PLAN, 'year': tx.context.period, 'assignments': [assignment], 'submit_actor_ids': []}
    directions, _, staged = _validate_plan(tx.kernel, payload, tx.context.period)
    aid = assignment['actor_id']
    tx.require_native_author(aid)
    if aid in tx.project_updates:
        raise GraphRuntimeError('one atomic domain batch has conflicting native project writers')
    start, end = staged[aid]
    tx.project_updates[aid] = {'direction': directions[aid], 'start': start, 'end': end}
    tx.events.append(MechanismEvent('native.domain.project_applied', actor_ids=(aid,),
        payload={'origin_actor_id': principal, 'command_key': tx.command_key, 'assignment': deepcopy(assignment)}))


def _native_transfer(tx, p, principal):
    tx.require_native_author(p['from_actor'])
    tx.require_native_author(p['to_actor'])
    tx.transfers.append(replace(tx.value, payload={'transaction_id': tx.command_key, **p}))


def apply_domain_commands(kernel, context):
    if kernel._simulation is None or kernel._frame is None:
        raise GraphRuntimeError('native domain actions need an executing original-world boundary')
    values = context.inputs.get('commands', ())
    if len(values) > 1024:
        raise GraphRuntimeError('native domain atomic command batch exceeds explicit resource bound')
    tx = DomainTransaction(kernel, context)
    registry = kernel.domain_actions
    for value in values:
        command = deepcopy(dict(value.payload))
        if (set(command) != {'schema', 'command_id', 'actor_id', 'action', 'payload'}
                or command['schema'] != COMMAND_SCHEMA or not isinstance(command['payload'], dict)
                or not isinstance(command['actor_id'], str) or not value.lineage_event_ids
                or value.emitted_period > context.period):
            raise GraphRuntimeError('native domain command requires exact typed envelope and causal source')
        _identity(command['command_id'])
        origin = {'source_mechanism': value.source_mechanism, 'source_port': value.source_port,
            'emitted_period': value.emitted_period, 'command_id': command['command_id']}
        key = sha(origin)
        prior = tx.state['receipts'].get(key)
        if prior is not None:
            if prior['command_sha256'] != sha(command):
                raise GraphRuntimeError('replayed native domain command changes its exact body')
            continue
        tx.authorize(command['actor_id'], command['action'])
        if command['action'] not in registry.actions:
            raise GraphRuntimeError('unregistered typed native action capability')
        schema, prepare = registry.actions[command['action']]
        _validate(schema, command['payload'])
        tx.command_key, tx.value = key, value
        prepare(tx, command['payload'], command['actor_id'])
        tx.validate_links()
        previous = tx.state['last_receipt_key']
        receipt = {'index': len(tx.state['receipts']), 'command_key': key, 'origin': origin,
            'command_sha256': sha(command), 'command': command, 'received_year': context.period,
            'input_event_ids': list(value.lineage_event_ids),
            'previous_receipt_sha256': sha(tx.state['receipts'][previous]) if previous else None,
            'domain_content_sha256': _content_hash(tx.state)}
        tx.state['receipts'][key] = receipt
        tx.state['last_receipt_key'] = key
        actors = () if command['actor_id'] == BOOTSTRAP else (command['actor_id'],)
        tx.events.append(MechanismEvent(EVENT, actor_ids=actors, payload=receipt))
    outputs = {'domain': (MechanismValue(deepcopy(tx.state)),)} if context.mechanism.outputs else {}
    # Runtime validation normally follows handler execution. Validate the staged
    # generic result now, before any native effects, including trusted plugins'
    # events and incorrectly configured output ports.
    _validate_result(context.mechanism, MechanismResult(outputs=outputs, events=tuple(tx.events)))
    if tx.events:
        validate_domain_state(tx.state)
        resource_events = tx.commit()
    else:
        resource_events = ()
    return MechanismResult(outputs=outputs, events=(*tx.events, *resource_events))


def register_native_domain(kernel, registry):
    for node in kernel.spec.mechanisms:
        if node.implementation != IMPLEMENTATION:
            continue
        capabilities = node.parameters.get('capabilities', {})
        if set(capabilities) != {'bootstrap', 'roles'} or not isinstance(capabilities['roles'], dict):
            raise GraphRuntimeError('domain receiver needs explicit bootstrap and role grants')
        _strings(capabilities['bootstrap'])
        for role, grants in capabilities['roles'].items():
            _identity(role)
            _strings(grants)
        for category in ('actor', 'artifact'):
            schemas = node.parameters.get(category + '_schemas', {})
            if not isinstance(schemas, dict):
                raise GraphRuntimeError('domain type schemas must be explicit mappings')
            for type_id, schema in schemas.items():
                _identity(type_id)
                _schema(schema)
    registry.register(IMPLEMENTATION, 1, lambda context: apply_domain_commands(kernel, context))
    registry.register(OBSERVER, 1, lambda context: MechanismResult(outputs={'domain': (
        MechanismValue(deepcopy(kernel.open_domain_state or empty_domain())),)}))


def add_domain_action_receiver(spec, *, source, source_port, capabilities, receiver='open-domain-actions',
                               phase=15, latency=0, actor_schemas=None, artifact_schemas=None):
    source_node = next(n for n in spec.mechanisms if n.mechanism_id == source)
    port = next(p for p in source_node.outputs if p.port_id == source_port)
    node = MechanismSpec(receiver, MechanismFamily.CUSTOM, IMPLEMENTATION,
        inputs=(replace(port, port_id='commands', required=False),),
        outputs=(PortSpec('domain', ChannelKind.ARTIFACT, STATE_ARTIFACT),),
        parameters={'capabilities': deepcopy(capabilities), 'actor_schemas': deepcopy(actor_schemas or {}),
                    'artifact_schemas': deepcopy(artifact_schemas or {})})
    types = spec.artifact_types if any(a.artifact_type_id == STATE_ARTIFACT for a in spec.artifact_types) else (*spec.artifact_types, ArtifactTypeSpec(STATE_ARTIFACT))
    return replace(spec, artifact_types=types, mechanisms=(*spec.mechanisms, node),
        schedules=(*spec.schedules, ScheduleSpec(receiver, phase)),
        connections=(*spec.connections, ConnectionSpec(source, source_port, receiver, 'commands', port.channel, latency=latency)))
