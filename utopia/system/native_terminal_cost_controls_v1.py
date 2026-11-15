"""Explicit developer opportunity control, not a model-discovered institution.

No active campaign, native cost rule, objective or optimizer is changed. This
authored source hypothesis still needs sandbox/public-path and real-world checks.
"""
from copy import deepcopy
from dataclasses import replace

from utopia.optimization.native_workflow_domain_v4 import execution_order
from .validation import validate_system_spec

HEADER='def step(context):\n'
TERMINAL_BRANCH='''    if context['period'] == TERMINAL_PERIOD:
        world = context['inputs']['world'][0]['payload']
        actors = [a for a in world['ecosystem']['agents'] if a['can_author'] and a['is_active']]
        commands = []
        if actors:
            banker = max(actors, key=lambda a: (a['resources'], a['id']))
            for actor in sorted(actors, key=lambda a: a['id']):
                if actor['id'] != banker['id'] and actor['resources'] > 0:
                    commands.append({'payload': {
                        'transaction_id': 'terminal-consolidation-' + str(context['period']) + '-' + actor['id'],
                        'from_actor': actor['id'], 'to_actor': banker['id'], 'amount': actor['resources']}})
        return {'outputs': {'funds': commands},
            'state': {'period': context['period'], 'transfers_requested': len(commands)}}
'''


def terminal_consolidation_control(parent,*,terminal_year):
    """One literal source change; never repair/reorder an incompatible parent.

    Existing original publication/funding precede the transfer, and original
    costs/close follow. Outside the new early branch the source body is literal,
    not a claim that all native prompts/trajectories must match. The general
    design language is not restricted by this developer control constructor.
    """
    if type(terminal_year) is not int or terminal_year<1:
        raise ValueError('explicit positive integer terminal year required')
    order=execution_order(parent); ranks={name:i for i,name in enumerate(order)}
    identities=('world.publication','world.funding','developer-liquidity-director',
                'developer-liquidity-effects','world.costs','world.close')
    if (any(name not in ranks for name in identities)
            or [ranks[name] for name in identities]!=sorted(ranks[name] for name in identities)):
        raise ValueError('exact post-publication/funding, pre-cost/close control window required')
    nodes={n.mechanism_id:n for n in parent.mechanisms}
    producer=nodes['developer-liquidity-director']; receiver=nodes['developer-liquidity-effects']
    if (producer.implementation!='code.python.v1'
            or receiver.implementation!='native.world.resource-transfers.v1'):
        raise ValueError('actual existing code producer and conserving native receiver required')
    required={('world.funding','world','developer-liquidity-director','world',0),
              ('developer-liquidity-director','funds','developer-liquidity-effects','transfers',0)}
    actual={(e.source_mechanism,e.source_port,e.target_mechanism,e.target_port,e.latency)
            for e in parent.connections}
    if not required<=actual: raise ValueError('exact literal post-funding snapshot and transfer edges required')
    parameters=deepcopy(producer.parameters); source=parameters['code_artifact']['source']
    if not source.startswith(HEADER) or source.count(HEADER)!=1:
        raise ValueError('explicit known single-step source prefix required; no automatic source repair')
    parameters['code_artifact']['source']=(HEADER+TERMINAL_BRANCH.replace('TERMINAL_PERIOD',str(terminal_year))
                                          +source[len(HEADER):])
    new=replace(producer,parameters=parameters)
    candidate=replace(parent,mechanisms=tuple(new if n.mechanism_id==producer.mechanism_id else n
                                            for n in parent.mechanisms))
    validate_system_spec(candidate).require_valid()
    return candidate
