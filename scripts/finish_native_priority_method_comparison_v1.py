"""Wait for this exact writer AND its exit journal before paired cold/cost reads.

The supervisor writes writer-exit.json after the scientist process exits.
Waiting on only the scientist PID can race that final raw inventory append.
No scientific execution, retry, source repair or model dispatch occurs here.
"""
import argparse
from datetime import datetime
from pathlib import Path
import time

from scripts.finish_native_code_tested_loop_v1 import run as finish, ROOT
from scripts.finish_native_institution_loop_v1 import wait_closed, sha
from scripts.run_pre_scale_completion_chain_v1 import process_identity
from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import decode_json


def read(path):
    return checked(decode_json(Path(path).read_text(), strict=True, finite_floats=True))


def wait_supervised(root, pid, identity, *, wait=wait_closed, observe=process_identity,
                    poll=time.sleep, clock=time.monotonic, supervisor_grace_seconds=60,
                    schema_prefix='scienceutopia.native-priority-method-writer'):
    plan, start = read(root / 'plan.json'), read(root / 'writer-supervision-start.json')
    if (start['schema'] != schema_prefix+'-supervision.v1'
            or start['source_commit'] != plan['source_commit']
            or start['plan_content_sha256'] != plan['content_sha256']
            or type(start['supervisor_pid']) is not int or start['supervisor_pid'] <= 0):
        raise ValueError('exact original supervised writer binding required')
    supervisor = start['supervisor_pid']; original = observe(supervisor)
    value = wait(root, pid, identity); began = clock()
    while True:
        current = observe(supervisor); path = root / 'writer-exit.json'
        if current != original and current is not None:
            raise ValueError('supervisor PID identity changed; no analysis')
        if current is None and path.is_file():
            result = read(path); end = read(root / 'terminal.json')
            if (result['schema'] != schema_prefix+'-exit.v1'
                    or result['source_commit'] != plan['source_commit']
                    or result['plan_content_sha256'] != plan['content_sha256']
                    or type(result['exit_code']) is not int or result['exit_code'] != 0
                    or datetime.fromisoformat(result['ended_utc']) < datetime.fromisoformat(end['ended_utc'])):
                raise ValueError('original wrapper exit is not exact successful closure')
            return {**value, 'original_process_exit_status': 0,
                    'supervisor_original_absent': True, 'writer_exit_file_sha256': sha(path)}
        if clock() - began >= supervisor_grace_seconds:
            raise ValueError('supervisor exit inventory not sealed within finite grace; science untouched')
        poll(1)


def run(args):
    output = args.output.resolve()
    if any(output.is_relative_to(p.resolve()) for p in (ROOT, args.run, args.frozen_source)):
        raise ValueError('closure output must be outside reader/scientific source and raw run')
    return finish(args, plan_schema='scienceutopia.native-priority-method-comparison.v1.plan',
        audit_module='scripts.audit_native_priority_method_comparison_v1',
        continuation_schema='scienceutopia.native-priority-method-comparison.v1.finish',
        writer_command='scripts.run_native_priority_method_comparison_v1 run',
        waiting_stage='await-original-priority-method-and-supervisor-closure',
        writer_wait=wait_supervised,
        next_steps='Retain all24 slots/three references and objective/method/history identities, '
        'including repeated suggestion ids across different histories; analyze effects and costs '
        'without reselection, imputed losses or an automatic superiority/readiness claim.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'frozen-source', 'output'):
        p.add_argument('--' + key, type=Path, required=True)
    p.add_argument('--writer-pid', type=int, required=True); run(p.parse_args())


if __name__ == '__main__':
    main()
