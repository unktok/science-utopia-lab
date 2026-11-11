"""Await the existing fixed evaluation before two read-only effect-trace exports."""
import argparse
from pathlib import Path

from scripts.await_native_objective_fixed_report_v1 import run as wait
from scripts.finish_native_institution_effect_trace_v1 import run as finish_trace


def run(args):
    return wait(args,finish_function=finish_trace,await_schema='scienceutopia.native-institution-effect-trace-await.v1')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('continuation','output'):p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())


if __name__=='__main__':main()
