#!/usr/bin/env python3
"""Print a result-blind progress snapshot for a held-out evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utopia.optimization.held_out_progress import build_held_out_progress


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--expected-runs", type=int, default=15)
    parser.add_argument("--observed-at-utc")
    parser.add_argument("--stale-after-hours", type=float, default=4.0)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    snapshot = build_held_out_progress(
        args.registry,
        expected_runs=args.expected_runs,
        observed_at_utc=args.observed_at_utc,
        stale_after_hours=args.stale_after_hours,
    )
    print(
        json.dumps(
            snapshot,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=None if args.compact else 2,
        )
    )
    return 2 if snapshot["health"]["stalled"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
