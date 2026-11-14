"""Prospective capacity-only shared CPU profile; never relabel old250% failures."""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time

import requests

from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

SCHEMA = 'scienceutopia.capacity-shared-cpu-resource.v3'
CONTRACT = {'schema': SCHEMA+'.contract', 'scope': 'two-frame-capacity-diagnostic-only',
    'minimum_physical_cores': 18, 'maximum_total_cpu_percent': 600,
    'minimum_free_plus_inactive_bytes': 38*1024**3, 'observations': 2, 'interval_seconds': 30,
    'maximum_proof_age_seconds': 120, 'loaded_ollama_models_permitted': False,
    'unclassified_python_or_model_processes_permitted': False,
    'scientific_dispatch_authorized': False, 'exclusive_lease_proved': False}


def read(path): return checked(json.loads(Path(path).read_text()))


def command(*args): return subprocess.check_output(args,text=True,timeout=15)


def inspect_allowances(value):
    checked(value)
    if value.get('schema') != SCHEMA+'.inspected-cpu-allowances' or not value.get('inspection_note'):
        raise ValueError('explicit inspected CPU-role allowances required')
    if not value.get('source_files'):
        raise ValueError('inspected CPU source bindings required')
    for path, sha in value['source_files'].items():
        p=Path(path)
        if p.is_symlink() or file_sha256(p)!=sha: raise ValueError('inspected external CPU source changed')
    for rule in value['rules']:
        if set(rule)-{'role','exact_arguments','arguments_fullmatch','pid','started_lstart','maximum_rss_KiB'}:
            raise ValueError('unknown CPU allowance field')
        if not rule.get('role') or ('exact_arguments' in rule)==('arguments_fullmatch' in rule):
            raise ValueError('one explicit CPU-command matcher per inspected role required')
        if rule.get('exact_arguments')=='.venv/bin/python -' and not all(k in rule for k in ('pid','started_lstart')):
            raise ValueError('stdin coordinator requires observed PID and start identity')
        if type(rule.get('maximum_rss_KiB')) is not int or rule['maximum_rss_KiB']<=0:
            raise ValueError('finite inspected CPU process-memory bound required')
    return value


def allowed(pid,arguments,rss,rules,identity):
    for r in rules:
        match=(arguments==r['exact_arguments'] if 'exact_arguments' in r else
            re.fullmatch(r['arguments_fullmatch'],arguments) is not None)
        if (match and rss<=r['maximum_rss_KiB'] and ('pid' not in r or pid==r['pid'])
                and ('started_lstart' not in r or identity(pid)==r['started_lstart'])):
            return r['role']
    return None


def assess(raw,vm,loaded,allowances,cores,identity,own_pid):
    total=0.;observed=[];unknown=[]
    for line in raw.splitlines():
        pid,cpu,rss,executable,arguments=line.split(None,4);pid=int(pid);cpu=float(cpu);rss=int(rss)
        if not math.isfinite(cpu) or cpu<0 or rss<0:raise ValueError('invalid host process observation')
        total+=cpu;first=Path(arguments.split()[0]).name.lower()
        if pid==own_pid:continue
        engine=any(x in first for x in ('mlx','llama','vllm'))
        if not ('python' in first or engine):continue
        if (arguments=='/opt/homebrew/bin/ollama serve' or
                (arguments.startswith('/Applications/Ollama.app/') and arguments.endswith(' hidden'))):continue
        role=None if engine else allowed(pid,arguments,rss,allowances['rules'],identity)
        row={'pid':pid,'cpu_percent':cpu,'rss_KiB':rss,'arguments':arguments,'inspected_CPU_role':role}
        observed.append(row)
        if role is None:unknown.append(row)
    page=int(re.search(r'page size of (\d+) bytes',vm).group(1))
    available=sum(int(re.search(r'Pages '+k+r':\s+(\d+)',vm).group(1)) for k in ('free','inactive'))*page
    ready=(cores>=CONTRACT['minimum_physical_cores'] and total<=600
        and available>=38*1024**3 and not loaded['models'] and not unknown)
    return {'total_host_cpu_percent':total,'free_plus_inactive_bytes':available,
        'physical_cpu_cores':cores,'observed_python_and_model_processes':observed,
        'unclassified_processes':unknown,'loaded_models':loaded,
        'compatible_with_declared_capacity_only_profile':ready,
        'whole_machine_saturation_inferred':False,'exclusive_lease_proved':False,
        'future_model_activity_excluded':False,'scientific_dispatch_authorized':False}


def observe(output,allowances_file):
    if output.exists():raise ValueError('fresh resource attempt required')
    allowances=inspect_allowances(read(allowances_file));output.mkdir(parents=True)
    save(output/'started.json',{'schema':SCHEMA+'.started','contract':CONTRACT,
        'allowances_file':str(allowances_file.resolve()),'allowances_file_sha256':file_sha256(allowances_file),
        'allowances':allowances,'observer_sha256':file_sha256(__file__),
        'started_utc':datetime.now(timezone.utc).isoformat(),'new_inference_POSTs':0})
    session=requests.Session();session.trust_env=False
    identity=lambda pid:command('/bin/ps','-p',str(pid),'-o','lstart=').strip()
    for i in (1,2):
        inspect_allowances(allowances)
        raw=command('/bin/ps','-ww','-axo','pid=,pcpu=,rss=,comm=,args=')
        vm=command('/usr/bin/vm_stat');cores=int(command('/usr/sbin/sysctl','-n','hw.physicalcpu'))
        response=session.get('http://127.0.0.1:11434/api/ps',timeout=10);response.raise_for_status()
        value=assess(raw,vm,response.json(),allowances,cores,identity,os.getpid())
        save(output/f'check-{i}.json',{'schema':SCHEMA+'.check','observed_utc':datetime.now(timezone.utc).isoformat(),
            'raw_host_processes':raw,'raw_vm_stat':vm,**value})
        print(json.dumps({'observation':i,'CPU_percent':value['total_host_cpu_percent'],
            'available_GiB':value['free_plus_inactive_bytes']/1024**3,
            'unknown':value['unclassified_processes'],'compatible':value['compatible_with_declared_capacity_only_profile']}),flush=True)
        if not value['compatible_with_declared_capacity_only_profile']:raise ValueError('capacity-only shared CPU profile failed')
        if i==1:time.sleep(30)
    save(output/'ended.json',{'schema':SCHEMA+'.ended','status':'two-capacity-only-observations-compatible',
        'ended_utc':datetime.now(timezone.utc).isoformat(),'new_inference_POSTs':0,
        'scientific_dispatch_authorized':False,'exclusive_lease_proved':False})


def require_resources(directory):
    root=Path(directory);s=read(root/'started.json');e=read(root/'ended.json')
    if (s['schema']!=SCHEMA+'.started' or s['contract']!=CONTRACT
            or s['observer_sha256']!=file_sha256(__file__)
            or e['schema']!=SCHEMA+'.ended' or e['status']!='two-capacity-only-observations-compatible'):
        raise ValueError('new declared shared-CPU diagnostic proof required; old failures cannot be reused')
    inspect_allowances(s['allowances'])
    if file_sha256(s['allowances_file']) != s['allowances_file_sha256']:
        raise ValueError('inspected CPU allowances changed')
    times=[]
    for i in (1,2):
        c=read(root/f'check-{i}.json')
        if (c['schema']!=SCHEMA+'.check' or not c['compatible_with_declared_capacity_only_profile']
                or c['unclassified_processes'] or c['loaded_models']['models']
                or c['total_host_cpu_percent']>600 or c['physical_cpu_cores']<18
                or not math.isfinite(c['total_host_cpu_percent'])
                or c['total_host_cpu_percent']<0
                or c['free_plus_inactive_bytes']<38*1024**3):raise ValueError('capacity resource conditions not proved')
        times.append(datetime.fromisoformat(c['observed_utc']))
    end=datetime.fromisoformat(e['ended_utc'])
    if (times[1]-times[0]).total_seconds()<30 or not times[1]<=end:
        raise ValueError('two spaced capacity observations required')
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(e['ended_utc'])).total_seconds()
    if not 0<=age<=120:raise ValueError('capacity resource observations stale/future')
    return {str(p):file_sha256(p) for p in sorted(root.glob('*.json'))}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allowances',type=Path,required=True);a=p.parse_args();observe(a.output,a.allowances)
