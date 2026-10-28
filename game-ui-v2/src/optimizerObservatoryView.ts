import { buildOptimizerObservatoryProjection, type OptimizerObservatoryProjection } from "./optimizerObservatory";
import { parseMissionBundle, verifyMissionBundle, type MissionBundle } from "./missionContract";

const required = <T extends HTMLElement>(id: string): T => {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Missing #${id}`);
  return node as T;
};
const escapeHtml = (value: unknown): string => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
const label = (value: string): string => value.replaceAll("_", " ").toUpperCase();

export function installOptimizerObservatory(): void {
  const panel = required<HTMLElement>("optimizer-observatory");
  const toggle = required<HTMLButtonElement>("observatory-toggle");
  const close = required<HTMLButtonElement>("observatory-close");
  const params = new URLSearchParams(location.search);
  const requested = params.get("observatory");
  const synthetic = requested === "synthetic";
  let open = requested === "on" || synthetic;
  let selectedArm = Math.max(0, Math.min(2, Number(params.get("loss") ?? "1") - 1));
  let selectedDesign = 0;
  let bundle: MissionBundle | undefined;
  let projection: OptimizerObservatoryProjection | undefined;

  const setOpen = (value: boolean): void => {
    open = value;
    panel.hidden = !value;
    toggle.setAttribute("aria-pressed", String(value));
    toggle.textContent = `OBSERVATORY: ${value ? "ON" : "OFF"}`;
    if (value) close.focus();
  };
  const render = (): void => {
    if (!projection || !bundle) return;
    panel.dataset.source = projection.truth_status === "synthetic" ? "synthetic" : "verified";
    required("observatory-truth").textContent = projection.truth_status === "synthetic" ? "SYNTHETIC DEMO FIXTURE" : "VERIFIED SNAPSHOT · READ ONLY";
    required("observatory-observed").textContent = `${projection.observed_at_utc.replace("T", " ").replace("+00:00", "Z")} · ${projection.provenance.source_commit.slice(0, 12)}`;
    required("observatory-arm-tabs").innerHTML = projection.arms.map((arm, index) => `<button type="button" data-observatory-arm="${index}" aria-pressed="${index === selectedArm}"><small>LOSSSPEC ${index + 1}</small><strong>${escapeHtml(arm.loss_label)}</strong></button>`).join("");
    const arm = projection.arms[selectedArm]!;
    const design = arm.designs[selectedDesign] ?? arm.designs[0];
    if (!design) return;
    selectedDesign = design.proposal_index;
    required("observatory-metric").innerHTML = `<span>CONDITIONING TARGET</span><strong>${escapeHtml(arm.loss_label)}</strong><code>${escapeHtml(arm.loss_spec_id)}</code><p>${escapeHtml(arm.interpretation)}</p>`;
    required("observatory-designs").innerHTML = Array.from({ length: bundle.arms[selectedArm]!.budget.maximum }, (_, index) => {
      const candidate = arm.designs.find((item) => item.proposal_index === index);
      if (!candidate) return `<span class="observatory-design observatory-design--empty"><b>C${index + 1}</b><small>NOT PROPOSED</small></span>`;
      return `<button class="observatory-design" type="button" data-observatory-design="${index}" data-status="${candidate.status}" aria-pressed="${candidate.proposal_index === selectedDesign}"><b>C${index + 1}</b><strong>${escapeHtml(candidate.design_id)}</strong><small>${label(candidate.status)}</small></button>`;
    }).join("");
    required("observatory-seeds").innerHTML = design.seeds.map((seed) => `<article class="observatory-seed" data-status="${seed.status}"><span>SEED ${seed.seed}</span><b>${label(seed.status)}</b><small>${label(seed.execution_kind)}</small><em>SCORE · NOT OBSERVED</em></article>`).join("");
    required("observatory-score").innerHTML = `<span>SCORE ARRAY</span><strong>NOT OBSERVED</strong><small>${escapeHtml(projection.score_export.note)}</small>`;
    required("observatory-winner").innerHTML = `<span>WINNER FREEZE</span><strong>NOT FROZEN</strong><small>${projection.winner_freeze.frozen_arms}/${projection.winner_freeze.required_arms} arms · no inferred winner</small>`;
    required("observatory-relation").innerHTML = `<strong>LOSSSPEC <i>CHOSES WHAT TO MINIMIZE</i> → SYSTEM DESIGN <i>IS THE OPTIMIZED VARIABLE</i></strong><span data-status="${projection.metric_conditioning.registered_cross_arm_divergence}">${escapeHtml(projection.metric_conditioning.note)}</span>`;
    required("observatory-report").textContent = `REPORT ${label(projection.report.status)} · ${projection.report.note}`;
    required("observatory-provenance").innerHTML = `<div><dt>SNAPSHOT SHA</dt><dd><code>${escapeHtml(projection.provenance.snapshot_hash)}</code></dd></div><div><dt>REGISTRY SHA</dt><dd><code>${escapeHtml(projection.provenance.registry_projection_sha256)}</code></dd></div><div><dt>STUDY SPEC SHA</dt><dd><code>${escapeHtml(projection.provenance.study_spec_sha256)}</code></dd></div><div><dt>SOURCE FILES</dt><dd>${projection.provenance.source_files.length} hashed inputs</dd></div>`;
    required("observatory-arm-tabs").querySelectorAll<HTMLButtonElement>("[data-observatory-arm]").forEach((button) => button.addEventListener("click", () => {
      selectedArm = Number(button.dataset.observatoryArm);
      selectedDesign = 0;
      render();
    }));
    required("observatory-designs").querySelectorAll<HTMLButtonElement>("[data-observatory-design]").forEach((button) => button.addEventListener("click", () => {
      selectedDesign = Number(button.dataset.observatoryDesign);
      render();
    }));
  };
  const load = async (): Promise<void> => {
    try {
      const response = await fetch(synthetic ? "/data/optimization-mission.synthetic.json" : "/data/optimization-mission.snapshot.json", { cache: "no-store" });
      if (!response.ok) throw new Error(`Optimizer snapshot returned HTTP ${response.status}`);
      bundle = parseMissionBundle(await response.json());
      await verifyMissionBundle(bundle);
      projection = buildOptimizerObservatoryProjection(bundle);
      render();
      required("observatory-loading").hidden = true;
    } catch (error) {
      required("observatory-loading").textContent = `OBSERVATORY FAIL-CLOSED · ${error instanceof Error ? error.message : String(error)}`;
      toggle.disabled = true;
    }
  };
  toggle.addEventListener("click", () => setOpen(!open));
  close.addEventListener("click", () => { setOpen(false); toggle.focus(); });
  window.addEventListener("keydown", (event) => {
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement) return;
    if ((event.key === "o" || event.key === "O") && !event.metaKey && !event.ctrlKey) { event.preventDefault(); event.stopImmediatePropagation(); setOpen(!open); }
    if (!open) return;
    if (event.key === "Escape") { event.preventDefault(); event.stopImmediatePropagation(); setOpen(false); toggle.focus(); }
    if (["1", "2", "3"].includes(event.key)) { event.preventDefault(); event.stopImmediatePropagation(); selectedArm = Number(event.key) - 1; selectedDesign = 0; render(); }
    if (event.key === "ArrowRight" || event.key === "ArrowLeft") { event.preventDefault(); event.stopImmediatePropagation(); selectedDesign = Math.max(0, Math.min((projection?.arms[selectedArm]?.designs.length ?? 1) - 1, selectedDesign + (event.key === "ArrowRight" ? 1 : -1))); render(); }
  }, { capture: true });
  setOpen(open);
  void load();
}
