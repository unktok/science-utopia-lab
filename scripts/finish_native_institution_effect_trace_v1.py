"""After original normal audits, export source/consumer/resource traces twice."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


SCOPES={
    'objective-development':('scienceutopia.native-objective-instrument-loop.v1.plan',
        'scienceutopia.native-objective-instrument-loop-finish.v1'),
    'fixed-evaluation':('scienceutopia.native-objective-fixed-evaluation.v1.plan',
        'scienceutopia.native-objective-fixed-evaluation-finish.v1')}


def run(args):
    plan,preceding=SCOPES[args.scope]
    return finish(args,plan_schema=plan,preceding_schema=preceding,
        continuation_schema='scienceutopia.native-institution-effect-trace-finish.v1',
        report_module='scripts.reports.native_institution_effect_trace_v1',
        report_extra_arguments=('--frozen-source',str(args.frozen_source.resolve()),'--scope',args.scope))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','analysis','frozen-source','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--scope',choices=tuple(SCOPES),required=True);run(p.parse_args())


if __name__=='__main__':main()
