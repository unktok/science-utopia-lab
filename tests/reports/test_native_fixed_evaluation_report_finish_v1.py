import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import finish_native_fixed_evaluation_report_v1 as module


def closed(tmp_path):
    for name in ('audit-1.json','audit-2.json','costs-1.json','costs-2.json'):
        (tmp_path/name).write_text('{}')
    value={'status':'closed','audit_file_sha256':module.sha(tmp_path/'audit-1.json'),
        'cost_file_sha256':module.sha(tmp_path/'costs-1.json')}
    (tmp_path/'ended.json').write_text(json.dumps(value));return value


def test_verified_chain_returns_without_polling_or_inference(tmp_path):
    value=closed(tmp_path)
    assert module.wait_analysis(tmp_path,poll=lambda seconds:pytest.fail('no wait'))==value


def test_stopped_analysis_is_not_a_successful_figure_input(tmp_path):
    (tmp_path/'ended.json').write_text('{"status":"stopped"}')
    with pytest.raises(ValueError,match='chain stopped'):module.wait_analysis(tmp_path)


@pytest.mark.parametrize('name',['audit-1.json','audit-2.json','costs-1.json','costs-2.json'])
def test_changed_or_nonmatching_analysis_output_stops_before_any_figure(tmp_path,name):
    closed(tmp_path);(tmp_path/name).write_text('changed')
    with pytest.raises(ValueError,match='outputs differ'):module.wait_analysis(tmp_path)


def test_absent_terminal_has_finite_wait_and_is_never_fabricated(tmp_path):
    ticks=iter([0,0,86401]);pauses=[]
    with pytest.raises(ValueError,match='wait exhausted'):
        module.wait_analysis(tmp_path,clock=lambda:next(ticks),poll=lambda s:pauses.append(s))
    assert pauses==[15] and not (tmp_path/'ended.json').exists()


@pytest.mark.parametrize('first_fails',[False,True])
def test_finite_chain_records_dispatches_and_never_retries_a_failed_build(tmp_path,monkeypatch,first_fails):
    from tests.reports.test_native_fixed_evaluation_report_v1 import fixture
    from utopia.optimization.native_numeric_designer import save
    data=tmp_path/'data';data.mkdir();analysis=tmp_path/'analysis';analysis.mkdir()
    plan,audit,original,origin=fixture()
    for name,value in [('plan',plan),('original-plan',original),('origin-audit',origin)]:
        save(data/(name+'.json'),{k:v for k,v in value.items() if k!='content_sha256'})
    closed(analysis)
    (analysis/'started.json').write_text(json.dumps({
        'schema':'scienceutopia.fixed-candidate-evaluation-finish.v1',
        'plan_file_sha256':module.sha(data/'plan.json'),'scientific_source_commit':plan['source_commit']}))
    args=SimpleNamespace(analysis=analysis,plan=data/'plan.json',original_plan=data/'original-plan.json',
        origin_audit=data/'origin-audit.json',output=tmp_path/'out')
    monkeypatch.setattr(module,'git_binding',lambda root:'c'*40);calls=[]
    def build(argv,**kwargs):
        calls.append(argv);destination=Path(argv[argv.index('--output')+1])
        assert (args.output/('report-'+str(len(calls))+'.started.json')).exists()
        if first_fails:return SimpleNamespace(returncode=3)
        destination.mkdir();(destination/'report.json').write_text('{"SCRIPTED":true}')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess,'run',build)
    if first_fails:
        with pytest.raises(ValueError,match='no automatic retry'):module.run(args)
        assert len(calls)==1
    else:
        module.run(args);assert len(calls)==2
    end=json.loads((args.output/'ended.json').read_text())
    assert end['status']==('stopped' if first_fails else 'closed')
    with pytest.raises(ValueError,match='fresh report'):module.run(args)
    assert len(calls)==(1 if first_fails else 2)
