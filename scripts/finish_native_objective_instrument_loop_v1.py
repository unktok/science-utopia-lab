"""Normal objective-loop closure -> two cold audits -> two complete cost views."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args,plan_schema='scienceutopia.native-objective-instrument-loop.v1.plan',
        audit_module='scripts.audit_native_objective_instrument_loop_v1',
        continuation_schema='scienceutopia.native-objective-instrument-loop-finish.v1',
        writer_command='scripts.run_native_objective_instrument_loop_v1 run',
        waiting_stage='await-objective-instrument-normal-closure',
        next_steps='Retain every T/U proposal, common-reference parents, actual critic ratings and costs; '
            'interpret mechanisms and select literal submitted policies before a separately frozen unused-seed evaluation. '
            'Normal closure is not scientific superiority or publication readiness.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--writer-pid',type=int,required=True);run(p.parse_args())


if __name__=='__main__':main()
