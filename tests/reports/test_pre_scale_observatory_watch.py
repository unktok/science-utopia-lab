"""Finite watcher tests with synthetic frames and clocks, never a model call."""
import json
from pathlib import Path

import pytest

from scripts.watch_pre_scale_observatory import watch
from utopia.system.design_patch import digest


def run(root,projector,*,seconds=15):
    elapsed=[0.];sleeps=[]
    def sleep(seconds):sleeps.append(seconds);elapsed[0]+=seconds
    output=root/'ui/latest.json';status=root/'ui/status.json'
    watch(root/'science-M',search_run=root/'science-O',output=output,status_output=status,
        interval=5,maximum_seconds=seconds,projector=projector,sleep=sleep,clock=lambda:elapsed[0])
    return output,status,sleeps


def frame(ordinal,*,completed=False,value=0):
    p={'observed_utc':'synthetic-'+str(ordinal),'information':{'closure_recorded':completed},
        'search':{'status':'recorded-closed' if completed else 'prepared-no-stage-terminal'},'value':value}
    return {'payload':p,'payload_sha256':digest(p),'web_sha256':'SYNTHETIC-not-a-browser-envelope'}


def test_unchanged_facts_do_not_refresh_the_research_observation_timestamp(tmp_path):
    calls=[]
    def project(*a,**kw):calls.append(kw);return frame(len(calls))
    output,status,sleeps=run(tmp_path,project)
    assert len(calls)==3 and sleeps==[5,5,5]
    assert json.loads(output.read_text())['payload']['observed_utc']=='synthetic-1'
    state=json.loads(status.read_text())
    assert state['published_frames']==1 and state['event']=='watch-ended'
    assert state['new_model_calls']==state['new_scientific_worlds']==0


def test_changed_recorded_facts_publish_a_new_frame(tmp_path):
    calls=[]
    def project(*a,**kw):calls.append(kw);return frame(len(calls),value=1 if len(calls)>1 else 0)
    output,status,_=run(tmp_path,project)
    assert json.loads(output.read_text())['payload']['observed_utc']=='synthetic-2'
    assert json.loads(status.read_text())['published_frames']==2


def test_temporary_multi_file_publication_does_not_publish_incomplete_data(tmp_path):
    calls=[]
    def project(*a,**kw):
        calls.append(kw)
        if len(calls)==1:raise FileNotFoundError('cross-scores not yet published')
        return frame(len(calls))
    output,status,_=run(tmp_path,project)
    assert json.loads(output.read_text())['payload']['observed_utc']=='synthetic-2'
    assert json.loads(status.read_text())['published_frames']==1


def test_integrity_error_stops_without_overwriting_last_dated_frame(tmp_path):
    calls=[]
    def project(*a,**kw):
        calls.append(kw)
        if len(calls)>1:raise ValueError('hash mismatch')
        return frame(1)
    with pytest.raises(ValueError,match='hash mismatch'):run(tmp_path,project)
    assert json.loads((tmp_path/'ui/latest.json').read_text())['payload']['observed_utc']=='synthetic-1'
    assert json.loads((tmp_path/'ui/status.json').read_text())['event']=='watch-stopped'


def test_three_missing_file_polls_stop_without_inventing_an_empty_snapshot(tmp_path):
    def project(*a,**kw):raise FileNotFoundError('absent')
    with pytest.raises(ValueError,match='three incomplete'):run(tmp_path,project,seconds=30)
    assert not (tmp_path/'ui/latest.json').exists()
    assert json.loads((tmp_path/'ui/status.json').read_text())['event']=='watch-stopped'


def test_normal_scientific_closure_ends_the_watcher_without_claiming_full_audits(tmp_path):
    output,status,sleeps=run(tmp_path,lambda *a,**kw:frame(1,completed=True))
    assert sleeps==[] and output.exists()
    state=json.loads(status.read_text())
    assert state['event']=='watch-ended' and 'not full audits' in state['reason']


def test_raw_study_and_existing_snapshot_are_never_overwritten(tmp_path):
    existing=tmp_path/'existing.json';existing.write_text('original')
    with pytest.raises(ValueError,match='fresh separate'):
        watch(tmp_path/'science',search_run=None,output=existing,status_output=tmp_path/'status')
    assert existing.read_text()=='original'
    with pytest.raises(ValueError,match='outside scientific'):
        watch(tmp_path/'science',search_run=None,output=tmp_path/'science/latest',status_output=tmp_path/'status')
