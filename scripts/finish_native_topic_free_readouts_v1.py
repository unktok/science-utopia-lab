"""After original paired cold/cost closure, export all three histories twice."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


def run(args):
    return finish(args,plan_schema='scienceutopia.native-topic-free-optimization.v1.plan',
        preceding_schema='scienceutopia.native-topic-free-optimization.v1.finish',
        continuation_schema='scienceutopia.native-topic-free-readout.v1.finish',
        report_module='scripts.reports.native_topic_free_readout_v1',
        report_extra_arguments=('--frozen-source',str(args.frozen_source.resolve())))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','analysis','frozen-source','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    run(parser.parse_args())


if __name__=='__main__': main()
