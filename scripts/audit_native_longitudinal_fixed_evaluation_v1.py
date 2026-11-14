"""Cold physical/critic proof for four frozen longitudinal-access selections."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from scripts.audit_native_objective_fixed_evaluation_v1 import worker as common_worker


def worker(root, output): return common_worker(root, output, study='longitudinal-v1')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'frozen-source', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--worker', action='store_true'); args = parser.parse_args()
    if args.worker: worker(args.run, args.output); return
    result = subprocess.run([sys.executable, '-m', 'scripts.audit_native_longitudinal_fixed_evaluation_v1', '--worker',
        '--run', str(args.run.resolve()), '--frozen-source', str(args.frozen_source.resolve()),
        '--output', str(args.output.resolve())], cwd=args.frozen_source,
        env={**os.environ, 'PYTHONHASHSEED': '42'}, timeout=1800, check=False)
    if result.returncode: raise SystemExit(result.returncode)


if __name__ == '__main__': main()
