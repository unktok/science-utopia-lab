"""Paired both-scope corrected fixed readouts only after exact cold/cost closure."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish
from scripts.finish_native_corrected_choice_fixed_evaluation_v1 import check_output
from scripts.run_native_corrected_choice_fixed_evaluation_v1 import SCHEMA

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    check_output(args, ROOT)
    extra = ('--frozen-source', str(args.frozen_source.resolve()),
        '--cost-one', str(args.analysis.resolve() / 'costs-1.json'),
        '--cost-two', str(args.analysis.resolve() / 'costs-2.json'))
    return finish(args, plan_schema=SCHEMA + '.plan', preceding_schema=SCHEMA + '.finish',
        continuation_schema=SCHEMA + '.readout.finish',
        report_module='scripts.reports.native_corrected_choice_fixed_evaluation_v1', report_extra_arguments=extra)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'analysis', 'frozen-source', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    run(parser.parse_args())
