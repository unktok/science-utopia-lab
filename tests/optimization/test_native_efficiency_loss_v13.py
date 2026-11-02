"""Prospective objective arithmetic only; these fixtures are not world evidence."""
from pathlib import Path

import pytest

from utopia.optimization.loss import evaluate_loss, load_loss_spec, loss_spec_sha256

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'research/objectives/losses/native-reviewed-production-efficiency-v13.json'


def measured(q, r, **extra):
    return {'run_id': 'unit-only', 'metrics': {
        'native.accepted_peer_score_sum': {'status': 'measured', 'value': q},
        'native.review_records': {'status': 'measured', 'value': r}, **extra}}


def test_new_loss_is_exactly_frozen_reviewed_production_and_work():
    spec = load_loss_spec(PATH)
    assert loss_spec_sha256(spec) == '942736daf5f33b3eee254ee7b95257050b2e77ea484241127f300fea15ff0ec4'
    result = evaluate_loss(spec, [measured(8, 6)])
    assert result['status'] == 'complete' and result['loss'] == -5
    assert evaluate_loss(spec, [measured(0, 0)])['loss'] == 0
    assert evaluate_loss(spec, [measured(8, 2)])['loss'] == -7


def test_admission_count_or_institution_score_cannot_silently_change_loss():
    spec = load_loss_spec(PATH)
    extra = {'native.accepted_decisions': {'status': 'measured', 'value': 1000},
             'institution.final_score': {'status': 'measured', 'value': 999999}}
    assert evaluate_loss(spec, [measured(8, 6, **extra)])['loss'] == -5


@pytest.mark.parametrize('missing', ['native.accepted_peer_score_sum', 'native.review_records'])
def test_missing_native_measurement_remains_unavailable_not_penalty(missing):
    item = measured(8, 6)
    item['metrics'].pop(missing)
    result = evaluate_loss(load_loss_spec(PATH), [item])
    assert result['status'] != 'complete' and result['loss'] is None
