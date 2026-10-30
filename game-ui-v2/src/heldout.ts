import { installArcologyRail } from "./arcologyNav";
import { joinHeldoutOps, parseFrozenSystemGrid, parseHeldoutProgressSnapshot, verifyFrozenSystemGrid, verifyHeldoutProgressSnapshot, type HeldoutOpsBundle, type HeldoutRun } from "./heldoutContract";
import "./style.css";
import "./heldout.css";

installArcologyRail("heldout");

const required = <T extends HTMLElement>(id: string): T => {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Missing #${id}`);
  return element as T;
};
const escapeHtml = (value: unknown): string => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
const label = (value: string): string => value.replaceAll("_", " ").toUpperCase();
const duration = (seconds: number | null): string => {
  if (seconds === null) return "—";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours ? `${hours}h ${String(minutes).padStart(2, "0")}m` : `${minutes}m`;
};

let bundle: HeldoutOpsBundle;
let selectedSystem = 0;

function runCell(run: HeldoutRun, active: boolean): string {
  const wall = run.status === "running" ? run.elapsed_seconds : run.wall_seconds;
  const copy = `seed ${run.seed}: ${label(run.status)}${wall === null ? "" : `, ${duration(wall)}`}`;
  return `<li data-status="${run.status}" data-current="${active}"><span class="seed-pod"><i></i><b>${run.seed}</b></span><strong>${label(run.status)}</strong><small>${wall === null ? (run.status === "planned" ? "queued" : "no wall time") : duration(wall)}</small><span class="sr-only">${escapeHtml(copy)}</span></li>`;
}

function renderSystems(): void {
  required("system-grid").innerHTML = bundle.grid.systems.map((system, index) => {
    const complete = system.runs.filter((run) => run.status === "complete").length;
    const terminal = complete + system.runs.filter((run) => run.status === "technical_failed").length;
    const activeRunIds = new Set(bundle.progress.progress.active_runs.map((run) => run.run_id));
    return `<article class="system-habitat" data-system="${index}" data-selected="${index === selectedSystem}">
      <header><span>FROZEN SYSTEM 0${index + 1}</span><b>${escapeHtml(system.label)}</b><small>${escapeHtml(system.loss_condition)}</small></header>
      <div class="habitat-world" aria-hidden="true">
        <span class="habitat-beacon"></span><img src="${escapeHtml(system.asset)}" alt="" />
        <span class="pixel-operator pixel-operator--a"></span><span class="pixel-operator pixel-operator--b"></span>
        <span class="data-cable"></span><span class="system-seal">SEALED</span>
      </div>
      <div class="system-identity"><span>DESIGN FINGERPRINT</span><code>${escapeHtml(system.design_fingerprint.slice(0, 16))}…</code></div>
      <ol class="seed-rail" aria-label="${escapeHtml(system.label)} held-out seed states">${system.runs.map((run) => runCell(run, activeRunIds.has(run.run_id))).join("")}</ol>
      <footer><span>${terminal} / 5 terminal</span><i><b style="width:${100 * terminal / 5}%"></b></i><button type="button" data-select-system="${index}" aria-pressed="${index === selectedSystem}">INSPECT SYSTEM</button></footer>
    </article>`;
  }).join("");
  document.querySelectorAll<HTMLButtonElement>("[data-select-system]").forEach((button) => button.addEventListener("click", () => selectSystem(Number(button.dataset.selectSystem))));
}

function renderSelected(): void {
  const system = bundle.grid.systems[selectedSystem]!;
  required<HTMLImageElement>("selected-system-asset").src = system.asset;
  required("selected-system").innerHTML = `<div><dt>SYSTEM</dt><dd>${escapeHtml(system.label)}</dd></div><div><dt>CONDITIONING LOSS</dt><dd>${escapeHtml(system.loss_condition)}</dd></div><div><dt>LOSS SPEC ID</dt><dd><code>${escapeHtml(system.loss_spec_id)}</code></dd></div><div><dt>DESIGN</dt><dd><code>${escapeHtml(system.design_fingerprint)}</code></dd></div><div><dt>FREEZE</dt><dd>SEALED · <code>${escapeHtml(system.freeze_id.slice(0, 12))}…</code></dd></div><div><dt>RESULT</dt><dd>NOT EXPORTED</dd></div>`;
  required("system-tabs").innerHTML = bundle.grid.systems.map((item, index) => `<button type="button" data-system-tab="${index}" aria-pressed="${index === selectedSystem}">0${index + 1} ${escapeHtml(item.label)}</button>`).join("");
  document.querySelectorAll<HTMLButtonElement>("[data-system-tab]").forEach((button) => button.addEventListener("click", () => selectSystem(Number(button.dataset.systemTab))));
}

function selectSystem(index: number): void {
  selectedSystem = Math.max(0, Math.min(bundle.grid.systems.length - 1, index));
  renderSystems();
  renderSelected();
}

function render(): void {
  required("study-id").textContent = `${bundle.progress.study.id} · ${bundle.progress.study.revision}`;
  required("phase-id").textContent = "COMMON HELD-OUT EXECUTION";
  required("snapshot-time").textContent = bundle.progress.observed_at_utc.replace("T", " ").replace("+00:00", "Z");
  required("relay-disclosure").textContent = `${bundle.progress.disclosure} ${bundle.grid.disclosure}`;
  const active = bundle.progress.progress.active_runs[0];
  const currentSystem = bundle.grid.systems.find((system) => system.runs.some((run) => run.run_id === active?.run_id));
  const current = currentSystem?.runs.find((run) => run.run_id === active?.run_id);
  required("current-run").textContent = current && currentSystem ? `${currentSystem.label} // SEED ${current.seed}` : "NO RUN ACTIVE";
  required("elapsed").textContent = duration(current?.elapsed_seconds ?? null);
  required("eta").textContent = duration(bundle.progress.progress.eta?.remaining_seconds ?? null);
  const counts = bundle.progress.progress.counts;
  const terminal = counts.complete + bundle.progress.progress.terminal_failures;
  required("progress-count").textContent = `${terminal} / ${bundle.grid.study.total_runs}`;
  required<HTMLElement>("progress-fill").style.width = `${100 * terminal / bundle.grid.study.total_runs}%`;
  required<HTMLElement>("progress-runner").style.left = `${100 * Math.min(bundle.grid.study.total_runs, terminal + (counts.running ? .55 : 0)) / bundle.grid.study.total_runs}%`;
  required("complete-count").textContent = String(counts.complete);
  required("running-count").textContent = String(counts.running);
  required("planned-count").textContent = String(counts.planned);
  required("failed-count").textContent = String(counts.failed);
  required("failure-beacon").textContent = `${counts.failed} SIGNAL${counts.failed === 1 ? "" : "S"}`;
  required("failure-list").innerHTML = bundle.grid.technical_failures.length ? bundle.grid.technical_failures.map((failure) => `<li><code>${escapeHtml(failure.id)}</code><span>${escapeHtml(failure.category)} · seed ${failure.seed} · ${failure.retryable ? "retryable" : "terminal"}</span></li>`).join("") : `<li class="failure-empty">NO TECHNICAL FAILURES IN THIS FIXTURE SNAPSHOT</li>`;
  required("boundary-copy").textContent = bundle.grid.boundary.statement;
  required("snapshot-hash").textContent = `progress ${bundle.progress.snapshot_sha256.slice(0, 12)}… · grid ${bundle.grid.snapshot_sha256.slice(0, 12)}…`;
  renderSystems();
  renderSelected();
  const verification = required("relay-verification");
  verification.dataset.state = "verified";
  verification.textContent = "SYNTHETIC CONTRACT VERIFIED";
}

async function boot(): Promise<void> {
  try {
    const [progressResponse, gridResponse] = await Promise.all([
      fetch("/data/held-out-progress.synthetic.json", { cache: "no-store" }),
      fetch("/data/held-out-run-grid.synthetic.json", { cache: "no-store" }),
    ]);
    if (!progressResponse.ok || !gridResponse.ok) throw new Error(`Held-out snapshots returned HTTP ${progressResponse.status}/${gridResponse.status}`);
    const progress = parseHeldoutProgressSnapshot(await progressResponse.json());
    const grid = parseFrozenSystemGrid(await gridResponse.json());
    await Promise.all([verifyHeldoutProgressSnapshot(progress), verifyFrozenSystemGrid(grid)]);
    bundle = joinHeldoutOps(progress, grid);
    render();
  } catch (error) {
    const panel = required("relay-error");
    panel.hidden = false;
    panel.querySelector("span")!.textContent = error instanceof Error ? error.message : String(error);
    const verification = required("relay-verification");
    verification.dataset.state = "error";
    verification.textContent = "SNAPSHOT REJECTED";
  }
}

window.addEventListener("keydown", (event) => {
  if (!bundle || event.target instanceof HTMLButtonElement || event.target instanceof HTMLInputElement) return;
  if (["1", "2", "3"].includes(event.key)) selectSystem(Number(event.key) - 1);
});

void boot();
