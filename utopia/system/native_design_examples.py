"""Declared developer-authored examples, not a required institution grammar."""
from dataclasses import replace

from .model import ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from .code_mechanisms import CODE_IMPLEMENTATION, CODE_SCHEMA
from .design_patch import make_patch
from .native_kernel import WORLD_ARTIFACT


def deliberation_patch(parent, *, image_id, threshold=4.0, retain_review=True):
    """Joint new protocol/producer/consumer/source/wiring edit on native papers.

    Acceptance threshold is only an explicit engineering design coordinate.
    These functions are examples, not an asserted useful scientific institution.
    """
    protocol = 'native-deliberation'
    producer_code = """def step(context):
    world = context['inputs']['observations'][0]['payload']
    proposals = []
    for conference in world['conferences']['conferences']:
        for paper in conference['submitted_papers']:
            reviews = conference['reviews'].get(paper['id'], [])
            score = sum(r['overall_score'] for r in reviews) / len(reviews) if reviews else 0.0
            proposals.append({'paper_id': paper['id'], 'conference_id': conference['conference_id'], 'score': score})
    return {'outputs': {'deliberations': [{'payload': {'world': world, 'proposals': proposals}}]},
            'state': {'cycles': context['state'].get('cycles', 0) + 1}}
"""
    consumer_code = """def step(context):
    deliberation = context['inputs']['deliberations'][0]['payload']
    decisions = [{'payload': {'paper_id': p['paper_id'], 'conference_id': p['conference_id'],
                  'final_score': p['score'], 'decision': 'accept' if p['score'] >= context['parameters']['threshold'] else 'reject'}}
                 for p in deliberation['proposals']]
    if not decisions:
        decisions = [{'payload': {'empty_cycle': True}}]
    return {'outputs': {'next': [{'payload': {'year': context['period']}}],
            'world': [{'payload': deliberation['world']}], 'decisions': decisions},
            'state': {'cycles': context['state'].get('cycles', 0) + 1}}
"""
    def artifact(label, source, inputs, outputs):
        return {'schema': CODE_SCHEMA, 'label': label, 'source': source,
                'inputs': {p.port_id: {'type': 'object'} for p in inputs},
                'outputs': {p.port_id: {'type': 'object'} for p in outputs}, 'state_schema': {'type': 'object'}}
    inputs = (PortSpec('observations', ChannelKind.ARTIFACT, WORLD_ARTIFACT),)
    outputs = (PortSpec('deliberations', ChannelKind.ARTIFACT, protocol),)
    producer = MechanismSpec('deliberation-assembly', MechanismFamily.CUSTOM, CODE_IMPLEMENTATION,
        inputs=inputs, outputs=outputs, parameters={'runtime_image_id': image_id,
            'code_artifact': artifact('Native deliberation producer', producer_code, inputs, outputs)})
    old = next(n for n in parent.mechanisms if n.mechanism_id == 'world.selection')
    inputs = (*old.inputs, PortSpec('deliberations', ChannelKind.ARTIFACT, protocol))
    consumer = replace(old, implementation=CODE_IMPLEMENTATION, inputs=inputs, parameters={
        'runtime_image_id': image_id, 'threshold': float(threshold),
        'code_artifact': artifact('Native deliberation consumer', consumer_code, inputs, old.outputs)})
    nodes = [consumer if n.mechanism_id == old.mechanism_id else n for n in parent.mechanisms]
    schedules = list(parent.schedules)
    edges = list(parent.connections)
    observe = 'world.review'
    if not retain_review:
        nodes = [n for n in nodes if n.mechanism_id != 'world.review']
        schedules = [s for s in schedules if s.mechanism_id != 'world.review']
        edges = [e for e in edges if 'world.review' not in (e.source_mechanism, e.target_mechanism)]
        edges.append(ConnectionSpec('world.costs', 'next', 'world.selection', 'after', ChannelKind.SIGNAL))
        observe = 'world.costs'
    edges.extend((ConnectionSpec(observe, 'world', producer.mechanism_id, 'observations', ChannelKind.ARTIFACT),
                  ConnectionSpec(producer.mechanism_id, 'deliberations', old.mechanism_id, 'deliberations', ChannelKind.ARTIFACT)))
    child = replace(parent, mechanisms=(*nodes, producer), schedules=(*schedules, ScheduleSpec(producer.mechanism_id, 125)),
                    connections=tuple(edges), artifact_types=(*parent.artifact_types, ArtifactTypeSpec(protocol)))
    before, after = parent.to_dict(), child.to_dict()
    return make_patch(parent, [{'op': 'replace', 'path': '/' + key, 'value': after[key]}
                              for key in ('mechanisms', 'connections', 'schedules', 'artifact_types')
                              if before[key] != after[key]], rationale='Joint native producer/consumer and protocol; declared developer example')
