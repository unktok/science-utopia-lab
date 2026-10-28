#!/usr/bin/env python3
"""Export verified and explicitly synthetic mission-control bundles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utopia.optimization.mission_control import (
    build_mission_control_snapshot,
    build_synthetic_mission_fixture,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--synthetic-output", type=Path)
    parser.add_argument("--observed-at-utc")
    args = parser.parse_args()
    payload = build_mission_control_snapshot(args.source_root, observed_at_utc=args.observed_at_utc)
    _write(args.output, payload)
    if args.synthetic_output:
        _write(args.synthetic_output, build_synthetic_mission_fixture(payload))
    print(json.dumps({"output": str(args.output), "snapshot_hash": payload["snapshot_hash"], "observed_at_utc": payload["observed_at_utc"]}, sort_keys=True))


if __name__ == "__main__":
    main()
