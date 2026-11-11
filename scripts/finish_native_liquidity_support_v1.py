"""Fixed resource-study binding to the existing finite read-only finish engine."""
import argparse
from pathlib import Path

from scripts.finish_native_code_tested_loop_v1 import run as finish


def run(args):
    return finish(args,plan_schema='scienceutopia.native-liquidity-support.v1.plan',
        audit_module='scripts.audit_native_liquidity_support_v1',
        continuation_schema='scienceutopia.native-liquidity-support-finish.v1',
        writer_command='scripts.run_native_liquidity_support_v1 run',
        waiting_stage='await-resource-support-normal-closure',
        next_steps='Interpret all four developer controls, annual resources and downstream researcher inputs; '
            'identify the next meaningful objective/action question. No policy search or publication readiness is implied.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--writer-pid',type=int,required=True)
    run(parser.parse_args())


if __name__=='__main__':main()
