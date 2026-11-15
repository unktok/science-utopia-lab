"""Wait for this finite pilot, then double original-source audits and costs."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args, plan_schema='scienceutopia.native-legacy-choice-pilot.v1.plan',
        audit_module='scripts.audit_native_legacy_choice_pilot_v1',
        continuation_schema='scienceutopia.native-legacy-choice-pilot-finish.v1',
        writer_command='scripts.run_native_legacy_choice_pilot_v1 run',
        waiting_stage='await-legacy-choice-pilot-normal-closure',
        next_steps='Retain all three controls, native topic/duration choices, actual delivered advice, '
            'project calendars, T/U and all role costs. This is a reused-seed hand-control feasibility '
            'pilot, not optimization, autonomous invention, unused evaluation or readiness.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'frozen-source', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--writer-pid', type=int, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
