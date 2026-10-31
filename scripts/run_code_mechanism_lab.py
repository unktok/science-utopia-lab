#!/usr/bin/env python3
"""Generate Python institutions, execute, measure, and revise from actual loss.

Engineering fixture, not a science-policy experiment. No generated code runs
on the host. Reproduce with --proposal-input <previous result.json> (no LLM).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utopia.optimization.blackbox import Suggestion
from utopia.optimization.code_lab import (INPUT_SCHEMAS, REQUIRED_OUTPUTS, code_lab_observation,
                                          run_code_lab)
from utopia.system.code_mechanisms import DockerCodeExecutor, sha
from utopia.system.code_proposals import propose_local_code


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--proposal-input", type=Path)
    parser.add_argument("--allow-dirty-development", action="store_true")
    args = parser.parse_args()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=PROJECT_ROOT))
    if dirty and not args.allow_dirty_development:
        parser.error("commit source first, or explicitly allow a development smoke test")
    executor = DockerCodeExecutor()
    start = time.monotonic()
    frozen = json.loads(args.proposal_input.read_text()) if args.proposal_input else None
    report = {
        "schema": "scienceutopia.generated-code-lab.v1", "started_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip(),
        "dirty_development": dirty, "image_id": executor.image_id,
        "source_sha256": {str(path.relative_to(PROJECT_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in [Path(__file__).resolve(),
                                       PROJECT_ROOT / "utopia/system/code_mechanisms.py",
                                       PROJECT_ROOT / "utopia/system/code_proposals.py",
                                       PROJECT_ROOT / "utopia/optimization/code_lab.py"]},
        "workload": "deterministic structural paper fixture, two periods, five papers",
        "objective_note": "deliberately gameable record-count losses; engineering evidence only",
        "proposals": [], "rounds": [],
    }
    task = """Invent a stateful research commons institution. It receives review_batches
with papers (full metadata) and reviews keyed by paper id; each review contains overall_score.
Concrete input access: for delivered in context['inputs']['review_batches']:
    batch = delivered['payload']
    for paper in batch['papers']:
        reviews = batch['reviews'].get(paper['id'], [])
It must produce publication-compatible decisions, and also invent at least one new
additional artifact type and emit artifacts carrying substantive information that a future
institution could use. You choose the artifact schema, algorithm and memory representation.
For decisions copy each original paper metadata UNCHANGED into payload.paper, its id into
paper_id and incoming batch_id into batch_id. Both accept and reject are legal. final_score
may be numeric. Emit actor_ids using paper.author_id and artifact_ids using paper.id.
First design: use review information and persistent memory in your invented algorithm.
Keep implementation concise (roughly 25 lines). This is an engineering fixture, not a
claim of a good real-world scientific policy. Do not invent fields in input papers.
"""

    def propose(index, instruction, history):
        print(f"proposal {index}: " + ("frozen-source execution" if frozen else "local Qwen source generation"), flush=True)
        if frozen:
            result = {**frozen["proposals"][index]}
            result["evidence"] = run_code_lab(result["artifact"], executor)
        else:
            def probe(artifact):
                if len(artifact["outputs"]) < 2:
                    raise ValueError("this demonstration requests a new artifact output, not decisions only")
                return run_code_lab(artifact, executor)
            result = propose_local_code(task=instruction, input_schemas=INPUT_SCHEMAS,
                                        required_outputs=REQUIRED_OUTPUTS, history=history,
                                        validate_executable=probe, seed=911 + 10 * index,
                                        record_attempts=lambda attempts: write_json(
                                            args.output / f"proposal-{index}.attempts.json", attempts))
        report["proposals"].append(result)
        write_json(args.output / "progress.json", report)
        return result

    initial = propose(0, task, [])
    for index, objective in enumerate(("accepted-record-count", "rejected-record-count"), start=1):
        execution = initial["evidence"]
        suggestion = Suggestion("initial-" + objective, execution["system"], 0, "initial")
        observation = code_lab_observation(suggestion, execution, objective=objective)
        direction = "accepted" if objective.startswith("accepted") else "rejected"
        history = [{"source": initial["artifact"]["source"], "artifact": initial["artifact"],
                    "observation": observation.to_dict()}]
        instruction = task + f"\nNOW REVISE THE PREVIOUS CODE to minimize loss = -{direction} record count.\n"
        instruction += "Use the actual observed loss and state below. Change the implementation, not the objective.\n"
        instruction += "No acceptance quota or fairness veto is imposed; all-accept or all-reject is legal.\n"
        revised = propose(index, instruction, history)
        candidate = Suggestion("revision-" + objective, revised["evidence"]["system"], 1,
                               "llm-result-conditioned", observation.observation_id)
        outcome = code_lab_observation(candidate, revised["evidence"], objective=objective)
        # Independent full replay, and split checkpoint/resume on the revised code.
        replay = run_code_lab(revised["artifact"], executor)
        first = run_code_lab(revised["artifact"], executor, periods=1)
        resumed = run_code_lab(revised["artifact"], executor, periods=1, checkpoint=first["checkpoint"])
        expected = revised["evidence"]
        if (replay["event_stream_hash"] != expected["event_stream_hash"]
                or replay["checkpoint"] != expected["checkpoint"]
                or resumed["checkpoint"] != expected["checkpoint"]
                or first["events"] + resumed["events"] != expected["events"]):
            raise RuntimeError("generated source replay or checkpoint equivalence failed")
        report["rounds"].append({
            "objective": objective, "suggestions": [suggestion.to_dict(), candidate.to_dict()],
            "observations": [observation.to_dict(), outcome.to_dict()],
            "selected_system_fingerprint": min((observation, outcome), key=lambda o: o.loss).metadata["system_fingerprint"],
            "source_changed": initial["artifact"]["source"] != revised["artifact"]["source"],
            "replay_passed": True, "checkpoint_resume_passed": True,
        })
        print(f"{objective}: {observation.loss} -> {outcome.loss}; replay/resume PASS", flush=True)
        write_json(args.output / "progress.json", report)
    if frozen:
        for old, new in zip(frozen["rounds"], report["rounds"]):
            if old["observations"] != new["observations"]:
                raise RuntimeError("frozen source reproduction changed observations")
        report["frozen_reproduction_passed"] = True
        report["frozen_input_sha256"] = hashlib.sha256(args.proposal_input.read_bytes()).hexdigest()
    report["wall_seconds"] = time.monotonic() - start
    write_json(args.output / "result.json", report)
    print(json.dumps({"output": str(args.output.resolve()), "sha256": sha(report),
                      "wall_seconds": report["wall_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
