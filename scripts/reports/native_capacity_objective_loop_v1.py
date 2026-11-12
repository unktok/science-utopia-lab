"""All four T/P slots and five strong controls after double original audit."""
import argparse
from pathlib import Path

from scripts.reports.native_objective_instrument_loop_v1 import export as export_study


def export(args):return export_study(args,study='capacity-v1')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','audit-one','audit-two','output'):p.add_argument('--'+key,type=Path,required=True)
    export(p.parse_args())


if __name__=='__main__':main()
