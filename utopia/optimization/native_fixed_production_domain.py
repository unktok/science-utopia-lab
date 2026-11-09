"""Explicit prospective pilot domain, not a global institutional merit gate.

Retain the original production/calendar/accounting stages while freely editing
institutions around them. Historical project-amending domains stay unchanged.
"""
from collections import Counter
from utopia.system.native_migration import native_execution_nodes

SCOPE='fixed-native-production-v1'
FREE_NATIVE={'native.phase.review.v1','native.phase.selection.v1'}


def fixed_nodes(anchor):
    return {n.mechanism_id:n for n in anchor.mechanisms
        if n.implementation.startswith(('native.phase.','native.activity.'))
        and n.implementation not in FREE_NATIVE}


def scope_description(anchor):
    return ('This prospective pilot fixes these native production/calendar/accounting nodes '
        'and their schedules: '+', '.join(sorted(fixed_nodes(anchor)))+'. '
        'Do not duplicate/wrap those effects, replace base-plan origins, add plan-amendment '
        'authority, grant native.project, or change the pinned code image. '
        'Other institutional code, entities, protocols, memory, wiring and institutional '
        'schedules may change. Review removal and all-accept/all-reject selection are legal. '
        'This is an explicit design domain, not an outcome, novelty or fairness veto.')


def require_fixed_production(anchor,candidate):
    protected=fixed_nodes(anchor)
    nodes={n.mechanism_id:n for n in candidate.mechanisms}
    for identity,node in protected.items():
        if nodes.get(identity)!=node:
            raise ValueError('pilot fixes native production/accounting contract: '+identity)
    schedules=lambda s,identity:[v for v in s.schedules if v.mechanism_id==identity]
    for identity in protected:
        if schedules(candidate,identity)!=schedules(anchor,identity):
            raise ValueError('pilot fixes native production/accounting schedule: '+identity)
    # Arbitrary code/process graphs cannot reintroduce a second copy of a
    # protected native effect under another ID or wrapped delegate.
    for node in native_execution_nodes(candidate):
        if (node.implementation.startswith(('native.phase.','native.activity.'))
                and node.implementation not in FREE_NATIVE
                and protected.get(node.mechanism_id)!=node):
            raise ValueError('pilot cannot duplicate or replace native production effects')
        grants=node.parameters.get('capabilities')
        if grants is not None:
            if (not isinstance(grants,dict) or not isinstance(grants.get('bootstrap'),list)
                    or not isinstance(grants.get('roles'),dict)
                    or any(not isinstance(v,list) for v in grants['roles'].values())):
                raise ValueError('explicit capability lists required in fixed-production pilot')
            if any('native.project' in v for v in [grants['bootstrap'],*grants['roles'].values()]):
                raise ValueError('project reassignment is outside this declared pilot domain')
    # The native base plan cannot be swapped for an invented/shorter project.
    # The graph still permits arbitrary information/selection paths and new
    # institutional entities. A future production-design domain may relax this.
    plan_ports={('research-plan-effects','plans'),('research-plan-effects','amendments'),
        ('world.collaboration','plans'),('world.submission','plans')}
    incoming=lambda s: [e for e in s.connections if (e.target_mechanism,e.target_port) in plan_ports]
    if Counter(incoming(candidate))!=Counter(incoming(anchor)):
        raise ValueError('pilot fixes actual native plan origin and amendment authority')
    for node in native_execution_nodes(candidate):
        if node.implementation=='code.python.v1':
            images={n.parameters['runtime_image_id'] for n in native_execution_nodes(anchor)
                    if n.implementation=='code.python.v1'}
            if node.parameters.get('runtime_image_id') not in images:
                raise ValueError('pilot code must use the predeclared pinned runtime image')
    return True
