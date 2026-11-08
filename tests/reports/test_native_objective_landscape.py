from copy import deepcopy
import json
import math

import pytest

from scripts.reports import native_design_objective_landscape as module
from scripts.reports.native_design_supplement import load_inputs
from utopia.system.design_patch import digest


@pytest.fixture(scope='module')
def report():
    return load_inputs(module.ROOT)[0]


@pytest.fixture(scope='module')
def data(report):
    return module.analyze(report)


def test_closed_input_and_all_attempts_are_preserved(report, data):
    assert data['search_slot_counts'] == {'complete': 64, 'generation-failure': 25, 'technical-failure': 31}
    assert len(data['complete_search_observations']) == 64
    assert len(data['reference_observations']) == 9
    assert data['input_report_content_sha256'] == report['content_sha256']
    assert data['input_audit_content_sha256'] == report['input_audit_content_sha256']
    assert data['new_model_calls'] == data['new_native_worlds'] == data['new_generated_code_executions'] == 0
    assert not data['held_out_values_used_to_reselect']
    assert not data['frozen_exact_selection_changed']


def test_reference_inversion_and_candidate_features_have_distinct_origins(data):
    for r in data['reference_observations']:
        a, q, n = r['AQR']
        scores = r['original_cross_scores']
        assert math.isclose(-a, scores['throughput'], abs_tol=1e-12)
        assert math.isclose(-q+.5*n, scores['efficiency'], abs_tol=1e-12)
        assert math.isclose(4*a-q+.1*n, scores['selective'], abs_tol=1e-12)
        assert r['feature_origin'].startswith('algebraic-inversion')
    assert all(r['feature_origin'] == 'retained-native-measurements'
               for r in data['complete_search_observations'])


def test_preexisting_C_and_posthoc_E_are_not_confused(data):
    c, e, u = data['point_checks']
    assert c['name'] == 'V2-selective'
    assert c['reference_best'] == 0
    assert c['search_best'] == 2.1
    assert e['name'] == 'diagnostic-E-not-an-optimized-arm'
    assert math.isclose(e['search_best'], -79/6)
    assert e['search_ids'] == ['run-02:throughput:code-and-graph:g2',
                              'run-02:throughput:code-and-graph:g3']
    assert all(r['post_hoc_observation_selection_not_optimizer_performance'] for r in (c, e, u))


def test_same_fingerprint_variation_keeps_ieee_roundoff_separate(data):
    groups = data['same_fingerprint_repeated_observations']
    assert data['same_fingerprint_different_AQR_beyond_tolerance'] == 2
    assert sum(r['differs_beyond_analysis_tolerance'] for r in groups) == 2
    assert any(0 < r['AQR_range'][1] < module.TOL for r in groups)
    assert any(math.isclose(r['AQR_range'][1], 1/3) for r in groups)


def test_coefficient_cells_are_not_replications(data):
    g = data['coefficient_grid']
    assert g['grid_count_is_not_probability_volume_or_independent_samples']
    assert len(g['alphas']) == 81 and len(g['betas']) == 51
    for key, panel in g['panels'].items():
        assert len(panel) == 51 and all(len(row) == 81 for row in panel)
        assert sum(g['point_counts'][key].values()) == 4131
    assert len(data['per_history']) == 30
    assert sum(r['completed_count'] for r in data['per_history']) == 64
    assert sum(r['declared_graph_change_completed_rows'] for r in data['per_history']) == 0


def test_analysis_does_not_mutate_input_or_exact_selection(report):
    before = digest(report)
    module.analyze(report, alphas=[0., 4.], betas=[.1, .5])
    assert digest(report) == before


@pytest.mark.parametrize('profile,alpha,beta', [([True, 1, 2], 1, 1), ([1, float('nan'), 2], 1, 1),
                                             ([1, 2, 3], float('inf'), 1)])
def test_nonfinite_or_boolean_values_reject(profile, alpha, beta):
    with pytest.raises(ValueError, match='finite'):
        module.loss(profile, alpha, beta)


def test_invalid_saved_measurement_is_not_zero_imputed(report):
    changed = deepcopy(report)
    next(r for r in changed['all_candidate_rows'] if r['status'] == 'complete')['metrics'][module.KEYS[1]]['status'] = 'unknown'
    changed['content_sha256'] = digest({k: v for k, v in changed.items() if k != 'content_sha256'})
    with pytest.raises(ValueError, match='missing measured'):
        module.analyze(changed)


def test_analytical_crossing_is_on_observed_lower_envelope(data):
    pool = data['reference_observations']+data['complete_search_observations']
    for s in data['envelope_slices']:
        assert s['lower_envelope_crossings_alpha']
        for alpha in s['lower_envelope_crossings_alpha']:
            _, ids = module.minima(pool, alpha, s['beta'])
            assert len({tuple(r['AQR']) for r in pool if r['id'] in ids}) >= 2


def test_plot_and_json_keep_data_unchanged(tmp_path, data):
    before = digest(data)
    module.plot(data, tmp_path)
    assert {p.name for p in tmp_path.iterdir()} == {'observed-objective-map.png', 'observed-objective-map.svg'}
    assert digest(data) == before
    assert json.loads(json.dumps(data)) == data
