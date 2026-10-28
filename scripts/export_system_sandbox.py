#!/usr/bin/env python3
"""Export the synthetic SystemSpec design-console contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utopia.system.sandbox import build_system_sandbox_bundle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build_system_sandbox_bundle()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "bundle_hash": payload["bundle_hash"],
        "base_fingerprint": payload["authoritative_fixtures"][0]["fingerprint"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
