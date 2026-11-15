"""Pure input/plot-data preparation, not rendered figures or real outcomes."""
from copy import deepcopy

import pytest

from scripts.reports.native_terminal_cost_interpretation_v1 import derive
from tests.reports.test_native_terminal_cost_semantics_v1 import rows
from utopia.system.design_patch import digest


def example():
    worlds = rows()
    for index, world in enumerate(worlds):
        world['condition'] = ['strong-related-reference', 'terminal-consolidation'][index]
        world['annual_resource_categories'] = [
            {'year': y, 'collected_activity_cost': 10 if index and y == 4 else 50,
             'uncollected_activity_cost': 40 if index and y == 4 else 0,
             'requested_activity_cost': 50, 'closing_active_authors': 1 if index and y == 4 else 5,
             'closing_resources': 70 if index and y == 4 else 30} for y in range(1, 5)]
    value = {'schema': 'scienceutopia.native-terminal-cost-pilot-readout.v1', 'worlds': worlds,
        'new_model_calls': 0, 'new_code_executions': 0, 'automatic_invention': False,
        'held_out_evaluation': False, 'scientific_source_commit': 'SCRIPTED-science',
        'analysis_source_commit': 'SCRIPTED-reader'}
    return {**value, 'content_sha256': digest(value)}


def test_derive_preserves_original_losses_and_records_annual_unpaid_values_without_rendering():
    value = example(); before = deepcopy(value)
    result = derive(value)
    assert value == before
    assert result['literal_readout_content_sha256'] == value['content_sha256']
    assert result['scientific_source_commit'] == 'SCRIPTED-science'
    assert result['contrast_control_minus_reference']['reported_C_loss'] == -4
    assert result['annual_cost_support'][1]['years'][-1]['uncollected_activity_cost'] == 40
    assert not result['requested_cost_score_is_optimized'] and not result['loss_or_selection_changed']
    assert not result['automatic_invention'] and not result['held_out_evaluation']
    assert not result['independent_optimizer_replications']


@pytest.mark.parametrize('field,new', [('automatic_invention', True), ('held_out_evaluation', True),
    ('new_model_calls', 1), ('schema', 'unbound-scope')])
def test_scope_changes_are_not_silently_misreported(field, new):
    value = example(); value.pop('content_sha256'); value[field] = new
    value['content_sha256'] = digest(value)
    with pytest.raises(ValueError, match='original readout scope'):
        derive(value)


def test_incomplete_annual_data_do_not_create_a_complete_four_year_plot():
    value = example(); value.pop('content_sha256')
    value['worlds'][1]['annual_resource_categories'].pop()
    value['content_sha256'] = digest(value)
    with pytest.raises(ValueError, match='four literal measured'):
        derive(value)
