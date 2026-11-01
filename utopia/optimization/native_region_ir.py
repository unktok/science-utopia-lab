"""Scoped, explicit graph authoring; syntax lowering never invents institutions."""
from __future__ import annotations

from jsonschema import Draft202012Validator

from utopia.optimization.native_region_design import compile_region, region_boundary
from utopia.system import ChannelKind
from utopia.system.code_mechanisms import sha
from utopia.system.design_patch import clone


def boundary_contract(parent, removed_nodes):
    """Stable local aliases for every actual external source and destination."""
    _, incoming, outgoing, lower, upper = region_boundary(parent, removed_nodes)
    nodes = {n.mechanism_id: n for n in parent.mechanisms}
    result = {'inputs': {}, 'exports': {}, 'phase_interval': [lower, upper]}
    for edges, key, direction, side in ((incoming, 'inputs', 'outputs', 'source'),
                                         (outgoing, 'exports', 'inputs', 'target')):
        endpoints = sorted({(getattr(c, side + '_mechanism'), getattr(c, side + '_port')) for c in edges})
        for mechanism, port_id in endpoints:
            alias = port_id
            suffix = 1
            while alias in result[key]:
                suffix += 1
                alias = port_id + '-' + str(suffix)
            port = next(p for p in getattr(nodes[mechanism], direction) if p.port_id == port_id)
            result[key][alias] = {'mechanism': mechanism, 'port': port_id,
                'channel': port.channel.value, 'artifact_type': port.artifact_type}
    return result


def region_ir_schema(contract):
    """A compact graph IR, not a catalog of possible institutional rules."""
    name = {'type': 'string', 'pattern': '^[a-zA-Z][a-zA-Z0-9_.-]{0,79}$'}
    reference = {'type': 'string', 'pattern': '^(boundary:[a-zA-Z][a-zA-Z0-9_.-]*|node:[a-zA-Z][a-zA-Z0-9_.-]*:[a-zA-Z][a-zA-Z0-9_.-]*)$'}
    obj = {'type': 'object'}
    def exact(fields):
        return {'type': 'object', 'required': list(fields), 'properties': fields, 'additionalProperties': False}
    source_list = {'type': 'array', 'minItems': 1, 'maxItems': 16, 'uniqueItems': True, 'items': reference}
    inp = exact({'sources': source_list, 'required': {'type': 'boolean'}, 'schema': obj})
    out = exact({'channel': {'enum': [c.value for c in ChannelKind]},
        'artifact_type': {'type': ['string', 'null']}, 'required': {'type': 'boolean'}, 'schema': obj})
    node = exact({'id': name,
        'inputs': {'type': 'object', 'propertyNames': name, 'maxProperties': 32, 'additionalProperties': inp},
        'outputs': {'type': 'object', 'propertyNames': name, 'maxProperties': 32, 'additionalProperties': out},
        'parameters': obj, 'python_code': {'type': 'string'}, 'state_schema': obj})
    return exact({'rationale': {'type': 'string'},
        'nodes': {'type': 'array', 'minItems': 1, 'maxItems': min(6, contract['phase_interval'][1] - contract['phase_interval'][0] - 1), 'items': node},
        'exports': exact({alias: source_list for alias in contract['exports']})})


def lower_region_ir(parent, generated, *, removed_nodes):
    """Lower only explicit source references and array order. Preserve Python bytes."""
    contract = boundary_contract(parent, removed_nodes)
    Draft202012Validator(region_ir_schema(contract)).validate(generated)
    namespace = 'generated-' + sha({'parent': parent.fingerprint, 'ir': generated})[:12]
    declared = {n['id']: n for n in generated['nodes']}
    if len(declared) != len(generated['nodes']):
        raise ValueError('duplicate scoped node IDs')
    ids = {key: namespace + '.' + key for key in declared}
    positions = {n['id']: i for i, n in enumerate(generated['nodes'])}
    edges, nodes = [], []

    def resolve(ref):
        parts = ref.split(':')
        if parts[0] == 'boundary':
            if parts[1] not in contract['inputs']:
                raise ValueError('unknown explicit boundary input ' + ref)
            return clone(contract['inputs'][parts[1]])
        _, local, port = parts
        if local not in declared or port not in declared[local]['outputs']:
            raise ValueError('unknown explicit local output ' + ref)
        return {'mechanism': ids[local], 'port': port, **clone(declared[local]['outputs'][port])}

    def connect(source, mechanism, port):
        edges.append({'source_mechanism': source['mechanism'], 'source_port': source['port'],
            'target_mechanism': mechanism, 'target_port': port, 'channel': source['channel'], 'latency': 0})

    lower, upper = contract['phase_interval']
    for i, item in enumerate(generated['nodes']):
        if set(item['inputs']) & set(item['outputs']):
            raise ValueError('input/output port IDs must be distinct; Python source is never rewritten')
        ins, outs, input_schemas, output_schemas = [], [], {}, {}
        for port, data in sorted(item['inputs'].items()):
            sources = [resolve(ref) for ref in data['sources']]
            signatures = {(s['channel'], s['artifact_type']) for s in sources}
            if len(signatures) != 1:
                raise ValueError('merged sources disagree in channel/artifact type')
            for ref, source in zip(data['sources'], sources):
                if ref.startswith('node:') and positions[ref.split(':')[1]] >= i:
                    raise ValueError('explicit internal wire must follow chosen node array order')
                connect(source, ids[item['id']], port)
            channel, artifact_type = next(iter(signatures))
            ins.append({'port_id': port, 'channel': channel, 'artifact_type': artifact_type, 'required': data['required']})
            input_schemas[port] = clone(data['schema'])
        for port, data in sorted(item['outputs'].items()):
            outs.append({'port_id': port, 'channel': data['channel'], 'artifact_type': data['artifact_type'], 'required': data['required']})
            output_schemas[port] = clone(data['schema'])
        nodes.append({'mechanism_id': ids[item['id']], 'phase': lower + (i + 1) * (upper - lower) // (len(generated['nodes']) + 1),
            'family': 'custom', 'inputs': ins, 'outputs': outs, 'parameters': clone(item['parameters']),
            'algorithm_name': item['id'], 'python_code': item['python_code'],
            'input_schemas': input_schemas, 'output_schemas': output_schemas, 'state_schema': clone(item['state_schema'])})
    for alias, refs in sorted(generated['exports'].items()):
        target = contract['exports'][alias]
        for ref in refs:
            if not ref.startswith('node:'):
                raise ValueError('exports must explicitly reference authored node outputs')
            source = resolve(ref)
            if (source['channel'], source['artifact_type']) != (target['channel'], target['artifact_type']):
                raise ValueError('explicit export channel/artifact type disagrees with native boundary ' + alias)
            connect(source, target['mechanism'], target['port'])
    return {'rationale': generated['rationale'], 'nodes': nodes, 'connections': edges}


def compile_region_ir(parent, generated, *, removed_nodes, image_id):
    return compile_region(parent, lower_region_ir(parent, generated, removed_nodes=removed_nodes),
        removed_nodes=removed_nodes, image_id=image_id)
