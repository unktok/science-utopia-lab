#!/usr/bin/env python3
"""Reproduce the committed initial-code proof without raw caches or an LLM."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utopia.optimization.code_lab import run_code_lab
from utopia.system.code_mechanisms import DockerCodeExecutor, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-input", type=Path, default=ROOT / "research/results/generated-code-mechanisms-v1.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    proof = json.loads(args.artifact_input.read_text())
    if proof.get("schema") != "scienceutopia.generated-code-execution-proof.v1" or sha(proof["artifact"]) != proof["artifact_sha256"]:
        raise ValueError("invalid execution-proof artifact")
    executor = DockerCodeExecutor(proof["image_id"])
    full = run_code_lab(proof["artifact"], executor)
    for key in ("system_fingerprint", "event_stream_hash", "summary"):
        if full[key] != proof[key]:
            raise ValueError("reproduction mismatch: " + key)
    first = run_code_lab(proof["artifact"], executor, periods=1)
    resumed = run_code_lab(proof["artifact"], executor, periods=1, checkpoint=first["checkpoint"])
    if resumed["checkpoint"] != full["checkpoint"] or first["events"] + resumed["events"] != full["events"]:
        raise ValueError("checkpoint/resume mismatch")
    report = {"schema": "scienceutopia.code-execution-replay.v1", "status": "pass",
              "evidence_role": "initial-source-execution-not-successful-optimization",
              "model_calls": 0, "checkpoint_resume_passed": True, "full": full}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "pass", "model_calls": 0, "summary": full["summary"]}))


if __name__ == "__main__":
    main()
