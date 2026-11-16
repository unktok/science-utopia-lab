"""Bind a named native topic-rule family to existing black-box ask/tell search.

This supplies a restricted comparator, not the free institution search space.
No new simulator, loss, optimizer, candidate repair or measured reference is
invented. A scientific caller must bind its real native evaluation separately.
"""
from .native_parameter_space_v1 import NativeParameterSpace, parameter_domain
from .native_institution_workflow_domain_v6 import SCOPE
from utopia.system.native_topic_priority_controls import topic_priority_control


def topic_priority_space(related_control):
    """Expose every displayed topic weight in [-1,1], keeping the rule literal.

    All topics receive an explicit zero before declaring numeric coordinates;
    the adapter never adds fields to a submitted proposal. The installed rule
    still prioritizes original duration, so weights cannot shorten a project or
    select an ineligible topic. Equal zero weights reproduce lexical tie order.
    This newly constructed anchor is not automatically a measured warm start.

    Continuous priorities encode relative ordering (with lexical ties). Their
    bounds are a comparator parameterization, not an empirical optimum or a
    limitation on separately declared free-program authors.
    """
    producer = next(n for n in related_control.mechanisms
                    if n.mechanism_id == 'developer-catalog-agenda')
    topics = sorted({d['topic'] for d in producer.parameters['catalog']['directions']})
    anchor = topic_priority_control(related_control, priorities={t: 0. for t in topics})
    pointer = lambda t: t.replace('~', '~0').replace('/', '~1')
    coordinates = [{'mechanism_id': producer.mechanism_id,
                    'path': '/parameters/topic_priorities/' + pointer(t),
                    'integer': False, 'lower': -1., 'upper': 1.} for t in topics]
    return NativeParameterSpace(anchor, parameter_domain(anchor, coordinates,
                                                        world_law_scope=SCOPE))
