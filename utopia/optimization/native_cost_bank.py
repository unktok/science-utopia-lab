"""Exact differentiable distribution objective on a frozen native outcome bank.

This is NOT sampled REINFORCE, a six-feature transition surrogate, a token
Jacobian, or source synthesis. Native costs stay fixed; policy logits train.
"""
import math
from pathlib import Path
import torch

from .loss import evaluate_loss, loss_spec_sha256, validate_loss_spec
from utopia.system import SystemSpec, validate_system_spec
from utopia.system.design_patch import digest

BANK_SCHEMA = 'scienceutopia.frozen-native-cost-bank.v1'


def validate_bank(bank):
    if bank.get('schema') != BANK_SCHEMA or not bank.get('entries') or len(bank['entries']) < 2:
        raise ValueError('at least two frozen native outcomes required')
    validate_loss_spec(bank['loss_spec'])
    if bank['loss_spec_sha256'] != loss_spec_sha256(bank['loss_spec']):
        raise ValueError('native bank loss binding differs')
    seen = set()
    for entry in bank['entries']:
        system = SystemSpec.from_dict(entry['candidate'])
        validate_system_spec(system).require_valid()
        if system.fingerprint != entry['system_fingerprint'] or system.fingerprint in seen:
            raise ValueError('native bank system identity duplicate or changed')
        seen.add(system.fingerprint)
        if (isinstance(entry['loss'], bool) or not isinstance(entry['loss'], (int, float))
                or not math.isfinite(entry['loss'])):
            raise ValueError('finite native bank loss required')
        result = evaluate_loss(bank['loss_spec'], entry['measurements'])
        if result['status'] != 'complete' or result['loss'] != entry['loss']:
            raise ValueError('native bank measurements and declared loss differ')
        if any(m['system_fingerprint'] != system.fingerprint for m in entry['measurements']):
            raise ValueError('native bank measurement design binding differs')
        if {r['seed'] for r in entry['runs']} != set(bank['seeds']) or len(entry['runs']) != len(bank['seeds']):
            raise ValueError('native bank replicate seeds differ')
    return bank


def optimize_bank(bank, *, steps=80, learning_rate=0.3):
    from utopia.utils.data_utils import file_sha256
    validate_bank(bank)
    if type(steps) is not int or steps < 1 or not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError('positive finite optimizer budget required')
    costs = torch.tensor([e['loss'] for e in bank['entries']], dtype=torch.float64)
    logits = torch.zeros(len(costs), dtype=torch.float64, requires_grad=True)
    optimizer = torch.optim.Adam([logits], lr=learning_rate)
    path = []
    for step in range(steps + 1):
        optimizer.zero_grad()
        probabilities = logits.softmax(0)
        expected = (probabilities * costs).sum()
        expected.backward()
        closed_form = probabilities.detach() * (costs - expected.detach())
        gradient_error = float((logits.grad - closed_form).abs().max())
        if gradient_error > 1e-12:
            raise ValueError('finite-bank autograd differs from exact categorical derivative')
        path.append({'step': step, 'logits': logits.detach().tolist(),
            'probabilities': probabilities.detach().tolist(),
            'expected_full_native_loss': float(expected.detach()),
            'gradient': logits.grad.detach().tolist(), 'closed_form_max_absolute_error': gradient_error})
        if step < steps:
            optimizer.step()
    return {'schema': 'scienceutopia.exact-native-bank-policy-optimization.v1',
        'bank_sha256': digest(bank), 'loss_spec_sha256': bank['loss_spec_sha256'],
        'method': 'exact-enumeration-of-frozen-native-costs-torch-backward-adam',
        'optimizer_source_sha256': file_sha256(Path(__file__)), 'torch_version': str(torch.__version__),
        'steps': steps, 'learning_rate': learning_rate, 'dtype': 'torch.float64',
        'native_costs': costs.tolist(), 'bank_size': len(costs), 'path': path,
        'initial_expected_loss': path[0]['expected_full_native_loss'],
        'final_expected_loss': path[-1]['expected_full_native_loss'],
        'best_already_observed_native_loss': float(costs.min()),
        'new_native_executions': 0, 'new_inference_calls': 0,
        'new_native_best_discovered': False, 'full_native_pathwise_autograd': False,
        'transition_surrogate_used': False, 'sampled_reinforce_estimator_used': False,
        'learned_parameters': 'categorical logits over the explicitly frozen bank only',
        'held_fixed': 'complete native SystemSpecs and audited full-run costs, fixed model/source/corpus/seeds',
        'limits': ['exact conditional finite-bank expectation, not open-ended institution/source gradient',
                   'full researcher replies are included in observed costs, but no LLM/token Jacobian is computed',
                   'no new native best, fresh native validation or scientific improvement established',
                   'does not repair the separate transition surrogate native-secant mismatch']}
