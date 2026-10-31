"""Native hard/soft institution example; no substitute scientific world."""
from dataclasses import replace

from . import ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from .code_mechanisms import CODE_IMPLEMENTATION, CODE_SCHEMA
from .native_kernel import WORLD_ARTIFACT
from .tensor_program import IMPLEMENTATION, SCHEMA


def addressed_selection_program():
    """Explicit policy: address threshold slots, branch, remember decisions.

    Algorithm is a developer example, not an assertion of scientific quality.
    Parameters and memory belong to the institution, not the world's physics.
    """
    def node(name, op, *args, **attrs): return {'id': name, 'op': op, 'args': list(args), 'attrs': attrs}
    return {'schema': SCHEMA, 'inputs': {'features': [-1, 2]},
        'parameters': {'keys': [[0.6, -0.2], [-0.3, 0.5]], 'thresholds': [[3.5], [4.5]],
                       'bias': 0.5, 'memory_cost': 0.01}, 'state': {'accepted_so_far': 0.0},
        'nodes': [node('keys-transposed', 'transpose', 'parameter:keys', dims=[0, 1]),
                  node('address-logits', 'matmul', 'input:features', 'keys-transposed'),
                  node('address', 'choose', 'address-logits'),
                  node('threshold-matrix', 'matmul', 'address', 'parameter:thresholds'),
                  node('threshold', 'column', 'threshold-matrix', index=0),
                  node('scores', 'column', 'input:features', index=0),
                  node('memory-penalty', 'mul', 'state:accepted_so_far', 'parameter:memory_cost'),
                  node('biased', 'add', 'threshold', 'parameter:bias'),
                  node('effective-threshold', 'add', 'biased', 'memory-penalty'),
                  node('margin', 'sub', 'scores', 'effective-threshold'),
                  node('accept', 'gate', 'margin'), node('count', 'sum', 'accept'),
                  node('next-memory', 'add', 'state:accepted_so_far', 'count')],
        'outputs': {'accept': 'accept', 'scores': 'scores', 'addresses': 'address'},
        'updates': {'accepted_so_far': 'next-memory'}}


def tensor_selection_system(parent, *, image_id, program=None):
    """Python feature producer -> tensor institution -> Python native consumer.

    Identity-carrying protocols are new; research/review/publication/funding are
    native. All tensor actions actually commit to conference/PaperTracker state.
    """
    producer_source = """def step(context):
    world = context['inputs']['observations'][0]['payload']
    records, values = [], []
    for conference in world['conferences']['conferences']:
        for paper in conference['submitted_papers']:
            reviews = conference['reviews'].get(paper['id'], [])
            score = sum(r['overall_score'] for r in reviews) / len(reviews) if reviews else 0.0
            records.append({'paper_id': paper['id'], 'conference_id': conference['conference_id']})
            values.append([score, len(reviews)])
    return {'outputs': {'features': [{'payload': {'values': values, 'records': records}}],
                        'world': [{'payload': world}]},
            'state': {'cycles': context['state'].get('cycles', 0) + 1}}
"""
    consumer_source = """def step(context):
    accepts = context['inputs']['accept'][0]['payload']
    scores = context['inputs']['scores'][0]['payload']
    if accepts['records'] != scores['records']:
        raise ValueError('decision tensors lost paper identity alignment')
    decisions = [{'payload': {'paper_id': row['paper_id'], 'conference_id': row['conference_id'],
        'decision': 'accept' if accepts['values'][i] >= 0.5 else 'reject',
        'final_score': scores['values'][i]}} for i,row in enumerate(accepts['records'])]
    return {'outputs': {'decisions': decisions or [{'payload': {'empty_cycle': True}}],
        'next': [{'payload': {'year': context['period']}}],
        'world': [{'payload': context['inputs']['observations'][0]['payload']}]},
        'state': {'cycles': context['state'].get('cycles', 0) + 1}}
"""
    feature_type, decision_type = 'native-tensor-feature-frame', 'native-tensor-decision-frame'
    def code(label, source, inputs, outputs):
        return {'runtime_image_id': image_id, 'code_artifact': {'schema': CODE_SCHEMA, 'label': label,
            'source': source, 'inputs': {p.port_id: {'type': 'object'} for p in inputs},
            'outputs': {p.port_id: {'type': 'object'} for p in outputs}, 'state_schema': {'type': 'object'}}}
    producer_inputs = (PortSpec('observations', ChannelKind.ARTIFACT, WORLD_ARTIFACT),)
    producer_outputs = (PortSpec('features', ChannelKind.ARTIFACT, feature_type), PortSpec('world', ChannelKind.ARTIFACT, WORLD_ARTIFACT))
    producer = MechanismSpec('native-feature-extractor', MechanismFamily.CUSTOM, CODE_IMPLEMENTATION,
        inputs=producer_inputs, outputs=producer_outputs,
        parameters=code('Native review feature extraction', producer_source, producer_inputs, producer_outputs))
    program = program or addressed_selection_program()
    tensor = MechanismSpec('addressed-selection', MechanismFamily.CUSTOM, IMPLEMENTATION,
        inputs=(PortSpec('features', ChannelKind.ARTIFACT, feature_type),),
        outputs=tuple(PortSpec(p, ChannelKind.ARTIFACT, decision_type) for p in program['outputs']),
        parameters={'program': program, 'input_bindings': {'features': {'port': 'features', 'path': '/values'}}})
    old = next(n for n in parent.mechanisms if n.mechanism_id == 'world.selection')
    consumer_inputs = (*old.inputs, PortSpec('accept', ChannelKind.ARTIFACT, decision_type),
        PortSpec('scores', ChannelKind.ARTIFACT, decision_type), PortSpec('observations', ChannelKind.ARTIFACT, WORLD_ARTIFACT))
    consumer = replace(old, implementation=CODE_IMPLEMENTATION, inputs=consumer_inputs,
        parameters=code('Native tensor decision consumer', consumer_source, consumer_inputs, old.outputs))
    def edge(source, port, target, target_port): return ConnectionSpec(source, port, target, target_port, ChannelKind.ARTIFACT)
    return replace(parent, artifact_types=(*parent.artifact_types, ArtifactTypeSpec(feature_type), ArtifactTypeSpec(decision_type)),
        mechanisms=(*(consumer if n.mechanism_id == old.mechanism_id else n for n in parent.mechanisms), producer, tensor),
        schedules=(*parent.schedules, ScheduleSpec(producer.mechanism_id, 125), ScheduleSpec(tensor.mechanism_id, 130)),
        connections=(*parent.connections, edge('world.review', 'world', producer.mechanism_id, 'observations'),
            edge(producer.mechanism_id, 'features', tensor.mechanism_id, 'features'),
            edge(producer.mechanism_id, 'world', consumer.mechanism_id, 'observations'),
            edge(tensor.mechanism_id, 'accept', consumer.mechanism_id, 'accept'),
            edge(tensor.mechanism_id, 'scores', consumer.mechanism_id, 'scores')))
