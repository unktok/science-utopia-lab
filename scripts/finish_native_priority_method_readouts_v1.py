"""Wait for exact mixed-method cold/cost closure, then project all slots twice.

No inference, candidate execution, refill, reselection or graphics rendering.
"""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    output = args.output.resolve()
    roots = tuple(p.resolve() for p in (ROOT, args.frozen_source, args.run, args.analysis))
    # Check actual child destinations before the inherited helper can wait or
    # create anything. Resolving catches existing external symlinks into source.
    if output.exists() or any(child.is_relative_to(root)
            for child in (output, (output / 'report-1').resolve(), (output / 'report-2').resolve())
            for root in roots):
        raise ValueError('fresh reports outside reader/scientific sources, raw and analysis required before waiting')
    extra = ('--frozen-source', str(args.frozen_source.resolve()),
        '--cost-one', str(args.analysis.resolve() / 'costs-1.json'),
        '--cost-two', str(args.analysis.resolve() / 'costs-2.json'))
    return finish(args, plan_schema='scienceutopia.native-priority-method-comparison.v1.plan',
        preceding_schema='scienceutopia.native-priority-method-comparison.v1.finish',
        continuation_schema='scienceutopia.native-priority-method-comparison.v1.readout.finish',
        report_module='scripts.reports.native_priority_method_readout_v1', report_extra_arguments=extra)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'analysis', 'frozen-source', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
