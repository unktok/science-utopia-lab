"""All six frozen labels, cross-losses and separate objective/access contrasts."""
import argparse
from pathlib import Path

from scripts.reports.native_objective_fixed_evaluation_v1 import export as common_export


def export(args): return common_export(args, study='longitudinal-v1')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'audit-one', 'audit-two', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__': main()
