"""One numeric study after normal upstream closure; no overlapping inference/retry."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from scripts.analyze_native_open_v7 import _inventory
from scripts.finish_native_institution_loop_v1 import git_binding, sha, same_files, wait_closed, utc
from scripts.run_pre_scale_completion_chain_v1 import process_identity, save, ENVIRONMENT
from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest

ROOT = Path(__file__).resolve().parents[1]


def read(path): return checked(json.loads(Path(path).read_text()))


def wait_analysis(directory, pid, identity, *, observe=process_identity, poll=time.sleep, clock=time.monotonic):
    begin = clock()
    while True:
        current = observe(pid); path = directory / 'ended.json'
        if path.is_file():
            if json.loads(path.read_text()).get('status') != 'closed':
                raise ValueError('upstream analysis stopped; no next inference')
            if current is None: return {'analysis_writer_absent': True, 'poll_elapsed_seconds': clock() - begin}
        if current is None: raise ValueError('analysis disappeared without normal closure; no next inference')
        if current != identity: raise ValueError('analysis PID identity changed; no next inference')
        if clock() - begin >= 86400: raise ValueError('finite analysis wait exhausted; original study untouched')
        poll(15)


def require_previous(args):
    p = read(args.wait_run / 'plan.json'); start = read(args.wait_run / 'started.json')
    a, b = [read(args.wait_analysis / ('audit-' + str(i) + '.json')) for i in (1, 2)]
    end = json.loads((args.wait_analysis / 'ended.json').read_text())
    if (a != b or a['schema'] != 'scienceutopia.native-parent-presentation-loop-audit.v1'
            or a['source_commit'] != p['source_commit'] or a['plan_sha256'] != p['content_sha256']
            or a['source_proof']['status'] != 'verified-exact-source-closure'
            or a['closure']['started'] != start or a['closure']['terminal'] != read(args.wait_run / 'terminal.json')
            or a['closure']['terminal']['status'] != 'closed'
            or a['new_model_calls'] or a['new_code_executions'] or end['status'] != 'closed'
            or end['audit_file_sha256'] != sha(args.wait_analysis / 'audit-1.json')
            or end['cost_file_sha256'] != sha(args.wait_analysis / 'costs-1.json')
            or (args.wait_analysis / 'costs-1.json').read_bytes() != (args.wait_analysis / 'costs-2.json').read_bytes()
            or a['raw_inventory_sha256'] != digest(_inventory(args.wait_run))):
        raise ValueError('normal matching upstream double audits/costs and unchanged raw required')
    return {'upstream_audit_content_sha256': a['content_sha256'],
        'upstream_analysis_ended_sha256': sha(args.wait_analysis / 'ended.json')}


def run(args, *, observe=process_identity, poll=time.sleep, clock=time.monotonic, command=subprocess.run):
    for key in ('run', 'frozen_source', 'wait_run', 'wait_source', 'wait_analysis', 'output'):
        setattr(args, key, Path(getattr(args, key)).resolve())
    source, numeric, previous = git_binding(ROOT), git_binding(args.frozen_source), git_binding(args.wait_source)
    p, old = read(args.run / 'plan.json'), read(args.wait_run / 'plan.json')
    old_start = read(args.wait_run / 'started.json')
    analysis_start = json.loads((args.wait_analysis / 'started.json').read_text())
    if (args.output.exists() or any(args.output.is_relative_to(path) for path in (args.run, args.frozen_source, args.wait_run, args.wait_source))
            or p['schema'] != 'scienceutopia.native-parameter-comparator.v1.plan' or p['source_commit'] != numeric
            or old['schema'] != 'scienceutopia.native-parent-presentation-loop.v1.plan' or old['source_commit'] != previous
            or old_start['pid'] != args.wait_writer_pid or old_start['plan_sha256'] != old['content_sha256']
            or analysis_start['scientific_source_commit'] != previous or analysis_start['writer_pid'] != args.wait_writer_pid
            or (args.run / 'started.json').exists()):
        raise ValueError('fresh independent chain and exact unconsumed numeric/upstream study/source bindings required')
    identities = {pid: observe(pid) for pid in (args.wait_writer_pid, args.wait_analysis_pid)}
    for pid, module in ((args.wait_writer_pid, 'scripts.run_native_parent_presentation_loop_v1 run'),
            (args.wait_analysis_pid, 'scripts.finish_native_parent_presentation_loop_v1')):
        if identities[pid] is not None and module not in identities[pid]:
            raise ValueError('upstream PID belongs to a different task')
    args.output.mkdir(parents=True)
    binding = {'analysis_source_commit': source, 'numeric_source_commit': numeric, 'previous_source_commit': previous,
        'numeric_plan_file_sha256': sha(args.run / 'plan.json'), 'previous_plan_file_sha256': sha(args.wait_run / 'plan.json')}
    save(args.output / 'started.json', {'schema': 'scienceutopia.native-parameter-comparator-chain.v1',
        **binding, 'pid': os.getpid(), 'started_utc': utc(), 'wait_writer_pid': args.wait_writer_pid,
        'wait_analysis_pid': args.wait_analysis_pid, 'upstream_process_identities': identities,
        'maximum_wait_seconds_per_process': 86400, 'maximum_new_native_worlds': 6,
        'new_inference_allowed_only_after_upstream_normal_double_audit': True, 'automatic_retries': False})
    steps, stage = [], 'wait-upstream-science'
    def require_sources():
        if (git_binding(ROOT) != source or git_binding(args.frozen_source) != numeric or git_binding(args.wait_source) != previous
                or sha(args.run / 'plan.json') != binding['numeric_plan_file_sha256']
                or sha(args.wait_run / 'plan.json') != binding['previous_plan_file_sha256']):
            raise ValueError('chain source/plan changed before dispatch; no next action')
    def execute(name, module, argv, *, scientific=False):
        nonlocal stage
        stage = name; require_sources()
        cmd = [sys.executable, '-m', module, *argv]
        save(args.output / (name + '.started.json'), {'command': cmd, 'cwd': str(args.frozen_source), 'started_utc': utc()})
        with (args.output / (name + '.log')).open('x') as log:
            # The scientific runner owns its already-declared finite component
            # budgets; a polling timeout must not kill/relaunch a live world.
            extra = {} if scientific else {'timeout': 1800}
            result = command(cmd, cwd=args.frozen_source, env={**os.environ, **ENVIRONMENT},
                stdout=log, stderr=subprocess.STDOUT, check=False, **extra)
        step = {'stage': name, 'exit_code': result.returncode, 'ended_utc': utc()}; steps.append(step)
        save(args.output / (name + '.ended.json'), step); print(json.dumps(step), flush=True)
        if result.returncode: raise ValueError('finite stage failed; never retry: ' + name)
        require_sources()
    try:
        print(json.dumps({'stage': stage, 'new_numeric_study_dispatched': False}), flush=True)
        save(args.output / 'previous-writer-absent.json', wait_closed(args.wait_run, args.wait_writer_pid,
            identities[args.wait_writer_pid], observe=observe, poll=poll, clock=clock))
        stage = 'wait-upstream-analysis'
        save(args.output / 'previous-analysis-absent.json', wait_analysis(args.wait_analysis, args.wait_analysis_pid,
            identities[args.wait_analysis_pid], observe=observe, poll=poll, clock=clock))
        require_sources(); save(args.output / 'previous-verified.json', require_previous(args))
        if (args.run / 'started.json').exists(): raise ValueError('numeric study consumed while waiting; no redispatch')
        execute('numeric-run', 'scripts.run_native_parameter_comparator_v1', ['run', '--output', str(args.run)], scientific=True)
        for i in (1, 2):
            execute('audit-' + str(i), 'scripts.audit_native_parameter_comparator_v1', ['--run', str(args.run),
                '--frozen-source', str(args.frozen_source), '--output', str(args.output / ('audit-' + str(i) + '.json'))])
        if (args.output / 'audit-1.json').read_bytes() != (args.output / 'audit-2.json').read_bytes():
            raise ValueError('original numeric cold audits differ')
        for i in (1, 2):
            execute('costs-' + str(i), 'scripts.reports.pre_scale_costs_v1', ['--run', str(args.run),
                '--plan', str(args.run / 'plan.json'), '--audit', str(args.output / 'audit-1.json'),
                '--output', str(args.output / ('costs-' + str(i) + '.json'))])
            execute('report-' + str(i), 'scripts.reports.native_parameter_comparator_v1', ['--run', str(args.run),
                '--audit-one', str(args.output / 'audit-1.json'), '--audit-two', str(args.output / 'audit-2.json'),
                '--output', str(args.output / ('report-' + str(i)))])
        if (args.output / 'costs-1.json').read_bytes() != (args.output / 'costs-2.json').read_bytes():
            raise ValueError('numeric cost exports differ')
        files = same_files(args.output / 'report-1', args.output / 'report-2')
    except BaseException as error:
        save(args.output / 'ended.json', {'status': 'stopped', 'stage': stage, 'steps': steps,
            'error_type': type(error).__name__, 'error': str(error), 'ended_utc': utc(), 'science_restarted': False})
        raise
    save(args.output / 'ended.json', {'status': 'closed', 'steps': steps, 'report_files': files,
        'ended_utc': utc(), 'publication_ready': False, 'research_goal_complete': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'frozen-source', 'wait-run', 'wait-source', 'wait-analysis', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    for key in ('wait-writer-pid', 'wait-analysis-pid'): parser.add_argument('--' + key, type=int, required=True)
    run(parser.parse_args())


if __name__ == '__main__': main()
