"""Literal accounting identities, not scientific gains or new native worlds."""
from copy import deepcopy
import pytest

from scripts.reports.native_terminal_cost_semantics_v1 import describe


def rows():
    # Explicit forecast-shaped SCRIPTED inputs, not the still running study.
    return [{'condition': 'SCRIPTED-reference', 'resource_cost': 200., 'uncollected_activity_cost': 0.,
             'requested_activity_cost': 200., 'scores': {'content-utility': -28.666666666666668,
                                                        'resource-aware-content': -8.666666666666668}},
            {'condition': 'SCRIPTED-control', 'resource_cost': 160., 'uncollected_activity_cost': 40.,
             'requested_activity_cost': 200., 'scores': {'content-utility': -28.666666666666668,
                                                        'resource-aware-content': -12.666666666666668}}]


def test_cost_collection_gain_remains_a_declared_gain_without_becoming_real_efficiency_or_a_veto():
    values = rows(); before = deepcopy(values)
    result = describe(values, coefficient=0.1)
    assert values == before
    contrast = result['contrast_control_minus_reference']
    assert contrast['reported_C_loss'] == -4.
    assert contrast['weighted_unpaid_cost'] == 4.
    assert contrast['requested_cost_score_diagnostic_not_optimized'] == 0.
    assert result['floating_identity_residual'] == 0.
    assert not result['loss_or_selection_changed'] and not result['publication_ready']


def test_worsening_and_noop_are_not_filtered_and_other_coefficients_are_explicit():
    for coefficient in (0., 0.05, 0.1, 1.):
        for u in (-30., -20., -10.):
            values = rows()
            for world in values:
                world['scores']['content-utility'] = u
                world['scores']['resource-aware-content'] = u + coefficient * world['resource_cost']
            # Make the second outcome genuinely worse under requested-cost
            # accounting; describing it is allowed, not a hidden rejection.
            values[1]['scores']['content-utility'] += 8
            values[1]['scores']['resource-aware-content'] += 8
            result = describe(values, coefficient=coefficient)
            assert result['status'] == 'measured-diagnostic'
            assert result['contrast_control_minus_reference']['requested_cost_score_diagnostic_not_optimized'] == pytest.approx(8)
    result = describe([rows()[0], deepcopy(rows()[0])], coefficient=0.1)
    assert all(value == 0 for value in result['contrast_control_minus_reference'].values())


@pytest.mark.parametrize('field', ['resource_cost', 'uncollected_activity_cost', 'requested_activity_cost'])
def test_unknown_is_not_zero_or_a_penalty(field):
    values = rows(); values[1][field] = None
    result = describe(values, coefficient=0.1)
    assert result['status'] == 'unavailable' and not result['unknown_cost_or_loss_imputed']
    assert result['missing'] == ['world[1].' + field]


def test_missing_loss_mapping_stays_unknown_instead_of_acquiring_a_score():
    values = rows(); values[1]['scores'] = None
    result = describe(values, coefficient=0.1)
    assert result['status'] == 'unavailable'
    assert result['missing'] == ['world[1].scores.content-utility', 'world[1].scores.resource-aware-content']


@pytest.mark.parametrize('value', [True, float('nan'), float('inf'), -1])
def test_malformed_costs_are_not_silently_sanitized(value):
    values = rows(); values[1]['uncollected_activity_cost'] = value
    with pytest.raises(ValueError, match='literal finite'):
        describe(values, coefficient=0.1)


def test_accounting_mismatch_or_wrong_declared_loss_remains_an_error():
    values = rows(); values[1]['requested_activity_cost'] = 201
    with pytest.raises(ValueError, match='requested expense'):
        describe(values, coefficient=0.1)
    with pytest.raises(ValueError, match='original declared coefficient'):
        describe(rows(), coefficient=0.2)
