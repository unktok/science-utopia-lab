"""Repeated closed presentation score, choice, effect or full-input export."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


def run(args):
    modules = {'scores':'scripts.reports.native_parent_presentation_loop_v1',
        'choices':'scripts.reports.native_planning_choice_trace_v1',
        'effects':'scripts.reports.native_institution_effect_trace_v1',
        'requests':'scripts.reports.native_observed_request_classes_v1'}
    if args.kind not in modules:
        raise ValueError('explicit presentation readout kind required')
    extra = ()
    if args.kind in ('choices','effects'):
        extra += ('--frozen-source',str(args.frozen_source.resolve()))
    if args.kind == 'choices': extra += ('--study','parent-presentation')
    if args.kind == 'effects': extra += ('--scope','parent-presentation-development')
    return finish(args, plan_schema='scienceutopia.native-parent-presentation-loop.v1.plan',
        preceding_schema='scienceutopia.native-parent-presentation-loop-finish.v1',
        continuation_schema='scienceutopia.native-parent-presentation-'+args.kind+'-finish.v1',
        report_module=modules[args.kind], report_extra_arguments=extra)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run','analysis','frozen-source','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--kind',choices=('scores','choices','effects','requests'),required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
