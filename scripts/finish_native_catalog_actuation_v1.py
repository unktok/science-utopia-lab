"""Normal catalog-control closure to two original audits and cost projections."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args, plan_schema='scienceutopia.native-catalog-actuation.v1.plan',
        audit_module='scripts.audit_native_catalog_actuation_v1',
        continuation_schema='scienceutopia.native-catalog-actuation-finish.v1',
        writer_command='scripts.run_native_catalog_actuation_v1 run',
        waiting_stage='await-catalog-actuation-normal-closure',
        next_steps='Compare every native agenda/project/production/input and both unchanged T/P losses. '
            'Retain all costs and nulls. Developer controls are not automatic institution invention.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'frozen-source', 'output'): parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--writer-pid', type=int, required=True); run(parser.parse_args())


if __name__ == '__main__': main()
