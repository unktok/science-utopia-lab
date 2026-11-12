"""Exact full scientist inputs/response classes, only after original closure."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


def run(args):
    return finish(args,plan_schema='scienceutopia.native-capacity-objective-loop.v1.plan',
        preceding_schema='scienceutopia.native-capacity-objective-loop-finish.v1',
        continuation_schema='scienceutopia.native-capacity-request-report-finish.v1',
        report_module='scripts.reports.native_observed_request_classes_v1')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','analysis','output'):p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())


if __name__=='__main__':main()
