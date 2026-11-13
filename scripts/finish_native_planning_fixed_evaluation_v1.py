"""Normal fixed planning closure, then two original audits and cost views."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args, plan_schema='scienceutopia.native-planning-fixed-evaluation.v1.plan',
        audit_module='scripts.audit_native_planning_fixed_evaluation_v1',
        continuation_schema='scienceutopia.native-planning-fixed-evaluation-finish.v1',
        writer_command='scripts.run_native_planning_fixed_evaluation_v1 run',
        waiting_stage='await-planning-fixed-evaluation-normal-closure',
        next_steps='Retain every exact selected policy/reference/seed, both losses, nulls and costs; '
            'interpret mechanisms without reselection. Fixed-seed evaluation is not independent optimizer replication or publication readiness.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'frozen-source', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--writer-pid', type=int, required=True); run(parser.parse_args())


if __name__ == '__main__': main()
