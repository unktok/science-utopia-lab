"""Wait for normal double planning audit/cost closure, then export twice."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


def run(args):
    return finish(args, plan_schema='scienceutopia.native-planning-objective-loop.v1.plan',
        preceding_schema='scienceutopia.native-planning-objective-loop-finish.v1',
        continuation_schema='scienceutopia.native-planning-objective-report-finish.v1',
        report_module='scripts.reports.native_planning_objective_loop_v1')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'analysis', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__': main()
