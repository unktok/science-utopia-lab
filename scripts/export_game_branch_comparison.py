"""Export the deterministic NOCTILUCA intervention-branch fixture bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utopia.replay.branch_comparison import branch_manifest, branch_payload


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args(argv)
    payloads = {
        branch_id: branch_payload(branch_id)
        for branch_id in ("open-synthesis", "sealed-panel")
    }
    for branch_id, payload in payloads.items():
        _write(args.output_directory / f"branch-{branch_id}.replay.json", payload)
    manifest = branch_manifest(payloads)
    _write(args.output_directory / "intervention-branches.manifest.json", manifest)
    print(json.dumps({
        "manifest": str(args.output_directory / "intervention-branches.manifest.json"),
        "shared_origin": manifest["shared_origin"],
        "branches": [branch["id"] for branch in manifest["branches"]],
    }), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
