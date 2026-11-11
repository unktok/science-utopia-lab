"""Normal fixed-policy evaluation closure, then two cold audits and cost views."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args,plan_schema='scienceutopia.native-objective-fixed-evaluation.v1.plan',
        audit_module='scripts.audit_native_objective_fixed_evaluation_v1',
        continuation_schema='scienceutopia.native-objective-fixed-evaluation-finish.v1',
        writer_command='scripts.run_native_objective_fixed_evaluation_v1 run',
        waiting_stage='await-objective-fixed-evaluation-normal-closure',
        next_steps='Export every fixed policy/control and seed, both losses and missing results; '
            'interpret without reselection, inspect actual figures and update the manuscript. Publication readiness remains a separate judgment.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--writer-pid',type=int,required=True);run(p.parse_args())


if __name__=='__main__':main()
