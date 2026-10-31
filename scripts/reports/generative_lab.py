"""Verify recorded miniature runs and publish compact evidence and figures."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from utopia.system import SystemSpec
from utopia.system.program_world import evaluate_program_system, make_world_loss
from utopia.system.programs import digest


def load_run(directory: Path) -> tuple[dict, dict]:
    manifest = json.loads((directory / "manifest.json").read_text())
    if (manifest.get("schema") != "scienceutopia.generative-lab-manifest.v1"
            or set(manifest.get("files", {})) != {"report.json", "viewer.json"}):
        raise ValueError("manifest must bind exactly report.json and viewer.json")
    for filename, expected in manifest["files"].items():
        if filename not in {"report.json", "viewer.json"}:
            raise ValueError("unexpected run artifact")
        if hashlib.sha256((directory / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f"artifact hash mismatch: {filename}")
    report = json.loads((directory / "report.json").read_text())
    if report.get("schema") != "scienceutopia.generative-lab-report.v1":
        raise ValueError("unsupported recorded report")
    if report["source"]["dirty_development"]:
        raise ValueError("recorded result requires a clean source revision")
    if report["source"] != manifest["source"]:
        raise ValueError("report/manifest source mismatch")
    for arm in report["arms"].values():
        if not arm["gradient"]["gradient_audit"]["all_pass"]:
            raise ValueError("gradient audit failed")
    return report, manifest


def assert_reproduction(original: dict, repeated: dict) -> dict:
    for key in ("arms", "worlds", "mutation_showcase", "development_cross_scoring", "config", "qwen_receipt"):
        if original[key] != repeated[key]:
            raise ValueError(f"numerical reproduction differs: {key}")
    for key in ("commit", "files", "runtime"):
        if original["source"][key] != repeated["source"][key]:
            raise ValueError(f"reproduction source differs: {key}")
    return {"status": "exact-match", "compared": ["programs", "systems", "losses", "metrics",
            "gradients", "trajectories", "proposal-lineage", "mutation-showcase"],
            "excluded": ["wall-time", "started-utc", "completed-utc"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--reproduction-run-dir", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--figures", type=Path, required=True)
    parser.add_argument("--proposal-output", type=Path)
    args = parser.parse_args()
    report, manifest = load_run(args.run_dir)
    repeated, repeated_manifest = load_run(args.reproduction_run_dir)
    reproduction = assert_reproduction(report, repeated)
    selected = []
    for objective, arm in report["arms"].items():
        for method in ("blackbox", "gradient", "hybrid"):
            outcome = arm[method]
            spec = SystemSpec.from_dict(outcome["system_spec"])
            declared = outcome["final_outer"]["loss"] if method == "gradient" else outcome["best_loss"]
            recomputed = evaluate_program_system(spec, report["worlds"], arm["loss_spec"],
                                                periods=report["config"]["periods"])
            if abs(recomputed["loss"] - declared) > 1e-12:
                raise ValueError("independent discrete loss recomputation failed")
            selected.append({
                "objective": objective, "method": method, "loss": declared,
                "system_fingerprint": spec.fingerprint,
                "mechanism_count": len(spec.mechanisms), "edge_count": len(spec.connections),
                "mechanisms": [{"id": node.mechanism_id, "family": node.family.value,
                                "program_sha256": digest(node.parameters["program"])}
                               for node in spec.mechanisms],
                "schedule": [schedule.mechanism_id for schedule in sorted(
                    spec.schedules, key=lambda item: (item.phase, item.mechanism_id),
                )],
                "metrics_mean": {key: sum(run["metrics"][key] for run in recomputed["runs"])
                                 / len(recomputed["runs"]) for key in recomputed["runs"][0]["metrics"]},
            })
    max_error = max(row["absolute_error"] for arm in report["arms"].values()
                    for row in arm["gradient"]["gradient_audit"]["records"])
    summary = {
        "schema": "scienceutopia.generative-lab-compact-result.v1",
        "source": report["source"], "config": report["config"],
        "evidence_role": "miniature-development-not-held-out",
        "backend": "numeric-program-world-v1", "qwen_in_autograd": False,
        "elapsed_seconds": report["elapsed_seconds"], "qwen_receipt": report["qwen_receipt"],
        "gradient_maximum_absolute_error": max_error,
        "baseline": {key: value["baseline"]["loss"] for key, value in report["arms"].items()},
        "selected": selected, "development_cross_scoring": report["development_cross_scoring"],
        "projection_gaps": {key: value["gradient"]["relaxation_projection_gap"]
                            for key, value in report["arms"].items()},
        "mutation_showcase": [{"mutation": value["mutation"], "outer_loss": value["outer_loss"]}
                              for value in report["mutation_showcase"]],
        "reproduction": reproduction,
        "raw_artifacts": {"run": str(args.run_dir.resolve()), "files": manifest["files"],
                          "reproduction_run": str(args.reproduction_run_dir.resolve()),
                          "reproduction_files": repeated_manifest["files"]},
    }
    generated = None
    if report["qwen_receipt"] is not None:
        raw_path = args.run_dir / "qwen-proposal.raw.json"
        generated = json.loads(raw_path.read_text())
        if (generated["receipt"] != report["qwen_receipt"]
                or generated["world"] != report["worlds"][0]
                or digest(generated["response"]) != generated["receipt"]["response_sha256"]):
            raise ValueError("recorded Qwen proposal/response receipt mismatch")
        for arm in report["arms"].values():
            initial = SystemSpec.from_dict(arm["gradient"]["baseline_system"])
            invented = next(node for node in initial.mechanisms if node.mechanism_id == "generated-commons")
            if invented.parameters["program"] != generated["proposal"]["program"]:
                raise ValueError("recorded Qwen program differs from executed baseline")
        summary["raw_artifacts"]["qwen-proposal.raw.json"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    if args.proposal_output:
        if generated is None:
            raise ValueError("numeric-only run has no recorded Qwen proposal")
        compact = {key: generated[key] for key in ("proposal", "world", "receipt")}
        args.proposal_output.parent.mkdir(parents=True, exist_ok=True)
        args.proposal_output.write_text(json.dumps(compact, indent=2, ensure_ascii=False) + "\n")
    args.figures.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    figure, axes = plt.subplots(2, 2, figsize=(10, 6), layout="constrained")
    for row, (objective, arm) in enumerate(report["arms"].items()):
        gradient = arm["gradient"]
        axes[row, 0].plot([point["step"] for point in gradient["trace"]],
                          [point["relaxed_loss"] for point in gradient["trace"]],
                          color="#207e82", label="relaxed recurrent-world loss")
        axes[row, 0].scatter([0, report["config"]["steps"]],
                             [gradient["initial_outer"]["loss"], gradient["final_outer"]["loss"]],
                             color="#b85d9c", marker="D", zorder=4, label="exact projected loss")
        axes[row, 0].set(title=f"{objective}: direct whole-world gradients", xlabel="gradient update", ylabel="loss (minimize)")
        observations = [record["observation"]["loss"] for record in arm["blackbox"]["records"]]
        valid = [(index + 1, loss) for index, loss in enumerate(observations) if loss is not None]
        axes[row, 1].plot([item[0] for item in valid], [item[1] for item in valid],
                          color="#89609b", marker="o", label="discrete generated-system loss")
        best = []
        for _, loss in valid:
            best.append(min(loss, best[-1]) if best else loss)
        axes[row, 1].step([item[0] for item in valid], best, where="post", color="#327f89", label="incumbent")
        axes[row, 1].set(title=f"{objective}: compositional black-box search", xlabel="outer evaluation", ylabel="loss (minimize)")
    for ax in axes.flat:
        ax.grid(alpha=0.15)
        ax.legend(fontsize=7, loc="best")
    figure.suptitle("Generated institutions: optimization paths in a miniature numeric world\nDevelopment evidence; information and budgets are not matched", fontsize=11)
    for extension in ("png", "pdf"):
        figure.savefig(args.figures / f"search-paths.{extension}", dpi=180)
    plt.close(figure)
    figure, ax = plt.subplots(figsize=(7, 4.5), layout="constrained")
    markers = {"blackbox": "o", "gradient": "D", "hybrid": "s"}
    colors = {"production": "#287e88", "burden": "#a267a4"}
    offsets = {("production", "blackbox"): (12, 12),
               ("production", "gradient"): (-115, -12),
               ("production", "hybrid"): (-110, 10),
               ("burden", "blackbox"): (-105, -18),
               ("burden", "gradient"): (12, 12),
               ("burden", "hybrid"): (12, -18)}
    for result in selected:
        profile = result["metrics_mean"]
        ax.scatter(profile["production"], profile["burden"], marker=markers[result["method"]],
                   color=colors[result["objective"]], s=65)
        ax.annotate(f"{result['objective']} / {result['method']}",
                    (profile["production"], profile["burden"]),
                    xytext=offsets[result["objective"], result["method"]],
                    textcoords="offset points", fontsize=7)
    ax.set(xlabel="Mean production (two development worlds)", ylabel="Mean mechanism activity burden",
           title="Changing the objective changes the resulting system\nDescriptive miniature result; no universal winner selected")
    ax.grid(alpha=0.15)
    ax.margins(x=0.12, y=0.15)
    for extension in ("png", "pdf"):
        figure.savefig(args.figures / f"objective-conditioned-systems.{extension}", dpi=180)
    plt.close(figure)
    print(json.dumps({"result": str(args.result), "selected_systems": len(selected),
                      "reproduction": reproduction["status"], "maximum_gradient_error": max_error}))


if __name__ == "__main__":
    main()
