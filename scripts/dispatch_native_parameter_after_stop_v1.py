"""First dispatch of an unused numeric plan, never resumption of stopped science."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.analyze_native_open_v7 import _inventory
from scripts.finish_native_institution_loop_v1 import same_files
from scripts.run_pre_scale_completion_chain_v1 import process_identity, save, ENVIRONMENT
from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-parameter-post-stop-dispatch.v1'
PROTOCOL = 'research/protocols/campaigns/native-parameter-post-stop-dispatch-v1.md'
QUIET_SECONDS = 30


def utc(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return decode_json(Path(path).read_text(), strict=True, finite_floats=True)
def scientific(path): return checked(read(path))


def revision(root):
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root):
        raise ValueError('clean commit-pinned dispatch/scientific source required')
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()


def stopped_evidence(args, *, observe=process_identity):
    old, old_chain = args.stopped_run, args.stopped_chain
    plan, start, end = [scientific(old / n) for n in ('plan.json', 'started.json', 'terminal.json')]
    chain_start, chain_end = [read(old_chain / n) for n in ('started.json', 'ended.json')]
    if (plan['schema'] != 'scienceutopia.native-parent-presentation-loop.v1.plan'
            or plan['source_commit'] != revision(args.stopped_source)
            or start['plan_sha256'] != plan['content_sha256'] or end['status'] != 'stopped'
            or end['stage'] != 'readiness' or end['error_type'] != 'CompletionUnknown'
            or chain_start['schema'] != 'scienceutopia.native-parameter-comparator-chain.v1'
            or chain_start['wait_writer_pid'] != start['pid'] or chain_end['status'] != 'stopped'
            or chain_end['stage'] != 'wait-upstream-science' or chain_end['steps']):
        raise ValueError('exact stopped unknown-readiness study and unexecuted old chain required')
    retired = sorted({start['pid'], chain_start['pid'], chain_start['wait_analysis_pid']})
    if any(observe(pid) is not None for pid in retired):
        raise ValueError('a retired scientific/analysis/scheduler PID is live or reused; no dispatch')
    result_path = old / 'search/throughput-literal/readiness-1/editor-readiness/result.json'
    result = scientific(result_path)
    if (result.get('worker_result_exists') is not False or result['execution']['timed_out'] is not True
            or result['execution']['server_cancel_confirmed'] is not False):
        raise ValueError('original unknown owned-worker result required; never resolve it by assumption')
    files = [old / n for n in ('plan.json', 'started.json', 'terminal.json')]
    files += [result_path, old_chain / 'started.json', old_chain / 'ended.json']
    return {'stopped_source_commit': plan['source_commit'], 'retired_pids': retired,
        'files': {str(p): sha(p) for p in files}, 'stopped_raw_inventory_sha256': digest(_inventory(old)),
        'stopped_status': 'stopped', 'historical_completion_unknown': True,
        'historical_server_cancellation_confirmed': False, 'original_study_resumed_or_refilled': False}


def backend_observation(*, session=None):
    import requests
    if session is None: session = requests.Session(); session.trust_env = False
    record = {'schema': SCHEMA + '.quiescence', 'observed_utc': utc(),
        'metadata_GETs': 2, 'inference_POSTs': 0, 'restart_or_unload': False}
    for resource in ('ps', 'version'):
        url = 'http://127.0.0.1:11434/api/' + resource
        response = session.get(url, timeout=10)
        record[resource] = {'url': url, 'http_status': response.status_code, 'raw_http_response': response.text}
        response.raise_for_status()
        record[resource]['payload'] = decode_json(response.text, strict=True, finite_floats=True)
    if (record['ps']['http_status'] != 200 or not isinstance(record['ps']['payload'], dict)
            or record['ps']['payload'].get('models') != []
            or record['version']['http_status'] != 200
            or not isinstance(record['version']['payload'], dict)
            or not isinstance(record['version']['payload'].get('version'), str)):
        raise ValueError('present backend is not observably empty/known; no restart/unload to force readiness')
    return record


def validate_numeric(args, *, command=subprocess.run):
    code = ('import json,sys;from pathlib import Path;'
        'from scripts.run_native_parameter_comparator_v1 import require_plan;'
        'p=require_plan(Path(sys.argv[1]));'
        'print(json.dumps({"source_commit":p["source_commit"],"plan_sha256":p["content_sha256"]}))')
    result = command([sys.executable, '-c', code, str(args.run)], cwd=args.frozen_source,
        env={**os.environ, **ENVIRONMENT}, capture_output=True, text=True, timeout=1800, check=False)
    if result.returncode: raise ValueError('original public numeric require_plan failed: ' + result.stderr[-2000:])
    return decode_json(result.stdout, strict=True, finite_floats=True)


def normalized(args):
    for key in ('run', 'frozen_source', 'stopped_run', 'stopped_source', 'stopped_chain', 'output'):
        setattr(args, key, Path(getattr(args, key)).resolve())
    return args


def binding(args, *, observe=process_identity):
    numeric = scientific(args.run / 'plan.json')
    if (numeric['schema'] != 'scienceutopia.native-parameter-comparator.v1.plan'
            or numeric['source_commit'] != revision(args.frozen_source)
            or (args.run / 'started.json').exists() or (args.run / 'terminal.json').exists()
            or numeric['budget']['native_worlds_upper_bound'] != 6
            or numeric['origin']['run'] == str(args.stopped_run)):
        raise ValueError('original distinct-bank numeric plan must be exact and unconsumed')
    old = stopped_evidence(args, observe=observe)
    old_dispatch = read(args.stopped_chain / 'started.json')
    if (old_dispatch['numeric_source_commit'] != numeric['source_commit']
            or old_dispatch['numeric_plan_file_sha256'] != sha(args.run / 'plan.json')
            or numeric['origin']['source_commit'] == old['stopped_source_commit']):
        raise ValueError('exact originally queued numeric plan with a distinct closed scientific bank required')
    return {'schema': SCHEMA + '.plan', 'source_commit': revision(ROOT), 'protocol': PROTOCOL,
        'protocol_sha256': sha(ROOT / PROTOCOL), 'run': str(args.run), 'frozen_source': str(args.frozen_source),
        'numeric_source_commit': numeric['source_commit'], 'numeric_plan_file_sha256': sha(args.run / 'plan.json'),
        'numeric_plan_content_sha256': numeric['content_sha256'], 'stopped_run': str(args.stopped_run),
        'stopped_source': str(args.stopped_source), 'stopped_chain': str(args.stopped_chain),
        'stopped_evidence': old, 'quiet_seconds': QUIET_SECONDS,
        'expected_backend_version': numeric['observer_contract']['backend']['ollama_version'],
        'new_numeric_worlds_upper_bound': 6, 'new_designer_calls': 0,
        'old_protocol_criteria_relaxed_in_place': False, 'historical_unknown_resolved': False}


def prepare(args):
    args = normalized(args)
    if args.output.exists() or any(args.output.is_relative_to(p) for p in (
            args.run, args.frozen_source, args.stopped_run, args.stopped_source, args.stopped_chain)):
        raise ValueError('fresh independent post-stop scheduler directory required')
    p = binding(args); observation = backend_observation(); public = validate_numeric(args)
    if (public != {'source_commit': p['numeric_source_commit'], 'plan_sha256': p['numeric_plan_content_sha256']}
            or observation['version']['payload']['version'] != p['expected_backend_version']):
        raise ValueError('original numeric public contract/backend differs')
    args.output.mkdir(parents=True)
    save(args.output / 'plan.json', p); save(args.output / 'prepare-quiescence.json', observation)
    save(args.output / 'original-public-plan-check.json', public)
    print(json.dumps({'prepared_source': p['source_commit'], 'new_inference_POSTs': 0,
        'new_numeric_worlds_upper_bound': 6}), flush=True)


def run(output, *, observe=process_identity, backend=backend_observation,
        poll=time.sleep, clock=time.monotonic, command=subprocess.run):
    output = Path(output).resolve(); p = read(output / 'plan.json')
    args = normalized(argparse.Namespace(**{k: p[k] for k in
        ('run', 'frozen_source', 'stopped_run', 'stopped_source', 'stopped_chain')}, output=output))
    if p != binding(args, observe=observe): raise ValueError('frozen independent post-stop binding changed')
    if (output / 'started.json').exists(): raise ValueError('consumed post-stop scheduler; no retry')
    with ExitStack() as stack:
        for path in (output / 'owner.lock', args.stopped_run / 'writer.lock'):
            handle = stack.enter_context(path.open('a' if path.parent == output else 'r'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save(output / 'started.json', {'schema': SCHEMA, 'pid': os.getpid(), 'source_commit': p['source_commit'],
            'numeric_source_commit': p['numeric_source_commit'], 'started_utc': utc(),
            'plan_file_sha256': sha(output / 'plan.json'), 'original_study_restarted': False})
        stage, steps = 'present-quiescence', []
        def unchanged(*, unused=False):
            if (revision(ROOT) != p['source_commit'] or revision(args.frozen_source) != p['numeric_source_commit']
                    or sha(args.run / 'plan.json') != p['numeric_plan_file_sha256']
                    or stopped_evidence(args, observe=observe) != p['stopped_evidence']):
                raise ValueError('source/plan/stopped evidence changed; no next stage')
            if unused and (args.run / 'started.json').exists(): raise ValueError('numeric plan consumed before first dispatch')
        def execute(name, module, argv, *, science=False):
            nonlocal stage
            stage = name; unchanged(unused=science)
            cmd = [sys.executable, '-m', module, *argv]
            save(output / (name + '.started.json'), {'command': cmd, 'cwd': str(args.frozen_source), 'started_utc': utc()})
            with (output / (name + '.log')).open('x') as log:
                result = command(cmd, cwd=args.frozen_source, env={**os.environ, **ENVIRONMENT},
                    stdout=log, stderr=subprocess.STDOUT, check=False, **({} if science else {'timeout': 1800}))
            step = {'stage': name, 'exit_code': result.returncode, 'ended_utc': utc()}; steps.append(step)
            save(output / (name + '.ended.json'), step); print(json.dumps(step), flush=True)
            if result.returncode: raise ValueError('post-stop stage failed; never retry: ' + name)
            unchanged()
        try:
            started = clock(); first_completed = None
            for i in (1, 2):
                if i == 2 and clock() - first_completed < QUIET_SECONDS:
                    raise ValueError('required fresh backend observation separation not met')
                unchanged(unused=True); value = backend()
                if (value['ps']['payload'].get('models') != []
                        or value['version']['payload'].get('version') != p['expected_backend_version']):
                    raise ValueError('backend not empty/unchanged before independent dispatch')
                save(output / ('quiescence-' + str(i) + '.json'), value)
                if i == 1: first_completed = clock(); poll(QUIET_SECONDS)
            if clock() - started < QUIET_SECONDS:
                raise ValueError('required fresh backend observation separation not met')
            save(output / 'quiescence-review.json', {'elapsed_seconds': clock() - started,
                'historical_completion_unknown': True, 'historical_cancellation_confirmed': False,
                'present_empty_backend_and_absent_retired_jobs': True, 'inference_POSTs': 0})
            execute('numeric-run', 'scripts.run_native_parameter_comparator_v1', ['run', '--output', str(args.run)], science=True)
            for i in (1, 2):
                execute('audit-' + str(i), 'scripts.audit_native_parameter_comparator_v1', ['--run', str(args.run),
                    '--frozen-source', str(args.frozen_source), '--output', str(output / ('audit-' + str(i) + '.json'))])
            if (output / 'audit-1.json').read_bytes() != (output / 'audit-2.json').read_bytes():
                raise ValueError('original numeric cold audits differ')
            for i in (1, 2):
                execute('costs-' + str(i), 'scripts.reports.pre_scale_costs_v1', ['--run', str(args.run),
                    '--plan', str(args.run / 'plan.json'), '--audit', str(output / 'audit-1.json'),
                    '--output', str(output / ('costs-' + str(i) + '.json'))])
                execute('report-' + str(i), 'scripts.reports.native_parameter_comparator_v1', ['--run', str(args.run),
                    '--audit-one', str(output / 'audit-1.json'), '--audit-two', str(output / 'audit-2.json'),
                    '--output', str(output / ('report-' + str(i)))])
            if (output / 'costs-1.json').read_bytes() != (output / 'costs-2.json').read_bytes():
                raise ValueError('original numeric cost projections differ')
            files = same_files(output / 'report-1', output / 'report-2')
        except BaseException as error:
            save(output / 'ended.json', {'status': 'stopped', 'stage': stage, 'steps': steps,
                'error_type': type(error).__name__, 'error': str(error), 'ended_utc': utc(),
                'science_restarted': False, 'old_unknown_resolved': False})
            raise
        save(output / 'ended.json', {'status': 'closed', 'steps': steps, 'report_files': files,
            'ended_utc': utc(), 'science_restarted': False, 'old_unknown_resolved': False,
            'publication_ready': False, 'research_goal_complete': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    for key in ('run', 'frozen-source', 'stopped-run', 'stopped-source', 'stopped-chain', 'output'):
        p.add_argument('--' + key, type=Path, required=True)
    p = sub.add_parser('run'); p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare': prepare(args)
    else: run(args.output)


if __name__ == '__main__': main()
