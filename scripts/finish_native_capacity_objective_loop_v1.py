"""Normal capacity pilot closure -> double original cold audit and cost read."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args,plan_schema='scienceutopia.native-capacity-objective-loop.v1.plan',
        audit_module='scripts.audit_native_capacity_objective_loop_v1',
        continuation_schema='scienceutopia.native-capacity-objective-loop-finish.v1',
        writer_command='scripts.run_native_capacity_objective_loop_v1 run',
        waiting_stage='await-capacity-objective-normal-closure',
        next_steps='Retain every objective/candidate/reference, literal edit, loss path, null and cost; '
            'examine original trajectories before fixing any independent replication. Publication readiness remains open.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--writer-pid',type=int,required=True);run(p.parse_args())


if __name__=='__main__':main()
