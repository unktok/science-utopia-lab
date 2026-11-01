from copy import deepcopy
import json
from pathlib import Path

import pytest

from tests.optimization.test_native_discrete_policy import designs
from tests.optimization.test_native_world import loss_spec
from utopia.optimization.loss import loss_spec_sha256
from utopia.optimization.native_cost_bank import BANK_SCHEMA, optimize_bank, validate_bank


def fixture_bank():
    loss = loss_spec()
    entries = []
    for index, (system, cost) in enumerate(zip(designs(4), [-2., -2., -3., -3.])):
        entries.append({'candidate': system.to_dict(), 'system_fingerprint': system.fingerprint,
            'loss': cost, 'runs': [{'seed': 42}], 'measurements': [{
                'run_id': f'fixture-{index}', 'system_fingerprint': system.fingerprint,
                'metrics': {'native.accepted_decisions': {'status': 'measured', 'value': -cost}}}]})
    return {'schema': BANK_SCHEMA, 'loss_spec': loss, 'loss_spec_sha256': loss_spec_sha256(loss),
            'seeds': [42], 'entries': entries}


def test_exact_bank_backward_changes_probabilities_not_native_costs():
    bank = fixture_bank()
    original = deepcopy(bank)
    result = optimize_bank(bank)
    assert bank == original
    assert result['initial_expected_loss'] == -2.5
    assert result['path'][0]['gradient'] == pytest.approx([.125, .125, -.125, -.125])
    assert -3. < result['final_expected_loss'] < -2.999
    assert result['best_already_observed_native_loss'] == -3.
    assert result['new_native_executions'] == 0
    assert result['new_native_best_discovered'] is False
    assert result['transition_surrogate_used'] is False
    assert result['sampled_reinforce_estimator_used'] is False
    assert all(sum(p['probabilities']) == pytest.approx(1.) for p in result['path'])
    assert result['path'][-1]['probabilities'][2] == result['path'][-1]['probabilities'][3]


def test_actual_bank_loss_cannot_be_changed_without_measurements():
    bank = fixture_bank()
    bank['entries'][0]['loss'] = -9.
    with pytest.raises(ValueError, match='measurements'):
        validate_bank(bank)


def test_bank_design_and_seed_bindings_cannot_be_changed():
    bank = fixture_bank()
    bank['entries'][0]['system_fingerprint'] = 'changed'
    with pytest.raises(ValueError, match='identity'):
        validate_bank(bank)
    bank = fixture_bank()
    bank['entries'][0]['runs'][0]['seed'] = 99
    with pytest.raises(ValueError, match='seeds'):
        validate_bank(bank)


def test_deterministic_exact_enumeration_not_a_random_estimator():
    assert optimize_bank(fixture_bank(), steps=8) == optimize_bank(fixture_bank(), steps=8)


def test_recorded_native_bank_probability_path_replays_without_inference():
    root = Path(__file__).resolve().parents[2]
    bank = json.loads((root / 'research/artifacts/native-cost-bank-v4.json').read_text())
    recorded = json.loads((root / 'research/results/native-cost-bank-v4.json').read_text())
    replayed = optimize_bank(bank, steps=recorded['steps'], learning_rate=recorded['learning_rate'])
    assert replayed['bank_sha256'] == recorded['bank_sha256']
    assert replayed['native_costs'] == [-2., -2., -3., -3.]
    assert replayed['path'] == recorded['path']
    assert bank['seeds'] == [1301]
    assert bank['world']['source_commit'] == '8a114f37ef740f2486aa4df45034d23e90e026ea'
    assert bank['world']['model'] == 'qwen3:8b'
