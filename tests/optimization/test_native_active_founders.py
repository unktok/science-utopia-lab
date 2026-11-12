from copy import deepcopy

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_active_founders import from_states, measure, measure_from_checkpoints, METRIC
from utopia.system.design_patch import digest


def states():
    return [{'year': year, 'phase': 0 if year == 0 else 5,
        'native_system': {'last_year': year, 'spec': {'SCRIPTED': 'fixed'}},
        'portable': {'contract': {'binding': {'SCRIPTED': 'same'}}},
        'ecosystem_data': {'agents': [{'id': 'SCRIPTED-a', 'can_author': True, 'is_active': True},
                                     {'id': 'SCRIPTED-b', 'can_author': True, 'is_active': year < 2}]}}
        for year in range(4)]


def test_original_cohort_year0_exclusion_and_native_flags_not_resources():
    source = states(); source[1]['ecosystem_data']['agents'][0]['resources'] = 0
    before = digest(source); r = from_states(source)
    assert digest(source) == before
    assert r['value'] == 4 and r['maximum'] == 6
    assert [a['active_founders'] for a in r['annual']] == [2, 1, 1]
    assert r['annual'][0]['founders'][0]['counted_active']  # no hidden resource threshold


def test_prospective_loss_is_explicit_one_metric_not_an_extra_social_veto():
    from pathlib import Path
    from utopia.optimization.loss import load_loss_spec, evaluate_loss
    root = Path(__file__).resolve().parents[2]
    loss = load_loss_spec(root/'research/objectives/losses/native-active-founder-boundaries-v1.json')
    assert loss['per_run']['terms'] == [{'metric_id': METRIC, 'slice_id': None, 'coefficient': -1.0}]
    result = evaluate_loss(loss, [{'run_id': 'SCRIPTED-state-count',
        'metrics': {METRIC: {'status': 'measured', 'value': from_states(states())['value']}}}])
    assert result['loss'] == -4.0
    assert 'not-adopted' in loss['status']


def test_new_actors_and_absent_original_founders_keep_explicit_meaning():
    source = states()
    source[1]['ecosystem_data']['agents'].append({'id': 'SCRIPTED-new', 'can_author': True, 'is_active': True})
    source[2]['ecosystem_data']['agents'] = source[2]['ecosystem_data']['agents'][1:]
    r = from_states(source)
    assert r['initial_founder_ids'] == ['SCRIPTED-a', 'SCRIPTED-b']
    assert r['value'] == 3
    assert r['annual'][1]['founders'][0] == {'actor_id': 'SCRIPTED-a', 'present': False,
        'can_author': None, 'is_active': None, 'counted_active': False}


@pytest.mark.parametrize('change', ['missing-year', 'wrong-phase', 'new-binding', 'changed-spec',
                                   'flag-unknown', 'flag-number', 'duplicate-actor'])
def test_unknown_or_incompatible_state_never_becomes_numeric_activity(change):
    source = states()
    if change == 'missing-year': source.pop(1)
    if change == 'wrong-phase': source[2]['phase'] = 4
    if change == 'new-binding': source[2]['portable']['contract']['binding'] = {'SCRIPTED': 'other'}
    if change == 'changed-spec': source[2]['native_system']['spec'] = {'SCRIPTED': 'other'}
    if change == 'flag-unknown': source[2]['ecosystem_data']['agents'][0]['is_active'] = None
    if change == 'flag-number': source[2]['ecosystem_data']['agents'][0]['is_active'] = 1
    if change == 'duplicate-actor': source[2]['ecosystem_data']['agents'] *= 2
    with pytest.raises(ValueError): from_states(source)


def test_real_original_native_states_append_metric_without_changing_other_measurements(tmp_path,fixed_corpus):
    from tests.system.test_native_science_kernel import make_sim
    from utopia.system.native_kernel import NativeScienceKernel, legacy_world_system
    from utopia.optimization.native_world import measure_native_world
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from pathlib import Path
    sim, _ = make_sim(tmp_path/'native-active', native=NativeScienceKernel(legacy_world_system()))
    try:
        sim.run(); base = measure_native_world(sim, run_id='SCRIPTED-native-actual-states')
        before = digest(base); output = measure(sim, base)
        assert digest(base) == before
        assert all(output[k] == v for k, v in base.items() if k != 'metrics')
        assert all(output['metrics'][k] == v for k, v in base['metrics'].items())
        actual = [read_portable_checkpoint(Path(sim.output_dir)/f'portable_checkpoint_year_{y}.json.gz')
                  for y in range(sim.num_years+1)]
        assert output['metrics'][METRIC]['value'] == from_states(actual)['value'] == 24
        assert len(output['active_founder_boundary_instrument']['checkpoint_sha256s']) == 7
        paths = [Path(sim.output_dir)/f'portable_checkpoint_year_{y}.json.gz' for y in range(sim.num_years+1)]
        assert measure_from_checkpoints(base, paths) == output
        with pytest.raises(ValueError, match='distinct'):
            measure_from_checkpoints(base, [paths[0], paths[0]])
        wrong = deepcopy(base); wrong['system_fingerprint'] = 'SCRIPTED-wrong-system'
        with pytest.raises(ValueError, match='literal native system'):
            measure_from_checkpoints(wrong, paths)
        with pytest.raises(ValueError, match='nonoverwriting'): measure(sim, output)
    finally: sim.llm.response_cache.close()
