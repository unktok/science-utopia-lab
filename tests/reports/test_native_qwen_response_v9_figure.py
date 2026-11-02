"""Synthetic schema/render fixtures ONLY; never published as actual Qwen data."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.figures.native_qwen_response_v9 import ACTUAL,FIXTURE,NAMES,SCHEMA,create,figure_data
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256,write_json_atomic


def h(value):return hashlib.sha256(value.encode()).hexdigest()


def reseal(report):
    report['content_sha256']=digest({k:v for k,v in report.items() if k!='content_sha256'})
    return report


def fixture_report(*,candidate_loss=.4):
    """Deliberately synthetic values and identities, visibly marked as such."""
    theta=[.2,.5,.8,.35,.65,.46]
    native=[-.3,.4,-.5,.1,-.2,candidate_loss]
    predictions=[-.28,.43,-.45,.12,-.1,.3]
    rows=[]
    for i,(name,x,loss) in enumerate(zip(NAMES,theta,native)):
        a=2 if i in (1,3,5) else 1
        rows.append({'name':name,'theta':x,'native_loss':loss,'hard_represented_loss':loss,
            'response_count':2,'checkpoint_sha256':h(name),'system_fingerprint':h('system'+name),
            'objective_measurements':{'native.accepted_decisions':a,
                'native.accepted_peer_score_sum':3.25*a+.15-loss,'native.review_records':3}})
    def check(i):
        return {'status':'failed-unused-native-fidelity','checkpoint_sha256':rows[i]['checkpoint_sha256'],
            'coordinates':[theta[i]],'native_loss':native[i],'predicted_loss':predictions[i],
            'absolute_error':abs(native[i]-predictions[i])}
    backward={'coordinates':[.5],'gradient':[2.],'frozen_boundary_gradient':[.25],
        'learned_response_contribution':[1.75],'native_derivative_verified':False,
        'full_native_world_autograd':False,'represented_loss':.43}
    delta=candidate_loss-native[1]
    report={'schema':SCHEMA,'classification':ACTUAL,'fixture_kind':FIXTURE,'status':'complete',
        'source_commit':'a'*40,'world_binding':{'source_commit':'a'*40,'model_digest':h('model'),
            'corpus_sha256':h('corpus'),'seed':42,'years':2,'corpus_years':4},
        'source_proof':{'current_scientific_and_comparator_modules_match_experiment_commit':True,
            'module_sha256s':{'synthetic-fixture.py':h('fixture-source')}},
        'technical_validity':{'completed_worlds':6,'planned_world_budget':6,'failures':[],
            'all_completed_checkpoints_remeasured':True,'all_completed_raw_response_projections_rejoined':True},
        'world_order':[{'name':r['name'],'theta':r['theta']} for r in rows],
        'endpoints':rows,'physical_reply_count':12,
        'objective':{'role':'optimization-loss','hard_loss_replayed_for_every_completed_world':True,
            'loss_spec':{'id':'native-joint-v5-net-reviewed-utility'}},
        'claims':{'actual_fixed_weight_Qwen':True,'exact_Qwen_Jacobian':False,
            'full_native_world_autograd':False,'held_out_generalization':False,
            'causal_scientific_benefit':False,'new_model_calls':0,'new_native_worlds':0,
            'new_container_or_generated_source_executions':0},
        'response_operator_analysis':{'operator_representation_sha256':h('operator'),
            'all_control_check':{'status':'exact-control-invariants-verified','world_count':6},
            'freeze_order_proof':{'calibration_only_operator_reconstructed':True,'unused_outcomes_seen':0,
                'frozen_file_content_matches_current_bytes':True,'historical_creation_time_authenticated':False},
            'center_backward':backward,
            'frozen_proposal':{'proposal':{'candidate':.46,'unused_outcomes_seen':0}},
            'temperature_selection':{'selected_index':0,'unused_endpoints_seen':0,'candidates':[
                {'temperature':.05,'native_calibration_losses':native[:3],
                 'predicted_calibration_losses':predictions[:3]}]},
            'unused_checks':[check(3),check(4)],'candidate_check':check(5),
            'unused_finite_path':{'status':'failed-unused-native-finite-path-fidelity',
                'actual_native_delta':-.3,'predicted_finite_delta':-.22,
                'frozen_boundary_predicted_finite_delta':0.,'response_aware_native_error':.08,
                'frozen_boundary_native_error':.3,'native_derivative_verified':False,
                'full_native_world_autograd':False},
            'candidate_minus_center_native_loss':delta,
            'candidate_improvement_status':'improved' if delta<0 else 'worse' if delta>0 else 'tied'}}
    return reseal(report)


def write_fixture(tmp_path,report):
    path=tmp_path/'synthetic-audit.json'
    write_json_atomic(path,report,sort_keys=True,allow_nan=False)
    return path


@pytest.mark.parametrize('candidate_loss,outcome',[(.4,'tied'),(1.,'worse'),(-.2,'improved')])
def test_exact_plotted_values_keep_unfavorable_tied_and_improved_outcomes(candidate_loss,outcome):
    report=fixture_report(candidate_loss=candidate_loss)
    data=figure_data(report,allow_synthetic=True,expected_source='a'*40)
    assert data['classification']==FIXTURE
    assert data['candidate']['outcome']==outcome
    assert data['candidate']['delta']==candidate_loss-.4
    assert data['unused_finite_path']['response_error']==pytest.approx(.08)
    assert data['gradients']=={'total':2.,'frozen':.25,'response_contribution':1.75}
    assert [p['role'] for p in data['endpoints']]==['calibration']*3+['unused']*2+['frozen-candidate']


def test_render_is_deterministic_watermarked_tmp_only_png_svg_and_manifest(tmp_path):
    source=write_fixture(tmp_path,fixture_report())
    first=create(source,tmp_path/'fixture',allow_synthetic=True)
    before={k:file_sha256(v['path']) for k,v in first['outputs'].items()}
    second=create(source,tmp_path/'fixture',allow_synthetic=True)
    assert before=={k:file_sha256(v['path']) for k,v in second['outputs'].items()}
    assert set(first['outputs'])=={'png','svg'} and not (tmp_path/'fixture.pdf').exists()
    svg=Path(first['outputs']['svg']['path']).read_text()
    assert 'SCHEMA FIXTURE' in svg and 'NOT ACTUAL QWEN' in svg
    assert 'FAILED' in svg and 'tied' in svg
    assert 'Fidelity failed / unsupported' in svg
    assert first['new_model_calls']==first['new_native_worlds']==0
    assert not first['exact_Qwen_or_native_Jacobian_claim']
    assert first['audit_file_sha256']==file_sha256(source)
    assert first['content_sha256']==digest({k:v for k,v in first.items() if k!='content_sha256'})


@pytest.mark.parametrize('change,match',[
    (lambda r:r.update(content_sha256='bad'),'hash-bound'),
    (lambda r:r.update(status='valid-preserved-partial-failure'),'complete'),
    (lambda r:r.update(classification='scripted-fixture-not-native-results'),'actual-Qwen'),
    (lambda r:r.update(response_operator_analysis=None),'operator'),
    (lambda r:r['source_proof'].update(current_scientific_and_comparator_modules_match_experiment_commit=False),'source'),
    (lambda r:r['world_binding'].update(source_commit='b'*40),'source'),
    (lambda r:r['claims'].update(exact_Qwen_Jacobian=True),'claim'),
    (lambda r:r['technical_validity'].update(failures=[{'loss':None}]),'six completed'),
    (lambda r:r['endpoints'].reverse(),'six rows'),
    (lambda r:r['endpoints'][3].update(theta=.36),'coordinates'),
    (lambda r:r['endpoints'][2].update(native_loss=999.),'endpoint native loss'),
    (lambda r:r['response_operator_analysis']['center_backward'].update(learned_response_contribution=[2.]),'contribution'),
    (lambda r:r['response_operator_analysis']['frozen_proposal']['proposal'].update(candidate=.42),'candidate differs'),
    (lambda r:r['response_operator_analysis'].update(candidate_improvement_status='improved'),'outcome'),
    (lambda r:r['response_operator_analysis']['unused_checks'][0].update(predicted_loss=None),'missing predictions'),
    (lambda r:r['response_operator_analysis']['unused_finite_path'].update(response_aware_native_error=0.),'finite-change'),
])
def test_missing_mislabeled_or_inconsistent_audits_fail_closed(change,match):
    report=fixture_report();change(report)
    if match!='hash-bound':reseal(report)
    with pytest.raises(ValueError,match=match):figure_data(report,allow_synthetic=True)


def test_unsupported_predictions_are_missing_and_labelled_never_zero(tmp_path):
    report=fixture_report();analysis=report['response_operator_analysis']
    analysis['unused_checks'][0]={'status':'unsupported-record-routing-or-shape-change',
        'checkpoint_sha256':report['endpoints'][3]['checkpoint_sha256'],'native_loss':.1,
        'predicted_loss':None,'gradient':None}
    analysis['unused_finite_path']={'status':'unsupported-native-endpoint-path','predicted_finite_delta':None}
    reseal(report)
    data=figure_data(report,allow_synthetic=True)
    assert data['endpoints'][3]['predicted_loss'] is None
    assert data['unused_finite_path']['response_delta'] is None
    assert data['unused_finite_path']['actual_native_delta']==pytest.approx(-.3)
    receipt=create(write_fixture(tmp_path,report),tmp_path/'unsupported',allow_synthetic=True)
    assert 'unsupported' in Path(receipt['outputs']['svg']['path']).read_text()


def test_no_fixture_published_as_actual_or_outside_tmp_and_no_raw_mutation(tmp_path):
    source=write_fixture(tmp_path,fixture_report())
    with pytest.raises(ValueError,match='explicit test-only'):
        create(source,tmp_path/'default')
    with pytest.raises(ValueError,match='temporary directory'):
        create(source,Path.home()/'fictional-paper-assets'/'not-allowed',allow_synthetic=True)
    report=fixture_report();report['raw_output_root']=str(tmp_path/'raw');reseal(report)
    source=write_fixture(tmp_path,report)
    with pytest.raises(ValueError,match='immutable native raw'):
        create(source,tmp_path/'raw'/'not-allowed',allow_synthetic=True)
    with pytest.raises(ValueError,match='source'):
        figure_data(fixture_report(),allow_synthetic=True,expected_source='b'*40)


def coupled_fixture():
    report=fixture_report()
    report['prospective_amendment']={'id':'native-qwen-response-gradient-v9-a3'}
    report['response_coupling']={'mode':'actual-common-prefix-replay','unique_anchor_prefix_calls':1}
    report['logical_response_count']=12
    report['physical_reply_count']=report['fresh_physical_reply_count']=6
    for row in report['endpoints']:
        row['fresh_physical_reply_count']=row['replayed_response_count']=1
    return reseal(report)


def test_coupled_counts_keep_logical_replay_anchor_and_new_fresh_calls_separate(tmp_path):
    data=figure_data(coupled_fixture(),allow_synthetic=True)
    assert data['physical_reply_count']==data['fresh_physical_reply_count']==6
    assert data['logical_response_count']==12 and data['replayed_response_count']==6
    assert data['response_coupling']['unique_anchor_prefix_calls']==1
    receipt=create(write_fixture(tmp_path,coupled_fixture()),tmp_path/'coupled',allow_synthetic=True)
    svg=Path(receipt['outputs']['svg']['path']).read_text()
    assert 'anchor-origin calls counted separately from new fresh calls' in svg
    assert '6 fresh native worlds' not in svg


@pytest.mark.parametrize('change,match',[
    (lambda r:r.update(physical_reply_count=12),'coupled campaign'),
    (lambda r:r.update(logical_response_count=6),'coupled campaign'),
    (lambda r:r['endpoints'][0].update(replayed_response_count=0),'coupled endpoint'),
    (lambda r:r['response_coupling'].update(unique_anchor_prefix_calls=0),'anchor-origin'),
    (lambda r:r['response_coupling'].update(mode='unrecorded-replay'),'known a3'),
    (lambda r:r.pop('response_coupling'),'a3 requires'),
])
def test_coupled_count_or_provenance_inconsistency_is_never_normalized(change,match):
    report=coupled_fixture();change(report);reseal(report)
    with pytest.raises(ValueError,match=match):figure_data(report,allow_synthetic=True)
