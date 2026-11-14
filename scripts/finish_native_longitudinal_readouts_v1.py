"""Only after paired audit/cost closure: repeat a matched scientific readout."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


def run(args):
    modules={'scores':'scripts.reports.native_longitudinal_comparison_v1',
        'choices':'scripts.reports.native_planning_choice_trace_v1',
        'effects':'scripts.reports.native_institution_effect_trace_v1',
        'requests':'scripts.reports.native_observed_request_classes_v1',
        'construction':'scripts.reports.native_workflow_construction_trace_v1'}
    if args.kind not in modules:raise ValueError('explicit matched longitudinal readout required')
    extra=()
    if args.kind in ('choices','effects'):
        extra=('--frozen-source',str(args.frozen_source.resolve()))
        extra+=(('--study','longitudinal-development') if args.kind=='choices' else
                ('--scope','longitudinal-objective-development'))
    return finish(args,plan_schema='scienceutopia.native-longitudinal-comparison.v1.plan',
        preceding_schema='scienceutopia.native-longitudinal-comparison-finish.v1',
        continuation_schema='scienceutopia.native-longitudinal-'+args.kind+'-finish.v1',
        report_module=modules[args.kind],report_extra_arguments=extra)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','analysis','frozen-source','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--kind',choices=('scores','choices','effects','requests','construction'),required=True)
    run(p.parse_args())
