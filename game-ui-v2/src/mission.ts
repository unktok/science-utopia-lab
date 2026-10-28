import { parseMissionBundle, verifyMissionBundle, type MissionArm, type MissionBundle, type MissionCandidate } from "./missionContract";
import "./style.css";
import "./mission.css";

const required = <T extends HTMLElement>(id: string): T => {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Missing #${id}`);
  return element as T;
};
const escapeHtml = (value: unknown): string => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
const formatUtc = (value: string): string => value.replace("T", " ").replace("+00:00", "Z");
const statusLabel = (value: string): string => value.replaceAll("_", " ").toUpperCase();

let bundle: MissionBundle;
let selectedArm = 0;
let selectedCandidate = 0;

function candidateAt(arm: MissionArm, index: number): MissionCandidate | undefined {
  return arm.candidates.find((candidate) => candidate.proposal_index === index);
}

function seedWindow(candidate: MissionCandidate, seedIndex: number): string {
  const seed = candidate.seeds[seedIndex]!;
  const mode = seed.execution_kind === "adopted" ? "A" : seed.execution_kind === "physical" ? "P" : "·";
  const label = `seed ${seed.seed}: ${statusLabel(seed.status)}, ${statusLabel(seed.execution_kind)}, attempt ${seed.attempt}/${seed.max_attempts}`;
  return `<span class="seed-window" data-status="${seed.status}" data-execution="${seed.execution_kind}" title="${escapeHtml(label)}"><i>${seed.seed}</i><b aria-hidden="true">${mode}</b><span class="sr-only">${escapeHtml(label)}</span></span>`;
}

function candidateTower(arm: MissionArm, armIndex: number, proposalIndex: number): string {
  const candidate = candidateAt(arm, proposalIndex);
  if (!candidate) return `<article class="candidate-tower candidate-tower--empty" aria-label="Candidate ${proposalIndex + 1}: not proposed"><div class="tower-roof">C${proposalIndex + 1}</div><div class="empty-lab">NOT<br/>PROPOSED</div><small>adaptive slot</small></article>`;
  const selected = armIndex === selectedArm && proposalIndex === selectedCandidate;
  return `<button class="candidate-tower" type="button" data-arm="${armIndex}" data-candidate="${proposalIndex}" data-status="${candidate.status}" aria-pressed="${selected}" aria-label="Candidate ${proposalIndex + 1}, design ${escapeHtml(candidate.design_id)}, ${statusLabel(candidate.status)}">
    <span class="tower-roof">C${proposalIndex + 1}<i>${statusLabel(candidate.phase)}</i></span>
    <span class="tower-core"><img src="/assets/noctiluca/production/institution-lab.svg" alt="" width="58" height="48"/><b>${escapeHtml(candidate.design_id.slice(0, 7))}</b></span>
    <span class="seed-windows">${candidate.seeds.map((_, index) => seedWindow(candidate, index)).join("")}</span>
    <span class="tower-status">${statusLabel(candidate.status)}</span>
  </button>`;
}

function renderArms(): void {
  required("arm-grid").innerHTML = bundle.arms.map((arm, armIndex) => `
    <article class="arm-lane" data-arm-index="${armIndex}" data-selected="${armIndex === selectedArm}">
      <header><span>ARM ${String.fromCharCode(65 + armIndex)}</span><button type="button" data-select-arm="${armIndex}" aria-pressed="${armIndex === selectedArm}"><b>${escapeHtml(arm.loss_spec.label)}</b><small>${arm.budget.used}/${arm.budget.maximum} candidates proposed</small></button><i>WINNER: NOT FROZEN</i></header>
      <div class="candidate-rail" aria-label="${escapeHtml(arm.loss_spec.label)} candidates">${Array.from({ length: arm.budget.maximum }, (_, index) => candidateTower(arm, armIndex, index)).join("")}</div>
      <footer><code>${escapeHtml(arm.loss_spec.id)}</code><span>minimize · 3 development seeds</span></footer>
    </article>`).join("");
  document.querySelectorAll<HTMLButtonElement>("[data-select-arm]").forEach((button) => button.addEventListener("click", () => select(Number(button.dataset.selectArm), 0)));
  document.querySelectorAll<HTMLButtonElement>("[data-candidate]").forEach((button) => button.addEventListener("click", () => select(Number(button.dataset.arm), Number(button.dataset.candidate))));
}

function renderInspector(): void {
  const arm = bundle.arms[selectedArm]!;
  const candidate = candidateAt(arm, selectedCandidate) ?? arm.candidates[0];
  required("selected-arm-title").textContent = `ARM ${String.fromCharCode(65 + selectedArm)} // ${arm.loss_spec.label}`;
  required("selected-arm-interpretation").textContent = arm.loss_spec.interpretation;
  const panel = required("selected-candidate");
  if (!candidate) {
    panel.innerHTML = "<div><dt>CANDIDATE</dt><dd>Not proposed</dd></div>";
    return;
  }
  const wall = candidate.seeds.reduce((sum, seed) => sum + (seed.wall_seconds ?? 0), 0);
  panel.innerHTML = `<div><dt>SELECTED</dt><dd>C${candidate.proposal_index + 1} · <code>${escapeHtml(candidate.design_id)}</code></dd></div><div><dt>STATE</dt><dd data-status="${candidate.status}">${statusLabel(candidate.status)}</dd></div><div><dt>SEEDS</dt><dd>${candidate.seeds.map((seed) => `${seed.seed}:${seed.status}`).join(" · ")}</dd></div><div><dt>OBSERVED WALL</dt><dd>${wall ? `${wall.toFixed(1)} s` : "not recorded"}</dd></div><div><dt>WINNER</dt><dd>NOT FROZEN — no inference</dd></div>`;
}

function select(armIndex: number, candidateIndex: number): void {
  selectedArm = Math.max(0, Math.min(bundle.arms.length - 1, armIndex));
  selectedCandidate = Math.max(0, Math.min(bundle.arms[selectedArm]!.budget.maximum - 1, candidateIndex));
  renderArms();
  renderInspector();
}

function render(): void {
  const synthetic = bundle.truth_status === "synthetic";
  required("mission-app").dataset.source = synthetic ? "synthetic" : "verified";
  required("truth-badge").textContent = synthetic ? "SYNTHETIC UI FIXTURE" : "VERIFIED READ-ONLY SNAPSHOT";
  required("mission-disclosure").textContent = bundle.disclosure;
  required("study-id").textContent = `${bundle.study.id} · v${bundle.study.version}`;
  required("runtime-id").textContent = `${bundle.runtime.model} · ${bundle.runtime.workers} worker`;
  required("snapshot-time").textContent = formatUtc(bundle.observed_at_utc);
  required("mission-goal").textContent = bundle.study.goal;
  required("logical-count").textContent = `${bundle.progress.logical_registered} / ${bundle.progress.logical_capacity}`;
  required<HTMLElement>("logical-fill").style.width = `${100 * bundle.progress.logical_registered / bundle.progress.logical_capacity}%`;
  required("logical-detail").textContent = `${bundle.progress.status_counts.complete} complete · ${bundle.progress.status_counts.running} running · ${bundle.progress.status_counts.planned} planned · ${bundle.progress.status_counts.failed} failed`;
  required("workflow").innerHTML = bundle.workflow.map((stage, index) => `<article data-status="${stage.status}"><span>0${index + 1}</span><b>${escapeHtml(stage.label)}</b><small>${statusLabel(stage.status)}</small></article>`).join("");
  required("freeze-status").textContent = `${bundle.winner_freeze.frozen_arms} / ${bundle.winner_freeze.required_arms} FROZEN`;
  required("heldout-seeds").innerHTML = bundle.held_out.seeds.map((seed) => `<span>🔒 ${seed}</span>`).join("");
  required("heldout-reason").textContent = bundle.held_out.reason;
  required("physical-complete").textContent = String(bundle.progress.execution_counts.physical_complete);
  required("physical-running").textContent = String(bundle.progress.execution_counts.physical_running);
  required("adopted-complete").textContent = String(bundle.progress.execution_counts.adopted_complete);
  required("source-commit").textContent = bundle.provenance.source_commit;
  required("snapshot-hash").textContent = bundle.snapshot_hash;
  required("registry-hash").textContent = bundle.provenance.registry_projection_sha256;
  renderArms();
  renderInspector();
  const verification = required("mission-verification");
  verification.dataset.state = "verified";
  verification.textContent = synthetic ? "SYNTHETIC CONTRACT VERIFIED" : "SNAPSHOT HASH VERIFIED";
}

async function boot(): Promise<void> {
  try {
    const synthetic = new URLSearchParams(location.search).get("source") === "synthetic";
    const response = await fetch(synthetic ? "/data/optimization-mission.synthetic.json" : "/data/optimization-mission.snapshot.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Mission snapshot returned HTTP ${response.status}`);
    bundle = parseMissionBundle(await response.json());
    await verifyMissionBundle(bundle);
    render();
  } catch (error) {
    const panel = required("mission-error");
    panel.hidden = false;
    panel.querySelector("span")!.textContent = error instanceof Error ? error.message : String(error);
    const verification = required("mission-verification");
    verification.dataset.state = "error";
    verification.textContent = "SNAPSHOT REJECTED";
  }
}

window.addEventListener("keydown", (event) => {
  if (!bundle || event.target instanceof HTMLInputElement || event.target instanceof HTMLButtonElement || event.target instanceof HTMLSelectElement) return;
  if (["1", "2", "3"].includes(event.key)) select(Number(event.key) - 1, 0);
  if (event.key === "ArrowRight") select(selectedArm, selectedCandidate + 1);
  if (event.key === "ArrowLeft") select(selectedArm, selectedCandidate - 1);
});

void boot();
