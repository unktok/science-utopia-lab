#!/usr/bin/env python3
"""Run the bounded rule-generation / structure / direct-gradient lab.

Example:
  .venv/bin/python scripts/run_generative_lab.py --output outputs/generative-lab-v1
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

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utopia.optimization.generative_system import GenerativeSystemSpace, seed_generative_system
from utopia.optimization.program_search import optimize_program_world, search_program_systems
from utopia.replay.program_lab import viewer_entry
from utopia.system import SystemSpec
from utopia.system.program_proposals import attach_generated_proposal, generate_local_proposal
from utopia.system.program_world import evaluate_program_system, initial_world, make_world_loss
from utopia.system.programs import digest


def write_json(path: Path, value) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ui-output", type=Path)
    parser.add_argument("--budget", type=int, default=5)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--periods", type=int, default=3)
    parser.add_argument("--ollama", action="store_true")
    parser.add_argument("--proposal-input", type=Path,
                        help="reuse an already recorded local Qwen proposal without a new query")
    parser.add_argument("--allow-dirty-development", action="store_true")
    args = parser.parse_args()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=PROJECT_ROOT, text=True))
    if dirty and not args.allow_dirty_development:
        parser.error("commit development changes first or use --allow-dirty-development for a local smoke test")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("output directory is not empty; choose a fresh run directory")
    started = time.perf_counter()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    source_files = [*sorted((PROJECT_ROOT / "utopia/system").glob("program*.py")),
                    PROJECT_ROOT / "utopia/optimization/generative_system.py",
                    PROJECT_ROOT / "utopia/optimization/program_search.py",
                    PROJECT_ROOT / "utopia/optimization/blackbox.py",
                    PROJECT_ROOT / "utopia/optimization/loss.py",
                    PROJECT_ROOT / "utopia/replay/program_lab.py",
                    PROJECT_ROOT / "utopia/system/model.py",
                    PROJECT_ROOT / "utopia/system/runtime.py",
                    PROJECT_ROOT / "utopia/system/validation.py", Path(__file__)]
    source_hashes = {str(path.relative_to(PROJECT_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in source_files}
    system = seed_generative_system()
    worlds = [initial_world(811), initial_world(821)]
    generated = None
    if args.ollama and args.proposal_input:
        parser.error("choose --ollama or --proposal-input")
    if args.ollama or args.proposal_input:
        print("Generating a new mechanism and a six-agent world with local Qwen3-8B…", flush=True)
        generated = (generate_local_proposal() if args.ollama else
                     json.loads(args.proposal_input.read_text(encoding="utf-8")))
        write_json(args.output / "qwen-proposal.raw.json", generated)
        system = attach_generated_proposal(system, generated)
        worlds = [generated["world"], initial_world(821)]
    payload = {
        "schema": "scienceutopia.generative-lab-view.v1",
        "source": {"commit": commit, "dirty_development": dirty, "files": source_hashes,
                   "started_utc": datetime.now(timezone.utc).isoformat(),
                   "runtime": {"python": sys.version, "torch": torch.__version__,
                               "torch_device": "cpu", "torch_threads": 1,
                               "deterministic_algorithms": True}},
        "backend": "numeric-program-world-v1",
        "qwen_role": "frozen-mechanism-and-initial-attributes" if generated else "none",
        "qwen_in_autograd": False,
        "worlds": worlds, "arms": [],
    }
    reports = {}
    for objective in ("production", "burden"):
        print(f"Running objective={objective}: generated-program black box, direct gradient, hybrid…", flush=True)
        loss = make_world_loss(objective)
        baseline = evaluate_program_system(system, worlds, loss, periods=args.periods, record=True)
        blackbox = search_program_systems(system, worlds, loss, budget=args.budget, periods=args.periods)
        gradient = optimize_program_world(system, worlds, loss, steps=args.steps, periods=args.periods)
        gradient_system = SystemSpec.from_dict(gradient["system_spec"])
        hybrid = search_program_systems(gradient_system, worlds, loss,
                                        budget=args.budget, seed=29, periods=args.periods)
        systems = [viewer_entry("Initial system", system, worlds[0], baseline)]
        for label, result in (("Black-box best", blackbox), ("Hybrid best", hybrid)):
            if result["system_spec"] is None:
                continue
            chosen = SystemSpec.from_dict(result["system_spec"])
            outer = evaluate_program_system(chosen, worlds, loss, periods=args.periods, record=True)
            systems.append(viewer_entry(label, chosen, worlds[0], outer))
        systems.append(viewer_entry("Gradient projection", gradient_system, worlds[0], gradient["final_outer"]))
        arm = {
            "objective": objective, "loss_spec": loss,
            "systems": systems, "gradient_trace": gradient["trace"],
            "gradient_audit": gradient["gradient_audit"],
            "projection_gap": gradient["relaxation_projection_gap"],
            "blackbox_path": [{
                "proposal_id": record["suggestion"]["suggestion_id"],
                "phase": record["suggestion"]["phase"],
                "parent_observation": record["suggestion"]["based_on_observation_id"],
                "system_fingerprint": record["system_fingerprint"],
                "loss": record["observation"]["loss"],
                "program_hashes": record["program_hashes"],
            } for record in blackbox["records"]],
        }
        payload["arms"].append(arm)
        reports[objective] = {"loss_spec": loss, "baseline": baseline,
                              "blackbox": blackbox, "gradient": gradient, "hybrid": hybrid}
        print(json.dumps({"objective": objective, "baseline": baseline["loss"],
                          "blackbox": blackbox["best_loss"], "gradient": gradient["final_outer"]["loss"],
                          "hybrid": hybrid["best_loss"], "gradient_audit": gradient["gradient_audit"]["all_pass"]}),
              flush=True)
    # Exhaustively exercise mutation *operators*, not every possible system.
    showcase = []
    for index, operation in enumerate(("program", "add-node", "remove-node", "add-edge",
                                       "remove-edge", "delay", "order", "parameter")):
        candidate, mutation = GenerativeSystemSpace(system).mutate_with_record(
            system.to_dict(), seed=113, proposal_index=index + 1, operation=operation,
        )
        outer = evaluate_program_system(SystemSpec.from_dict(candidate), worlds,
                                        make_world_loss("production"), periods=args.periods)
        showcase.append({"mutation": mutation, "outer_loss": outer["loss"],
                         "system_spec": candidate})
    cross_scoring = []
    for source_objective, report in reports.items():
        for method, candidate in (("blackbox", report["blackbox"]["system_spec"]),
                                  ("gradient", report["gradient"]["system_spec"]),
                                  ("hybrid", report["hybrid"]["system_spec"])):
            if candidate is None:
                continue
            chosen = SystemSpec.from_dict(candidate)
            cross_scoring.append({
                "selected_under": source_objective, "method": method,
                "system_fingerprint": chosen.fingerprint,
                "development_losses": {target: evaluate_program_system(
                    chosen, worlds, make_world_loss(target), periods=args.periods,
                )["loss"] for target in reports},
            })
    elapsed = time.perf_counter() - started
    payload["elapsed_seconds"] = elapsed
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    envelope = {"schema": "scienceutopia.generative-lab-envelope.v1", "payload_json": payload_json,
                "payload_sha256": hashlib.sha256(payload_json.encode()).hexdigest()}
    report = {"schema": "scienceutopia.generative-lab-report.v1", "source": payload["source"],
              "config": {"budget": args.budget, "steps": args.steps, "periods": args.periods,
                         "seeds": [811, 821], "population": 6},
              "worlds": worlds, "arms": reports, "mutation_showcase": showcase,
              "development_cross_scoring": cross_scoring,
              "qwen_receipt": generated["receipt"] if generated else None,
              "elapsed_seconds": elapsed}
    report_hash = write_json(args.output / "report.json", report)
    viewer_hash = write_json(args.output / "viewer.json", envelope)
    if args.ui_output:
        write_json(args.ui_output, envelope)
    write_json(args.output / "manifest.json", {
        "schema": "scienceutopia.generative-lab-manifest.v1", "source": payload["source"],
        "files": {"report.json": report_hash, "viewer.json": viewer_hash},
        "viewer_payload_sha256": envelope["payload_sha256"],
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    })
    print(json.dumps({"output": str(args.output), "elapsed_seconds": elapsed,
                      "report_sha256": report_hash, "viewer_sha256": viewer_hash}), flush=True)


if __name__ == "__main__":
    main()
