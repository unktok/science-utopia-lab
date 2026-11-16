"""Original-source cold reconstruction of mixed numeric/free native histories."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from scripts import run_native_priority_method_comparison_v1 as driver
from scripts.audit_native_workflow_objective_loop_v1 import worker as common_worker


def worker(root, output):
    return common_worker(root, output, driver_module=driver)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'frozen-source', 'output'):
        p.add_argument('--' + key, type=Path, required=True)
    p.add_argument('--worker', action='store_true'); a = p.parse_args()
    if a.worker:
        worker(a.run, a.output); return
    result = subprocess.run([sys.executable, '-B', '-m', 'scripts.audit_native_priority_method_comparison_v1',
        '--worker', '--run', str(a.run.resolve()), '--frozen-source', str(a.frozen_source.resolve()),
        '--output', str(a.output.resolve())], cwd=a.frozen_source,
        env={**os.environ, 'PYTHONHASHSEED': '42'}, timeout=1800, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
