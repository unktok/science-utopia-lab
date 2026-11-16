"""One finite native writer and a durable actual child-exit record; no restart."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys

from scripts import run_native_corrected_choice_search_v1 as driver

PREFIX='scienceutopia.native-corrected-choice-search-writer'


def run(root):
    root=Path(root).resolve();plan=driver.require_plan(root)
    with (root/'supervisor.lock').open('a') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'writer-supervision-start.json').exists() or (root/'started.json').exists():
            raise ValueError('consumed supervised study; no scientific restart')
        argv=[sys.executable,'-B','-m','scripts.run_native_corrected_choice_search_v1','run','--output',str(root)]
        driver.save(root/'writer-supervision-start.json',{'schema':PREFIX+'-supervision.v1',
            'source_commit':plan['source_commit'],'plan_content_sha256':plan['content_sha256'],
            'supervisor_pid':os.getpid(),'command':argv,'started_utc':driver.utc(),'redispatch_allowed':False})
        try:
            child=subprocess.Popen(argv,cwd=driver.ROOT,env=dict(os.environ))
            driver.save(root/'writer-launched.json',{'source_commit':plan['source_commit'],
                'plan_content_sha256':plan['content_sha256'],'writer_pid':child.pid,'command':argv})
            code=child.wait()
        except BaseException as error:
            driver.save(root/'writer-supervision-failure.json',{'error_type':type(error).__name__,
                'error':str(error),'child_exit_status_unknown':True,'redispatch_allowed':False})
            raise
        driver.save(root/'writer-exit.json',{'schema':PREFIX+'-exit.v1','source_commit':plan['source_commit'],
            'plan_content_sha256':plan['content_sha256'],'exit_code':code,'ended_utc':driver.utc()})
        if code:raise SystemExit(code)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True)
    run(parser.parse_args().run)


if __name__=='__main__':main()
