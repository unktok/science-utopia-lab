"""Fresh scientific resource admission, then unchanged frozen native comparison."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import requests

from scripts import observe_native_capacity_shared_cpu_v3 as cpu
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_jobs import pinned_revision
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[1]
SOURCE='a5be8d3103854368a4bc6ba4c13eff7552e9dd15'
SCHEMA='scienceutopia.native-longitudinal-shared-cpu-dispatch.v1'
CONTRACT={**cpu.CONTRACT,'schema':SCHEMA+'.resource-contract',
    'scope':'predeclared-four-history-native-scientific-comparison',
    'scientific_dispatch_authorized':False,'resource_observation_is_not_execution_readiness':True}
PROTOCOL='research/protocols/campaigns/native-longitudinal-scientific-shared-cpu-v1.md'


def utc():return datetime.now(timezone.utc).isoformat()


def read(path):return checked(json.loads(Path(path).read_text()))


def frozen_command(source,run):
    if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=SOURCE:
        raise ValueError('unchanged tested scientific source required')
    if subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip():
        raise ValueError('clean frozen scientific source required')
    if run.exists() and (run/'started.json').exists():raise ValueError('comparison already attempted; no redispatch')
    p=read(run/'plan.json')
    if (p['source_commit']!=SOURCE or p['schema']!='scienceutopia.native-longitudinal-comparison.v1.plan'):
        raise ValueError('exact prepared scientific plan required')
    return [sys.executable,'-m','scripts.run_native_longitudinal_comparison_v1','run','--output',str(run)]


def dispatch(source,run,out,allowances_file,capacity_file,software_file):
    outer_source=pinned_revision(ROOT)
    if out.exists():raise ValueError('fresh scientific resource attempt required')
    source=source.resolve();run=run.resolve()
    if not run.is_relative_to(source/'outputs'):raise ValueError('original frozen scientific output required')
    command=frozen_command(source,run)
    capacity=read(capacity_file);software=read(software_file)
    if (capacity['scientific_source']!=SOURCE or not capacity['source_utopia_literal_to_tested_scientific_source']
            or [f['arm'] for f in capacity['frames']]!=['scalar','parent-trajectory']
            or not all(f['capacity_supported_for_this_literal_frame'] for f in capacity['frames'])
            or capacity['actual_POSTs']!={'empty_load':1,'capacity_chat':2,'total':3}
            or capacity['actual_session_exit_code']!=0 or software['source_commit']!=SOURCE
            or software['actual_terminal_exit_code']!=0):
        raise ValueError('closed exact-source software and real late-frame capacity evidence required')
    for path,sha in capacity['files'].items():
        if file_sha256(path)!=sha:raise ValueError('actual capacity evidence changed')
    allowances=cpu.inspect_allowances(read(allowances_file))
    out.mkdir(parents=True)
    save(out/'started.json',{'schema':SCHEMA+'.resource-started','contract':CONTRACT,
        'started_utc':utc(),'outer_source_commit':outer_source,'source_commit':SOURCE,'source':str(source),'run':str(run),
        'scientific_plan_sha256':file_sha256(run/'plan.json'),
        'dispatcher_sha256':file_sha256(__file__),'CPU_observer_sha256':file_sha256(cpu.__file__),
        'protocol_sha256':file_sha256(ROOT/PROTOCOL),'allowances':allowances,
        'allowances_file':str(allowances_file.resolve()),'allowances_file_sha256':file_sha256(allowances_file),
        'capacity_file':str(capacity_file.resolve()),'capacity_file_sha256':file_sha256(capacity_file),
        'software_file':str(software_file.resolve()),'software_file_sha256':file_sha256(software_file),
        'old_resource_failures_reclassified':False,'new_model_POSTs':0})
    session=requests.Session();session.trust_env=False
    identity=lambda pid:cpu.command('/bin/ps','-p',str(pid),'-o','lstart=').strip()
    for i in (1,2):
        cpu.inspect_allowances(allowances)
        raw=cpu.command('/bin/ps','-ww','-axo','pid=,pcpu=,rss=,comm=,args=')
        vm=cpu.command('/usr/bin/vm_stat');cores=int(cpu.command('/usr/sbin/sysctl','-n','hw.physicalcpu'))
        response=session.get('http://127.0.0.1:11434/api/ps',timeout=10);response.raise_for_status()
        measurement=cpu.assess(raw,vm,response.json(),allowances,cores,identity,os.getpid())
        compatible=measurement['compatible_with_declared_capacity_only_profile']
        save(out/f'check-{i}.json',{'schema':SCHEMA+'.resource-check','observed_utc':utc(),
            'raw_host_processes':raw,'raw_vm_stat':vm,'technical_measurement':measurement,
            'compatible_with_separately_declared_scientific_resource_profile':compatible,
            'scientific_execution_readiness_proved':False})
        print(json.dumps({'observation':i,'CPU_percent':measurement['total_host_cpu_percent'],
            'available_GiB':measurement['free_plus_inactive_bytes']/1024**3,
            'unknown':measurement['unclassified_processes'],'compatible':compatible}),flush=True)
        if not compatible:raise ValueError('scientific resource admission failed before dispatch')
        if i==1:time.sleep(30)
    frozen_command(source,run);cpu.inspect_allowances(allowances)
    # The frozen driver performs its own complete exact-plan/backend reconstruction
    # and actual request-bound readiness before any scientific world.
    save(out/'dispatch-started.json',{'schema':SCHEMA+'.dispatch-started','started_utc':utc(),
        'scientific_source':SOURCE,'argv':command,'working_directory':str(source),
        'automatic_retry':False,'scientific_execution_readiness_proved':False})
    execution=subprocess.run(command,cwd=source,check=False)
    save(out/'terminal.json',{'schema':SCHEMA+'.terminal','returncode':execution.returncode,
        'ended_utc':utc(),'automatic_retry':False,'scientific_source':SOURCE,
        'scientific_terminal_present':(run/'terminal.json').exists(),
        'scientific_gain_claimed':False,'publication_ready':False})
    if execution.returncode:raise ValueError('original comparison stopped; no retry')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','run','output','allowances','capacity','software'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();dispatch(a.source,a.run,a.output,a.allowances,a.capacity,a.software)
