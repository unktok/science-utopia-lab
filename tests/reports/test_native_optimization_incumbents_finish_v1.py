"""Original readout waits are read-only and cannot invent a scientific closure."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import finish_native_optimization_incumbents_v1 as finish
from tests.reports.test_native_optimization_incumbents_v1 import variant,seal
from utopia.optimization.native_numeric_designer import save


def inputs(tmp_path,monkeypatch,kind='presentation-scores'):
    args=SimpleNamespace(original_output=tmp_path/'original-output',scientific_source=tmp_path/'science',
        producer_source=tmp_path/'producer',output=tmp_path/'new-analysis',producer_pid=100,producer_kind=kind)
    args.original_output.mkdir();report=variant('presentation' if kind=='presentation-scores' else 'numeric')
    for i in (1,2):save(args.original_output/('report-'+str(i)+'/report.json'),{k:v for k,v in report.items() if k!='content_sha256'})
    key='scientific_source_commit' if kind=='presentation-scores' else 'numeric_source_commit'
    start={'schema':finish.KINDS[kind]['start_schema'],'analysis_source_commit':'p'*40,key:'a'*40}
    if kind=='presentation-scores':seal(start)
    finish.save(args.original_output/'started.json',start)
    end={'status':'closed',
        'steps':[{'exit_code':0}]*finish.KINDS[kind]['steps'],
        'report_files':finish.same_files(args.original_output/'report-1',args.original_output/'report-2')}
    if kind=='presentation-scores':seal(end)
    finish.save(args.original_output/'ended.json',end)
    monkeypatch.setattr(finish,'git_binding',lambda path:'a'*40 if path==args.scientific_source else
        'p'*40 if path==args.producer_source else 'z'*40)
    return args


@pytest.mark.parametrize('kind',['presentation-scores','numeric-chain'])
def test_waits_original_normal_output_and_runs_projection_twice_without_new_science(tmp_path,monkeypatch,kind):
    args=inputs(tmp_path,monkeypatch,kind);events=[]
    identity=finish.KINDS[kind]['producer']+' '+finish.KINDS[kind]['extra']
    def wait(*a,**kw):events.append('wait');return {'analysis_writer_absent':True}
    def command(cmd,**kw):
        assert events[0]=='wait' and cmd[2]=='scripts.reports.native_optimization_incumbents_v1'
        assert kw['env']['HF_HUB_OFFLINE']=='1'
        out=Path(cmd[cmd.index('--output')+1]);out.mkdir();save(out/'report.json',{'SCRIPTED':'same pure readout'})
        events.append('projection');return SimpleNamespace(returncode=0)
    finish.run(args,observe=lambda pid:identity,wait=wait,command=command)
    assert events==['wait','projection','projection']
    end=json.loads((args.output/'ended.json').read_text())
    assert end['status']=='closed' and end['new_model_calls']==end['new_native_worlds']==0
    assert not end['original_selection_changed'] and not end['publication_ready']


@pytest.mark.parametrize('bad',['wrong-pid','stopped','changed-report','wrong-source','failed-step'])
def test_bad_original_readout_cannot_trigger_a_projection(tmp_path,monkeypatch,bad):
    args=inputs(tmp_path,monkeypatch)
    if bad=='wrong-source':
        path=args.original_output/'started.json';path.unlink();finish.save(path,seal({'schema':finish.KINDS[args.producer_kind]['start_schema'],
            'analysis_source_commit':'x'*40,'scientific_source_commit':'a'*40}))
    elif bad in ('stopped','failed-step'):
        path=args.original_output/'ended.json';end=json.loads(path.read_text());path.unlink()
        if bad=='stopped':end['status']='stopped'
        else:end['steps'][0]['exit_code']=1
        finish.save(path,seal(end))
    elif bad=='changed-report':
        save(args.original_output/'report-1/unaccounted.json',{'SCRIPTED':'not in original closed manifest'})
    identity='different task' if bad=='wrong-pid' else finish.KINDS[args.producer_kind]['producer']+' --kind scores'
    def wait(*a,**kw):
        if bad=='stopped':raise ValueError('original stopped')
        return {'analysis_writer_absent':True}
    with pytest.raises(ValueError):
        finish.run(args,observe=lambda pid:identity,wait=wait,
            command=lambda *a,**k:pytest.fail('invalid original must not project'))


def test_failed_projection_is_not_retried_or_followed_by_a_second_export(tmp_path,monkeypatch):
    args=inputs(tmp_path,monkeypatch);calls=[]
    def command(cmd,**kw):calls.append(cmd);return SimpleNamespace(returncode=1)
    with pytest.raises(ValueError,match='no retry'):
        finish.run(args,observe=lambda pid:None,wait=lambda *a,**kw:{'analysis_writer_absent':True},command=command)
    assert len(calls)==1 and not (args.output/'report-2.started.json').exists()
