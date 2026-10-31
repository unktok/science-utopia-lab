"""Render the actual conditional-fit trace separately from native hard outcomes.

Reads tracked evidence only; never runs inference or mutates campaign state.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "research/results/native-trace-relaxation-v1.json"
ENVELOPE = ROOT / "game-ui-v2/public/data/native-design-lab-v1.json"


def load_evidence(audit: dict, envelope: dict) -> tuple[list[dict], list[float]]:
    """Fail closed on identity, trace, installed-program or outcome disagreement."""
    payload_bytes = envelope["payload_json"].encode("utf8")
    if hashlib.sha256(payload_bytes).hexdigest() != envelope["payload_sha256"]:
        raise ValueError("native evidence payload hash mismatch")
    payload = json.loads(payload_bytes)
    if payload["source"] != audit["binding"]:
        raise ValueError("native source binding mismatch")
    fit = payload["relaxation"]
    if fit["trace_sha256"] != audit["relaxation"]["trace_sha256"]:
        raise ValueError("native fit trace mismatch")
    if fit["full_native_world_autograd"] is not False:
        raise ValueError("unsupported full-world derivative claim")
    history = fit["history"]
    if [row["step"] for row in history] != list(range(31)):
        raise ValueError("expected actual 30-step fit history including initial state")
    if any(not math.isfinite(row["conditional_soft_loss"]) for row in history):
        raise ValueError("non-finite conditional loss")
    if history[0]["conditional_soft_loss"] != audit["relaxation"]["first_conditional_soft_loss"] or history[-1]["conditional_soft_loss"] != audit["relaxation"]["last_conditional_soft_loss"]:
        raise ValueError("fit endpoints differ from independent audit")
    if len(payload["systems"]) != 2 or len(audit["rows"]) != 2:
        raise ValueError("expected initial and fitted native executions")
    losses = []
    for system, row in zip(payload["systems"], audit["rows"]):
        spec_bytes = system["system_spec_json"].encode("utf8")
        if hashlib.sha256(spec_bytes).hexdigest() != system["system_fingerprint"] or system["system_fingerprint"] != row["difference"]["candidate_fingerprint"]:
            raise ValueError("system fingerprint mismatch")
        if system["status"] != "complete" or row["status"] != "complete" or system["native_loss"] != row["loss"]:
            raise ValueError("native completion/loss mismatch")
        observed = -sum(run["counts"]["native.accepted_decisions"] for run in row["runs"]) / len(row["runs"])
        if observed != row["loss"]:
            raise ValueError("native count and audited loss disagree")
        losses.append(row["loss"])
    fitted_spec = json.loads(payload["systems"][1]["system_spec_json"])
    for node_id, parameters in history[-1]["parameters"].items():
        node = next(n for n in fitted_spec["mechanisms"] if n["mechanism_id"] == node_id)
        if node["parameters"]["program"]["parameters"] != parameters:
            raise ValueError("fitted parameters not installed in native candidate")
    return history, losses


def main() -> None:
    audit = json.loads(AUDIT.read_text())
    envelope = json.loads(ENVELOPE.read_text())
    history, losses = load_evidence(audit, envelope)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.7), gridspec_kw={"width_ratios": [1.35, 1]})
    left, right = axes
    left.plot([r["step"] for r in history], [r["conditional_soft_loss"] for r in history], color="#176B87", linewidth=2)
    left.scatter([0, 30], [history[0]["conditional_soft_loss"], history[-1]["conditional_soft_loss"]], color="#176B87", s=22, zorder=3)
    left.set(title="a  Conditional institution fit", xlabel="Adam update", ylabel="Negative soft accepted-count", xticks=[0, 10, 20, 30], ylim=(-3.3, .15))
    left.text(.96, .92, "Frozen native observations\n7 fitted coordinates", transform=left.transAxes, ha="right", va="top", fontsize=8, color="#426078")
    right.scatter([0, 1], losses, color=["#68778A", "#76529B"], s=65, zorder=3)
    for index, loss in enumerate(losses):
        right.annotate(f"{loss:g}", (index, loss), xytext=(8, 5), textcoords="offset points", fontweight="bold", color="#34445A")
    right.set(title="b  Actual native hard executions", ylabel="Negative accepted-decision count", xticks=[0, 1], xticklabels=["Initial system", "Fitted system"], xlim=(-.4, 1.5), ylim=(-3.4, .65))
    right.text(.5, .60, "Fresh world per system\nSame fixed Qwen3-8B", transform=right.transAxes, ha="center", va="top", fontsize=8, color="#6A547E")
    for ax in axes:
        ax.grid(axis="y", color="#E4E8EC", linewidth=.6)
        ax.set_axisbelow(True)
        ax.title.set_fontsize(9)
        ax.title.set_weight("bold")
    fig.tight_layout(w_pad=2.2)
    target = ROOT / "paper/figures/native-design-evidence"
    for suffix in (".pdf", ".png"):
        fig.savefig(target.with_suffix(suffix), dpi=220, bbox_inches="tight")
    plt.close(fig)
    manifest = {
        "schema": "scienceutopia.native-design-paper-figure.v1",
        "inputs": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (AUDIT, ENVELOPE)},
        "conditional_trace_sha256": audit["relaxation"]["trace_sha256"],
        "steps": 30,
        "native_losses": losses,
        "full_native_world_autograd": False,
        "outputs": {str(target.with_suffix(s).relative_to(ROOT)): hashlib.sha256(target.with_suffix(s).read_bytes()).hexdigest() for s in (".pdf", ".png")},
    }
    target.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
