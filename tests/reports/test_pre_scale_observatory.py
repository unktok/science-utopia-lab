"""Snapshot projection QA, never live/native inference."""
import json

import pytest

from scripts.export_pre_scale_observatory import project,reference_projection,readiness_projection,REFERENCES
from utopia.optimization.native_numeric_designer import save
from utopia.replay.campaign_adapter import web_event_stream_hash


def fixture(root):
    p=save(root/'plan.json',{'schema':'scienceutopia.pre-scale-pilot.v1.plan','source_commit':'a'*40,
        'runtime':{'SCRIPTED':'source'},'scientist':{'model':'qwen3:8b'},
        'designer':{'model':'qwen3.6:35b-mlx-64k'},'mechanism_seeds':[41001,41011,41017],
        'losses':{'throughput':{},'efficiency':{},'selective':{}}})
    save(root/'mechanisms/M0-s41001/started.json',{'identity':'M0-s41001','plan_sha256':p['content_sha256']})
    return p


def test_started_journal_never_becomes_a_live_process_or_zero_loss(tmp_path):
    fixture(tmp_path)
    e=project(tmp_path,observed_utc='2026-11-09T01:00:00+00:00');p=e['payload']
    assert len(p['information']['worlds'])==12
    assert p['information']['worlds'][0]['status']=='started-no-terminal-observation'
    assert all(r['scores'] is None for r in p['information']['worlds'])
    assert p['search']['status']=='not-dispatched' and not p['search']['selection_fixed']
    assert 'not-live-heartbeat' in p['observation_kind']
    assert e['web_sha256']==web_event_stream_hash([p])


def test_fake_closure_cannot_hide_missing_mechanism_observations(tmp_path):
    p=fixture(tmp_path)
    save(tmp_path/'mechanisms-complete.json',{'plan_sha256':p['content_sha256'],
        'all_observation_file_sha256':{}})
    with pytest.raises(ValueError,match='does not cover'):project(tmp_path)


def test_cross_source_numeric_certificate_is_rejected(tmp_path):
    p=fixture(tmp_path)
    save(tmp_path/'numeric-readiness/certificate.json',{'provider':p['designer'],
        'runtime':{'SCRIPTED':'different-source'},'cases':[]})
    with pytest.raises(ValueError,match='source/model'):project(tmp_path)


@pytest.mark.parametrize('terminal',[None,'closed','stopped'])
def test_actual_hashed_stage_records_are_not_stuck_in_prepared_state(tmp_path,terminal):
    fixture(tmp_path/'M');search=tmp_path/'O'
    p=save(search/'plan.json',{'schema':'scienceutopia.pre-scale-search.v1.plan',
        'source_commit':'b'*40,'arm_order':[]})
    start={'stage':'readiness','plan_sha256':p['content_sha256'],'pid':123,
        'started_utc':'2026-11-09T00:00:00+00:00'}
    save(search/'readiness.started.json',start)
    if terminal:
        save(search/'readiness.ended.json',{**start,'status':terminal,
            'ended_utc':'2026-11-09T00:01:00+00:00',**({'error_type':'SCRIPTEDError','error':'synthetic failure'} if terminal=='stopped' else {})})
    data=project(tmp_path/'M',search_run=search)['payload']['search']
    assert data['status']==('stage-started-no-terminal' if terminal is None else 'stage-closed' if terminal=='closed' else 'stage-stopped')
    assert data['observed_stage']=='readiness'
    assert data['stage_error_type']==('SCRIPTEDError' if terminal=='stopped' else None)


def test_stage_end_cannot_rebind_its_dispatch(tmp_path):
    fixture(tmp_path/'M');search=tmp_path/'O'
    p=save(search/'plan.json',{'schema':'scienceutopia.pre-scale-search.v1.plan','source_commit':'b'*40,'arm_order':[]})
    start={'stage':'readiness','plan_sha256':p['content_sha256'],'pid':123,'started_utc':'2026-11-09T00:00:00+00:00'}
    save(search/'readiness.started.json',start)
    save(search/'readiness.ended.json',{**start,'pid':999,'status':'closed','ended_utc':'2026-11-09T00:01:00+00:00'})
    with pytest.raises(ValueError,match='completion differs'):project(tmp_path/'M',search_run=search)


def reference_fixture(root,*,write=True):
    plan={'reference_order':list(REFERENCES),'reference_systems':{name:{'SCRIPTED':name} for name in REFERENCES}}
    start={'identity':'reference-open-seed','seed':41001,'role':'developer-reference',
        'system':plan['reference_systems']['open-seed']}
    if write:save(root/'references/open-seed/started.json',start)
    return plan,start


def test_reference_start_does_not_become_completion_or_zero_score(tmp_path):
    p,_=reference_fixture(tmp_path);rows=reference_projection(tmp_path,p)
    assert len(rows)==6 and rows[0]['status']=='started-no-terminal-observation'
    assert all(r['scores'] is None and r['observation_sha256'] is None for r in rows)
    assert all(r['status']=='not-dispatched' for r in rows[1:])


@pytest.mark.parametrize('status',['complete','failed'])
def test_reference_terminal_preserves_measured_zero_versus_failed_unknown(tmp_path,status):
    p,_=reference_fixture(tmp_path);cell=tmp_path/'references/open-seed'
    save(cell/'observation.json',{'suggestion_id':'reference-open-seed','status':status})
    save(cell/'cross-scores.json',{key:{'loss':0. if status=='complete' else None}
        for key in ('throughput','efficiency','selective')})
    row=reference_projection(tmp_path,p)[0]
    assert row['status']==status and row['observation_sha256'] is not None
    assert row['scores']==({'throughput':0.,'efficiency':0.,'selective':0.} if status=='complete' else None)


@pytest.mark.parametrize('part',['seed','system','role','identity'])
def test_reference_intent_must_match_declared_system_and_seed(tmp_path,part):
    p,start=reference_fixture(tmp_path,write=False)
    start[part]={'seed':42,'system':{'SCRIPTED':'other'},'role':'generated-candidate','identity':'other'}[part]
    save(tmp_path/'references/open-seed/started.json',start)
    with pytest.raises(ValueError,match='dispatch differs'):reference_projection(tmp_path,p)


def test_reference_never_accepts_orphan_observation(tmp_path):
    p,_=reference_fixture(tmp_path)
    save(tmp_path/'references/legacy/observation.json',{'status':'complete'})
    with pytest.raises(ValueError,match='without dispatch'):reference_projection(tmp_path,p)


def readiness_fixture(root,*,write=True):
    p={'source_commit':'b'*40,'runtime':{'SCRIPTED':'runtime'},'designer':{'SCRIPTED':'provider'}}
    numeric={'runtime':p['runtime'],'provider':p['designer'],'passed':True,
        'cases':[{'objective':name,'submitted':True} for name in ('throughput','efficiency')]}
    editor={'plan':{'source_commit':p['source_commit'],'runtime':p['runtime'],'provider':p['designer'],
        'cases':list(range(28))},'all_controls_passed':True,'records':[{'ok':True} for _ in range(28)]}
    if write:
        save(root/'numeric-readiness/certificate.json',numeric)
        save(root/'editor-readiness/calibration/certificate.json',editor)
    return p,numeric,editor


def test_readiness_counts_are_source_bound_controls_not_native_losses(tmp_path):
    p,_,_=readiness_fixture(tmp_path);r=readiness_projection(tmp_path,p)
    assert r['numeric']['accepted']==2 and r['editor']['accepted']==28
    assert r['numeric']['passed'] and r['editor']['passed']
    assert 'loss' not in r['numeric'] and 'loss' not in r['editor']


@pytest.mark.parametrize('part',['wrong-source','missing-control','nonboolean','duplicate-numeric'])
def test_readiness_cannot_promote_missing_or_cross_source_controls(tmp_path,part):
    p,n,e=readiness_fixture(tmp_path,write=False)
    if part=='wrong-source':e['plan']['source_commit']='c'*40
    if part=='missing-control':e['records'].pop()
    if part=='nonboolean':n['cases'][0]['submitted']=1
    if part=='duplicate-numeric':n['cases'][1]['objective']='throughput'
    save(tmp_path/'numeric-readiness/certificate.json',n)
    save(tmp_path/'editor-readiness/calibration/certificate.json',e)
    with pytest.raises(ValueError):readiness_projection(tmp_path,p)


def test_failed_editor_certificate_is_recorded_as_failed_not_missing_or_passed(tmp_path):
    p,_,e=readiness_fixture(tmp_path,write=False);e['all_controls_passed']=False;e['records'][-1]['ok']=False
    save(tmp_path/'editor-readiness/calibration/certificate.json',e)
    r=readiness_projection(tmp_path,p)
    assert r['editor']['accepted']==27 and not r['editor']['passed']
