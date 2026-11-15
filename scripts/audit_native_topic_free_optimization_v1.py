"""Frozen-source cold reconstruction of all objective-conditioned topic slots."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from scripts import run_native_topic_free_optimization_v1 as driver
from scripts.audit_native_workflow_objective_loop_v1 import worker as common_worker


def worker(root, output):
    return common_worker(root, output, driver_module=driver)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'): parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--worker',action='store_true'); args=parser.parse_args()
    if args.worker: worker(args.run,args.output); return
    result = subprocess.run([sys.executable,'-B','-m','scripts.audit_native_topic_free_optimization_v1',
        '--worker','--run',str(args.run.resolve()),'--frozen-source',str(args.frozen_source.resolve()),
        '--output',str(args.output.resolve())],cwd=args.frozen_source,
        env={**os.environ,'PYTHONHASHSEED':'42'},timeout=1800,check=False)
    if result.returncode: raise SystemExit(result.returncode)


if __name__ == '__main__': main()
