"""Separate native surrogate fidelity from exact frozen-bank policy fitting."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ["research/results/native-transition-v4-recovered.json",
          "research/results/native-cost-bank-v4.json", "research/artifacts/native-cost-bank-v4.json"]


def load_evidence(recovered, report, bank):
    from utopia.optimization.native_cost_bank import validate_bank
    from utopia.system.design_patch import digest
    validate_bank(bank)
    if (recovered["status"] != "existing-native-data-representation-and-proposal-independently-audited"
            or not recovered["raw_outputs_unchanged"] or recovered["new_native_executions"] != 0
            or report["bank_sha256"] != digest(bank) or report["new_native_executions"] != 0
            or report["transition_surrogate_used"] or report["sampled_reinforce_estimator_used"]):
        raise ValueError("separate audited native fidelity and exact-bank evidence required")
    costs = np.array([e["loss"] for e in bank["entries"]], dtype=float)
    if report["native_costs"] != costs.tolist() or recovered["summary"]["training_losses"] != costs.tolist():
        raise ValueError("audited native bank costs differ")
    for index, point in enumerate(report["path"]):
        p = np.array(point["probabilities"], dtype=float)
        if (point["step"] != index or p.shape != costs.shape or np.any(p < 0)
                or not np.isclose(p.sum(), 1, atol=1e-12, rtol=0)
                or not np.isclose(p @ costs, point["expected_full_native_loss"], atol=1e-12, rtol=0)
                or not np.allclose(p * (costs - p @ costs), point["gradient"], atol=1e-12, rtol=0)):
            raise ValueError("saved probability path and exact native-cost expectation differ")
    if (len(report["path"]) != report["steps"] + 1
            or report["initial_expected_loss"] != report["path"][0]["expected_full_native_loss"]
            or report["final_expected_loss"] != report["path"][-1]["expected_full_native_loss"]):
        raise ValueError("saved path endpoints differ")
    return recovered["summary"]["directional_fidelity"], report["path"], float(costs.min())


def make_figure():
    values = [json.loads((ROOT / name).read_text()) for name in INPUTS]
    fidelity, path, best = load_evidence(*values)
    plt.rcParams.update({"font.family": "DejaVu Sans", "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.65))
    fig.subplots_adjust(left=.105, right=.985, bottom=.29, top=.82, wspace=.48)
    ax = axes[0]
    ys = [fidelity["predicted_directional_derivative"], fidelity["actual_native_secant"]]
    ax.bar([0, 1], ys, width=.48, color=["#3269A8", "#B84D55"], zorder=3)
    ax.axhline(0, color="#8B95A3", lw=.7)
    for x, y in enumerate(ys):
        ax.annotate(f"{y:.3f}", (x, y), xytext=(0, -12 if y < 0 else 5),
                    textcoords="offset points", ha="center", fontsize=8)
    ax.set_xticks([0, 1], ["Represented\nderivative", "Actual native\nsecant"])
    ax.set_ylim(-2.45, .4)
    ax.set_ylabel("Directional loss sensitivity", fontsize=8)
    ax.set_title("A   Unused-design fidelity check", fontsize=8.5, loc="left", pad=11)
    ax = axes[1]
    ax.plot([p["step"] for p in path], [p["expected_full_native_loss"] for p in path],
            color="#3269A8", lw=1.7, label="Exact bank expectation")
    ax.axhline(best, color="#8B95A3", ls="--", lw=1, label="Already observed best")
    ax.set_xlabel("Adam updates of design probabilities", fontsize=8)
    ax.set_ylabel("Expected negative accepted count", fontsize=8)
    ax.set_ylim(-3.08, -2.38)
    ax.set_yticks([-3, -2.75, -2.5])
    ax.set_title("B   Frozen native bank: exact backward", fontsize=8.5, loc="left", pad=11)
    ax.legend(fontsize=6.6, loc="upper right", frameon=False)
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=7)
        ax.grid(axis="y", color="#E0E6ED", lw=.6, zorder=0)
    fig.text(.105, .045, "A: Fidelity not established.  B: Four fixed native outcomes; no new worlds, best or validation.",
             fontsize=6.9, color="#637285")
    output = ROOT / "paper/figures/native-transition-validation-v4"
    for suffix in (".pdf", ".png"):
        kwargs = {"metadata": {"CreationDate": None, "ModDate": None}} if suffix == ".pdf" else {"dpi": 200}
        fig.savefig(output.with_suffix(suffix), **kwargs)
    plt.close(fig)
    inputs = [*INPUTS, "scripts/figures/native_transition_validation.py"]
    manifest = {"schema": "scienceutopia.native-transition-validation-figure.v4",
        "classification": "native-development-fidelity-and-offline-bank-fit-not-heldout",
        "inputs": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in inputs},
        "native_fidelity_established": False, "new_native_best": False,
        "outputs": {str(output.with_suffix(s).relative_to(ROOT)): hashlib.sha256(output.with_suffix(s).read_bytes()).hexdigest() for s in (".pdf", ".png")}}
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    make_figure()
