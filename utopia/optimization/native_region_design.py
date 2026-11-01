"""Joint source/protocol/wiring invention inside an explicit native graph cut.

No institution-algorithm catalog. A manifest declares arbitrary Python nodes,
payload schemas, edges and order. This initial isolated probe supports annual
zero-delay DAG regions, not arbitrary live-society migration or cross-year edges.
"""
from dataclasses import replace
import math

from utopia.optimization.native_code_trace import validate_record
from utopia.system import (ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily,
    MechanismSpec, PortSpec, ScheduleSpec, validate_system_spec)
from utopia.system.code_mechanisms import CODE_IMPLEMENTATION, CODE_SCHEMA, sha, validate_code_artifact
from utopia.system.design_patch import clone, make_patch, apply_design_patch


def compile_region(parent, manifest, *, removed_nodes, image_id):
    if set(manifest) != {'rationale', 'nodes', 'connections'} or not isinstance(manifest['rationale'], str):
        raise ValueError('exact region rationale/nodes/connections required')
    if not 1 <= len(manifest['nodes']) <= 6 or not 1 <= len(manifest['connections']) <= 32:
        raise ValueError('bounded region node/edge budgets required')
    removed = set(removed_nodes)
    if not removed or not removed <= {n.mechanism_id for n in parent.mechanisms}:
        raise ValueError('declared existing native region required')
    incoming = [c for c in parent.connections if c.source_mechanism not in removed and c.target_mechanism in removed]
    outgoing = [c for c in parent.connections if c.source_mechanism in removed and c.target_mechanism not in removed]
    phases = {s.mechanism_id: s.phase for s in parent.schedules}
    lower = max(phases[c.source_mechanism] for c in incoming)
    upper = min(phases[c.target_mechanism] for c in outgoing)
    nodes, schedules = [], []
    artifacts = {a.artifact_type_id: a for a in parent.artifact_types}
    for value in manifest['nodes']:
        expected = {'mechanism_id', 'family', 'phase', 'inputs', 'outputs', 'parameters',
            'algorithm_name', 'python_code', 'input_schemas', 'output_schemas', 'state_schema'}
        if set(value) != expected or type(value['phase']) is not int or not lower < value['phase'] < upper:
            raise ValueError('exact node fields and phase inside the native boundary required')
        def ports(direction):
            result = tuple(PortSpec(p['port_id'], ChannelKind(p['channel']), p.get('artifact_type'), p.get('required', True)) for p in value[direction])
            for p in result:
                if p.artifact_type and p.artifact_type not in artifacts:
                    artifacts[p.artifact_type] = ArtifactTypeSpec(p.artifact_type)
            return result
        ins, outs = ports('inputs'), ports('outputs')
        artifact = {'schema': CODE_SCHEMA, 'label': value['algorithm_name'], 'source': value['python_code'],
            'inputs': clone(value['input_schemas']), 'outputs': clone(value['output_schemas']), 'state_schema': clone(value['state_schema'])}
        validate_code_artifact(artifact)
        if set(artifact['inputs']) != {p.port_id for p in ins} or set(artifact['outputs']) != {p.port_id for p in outs}:
            raise ValueError('generated port declarations and code payload schemas disagree')
        if {'code_artifact', 'runtime_image_id'} & set(value['parameters']):
            raise ValueError('implementation/runtime fields belong to the mechanical compiler')
        nodes.append(MechanismSpec(value['mechanism_id'], MechanismFamily(value['family']), CODE_IMPLEMENTATION,
            inputs=ins, outputs=outs, parameters={**clone(value['parameters']), 'code_artifact': artifact, 'runtime_image_id': image_id}))
        schedules.append(ScheduleSpec(value['mechanism_id'], value['phase']))
    ids = {n.mechanism_id for n in nodes}
    if len(ids) != len(nodes) or ids & {n.mechanism_id for n in parent.mechanisms if n.mechanism_id not in removed}:
        raise ValueError('region node identities collide with the retained native world')
    entries = {(c.source_mechanism, c.source_port, c.channel) for c in incoming}
    exits = {(c.target_mechanism, c.target_port, c.channel) for c in outgoing}
    edges = []
    local_phases = {s.mechanism_id: s.phase for s in schedules}
    covered_exits = set()
    for value in manifest['connections']:
        c = ConnectionSpec(value['source_mechanism'], value['source_port'], value['target_mechanism'], value['target_port'],
            ChannelKind(value['channel']), value.get('latency', 0))
        if c.latency != 0:
            raise ValueError('this native-region probe supports zero-delay edges only')
        if c.source_mechanism not in ids:
            if c.target_mechanism not in ids or (c.source_mechanism, c.source_port, c.channel) not in entries:
                raise ValueError('edge reads outside the declared native boundary')
        elif c.target_mechanism not in ids:
            target = c.target_mechanism, c.target_port, c.channel
            if target not in exits:
                raise ValueError('edge writes outside the declared native boundary')
            covered_exits.add(target)
        elif local_phases[c.source_mechanism] >= local_phases[c.target_mechanism]:
            raise ValueError('region edges must follow strictly increasing phases')
        edges.append(c)
    if covered_exits != exits:
        raise ValueError('region does not reconnect every required native exit')
    child = replace(parent, mechanisms=tuple(n for n in parent.mechanisms if n.mechanism_id not in removed) + tuple(nodes),
        schedules=tuple(s for s in parent.schedules if s.mechanism_id not in removed) + tuple(schedules),
        artifact_types=tuple(artifacts.values()), connections=tuple(c for c in parent.connections
            if c.source_mechanism not in removed and c.target_mechanism not in removed) + tuple(edges),
        metadata={**parent.metadata, 'native_design_region': {'node_ids': sorted(ids), 'boundary_origin_nodes': sorted(removed)}})
    validate_system_spec(child).require_valid()
    before, after = parent.to_dict(), child.to_dict()
    patch = make_patch(parent, [{'op': 'replace', 'path': '/' + key, 'value': after[key]} for key in
        ('mechanisms', 'connections', 'schedules', 'artifact_types', 'metadata') if before[key] != after[key]], rationale=manifest['rationale'])
    return patch, apply_design_patch(parent, patch)


def probe_selection_region(parent, child, records, *, executor, original_node='world.selection'):
    """Execute generated internal protocols on exact recorded native boundaries."""
    old = next(n for n in parent.mechanisms if n.mechanism_id == original_node)
    if child.metadata['native_design_region']['boundary_origin_nodes'] != [original_node]:
        raise ValueError('this publication probe supports a single original selection cut')
    region = set(child.metadata['native_design_region']['node_ids'])
    nodes = {n.mechanism_id: n for n in child.mechanisms if n.mechanism_id in region}
    schedules = sorted((s for s in child.schedules if s.mechanism_id in region), key=lambda s: (s.phase, s.mechanism_id))
    memory, runs, seen, current_run = {}, [], set(), None
    for row in sorted(records, key=lambda r: (r['binding']['run_id'], r['context']['period'], r['bundle_sha256'])):
        validate_record(row)
        if row['artifact'] != old.parameters['code_artifact'] or row['binding']['system_fingerprint'] != parent.fingerprint:
            raise ValueError('selection probe boundary is not the actual parent implementation')
        period = row['context']['period']
        identity = row['binding']['run_id'], period, row['receipt']['context_sha256'], row['receipt']['result_sha256']
        if identity in seen:
            continue
        seen.add(identity)
        if current_run != row['binding']['run_id']:
            memory = {}
            current_run = row['binding']['run_id']
        boundary = {}
        for port, values in row['context']['inputs'].items():
            matching = [c for c in parent.connections if c.target_mechanism == original_node and c.target_port == port]
            if len(matching) != 1:
                raise ValueError('recorded selection input must identify one actual boundary edge')
            c = matching[0]
            boundary[(c.source_mechanism, c.source_port)] = clone(values)
        produced, executions = {}, []
        for schedule in schedules:
            node = nodes[schedule.mechanism_id]
            inputs = {p.port_id: [] for p in node.inputs}
            for c in child.connections:
                if c.target_mechanism == node.mechanism_id:
                    source = (c.source_mechanism, c.source_port)
                    values = produced.get(source) if c.source_mechanism in region else boundary.get(source)
                    if values is None:
                        raise ValueError('generated region has an unavailable native/internal input')
                    inputs[c.target_port].extend(clone(values))
            context = {'period': period, 'phase': schedule.phase,
                'random_seed': int(sha({'period': period, 'mechanism': node.mechanism_id, 'seed': child.initial_state.get('seed', 0)})[:16], 16),
                'state': memory.get(node.mechanism_id, {}), 'parameters': {k: clone(v) for k, v in node.parameters.items() if k not in {'code_artifact', 'runtime_image_id'}},
                'inputs': inputs}
            result = executor.execute(node.parameters['code_artifact'], context)
            memory[node.mechanism_id] = clone(result.result['state'])
            executions.append({'mechanism_id': node.mechanism_id, 'receipt': result.receipt})
            for port, values in result.result['outputs'].items():
                produced[(node.mechanism_id, port)] = [{**clone(v), 'source_mechanism': node.mechanism_id, 'emitted_period': period} for v in values]
        exits = {}
        for c in child.connections:
            if c.source_mechanism in region and c.target_mechanism not in region:
                exits.setdefault((c.target_mechanism, c.target_port), []).extend(produced[(c.source_mechanism, c.source_port)])
        worlds = [v['payload'] for values in row['context']['inputs'].values() for v in values
            if v['payload'].get('schema') == 'scienceutopia.native-world-observation.v1']
        if len(worlds) != 1:
            raise ValueError('actual pre-selection world snapshot required for native identity validation')
        expected = {p['id']: conf['conference_id'] for conf in worlds[0]['conferences']['conferences'] for p in conf['submitted_papers']}
        decisions = [v['payload'] for v in exits.get(('world.publication', 'decisions'), [])]
        if not expected:
            if decisions != [{'empty_cycle': True}]:
                raise ValueError('empty real native cycle requires exactly an empty-cycle marker')
        else:
            if len(decisions) != len(expected) or {d.get('paper_id') for d in decisions} != set(expected):
                raise ValueError('generated decisions must cover each real native paper exactly once')
            for d in decisions:
                score = d.get('final_score')
                if d.get('conference_id') != expected[d['paper_id']] or d.get('decision') not in {'accept', 'reject'} or type(score) not in (int, float) or not math.isfinite(score):
                    raise ValueError('generated decision has invalid native conference/decision/score')
        signals = exits.get(('world.publication', 'after'), [])
        if not signals or any(v['payload'].get('year') != period for v in signals):
            raise ValueError('publication control signal must refer to the actual native year')
        runs.append({'year': period, 'native_boundary_bundle_sha256': row['bundle_sha256'], 'code_executions': executions,
            'decisions': decisions, 'decisions_changed': decisions != [v['payload'] for v in row['result']['outputs']['decisions']]})
    if not runs:
        raise ValueError('nonempty actual native boundary probes required')
    return {'status': 'isolated-native-region-passed-not-native-evaluated', 'runs': runs,
        'scope': 'actual parent boundary inputs, generated internal messages and container source; fresh native rollout still required'}
