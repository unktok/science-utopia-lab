#!/usr/bin/env python3
"""Posthoc numerical diagnosis of frozen v9 gradients; ZERO native/model calls.

Temperature sweeps are representation ablations on old development evidence,
not new native outcomes, held-out checks, or a reselection of the v9 proposal.
"""
from copy import deepcopy
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import torch

from utopia.optimization.native_response_fidelity import (
    NativeResponseOperator, programs, project_response, response_replay,
)
from utopia.optimization.native_relaxation import trace_objective
from utopia.system.design_patch import digest
from utopia.system.tensor_program import execute_tensor_program
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.posthoc-native-gradient-diagnosis.v10'
TEMPERATURES = (1., .2, .05, .01)
DTYPE = torch.float64


def read(path):
    value = json.loads(Path(path).read_text())
    if value.get('content_sha256') != digest({k: v for k, v in value.items() if k != 'content_sha256'}):
        raise ValueError('saved content hash differs: '+str(path))
    return value


def inventory(root):
    result = {}
    for path in sorted(Path(root).rglob('*')):
        if path.is_symlink():
            raise ValueError('raw evidence cannot contain symlinks')
        if path.is_file():
            result[str(path.relative_to(root))] = {'sha256': file_sha256(path), 'bytes': path.stat().st_size}
    return result


def represented_replay(state, values, temperature, *, detach_memory=False):
    """Same frozen tensor programs/edges, with optional backward-only memory cut.

    Extra outputs expose existing selector nodes without changing any equation.
    Declared v9 coordinate is an opaque charter parameter, never a tensor weight.
    """
    endpoint = state['calibration'][0]
    ps = programs(endpoint)
    if any(d['mechanism'] in ps for d in state['declarations']):
        raise ValueError('this v9 diagnostic requires an opaque charter-only coordinate')
    overrides = {}
    for entry in state['layout']:
        array = values[entry['offset']:entry['offset']+entry['size']].reshape(entry['shape'])
        if entry['canonical_to_actual']:
            array = array[np.argsort(entry['canonical_to_actual']).tolist()]
        overrides[(entry['frame'], entry['input'])] = array
    memory, produced, frames, diagnostics = {}, {}, [], []
    for index, frame in enumerate(endpoint['trace']):
        name = frame['mechanism']
        inputs = {}
        for key, source in frame['input_sources'].items():
            inputs[key] = (produced[(source['mechanism'], source['port'], frame['year'])]
                if source['mechanism'] in ps and source['path'] == '/values' else overrides[(index, key)])
        if name not in memory:
            memory[name] = {k: torch.tensor(v, dtype=DTYPE) for k, v in frame['state_before'].items()}
        if detach_memory:
            memory[name] = {k: v.detach() for k, v in memory[name].items()}
        program = deepcopy(ps[name])
        if name == 'addressed-selection':
            for label, node in (('diagnostic-margin', 'margin'), ('diagnostic-threshold', 'effective-threshold'),
                                ('diagnostic-memory', 'memory-penalty')):
                program['outputs'][label] = node
        outputs, memory[name] = execute_tensor_program(program, inputs, state=memory[name],
            hard=False, temperature=temperature)
        if name == 'addressed-selection':
            diagnostics.append({'year': frame['year'], 'records': frame['records'], 'outputs': outputs})
        for port in ps[name]['outputs']:
            produced[(name, port, frame['year'])] = outputs[port]
        frames.append({'year': frame['year'], 'mechanism': name,
            'outputs': {k: outputs[k] for k in ps[name]['outputs']}})
    return frames, diagnostics


def numerical_chain(state, theta, *, parser_temperature, institution_temperature, detach_memory=False):
    weights = torch.tensor(state['weights'], dtype=DTYPE)
    center = torch.tensor(state['center'], dtype=DTYPE)
    if weights.shape[0] != 2 or center.numel() != 1:
        raise ValueError('one independently identified v9 coordinate required')
    raw = (weights[0]+(theta-center[0])*weights[1]).detach().requires_grad_()
    jacobian = weights[1]
    projected = project_response(raw, state['projection'], hard=False, temperature=parser_temperature)
    frames, diagnostics = represented_replay(state, projected, institution_temperature, detach_memory=detach_memory)
    loss = trace_objective(frames, state['terms'])
    dloss_dz, = torch.autograd.grad(loss, projected, retain_graph=True)
    dloss_draw, = torch.autograd.grad(loss, raw, retain_graph=True)
    parse_jacobian = torch.autograd.functional.jacobian(lambda value: project_response(
        value, state['projection'], hard=False, temperature=parser_temperature), raw)
    dz_dtheta = parse_jacobian@jacobian
    publication_cost = programs(state['calibration'][0])['loss-accounting']['parameters']['publication_cost']
    pub = sum(publication_cost*f['outputs']['accept'].sum() for f in diagnostics)
    utility = sum(-(f['outputs']['accept']*f['outputs']['scores']).sum() for f in diagnostics)
    def derivative(value):
        gradient, = torch.autograd.grad(value, raw, retain_graph=True)
        return float(gradient@jacobian)
    components = {'publication_cost_gradient': derivative(pub), 'accepted_score_utility_gradient': derivative(utility)}
    components['review_cost_and_other_gradient'] = float(dloss_draw@jacobian)-sum(components.values())
    selected = state['projection']['indices']
    raw_details = []
    for position, index in enumerate(selected):
        levels = torch.arange(1, state['projection']['upper']+1, dtype=DTYPE)
        sigmoid = torch.sigmoid((raw[index]-levels)/parser_temperature)
        raw_details.append({'semantic_id': state['projection']['contract']['raw_review_semantic_ids'][position],
            'raw_index': index, 'fitted_raw': float(raw[index].detach()), 'raw_response_slope': float(jacobian[index]),
            'integer_projection_slope': float((sigmoid*(1.-sigmoid)/parser_temperature).sum().detach()),
            'downstream_loss_wrt_raw': float(dloss_draw[index]),
            'gradient_contribution': float(dloss_draw[index]*jacobian[index])})
    papers = []
    for frame in diagnostics:
        outputs = frame['outputs']
        for i, record in enumerate(frame['records']):
            papers.append({'year': frame['year'], **record,
                'soft_score': float(outputs['scores'][i].detach()),
                'effective_threshold': float(outputs['diagnostic-threshold'][i].detach()),
                'margin': float(outputs['diagnostic-margin'][i].detach()),
                'soft_admission': float(outputs['accept'][i].detach()),
                'memory_penalty': float(outputs['diagnostic-memory'].detach())})
    score_entries = []
    for group in state['projection']['contract']['aggregation']:
        index = group['target']
        score_entries.append({'target_index': index, 'd_projected_score_d_theta': float(dz_dtheta[index]),
            'd_loss_d_projected_score': float(dloss_dz[index]),
            'gradient_contribution': float(dz_dtheta[index]*dloss_dz[index])})
    return {'theta': float(theta), 'parser_temperature': parser_temperature, 'institution_temperature': institution_temperature,
        'loss': float(loss.detach()), 'gradient': float(dloss_draw@jacobian),
        'chain_gradient': float(dloss_dz@dz_dtheta), 'component_gradients': components,
        'detach_memory_backward': detach_memory, 'raw_reviews': raw_details, 'paper_states': papers,
        'projected_score_chain': score_entries,
        'raw_response_slope_l2': float(jacobian[selected].square().sum().sqrt()),
        'projected_response_slope_l2': float(dz_dtheta.square().sum().sqrt())}


def analyze(audit_path):
    audit_path = Path(audit_path).resolve()
    audit = read(audit_path)
    root = Path(audit['raw_output_root']).resolve()
    before = inventory(root)
    if before != audit['raw_hashes']['files']:
        raise ValueError('frozen v9 raw differs from its independent audit')
    for relative, expected in audit['source_proof']['module_sha256s'].items():
        if file_sha256(ROOT/relative) != expected:
            raise ValueError('frozen scientific/comparator source changed: '+relative)
    operator_path = root/'response-operator.json'
    operator = NativeResponseOperator.load(operator_path)  # Read-only full native-calibration reconstruction.
    state = operator.state
    if operator._hash != audit['response_operator_analysis']['operator_representation_sha256']:
        raise ValueError('saved response operator does not match the audited representation')
    sweeps = []
    for temperature in TEMPERATURES:
        center = numerical_chain(state, .5, parser_temperature=temperature, institution_temperature=temperature)
        changed = deepcopy(state)
        changed['temperature'] = temperature
        reference = NativeResponseOperator(changed)
        original = reference.backward([.5])
        if not math.isclose(center['gradient'], original['gradient'][0], rel_tol=1e-10, abs_tol=1e-14):
            raise ValueError('instrumented derivative does not match the original unchanged representation')
        memory_cut = numerical_chain(state, .5, parser_temperature=temperature,
            institution_temperature=temperature, detach_memory=True)
        if not math.isclose(memory_cut['loss'], center['loss'], abs_tol=1e-14, rel_tol=1e-14):
            raise ValueError('backward-only memory cut altered forward values')
        calibration = [{'theta': p['coordinate_values']['evidence-weight'], 'native_loss': p['native_loss'],
            'represented_loss': float(reference.value([p['coordinate_values']['evidence-weight']])[0].detach())}
            for p in state['calibration']]
        curve = []
        for coordinate in np.linspace(.2, .8, 61):
            value = reference.backward([float(coordinate)])
            curve.append({'theta': float(coordinate), 'loss': value['represented_loss'], 'gradient': value['gradient'][0]})
        sweeps.append({'temperature': temperature, 'center': center,
            'memory_cut_gradient': memory_cut['gradient'],
            'memory_backward_contribution': center['gradient']-memory_cut['gradient'],
            'calibration': calibration,
            'calibration_loss_rmse': math.sqrt(sum((r['represented_loss']-r['native_loss'])**2 for r in calibration)/3),
            'frozen_coordinate_curve': curve})
    crossed = [numerical_chain(state, .5, parser_temperature=p, institution_temperature=i)
        for p in TEMPERATURES for i in TEMPERATURES]
    after = inventory(root)
    if after != before:
        raise ValueError('frozen raw changed during posthoc numerical analysis')
    value = {'schema': SCHEMA, 'classification': 'posthoc-frozen-v9-development-representation-diagnosis-not-native-results',
        'audit_file': str(audit_path), 'audit_file_sha256': file_sha256(audit_path),
        'audit_content_sha256': audit['content_sha256'], 'raw_output_root': str(root),
        'actual_native_source_commit': audit['source_commit'],
        'analysis_source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'analysis_script_sha256': file_sha256(Path(__file__)),
        'operator_file_sha256': file_sha256(operator_path), 'operator_content_sha256': read(operator_path)['content_sha256'],
        'operator_representation_sha256': operator._hash,
        'scientific_module_sha256s': audit['source_proof']['module_sha256s'],
        'frozen_raw_file_count': len(before), 'frozen_raw_inventory_sha256': digest(before), 'all_raw_bytes_unchanged': True,
        'v9_selected_temperature': state['temperature'],
        'temperatures': sweeps, 'crossed_parser_institution_temperature_center_ablations': crossed,
        'limitations': ['Posthoc old development representation only; no native counterfactual temperature effects.',
            'Higher temperature changes both forward bias and gradient sign; not evidence of native improvement.',
            'No reselection of the historical v9 temperature/proposal; unused v9 outcomes are now historical development data.',
            'Calibration raw-response error and parser/selection relaxation error remain distinct.'],
        'new_model_calls': 0, 'new_native_worlds': 0, 'new_container_executions': 0}
    value['content_sha256'] = digest(value)
    return value


def markdown(value):
    lines = ['# Posthoc v9 gradient diagnosis for v10 method development', '',
        'No fresh model/native/container calls. All old raw bytes remain unchanged.', '',
        '| temperature | center gradient | calibration loss RMSE | memory backward contribution |',
        '|---:|---:|---:|---:|']
    for entry in value['temperatures']:
        lines.append(f"| {entry['temperature']:g} | {entry['center']['gradient']:.10g} | {entry['calibration_loss_rmse']:.10g} | {entry['memory_backward_contribution']:.5g} |")
    lines.extend(['', 'Only one of 18 raw review responses has a substantial fitted slope: '
        'at theta0.5 its fitted raw score is3.8333333333 and slope1.6666666667. '
        'The other17 slopes are approximately2.28e-15 numerical fitting residuals, retained rather than zero-imputed.', '',
        'At temperature0.01 the individual integer-parse relaxation is nearly flat; '
        'the affected paper remains near score3 below the3.25 selection threshold, so the admission gate is also nearly flat. '
        'Their product, not recurrent-memory differentiation, suppresses the center gradient. '
        'At0.05 the gradient is positive, while at0.2 and1 it is negative. '
        'The smooth objective charges publication cost even for fractional acceptance of papers whose score is below that cost; '
        'publication-cost and accepted-score utility derivatives compete. Thus a larger gradient need not point in the native-improving direction.', '',
        'Selecting temperature by calibration loss-value RMSE rewards a nearly hard, locally flat representation. '
        'This does not validate the fitted response slope: the varying review is observed as3.5,3.5,4.5 at the three calibration points. '
        'A single affine fit moves its crossing earlier; the old unused0.65 failure is not repaired by this temperature diagnosis.', '',
        'Prospective method recommendation: fix a continuation schedule and step/trust rule before any new model calls; '
        'report all stages and gradient signs, retain native reevaluation as the authority, and compare with an equal-budget '
        'black-box method using the same historical development data. Do not select a temperature retrospectively by favorable native/unused outcomes.', '',
        f"Actual native source: `{value['actual_native_source_commit']}`. Operator SHA-256: `{value['operator_file_sha256']}`.",
        f"Analysis source: `{value['analysis_source_commit']}`. {value['frozen_raw_file_count']} old files checked before/after.", '',
        'All temperature curves and mixed parser/institution sweeps are offline representation ablations, not native samples or held-out evaluation.', ''])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, default=ROOT/'research/results/native-qwen-response-v9-a3.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--markdown', type=Path)
    args = parser.parse_args()
    raw = Path(read(args.audit)['raw_output_root']).resolve()
    for target in (args.output, args.markdown):
        if target and target.resolve().is_relative_to(raw):
            raise ValueError('analysis outputs must not be written inside old frozen raw')
    value = analyze(args.audit)
    write_json_atomic(args.output, value, sort_keys=True, allow_nan=False)
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(markdown(value))
    print(json.dumps({'status': 'complete-posthoc-offline', 'raw_files_unchanged': value['frozen_raw_file_count'],
        'new_model_calls': 0, 'content_sha256': value['content_sha256']}))


if __name__ == '__main__':
    main()
