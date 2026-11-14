"""Finite JSON-only waiting/routing; not scientific/cold/model evidence."""
from types import SimpleNamespace

import pytest

from scripts import finish_native_longitudinal_allocation_v1 as m


def completed(directory,plan_sha='SCRIPTED-plan',source='SCRIPTED-science',status='closed',bad_terminal_files=False):
    m.save(directory/'started.json',{
        'schema':'scienceutopia.native-longitudinal-construction-finish.v1',
        'plan_file_sha256':plan_sha,'scientific_source_commit':source,
        'preceding_analysis':str(directory.parent/'audit-chain')})
    if status=='closed':
        for name in ('report-1','report-2'):m.save(directory/name/'report.json',{'SCRIPTED':'paired'})
        files=m.same_files(directory/'report-1',directory/'report-2')
    else:files={}
    m.save(directory/'ended.json',{'status':status,'report_files':{} if bad_terminal_files else files})


def test_wait_accepts_late_construction_start_without_early_export(tmp_path):
    directory=tmp_path/'construction';ticks=[0];polls=[]
    def poll(seconds):
        polls.append(seconds);ticks[0]+=seconds;completed(directory)
    value=m.wait_construction(directory,'SCRIPTED-plan','SCRIPTED-science',
        clock=lambda:ticks[0],poll=poll)
    assert polls==[15] and value['report_files']==m.same_files(directory/'report-1',directory/'report-2')


@pytest.mark.parametrize('change',['plan','source','stopped','missing-start','files','terminal-files'])
def test_wrong_or_stopped_construction_never_proceeds(tmp_path,change):
    directory=tmp_path/'construction'
    completed(directory,plan_sha='wrong' if change=='plan' else 'SCRIPTED-plan',
        source='wrong' if change=='source' else 'SCRIPTED-science',
        status='stopped' if change=='stopped' else 'closed',bad_terminal_files=change=='terminal-files')
    if change=='missing-start':(directory/'started.json').unlink()
    if change=='files':m.save(directory/'report-2/extra.json',{'SCRIPTED':'mismatch'})
    with pytest.raises(ValueError):m.wait_construction(directory,'SCRIPTED-plan','SCRIPTED-science')


def test_finite_wait_never_fabricates_end_or_changes_original_directory(tmp_path):
    times=iter([0,0,16])
    with pytest.raises(ValueError,match='finite construction wait'):
        m.wait_construction(tmp_path/'absent','SCRIPTED-plan','SCRIPTED-science',
            seconds=15,clock=lambda:next(times),poll=lambda _:None)
    assert not (tmp_path/'absent').exists()


def test_different_audit_chain_is_not_reused(tmp_path):
    completed(tmp_path/'construction')
    with pytest.raises(ValueError,match='exact original construction'):
        m.wait_construction(tmp_path/'construction','SCRIPTED-plan','SCRIPTED-science',
            preceding_analysis=tmp_path/'different-audit-chain')


def setup_run(tmp_path,monkeypatch):
    args=SimpleNamespace(run=tmp_path/'raw',analysis=tmp_path/'audit-chain',
        construction=tmp_path/'construction',output=tmp_path/'allocation')
    m.save(args.run/'plan.json',{'schema':'scienceutopia.native-longitudinal-comparison.v1.plan',
        'source_commit':'SCRIPTED-science'})
    completed(args.construction,m.sha(args.run/'plan.json'))
    monkeypatch.setattr(m,'git_binding',lambda _: 'SCRIPTED-reader')
    return args


def test_public_route_waits_exact_pair_and_uses_existing_finite_audit_engine(tmp_path,monkeypatch):
    args=setup_run(tmp_path,monkeypatch);seen={}
    def finish(actual,**kw):
        assert actual is args and (args.output.with_name('allocation-wait')/'construction-closed.json').exists()
        seen.update(kw);m.save(args.output/'ended.json',{'status':'closed'})
    monkeypatch.setattr(m,'finish',finish);m.run(args)
    assert seen['plan_schema']=='scienceutopia.native-longitudinal-comparison.v1.plan'
    assert seen['preceding_schema']=='scienceutopia.native-longitudinal-comparison-finish.v1'
    assert seen['report_module']=='scripts.reports.native_longitudinal_search_allocation_v1'
    assert seen['report_extra_arguments']==('--construction-one',str(args.construction/'report-1'),
        '--construction-two',str(args.construction/'report-2'))
    terminal=m.read(args.output.with_name('allocation-wait')/'ended.json')
    assert terminal['status']=='closed' and terminal['new_model_calls']==0 and not terminal['publication_ready']


def test_source_change_during_wait_stops_before_export_without_science_change(tmp_path,monkeypatch):
    args=setup_run(tmp_path,monkeypatch);sources=iter(['SCRIPTED-reader','changed'])
    monkeypatch.setattr(m,'git_binding',lambda _:next(sources))
    monkeypatch.setattr(m,'finish',lambda *a,**kw:pytest.fail('must not export changed source'))
    before=m.sha(args.run/'plan.json')
    with pytest.raises(ValueError,match='source or original plan changed'):m.run(args)
    assert not args.output.exists() and m.sha(args.run/'plan.json')==before
    assert m.read(args.output.with_name('allocation-wait')/'ended.json')['status']=='stopped'


def test_report_failure_is_retained_without_retry(tmp_path,monkeypatch):
    args=setup_run(tmp_path,monkeypatch);calls=[]
    def fail(*a,**kw):calls.append(1);raise ValueError('SCRIPTED export failure')
    monkeypatch.setattr(m,'finish',fail)
    with pytest.raises(ValueError,match='SCRIPTED export failure'):m.run(args)
    assert calls==[1]
    assert m.read(args.output.with_name('allocation-wait')/'ended.json')['status']=='stopped'


def test_changed_construction_after_export_is_not_accepted(tmp_path,monkeypatch):
    args=setup_run(tmp_path,monkeypatch)
    def alter(*a,**kw):
        m.save(args.output/'ended.json',{'status':'closed'})
        m.save(args.construction/'report-1/extra.json',{'SCRIPTED':'changed after report'})
    monkeypatch.setattr(m,'finish',alter)
    with pytest.raises(ValueError,match='outputs differ'):m.run(args)
    assert m.read(args.output.with_name('allocation-wait')/'ended.json')['status']=='stopped'
