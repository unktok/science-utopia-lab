import {
  activateMissionContract, activeMission, emptyMissionBook, linkMissionJob, missionMatchesDraft,
  missionProgress, observeMissionJob, parseMissionBook,
  type MissionDraft, type MissionJobLink, type MissionObservation,
} from "./nativeMission";

const STORAGE_KEY = "noctiluca.native-sandbox-missions.v1";
const el = <T extends HTMLElement>(id: string): T => { const node = document.getElementById(id); if (!node) throw new Error(`Missing mission element ${id}`); return node as T; };
const escape = (value: unknown): string => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");

export type NativeMissionController = {
  canSubmit(): { ok: boolean; reason: string };
  linkJob(job: { job_id: string; request_sha256: string }): void;
  observeFailure(job: any): void;
  observeEvidence(job: any): void;
  refresh(): void;
};

export function initializeNativeMission(loss: HTMLTextAreaElement, onDraftChanged: () => void): NativeMissionController {
  const target = el<HTMLInputElement>("mission-target"), limit = el<HTMLInputElement>("mission-limit"), activate = el<HTMLButtonElement>("mission-activate");
  let book = emptyMissionBook(), storageError = "";
  try { const saved = localStorage.getItem(STORAGE_KEY); if (saved) book = parseMissionBook(JSON.parse(saved)); } catch (error) { storageError = `Mission storage ignored: ${String(error)}`; }
  const save = (): void => { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(book)); } catch (error) { storageError = `Mission storage unavailable: ${String(error)}`; } };
  const draft = (): MissionDraft => ({ loss_spec: JSON.parse(loss.value), target_loss: Number(target.value), trial_limit: Number(limit.value) });
  const matches = (): boolean => { try { return missionMatchesDraft(book, draft()); } catch { return false; } };
  const active = (): ReturnType<typeof activeMission> => activeMission(book);

  const render = (): void => {
    const record = active(), panel = el("mission-active"), status = el("mission-draft-status");
    panel.hidden = !record;
    if (!record) { status.className = "mission-draft-status"; status.textContent = storageError || "No design contract locked. Validation may inspect a design, but submission remains unavailable."; return; }
    const progress = missionProgress(book, record.contract.contract_id), aligned = matches();
    status.className = `mission-draft-status ${aligned ? "aligned" : "changed"}`;
    status.textContent = storageError || (aligned ? "CONTRACT LOCKED / Edit a system, validate it, authorize one run, then load completed evidence." : "DRAFT CHANGED / Lock a new contract before another trial. Prior scores remain under their original target.");
    el("mission-contract-id").textContent = record.contract.contract_id;
    el("mission-objective").textContent = `${record.contract.direction.toUpperCase()} ${record.contract.loss_id} → ${record.contract.target_loss}`;
    el("mission-best").textContent = progress.best_loss === null ? "NOT OBSERVED" : String(progress.best_loss);
    el("mission-trials").textContent = `${progress.attempted} / ${record.contract.trial_limit}`;
    el("mission-state").textContent = progress.target_achieved ? "GAME TARGET REACHED" : progress.remaining === 0 ? "TRIAL LIMIT REACHED" : progress.observed ? "CONTINUE DESIGNING" : "AWAITING EVIDENCE";
    el("mission-state").className = progress.target_achieved ? "reached" : "";
    el("mission-pips").innerHTML = Array.from({ length: record.contract.trial_limit }, (_, index) => {
      const link = book.jobs.filter(row => row.contract_id === record.contract.contract_id)[index], observation = link && record.observations.find(row => row.job_id === link.job_id);
      const state = observation?.status === "complete" ? "observed" : observation?.status === "failed" ? "failed" : link ? "submitted" : "open";
      return `<span class="mission-pip ${state}" title="Trial ${index + 1}: ${state}">${String(index + 1).padStart(2, "0")}</span>`;
    }).join("");
    const links = book.jobs.filter(row => row.contract_id === record.contract.contract_id);
    el("mission-history").innerHTML = links.length ? links.map((link, index) => {
      const observation = record.observations.find(row => row.job_id === link.job_id);
      const result = !observation ? "SUBMITTED / NO EVIDENCE LOADED" : observation.status === "failed" ? "TECHNICAL FAILURE / NO SCORE" : `ACTUAL LOSS ${observation.native_loss}`;
      return `<article class="mission-run ${observation?.status || "pending"}"><span>${String(index + 1).padStart(2, "0")}</span><div><b>${escape(result)}</b><code>${escape(link.job_id)}</code></div><small>${observation ? `SEED ${observation.seed} / ${observation.years} YEARS / SOURCE ${escape(observation.source_commit.slice(0, 12))}` : `REQUEST ${escape(link.request_sha256.slice(0, 12))}`}</small></article>`;
    }).join("") : "<p>NO SUBMITTED TRIALS. NOTHING IS INFERRED FROM THE EDITOR.</p>";
    const archives = book.contracts.filter(row => row.contract.contract_id !== record.contract.contract_id);
    el("mission-archive-count").textContent = String(archives.length);
    el("mission-archives").innerHTML = archives.length ? archives.map(row => { const value = missionProgress(book, row.contract.contract_id); return `<article><code>${escape(row.contract.contract_id)}</code><span>${escape(row.contract.loss_id)} / TARGET ${row.contract.target_loss}</span><span>${value.attempted} TRIALS / BEST ${value.best_loss ?? "NOT OBSERVED"}</span></article>`; }).join("") : "<p>NO PRIOR CONTRACTS</p>";
  };

  const canSubmit = (): { ok: boolean; reason: string } => {
    const record = active();
    if (!record) return { ok: false, reason: "Lock a sandbox mission contract first" };
    if (!matches()) return { ok: false, reason: "LossSpec, target or limit differs from the active contract" };
    const progress = missionProgress(book, record.contract.contract_id);
    if (progress.remaining < 1) return { ok: false, reason: "Mission trial limit reached" };
    return { ok: true, reason: "Mission contract permits one explicitly authorized trial" };
  };

  const terminal = (job: any, status: "complete" | "failed", evidenceLoaded: boolean): MissionObservation => ({
    job_id: String(job.job_id), request_sha256: String(job.request_sha256), status,
    native_loss: status === "complete" ? Number(job.result?.native_loss) : null,
    seed: Number(job.seed), years: Number(job.years), source_commit: String(job.source_commit), evidence_loaded: evidenceLoaded,
  });
  const observe = (job: any, status: "complete" | "failed", evidenceLoaded: boolean): void => {
    if (!book.jobs.some(row => row.job_id === String(job.job_id))) return;
    book = observeMissionJob(book, terminal(job, status, evidenceLoaded)); save(); render();
  };

  activate.addEventListener("click", () => { try { book = activateMissionContract(book, draft()); storageError = ""; save(); render(); onDraftChanged(); } catch (error) { storageError = String(error); render(); } });
  for (const control of [target, limit]) control.addEventListener("input", () => { render(); onDraftChanged(); });
  loss.addEventListener("input", render);
  render();
  return {
    canSubmit,
    linkJob(job): void { const record = active(); if (!record || !matches()) throw new Error("Lock the current LossSpec and target as a mission contract first"); const link: MissionJobLink = { ...job, contract_id: record.contract.contract_id }; book = linkMissionJob(book, link); save(); render(); },
    observeFailure(job): void { observe(job, "failed", false); },
    observeEvidence(job): void { observe(job, "complete", true); },
    refresh: render,
  };
}
