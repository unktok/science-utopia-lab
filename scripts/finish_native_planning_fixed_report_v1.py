"""Double fixed-planning export after normal original audit/cost closure."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


def run(args):
    return finish(args,plan_schema='scienceutopia.native-planning-fixed-evaluation.v1.plan',
        preceding_schema='scienceutopia.native-planning-fixed-evaluation-finish.v1',
        continuation_schema='scienceutopia.native-planning-fixed-report-finish.v1',
        report_module='scripts.reports.native_planning_fixed_evaluation_v1')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','analysis','output'):parser.add_argument('--'+key,type=Path,required=True)
    run(parser.parse_args())


if __name__=='__main__':main()
