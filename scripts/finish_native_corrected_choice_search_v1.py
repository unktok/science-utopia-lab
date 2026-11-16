"""Wait for original writer and supervisor exit, then paired cold/cost only."""
import argparse
from functools import partial
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish
from scripts.finish_native_priority_method_comparison_v1 import wait_supervised
from scripts.supervise_native_corrected_choice_search_v1 import PREFIX
from scripts.run_native_corrected_choice_search_v1 import SCHEMA

ROOT=Path(__file__).resolve().parents[1]


def run(args):
    output=args.output.resolve()
    if output.exists() or any(output.is_relative_to(p.resolve()) for p in (ROOT,args.run,args.frozen_source)):
        raise ValueError('fresh closure outside reader/scientific sources and raw required before waiting')
    return finish(args,plan_schema=SCHEMA+'.plan',audit_module='scripts.audit_native_corrected_choice_search_v1',
        continuation_schema=SCHEMA+'.finish',writer_command='scripts.run_native_corrected_choice_search_v1 run',
        waiting_stage='await-original-corrected-choice-writer-and-supervisor',
        writer_wait=partial(wait_supervised,schema_prefix=PREFIX),
        next_steps='All24 original slots/own and best-known endpoints retained. Interpret effects/costs without '
            'reselection or guaranteed gain; do not automatically expand a flat result or declare publication readiness.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--writer-pid',type=int,required=True);run(parser.parse_args())


if __name__=='__main__':main()
