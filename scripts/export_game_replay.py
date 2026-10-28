"""Export a saved artifact bundle for the buildless game replay viewer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utopia.replay import (
    ArtifactBundle,
    build_viewer_payload,
    build_viewer_payload_v2,
    convert_artifacts,
    export_campaign_bundle,
    vertical_slice_events,
    vertical_slice_metadata,
    vertical_slice_presentation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", nargs="?", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--title")
    parser.add_argument("--source-label")
    parser.add_argument(
        "--campaign-source-manifest",
        type=Path,
        help="Verified source declaration for a completed commit-pinned campaign run.",
    )
    parser.add_argument(
        "--campaign-root",
        type=Path,
        help="Local raw campaign root; required with --campaign-source-manifest.",
    )
    parser.add_argument(
        "--view-version",
        choices=("1", "2"),
        help=(
            "Browser replay contract. Saved artifacts default to v1; the vertical "
            "slice fixture is always v2."
        ),
    )
    parser.add_argument(
        "--vertical-slice-fixture",
        action="store_true",
        help=(
            "Export the explicit synthetic v2 renderer fixture. This is not an "
            "experimental run and does not accept a checkpoint."
        ),
    )
    args = parser.parse_args(argv)

    if args.campaign_source_manifest:
        if args.checkpoint is not None or args.vertical_slice_fixture:
            parser.error("campaign source cannot be combined with a checkpoint or fixture")
        if args.campaign_root is None:
            parser.error("--campaign-root is required with --campaign-source-manifest")
        if args.view_version == "1":
            parser.error("campaign source requires replay-view v2")
        payload = export_campaign_bundle(
            args.campaign_source_manifest,
            args.campaign_root,
            PROJECT_ROOT,
        )
    elif args.vertical_slice_fixture:
        if args.checkpoint is not None:
            parser.error("checkpoint cannot be combined with --vertical-slice-fixture")
        if args.view_version == "1":
            parser.error("--vertical-slice-fixture requires replay-view v2")
        events = vertical_slice_events()
        choreography, ambient = vertical_slice_presentation(events)
        metadata = vertical_slice_metadata()
        if args.title:
            metadata["title"] = args.title
        if args.source_label:
            metadata["source_label"] = args.source_label
        payload = build_viewer_payload_v2(
            events,
            metadata=metadata,
            choreography=choreography,
            ambient=ambient,
        )
    else:
        if args.checkpoint is None:
            parser.error("checkpoint is required unless a fixture or campaign source is used")
        events = convert_artifacts(ArtifactBundle.discover(args.checkpoint))
        metadata = {
            "title": args.title or "ScienceUtopia replay",
            "source_label": args.source_label or args.checkpoint.name,
        }
        payload = (
            build_viewer_payload(events, metadata=metadata)
            if args.view_version in (None, "1")
            else build_viewer_payload_v2(events, metadata=metadata)
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps({
            "schema_version": payload["schema_version"],
            "events": len(
                payload.get("events", payload.get("canonical", {}).get("events", []))
            ),
            "frames": len(
                payload.get("frames", payload.get("projection", {}).get("frames", []))
            ),
            "stream_hash": payload["stream_hash"],
            "output": str(args.output),
        }),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
