"""Normal closure to two original presentation audits and cost projections."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args, plan_schema='scienceutopia.native-parent-presentation-loop.v1.plan',
        audit_module='scripts.audit_native_parent_presentation_loop_v1',
        continuation_schema='scienceutopia.native-parent-presentation-loop-finish.v1',
        writer_command='scripts.run_native_parent_presentation_loop_v1 run',
        waiting_stage='await-native-parent-presentation-normal-closure',
        next_steps='Retain all twelve own slots, eight references, exact presentation frames, '
            'T/U cross-scores, ties/nulls, native consumers and costs before defining replication or unused evaluation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'frozen-source', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--writer-pid', type=int, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
