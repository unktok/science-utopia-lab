// Browser edits are data. Only the separate, commit-pinned worker executes jobs.
const item = <T extends HTMLElement>(id: string): T => {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Missing design workbench element ${id}`);
  return node as T;
};
export const nativeEngineeringLoss = {
  schema: "scienceutopia.loss-spec.v1", id: "native-accepted-count-engineering-v1", version: "1",
  status: "engineering-only-not-scientific-value", optimization_seed_role: "development", direction: "minimize",
  per_run: { intercept: 0, terms: [{ metric_id: "native.accepted_decisions", slice_id: null, coefficient: -1 }] },
  across_seeds: { aggregation: "mean_plus_population_sd", dispersion_weight: 0, minimum_valid_runs: 1 },
  interpretation: "Gameable engineering objective, not scientific quality. All-accept is legal. No implicit policy veto.",
};

export function designRequest(parent: unknown, systemText: string, lossText: string, seed: number, years: number): Record<string, unknown> {
  if (!Number.isInteger(seed) || !Number.isInteger(years)) throw new Error("Integer seed and horizon required");
  const system: unknown = JSON.parse(systemText), loss: unknown = JSON.parse(lossText);
  if (!system || typeof system !== "object" || Array.isArray(system) || !loss || typeof loss !== "object" || Array.isArray(loss)) throw new Error("System and loss must be JSON objects");
  return { parent_system: parent, system, loss_spec: loss, seed, years };
}

export function initializeNativeJobs(selectedSystem: () => unknown, loadEvidence: (value: unknown) => Promise<void>): void {
  const panel = item<HTMLDetailsElement>("design-console"), system = item<HTMLTextAreaElement>("design-system"), loss = item<HTMLTextAreaElement>("design-loss");
  const validate = item<HTMLButtonElement>("design-validate"), submit = item<HTMLButtonElement>("design-submit"), result = item<HTMLButtonElement>("design-result"), consent = item<HTMLInputElement>("design-consent");
  let parent: unknown, token = "", validated = "", jobId = "", initialized = false, timer: number | undefined;
  const request = (): Record<string, unknown> => designRequest(parent, system.value, loss.value, Number(item<HTMLInputElement>("design-seed").value), Number(item<HTMLInputElement>("design-years").value));
  const error = (value: unknown): void => { item("design-job-error").hidden = false; item("design-job-error").textContent = String(value); };
  const changed = (): void => { validated = ""; submit.disabled = true; item("design-validation").textContent = "Edited design needs validation. No experiment submitted."; };
  const copy = (): void => {
    try { parent = selectedSystem(); system.value = JSON.stringify(parent, null, 2); loss.value = JSON.stringify(nativeEngineeringLoss, null, 2); item("design-parent").textContent = "Parent captured from the selected system. Edit source, nodes, ports, wiring, schedules or parameters below."; changed(); } catch (failure) { error(failure); }
  };
  const api = async (path: string, body?: unknown): Promise<any> => {
    const response = await fetch(`/native-api/${path}`, { method: body === undefined ? "GET" : "POST", headers: { "X-Native-Lab-Token": token, ...(body === undefined ? {} : { "Content-Type": "application/json" }) }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    if (!response.ok) { const message = await response.text(); throw new Error(`Local service ${response.status}: ${message.slice(0, 500)}`); }
    return response.json();
  };
  const poll = async (): Promise<void> => {
    if (!jobId) return;
    try {
      const job = await api(`jobs/${jobId}`);
      item("design-job-status").textContent = job.status === "complete" ? `COMPLETE / ACTUAL NATIVE LOSS ${job.result.native_loss}` : job.status === "failed" ? "TECHNICAL FAILURE / NO LOSS ASSIGNED" : `${String(job.status).toUpperCase()} / SAVED YEAR ${job.checkpoint_year ?? 0} OF ${job.years} / NO MEASURED RESULT YET`;
      item("design-job-id").textContent = jobId;
      item("design-job-provenance").textContent = `RUN SOURCE ${String(job.source_commit).slice(0, 12)} / DEVELOPMENT SEED ${job.seed} / ${job.years} YEARS / LOSS ${job.loss_id ?? "recorded request"}`;
      result.disabled = job.status !== "complete";
      if (job.error) error(job.error);
      if (job.status === "queued" || job.status === "running") timer = window.setTimeout(() => { void poll(); }, 2000);
    } catch (failure) { error(failure); }
  };
  panel.addEventListener("toggle", () => {
    if (!panel.open || initialized) return;
    initialized = true; copy();
    void api("session").then(session => {
      token = session.token; validate.disabled = false;
      item("design-service").textContent = `LOCAL QUEUE / SOURCE ${String(session.source_commit).slice(0, 12)}`;
      try { jobId = sessionStorage.getItem("native-lab-job") || ""; } catch { /* no storage required */ }
      if (jobId) void poll();
    }).catch(() => { item("design-service").textContent = "OFFLINE / START serve_native_lab.py TO SUBMIT"; });
  });
  item("design-reset").addEventListener("click", copy);
  for (const control of [system, loss, item("design-seed"), item("design-years")]) control.addEventListener("input", changed);
  consent.addEventListener("change", () => { submit.disabled = !validated || !consent.checked; });
  validate.addEventListener("click", () => {
    void (async () => { try {
      item("design-job-error").hidden = true;
      const body = request(), checked = await api("validate", body);
      validated = JSON.stringify(body); submit.disabled = !consent.checked;
      item("design-validation").textContent = `STRUCTURALLY VALID / ${String(checked.candidate_fingerprint).slice(0, 16)} / NOT EXECUTED`;
    } catch (failure) { changed(); error(failure); } })();
  });
  submit.addEventListener("click", () => {
    void (async () => { try {
      const body = request();
      if (!consent.checked || validated !== JSON.stringify(body)) throw new Error("Validate the exact edited design and explicitly authorize its execution first");
      submit.disabled = true; validated = ""; consent.checked = false;
      const job = await api("jobs", body); jobId = job.job_id;
      try { sessionStorage.setItem("native-lab-job", jobId); } catch { /* no storage required */ }
      if (timer !== undefined) clearTimeout(timer);
      await poll();
    } catch (failure) { error(failure); } })();
  });
  result.addEventListener("click", () => { void (async () => { try { await loadEvidence(await api(`jobs/${jobId}/evidence`)); item("design-validation").textContent = "Loaded completed native evidence. Original run was not modified."; } catch (failure) { error(failure); } })(); });
}
