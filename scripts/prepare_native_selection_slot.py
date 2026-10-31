#!/usr/bin/env python3
"""Declare a developer baseline implementation slot, not model invention."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_kernel import legacy_world_system
    from utopia.system.native_selection_slot import selection_source_slot
    from utopia.utils.data_utils import write_json_atomic
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=1301)
    parser.add_argument('--rates', type=float, nargs='+')
    args = parser.parse_args()
    spec = selection_source_slot(legacy_world_system(seed=args.seed), image_id=DockerCodeExecutor().image_id, annual_rates=args.rates)
    write_json_atomic(args.output, spec.to_dict(), sort_keys=True, allow_nan=False)
    print(spec.fingerprint)


if __name__ == '__main__':
    main()
