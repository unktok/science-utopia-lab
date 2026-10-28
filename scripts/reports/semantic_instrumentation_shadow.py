"""Validate semantic events and write one report-only shadow diagnostic."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

from utopia.metrics.semantic_instrumentation import build_shadow_report, load_bundle


def write_report(bundle_path: Path, output_path: Path) -> dict:
    bundle = load_bundle(bundle_path)
    report = build_shadow_report(bundle)
    if output_path.exists():
        raise FileExistsError(f"refuse to overwrite existing shadow report: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", dir=output_path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output_path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    report = write_report(args.bundle, args.output)
    print(json.dumps({
        "output": str(args.output),
        "source_bundle_sha256": report["source_bundle_sha256"],
        "authorization": report["authorization"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
