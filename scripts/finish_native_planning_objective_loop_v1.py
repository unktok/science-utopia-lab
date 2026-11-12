"""Normal planning study closure to two original audits and cost projections."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args, plan_schema='scienceutopia.native-planning-objective-loop.v1.plan',
        audit_module='scripts.audit_native_planning_objective_loop_v1',
        continuation_schema='scienceutopia.native-planning-objective-loop-finish.v1',
        writer_command='scripts.run_native_planning_objective_loop_v1 run',
        waiting_stage='await-native-planning-normal-closure',
        next_steps='Retain all T/U proposals, cross-scores, ties, failures, planning/allocation/selection effects '
            'and costs. Compare every strong reference before defining independent histories/unused evaluation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'frozen-source', 'output'): parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--writer-pid', type=int, required=True); run(parser.parse_args())


if __name__ == '__main__': main()
