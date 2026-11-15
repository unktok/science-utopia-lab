"""Wait for original audit/cost closure, then export literal contrasts twice."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


def run(args):
    return finish(args, plan_schema='scienceutopia.native-terminal-cost-pilot.v1.plan',
        preceding_schema='scienceutopia.native-terminal-cost-pilot-finish.v1',
        continuation_schema='scienceutopia.native-terminal-cost-readout.v1.finish',
        report_module='scripts.reports.native_terminal_cost_pilot_v1',
        report_extra_arguments=('--frozen-source', str(args.frozen_source.resolve()),
            '--cost-one', str((args.analysis / 'costs-1.json').resolve()),
            '--cost-two', str((args.analysis / 'costs-2.json').resolve())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'analysis', 'frozen-source', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
