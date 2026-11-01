"""Projected continuous institutions and falsifiable local native-gradient checks.

The original native simulation is the forward system. Recorded tensors are
conditional representations, not a compiler for arbitrary Python, text or LLM
responses. Actual endpoint secants are labelled numerical measurements, never
installed as a fabricated pathwise backward rule.
"""
from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path

import torch

from .loss import evaluate_loss, loss_spec_sha256
from .native_relaxation import native_tensor_trace, replay_tensor_trace, trace_objective
from .native_transition_data import physical_initial_identity
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system import SystemSpec, validate_system_spec
from utopia.system.design_patch import apply_design_patch, digest, make_patch, read_pointer
from utopia.system.native_kernel import NativeScienceKernel
from utopia.system.tensor_program import IMPLEMENTATION
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-hybrid-fidelity.v7'


def continuous_coordinates(system, declarations):
    """Bind scalar coordinates to actual tensor or arbitrary Python parameters.

    Python values are executable source parameters, NOT differentiable source.
    Text/source, state initialization and native laws are never silently edited.
    """
    if not isinstance(declarations, list) or not declarations:
        raise ValueError('explicit nonempty continuous coordinate declarations required')
    nodes = {node.mechanism_id: node for node in system.mechanisms}
    names, addresses, result = set(), set(), []
    for item in declarations:
        if (not isinstance(item, dict) or set(item) != {'id', 'mechanism', 'path', 'lower', 'upper', 'quantum'}
                or not isinstance(item['id'], str) or not item['id'] or item['id'] in names
                or item['mechanism'] not in nodes or not isinstance(item['path'], str) or not item['path'].startswith('/')):
            raise ValueError('unique coordinate identity and exact parameter address required')
        node = nodes[item['mechanism']]
        if (node.implementation not in (IMPLEMENTATION, 'code.python.v1')
                or (node.implementation == IMPLEMENTATION and not item['path'].startswith('/program/parameters/'))
                or (node.implementation == 'code.python.v1' and item['path'].split('/')[1] in {'code_artifact', 'runtime_image_id'})):
            raise ValueError('coordinate must be an actual institution parameter, not source/state/world-law rewriting')
        value = read_pointer(node.parameters, item['path'])
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in (value, item['lower'], item['upper'])):
            raise ValueError('continuous values/bounds must be finite scalars, not booleans')
        if not item['lower'] <= value <= item['upper'] or item['lower'] == item['upper']:
            raise ValueError('initial coordinate must lie in a nontrivial declared interval')
        quantum = item['quantum']
        if quantum is not None and (type(quantum) not in (int, float) or not math.isfinite(quantum) or quantum <= 0):
            raise ValueError('optional operational quantization must be explicitly positive')
        address = (item['mechanism'], item['path'])
        if address in addresses:
            raise ValueError('duplicate scalar parameter address')
        names.add(item['id'])
        addresses.add(address)
        result.append({**deepcopy(item), 'value': float(value),
            'derivative_route': 'represented-conditional-autograd' if node.implementation == IMPLEMENTATION else 'opaque-source-parameter-native-perturbation'})
    return result


def project_continuous(system, declarations, values):
    coordinates = continuous_coordinates(system, declarations)
    if set(values) != {c['id'] for c in coordinates}:
        raise ValueError('one proposed value per declared coordinate required')
    operations, report = [], []
    for coordinate in coordinates:
        requested = values[coordinate['id']]
        if type(requested) not in (int, float) or not math.isfinite(requested):
            raise ValueError('projected coordinates must be finite real values')
        value = min(coordinate['upper'], max(coordinate['lower'], float(requested)))
        if coordinate['quantum'] is not None:
            value = coordinate['lower'] + round((value-coordinate['lower']) / coordinate['quantum']) * coordinate['quantum']
            value = min(coordinate['upper'], max(coordinate['lower'], value))
        index = next(i for i, node in enumerate(system.mechanisms) if node.mechanism_id == coordinate['mechanism'])
        if value != coordinate['value']:
            operations.append({'op': 'replace', 'path': f'/mechanisms/{index}/parameters' + coordinate['path'], 'value': value})
        report.append({'id': coordinate['id'], 'before': coordinate['value'], 'requested': requested, 'projected': value,
            'quantum': coordinate['quantum'], 'derivative_route': coordinate['derivative_route'],
            'projection_derivative': 'not-pathwise-quantized' if coordinate['quantum'] is not None else
                'clamped-zero' if requested != value else 'boundary-nondifferentiable'
                if value in (coordinate['lower'], coordinate['upper']) else 'identity-in-interior'})
    patch = make_patch(system, operations, rationale='explicit continuous institutional projection') if operations else None
    candidate = apply_design_patch(system, patch) if patch else system
    return candidate, {'coordinates': report, 'patch': patch, 'parent_fingerprint': system.fingerprint,
        'candidate_fingerprint': candidate.fingerprint, 'candidate': candidate.to_dict(),
        'projection_sha256': digest(report), 'native_effect_not_yet_evaluated': True}


def boundary_coverage(system, events):
    """Report routable protocols and exactly where numerical backward stops."""
    validate_system_spec(system).require_valid()
    events = list(events)
    has_tensor_events = any((e.to_dict() if hasattr(e, 'to_dict') else e)['event_type'] == 'native.tensor.executed' for e in events)
    trace = native_tensor_trace(events) if has_tensor_events else []
    nodes = {n.mechanism_id: n for n in system.mechanisms}
    programs = {n.mechanism_id: n.parameters['program'] for n in system.mechanisms if n.implementation == IMPLEMENTATION}
    if trace:
        replay_tensor_trace(trace, programs, hard=True, verify_recorded=True)
    dependencies = {(f['mechanism'], name): source for f in trace for name, source in f['input_sources'].items()}
    edges = []
    for edge in system.connections:
        source, target = nodes[edge.source_mechanism], nodes[edge.target_mechanism]
        represented = source.implementation == target.implementation == IMPLEMENTATION
        bindings = target.parameters.get('input_bindings', {}) if target.implementation == IMPLEMENTATION else {}
        paths = [binding['path'] for binding in bindings.values() if binding['port'] == edge.target_port]
        if represented and paths and all(path == '/values' for path in paths):
            kind = 'represented-numeric-communication'
        elif target.implementation == IMPLEMENTATION:
            kind = 'conditioned-numeric-input-opaque-upstream'
        elif source.implementation == IMPLEMENTATION:
            kind = 'opaque-consumer-or-native-effect'
        else:
            kind = 'opaque-numeric-or-nonnumeric-protocol'
        observed = any(f['mechanism'] == edge.target_mechanism and any(
            source['mechanism'] == edge.source_mechanism and source['port'] == edge.source_port
            and bindings.get(name, {}).get('port') == edge.target_port
            for name, source in f['input_sources'].items()) for f in trace)
        edges.append({'source_mechanism': edge.source_mechanism, 'source_port': edge.source_port,
            'target_mechanism': edge.target_mechanism, 'target_port': edge.target_port,
            'channel': edge.channel.value, 'latency': edge.latency, 'derivative_coverage': kind,
            'declared_routable': True, 'observed_tensor_input_dependency': observed, 'latency_preserved': edge.latency,
            'text_and_identity_derivatives_available': False})
    return {'schema': SCHEMA + '.boundary-coverage', 'system_fingerprint': system.fingerprint,
        'represented_mechanisms': sorted(programs), 'trace_frames': len(trace), 'edges': edges,
        'verified_represented_mechanisms': sorted({f['mechanism'] for f in trace}),
        'declared_unobserved_tensor_mechanisms': sorted(set(programs)-{f['mechanism'] for f in trace}),
        'represented_numeric_edge_count': sum(e['derivative_coverage'] == 'represented-numeric-communication' for e in edges),
        'opaque_mechanisms': [{'mechanism': n.mechanism_id, 'implementation': n.implementation,
            'boundary': 'arbitrary-source-or-LLM' if n.implementation in ('code.python.v1', 'native.world.llm-institution.v1') else 'native-or-unrepresented-transition'}
            for n in system.mechanisms if n.implementation != IMPLEMENTATION],
        'conditioned_input_sources': [{'mechanism': key[0], 'input': key[1], **value} for key, value in dependencies.items()],
        'nonnumeric_records': 'actor/artifact IDs and text remain routable data, not numerical differentiable coordinates',
        'full_native_world_autograd': False}


def endpoint_input_drift(left, right):
    """Expose changed native conditioning; do not freeze it away at validation."""
    frames = {(f['mechanism'], f['year']): f for f in right['trace']}
    comparisons = []
    for source in left['trace']:
        key = (source['mechanism'], source['year'])
        if key not in frames:
            comparisons.append({'mechanism': key[0], 'year': key[1], 'status': 'missing-endpoint-frame'})
            continue
        target = frames[key]
        for name, value in source['inputs'].items():
            first = torch.tensor(value, dtype=torch.float64)
            second = torch.tensor(target['inputs'][name], dtype=torch.float64)
            comparisons.append({'mechanism': key[0], 'year': key[1], 'input': name,
                'shape_changed': first.shape != second.shape,
                'maximum_absolute_change': float((first-second).abs().max()) if first.shape == second.shape and first.numel() else None,
                'identity_records_changed': source.get('records') != target.get('records')})
    return {'endpoint_checkpoint_sha256s': [left['checkpoint_sha256'], right['checkpoint_sha256']],
        'comparisons': comparisons,
        'conditioning_changed': any(c.get('shape_changed') or c.get('identity_records_changed')
            or (c.get('maximum_absolute_change') or 0.) > 1e-12 or c.get('status') for c in comparisons),
        'scope': 'Recorded numeric inputs/identity alignment, not a Jacobian of opaque researcher text.'}


def conditional_backward(trace, programs, *, trainable, terms, temperature=1., epsilon=1e-5):
    """Real autograd plus local numerical checks on the SAME conditional model."""
    if type(epsilon) not in (int, float) or not 0 < epsilon < .1:
        raise ValueError('explicit small positive numerical check epsilon required')
    replay_tensor_trace(trace, programs, hard=True, verify_recorded=True)
    if set(trainable) - set(programs):
        raise ValueError('unknown trainable mechanism')
    parameters, leaves, addresses = {}, [], []
    for mechanism, program in programs.items():
        if set(trainable.get(mechanism, [])) - set(program['parameters']):
            raise ValueError('unknown trainable parameter')
        parameters[mechanism] = {}
        for key, value in program['parameters'].items():
            leaf = torch.tensor(value, dtype=torch.float64, requires_grad=key in trainable.get(mechanism, []))
            parameters[mechanism][key] = leaf
            if leaf.requires_grad:
                leaves.append(leaf)
                addresses.append((mechanism, key))
    if not leaves or sum(p.numel() for p in leaves) > 128:
        raise ValueError('one to 128 explicitly trainable scalar entries required')
    def objective():
        return trace_objective(replay_tensor_trace(trace, programs, parameters=parameters,
            hard=False, temperature=temperature), terms)
    loss = objective()
    gradients = torch.autograd.grad(loss, leaves)
    checks = []
    result = {}
    for (mechanism, key), leaf, gradient in zip(addresses, leaves, gradients):
        numerical = torch.zeros_like(leaf)
        for index in range(leaf.numel()):
            original = float(leaf.detach().flatten()[index])
            with torch.no_grad():
                leaf.flatten()[index] = original + epsilon
            plus = float(objective().detach())
            with torch.no_grad():
                leaf.flatten()[index] = original - epsilon
            minus = float(objective().detach())
            with torch.no_grad():
                leaf.flatten()[index] = original
            numerical.flatten()[index] = (plus-minus)/(2*epsilon)
        if not torch.isfinite(gradient).all() or not torch.isfinite(numerical).all():
            raise ValueError('nonfinite represented gradient; no replacement gradient supplied')
        error = float((gradient-numerical).abs().max())
        result.setdefault(mechanism, {})[key] = gradient.tolist()
        checks.append({'mechanism': mechanism, 'parameter': key, 'autograd': gradient.tolist(),
            'conditional_finite_difference': numerical.tolist(), 'absolute_max_error': error,
            'status': 'passed' if torch.allclose(gradient, numerical, atol=1e-5, rtol=1e-4) else 'failed'})
    return {'schema': SCHEMA + '.conditional-backward', 'trace_sha256': digest(trace),
        'program_sha256s': {name: digest(program) for name, program in programs.items()},
        'conditional_soft_loss': float(loss.detach()), 'terms': deepcopy(terms), 'temperature': temperature,
        'finite_difference_epsilon': epsilon,
        'gradient': result, 'numerical_checks': checks,
        'status': 'passed' if all(c['status'] == 'passed' for c in checks) else 'failed',
        'native_loss_gradient_verified': False, 'full_native_world_autograd': False}


def native_endpoint(checkpoint, system, declarations, loss_spec, *, world, code_contexts=None):
    """Independently remeasure complete original-native endpoint facts, read only."""
    checkpoint = Path(checkpoint).resolve()
    original = file_sha256(checkpoint)
    saved = read_portable_checkpoint(checkpoint)
    kernel = NativeScienceKernel(system, checkpoint=saved['native_system'])
    binding = saved['portable']['contract']['binding']
    horizon = saved['portable']['contract']['simulation']['num_years']
    if (saved.get('phase') != 5 or saved.get('year') != horizon or kernel.last_year != horizon
            or saved['portable']['contract']['native_system']['system_fingerprint'] != system.fingerprint
            or binding['cell'] != system.fingerprint
            or binding['science_config']['source_commit'] != world['source_commit']
            or binding['model_revision'] != world['model_digest'] or binding['corpus_sha256'] != world['corpus_sha256']
            or binding['seed'] != world['seed']):
        raise ValueError('native endpoint is not the exact completed source/model/corpus/seed/design')
    if (saved['portable']['contract']['model'] != binding['model']
            or saved['portable']['contract']['model_revision'] != binding['model_revision']
            or binding['science_config'].get('years', horizon) != horizon
            or world.get('years', horizon) != horizon):
        raise ValueError('native endpoint execution model/horizon differs from scientific binding')
    rag_digest = saved['rag'].get('ordered_documents_sha256')
    if rag_digest is not None and rag_digest != world['corpus_sha256']:
        raise ValueError('actual native ordered RAG corpus differs from declared identity')
    decisions = [d for p in saved['paper_tracker']['papers'] for d in p['review_history']]
    accepted = [d for d in decisions if d.get('decision') == 'accept']
    authors = [a for a in saved['ecosystem_data']['agents'] if a['can_author']]
    values = {'native.accepted_decisions': len(accepted),
        'native.rejected_decisions': sum(d.get('decision') == 'reject' for d in decisions),
        'native.review_records': sum(len(d.get('reviews', [])) for d in decisions),
        'native.final_active_authors': sum(a['is_active'] for a in authors),
        'native.final_author_resources': sum(a['resources'] for a in authors),
        'native.institutional_context_deliveries': sum(e.event_type == 'native.system.context_delivered' for e in kernel.events),
        'native.accepted_unreviewed_decisions': sum(not d.get('reviews') for d in accepted)}
    means, unavailable = [], False
    for decision in accepted:
        scores = [r.get('overall_score') for r in decision.get('reviews', [])]
        if any(type(s) not in (int, float) or not math.isfinite(s) for s in scores):
            unavailable = True
            break
        means.append(math.fsum(scores)/len(scores) if scores else 0.)
    metrics = {k: {'status': 'measured', 'value': v} for k, v in values.items()}
    metrics['native.accepted_peer_score_sum'] = ({'status': 'unavailable', 'value': None,
        'reason': 'accepted decision has a missing or nonfinite raw reviewer score'} if unavailable else
        {'status': 'measured', 'value': sum(means)})
    measurement = {'run_id': str(checkpoint), 'system_fingerprint': system.fingerprint,
        'measurement_schema': 'scienceutopia.native-domain-measurements.v1', 'metrics': metrics}
    evaluated = evaluate_loss(loss_spec, [measurement])
    if evaluated['status'] != 'complete':
        raise ValueError('native objective unavailable; no numerical endpoint loss fabricated')
    coordinates = continuous_coordinates(system, declarations)
    source_coordinates = [c for c in coordinates if c['derivative_route'].startswith('opaque-source')]
    source_proofs = []
    code_original = file_sha256(Path(code_contexts)) if code_contexts is not None else None
    if source_coordinates:
        if code_contexts is None:
            raise ValueError('actual code-input receipts required for opaque source-parameter coordinates')
        import json
        from .native_code_trace import validate_record
        records = [validate_record(json.loads(line)) for line in Path(code_contexts).read_text().splitlines()]
        for coordinate in source_coordinates:
            node = next(n for n in system.mechanisms if n.mechanism_id == coordinate['mechanism'])
            matches = [r for r in records if r['artifact'] == node.parameters['code_artifact']]
            expected_parameters = {k: v for k, v in node.parameters.items() if k not in {'code_artifact', 'runtime_image_id'}}
            if not matches or any(r['binding'] != {'source_commit': world['source_commit'],
                    'system_fingerprint': system.fingerprint, 'run_id': records[0]['binding']['run_id']}
                    or r['context']['parameters'] != expected_parameters or not any(e.event_type == 'generated.code_executed'
                        and e.provenance['mechanism_id'] == node.mechanism_id and e.year == r['context']['period']
                        and all(e.payload[key] == r['receipt'][key] for key in ('image_id', 'artifact_sha256', 'context_sha256', 'result_sha256'))
                        for e in kernel.events) for r in matches):
                raise ValueError('opaque source parameter lacks exact actual code-context/native-event binding')
            source_proofs.append({'coordinate': coordinate['id'], 'actual_value': coordinate['value'],
                'actual_context_bundle_sha256s': [r['bundle_sha256'] for r in matches]})
    normalized = deepcopy(system.to_dict())
    for coordinate in coordinates:
        index = next(i for i, n in enumerate(system.mechanisms) if n.mechanism_id == coordinate['mechanism'])
        # A normalized candidate binds all source/protocol/wiring except the
        # explicitly declared scalar coordinates.
        from utopia.system.design_patch import _edit
        _edit(normalized, {'op': 'replace', 'path': f'/mechanisms/{index}/parameters' + coordinate['path'], 'value': 0.})
    initial = checkpoint.parent / 'portable_checkpoint_year_0.json.gz'
    initial_hash = file_sha256(initial)
    initial_state = read_portable_checkpoint(initial)
    if (initial_state.get('year') != 0 or initial_state.get('phase') != 0
            or initial_state['native_system']['spec'] != system.to_dict()
            or initial_state['portable']['contract']['binding'] != binding
            or initial_state['portable']['response_cache_count'] != 0):
        raise ValueError('endpoint requires the original initialized candidate world, not an unrelated/reset society')
    result = {'checkpoint': str(checkpoint), 'checkpoint_sha256': original,
        'initial_checkpoint_sha256': initial_hash,
        'physical_initial_identity': physical_initial_identity(initial_state),
        'system': system.to_dict(), 'system_fingerprint': system.fingerprint,
        'archived_ordered_corpus_sha256': rag_digest,
        'noncoordinate_system_sha256': digest(normalized), 'coordinates_sha256': digest(declarations),
        'coordinate_values': {c['id']: c['value'] for c in coordinates}, 'world': deepcopy(world),
        'loss_spec_sha256': loss_spec_sha256(loss_spec), 'measurement': measurement, 'native_loss': evaluated['loss'],
        'response_cache_count': saved['portable']['response_cache_count'],
        'code_contexts': str(Path(code_contexts).resolve()) if code_contexts is not None else None,
        'code_contexts_sha256': code_original,
        'opaque_parameter_executions': source_proofs,
        'native_event_stream_hash': kernel.to_dict()['event_stream_hash'], 'trace': native_tensor_trace(kernel.events)}
    if file_sha256(checkpoint) != original:
        raise ValueError('native checkpoint changed during endpoint inspection')
    if code_contexts is not None and file_sha256(Path(code_contexts)) != code_original:
        raise ValueError('native code contexts changed during endpoint inspection')
    if file_sha256(initial) != initial_hash:
        raise ValueError('native initial checkpoint changed during endpoint inspection')
    return result


def native_directional_fidelity(minus, plus, gradient, *, atol=1e-4, rtol=.1):
    """Compare an explicitly supplied conditional prediction with fresh native facts."""
    for key in ('world', 'physical_initial_identity', 'noncoordinate_system_sha256', 'coordinates_sha256', 'loss_spec_sha256'):
        if minus[key] != plus[key]:
            raise ValueError('native endpoint comparison changes undeclared world/design/objective: ' + key)
    if minus['checkpoint'] == plus['checkpoint'] or minus['checkpoint_sha256'] == plus['checkpoint_sha256']:
        raise ValueError('two distinct actual endpoint checkpoints required; not fake independent replicates')
    names = list(minus['coordinate_values'])
    if set(gradient) != set(names) or set(plus['coordinate_values']) != set(names):
        raise ValueError('one conditional gradient per declared continuous coordinate required')
    delta = [plus['coordinate_values'][key]-minus['coordinate_values'][key] for key in names]
    distance = math.sqrt(sum(v*v for v in delta))
    if distance == 0:
        return {'status': 'undefined-projected-endpoints-coincide', 'native_derivative_verified': False}
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in [*gradient.values(), atol, rtol]) or min(atol, rtol) < 0:
        raise ValueError('finite explicit gradient and nonnegative fidelity tolerances required')
    predicted = sum(gradient[key]*value for key, value in zip(names, delta))/distance
    actual = (plus['native_loss']-minus['native_loss'])/distance
    error = abs(predicted-actual)
    passed = error <= atol + rtol*abs(actual)
    return {'schema': SCHEMA + '.directional-check', 'status': 'passed-local-secant-check' if passed else 'failed-local-native-fidelity',
        'predicted_conditional_directional_derivative': predicted, 'actual_native_secant': actual,
        'absolute_error': error, 'atol': atol, 'rtol': rtol, 'actual_coordinate_displacement': delta,
        'minus_native_loss': minus['native_loss'], 'plus_native_loss': plus['native_loss'],
        'endpoint_checkpoint_sha256s': [minus['checkpoint_sha256'], plus['checkpoint_sha256']],
        'full_native_world_autograd': False,
        'scope': 'Local native secant check including fresh native researcher reactions; finite-radius agreement is not an exact LLM/native Jacobian or generalization.'}


def hybrid_gradient(system, declarations, conditional, *, opaque_endpoints):
    """Combine exact conditional backward and explicitly measured opaque secants.

    These components have different estimands. They are never relabelled as a
    single exact full-native gradient or used to backprop through saved tokens.
    """
    if conditional['status'] != 'passed':
        raise ValueError('conditional numerical backward check failed; no hybrid update')
    expected_programs = {n.mechanism_id: digest(n.parameters['program']) for n in system.mechanisms if n.implementation == IMPLEMENTATION}
    if conditional.get('program_sha256s') != expected_programs:
        raise ValueError('conditional gradient belongs to different represented institution programs')
    coordinates = continuous_coordinates(system, declarations)
    expected_values = {c['id']: c['value'] for c in coordinates}
    values, evidence = {}, []
    for coordinate in coordinates:
        key = coordinate['id']
        if coordinate['derivative_route'] == 'represented-conditional-autograd':
            tree = {'program': {'parameters': conditional['gradient'].get(coordinate['mechanism'], {})}}
            value = read_pointer(tree, coordinate['path'])
            proof = {'id': key, 'method': 'conditional-represented-autograd',
                'trace_sha256': conditional['trace_sha256'], 'native_loss_gradient_verified': False}
        else:
            if key not in opaque_endpoints:
                raise ValueError('opaque source parameter needs actual native perturbation endpoints: ' + key)
            minus, plus = opaque_endpoints[key]
            if (minus['coordinate_values'] != expected_values or digest(minus['trace']) != conditional['trace_sha256']):
                raise ValueError('hybrid conditional gradient and opaque perturbation use different actual base records/controls')
            for field in ('world', 'physical_initial_identity', 'noncoordinate_system_sha256', 'coordinates_sha256', 'loss_spec_sha256'):
                if minus[field] != plus[field]:
                    raise ValueError('opaque perturbation changes undeclared endpoint binding')
            if any(minus['coordinate_values'][name] != plus['coordinate_values'][name]
                    for name in minus['coordinate_values'] if name != key):
                raise ValueError('opaque partial secant changed another continuous coordinate')
            delta = plus['coordinate_values'][key]-minus['coordinate_values'][key]
            if delta == 0 or minus['checkpoint'] == plus['checkpoint']:
                raise ValueError('opaque partial secant requires distinct projected native endpoints')
            value = (plus['native_loss']-minus['native_loss'])/delta
            proof = {'id': key, 'method': 'measured-native-partial-secant-not-pathwise',
                'checkpoint_sha256s': [minus['checkpoint_sha256'], plus['checkpoint_sha256']],
                'actual_coordinate_displacement': delta, 'native_loss_gradient_verified': False}
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('undefined/nonfinite hybrid component')
        values[key] = value
        evidence.append(proof)
    return {'gradient': values, 'components': evidence, 'full_native_world_autograd': False,
        'requires_projected_native_reevaluation': True}


def save_hybrid_report(path, report):
    document = {'schema': SCHEMA, 'report': deepcopy(report)}
    document['receipt_sha256'] = digest(document)
    write_json_atomic(Path(path), document, sort_keys=True, allow_nan=False)
    return document


def load_hybrid_report(path, *, verify_checkpoints=True):
    import json
    document = json.loads(Path(path).read_text())
    if (set(document) != {'schema', 'report', 'receipt_sha256'} or document['schema'] != SCHEMA
            or digest({k: v for k, v in document.items() if k != 'receipt_sha256'}) != document['receipt_sha256']):
        raise ValueError('hybrid report schema/content receipt changed')
    if verify_checkpoints:
        report = document['report']
        for endpoint in report.get('endpoints', []):
            if (file_sha256(Path(endpoint['checkpoint'])) != endpoint['checkpoint_sha256']
                    or file_sha256(Path(endpoint['checkpoint']).parent / 'portable_checkpoint_year_0.json.gz') != endpoint['initial_checkpoint_sha256']):
                raise ValueError('hybrid endpoint checkpoint evidence changed')
            if native_endpoint(endpoint['checkpoint'], SystemSpec.from_dict(endpoint['system']),
                    document['report']['declarations'], document['report']['loss_spec'], world=endpoint['world'],
                    code_contexts=endpoint.get('code_contexts')) != endpoint:
                raise ValueError('hybrid native endpoint semantic facts changed')
        if report.get('endpoints'):
            base = report['endpoints'][0]
            system = SystemSpec.from_dict(base['system'])
            endpoints = {e['checkpoint_sha256']: e for e in report['endpoints']}
            if len(endpoints) != len(report['endpoints']):
                raise ValueError('duplicate physical endpoint entries are not independent observations')
            if 'coverage' in report:
                state = read_portable_checkpoint(Path(base['checkpoint']))
                kernel = NativeScienceKernel(system, checkpoint=state['native_system'])
                if boundary_coverage(system, kernel.events) != report['coverage']:
                    raise ValueError('durable native boundary coverage changed')
            if 'conditional_backward' in report:
                saved = report['conditional_backward']
                programs = {n.mechanism_id: n.parameters['program'] for n in system.mechanisms if n.implementation == IMPLEMENTATION}
                replayed = conditional_backward(base['trace'], programs,
                    trainable={name: list(values) for name, values in saved['gradient'].items()},
                    terms=saved['terms'], temperature=saved['temperature'], epsilon=saved['finite_difference_epsilon'])
                if replayed != saved:
                    raise ValueError('durable conditional backward/gradient evidence changed')
            if 'hybrid_gradient' in report:
                opaque = {p['id']: tuple(endpoints[key] for key in p['checkpoint_sha256s'])
                    for p in report['hybrid_gradient']['components'] if p['method'] == 'measured-native-partial-secant-not-pathwise'}
                if hybrid_gradient(system, report['declarations'], report['conditional_backward'], opaque_endpoints=opaque) != report['hybrid_gradient']:
                    raise ValueError('durable hybrid gradient evidence changed')
            if 'projection' in report:
                saved = report['projection']
                candidate, replayed = project_continuous(system, report['declarations'],
                    {coordinate['id']: coordinate['requested'] for coordinate in saved['coordinates']})
                if replayed != saved or not any(e['system_fingerprint'] == candidate.fingerprint for e in endpoints.values()):
                    raise ValueError('durable projected design lacks exact actual reevaluation')
            if 'native_directional_fidelity' in report:
                saved = report['native_directional_fidelity']
                if 'endpoint_checkpoint_sha256s' in saved:
                    pair = [endpoints[key] for key in saved['endpoint_checkpoint_sha256s']]
                    if native_directional_fidelity(*pair, report['hybrid_gradient']['gradient'], atol=saved['atol'], rtol=saved['rtol']) != saved:
                        raise ValueError('durable native fidelity check changed')
            if 'endpoint_input_drift' in report:
                saved = report['endpoint_input_drift']
                if endpoint_input_drift(*(endpoints[key] for key in saved['endpoint_checkpoint_sha256s'])) != saved:
                    raise ValueError('durable native input-drift evidence changed')
    return document['report']
