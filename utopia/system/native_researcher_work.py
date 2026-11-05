"""Open, institution-authored work for the ORIGINAL fixed-model researchers.

This is a trusted effect capability, not a catalogue of scientific activities.
Untrusted institutions send data through graph ports; their Python stays in the
existing pinned container. Responses are model output, never fabricated papers,
reviews, measurements or automatic state changes.
"""
from copy import deepcopy
from dataclasses import replace
import re

from jsonschema import Draft202012Validator, SchemaError, ValidationError

from .code_mechanisms import _schema, canonical, sha
from .model import ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from .runtime import GraphRuntimeError, MechanismEvent, MechanismResult, MechanismValue

IMPLEMENTATION = 'native.researcher.work.v15'
REQUEST = 'native-researcher-work-request-v15'
RESPONSE = 'native-researcher-work-response-v15'
STATE = 'scienceutopia.native-researcher-work-state.v15'
RECEIPT = 'scienceutopia.native-researcher-work-receipt.v15'
EVENT = 'native.system.researcher_work_completed'
_REQUEST_KEYS = {'schema', 'request_id', 'actor_id', 'instruction', 'content', 'artifact_ids', 'response_schema'}


def _identity(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 200:
        raise GraphRuntimeError('researcher work requires a bounded explicit identity')
    return value


def validate_work_request(request):
    """Pure finite-data/type checking, without interpreting an activity name."""
    if not isinstance(request, dict) or set(request) != _REQUEST_KEYS or request['schema'] != REQUEST:
        raise GraphRuntimeError('researcher work requires the exact request envelope')
    _identity(request['request_id']); _identity(request['actor_id'])
    if (not isinstance(request['instruction'], str) or not request['instruction'].strip()
            or not isinstance(request['content'], dict) or not isinstance(request['artifact_ids'], list)
            or any(not isinstance(v, str) or not v for v in request['artifact_ids'])
            or len(set(request['artifact_ids'])) != len(request['artifact_ids'])):
        raise GraphRuntimeError('researcher work instruction/content/artifact identities differ')
    try:
        _schema(request['response_schema'])
        if request['response_schema'].get('type') != 'object':
            raise ValueError('response schema must explicitly declare an object')
        if len(canonical(request)) > 262_144:
            raise ValueError('request exceeds 262144 UTF-8 bytes')
    except (ValueError, TypeError, SchemaError) as error:
        raise GraphRuntimeError('invalid researcher work finite-data/schema contract: ' + str(error)) from error
    return request


def validate_work_node(node):
    if (set(node.parameters) != {'max_requests_per_invocation'}
            or type(node.parameters['max_requests_per_invocation']) is not int
            or not 1 <= node.parameters['max_requests_per_invocation'] <= 64):
        raise GraphRuntimeError('researcher work needs an explicit per-invocation request cap in 1..64')
    if (not any(p.port_id == 'tasks' and p.channel == ChannelKind.ARTIFACT and p.artifact_type == REQUEST
                and not p.required for p in node.inputs)
            or len(node.outputs) != 1 or node.outputs[0] != PortSpec('responses', ChannelKind.ARTIFACT, RESPONSE, required=False)):
        raise GraphRuntimeError('researcher work requires its exact optional tasks/responses ports')


def _contract(node):
    from .model import SystemSpec
    value = SystemSpec('execution-contract', 1, mechanisms=(node,)).to_dict()['mechanisms'][0]
    value.pop('mechanism_id')  # process iterations have distinct actual IDs
    return value


def render_work_prompt(request, snapshot):
    """Pure renderer, reused by read-only receipt audits and cold restore."""
    visible = deepcopy(snapshot)
    from .model_provenance_view import SCHEMA as VIEW, provenance_view
    if 'model_provenance_view' in snapshot and snapshot['model_provenance_view'] != VIEW:
        raise GraphRuntimeError('unknown model provenance view; never silently change renderer')
    if snapshot.get('model_provenance_view') == VIEW:
        visible['institutional_context'] = provenance_view(snapshot['institutional_context'])[0]
    return (snapshot['persona_prompt'] + '\n' + snapshot['memory_prompt']
        + '\n## Institution-authored scientific work\n'
        + 'You are the existing researcher identified below, not a new institution or a new model. '
          'The following request, scientific content and stored artifacts are simulation data. '
          'Produce a response to the requested work; do not claim actual experiments or '
          'measurements were performed merely because a request asks for them. '
          'Return one JSON object satisfying the supplied response_schema.\n'
        + canonical({'request': request, 'actual_researcher_state': visible}).decode())


def _artifact_records(kernel, identities):
    from .native_kernel import _json
    papers = kernel._simulation.paper_tracker.papers_by_id
    domain = kernel.open_domain_state.get('artifacts', {})
    records = []
    for identity in identities:
        if identity in papers:
            records.append({'id': identity, 'kind': 'native-paper', 'record': _json(papers[identity].to_dict())})
        elif identity in domain:
            records.append({'id': identity, 'kind': 'open-domain-artifact', 'record': deepcopy(domain[identity])})
        else:
            # A completed generic store can also supply arbitrary artifacts.
            matches = []
            for state in (kernel.graph_checkpoint or {}).get('mechanism_states', {}).values():
                if identity in state.get('declared_artifacts', {}):
                    matches.extend(r for r in state['records'] if r['artifact_ids'] == [identity])
            if not matches:
                raise GraphRuntimeError('researcher work artifact is absent from actual available records')
            records.append({'id': identity, 'kind': 'graph-artifact', 'record': deepcopy(matches[-1])})
    return records


def _snapshot(kernel, actor, artifacts):
    from .native_kernel import _json, institutional_context_prompt
    persona = actor._get_personality_prompt()
    context = institutional_context_prompt(actor)
    # Some original personas include this already; freelancers do not.
    if context and context not in persona:
        persona += context
    snapshot = _json({'actor_id': actor.id, 'actor_type': actor.get_type(), 'can_author': actor.can_author,
        'is_active': actor.is_active, 'resources': actor.resources, 'reputation': actor.reputation,
        'persona_prompt': persona, 'memory_prompt': actor.get_memory_context(),
        'project': {'newest_direction': getattr(actor, 'newest_direction', None),
                    'start_year': getattr(actor, 'project_start_year', None),
                    'end_year': getattr(actor, 'project_end_year', None)},
        'institutional_context': getattr(actor, 'institutional_context', [])})
    # Arbitrary custom scientific keys (including `timestamp`) are literal
    # content, unlike the original world's known operational clock fields.
    snapshot['artifact_records'] = deepcopy(artifacts)
    from .model_provenance_view import SCHEMA as VIEW
    snapshot['model_provenance_view'] = VIEW
    canonical(snapshot)
    return snapshot


def _request_key(record):
    return sha({k: record[k] for k in ('execution_node', 'year', 'origin', 'request')})


def validate_work_receipt(record):
    """Self-contained consistency checks; actual source/world joins are separate."""
    keys = {'schema', 'index', 'execution_node', 'execution_contract_sha256', 'year', 'origin',
        'request', 'request_sha256', 'native_snapshot', 'native_snapshot_sha256', 'prompt',
        'prompt_sha256', 'response', 'response_sha256', 'seed_ctx', 'request_key',
        'previous_receipt_sha256', 'receipt_sha256'}
    if not isinstance(record, dict) or set(record) != keys or record['schema'] != RECEIPT:
        raise GraphRuntimeError('researcher work receipt schema differs')
    try:
        validate_work_request(record['request'])
        request, snapshot, origin = record['request'], record['native_snapshot'], record['origin']
        snapshot_keys = {'actor_id', 'actor_type', 'can_author', 'is_active', 'resources', 'reputation',
            'persona_prompt', 'memory_prompt', 'project', 'institutional_context', 'artifact_records'}
        from .model_provenance_view import SCHEMA as VIEW
        if (not isinstance(snapshot, dict) or not snapshot_keys <= set(snapshot) <= snapshot_keys | {'model_provenance_view'}
                or ('model_provenance_view' in snapshot and snapshot['model_provenance_view'] != VIEW)
                or not isinstance(snapshot['persona_prompt'], str) or not isinstance(snapshot['memory_prompt'], str)
                or type(snapshot['is_active']) is not bool or not isinstance(snapshot['artifact_records'], list)
                or not isinstance(snapshot['institutional_context'], list)
                or not isinstance(snapshot['project'], dict)):
            raise GraphRuntimeError('researcher work actual-author snapshot contract differs')
        for name in ('execution_contract_sha256', 'request_sha256', 'native_snapshot_sha256',
                     'prompt_sha256', 'response_sha256', 'request_key', 'receipt_sha256'):
            if not isinstance(record[name], str) or not re.fullmatch('[0-9a-f]{64}', record[name]):
                raise GraphRuntimeError('researcher work receipt digest differs')
        if record['previous_receipt_sha256'] is not None and (
                not isinstance(record['previous_receipt_sha256'], str)
                or not re.fullmatch('[0-9a-f]{64}', record['previous_receipt_sha256'])):
            raise GraphRuntimeError('researcher work receipt predecessor differs')
        if (type(record['index']) is not int or record['index'] < 0
                or type(record['year']) is not int or record['year'] < 1
                or not isinstance(origin, dict) or set(origin) != {'source_mechanism', 'source_port',
                    'emitted_period', 'input_event_ids'} or not isinstance(origin['input_event_ids'], list)
                or not origin['input_event_ids'] or len(set(origin['input_event_ids'])) != len(origin['input_event_ids'])
                or any(not isinstance(e, str) or not e for e in origin['input_event_ids'])
                or not isinstance(origin['source_mechanism'], str) or not origin['source_mechanism']
                or not isinstance(origin['source_port'], str) or not origin['source_port']
                or type(origin['emitted_period']) is not int or not 1 <= origin['emitted_period'] <= record['year']
                or snapshot['actor_id'] != request['actor_id'] or snapshot['can_author'] is not True
                or [a['id'] for a in snapshot['artifact_records']] != request['artifact_ids']
                or record['request_key'] != _request_key(record)
                or record['request_sha256'] != sha(request)
                or record['native_snapshot_sha256'] != sha(snapshot)
                or record['prompt'] != render_work_prompt(request, snapshot)
                or record['prompt_sha256'] != sha(record['prompt'])
                or record['response_sha256'] != sha(record['response'])
                or not isinstance(record['response'], dict)
                or record['seed_ctx'] != ['native_researcher_work_v15', record['year'],
                    record['execution_node'], request['actor_id'], record['request_key'],
                    record['native_snapshot_sha256'], record['execution_contract_sha256']]
                or record['receipt_sha256'] != sha({k: v for k, v in record.items() if k != 'receipt_sha256'})):
            raise GraphRuntimeError('researcher work receipt identity/content/hash differs')
        Draft202012Validator(request['response_schema']).validate(record['response'])
        for artifact in snapshot['artifact_records']:
            if (not isinstance(artifact, dict) or set(artifact) != {'id', 'kind', 'record'}
                    or not isinstance(artifact['record'], dict)
                    or artifact['kind'] not in {'native-paper', 'open-domain-artifact', 'graph-artifact'}):
                raise GraphRuntimeError('researcher work artifact snapshot kind differs')
            identity = (artifact['record'].get('id') if artifact['kind'] != 'graph-artifact'
                else artifact['record'].get('artifact_ids', [None])[0])
            if identity != artifact['id']:
                raise GraphRuntimeError('researcher work artifact snapshot identity differs')
    except (KeyError, TypeError, ValueError, IndexError, ValidationError) as error:
        if isinstance(error, GraphRuntimeError):
            raise
        raise GraphRuntimeError('invalid researcher work receipt: ' + str(error)[:300]) from error


def validate_work_state(state):
    if state == {}:
        return
    if not isinstance(state, dict) or set(state) != {'schema', 'receipts'} or state['schema'] != STATE or not isinstance(state['receipts'], list):
        raise GraphRuntimeError('researcher work persistent state differs')
    previous, seen = None, set()
    for index, record in enumerate(state['receipts']):
        validate_work_receipt(record)
        if record['index'] != index or record['previous_receipt_sha256'] != previous or record['request_key'] in seen:
            raise GraphRuntimeError('researcher work receipt sequence/duplicate differs')
        previous = record['receipt_sha256']; seen.add(record['request_key'])


def execute_researcher_work(kernel, context):
    validate_work_node(context.mechanism)
    validate_work_state(dict(context.state))
    values = context.inputs.get('tasks', ())
    if len(values) > context.mechanism.parameters['max_requests_per_invocation']:
        raise GraphRuntimeError('researcher work exceeds the explicit per-invocation request cap; never clipped')
    receipts = deepcopy(context.state.get('receipts', []))
    seen = {r['request_key'] for r in receipts}
    planned = []
    # Preflight ALL tasks/actors/schemas/artifacts and prompts before any call.
    for value in values:
        request = deepcopy(dict(value.payload))
        validate_work_request(request)
        if (value.actor_ids != (request['actor_id'],) or value.artifact_ids != tuple(request['artifact_ids'])
                or not value.lineage_event_ids or not 1 <= value.emitted_period <= value.available_period <= context.period):
            raise GraphRuntimeError('researcher work addressing/causal availability differs')
        actor = kernel._simulation.ecosystem.agent_population.get(request['actor_id'])
        if actor is None or not getattr(actor, 'can_author', False) or actor.llm is not kernel._simulation.llm:
            raise GraphRuntimeError('researcher work requires an existing original author with the fixed world model')
        snapshot = _snapshot(kernel, actor, _artifact_records(kernel, request['artifact_ids']))
        record = {'schema': RECEIPT, 'index': len(receipts) + len(planned),
            'execution_node': context.mechanism.mechanism_id,
            'execution_contract_sha256': sha(_contract(context.mechanism)), 'year': context.period,
            'origin': {'source_mechanism': value.source_mechanism, 'source_port': value.source_port,
                'emitted_period': value.emitted_period, 'input_event_ids': list(value.lineage_event_ids)},
            'request': request, 'request_sha256': sha(request), 'native_snapshot': snapshot,
            'native_snapshot_sha256': sha(snapshot)}
        record['request_key'] = _request_key(record)
        if record['request_key'] in seen:
            raise GraphRuntimeError('duplicate researcher work request identity in this invocation/history')
        seen.add(record['request_key'])
        record['prompt'] = render_work_prompt(request, snapshot)
        if len(record['prompt'].encode()) > 524_288:
            raise GraphRuntimeError('researcher work prompt exceeds 524288 UTF-8 bytes; never truncated')
        record['prompt_sha256'] = sha(record['prompt'])
        record['seed_ctx'] = ['native_researcher_work_v15', context.period, record['execution_node'],
            actor.id, record['request_key'], record['native_snapshot_sha256'], record['execution_contract_sha256']]
        planned.append(record)
    events, outputs = [], []
    for record in planned:
        kernel._simulation.portable_safe_point()
        response, _ = kernel._simulation.llm.generate(prompt=record['prompt'],
            response_format={'type': 'json_schema', 'json_object': {
                'name': 'native_researcher_work_v15', 'schema': record['request']['response_schema']}},
            seed_ctx=tuple(record['seed_ctx']))
        if not isinstance(response, dict):
            raise GraphRuntimeError('researcher work returned a non-object response')
        try:
            canonical(response)
            Draft202012Validator(record['request']['response_schema']).validate(response)
        except (ValueError, TypeError, ValidationError) as error:
            raise GraphRuntimeError('researcher work response violates the authored contract: ' + str(error)[:300]) from error
        record.update(response=deepcopy(response), response_sha256=sha(response),
            previous_receipt_sha256=receipts[-1]['receipt_sha256'] if receipts else None)
        record['receipt_sha256'] = sha(record)
        validate_work_receipt(record)
        receipts.append(record)
        events.append(MechanismEvent(EVENT, actor_ids=(record['request']['actor_id'],),
            artifact_ids=tuple(record['request']['artifact_ids']), payload=record))
        outputs.append(MechanismValue({'schema': RESPONSE, 'request_id': record['request']['request_id'],
            'actor_id': record['request']['actor_id'], 'response': deepcopy(response),
            'receipt_sha256': record['receipt_sha256']}, actor_ids=(record['request']['actor_id'],),
            artifact_ids=tuple(record['request']['artifact_ids']), event_prefix_length=len(events)))
    return MechanismResult(outputs={'responses': tuple(outputs)}, events=tuple(events),
        next_state={'schema': STATE, 'receipts': receipts})


def register_researcher_work(kernel, registry):
    from .native_migration import native_execution_nodes
    for node in native_execution_nodes(kernel.spec):
        if node.implementation == IMPLEMENTATION:
            validate_work_node(node)
    registry.register(IMPLEMENTATION, 1, lambda context: execute_researcher_work(kernel, context))


def validate_work_checkpoint(spec, graph, events):
    """Bind direct/wrapped persistent receipts to exact canonical event history."""
    from .native_migration import _execution_contract
    work_events = [e for e in events if e.event_type == EVENT]
    by_id = {e.event_id: e for e in events}
    for event in work_events:
        validate_work_receipt(dict(event.payload))
        actual_work = (event.provenance.get('implementation') == IMPLEMENTATION or (
            event.provenance.get('implementation') == 'native.process.activity.v1'
            and event.provenance.get('delegate_implementation') == IMPLEMENTATION))
        if (not actual_work or event.actor_ids != (event.payload['request']['actor_id'],)
                or event.artifact_ids != tuple(event.payload['request']['artifact_ids'])
                or event.year != event.payload['year']
                or not set(event.payload['origin']['input_event_ids']) <= set(event.provenance.get('input_event_ids', []))
                or not any(by_id.get(identity) is not None
                    and by_id[identity].provenance.get('mechanism_id') == event.payload['origin']['source_mechanism']
                    and by_id[identity].year == event.payload['origin']['emitted_period']
                    for identity in event.payload['origin']['input_event_ids'])):
            raise GraphRuntimeError('researcher work canonical receipt addressing/lineage differs')
    for node in spec.mechanisms:
        execution = _execution_contract(node)
        if execution.implementation != IMPLEMENTATION:
            continue
        validate_work_node(execution)
        state = (graph or {}).get('mechanism_states', {}).get(node.mechanism_id, {})
        if execution is not node:
            state = state.get('delegate_state', node.parameters['initial_delegate_state'])
        validate_work_state(state)
        matching = [dict(e.payload) for e in work_events if e.provenance.get('mechanism_id') == node.mechanism_id
            and e.provenance.get('system_fingerprint') == spec.fingerprint]
        for record in matching:
            valid_execution = (record['execution_node'] == node.mechanism_id if execution is node
                else re.fullmatch(re.escape(node.mechanism_id) + r'\.iteration-[0-9]+', record['execution_node']))
            if not valid_execution or record['execution_contract_sha256'] != sha(_contract(execution)):
                raise GraphRuntimeError('researcher work actual execution contract differs')
        current = [r for r in state.get('receipts', []) if r in matching]
        # Migrated state can carry earlier receipts; all must still have an event.
        if (any(r not in [dict(e.payload) for e in work_events] for r in state.get('receipts', []))
                or current != matching):
            raise GraphRuntimeError('researcher work saved state differs from canonical receipt history')
    nodes = {n.mechanism_id: _execution_contract(n) for n in spec.mechanisms}
    for delivery in (graph or {}).get('queued_deliveries', []):
        target = nodes[delivery['target_mechanism']]
        if target.implementation == IMPLEMENTATION and delivery['target_port'] == 'tasks':
            validate_work_request(delivery['value']['payload'])


def add_researcher_work_receiver(spec, *, source, source_port, receiver='researcher-work',
                                 phase=190, latency=0, max_requests_per_invocation=16):
    """Grant an explicit producer work authority; caller supplies every task."""
    node = MechanismSpec(receiver, MechanismFamily.CUSTOM, IMPLEMENTATION,
        inputs=(PortSpec('tasks', ChannelKind.ARTIFACT, REQUEST, required=False),),
        outputs=(PortSpec('responses', ChannelKind.ARTIFACT, RESPONSE, required=False),),
        parameters={'max_requests_per_invocation': max_requests_per_invocation})
    validate_work_node(node)
    types = {a.artifact_type_id for a in spec.artifact_types}
    return replace(spec, mechanisms=(*spec.mechanisms, node),
        artifact_types=(*spec.artifact_types, *(ArtifactTypeSpec(a) for a in (REQUEST, RESPONSE) if a not in types)),
        schedules=(*spec.schedules, ScheduleSpec(receiver, phase)),
        connections=(*spec.connections, ConnectionSpec(source, source_port, receiver, 'tasks', ChannelKind.ARTIFACT, latency=latency)))
