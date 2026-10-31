"""Record an initial-code execution proof without promoting a failed search.

This deliberately accepts an incomplete lab progress file. It publishes ONLY
the generated initial implementation/replay proof and failed revision receipts;
it does not substitute that proof for a completed optimization experiment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from utopia.system.code_mechanisms import DockerCodeExecutor, sha, validate_code_artifact
from utopia.optimization.code_lab import run_code_lab


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--progress", type=Path, required=True)
    parser.add_argument("--attempts", type=Path, nargs="+", required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    progress = json.loads(args.progress.read_text())
    if progress["dirty_development"] or len(progress["proposals"]) != 1 or progress["rounds"]:
        raise ValueError("this probe requires the clean initial-only incomplete campaign")
    for path, expected in progress["source_sha256"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise ValueError("execution source differs from pinned experiment: " + path)
    proposal = progress["proposals"][0]
    artifact = proposal["artifact"]
    validate_code_artifact(artifact)
    final_attempt = proposal["attempts"][-1]
    for attempt in proposal["attempts"]:
        if (sha(attempt["request"]) != attempt["receipt"]["request_sha256"]
                or sha(attempt["response"]) != attempt["receipt"]["response_sha256"]):
            raise ValueError("initial proposal receipt mismatch")
    generated = json.loads(final_attempt["response"]["message"]["content"])
    if (final_attempt["status"] != "complete" or generated["source"] != artifact["source"]
            or proposal["receipt"] != final_attempt["receipt"]
            or generated["state_schema"] != artifact["state_schema"]
            or any(artifact["outputs"].get(k) != v for k, v in generated["new_port_schemas"].items())):
        raise ValueError("executed code differs from validated model response")
    executor = DockerCodeExecutor(progress["image_id"])
    repeated = run_code_lab(artifact, executor)
    first = run_code_lab(artifact, executor, periods=1)
    resumed = run_code_lab(artifact, executor, periods=1, checkpoint=first["checkpoint"])
    original = proposal["evidence"]
    for key in ("system", "system_fingerprint", "summary", "checkpoint", "events", "event_stream_hash"):
        if repeated[key] != original[key]:
            raise ValueError("initial source replay mismatch: " + key)
    if resumed["checkpoint"] != original["checkpoint"] or first["events"] + resumed["events"] != original["events"]:
        raise ValueError("initial source checkpoint/resume mismatch")
    records = [e["payload"] for e in repeated["events"] if e["event_type"] == "publication.recorded"]
    summary = repeated["summary"]
    if (summary["accepted"] != sum(r["status"] == "accept" for r in records)
            or summary["rejected"] != sum(r["status"] == "reject" for r in records)
            or summary["publication_records"] != len(records)):
        raise ValueError("host summary differs from actual publication events")
    # Identity conservation is checked as an audit of this exercised fixture,
    # not a fairness/acceptance constraint or a universally meaningful schema.
    expected_ids = {f"paper-{period}-{index}" for period, size in enumerate((2, 3)) for index in range(size)}
    if {r["paper_id"] for r in records} != expected_ids or len(records) != len(expected_ids):
        raise ValueError("this exercised source did not preserve the five fixture paper identities")
    development = []
    for path in args.attempts:
        attempts = json.loads(path.read_text())
        for attempt in attempts:
            if (sha(attempt["request"]) != attempt["receipt"]["request_sha256"]
                    or sha(attempt["response"]) != attempt["receipt"]["response_sha256"]):
                raise ValueError("development attempt receipt mismatch")
        development.append({
            "path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "attempts": [{"status": a["status"], "error": a.get("error"), "receipt": a["receipt"],
                          "done_reason": a["response"].get("done_reason")} for a in attempts],
        })
    raw = {"original": original, "repeated": repeated, "first": first, "resumed": resumed}
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    args.raw_output.write_text(json.dumps(raw, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    result = {
        "schema": "scienceutopia.generated-code-execution-proof.v1",
        "evidence_role": "initial-execution-only-optimization-incomplete",
        "source_commit": progress["source_commit"], "source_sha256": progress["source_sha256"],
        "image_id": executor.image_id, "artifact": artifact, "artifact_sha256": sha(artifact),
        "rationale": proposal["rationale"],
        "verification": {"script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         "python": sys.version},
        "model_receipt": proposal["receipt"], "system_fingerprint": repeated["system_fingerprint"],
        "summary": summary, "event_stream_hash": repeated["event_stream_hash"],
        "initial_attempt_statuses": [a["status"] for a in proposal["attempts"]],
        "frozen_source_replay_passed": True, "checkpoint_resume_passed": True,
        "publication_counts_independently_verified": True, "fixture_paper_identity_check_passed": True,
        "optimization_status": "failed-during-first-objective-code-revision",
        "selected_optimized_system": None, "failed_proposals_assigned_numeric_loss": False,
        "development_attempts": development,
        "raw_artifacts": [{"path": str(p.resolve()), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                          for p in (args.progress, args.raw_output)],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"verified": "initial-execution-only", "summary": summary,
                      "optimization": result["optimization_status"], "output": str(args.output.resolve())}))


if __name__ == "__main__":
    main()
