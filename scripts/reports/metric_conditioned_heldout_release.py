"""Gate and publish the completed metric-conditioned held-out study.

The readiness check intentionally reads only sealed metadata and SQLite run
status fields.  It does not open the cross-evaluation report before every
preregistered held-out run is complete.  Publication then delegates to the
fail-closed paper-slice builder and its atomic output boundary.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from scripts.figures.metric_conditioned_results import EXPERIMENTAL, SYNTHETIC
from scripts.reports.metric_conditioned_paper_slice import (
    PAPER_OUTPUT,
    _assignment,
    build_slice,
    write_outputs,
)


READINESS_SCHEMA = "scienceutopia.metric-conditioned-heldout-readiness.v1"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _status_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"missing held-out registry: {path}")
    connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return [
            dict(row)
            for row in connection.execute(
                "SELECT run_id, status, attempt, max_attempts "
                "FROM runs ORDER BY run_id"
            ).fetchall()
        ]
    finally:
        connection.close()


def probe_readiness(study_root: Path) -> dict[str, Any]:
    """Return status without reading any held-out metric or loss value."""
    snapshot_path = study_root / "held-out-evaluation/snapshot.json"
    freeze_path = study_root / "winner-freeze.json"
    if not snapshot_path.is_file() or not freeze_path.is_file():
        raise ValueError("winner freeze and held-out snapshot must exist")
    snapshot = _read_json(snapshot_path)
    freeze = _read_json(freeze_path)
    if snapshot.get("winner_freeze_sha256") != freeze.get("freeze_sha256"):
        raise ValueError("held-out snapshot does not match the winner freeze")
    expected = {item.get("run_id") for item in snapshot.get("runs", [])}
    if None in expected or not expected:
        raise ValueError("held-out snapshot has no valid sealed run set")
    rows = _status_rows(study_root / "held-out-evaluation/runs.sqlite3")
    actual = {row["run_id"] for row in rows}
    if actual != expected:
        raise ValueError("held-out registry rows differ from the sealed snapshot")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    exhausted_failures = [
        row["run_id"]
        for row in rows
        if row["status"] == "failed" and row["attempt"] >= row["max_attempts"]
    ]
    ready = counts.get("complete", 0) == len(expected) and not exhausted_failures
    report_exists = (study_root / "held-out-evaluation/cross-evaluation.json").is_file()
    return {
        "schema": READINESS_SCHEMA,
        "study_id": snapshot.get("study_id"),
        "study_revision": snapshot.get("study_revision"),
        "winner_freeze_sha256": snapshot.get("winner_freeze_sha256"),
        "expected_runs": len(expected),
        "status_counts": counts,
        "exhausted_failure_count": len(exhausted_failures),
        "ready_for_report": ready,
        "cross_evaluation_report_exists": report_exists,
        "ready_for_publication": ready and report_exists,
        "value_files_read": False,
        "note": (
            "Readiness uses sealed metadata and SQLite status fields only; "
            "no held-out metric or loss value was read."
        ),
    }


def publish(
    *,
    manifest_path: Path,
    study_root: Path,
    campaign_roots: Mapping[str, Path],
    output_dir: Path,
    classification: str,
    formats: tuple[str, ...],
) -> list[Path]:
    readiness = probe_readiness(study_root)
    if not readiness["ready_for_report"]:
        raise RuntimeError(
            "held-out split is incomplete; refusing to read cross-evaluation values"
        )
    if not readiness["cross_evaluation_report_exists"]:
        raise RuntimeError(
            "all held-out runs are complete, but the commit-pinned controller "
            "must generate report-evaluation before publication"
        )
    slice_data, figure_data = build_slice(
        manifest_path=manifest_path,
        study_root=study_root,
        campaign_roots=campaign_roots,
        classification=classification,
    )
    return write_outputs(slice_data, figure_data, output_dir, formats=formats)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check")
    check.add_argument("--study-root", required=True, type=Path)
    release = commands.add_parser("publish")
    release.add_argument("--manifest", required=True, type=Path)
    release.add_argument("--study-root", required=True, type=Path)
    release.add_argument(
        "--campaign-root", action="append", required=True, type=_assignment
    )
    release.add_argument("--output-dir", required=True, type=Path)
    release.add_argument(
        "--classification",
        choices=("experimental", "synthetic-test"),
        default="experimental",
    )
    release.add_argument("--formats", default="pdf,png")
    args = parser.parse_args(argv)
    if args.command == "check":
        print(json.dumps(probe_readiness(args.study_root), indent=2, sort_keys=True))
        return 0
    classification = (
        SYNTHETIC if args.classification == "synthetic-test" else EXPERIMENTAL
    )
    output = args.output_dir.resolve()
    if classification == SYNTHETIC and (
        output == PAPER_OUTPUT.resolve() or PAPER_OUTPUT.resolve() in output.parents
    ):
        raise ValueError("synthetic fixtures may not be published into the paper output")
    campaign_roots = dict(args.campaign_root)
    if len(campaign_roots) != len(args.campaign_root):
        raise ValueError("campaign roots contain duplicate arm assignments")
    paths = publish(
        manifest_path=args.manifest,
        study_root=args.study_root,
        campaign_roots=campaign_roots,
        output_dir=args.output_dir,
        classification=classification,
        formats=tuple(
            item.strip() for item in args.formats.split(",") if item.strip()
        ),
    )
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
