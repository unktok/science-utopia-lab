"""After normal workflow audits/costs, repeat all-slot reports; no new science."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


def run(args):
    return finish(args, plan_schema='scienceutopia.native-workflow-objective-loop.v1.plan',
        preceding_schema='scienceutopia.native-workflow-objective-loop-finish.v1',
        continuation_schema='scienceutopia.native-workflow-objective-report-finish.v1',
        report_module='scripts.reports.native_workflow_objective_loop_v1')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'analysis', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
