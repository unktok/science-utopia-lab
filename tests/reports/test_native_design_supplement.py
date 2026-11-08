"""Actual retained all-trial/cost/outside projections, without model or world calls."""
from copy import deepcopy
import csv
import json
import math

import pytest

from scripts.reports import native_design_supplement as module
from utopia.system.design_patch import digest


@pytest.fixture(scope='module')
def inputs():
    return module.load_inputs(module.ROOT)


@pytest.fixture(scope='module')
def data(inputs):
    return module.project(*inputs)


def rehash(value):
    value['content_sha256'] = digest({k:v for k,v in value.items() if k!='content_sha256'})


def test_all_120_cross_scores_and_nulls_preserve_exact_values(inputs, data):
    original = {r['row_id']:r for r in inputs[0]['all_candidate_rows']}
    assert len(data['trials']) == len(original) == 120
    assert data['search_counts'] == {'complete':64,'generation-failure':25,'technical-failure':31}
    for row in data['trials']:
        before = original[row['row_id']]
        assert row['cross_scores'] == before['cross_scores']
        assert row['own_loss'] == before['own_loss']
        if row['status'] != 'complete':
            assert row['metrics'] == dict.fromkeys(module.METRICS)
            assert row['own_loss'] is None


def test_failed_authoring_is_charged_and_random_is_not_free_science(inputs, data):
    failures = [r for r in data['trials'] if r['status']=='generation-failure']
    assert len(failures)==25
    assert all(r['designer_host_model_seconds']>0 and r['designer_request_intents']==16 for r in failures)
    assert sum(r['designer_request_intents'] for r in data['trials'])==1387
    totals = inputs[1]['groups']['designer-proposal']['measurements']
    assert math.isclose(sum(r['designer_host_model_seconds'] for r in data['trials']),
                        totals['host_model_call_seconds']['recorded_sum'],rel_tol=1e-12)
    random = [r for r in data['per_history_method_costs'] if r['arm'].endswith(':random')]
    assert len(random)==6 and all(r['native']['physical_researcher_responses']>0 for r in random)
    assert all(r['designer']['request_intents']==0 for r in random)


def test_cost_groups_keep_nonfinal_signals_cache_subsets_and_partial_worlds(data):
    rows = data['per_history_method_costs']
    assert len(rows)==30
    assert sum(r['designer']['request_intents'] for r in rows)==1387
    assert sum(r['designer']['final_response_reported'] for r in rows)==1385
    assert all(r['designer']['unknown_usage_imputed'] is False for r in rows)
    assert all(not r['initial_reference_calibration_load_or_evaluation_costs_included'] for r in rows)
    assert any(r['native']['physical_world_directory_count']>r['native']['physical_native_worlds'] for r in rows)
    assert not data['unknown_scientist_usage_imputed_when_group_absent']


def test_90_physical_jobs_and_38_label_horizon_summaries_are_not_new_samples(data):
    assert len(data['evaluation_jobs'])==90
    assert len({r['job_id'] for r in data['evaluation_jobs']})==90
    assert len({r['policy_sha256'] for r in data['evaluation_jobs']})==15
    assert len(data['outside_metric_summaries'])==38
    for row in data['outside_metric_summaries']:
        for metric in row['metrics'].values():
            assert metric['available']==(5 if row['years']==2 else 1)
            assert metric['missing']==0
            assert metric['minimum']<=metric['mean']<=metric['maximum']
    assert not data['horizons_or_shared_jobs_counted_as_extra_replication']


def test_raw_csvs_keep_nulls_blank_and_all_job_labels(tmp_path, data):
    module.write_tables(data,tmp_path)
    with (tmp_path/'all-search-observations.csv').open() as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==120
    assert sum(r['throughput']=='' for r in rows)==56
    with (tmp_path/'evaluation-physical-observations.csv').open() as f:
        jobs=list(csv.DictReader(f))
    assert len(jobs)==90 and all(isinstance(json.loads(j['labels']),list) for j in jobs)
    with (tmp_path/'per-history-method-costs.csv').open() as f:
        assert len(list(csv.DictReader(f)))==30


def test_unknown_generation_timing_does_not_become_zero(inputs):
    report, auxiliary, scientist=deepcopy(inputs)
    body=auxiliary['proposal_runs']['run-00']['throughput:parameters']
    body['generations'][0]['measurements']['host_model_call_seconds']['all_records_known']=False
    body['measurements']['host_model_call_seconds']['all_records_known']=False
    rehash(auxiliary)
    result=module.project(report,auxiliary,scientist)
    rows=[r for r in result['trials'] if r['run']=='run-00' and r['arm']=='throughput:parameters']
    assert rows[0]['designer_host_model_seconds'] is None
    assert all(r['cumulative_designer_host_model_seconds'] is None for r in rows)


def test_source_mismatch_or_missing_generation_rejects(inputs):
    report, auxiliary, scientist=deepcopy(inputs)
    auxiliary['source_commit']='a'*40; rehash(auxiliary)
    with pytest.raises(ValueError,match='common exact source'):
        module.project(report,auxiliary,scientist)
    report, auxiliary, scientist=deepcopy(inputs)
    auxiliary['proposal_runs']['run-00']['throughput:parameters']['generations'].pop()
    rehash(auxiliary)
    with pytest.raises(ValueError,match='four designer'):
        module.project(report,auxiliary,scientist)


def test_all_five_supplement_panels_render_without_mutating_numbers(tmp_path, data):
    from scripts.figures.native_design_supplement import plot
    before=digest(data)
    plot(data,tmp_path)
    expected={'all-cross-scores-throughput','all-cross-scores-selective',
              'designer-cost-paths-throughput','designer-cost-paths-selective','outside-activity-resources-2y'}
    assert {p.stem for p in tmp_path.glob('*.png')}==expected
    assert len(list(tmp_path.glob('*.svg')))==5
    assert digest(data)==before
