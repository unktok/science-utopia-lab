"""After original paired cold/cost closure: two source-bound native effect reads.

No inference, source execution, new world, loss edits, restart or rendering.
"""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish
from scripts.run_native_corrected_choice_search_v1 import SCHEMA as STUDY

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-corrected-choice-effects-finish.v1'


def run(args):
    output = args.output.resolve()
    roots = (ROOT.resolve(), args.run.resolve(), args.analysis.resolve(), args.frozen_source.resolve())
    if output.exists() or any(child.is_relative_to(root) for root in roots
            for child in (output, (output / 'report-1').resolve(), (output / 'report-2').resolve())):
        raise ValueError('fresh external effect children required before waiting')
    return finish(args, plan_schema=STUDY + '.plan', preceding_schema=STUDY + '.finish',
        continuation_schema=SCHEMA, report_module='scripts.reports.native_institution_effect_trace_v1',
        report_extra_arguments=('--frozen-source', str(args.frozen_source.resolve()),
            '--scope', 'corrected-choice-development'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'analysis', 'frozen-source', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    run(parser.parse_args())
