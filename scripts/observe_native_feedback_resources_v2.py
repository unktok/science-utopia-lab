"""Two read-only local resource observations; never dispatch inference or other jobs."""
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

from utopia.optimization.native_numeric_designer import save


def command(*args):
    return subprocess.check_output(args, text=True, timeout=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('fresh resource output required')
    args.output.mkdir(parents=True)
    allowed_python_arguments = {
        '.venv/bin/python -m rrs.next_improver_cycle advance',
        '.venv/bin/python -m rrs.next_cycle advance',
        '/Users/shiro/unktok/dev/anchor-lab/.venv/bin/python way/instruments/rhm/ilc_sweep.py --v 8 --s 3 --L 3 4 5 6 --m 8 --grammars 10 --method cocluster_bp --p0 50 --eta 0.05 --pmax 2000000 --out lines/line-20261114-03/results --tag noise_coclusterbp_L',
        '/Users/shiro/unktok/dev/anchor-lab/.venv/bin/python way/instruments/rhm/ilc_sweep.py --v 8 --s 3 --L 5 --m 6 8 12 16 24 --grammars 10 --method cocluster_bp --p0 50 --eta 0.05 --pmax 2000000 --out lines/line-20261114-03/results --tag noise_coclusterbp_m',
    }
    save(args.output / 'started.json', {
        'schema': 'scienceutopia.native-feedback-resource-observation.v2',
        'started_utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
        'observations': 2, 'interval_seconds': 30, 'maximum_total_cpu_percent': 250,
        'minimum_free_plus_inactive_bytes': 38 * 1024**3,
        'allowed_external_python_arguments': sorted(allowed_python_arguments),
        'allowed_CPU_job_note': 'Previously inspected NumPy/SciPy CPU sweep; no job is changed.',
        'scientific_dispatch_allowed': False, 'new_inference_POSTs': 0,
        'exclusive_lease_proved': False, 'other_jobs_may_start_later': True,
    })
    session = requests.Session(); session.trust_env = False
    for index in (1, 2):
        raw = command('/bin/ps', '-ww', '-axo', 'pid=,pcpu=,comm=,args=')
        total = 0.; unknown = []; active = []
        for line in raw.splitlines():
            pid, cpu, executable, arguments = line.split(None, 3)
            value = float(cpu)
            if not math.isfinite(value) or value < 0:
                raise ValueError('invalid host CPU observation')
            total += value
            first = arguments.split()[0]
            python = 'python' in Path(first).name.lower()
            engine = any(word in Path(first).name.lower() for word in ('mlx', 'llama', 'vllm'))
            if python or engine:
                active.append({'pid': int(pid), 'arguments': arguments, 'cpu_percent': value})
                if (int(pid) != os.getpid() and arguments not in allowed_python_arguments
                        and arguments != '/opt/homebrew/bin/ollama serve'
                        and not (first.startswith('/Applications/Ollama.app/') and arguments.endswith(' hidden'))):
                    unknown.append(active[-1])
        vm = command('/usr/bin/vm_stat')
        page = int(re.search(r'page size of (\d+) bytes', vm).group(1))
        available = sum(int(re.search(r'Pages ' + k + r':\s+(\d+)', vm).group(1))
            for k in ('free', 'inactive')) * page
        response = session.get('http://127.0.0.1:11434/api/ps', timeout=10)
        response.raise_for_status(); loaded = response.json()
        ready = not unknown and not loaded['models'] and total <= 250 and available >= 38 * 1024**3
        save(args.output / ('check-' + str(index) + '.json'), {
            'observed_utc': datetime.now(timezone.utc).isoformat(),
            'raw_host_processes': raw, 'raw_vm_stat': vm,
            'total_host_cpu_percent': total, 'free_plus_inactive_bytes': available,
            'observed_python_and_model_executables': active,
            'unclassified_python_or_model_executables': unknown, 'loaded_models': loaded,
            'ready_under_declared_shared_resource_profile': ready,
            'exclusive_lease_proved': False, 'new_inference_POSTs': 0,
        })
        print(json.dumps({'observation': index, 'cpu_percent': total,
            'free_plus_inactive_GiB': available / 1024**3, 'unknown': unknown, 'ready': ready}), flush=True)
        if not ready:
            raise ValueError('declared resource observation failed before inference')
        if index == 1:
            time.sleep(30)
    save(args.output / 'ended.json', {'status': 'two-observations-ready',
        'ended_utc': datetime.now(timezone.utc).isoformat(), 'new_inference_POSTs': 0,
        'exclusive_lease_proved': False, 'other_projects_changed': False})


if __name__ == '__main__':
    main()
