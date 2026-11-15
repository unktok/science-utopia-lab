"""After original matched paired audit/cost closure, export all eight slots twice."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


def run(args):
    extra = ('--frozen-source', str(args.frozen_source.resolve()),
        '--cost-one', str(args.analysis.resolve() / 'costs-1.json'),
        '--cost-two', str(args.analysis.resolve() / 'costs-2.json'))
    return finish(args, plan_schema='scienceutopia.native-consumer-source-comparison.v1.plan',
        preceding_schema='scienceutopia.native-consumer-source-comparison.v1.finish',
        continuation_schema='scienceutopia.native-consumer-source-comparison.v1.readout.finish',
        report_module='scripts.reports.native_consumer_source_comparison_v1', report_extra_arguments=extra)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'analysis', 'frozen-source', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
