"""SCRIPTED supervisor/continuation metadata, no scientist/model/native work."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import supervise_native_corrected_choice_search_v1 as supervisor
from scripts import finish_native_corrected_choice_search_v1 as closure
from scripts import finish_native_corrected_choice_readouts_v1 as reports
from scripts.finish_native_priority_method_comparison_v1 import wait_supervised
from utopia.optimization.native_numeric_designer import save


@pytest.mark.parametrize('code',[0,2])
def test_supervisor_records_actual_known_child_status_and_never_refills(tmp_path,monkeypatch,code):
    plan=save(tmp_path/'plan.json',{'source_commit':'a'*40})
    monkeypatch.setattr(supervisor.driver,'require_plan',lambda root:plan)
    calls=[]
    def popen(argv,**kwargs):
        calls.append(argv)
        assert supervisor.driver.read(tmp_path/'writer-supervision-start.json')['command']==argv
        assert argv[3]=='scripts.run_native_corrected_choice_search_v1' and argv[4]=='run'
        return SimpleNamespace(pid=1234,wait=lambda:code)
    monkeypatch.setattr(supervisor.subprocess,'Popen',popen)
    if code:
        with pytest.raises(SystemExit) as e:supervisor.run(tmp_path)
        assert e.value.code==code
    else:supervisor.run(tmp_path)
    assert supervisor.driver.read(tmp_path/'writer-exit.json')['exit_code']==code
    assert supervisor.driver.read(tmp_path/'writer-launched.json')['writer_pid']==1234
    with pytest.raises(ValueError,match='no scientific restart'):supervisor.run(tmp_path)
    assert len(calls)==1


def test_unknown_child_launch_or_wait_never_becomes_a_success_exit(tmp_path,monkeypatch):
    plan=save(tmp_path/'plan.json',{'source_commit':'a'*40})
    monkeypatch.setattr(supervisor.driver,'require_plan',lambda root:plan)
    def broken(*a,**kw):raise OSError('SCRIPTED launch unknown')
    monkeypatch.setattr(supervisor.subprocess,'Popen',broken)
    with pytest.raises(OSError):supervisor.run(tmp_path)
    assert not (tmp_path/'writer-exit.json').exists()
    assert supervisor.driver.read(tmp_path/'writer-supervision-failure.json')['child_exit_status_unknown']
    with pytest.raises(ValueError):supervisor.run(tmp_path)


def test_new_supervisor_schema_is_explicit_old_schema_is_not_transplanted(tmp_path):
    plan=save(tmp_path/'plan.json',{'source_commit':'a'*40})
    save(tmp_path/'terminal.json',{'status':'closed','ended_utc':'2026-11-17T00:00:00+00:00'})
    save(tmp_path/'writer-supervision-start.json',{'schema':supervisor.PREFIX+'-supervision.v1',
        'source_commit':plan['source_commit'],'plan_content_sha256':plan['content_sha256'],'supervisor_pid':22})
    save(tmp_path/'writer-exit.json',{'schema':supervisor.PREFIX+'-exit.v1','source_commit':plan['source_commit'],
        'plan_content_sha256':plan['content_sha256'],'exit_code':0,'ended_utc':'2026-11-17T00:00:01+00:00'})
    args={'wait':lambda *a:{'original_writer_absent':True},'observe':lambda pid:None}
    with pytest.raises(ValueError,match='supervised writer'):wait_supervised(tmp_path,11,None,**args)
    assert wait_supervised(tmp_path,11,None,schema_prefix=supervisor.PREFIX,**args)['original_process_exit_status']==0


@pytest.mark.parametrize('module',[closure,reports])
@pytest.mark.parametrize('location',['reader','raw','science','symlink','existing'])
def test_continuation_path_preflight_before_waiting_or_any_creation(tmp_path,monkeypatch,module,location):
    roots={key:tmp_path/key for key in ('reader','raw','science','analysis')}
    for path in roots.values():path.mkdir()
    monkeypatch.setattr(module,'ROOT',roots['reader'])
    monkeypatch.setattr(module,'finish',lambda *a,**kw:pytest.fail('invalid output cannot enter continuation'))
    if location=='symlink':
        alias=tmp_path/'alias';alias.symlink_to(roots['reader']);out=alias/'out'
    elif location=='existing':out=tmp_path/'existing';out.mkdir()
    else:out=roots[location]/'out'
    args=SimpleNamespace(run=roots['raw'],analysis=roots['analysis'],frozen_source=roots['science'],output=out,writer_pid=11)
    with pytest.raises(ValueError,match='before waiting'):module.run(args)


def test_new_wrappers_bind_correct_scientific_schema_and_exact_paired_cost_inputs(tmp_path,monkeypatch):
    args=SimpleNamespace(run=tmp_path/'raw',analysis=tmp_path/'analysis',frozen_source=tmp_path/'science',output=tmp_path/'out',writer_pid=11)
    captured=[]
    for module in (closure,reports):
        monkeypatch.setattr(module,'finish',lambda a,**kw:captured.append(kw))
        module.run(args)
    assert captured[0]['plan_schema']==captured[1]['plan_schema']=='scienceutopia.native-corrected-choice-search.v1.plan'
    assert captured[0]['writer_wait'].keywords['schema_prefix']==supervisor.PREFIX
    assert captured[0]['audit_module']=='scripts.audit_native_corrected_choice_search_v1'
    assert captured[1]['report_module']=='scripts.reports.native_priority_method_readout_v1'
    assert '--cost-one' in captured[1]['report_extra_arguments'] and '--cost-two' in captured[1]['report_extra_arguments']
