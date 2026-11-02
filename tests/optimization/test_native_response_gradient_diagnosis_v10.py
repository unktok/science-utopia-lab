"""Pure representation/unit fixtures: no native, corpus, model or container."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest
import torch

from utopia.optimization.native_response_fidelity import boundary_layout, project_response, response_replay
from utopia.optimization.native_relaxation import trace_objective
from utopia.system.design_patch import digest
from utopia.system.native_response_examples import response_gradient_system, DECLARATIONS, TERMS
from utopia.system.tensor_program import execute_tensor_program

ROOT = Path(__file__).resolve().parents[2]


def module():
    spec = importlib.util.spec_from_file_location('gradient_diagnosis_v10_unit', ROOT/'scripts/analyze_native_response_gradient_v10.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def representation_fixture():
    """Synthetic numeric trace of existing equations, not a native endpoint."""
    system = response_gradient_system('sha256:'+'a'*64).to_dict()
    ps = {n['mechanism_id']: n['parameters']['program'] for n in system['mechanisms'] if n['implementation'] == 'program.tensor.v1'}
    trace, memory = [], {}
    for year in (1, 2):
        records = [{'paper_id': 'unit-paper-'+str(year), 'conference_id': 'unit-conference'}]
        features = torch.tensor([[3., 3.]], dtype=torch.float64)
        for name in ('addressed-selection', 'loss-accounting'):
            program = ps[name]
            if name == 'addressed-selection':
                inputs = {'features': features}
                sources = {'features': {'mechanism': 'opaque-features', 'port': 'features', 'period': year, 'path': '/values'}}
            else:
                inputs = {'features': features, 'accept': selected['accept'], 'scores': selected['scores']}
                sources = {key: {'mechanism': 'opaque-features' if key == 'features' else 'addressed-selection',
                    'port': key, 'period': year, 'path': '/values'} for key in inputs}
            before = memory.get(name, {k: torch.tensor(v, dtype=torch.float64) for k, v in program['state'].items()})
            outputs, updated = execute_tensor_program(program, inputs, state=before, hard=True)
            if name == 'addressed-selection': selected = outputs
            memory[name] = updated
            trace.append({'year': year, 'mechanism': name, 'event_id': 'unit-event-'+str(len(trace)),
                'program_sha256': digest(program), 'inputs': {k: v.tolist() for k, v in inputs.items()},
                'input_sources': sources, 'state_before': {k: v.tolist() for k, v in before.items()},
                'state_after': {k: v.tolist() for k, v in updated.items()},
                'outputs': {k: v.tolist() for k, v in outputs.items()}, 'records': records})
    endpoint = {'system': system, 'trace': trace}
    layout, native, _ = boundary_layout(endpoint)
    raw = torch.cat((native, native.new_tensor([3.5]*5+[3.8333333333333335])))
    weights = torch.stack((raw, torch.zeros_like(raw)))
    weights[1, -1] = 5/3
    targets = [entry['offset'] for entry in layout if entry['mechanism'] == 'addressed-selection']
    projection = {'kind': 'positive-int-truncation-per-review-mean', 'upper': 10,
        'indices': list(range(len(native), len(raw))), 'contract': {'native_boundary_size': len(native),
            'raw_review_semantic_ids': ['unit-review-'+str(i) for i in range(6)],
            'aggregation': [{'target': target, 'sources': list(range(len(native)+3*i, len(native)+3*i+3))}
                for i, target in enumerate(targets)]}}
    return {'calibration': [endpoint], 'layout': layout, 'declarations': DECLARATIONS,
        'terms': TERMS, 'weights': weights.tolist(), 'center': [.5], 'projection': projection}


@pytest.mark.parametrize('temperature', [1., .2, .05, .01])
def test_instrumented_chain_matches_original_equations_and_component_derivatives(temperature):
    analysis, state = module(), representation_fixture()
    result = analysis.numerical_chain(state, .5, parser_temperature=temperature, institution_temperature=temperature)
    assert result['chain_gradient'] == pytest.approx(result['gradient'], rel=1e-12, abs=1e-18)
    assert sum(result['component_gradients'].values()) == pytest.approx(result['gradient'], abs=1e-15)
    theta = torch.tensor([.5], dtype=torch.float64, requires_grad=True)
    w = torch.tensor(state['weights'], dtype=torch.float64)
    raw = w[0]+(theta[0]-.5)*w[1]
    z = project_response(raw, state['projection'], hard=False, temperature=temperature)
    frames = response_replay(state['calibration'][0], state['layout'], z, theta, state['declarations'],
        hard=False, temperature=temperature)
    loss = trace_objective(frames, state['terms'])
    derivative, = torch.autograd.grad(loss, theta)
    assert result['loss'] == pytest.approx(float(loss.detach()), abs=1e-14)
    assert result['gradient'] == pytest.approx(float(derivative[0].detach()), rel=1e-12, abs=1e-18)


def test_temperature_can_change_sign_and_parser_is_only_one_chain_factor():
    analysis, state = module(), representation_fixture()
    broad = analysis.numerical_chain(state, .5, parser_temperature=.2, institution_temperature=.2)
    narrow = analysis.numerical_chain(state, .5, parser_temperature=.01, institution_temperature=.01)
    middle = analysis.numerical_chain(state, .5, parser_temperature=.05, institution_temperature=.05)
    assert broad['gradient'] < 0 < middle['gradient']
    assert abs(narrow['gradient']) < 1e-12
    assert narrow['raw_reviews'][-1]['raw_response_slope'] == pytest.approx(5/3)
    assert narrow['raw_reviews'][-1]['integer_projection_slope'] < 1e-4
    assert narrow['paper_states'][-1]['soft_admission'] < 1e-9
    split = analysis.numerical_chain(state, .5, parser_temperature=.01, institution_temperature=.2)
    assert abs(split['gradient']) > abs(narrow['gradient'])


def test_memory_detach_preserves_forward_but_cuts_only_the_recurrent_backward_path():
    analysis, state = module(), representation_fixture()
    for index in state['projection']['indices'][:3]: state['weights'][1][index] = .2
    original = analysis.numerical_chain(state, .5, parser_temperature=.2, institution_temperature=.2)
    detached = analysis.numerical_chain(state, .5, parser_temperature=.2, institution_temperature=.2, detach_memory=True)
    assert original['loss'] == detached['loss']
    assert abs(original['gradient']-detached['gradient']) > 1e-8
    assert original['paper_states'] == detached['paper_states']


def test_saved_content_hash_and_readonly_inventory_fail_closed(tmp_path):
    analysis = module()
    value = {'scope': 'unit-not-native'}
    value['content_sha256'] = digest(value)
    path = tmp_path/'unit.json'
    path.write_text(json.dumps(value))
    before = analysis.inventory(tmp_path)
    assert analysis.read(path) == value
    assert analysis.inventory(tmp_path) == before
    value['scope'] = 'tampered'
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='hash'): analysis.read(path)
    (tmp_path/'forbidden-symlink').symlink_to(path)
    with pytest.raises(ValueError, match='symlink'): analysis.inventory(tmp_path)
