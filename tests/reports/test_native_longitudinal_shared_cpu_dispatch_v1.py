"""Outer-only admission reaches the literal frozen public driver, never real HTTP."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import dispatch_native_longitudinal_shared_cpu_v1 as d
from utopia.optimization.native_numeric_designer import save


def fixtures(tmp_path,monkeypatch):
    monkeypatch.setattr(d,'pinned_revision',lambda root:'outer-frozen')
    source=tmp_path/'source';run=source/'outputs/run';run.mkdir(parents=True)
    save(run/'plan.json',{'schema':'scienceutopia.native-longitudinal-comparison.v1.plan','source_commit':d.SOURCE})
    cap=tmp_path/'capacity.json';soft=tmp_path/'software.json';a=tmp_path/'allowances.json'
    save(cap,{'scientific_source':d.SOURCE,'source_utopia_literal_to_tested_scientific_source':True,
        'frames':[{'arm':arm,'capacity_supported_for_this_literal_frame':True} for arm in ('scalar','parent-trajectory')],
        'actual_POSTs':{'empty_load':1,'capacity_chat':2,'total':3},'actual_session_exit_code':0,'files':{}})
    save(soft,{'source_commit':d.SOURCE,'actual_terminal_exit_code':0})
    save(a,{'SCRIPTED':'allowance'})
    monkeypatch.setattr(d.cpu,'inspect_allowances',lambda a:a)
    monkeypatch.setattr(d,'frozen_command',lambda source,run:['literal-frozen-public-driver',str(run)])
    monkeypatch.setattr(d.cpu,'command',lambda *args:'18' if args[-1]=='hw.physicalcpu' else 'SCRIPTED')
    monkeypatch.setattr(d.time,'sleep',lambda seconds:None)
    monkeypatch.setattr(d.requests,'Session',lambda:SimpleNamespace(get=lambda *a,**k:
        SimpleNamespace(raise_for_status=lambda:None,json=lambda:{'models':[]})))
    return source,run,tmp_path/'outer-output',a,cap,soft


def test_outer_admission_does_not_replace_frozen_readiness(tmp_path,monkeypatch):
    args=fixtures(tmp_path,monkeypatch);calls=[]
    monkeypatch.setattr(d.cpu,'assess',lambda *a:{'compatible_with_declared_capacity_only_profile':True,
        'total_host_cpu_percent':450,'free_plus_inactive_bytes':40*1024**3,'unclassified_processes':[]})
    monkeypatch.setattr(d.subprocess,'run',lambda cmd,**kw:(calls.append((cmd,kw)) or SimpleNamespace(returncode=0)))
    d.dispatch(*args)
    record=d.read(args[2]/'dispatch-started.json')
    assert not record['scientific_execution_readiness_proved']
    assert calls==[(['literal-frozen-public-driver',str(args[1])],{'cwd':args[0],'check':False})]
    assert d.read(args[2]/'terminal.json')['returncode']==0
    assert not d.read(args[2]/'terminal.json')['scientific_gain_claimed']
    with pytest.raises(ValueError,match='fresh'):d.dispatch(*args)


def test_failed_resource_admission_never_calls_scientific_driver(tmp_path,monkeypatch):
    args=fixtures(tmp_path,monkeypatch)
    monkeypatch.setattr(d.cpu,'assess',lambda *a:{'compatible_with_declared_capacity_only_profile':False,
        'total_host_cpu_percent':601,'free_plus_inactive_bytes':40*1024**3,'unclassified_processes':[]})
    monkeypatch.setattr(d.subprocess,'run',lambda *a,**k:pytest.fail('dispatched scientific driver'))
    with pytest.raises(ValueError,match='admission failed'):d.dispatch(*args)
    assert (args[2]/'check-1.json').exists()
    assert not (args[2]/'dispatch-started.json').exists()


def test_actual_frozen_command_rejects_source_or_consumed_run(tmp_path,monkeypatch):
    source=tmp_path/'source';run=source/'outputs/run';run.mkdir(parents=True)
    monkeypatch.setattr(d.subprocess,'check_output',lambda *a,**kw:'wrong source\n')
    with pytest.raises(ValueError,match='tested scientific source'):d.frozen_command(source,run)
    monkeypatch.setattr(d.subprocess,'check_output',lambda argv,**kw:d.SOURCE+'\n' if 'rev-parse' in argv else '')
    save(run/'started.json',{'already':'consumed'})
    with pytest.raises(ValueError,match='already attempted'):d.frozen_command(source,run)
