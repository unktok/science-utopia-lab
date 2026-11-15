"""Wait on the exact original matched writer, then paired source audits/costs."""
import argparse
from pathlib import Path
from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args, plan_schema='scienceutopia.native-consumer-source-comparison.v1.plan',
        audit_module='scripts.audit_native_consumer_source_comparison_v1',
        continuation_schema='scienceutopia.native-consumer-source-comparison.v1.finish',
        writer_command='scripts.run_native_consumer_source_comparison_v1 run',
        waiting_stage='await-original-consumer-comparison-closure',
        next_steps='Retain all eight matched own slots and three references, exact information visibility, '
        'full native input/effect/loss paths, nulls and per-role costs. No automatic method-superiority claim.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'frozen-source', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--writer-pid', type=int, required=True); run(parser.parse_args())


if __name__ == '__main__':
    main()
