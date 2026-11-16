"""Wait for exact corrected closure, then pair all-slot readouts; no inference."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish
from scripts.run_native_corrected_choice_search_v1 import SCHEMA

ROOT=Path(__file__).resolve().parents[1]


def run(args):
    output=args.output.resolve();roots=tuple(p.resolve() for p in (ROOT,args.run,args.analysis,args.frozen_source))
    if output.exists() or any(child.is_relative_to(root) for child in
            (output,(output/'report-1').resolve(),(output/'report-2').resolve()) for root in roots):
        raise ValueError('fresh report children outside reader/scientific source/raw/analysis required before waiting')
    extra=('--frozen-source',str(args.frozen_source.resolve()),'--cost-one',str(args.analysis.resolve()/'costs-1.json'),
        '--cost-two',str(args.analysis.resolve()/'costs-2.json'))
    return finish(args,plan_schema=SCHEMA+'.plan',preceding_schema=SCHEMA+'.finish',
        continuation_schema=SCHEMA+'.readout.finish',report_module='scripts.reports.native_priority_method_readout_v1',
        report_extra_arguments=extra)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','analysis','frozen-source','output'):parser.add_argument('--'+key,type=Path,required=True)
    run(parser.parse_args())


if __name__=='__main__':main()
