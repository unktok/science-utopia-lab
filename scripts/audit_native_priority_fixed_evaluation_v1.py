"""Cold original-source audit of all frozen mixed-method evaluation policies."""
import argparse
from pathlib import Path

from scripts.audit_native_objective_fixed_evaluation_v1 import worker as common_worker


def worker(root, output):
    return common_worker(root, output, study='priority-fixed-v1')


def main():
    import json
    import os
    import subprocess
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'frozen-source', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--worker', action='store_true'); args = parser.parse_args()
    if args.worker: worker(args.run, args.output); return
    if json.loads((args.run / 'terminal.json').read_text())['status'] != 'closed':
        raise ValueError('normal mixed-method fixed evaluation closure required')
    result = subprocess.run([sys.executable, '-B', '-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()), str(Path(__file__).resolve()), '--worker', '--run', str(args.run.resolve()),
        '--frozen-source', str(args.frozen_source.resolve()), '--output', str(args.output.resolve())],
        cwd=args.frozen_source, env={**os.environ, 'PYTHONHASHSEED': '42'}, timeout=1800, check=False)
    if result.returncode: raise SystemExit(result.returncode)


if __name__ == '__main__': main()
