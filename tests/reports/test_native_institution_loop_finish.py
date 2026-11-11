"""Finite read-only continuation guards; no model or scientific process."""
import json

import pytest

from scripts import finish_native_institution_loop_v1 as driver
from scripts.finish_native_institution_loop_v1 import same_files, wait_closed
from types import SimpleNamespace


def test_normal_terminal_waits_for_original_writer_to_leave(tmp_path):
    (tmp_path/'terminal.json').write_text(json.dumps({'status':'closed'}))
    values=iter(['SCRIPTED same',None]);ticks=iter([0.,.5,1.])
    result=wait_closed(tmp_path,1,'SCRIPTED same',observe=lambda p:next(values),
        poll=lambda s:None,clock=lambda:next(ticks))
    assert result['original_writer_absent'] and result['original_process_exit_status'] is None


@pytest.mark.parametrize('status', ['stopped', 'unknown'])
def test_scientific_failure_does_not_dispatch_analysis_or_another_world(tmp_path,status):
    (tmp_path/'terminal.json').write_text(json.dumps({'status':status}))
    with pytest.raises(ValueError,match='science stopped'):
        wait_closed(tmp_path,1,'SCRIPTED',observe=lambda p:'SCRIPTED')


def test_missing_terminal_pid_reuse_and_finite_timeout_are_not_silently_retried(tmp_path):
    for observed,message in ((None,'disappeared'),('different','identity changed')):
        with pytest.raises(ValueError,match=message):
            wait_closed(tmp_path,1,'SCRIPTED',observe=lambda p:observed)
    ticks=iter([0.,1.])
    with pytest.raises(ValueError,match='finite wait'):
        wait_closed(tmp_path,1,'SCRIPTED',observe=lambda p:'SCRIPTED',seconds=1,clock=lambda:next(ticks))


def test_repeated_report_compares_every_filename_and_byte_not_just_json(tmp_path):
    left=tmp_path/'left';right=tmp_path/'right';left.mkdir();right.mkdir()
    for root in (left,right):
        (root/'report.json').write_text('{}');(root/'figure.svg').write_text('SCRIPTED svg')
    assert set(same_files(left,right))=={'report.json','figure.svg'}
    (right/'figure.svg').write_text('changed')
    with pytest.raises(ValueError,match='outputs differ'):same_files(left,right)


@pytest.mark.parametrize('fail', [False, True])
def test_whole_chain_dispatches_only_readonly_stages_and_never_restarts_science(tmp_path,monkeypatch,fail):
    scientific=tmp_path/'science';frozen=tmp_path/'frozen';out=tmp_path/'analysis'
    scientific.mkdir();frozen.mkdir()
    (scientific/'plan.json').write_text(json.dumps({'schema':'scienceutopia.native-institution-loop.v1.plan',
        'source_commit':'a'*40,'content_sha256':'b'*64}))
    (scientific/'started.json').write_text(json.dumps({'pid':7,'plan_sha256':'b'*64}))
    monkeypatch.setattr(driver,'git_binding',lambda p:'a'*40 if p==frozen else 'c'*40)
    monkeypatch.setattr(driver,'process_identity',lambda p:None)
    monkeypatch.setattr(driver,'wait_closed',lambda *a,**k:{'original_writer_absent':True})
    calls=[]
    def execute(command,**kwargs):
        calls.append(command)
        assert command[2] in ('scripts.audit_native_institution_loop_v1',
            'scripts.reports.pre_scale_costs_v1','scripts.reports.pre_scale_search_v1')
        if fail:return SimpleNamespace(returncode=1)
        path=__import__('pathlib').Path(command[command.index('--output')+1])
        if command[2]=='scripts.reports.pre_scale_search_v1':
            path.mkdir();(path/'report.json').write_text('{}');(path/'figure.svg').write_text('SCRIPTED')
        else:path.write_text('{}')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(driver.subprocess,'run',execute)
    args=SimpleNamespace(run=scientific,frozen_source=frozen,output=out,writer_pid=7)
    if fail:
        with pytest.raises(ValueError,match='no automatic retry'):driver.run(args)
        assert len(calls)==1
        assert json.loads((out/'ended.json').read_text())['status']=='stopped'
    else:
        driver.run(args);assert len(calls)==6
        end=json.loads((out/'ended.json').read_text())
        assert end['status']=='closed' and not end['research_goal_complete']
        assert end['new_model_calls']==end['new_native_worlds']==0
    with pytest.raises(ValueError,match='fresh output'):driver.run(args)
