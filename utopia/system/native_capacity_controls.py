"""Explicit same-authority developer allocation references, not inventions.

No extra physics, host allocation or objective-dependent adoption gate. The
policy runs as ordinary code in the same isolated executor as authored systems.
"""
from copy import deepcopy
from dataclasses import replace

from .native_liquidity_controls import liquidity_control
from .validation import validate_system_spec

SOURCE = '''def step(context):
    world = context['inputs']['world'][0]['payload']
    actors = [a for a in world['ecosystem']['agents'] if a['can_author'] and a['is_active']]
    balances = {a['id']: a['resources'] for a in actors}
    reserve = context['parameters']['reserve_units']
    by_id = {a['id']: a for a in actors}
    def priority(identity):
        if context['parameters']['allocation_rule'] == 'completion-priority':
            end = by_id[identity]['project_end_year']
            remaining = max(0, end - context['period']) if end > 0 else 1000000000
            return (remaining, -balances[identity], identity)
        return (0, -balances[identity], identity)
    recipients = sorted((k for k in balances if balances[k] < reserve), key=priority)
    donors = sorted((k for k in balances if balances[k] > reserve), key=lambda k: (-balances[k], k))
    commands = []
    for recipient in recipients:
        need = max(0, int(reserve - balances[recipient]))
        available = sum(max(0, int(balances[k] - reserve)) for k in donors)
        if not need or available < need:
            continue
        for donor in donors:
            amount = min(max(0, int(balances[donor] - reserve)), max(0, int(reserve - balances[recipient])))
            if amount:
                commands.append({'payload': {'transaction_id': 'capacity-reserve-' + str(len(commands)),
                    'from_actor': donor, 'to_actor': recipient, 'amount': amount}})
                balances[donor] -= amount
                balances[recipient] += amount
    return {'outputs': {'funds': commands}, 'state': {'period': context['period'],
        'allocation_rule': context['parameters']['allocation_rule'], 'transfers_requested': len(commands)}}
'''


def capacity_allocation_control(anchor, image_id, *, rule, reserve_units=21):
    """Conserving full-reserve rescue; prioritize proximity or project dates.

    Whole-unit surplus above21 can raise an affordable active researcher to21
    before native annual costs. Proximity minimizes the immediate transfer per
    rescued actor; completion-priority orders actual native end dates first.
    Neither rule guarantees activity, output or optimality.21 is an explicit
    developer policy parameter, not a runtime law or hidden scientific veto.
    No pooled fund or resource minting is introduced. Partial unfunded rescues
    are skipped by this rule, not replaced by a host fallback.
    """
    if rule not in ('reserve-proximity', 'completion-priority'):
        raise ValueError('explicit capacity allocation rule required')
    if type(reserve_units) is not int or not 1 <= reserve_units <= 1000000:
        raise ValueError('positive bounded whole-unit developer reserve required')
    spec = liquidity_control(anchor, image_id)
    nodes = []
    for node in spec.mechanisms:
        if node.mechanism_id != 'developer-liquidity-director':
            nodes.append(node); continue
        parameters = deepcopy(node.parameters)
        parameters.update(allocation_rule=rule, reserve_units=reserve_units)
        parameters['code_artifact'].update(source=SOURCE,
            label='Developer '+rule+' reserve rule, not autonomous invention')
        nodes.append(replace(node, parameters=parameters))
    result = replace(spec, mechanisms=tuple(nodes))
    validate_system_spec(result).require_valid()
    return result
