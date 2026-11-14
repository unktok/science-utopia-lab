"""Await the original workflow writer, then audit/cost twice; never infer."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args, plan_schema='scienceutopia.native-workflow-objective-loop.v1.plan',
        audit_module='scripts.audit_native_workflow_objective_loop_v1',
        continuation_schema='scienceutopia.native-workflow-objective-loop-finish.v1',
        writer_command='scripts.run_native_workflow_objective_loop_v1 run',
        waiting_stage='await-native-workflow-normal-closure',
        next_steps='Compare both fresh controls and all six structural slots, preserve nulls and '
            'actual costs, align phases/effects with resource ledgers and original model inputs. '
            'A normally closed pilot is not independent replication or publication readiness.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'frozen-source', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--writer-pid', type=int, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
