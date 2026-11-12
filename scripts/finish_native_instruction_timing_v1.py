"""Normally closed advice controls -> two original audits and cost views."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args,plan_schema='scienceutopia.native-instruction-timing-support.v1.plan',
        audit_module='scripts.audit_native_instruction_timing_support_v1',
        continuation_schema='scienceutopia.native-instruction-timing-finish.v1',
        writer_command='scripts.run_native_instruction_timing_support_v1 run',
        waiting_stage='await-instruction-timing-normal-closure',
        next_steps='Read actual advice receipt, model inputs, topic/catalog-duration choices and outcomes; '
            'export all controls and costs without claiming optimization or publication readiness.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--writer-pid',type=int,required=True);run(p.parse_args())


if __name__=='__main__':main()
