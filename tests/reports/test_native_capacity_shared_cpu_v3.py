"""Capacity-only shared-host admission, never scientific readiness or inference."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from scripts import observe_native_capacity_shared_cpu_v3 as r
from scripts import diagnose_native_longitudinal_frame_capacity_v1 as base
from scripts import diagnose_native_longitudinal_frame_capacity_v3 as v3
from utopia.optimization.native_numeric_designer import save
from utopia.utils.data_utils import file_sha256


def allowance(tmp_path):
    source=tmp_path/'cpu.py';source.write_text('assert 1\n')
    return save(tmp_path/'allowances.json', {'schema':r.SCHEMA+'.inspected-cpu-allowances',
        'inspection_note':'SCRIPTED CPU arithmetic fixture, not a live host inspection',
        'source_files':{str(source):file_sha256(source)},
        'rules':[{'role':'CPU proof','exact_arguments':'/safe/python cpu.py',
                  'maximum_rss_KiB':100000,'pid':12,'started_lstart':'observed start'}]})


def assess(a, *, cpu=450, cores=18, gib=40, models=None, args='/safe/python cpu.py'):
    return r.assess(f'12 {cpu} 100 python {args}',
        f'page size of 16384 bytes\nPages free: {gib*1024**3//16384}.\nPages inactive: 0.',
        {'models':models or []},a,cores,lambda pid:'observed start',999)


def test_shared_cpu_diagnostic_profile_is_not_old_ceiling_or_science_permission(tmp_path):
    a=allowance(tmp_path);r.inspect_allowances(a);v=assess(a)
    assert v['compatible_with_declared_capacity_only_profile']
    assert v['total_host_cpu_percent']==450
    assert not v['scientific_dispatch_authorized'] and not v['exclusive_lease_proved']


@pytest.mark.parametrize('changes',[{'cpu':601},{'cores':17},{'gib':37},
    {'models':[{'name':'other'}]},{'args':'/safe/python other.py'},
    {'args':'/safe/mlx_lm cpu.py'}])
def test_incompatible_resources_still_reject(tmp_path,changes):
    assert not assess(allowance(tmp_path),**changes)['compatible_with_declared_capacity_only_profile']


def test_inspected_roles_are_source_pid_start_and_memory_bound(tmp_path):
    a=allowance(tmp_path);rules=a['rules']
    assert r.allowed(12,'/safe/python cpu.py',100,rules,lambda pid:'observed start')=='CPU proof'
    for pid,rss,start in [(13,100,'observed start'),(12,100001,'observed start'),(12,100,'new start')]:
        assert r.allowed(pid,'/safe/python cpu.py',rss,rules,lambda pid:start) is None
    (tmp_path/'cpu.py').write_text('changed\n')
    with pytest.raises(ValueError,match='source changed'):r.inspect_allowances(a)


def test_stdin_identity_and_fullmatch_are_not_blanket_python_allowances(tmp_path):
    a=allowance(tmp_path)
    # Reseal a new fixture, never edit an existing journal.
    value={k:v for k,v in a.items() if k!='content_sha256'}
    value['rules']=[{'role':'coordinator','exact_arguments':'.venv/bin/python -','maximum_rss_KiB':100}]
    from utopia.system.design_patch import digest
    value['content_sha256']=digest(value)
    with pytest.raises(ValueError,match='PID'):r.inspect_allowances(value)
    rules=[{'role':'CPU family','arguments_fullmatch':r'/safe/python cpu-[0-9]+\.py','maximum_rss_KiB':100}]
    assert r.allowed(1,'/safe/python cpu-12.py',10,rules,None)=='CPU family'
    assert r.allowed(1,'/safe/python cpu-12.py --model',10,rules,None) is None


def proof(tmp_path, *, interval=31, age=0, old=False):
    a=allowance(tmp_path);root=tmp_path/'resources';root.mkdir()
    end=datetime.now(timezone.utc)-timedelta(seconds=age)
    save(root/'started.json',{'schema':r.SCHEMA+'.started','contract':r.CONTRACT,
        'observer_sha256':file_sha256(r.__file__),'allowances':a,
        'allowances_file':str(tmp_path/'allowances.json'),
        'allowances_file_sha256':file_sha256(tmp_path/'allowances.json')})
    for i,offset in ((1,interval),(2,0)):
        save(root/f'check-{i}.json',{'schema':r.SCHEMA+'.check',
            'observed_utc':(end-timedelta(seconds=offset)).isoformat(),**assess(a)})
    save(root/'ended.json',{'schema':r.SCHEMA+'.ended','ended_utc':end.isoformat(),
        'status':'two-observations-ready' if old else 'two-capacity-only-observations-compatible'})
    return root


@pytest.mark.parametrize('changes,match',[({'interval':1},'spaced'),({'age':121},'stale'),({'old':True},'old failures')])
def test_two_fresh_spaced_observations_required(tmp_path,changes,match):
    with pytest.raises(ValueError,match=match):r.require_resources(proof(tmp_path,**changes))


def test_current_capacity_only_proof_read(tmp_path):
    assert len(r.require_resources(proof(tmp_path)))==4


def test_public_runner_uses_explicit_resource_checker_and_worker_without_old_fallback(tmp_path,monkeypatch):
    p={'schema':v3.SCHEMA+'.plan','content_sha256':'declared','worker_wall_seconds':2100,'source_commit':'fixed'}
    calls=[]
    def resource_check(path):calls.append(('resources',path));return {'sealed':'proof'}
    def execute(args,**kwargs):
        calls.append(('execute',args,kwargs));save(tmp_path/'worker-terminal.json',{'status':'closed-diagnostic-only'})
        return {'returncode':0}
    monkeypatch.setattr(base,'run_bounded',execute)
    monkeypatch.setattr(base,'require_resources',lambda path:pytest.fail('legacy resource checker called'))
    base.run(tmp_path,'resource-dir',require_plan_fn=lambda root:p,
        worker_module=v3.MODULE,resource_check_fn=resource_check)
    assert calls[0]==('resources','resource-dir')
    assert v3.MODULE in calls[1][1] and calls[1][2]['seconds']==2100
    assert base.read(tmp_path/'terminal.json')['schema']==v3.SCHEMA+'.terminal'
    assert not base.read(tmp_path/'terminal.json')['scientific_dispatch_authorized']
