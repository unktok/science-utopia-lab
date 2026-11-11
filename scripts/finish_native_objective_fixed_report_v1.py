"""Double all-seed export after the fixed evaluation's normal audit/cost chain."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


def run(args):
    return finish(args,plan_schema='scienceutopia.native-objective-fixed-evaluation.v1.plan',
        preceding_schema='scienceutopia.native-objective-fixed-evaluation-finish.v1',
        continuation_schema='scienceutopia.native-objective-fixed-report-finish.v1',
        report_module='scripts.reports.native_objective_fixed_evaluation_v1')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','analysis','output'):p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())


if __name__=='__main__':main()
