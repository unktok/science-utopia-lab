#!/usr/bin/env python3
"""Export actual native campaign evidence for the local game-like design UI."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--loss', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from utopia.optimization.loss import load_loss_spec
    from utopia.replay.native_lab import native_lab_envelope
    from utopia.utils.data_utils import write_json_atomic
    result = native_lab_envelope(args.run, loss_spec=load_loss_spec(args.loss))
    write_json_atomic(args.output, result, allow_nan=False)
    print(result['payload_sha256'])


if __name__ == '__main__': main()
