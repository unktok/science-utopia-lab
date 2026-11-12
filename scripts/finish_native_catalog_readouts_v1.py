"""Wait for original catalog closure, then repeat one explicit cold export."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_report_v1 import run as finish


def run(args):
    modules = {'choices': 'scripts.reports.native_catalog_actuation_v1',
        'effects': 'scripts.reports.native_institution_effect_trace_v1',
        'requests': 'scripts.reports.native_observed_request_classes_v1'}
    if args.kind not in modules: raise ValueError('explicit catalog readout kind required')
    extra = () if args.kind == 'requests' else ('--frozen-source', str(args.frozen_source.resolve()))
    if args.kind == 'effects': extra += ('--scope', 'catalog-actuation-controls')
    return finish(args, plan_schema='scienceutopia.native-catalog-actuation.v1.plan',
        preceding_schema='scienceutopia.native-catalog-actuation-finish.v1',
        continuation_schema='scienceutopia.native-catalog-' + args.kind + '-finish.v1',
        report_module=modules[args.kind], report_extra_arguments=extra)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'analysis', 'frozen-source', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--kind', choices=('choices', 'effects', 'requests'), required=True)
    run(parser.parse_args())


if __name__ == '__main__': main()
