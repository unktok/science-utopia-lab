"""Data-authored process dependencies, guards and repeated actual activities.

The original year remains a scientific measurement/checkpoint boundary, not a
mandatory sequence of institutions. Delegates use the existing native registry;
generated Python is never imported or evaluated in the host.
"""
from __future__ import annotations

from dataclasses import replace

from .model import (ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismSpec,
                    PortSpec, ScheduleSpec, SystemSpec, _mechanism_from_dict)
from .runtime import (GraphRuntimeError, MechanismEvent, MechanismResult,
                      MechanismValue, _validate_result)
from .code_mechanisms import canonical, sha

IMPLEMENTATION = 'native.process.activity.v1'
CONTROL = 'native-process-control-v1'
DONE = 'process-completion'


def _clone(value):
    import json
    return json.loads(canonical(value))


def controlled_activity(node, *, count=1, limit=16, control=False,
                        guard_path=None, count_path=None, until_path=None,
                        initial_state=None, missing_control='error'):
    """Wrap any registered activity, with optional typed source-authored control.

    Control payloads, e.g. ``{'enabled': True, 'count': 3}``, are real messages,
    not evaluated expressions. All limits are declared technical compute bounds.
    Skip is explicit process completion, NEVER a fabricated native phase effect.
    """
    if node.implementation == IMPLEMENTATION:
        raise GraphRuntimeError('compose process nodes through graph ports, not recursive delegates')
    if any(p.port_id == DONE for p in node.outputs) or any(p.port_id == 'process-control' for p in node.inputs):
        raise GraphRuntimeError('process control/completion port collides with activity')
    delegate = _clone(SystemSpec('delegate-contract', 1, mechanisms=(node,)).to_dict()['mechanisms'][0])
    parameters = {'delegate': delegate, 'count': count, 'limit': limit,
        'control': control, 'guard_path': guard_path, 'count_path': count_path,
        'until_path': until_path, 'initial_delegate_state': _clone({} if initial_state is None else initial_state),
        'missing_control': missing_control}
    _validate_parameters(parameters)
    return replace(node, implementation=IMPLEMENTATION, version=1,
        parameters=parameters,
        inputs=(*(replace(p, required=False) if control or count == 0 else p for p in node.inputs),
                *((PortSpec('process-control', ChannelKind.SIGNAL, CONTROL, required=missing_control != 'wait'),) if control else ())),
        outputs=(*(replace(p, required=False) for p in node.outputs),
                 PortSpec(DONE, ChannelKind.SIGNAL, CONTROL)))


def _validate_parameters(p):
    required = {'delegate', 'count', 'limit', 'control', 'guard_path', 'count_path',
                'until_path', 'initial_delegate_state', 'missing_control'}
    if set(p) != required or type(p['limit']) is not int or not 1 <= p['limit'] <= 1024:
        raise GraphRuntimeError('process requires explicit 1..1024 invocation limit and exact fields')
    if type(p['count']) is not int or not 0 <= p['count'] <= p['limit'] or type(p['control']) is not bool:
        raise GraphRuntimeError('process count/control must match the declared invocation bound')
    if p['missing_control'] not in ('wait', 'error'):
        raise GraphRuntimeError('missing control behavior must explicitly be wait or error')
    for key in ('guard_path', 'count_path', 'until_path'):
        path = p[key]
        if path is not None and (not isinstance(path, list) or not path
                or any(not isinstance(k, str) or not k for k in path)):
            raise GraphRuntimeError('process paths must be nonempty string-key lists')
    if not p['control'] and (p['guard_path'] is not None or p['count_path'] is not None):
        raise GraphRuntimeError('dynamic guard/count requires an explicit control input')
    if not isinstance(p['initial_delegate_state'], dict):
        raise GraphRuntimeError('initial delegate state must be an explicit JSON mapping')
    _clone(p)
    node = _mechanism_from_dict(p['delegate'])
    if node.implementation == IMPLEMENTATION:
        raise GraphRuntimeError('recursive process delegates are not allowed; use graph composition')
    return node


def _at(value, path):
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise GraphRuntimeError('process control/state path does not exist')
        value = value[key]
    return value


def _handler(registry, context):
    parameters = context.mechanism.parameters
    delegate = _validate_parameters(parameters)
    count, enabled, waiting = parameters['count'], True, False
    if parameters['control']:
        values = context.inputs.get('process-control', ())
        if not values and parameters['missing_control'] == 'wait':
            count, enabled, waiting = 0, False, True
        elif len(values) != 1 or not values[0].lineage_event_ids or not (
                values[0].emitted_period <= values[0].available_period <= context.period):
            raise GraphRuntimeError('process requires one available, causally bound control message')
        payload = _clone(dict(values[0].payload)) if values else {}
        if not waiting and parameters['guard_path'] is not None:
            enabled = _at(payload, parameters['guard_path'])
            if type(enabled) is not bool:
                raise GraphRuntimeError('process guard must be an explicit boolean')
        if not waiting and parameters['count_path'] is not None:
            count = _at(payload, parameters['count_path'])
    if type(count) is not int or not 0 <= count <= parameters['limit']:
        raise GraphRuntimeError('process count exceeds declared budget; never clipped')
    # Original phase routines use annual scientific request identities. Repeat
    # custom/domain/code/tensor/LLM activities instead of silently reusing those
    # identities for another annual phase call.
    if count > 1 and delegate.implementation.startswith(('native.phase.', 'native.activity.')):
        raise GraphRuntimeError('annual native phase is single-shot; repeat explicit custom activities')
    state = _clone(context.state.get('delegate_state', parameters['initial_delegate_state']))
    outputs = {p.port_id: [] for p in delegate.outputs}
    events, executed = [], 0
    for iteration in range(count if enabled else 0):
        if parameters['until_path'] is not None:
            stop = _at(state, parameters['until_path'])
            if type(stop) is not bool:
                raise GraphRuntimeError('process until-state must be boolean')
            if stop:
                break
        if any(p.required and not context.inputs.get(p.port_id, ()) for p in delegate.inputs):
            raise GraphRuntimeError('enabled process activity lacks a required actual input')
        invocation = replace(context,
            mechanism=replace(delegate,
                mechanism_id=context.mechanism.mechanism_id + '.iteration-' + str(iteration)),
            inputs={p.port_id: context.inputs.get(p.port_id, ()) for p in delegate.inputs},
            state=_clone(state))
        result = registry.resolve(delegate)(invocation)
        normalized = _validate_result(delegate, result)
        if result.next_state is not None:
            if not isinstance(result.next_state, dict):
                raise GraphRuntimeError('process delegate state must remain a JSON mapping')
            state = _clone(result.next_state)
        events.extend(replace(event, provenance={**event.provenance,
            'process_iteration': iteration, 'delegate_implementation': delegate.implementation,
            'delegate_contract_sha256': sha(parameters['delegate']),
            'delegate_mechanism_id': invocation.mechanism.mechanism_id}) for event in result.events)
        events.append(MechanismEvent('native.process.iteration', payload={
            'iteration': iteration, 'delegate_contract_sha256': sha(parameters['delegate']),
            'state_after_sha256': sha(state),
            'outputs_sha256': sha({k: [dict(v.payload) for v in values] for k, values in normalized.items()})}))
        for port, values in normalized.items():
            outputs[port].extend(replace(value, event_prefix_length=len(events)) for value in values)
        executed += 1
    receipt = {'year': context.period, 'enabled': enabled, 'requested': count, 'waiting_for_control': waiting,
        'executed': executed, 'limit': parameters['limit'],
        'delegate_contract_sha256': sha(parameters['delegate']),
        'state_before_sha256': sha(context.state.get('delegate_state', parameters['initial_delegate_state'])),
        'state_after_sha256': sha(state)}
    events.append(MechanismEvent('native.process.completed' if executed else 'native.process.skipped', payload=receipt))
    outputs[DONE] = [MechanismValue(receipt)]
    return MechanismResult(outputs={k: tuple(v) for k, v in outputs.items()},
        events=tuple(events), next_state={'delegate_state': state,
            'total_invocations': context.state.get('total_invocations', 0) + executed,
            'last_receipt': receipt})


def register_native_process(kernel, registry):
    """Called after ordinary native/domain/tensor/code registry setup."""
    delegates = [_validate_parameters(n.parameters) for n in kernel.spec.mechanisms if n.implementation == IMPLEMENTATION]
    from .code_mechanisms import CODE_IMPLEMENTATION, DockerCodeExecutor, register_code_mechanisms, validate_code_artifact
    images = {n.parameters.get('runtime_image_id') for n in (*kernel.spec.mechanisms, *delegates)
              if n.implementation == CODE_IMPLEMENTATION}
    if delegates and images:
        if len(images) != 1 or None in images:
            raise GraphRuntimeError('process code delegates require the same explicitly pinned native runtime image')
        for node in delegates:
            if node.implementation == CODE_IMPLEMENTATION:
                validate_code_artifact(node.parameters['code_artifact'])
        if (CODE_IMPLEMENTATION, 1) not in registry.registered:
            if kernel.code_executor is None:
                kernel.code_executor = DockerCodeExecutor(next(iter(images)))
            register_code_mechanisms(registry, kernel.code_executor, kernel.execution_receipts)
    # All delegates resolve before any activity mutates the actual society.
    from .code_mechanisms import _schema
    for node in delegates:
        if node.implementation == 'native.world.llm-institution.v1':
            schemas = node.parameters.get('output_schemas', {})
            if set(schemas) != {p.port_id for p in node.outputs}:
                raise GraphRuntimeError('process LLM delegate schemas and ports differ')
            for schema in (*schemas.values(), node.parameters.get('state_schema', {'type': 'object'})):
                _schema(schema)
        registry.resolve(node)
    registry.register(IMPLEMENTATION, 1, lambda context: _handler(registry, context))


def compile_dependencies(spec, dependencies, *, priorities=None, detach_serial=False):
    """Compile an arbitrary declared activity DAG into ordinary typed graph ports.

    No mandatory mechanism family or fixed order is inserted. Existing data
    edges are included in the dependency proof; a contradictory/cyclic process
    fails before execution. A producer must actually emit its declared completion
    port; the compiler never creates successful scientific activity.
    """
    nodes = {n.mechanism_id: n for n in spec.mechanisms}
    if set(dependencies) != set(nodes) or any(not isinstance(v, (list, tuple)) for v in dependencies.values()):
        raise GraphRuntimeError('explicit dependency lists must cover every mechanism')
    if any(len(set(v)) != len(v) or any(x not in nodes or x == key for x in v) for key, v in dependencies.items()):
        raise GraphRuntimeError('process dependency references must be unique existing other nodes')
    priorities = priorities or {s.mechanism_id: s.phase for s in spec.schedules}
    if set(priorities) != set(nodes) or any(type(v) is not int for v in priorities.values()):
        raise GraphRuntimeError('every process activity needs one explicit integer priority')
    edges = list(spec.connections)
    if detach_serial:
        def native(node):
            implementation = (_validate_parameters(node.parameters).implementation
                if node.implementation == IMPLEMENTATION else node.implementation)
            return implementation.startswith(('native.phase.', 'native.activity.'))
        removed = [e for e in edges if e.target_port == 'after' and e.source_port == 'next'
                   and native(nodes[e.source_mechanism]) and native(nodes[e.target_mechanism])]
        edges = [e for e in edges if e not in removed]
        targets = {e.target_mechanism for e in removed}
        for key in targets:
            node = nodes[key]
            params = _clone(node.parameters)
            if node.implementation == IMPLEMENTATION:
                params['delegate']['inputs'] = [p for p in params['delegate']['inputs'] if p['port_id'] != 'after']
            nodes[key] = replace(node, parameters=params, inputs=tuple(p for p in node.inputs if p.port_id != 'after'))
    for target, parents in dependencies.items():
        for index, parent in enumerate(parents):
            source = nodes[parent]
            port = DONE if source.implementation == IMPLEMENTATION else 'next'
            output = next((p for p in source.outputs if p.port_id == port), None)
            if output is None:
                raise GraphRuntimeError('dependency producer needs an actual next/completion output; wrap arbitrary activities explicitly')
            name = 'requires-' + str(index)
            if any(p.port_id == name for p in nodes[target].inputs):
                raise GraphRuntimeError('dependency input collides with existing activity port')
            if nodes[target].implementation == 'code.python.v1':
                raise GraphRuntimeError('wrap source activities before adding dependency controls; never rewrite their ABI')
            nodes[target] = replace(nodes[target], inputs=(*nodes[target].inputs, replace(output, port_id=name, required=True)))
            edges.append(ConnectionSpec(parent, port, target, name, output.channel))
    parents = {key: set(dependencies[key]) for key in nodes}
    for edge in edges:
        if edge.latency == 0:
            parents[edge.target_mechanism].add(edge.source_mechanism)
    pending, order = set(nodes), []
    while pending:
        ready = [key for key in pending if not (parents[key] & pending)]
        if not ready:
            raise GraphRuntimeError('declared/data process contains a same-period dependency cycle')
        selected = min(ready, key=lambda key: (priorities[key], key))
        pending.remove(selected)
        order.append(selected)
    artifact_types = spec.artifact_types
    if any(n.implementation == IMPLEMENTATION for n in nodes.values()) and CONTROL not in {a.artifact_type_id for a in artifact_types}:
        artifact_types = (*artifact_types, ArtifactTypeSpec(CONTROL))
    result = replace(spec, mechanisms=tuple(nodes[n.mechanism_id] for n in spec.mechanisms),
        artifact_types=artifact_types, connections=tuple(edges),
        schedules=tuple(ScheduleSpec(key, index * 10) for index, key in enumerate(order)),
        metadata={**spec.metadata, 'native_process': {'schema': 'scienceutopia.native-process.v1',
            'dependencies': _clone(dependencies), 'order': order, 'priorities': _clone(priorities)}})
    from .validation import validate_system_spec
    validate_system_spec(result).require_valid()
    return result
