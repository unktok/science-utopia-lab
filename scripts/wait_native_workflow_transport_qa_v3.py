"""Finite resource-window wait -> one SCRIPTED native check, never real science.

The criteria observe one known external workload PID and host-wide CPU only
(for example, an inference process or the parent of a queued CPU batch).
They are not a global GPU lease or proof that no other job can start later.
Other processes are never stopped, signalled, configured or reprioritized.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from scripts.run_pre_scale_completion_chain_v1 import ENVIRONMENT, save
from utopia.optimization.native_jobs import pinned_revision
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
TEST = 'tests/reports/test_native_workflow_objective_loop_native_v1.py'


def utc(): return datetime.now(timezone.utc).isoformat()
def sha(value): return hashlib.sha256(value.encode()).hexdigest()


def observe_identity(pid):
    p = subprocess.run(['/bin/ps', '-p', str(pid), '-o', 'lstart=', '-o', 'command='],
        capture_output=True, text=True, timeout=10, check=False)
    if p.returncode == 1 and not p.stdout.strip() and not p.stderr.strip(): return None
    if p.returncode or p.stderr.strip() or not p.stdout.strip():
        raise ValueError('cannot observe external PID; absence is not established')
    return p.stdout.strip()


def cpu_total():
    p = subprocess.run(['/bin/ps', '-axo', 'pid=,pcpu='], capture_output=True,
        text=True, timeout=10, check=False, env={**os.environ, 'LC_ALL': 'C'})
    if p.returncode or p.stderr.strip(): raise ValueError('host CPU observation failed')
    values = []
    for line in p.stdout.splitlines():
        fields = line.split()
        if len(fields) != 2 or not fields[0].isdigit(): raise ValueError('invalid host CPU row')
        value = float(fields[1])
        if not math.isfinite(value) or value < 0: raise ValueError('invalid CPU observation')
        values.append(value)
    if not values: raise ValueError('empty CPU observation is not idle evidence')
    return math.fsum(values)


def wait_window(pid, identity, *, ceiling, maximum_seconds, observe=observe_identity,
        cpu=cpu_total, clock=time.monotonic, poll=time.sleep, retain=lambda row: None, source_check=lambda: None):
    if (type(ceiling) not in (int, float) or not math.isfinite(ceiling) or not 0 < ceiling <= 200
            or type(maximum_seconds) is not int or not 1 <= maximum_seconds <= 86400):
        raise ValueError('finite declared resource wait and CPU ceiling required')
    begin = clock(); consecutive = 0; checks = 0
    while True:
        if clock() - begin >= maximum_seconds:
            raise TimeoutError('finite resource wait exhausted; external work left untouched')
        source_check(); current = observe(pid)
        if current is not None and current != identity:
            raise ValueError('external PID was reused; do not infer the original job is idle')
        load = cpu()
        if type(load) not in (int, float) or not math.isfinite(load) or load < 0:
            raise ValueError('invalid host CPU measurement')
        ready = current is None and load <= ceiling
        consecutive = consecutive + 1 if ready else 0; checks += 1
        row = {'observed_utc': utc(), 'known_external_pid_absent': current is None,
            'observed_identity_sha256': None if current is None else sha(current),
            'host_total_cpu_percent': load, 'ceiling_percent': ceiling,
            'consecutive_ready_observations': consecutive, 'elapsed_seconds': clock() - begin,
            'exclusive_resource_lease_proved': False}
        retain(row)
        if clock() - begin >= maximum_seconds:
            raise TimeoutError('finite resource wait exhausted; external work left untouched')
        if consecutive == 2: return {'checks': checks, **row}
        poll(min(30, maximum_seconds - (clock() - begin)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-pid', type=int, required=True)
    parser.add_argument('--maximum-total-cpu-percent', type=float, default=200.)
    parser.add_argument('--maximum-wait-seconds', type=int, default=86400)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); out = args.output.resolve()
    if out.exists() or not out.is_relative_to(ROOT / 'outputs'):
        raise ValueError('fresh exact ignored output below this frozen source required')
    if args.wait_pid <= 0: raise ValueError('explicit positive external PID required')
    if any(os.environ.get(k) != v for k, v in ENVIRONMENT.items()):
        raise ValueError('declared offline deterministic QA environment required')
    source = pinned_revision(ROOT); identity = observe_identity(args.wait_pid)
    if identity is None:
        raise ValueError('bind a currently live external wait target, do not assume a stale PID')
    out.mkdir(parents=True)
    (out / 'checks').mkdir()
    save(out / 'started.json', {'schema': 'scienceutopia.workflow-transport-resource-qa.v3',
        'source_commit': source, 'pid': os.getpid(), 'started_utc': utc(),
        'wait_pid': args.wait_pid, 'wait_identity_sha256': sha(identity),
        'maximum_wait_seconds': args.maximum_wait_seconds,
        'maximum_total_cpu_percent': args.maximum_total_cpu_percent,
        'readiness_observations': 2, 'poll_seconds': 30, 'qa_timeout_seconds': 1800,
        'real_inference_allowed': False, 'scientific_dispatch_allowed': False,
        'retry_failed_qa': False, 'other_jobs_may_start_later': True})
    stage = 'await-observed-resource-window'; count = 0
    def source_check():
        if pinned_revision(ROOT) != source: raise ValueError('QA source changed')
    def retain(row):
        nonlocal count
        save(out / 'checks' / f'check-{count:05}.json', row); count += 1
    try:
        print(json.dumps({'stage': stage, 'wait_pid': args.wait_pid, 'real_model_calls': 0}), flush=True)
        window = wait_window(args.wait_pid, identity, ceiling=args.maximum_total_cpu_percent,
            maximum_seconds=args.maximum_wait_seconds, source_check=source_check, retain=retain)
        save(out / 'resource-window.json', window); source_check()
        stage = 'one-SCRIPTED-native-transport-check'
        base, junit = out / 'native-qa', out / 'native-qa.xml'
        # The exact parent exists before pytest; both targets are fresh.
        if base.exists() or junit.exists(): raise ValueError('fresh QA targets required')
        argv = [sys.executable, '-m', 'pytest', TEST, '-k', 'read900 and independent-numeric-v2',
            '-q', '--basetemp=' + str(base), '--junitxml=' + str(junit)]
        save(out / 'qa-started.json', {'command': argv, 'started_utc': utc()})
        print(json.dumps({'stage': stage, 'new_scientific_model_calls': 0}), flush=True)
        with (out / 'qa.log').open('x') as log:
            p = subprocess.run(argv, cwd=ROOT, env={**os.environ, **ENVIRONMENT},
                stdout=log, stderr=subprocess.STDOUT, timeout=1800, check=False)
        save(out / 'qa-ended.json', {'exit_code': p.returncode, 'ended_utc': utc()})
        if p.returncode: raise ValueError('SCRIPTED QA failed; no automatic retry or scientific dispatch')
        cases = ET.parse(junit).getroot().findall('.//testcase')
        if len(cases) != 1 or any(c.find(tag) is not None for c in cases
                for tag in ('error', 'failure', 'skipped')):
            raise ValueError('one fully passing QA case required')
        proofs = {p.resolve() for p in base.rglob('verification.json')}
        if len(proofs) != 1: raise ValueError('unique actual software proof required')
        proof_path = proofs.pop(); proof = json.loads(proof_path.read_text())
        if (proof['source_commit'] != source or proof['scientist_profile'] != 'read900'
                or proof['native_software_worlds'] != 7 or proof['actual_transport_application_records'] != 7
                or proof['new_model_calls'] != 0): raise ValueError('actual new-profile software scope differs')
        source_check()
        save(out / 'ended.json', {'status': 'closed-SCRIPTED-verification-only', 'ended_utc': utc(),
            'source_commit': source, 'junit_sha256': file_sha256(junit),
            'verification_file': str(proof_path), 'verification_file_sha256': file_sha256(proof_path),
            'new_scientific_model_calls': 0, 'new_scientific_worlds': 0,
            'real_model_capacity_or_gain_proved': False, 'scientific_dispatched': False, 'publication_ready': False})
        print(json.dumps({'status': 'closed-SCRIPTED-verification-only', 'scientific_dispatched': False}), flush=True)
    except BaseException as error:
        save(out / 'ended.json', {'status': 'stopped', 'stage': stage, 'ended_utc': utc(),
            'error_type': type(error).__name__, 'error': str(error), 'qa_retry': False,
            'scientific_dispatched': False, 'other_jobs_changed': False})
        raise


if __name__ == '__main__': main()
