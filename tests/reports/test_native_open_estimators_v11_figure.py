"""Deliberately scripted plotting fixtures, never actual native-Qwen results."""
from copy import deepcopy
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from scripts.figures.native_open_estimators_v11 import ACTUAL, ARMS, FIXTURE, SCHEMA, create, figure_data
from utopia.optimization.loss import load_loss_spec
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic


@pytest.fixture
def tmp_path():
    with TemporaryDirectory(prefix='scienceutopia-v11-figure-test-') as directory:
        yield Path(directory)


def h(value):
    return hashlib.sha256(value.encode()).hexdigest()


def reseal(value):
    value['content_sha256'] = digest({k:v for k,v in value.items() if k != 'content_sha256'})
    return value


def fixture_report(*, all_tied=False):
    """Invented identities, values and gradients for renderer QA ONLY."""
    arms = {}
    for arm in ARMS:
        rows, path, ties, best = [], [], [], None
        for index in range(4):
            accepted = 0 if all_tied else [0,1,1,2][index]
            q = 0 if all_tied else [0,3.3,3.9,6.8][index]
            loss = 3.25*accepted - q + .05*18
            row = {'arm':arm,'generation':index//2,'draw_index':index%2,
                'status':'complete','loss':loss,'latent':[[-.5,.7,-.1,.3][index]],
                'assignment':{'review-aggregation':['mean-evidence','minimum-evidence'][index%2]},
                'observation_id':f'synthetic-{arm}-{index}',
                'system_fingerprint':h(f'synthetic-system-{arm}-{index}'),
                'checkpoint_sha256':h(f'synthetic-checkpoint-{arm}-{index}'),
                'metrics':{key:{'status':'measured','value':value} for key,value in {
                    'native.accepted_decisions':accepted,'native.accepted_peer_score_sum':q,
                    'native.review_records':18}.items()}}
            identity = {k:row[k] for k in ('generation','draw_index','observation_id','system_fingerprint')}
            if best is None or loss < best:
                best,ties = loss,[identity]
            elif loss == best:
                ties.append(identity)
            path.append({'generation':index//2,'draw_index':index%2,'observed_loss':loss,
                'best_loss_so_far':best,'best_observation_ties':deepcopy(ties)})
            rows.append(row)
        updates = []
        for generation in range(2):
            mixed = {'gradient':None}
            if arm == 'score-control-variate':
                plain = {'logits':{'review-aggregation':[.1,-.1]},'continuous_mean':[.3]}
                gradient = plain if generation == 0 else {'logits':{'review-aggregation':[.05,-.05]},'continuous_mean':[-.2]}
                correction = {'logits':{'review-aggregation':[0.,0.]},'continuous_mean':[0.]}
                if generation:
                    correction = {'logits':{'review-aggregation':[.01,-.01]},'continuous_mean':[.02]}
                mixed.update(gradient=gradient, expectation_estimator={'status':'valid',
                    'estimator':'plain-likelihood-ratio' if generation == 0 else 'frozen-prior-control-variate-lr',
                    'gradient':gradient,'plain_gradient':plain,'correction_gradient':correction,
                    'prior_sample_ids':[] if generation == 0 else [r['observation_id'] for r in rows[:2]]})
            updates.append({'generation':generation,'generation_error':None,'mixed_report':mixed})
        arms[arm] = {'observations':rows,'incumbents':{'path':path,'best_loss':best,
            'best_observation_ties':ties,'initial_unevaluated_system_scored':False},'updates':updates}
    report = {'schema':SCHEMA,'classification':FIXTURE,'status':'complete','source_commit':'a'*40,
        'arms':arms,'physical_native_worlds':8,'logical_completed_draws':8,
        'physical_researcher_responses':16,'logical_completed_researcher_responses':16,
        'completed_wire_requests':16,'reused_responses_in_completed_worlds':0,
        'loss_spec':load_loss_spec('research/objectives/losses/native-joint-v5-net-reviewed-utility.json'),
        'matched_initial_definitions':{'matched':True},
        'claims':{'live_fixed_Qwen_researchers':False,'scripted_researcher_HTTP':True,
            **{key:False for key in ('held_out','causal_institutional_benefit','scientific_value',
                'designer_improvement_established','full_native_world_pathwise_autograd',
                'variance_reduction_established','external_authorship_authenticated')}},
        'audit':{'new_model_calls':0,'new_container_executions':0,'checkpoint_loss_reextracted':True,
            'campaign_updates_and_prior_refits_replayed':True,'all_observations_and_exact_ties_retained':True,
            'raw_inventory_sha256':h('scripted-fixture-inventory')}}
    return reseal(report)


def write_fixture(directory, report):
    source = directory/'scripted-fixture-audit.json'
    write_json_atomic(source,report,sort_keys=True,allow_nan=False)
    return source


def test_all_exact_points_latents_assignments_and_no_invented_baseline():
    report = fixture_report()
    result = figure_data(report,allow_synthetic=True)
    assert result['historical_baseline'] is None and not result['initial_system_scored']
    for arm in ARMS:
        for original, plotted in zip(report['arms'][arm]['observations'],result['rows'][arm]):
            assert all(plotted[key] == value for key,value in original.items())
    assert result['updates'][0]['estimator'] == 'plain-likelihood-ratio'
    assert result['updates'][1]['estimator'] == 'frozen-prior-control-variate-lr'
    assert result['updates'][1]['vectors']['gradient'] == [.05,-.05,-.2]


def test_unfavorable_outcome_kept_and_all_exact_ties_retained():
    report = fixture_report()
    data = figure_data(report,allow_synthetic=True)
    assert data['rows']['blackbox'][-1]['loss'] > data['rows']['blackbox'][-1]['incumbent_loss']
    tied = fixture_report(all_tied=True)
    result = figure_data(tied,allow_synthetic=True)
    assert len(tied['arms']['blackbox']['incumbents']['best_observation_ties']) == 4
    assert len(result['rows']['blackbox']) == 4


def test_deterministic_temp_only_watermarked_png_svg_and_bound_manifest(tmp_path):
    source = write_fixture(tmp_path,fixture_report())
    first = create(source,tmp_path/'plot',allow_synthetic=True)
    hashes = {k:v['sha256'] for k,v in first['outputs'].items()}
    second = create(source,tmp_path/'plot',allow_synthetic=True)
    assert hashes == {k:v['sha256'] for k,v in second['outputs'].items()}
    assert set(first['outputs']) == {'png','svg'}
    assert first['audit_file_sha256'] == file_sha256(source)
    assert first['content_sha256'] == digest({k:v for k,v in first.items() if k != 'content_sha256'})
    assert first['new_model_calls'] == first['new_native_worlds'] == first['new_container_executions'] == 0
    assert not first['optimizer_superiority_claim'] and not first['variance_reduction_claim']
    svg = Path(first['outputs']['svg']['path']).read_text()
    assert 'SCRIPTED SCHEMA FIXTURE' in svg and 'NOT ACTUAL QWEN' in svg
    assert 'NOT the decision cutoff' in svg and 'No scored initial system or historical baseline' in svg
    assert 'G0: no prior' in svg and 'G1: prior fit' in svg


@pytest.mark.parametrize('change,match',[
    (lambda r:r.update(status='in-progress'),'complete eight-world'),
    (lambda r:r.update(physical_native_worlds=7),'complete eight-world'),
    (lambda r:r.update(logical_completed_draws=7),'complete eight-world'),
    (lambda r:r.update(completed_wire_requests=15),'response / wire'),
    (lambda r:r.update(reused_responses_in_completed_worlds=1),'response / wire'),
    (lambda r:r['claims'].update(variance_reduction_established=True),'claims'),
    (lambda r:r['claims'].update(live_fixed_Qwen_researchers=True),'attribution'),
    (lambda r:r['audit'].update(checkpoint_loss_reextracted=False),'audit proofs'),
    (lambda r:r['arms']['blackbox']['observations'].pop(),'all four'),
    (lambda r:r['arms']['blackbox']['observations'][0].update(loss=0.),'loss differs'),
    (lambda r:r['arms']['blackbox']['observations'][0].update(latent=[]),'recorded one-dimensional'),
    (lambda r:r['arms']['blackbox']['incumbents'].update(initial_unevaluated_system_scored=True),'unscored initial'),
    (lambda r:r['arms']['blackbox']['incumbents']['path'][1].update(best_loss_so_far=-999.),'incumbent'),
    (lambda r:r['arms']['score-control-variate']['updates'][1]['mixed_report']['expectation_estimator'].update(prior_sample_ids=['synthetic-blackbox-0']),'preceding own-arm'),
    (lambda r:r['arms']['score-control-variate']['updates'][0]['mixed_report']['expectation_estimator'].update(estimator='frozen-prior-control-variate-lr'),'batch boundary'),
])
def test_invalid_or_scope_exceeding_report_rejected(change,match):
    report = fixture_report(); change(report); reseal(report)
    with pytest.raises(ValueError,match=match):
        figure_data(report,allow_synthetic=True)


def test_hash_source_actual_flag_and_immutable_raw_guards(tmp_path):
    report = fixture_report()
    with pytest.raises(ValueError,match='test-only'):
        figure_data(report)
    with pytest.raises(ValueError,match='source pin'):
        figure_data(report,expected_source='b'*40,allow_synthetic=True)
    bad = deepcopy(report); bad['status'] = 'in-progress'
    with pytest.raises(ValueError,match='hash bound'):
        figure_data(bad,allow_synthetic=True)
    source = write_fixture(tmp_path,report)
    with pytest.raises(ValueError,match='temporary directory'):
        create(source,Path.home()/'not-a-published-fixture',allow_synthetic=True)
    report['audit']['raw_root'] = str(tmp_path/'raw'); reseal(report)
    source = write_fixture(tmp_path,report)
    with pytest.raises(ValueError,match='immutable raw'):
        create(source,tmp_path/'raw'/'plot',allow_synthetic=True)
    report['classification'] = ACTUAL
    report['claims'].update(live_fixed_Qwen_researchers=True,scripted_researcher_HTTP=False)
    reseal(report)
    with pytest.raises(ValueError,match='source pin'):
        figure_data(report)
    with pytest.raises(ValueError,match='source replay'):
        figure_data(report,expected_source='a'*40)


def test_figure_text_fits_canvas_and_uses_four_axes(tmp_path,monkeypatch):
    import scripts.figures.native_open_estimators_v11 as module
    original_close = module.plt.close
    checked = []
    def check_and_close(fig):
        if hasattr(fig,'axes'):
            assert len(fig.axes) == 4
            fig.canvas.draw(); renderer = fig.canvas.get_renderer()
            for text in fig.texts:
                bounds = text.get_window_extent(renderer)
                assert 0 <= bounds.x0 <= bounds.x1 <= fig.bbox.width
                assert 0 <= bounds.y0 <= bounds.y1 <= fig.bbox.height
            checked.append(True)
        original_close(fig)
    monkeypatch.setattr(module.plt,'close',check_and_close)
    create(write_fixture(tmp_path,fixture_report()),tmp_path/'layout',allow_synthetic=True)
    assert checked
