"""Frozen workflow own/control policies, both losses and objective contrasts."""
import argparse
from pathlib import Path

from scripts.reports.native_objective_fixed_evaluation_v1 import export as common_export


def export(args): return common_export(args, study='workflow-v1')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'audit-one', 'audit-two', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__': main()
