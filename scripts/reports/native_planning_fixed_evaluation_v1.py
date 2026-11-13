"""All fixed planning T/U policies and eight controls, without reselection."""
import argparse
from pathlib import Path

from scripts.reports.native_objective_fixed_evaluation_v1 import export as export_study


def export(args):return export_study(args,study='planning-v1')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','audit-one','audit-two','output'):parser.add_argument('--'+key,type=Path,required=True)
    export(parser.parse_args())


if __name__=='__main__':main()
