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
from utopia.system.code_mechanisms import (CODE_IMPLEMENTATION, CODE_SCHEMA, sha,
    validate_code_artifact, validate_code_result)
from utopia.system.design_patch import clone, make_patch, apply_design_patch


def region_boundary(parent, removed_nodes):
    """Explicit open graph cut; names/families do not select an algorithm."""
    removed = set(removed_nodes)
    if not removed or not removed <= {n.mechanism_id for n in parent.mechanisms}:
        raise ValueError('declared existing native region required')
    incoming = [c for c in parent.connections if c.source_mechanism not in removed and c.target_mechanism in removed]
    outgoing = [c for c in parent.connections if c.source_mechanism in removed and c.target_mechanism not in removed]
    phases = {s.mechanism_id: s.phase for s in parent.schedules}
    if any(c.latency != 0 for c in incoming + outgoing):
        raise ValueError('recorded region boundary currently requires zero-delay external edges')
    lower = max((phases[c.source_mechanism] for c in incoming), default=-1)
    upper = min((phases[c.target_mechanism] for c in outgoing), default=max(phases.values()) + 20)
    if upper <= lower + 1:
        raise ValueError('native boundary has no available strictly ordered phase interval')
    return removed, incoming, outgoing, lower, upper


def compile_region(parent, manifest, *, removed_nodes, image_id):
    if set(manifest) != {'rationale', 'nodes', 'connections'} or not isinstance(manifest['rationale'], str):
        raise ValueError('exact region rationale/nodes/connections required')
    if not 1 <= len(manifest['nodes']) <= 6 or not 0 <= len(manifest['connections']) <= 32:
        raise ValueError('bounded region node/edge budgets required')
    removed, incoming, outgoing, lower, upper = region_boundary(parent, removed_nodes)
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
    initial = clone(parent.initial_state)
    if 'mechanism_states' in initial:
        initial['mechanism_states'] = {k: v for k, v in initial['mechanism_states'].items() if k not in removed}
    child = replace(parent, mechanisms=tuple(n for n in parent.mechanisms if n.mechanism_id not in removed) + tuple(nodes),
        schedules=tuple(s for s in parent.schedules if s.mechanism_id not in removed) + tuple(schedules),
        artifact_types=tuple(artifacts.values()), connections=tuple(c for c in parent.connections
            if c.source_mechanism not in removed and c.target_mechanism not in removed) + tuple(edges),
        initial_state=initial,
        metadata={**parent.metadata, 'native_design_region': {'node_ids': sorted(ids), 'boundary_origin_nodes': sorted(removed)}})
    validate_system_spec(child).require_valid()
    before, after = parent.to_dict(), child.to_dict()
    patch = make_patch(parent, [{'op': 'replace', 'path': '/' + key, 'value': after[key]} for key in
        ('mechanisms', 'connections', 'schedules', 'artifact_types', 'initial_state', 'metadata') if before[key] != after[key]], rationale=manifest['rationale'])
    return patch, apply_design_patch(parent, patch)


def probe_region(parent, child, records, *, executor, exit_validator=None):
    """Replay arbitrary recorded Python cuts with chronological generated memory.

    External observations are frozen, not newly generated by this probe. Records
    must cover the WHOLE trajectory from year one, so a stateful candidate never
    receives a late-year observation with silently empty memory. This is not a
    native rollout, and its exits are not an optimization-loss observation.
    """
    removed = child.metadata['native_design_region']['boundary_origin_nodes']
    _, incoming, outgoing, _, _ = region_boundary(parent, removed)
    old_nodes = {n.mechanism_id: n for n in parent.mechanisms if n.mechanism_id in removed}
    if any(n.implementation != CODE_IMPLEMENTATION for n in old_nodes.values()):
        raise ValueError('isolated region replay needs recorded Python source at each removed node')
    region = set(child.metadata['native_design_region']['node_ids'])
    nodes = {n.mechanism_id: n for n in child.mechanisms if n.mechanism_id in region}
    schedules = sorted((s for s in child.schedules if s.mechanism_id in region), key=lambda s: (s.phase, s.mechanism_id))
    groups = {}
    # Validate all rows before executing ANY generated code.
    for row in records:
        validate_record(row)
        matches = [n for n in old_nodes.values() if row['artifact'] == n.parameters['code_artifact']
            and row['context']['phase'] == next(s.phase for s in parent.schedules if s.mechanism_id == n.mechanism_id)]
        if len(matches) != 1 or row['binding']['system_fingerprint'] != parent.fingerprint:
            raise ValueError('region probe boundary is not the actual parent implementation')
        key = row['binding']['run_id'], row['context']['period']
        node = matches[0].mechanism_id
        slot = groups.setdefault(key, {})
        if node in slot and slot[node]['bundle_sha256'] != row['bundle_sha256']:
            raise ValueError('conflicting repeated native boundary execution')
        slot[node] = row
    if not groups:
        raise ValueError('nonempty actual native boundary probes required')
    by_run = {}
    for (run_id, period), rows in groups.items():
        if set(rows) != set(old_nodes):
            raise ValueError('all removed node contexts are required for each actual native period')
        by_run.setdefault(run_id, []).append(period)
    for periods in by_run.values():
        if sorted(periods) != list(range(1, max(periods) + 1)):
            raise ValueError('complete contiguous native trajectory from period one required for stateful probe')
    memory, runs, current_run = {}, [], None
    for (run_id, period), rows in sorted(groups.items()):
        if current_run != run_id:
            memory = {k: clone(v) for k, v in child.initial_state.get('mechanism_states', {}).items() if k in region}
            current_run = run_id
        boundary = {}
        for c in incoming:
            values = rows[c.target_mechanism]['context']['inputs'][c.target_port]
            # The code context deliberately does not expose source_port; avoid
            # guessing when two ports from the same sender feed one input.
            matching = [e for e in incoming if e.target_mechanism == c.target_mechanism
                and e.target_port == c.target_port and e.source_mechanism == c.source_mechanism]
            if len(matching) != 1:
                raise ValueError('recorded boundary cannot disambiguate source ports at this merged input')
            selected = [v for v in values if v['source_mechanism'] == c.source_mechanism]
            source = c.source_mechanism, c.source_port
            if source in boundary and boundary[source] != selected:
                raise ValueError('recorded fan-out has inconsistent external native payloads')
            boundary[source] = clone(selected)
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
            if any(p.required and not inputs[p.port_id] for p in node.inputs):
                raise ValueError('generated region has a blocked required input')
            context = {'period': period, 'phase': schedule.phase,
                'random_seed': int(sha({'period': period, 'mechanism': node.mechanism_id, 'seed': child.initial_state.get('seed', 0)})[:16], 16),
                'state': memory.get(node.mechanism_id, {}), 'parameters': {k: clone(v) for k, v in node.parameters.items() if k not in {'code_artifact', 'runtime_image_id'}},
                'inputs': inputs}
            result = executor.execute(node.parameters['code_artifact'], context)
            validate_code_result(node.parameters['code_artifact'], result.result)
            if any(result.receipt.get(k + '_sha256') != sha(v) for k, v in
                    [('artifact', node.parameters['code_artifact']), ('context', context), ('result', result.result)]):
                raise ValueError('generated region isolated execution receipt mismatch')
            if result.receipt.get('image_id') != node.parameters['runtime_image_id']:
                raise ValueError('generated region isolated runtime image mismatch')
            memory[node.mechanism_id] = clone(result.result['state'])
            executions.append({'mechanism_id': node.mechanism_id, 'context': clone(context),
                'result': clone(result.result), 'receipt': result.receipt})
            for port, values in result.result['outputs'].items():
                declaration = next(p for p in node.outputs if p.port_id == port)
                if declaration.required and not values:
                    raise ValueError('generated region has an empty required output')
                produced[(node.mechanism_id, port)] = [{'payload': clone(v['payload']),
                    'actor_ids': clone(v.get('actor_ids', [])), 'artifact_ids': clone(v.get('artifact_ids', [])),
                    'source_mechanism': node.mechanism_id, 'emitted_period': period} for v in values]
        exits = {}
        for c in child.connections:
            if c.source_mechanism in region and c.target_mechanism not in region:
                exits.setdefault((c.target_mechanism, c.target_port), []).extend(produced[(c.source_mechanism, c.source_port)])
        if exit_validator is not None:
            exit_validator(period, rows, exits)
        runs.append({'run_id': run_id, 'year': period,
            'native_boundary_bundle_sha256s': {n: r['bundle_sha256'] for n, r in rows.items()},
            'code_executions': executions, 'exits': [
                {'target_mechanism': target, 'target_port': port, 'values': clone(values)}
                for (target, port), values in sorted(exits.items())], 'state_after': clone(memory)})
    return {'status': 'isolated-native-region-passed-not-native-evaluated', 'runs': runs,
        'scope': 'actual parent boundary inputs, full chronological generated state and container source; fresh native rollout still required'}


def probe_selection_region(parent, child, records, *, executor, original_node='world.selection'):
    """Publication adapter: generic graph replay plus real native paper identity."""
    if child.metadata['native_design_region']['boundary_origin_nodes'] != [original_node]:
        raise ValueError('this publication probe supports a single original selection cut')
    def validate_exits(period, rows, exits):
        row = rows[original_node]
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
    result = probe_region(parent, child, records, executor=executor, exit_validator=validate_exits)
    original = {(r['binding']['run_id'], r['context']['period']): r for r in records}
    for run in result['runs']:
        row = original[(run['run_id'], run['year'])]
        run['native_boundary_bundle_sha256'] = row['bundle_sha256']
        run['decisions'] = [v['payload'] for e in run['exits']
            if (e['target_mechanism'], e['target_port']) == ('world.publication', 'decisions') for v in e['values']]
        run['decisions_changed'] = run['decisions'] != [v['payload'] for v in row['result']['outputs']['decisions']]
    return result
