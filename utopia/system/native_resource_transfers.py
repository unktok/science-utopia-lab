"""Data-only capability: apply authored conserving transfers to native actors.

This is an effects bridge, not an allocation policy. Arbitrary institutional
code/LLM nodes choose commands. No candidate source executes in the host here.
"""
from copy import deepcopy
from dataclasses import replace
import math

from .model import ConnectionSpec, MechanismFamily, MechanismSpec, ScheduleSpec
from .runtime import GraphRuntimeError, MechanismEvent, MechanismResult
from .code_mechanisms import sha

IMPLEMENTATION = 'native.world.resource-transfers.v1'
EVENT = 'native.system.resource_transferred'
STATE_SCHEMA = 'scienceutopia.native-resource-transfer-state.v1'


def add_resource_transfer_receiver(spec, *, source, source_port,
                                   receiver='native-resource-transfers', phase=235, latency=0):
    """Explicitly grant a producer port transfer authority; insert no policy."""
    node = next(n for n in spec.mechanisms if n.mechanism_id == source)
    port = next(p for p in node.outputs if p.port_id == source_port)
    sink = MechanismSpec(receiver, MechanismFamily.CUSTOM, IMPLEMENTATION,
        inputs=(replace(port, port_id='transfers', required=False),))
    return replace(spec, mechanisms=(*spec.mechanisms, sink),
        schedules=(*spec.schedules, ScheduleSpec(receiver, phase)),
        connections=(*spec.connections, ConnectionSpec(source, source_port, receiver,
            'transfers', port.channel, latency=latency)))


def _command(value):
    payload = dict(value.payload)
    if (set(payload) != {'transaction_id', 'from_actor', 'to_actor', 'amount'}
            or not isinstance(payload['transaction_id'], str)
            or not 1 <= len(payload['transaction_id']) <= 200
            or any(not isinstance(payload[k], str) or not payload[k] for k in ('from_actor', 'to_actor'))
            or type(payload['amount']) not in (int, float)
            or not math.isfinite(payload['amount']) or payload['amount'] < 0):
        raise GraphRuntimeError('resource transfer requires exact ID/from_actor/to_actor/finite nonnegative amount')
    origin = {'source_mechanism': value.source_mechanism, 'source_port': value.source_port,
        'emitted_period': value.emitted_period, 'transaction_id': payload['transaction_id']}
    return sha(origin), sha(payload), origin, payload


def _history(kernel):
    result = {}
    for event in kernel.events:
        if event.event_type != EVENT:
            continue
        receipt = dict(event.payload)
        key = receipt['transaction_key']
        if (key != sha(receipt['origin']) or receipt['command_sha256'] != sha(receipt['command'])
                or key in result):
            raise GraphRuntimeError('native transfer history identity/hash/uniqueness differs')
        result[key] = receipt
    current = kernel._frame.get('native_resource_transactions', {})
    if result.keys() & current.keys():
        raise GraphRuntimeError('native resource transfer duplicates committed history')
    return {**result, **deepcopy(current)}


def apply_native_resource_transfers(kernel, context):
    """Validate a whole input batch before mutation; commit or roll back all legs.

    Replay identity is producer + output port + emitted period + transaction ID.
    Exact duplicate delivery is idempotent globally across consumers and years;
    reusing that identity for a different command fails before any mutation.
    """
    simulation = kernel._simulation
    if simulation is None or kernel._frame is None:
        raise GraphRuntimeError('native resource effects need an executing native year')
    actors = {k: a for k, a in simulation.ecosystem.agent_population.items()
        if getattr(a, 'can_author', False)}
    values = [v for port in sorted(context.inputs) for v in context.inputs[port]]
    if len(values) > 1024:
        raise GraphRuntimeError('native transfer batch exceeds explicit resource limit')
    if not values:
        return MechanismResult()
    history = _history(kernel)
    seen = dict(history)
    balances = {key: actor.resources for key, actor in actors.items()}
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in balances.values()):
        raise GraphRuntimeError('native actor has invalid actual resources')
    commands = []
    for value in values:
        key, command_hash, origin, payload = _command(value)
        if origin['emitted_period'] > context.period or not value.lineage_event_ids:
            raise GraphRuntimeError('native transfer requires actual causal producer events and a nonfuture period')
        if key in seen:
            if seen[key]['command_sha256'] != command_hash:
                raise GraphRuntimeError('native transfer identity replay changes its command')
            continue
        source, target, amount = payload['from_actor'], payload['to_actor'], payload['amount']
        if source not in actors or target not in actors:
            raise GraphRuntimeError('native transfer actors must be existing author-capable actors')
        if balances[source] < amount:
            raise GraphRuntimeError('native conserving transfer cannot debit unavailable actual resources')
        before = {actor_id: balances[actor_id] for actor_id in {source, target}}
        debit_before = balances[source]
        balances[source] -= amount
        actual_debit = debit_before - balances[source]
        credit_before = balances[target]
        balances[target] += amount
        actual_credit = balances[target] - credit_before
        if any(not math.isfinite(balances[aid]) for aid in (source, target)):
            raise GraphRuntimeError('native transfer produced nonfinite balances')
        if actual_debit != amount or actual_credit != amount:
            raise GraphRuntimeError('native transfer amount is not exactly representable in both actor balances')
        receipt = {'transaction_key': key, 'command_sha256': command_hash,
            'origin': origin, 'command': payload, 'received_period': context.period,
            'actual_debit': actual_debit, 'actual_credit': actual_credit,
            'input_event_ids': list(value.lineage_event_ids), 'balances_before': before,
            'balances_after': {aid: balances[aid] for aid in before}}
        commands.append(receipt)
        seen[key] = receipt
    if not commands:
        return MechanismResult()
    if not math.isclose(math.fsum(a.resources for a in actors.values()),
                        math.fsum(balances.values()), rel_tol=0, abs_tol=1e-9):
        raise GraphRuntimeError('native resource batch fails finite-precision conservation')
    state = deepcopy(context.state) if context.state else {'schema': STATE_SCHEMA, 'transactions': {}}
    if (set(state) != {'schema', 'transactions'} or state['schema'] != STATE_SCHEMA
            or not isinstance(state['transactions'], dict)):
        raise GraphRuntimeError('native resource capability has invalid persistent receipt state')
    state['transactions'].update({r['transaction_key']: r for r in commands})
    ledger = getattr(simulation, 'resource_ledger', None)
    from utopia.funding.accounting import NATIVE_TRANSFER_CATEGORIES, stable_id
    if any(getattr(actors[aid], 'resource_ledger', None) is not ledger
           for receipt in commands for aid in (receipt['command']['from_actor'], receipt['command']['to_actor'])):
        raise GraphRuntimeError('native actor accounting attachment differs from society ledger')
    if ledger is not None:
        for receipt in commands:
            command = receipt['command']
            for aid, category in ((command['from_actor'], NATIVE_TRANSFER_CATEGORIES[1]),
                                  (command['to_actor'], NATIVE_TRANSFER_CATEGORIES[0])):
                row = ledger.years.get(str(context.period), {}).get(aid)
                if row is None or row['closing_balance'] is not None:
                    raise GraphRuntimeError('native resource capability requires an open accounting year')
                eid = stable_id(context.period, aid, category, None, None, IMPLEMENTATION, receipt['transaction_key'])
                if ledger.event(eid) is not None:
                    raise GraphRuntimeError('resource ledger transfer exists without native causal receipt')
    touched = {aid for r in commands for aid in (r['command']['from_actor'], r['command']['to_actor'])}
    old = {aid: (actors[aid].resources, actors[aid].is_active) for aid in touched}
    ledger_before = deepcopy(ledger.__dict__) if ledger is not None else None
    try:
        if ledger is not None:
            ledger.enable_native_transfers()
        for receipt in commands:
            command = receipt['command']
            for aid, delta, category in (
                    (command['from_actor'], -command['amount'], NATIVE_TRANSFER_CATEGORIES[1]),
                    (command['to_actor'], command['amount'], NATIVE_TRANSFER_CATEGORIES[0])):
                actors[aid].update_resources(delta, category=category, year=context.period,
                    program=IMPLEMENTATION, reason=receipt['transaction_key'])
            if any(actors[aid].resources != balance for aid, balance in receipt['balances_after'].items()):
                raise GraphRuntimeError('actual native resource update differs from staged conserving transfer')
    except BaseException:
        for aid, (resources, active) in old.items():
            actors[aid].resources, actors[aid].is_active = resources, active
        if ledger is not None:
            ledger.__dict__.clear()
            ledger.__dict__.update(ledger_before)
        raise
    kernel._frame['native_resource_transactions'] = {
        **kernel._frame.get('native_resource_transactions', {}), **{r['transaction_key']: r for r in commands}}
    return MechanismResult(next_state=state, events=tuple(MechanismEvent(EVENT,
        actor_ids=tuple(dict.fromkeys((r['command']['from_actor'], r['command']['to_actor']))),
        payload=r) for r in commands))
