"""Normal original T/P closure -> two strict observed-archive geometry exports."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


def run(args):
    return finish(args,plan_schema='scienceutopia.native-capacity-objective-loop.v1.plan',
        preceding_schema='scienceutopia.native-capacity-objective-loop-finish.v1',
        continuation_schema='scienceutopia.native-capacity-preference-geometry-finish.v1',
        report_module='scripts.reports.native_capacity_preference_geometry_v1')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','analysis','output'):parser.add_argument('--'+key,type=Path,required=True)
    run(parser.parse_args())


if __name__=='__main__':main()
