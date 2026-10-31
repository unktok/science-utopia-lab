"""A developer-authored baseline slot exposing native decision-code freedom.

This is not an invented institution. Candidate source is supplied by a designer.
The baseline retains review-score ranking/rate selection in the original world.
"""
from dataclasses import replace

from utopia.system import ChannelKind, ConnectionSpec, PortSpec, validate_system_spec
from utopia.system.code_mechanisms import CODE_IMPLEMENTATION, CODE_SCHEMA
from utopia.system.native_kernel import WORLD_ARTIFACT

RANK_RATE_SOURCE = """def step(context):
    world = context['inputs']['observations'][0]['payload']
    decisions = []
    for conf in world['conferences']['conferences']:
        scored = []
        for paper in conf['submitted_papers']:
            reviews = conf['reviews'].get(paper['id'], [])
            if not reviews:
                raise ValueError('actual submitted paper has no reviews')
            score = sum(r['overall_score'] for r in reviews) / len(reviews)
            scored.append((paper['id'], score))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        rates = context['parameters'].get('annual_rates')
        rate = rates[context['period'] - 1] if rates is not None else conf['acceptance_rate']
        slots = max(1, round(len(scored) * rate))
        for index, (paper_id, score) in enumerate(scored):
            decisions.append({'payload': {'paper_id': paper_id, 'conference_id': conf['conference_id'],
                'final_score': score, 'decision': 'accept' if index < slots else 'reject'}})
    if not decisions:
        decisions = [{'payload': {'empty_cycle': True}}]
    return {'outputs': {'next': [{'payload': {'year': context['period']}}],
        'world': [{'payload': world}], 'decisions': decisions},
        'state': {'cycles': context['state'].get('cycles', 0) + 1}}
"""


def selection_source_slot(parent, *, image_id, annual_rates=None):
    original = next(n for n in parent.mechanisms if n.mechanism_id == 'world.selection')
    inputs = (*original.inputs, PortSpec('observations', ChannelKind.ARTIFACT, WORLD_ARTIFACT))
    parameters = {'runtime_image_id': image_id, 'code_artifact': {'schema': CODE_SCHEMA,
        'label': 'Developer native rank/rate source slot', 'source': RANK_RATE_SOURCE,
        'inputs': {p.port_id: {'type': 'object'} for p in inputs},
        'outputs': {p.port_id: {'type': 'object'} for p in original.outputs}, 'state_schema': {'type': 'object'}}}
    if annual_rates is not None:
        if not annual_rates or any(type(r) not in (int, float) or not 0 <= r <= 1 for r in annual_rates):
            raise ValueError('explicit annual decision rates must be finite in [0,1]')
        parameters['annual_rates'] = list(annual_rates)
    node = replace(original, implementation=CODE_IMPLEMENTATION, inputs=inputs, parameters=parameters)
    result = replace(parent, mechanisms=tuple(node if n.mechanism_id == original.mechanism_id else n for n in parent.mechanisms),
        connections=(*parent.connections, ConnectionSpec('world.review', 'world', 'world.selection', 'observations', ChannelKind.ARTIFACT)))
    validate_system_spec(result).require_valid()
    return result
