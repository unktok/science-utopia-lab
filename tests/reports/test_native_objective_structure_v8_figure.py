"""Synthetic plotting tests; values are not native or scientific findings."""
from copy import deepcopy

import pytest

from scripts.analyze_native_objective_structure_v8 import ARM_IDS, FIXTURE, SCHEMA
from scripts.figures.native_objective_structure_v8 import create, figure_data
from scripts.figures.native_objective_structure_v8_methods import create as create_methods
from scripts.reports.native_objective_structure_v8_paper_slice import render_slice
from utopia.system.design_patch import digest


METRICS = ('native.accepted_decisions', 'native.rejected_decisions', 'native.review_records',
    'native.final_active_authors', 'native.final_author_resources',
    'native.institutional_context_deliveries', 'native.accepted_unreviewed_decisions',
    'native.accepted_peer_score_sum')


def report():
    counts = {'nodes_added': 1, 'nodes_removed': 0, 'edges_added': 1,
        'edges_removed': 1, 'rewired_endpoint_pairs': 1, 'source_changes': 1,
        'protocol_changes': 1, 'source_bodies_added': 1, 'source_bodies_removed': 0}
    arms = {}
    for arm_index, arm in enumerate(ARM_IDS):
        rows = []
        for index in range(4):
            own = float(index + arm_index/2)
            cross = {ARM_IDS[0]: float(-index), ARM_IDS[1]: float(index+.25)}
            cross[arm] = own
            rows.append({'generation': index//2, 'draw_index': index%2, 'status': 'complete',
                'observation': {'status': 'complete', 'loss': own},
                'cross_objective_losses': cross,
                'independent_metrics': {key: {'status': 'measured', 'value': index} for key in METRICS},
                'physical_proof': {'measurement': {'system_fingerprint': f'{arm}-{index}'}},
                'graph_changes': {'vs_initial': {'counts': counts}, 'vs_parent': {'counts': counts}}})
        arms[arm] = {'rows': rows, 'loss_path': [r['observation']['loss'] for r in rows],
            'selection': {'best_loss': float(arm_index/2), 'tie_count': 1,
                'tied_system_fingerprints': [f'{arm}-0'],
                'representative_system_fingerprint': f'{arm}-0'}}
    value = {'schema': SCHEMA, 'classification': FIXTURE, 'source_commit': 'a'*40,
        'new_model_calls': 0, 'generated_source_executions': 0, 'arms': arms,
        'selected_cross_objective_matrix': {
            ARM_IDS[0]: {ARM_IDS[0]: 0., ARM_IDS[1]: .25},
            ARM_IDS[1]: {ARM_IDS[0]: 0., ARM_IDS[1]: .5}},
        'held_out_metrics': {'status': 'not-defined-or-measured'},
        'promotion_policy': {'status': 'not-defined-or-applied'}}
    value['content_sha256'] = digest(value)
    return value


def rehash(value):
    value['content_sha256'] = digest({k: v for k, v in value.items() if k != 'content_sha256'})
    return value


def test_figure_data_preserves_real_units_and_all_graph_diffs():
    data = figure_data(report())
    assert data['scope'].endswith('no held-out or improvement claim')
    assert data['arms'][ARM_IDS[0]]['rows'][3]['loss'] == 3.
    assert data['arms'][ARM_IDS[1]]['rows'][0]['graph_changes']['vs_parent']['counts']['source_changes'] == 1


def test_synthetic_figure_renders_outside_paper_and_is_hash_bound(tmp_path):
    manifest = create(report(), tmp_path/'qa'/'native-objective-structure-v8')
    assert set(manifest['outputs']) == {'pdf', 'png', 'svg'}
    assert all(item['sha256'] for item in manifest['outputs'].values())
    with pytest.raises(ValueError, match='cannot be published'):
        create(report(), tmp_path/'paper'/'figures'/'native-objective-structure-v8')


def test_result_independent_methods_flow_renders_without_empirical_inputs(tmp_path):
    manifest = create_methods(tmp_path/'methods'/'native-objective-structure-v8-methods')
    assert manifest['result_independent'] and manifest['new_model_calls'] == 0
    assert manifest['held_out_metrics'] == 'not-defined-or-measured'
    assert set(manifest['outputs']) == {'pdf', 'png', 'svg'}


def test_scripted_fixture_cannot_generate_neurips_paper_slice(tmp_path):
    value = report()
    results = create(value, tmp_path/'results'/'figure')
    methods = create_methods(tmp_path/'methods'/'figure')
    with pytest.raises(ValueError, match='only frozen actual evidence'):
        render_slice(value, results, methods, results_tex_path='figures/results.pdf',
                     methods_tex_path='figures/methods.pdf')


@pytest.mark.parametrize('mutation,match', [
    (lambda r: r.update(content_sha256='bad'), 'hash-bound'),
    (lambda r: r['arms'][ARM_IDS[0]]['rows'][0]['independent_metrics'].pop(METRICS[0]), 'eight'),
    (lambda r: r['arms'][ARM_IDS[0]]['rows'][0]['cross_objective_losses'].__setitem__(ARM_IDS[0], 99), 'differs'),
    (lambda r: r['selected_cross_objective_matrix'][ARM_IDS[0]].__setitem__(ARM_IDS[1], 99), 'matrix differs'),
    (lambda r: r.update(held_out_metrics={'status': 'measured'}), 'hash-bound'),
])
def test_false_empirical_plot_inputs_fail_closed(mutation, match):
    value = deepcopy(report()); mutation(value)
    if value['content_sha256'] != 'bad': rehash(value)
    with pytest.raises(ValueError, match=match):
        figure_data(value)

