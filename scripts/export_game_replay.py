"""Export a saved artifact bundle for the buildless game replay viewer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utopia.replay import ArtifactBundle, build_viewer_payload, convert_artifacts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--title", default="ScienceUtopia replay")
    parser.add_argument("--source-label")
    args = parser.parse_args(argv)

    events = convert_artifacts(ArtifactBundle.discover(args.checkpoint))
    payload = build_viewer_payload(
        events,
        metadata={
            "title": args.title,
            "source_label": args.source_label or args.checkpoint.name,
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps({
            "events": len(payload["events"]),
            "frames": len(payload["frames"]),
            "stream_hash": payload["stream_hash"],
            "output": str(args.output),
        }),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
