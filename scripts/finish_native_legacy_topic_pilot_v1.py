"""Finite wait for the original pilot, then paired original audits/costs."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args, plan_schema='scienceutopia.native-legacy-topic-pilot.v1.plan',
        audit_module='scripts.audit_native_legacy_topic_pilot_v1',
        continuation_schema='scienceutopia.native-legacy-topic-pilot-finish.v1',
        writer_command='scripts.run_native_legacy_topic_pilot_v1 run',
        waiting_stage='await-legacy-topic-pilot-normal-closure',
        next_steps='Retain both same-authority controls, actual original-topic assignments/calendars, '
            'T/U and report-only resource costs. No automatic invention, objective change or readiness claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'frozen-source', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--writer-pid', type=int, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
