"""Finite read-only journal projection into an explicitly separate local file.

No simulation/model/API dispatch. Only changed recorded facts update the data
file; unchanged polls do not manufacture fresh observation timestamps. The own
dated status journal is not proof of a currently live scientific process.
"""
import argparse
from datetime import datetime,timezone
import fcntl
import json
import os
from pathlib import Path
import time

from scripts.export_pre_scale_observatory import project
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256,write_json_atomic


def watch(information_run,*,search_run,output,status_output,interval=30,maximum_seconds=86400,
          projector=project,sleep=time.sleep,clock=time.monotonic):
    if (type(interval) is not int or not 5<=interval<=3600 or type(maximum_seconds) is not int
            or not interval<=maximum_seconds<=86400):raise ValueError('finite interval/wall allowance required')
    output=Path(output).resolve();status_output=Path(status_output).resolve()
    roots=[Path(information_run).resolve()]+([Path(search_run).resolve()] if search_run is not None else [])
    if output==status_output or any(p.is_relative_to(r) for p in (output,status_output) for r in roots):
        raise ValueError('projection outputs must be distinct and outside scientific raw records')
    if output.exists() or status_output.exists():raise ValueError('fresh separate projection/status targets required')
    code={str(p):file_sha256(p) for p in (Path(__file__).resolve(),Path(__file__).with_name('export_pre_scale_observatory.py').resolve())}
    output.parent.mkdir(parents=True,exist_ok=True);status_output.parent.mkdir(parents=True,exist_ok=True)
    start=clock();last=None;published=0;missing=0;polls=0
    metadata={'schema':'scienceutopia.pre-scale-observatory-watch.v1','pid':os.getpid(),
        'started_utc':datetime.now(timezone.utc).isoformat(),'source_files':code,
        'information_run':str(roots[0]),'search_run':str(roots[1]) if len(roots)>1 else None,
        'interval_seconds':interval,'maximum_seconds':maximum_seconds,
        'new_model_calls':0,'new_scientific_worlds':0,'independent_scientific_audit':False}
    def record(event,**extra):
        value={**metadata,'event':event,'observed_utc':datetime.now(timezone.utc).isoformat(),
            'polls':polls,'published_frames':published,**extra}
        write_json_atomic(status_output,{**value,'content_sha256':digest(value)},sort_keys=True,allow_nan=False)
        if event!='unchanged-records':print(json.dumps(value),flush=True)
    with output.with_name(output.name+'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        # Recheck after the exclusive lock; another watcher may have won a race.
        if output.exists() or status_output.exists():raise ValueError('projection targets already owned')
        record('watch-start-recorded')
        try:
            while clock()-start<maximum_seconds:
                if any(file_sha256(path)!=expected for path,expected in code.items()):
                    raise ValueError('projection source changed; preserve the last dated frame')
                polls+=1
                try:envelope=projector(information_run,search_run=search_run)
                except FileNotFoundError as error:
                    # Separate atomic files can briefly expose an observation
                    # before its cross-score. Never invent or publish half data.
                    missing+=1;record('incomplete-file-publication',error_type=type(error).__name__)
                    if missing>=3:raise ValueError('three incomplete observations; stop rather than conceal missing evidence') from error
                else:
                    missing=0;payload=envelope['payload']
                    identity=digest({k:v for k,v in payload.items() if k!='observed_utc'})
                    if identity!=last:
                        write_json_atomic(output,envelope,sort_keys=True,allow_nan=False)
                        last=identity;published+=1;record('snapshot-exported',snapshot_sha256=envelope['payload_sha256'])
                    else:record('unchanged-records')
                    if payload['information']['closure_recorded'] and payload['search']['status']=='recorded-closed':
                        record('watch-ended',reason='scientific completion records observed, not full audits');return
                remaining=maximum_seconds-(clock()-start)
                if remaining>0:sleep(min(interval,remaining))
        except BaseException as error:
            record('watch-stopped',error_type=type(error).__name__,error=str(error));raise
        record('watch-ended',reason='finite projection allowance expired; scientific writers left untouched')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('information-run','search-run','output','status-output'):
        p.add_argument('--'+name,type=Path,required=name!='search-run')
    p.add_argument('--interval',type=int,default=30);p.add_argument('--maximum-seconds',type=int,default=86400)
    a=p.parse_args();watch(a.information_run,search_run=a.search_run,output=a.output,status_output=a.status_output,
        interval=a.interval,maximum_seconds=a.maximum_seconds)


if __name__=='__main__':main()
