"""Finite original-writer wait, then paired cold audits and role costs."""
import argparse
from pathlib import Path
from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args,plan_schema='scienceutopia.native-topic-free-optimization.v1.plan',
        audit_module='scripts.audit_native_topic_free_optimization_v1',
        continuation_schema='scienceutopia.native-topic-free-optimization.v1.finish',
        writer_command='scripts.run_native_topic_free_optimization_v1 run',
        waiting_stage='await-free-topic-original-closure',
        next_steps='Interpret all objective-conditioned proposals, actual input/effect paths, nulls and costs. '
        'Determine an important supported claim and appropriate independent evidence before any new dispatch.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'): parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--writer-pid',type=int,required=True); run(parser.parse_args())


if __name__ == '__main__': main()
