"""Wait for closed T/U development audits, export all slots twice, compare bytes."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


def run(args):
    return finish(args,plan_schema='scienceutopia.native-objective-instrument-loop.v1.plan',
        preceding_schema='scienceutopia.native-objective-instrument-loop-finish.v1',
        continuation_schema='scienceutopia.native-objective-instrument-report-finish.v1',
        report_module='scripts.reports.native_objective_instrument_loop_v1')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','analysis','output'):p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())


if __name__=='__main__':main()
