"""Await the original12-slot writer; paired original-source audits/costs only."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args, plan_schema='scienceutopia.native-longitudinal-comparison.v1.plan',
        audit_module='scripts.audit_native_longitudinal_comparison_v1',
        continuation_schema='scienceutopia.native-longitudinal-comparison-finish.v1',
        writer_command='scripts.run_native_longitudinal_comparison_v1 run',
        waiting_stage='await-original-longitudinal-normal-closure',
        next_steps='Retain all twelve slots and four own-only selections, both fresh references, '
            'nulls, costs and actual mechanisms. No scientific retry, refill or model call. '
            'Complete paired readouts, then fresh reserved-seed inventory and frozen evaluation. '
            'A closed coupled comparison is not independent replication or publication readiness.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--writer-pid',type=int,required=True);run(p.parse_args())
