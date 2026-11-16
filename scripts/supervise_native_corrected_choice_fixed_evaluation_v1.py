"""One corrected fixed-policy writer, actual child exit, no restart/refill."""
import argparse
from pathlib import Path

from scripts import run_native_corrected_choice_fixed_evaluation_v1 as driver
from scripts.supervise_native_corrected_choice_search_v1 import run as supervise

PREFIX = 'scienceutopia.native-corrected-choice-fixed-evaluation-writer'


def run(root):
    return supervise(root, driver_module=driver, schema_prefix=PREFIX,
        writer_module='scripts.run_native_corrected_choice_fixed_evaluation_v1')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--run', type=Path, required=True)
    run(parser.parse_args().run)
