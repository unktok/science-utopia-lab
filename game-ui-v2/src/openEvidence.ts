import { verifyNativeOpenEvidence, type NativeOpenEvidence, type OpenEvidenceObservation } from "./openEvidenceContract";
import "./openEvidence.css";

const el = <T extends Element = HTMLElement>(id: string): T => { const node = document.getElementById(id); if (!node) throw new Error(`Missing open-evidence element ${id}`); return node as unknown as T; };
const esc = (value: unknown): string => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const short = (value: unknown, size = 12): string => typeof value === "string" && value.length > size ? `${value.slice(0, size)}…` : String(value ?? "—");
const json = (value: unknown): string => JSON.stringify(value, null, 2);
const record = (value: unknown): Record<string, any> => value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, any> : {};
const list = (value: unknown): any[] => Array.isArray(value) ? value : [];
const eventPayload = (event: unknown): Record<string, any> => record(record(event).payload);

let evidence: NativeOpenEvidence;
let selectedIndex = 0;
let registrySelection: { kind: "actor" | "artifact"; id: string } | null = null;

function complete(row: OpenEvidenceObservation): boolean { return row.observation?.status === "complete"; }
function selected(): OpenEvidenceObservation { return evidence.observations[selectedIndex]!; }

function renderCampaign(): void {
  el("campaign-meta").textContent = `${evidence.status.toUpperCase()} // ${evidence.complete_native_worlds} COMPLETE WORLDS // ${evidence.physical_reply_count} PHYSICAL QWEN REPLIES`;
  el("campaign-rail").innerHTML = evidence.records.map((item, index) => {
    const request = record(item.request), report = item.report === null ? null : record(item.report);
    const observations = list(item.observations), valid = observations.filter((observation) => record(observation).status === "complete").length;
    return `<article><span class="generation-id">GEN ${String(index).padStart(2, "0")}</span><div class="version-line"><i></i><code>${esc(short(item.version_sha256, 18))}</code></div><h3>${esc(request.strategy_id ?? "UNBOUND STRATEGY")}</h3><p>${item.generation_error ? "VOCABULARY GENERATION FAILED" : `${list(item.draws).length} IID CONDITIONAL DRAWS / ${valid} COMPLETE`}</p><b data-status="${esc(report?.status ?? "pending")}">${esc(report?.status ?? "PENDING")}</b></article>`;
  }).join("");
  const current = evidence.records[Math.min(selected().generation, evidence.records.length - 1)] ?? {};
  const request = record(current.request), definition = record(current.definition), report = record(current.report), mixed = record(report.mixed);
  const before = record(report.strategy_before), after = record(report.strategy_after);
  const draw = selected().draw;
  el("strategy-panel").innerHTML = `<div><span>EVOLVING VOCABULARY</span><strong>${esc(short(current.version_sha256, 24))}</strong><p>${list(definition.factors).length} discrete factor declarations · ${list(definition.continuous).length} bounded continuous coordinates. A later generation may replace the vocabulary.</p></div><div><span>ACTUAL DRAW ${selectedIndex + 1}</span><strong>${esc(Object.entries(record(draw.assignment)).map(([key, value]) => `${key}=${value}`).join(" / ") || "IDENTITY ASSIGNMENT")}</strong><p>latent ${esc(json(draw.latent ?? []))}<br />operations ${list(draw.continuous_operations).length} · log q ${esc(draw.conditional_latent_log_probability ?? "—")}</p></div><div><span>STRATEGY UPDATE</span><strong>${esc(request.strategy_id ?? "—")}</strong><p>before ${esc(json(before.logits ?? []))}<br />after ${esc(json(after.logits ?? []))}<br />mixed ${esc(mixed.status ?? report.status ?? "—")}</p></div>`;
}

function statusLabel(row: OpenEvidenceObservation): string {
  if (row.observation === null) return "NULL / NO OBSERVATION";
  return row.observation.status === "complete" ? `LOSS ${row.observation.loss}` : `${String(row.observation.status).toUpperCase()} / LOSS NULL`;
}
function renderObservations(): void {
  el("observation-meta").textContent = `SELECTED ${String(selectedIndex + 1).padStart(2, "0")} / ${String(evidence.observations.length).padStart(2, "0")}`;
  el("observation-deck").innerHTML = evidence.observations.map((item, index) => `<button type="button" data-observation="${index}" data-complete="${complete(item)}" aria-pressed="${index === selectedIndex}"><span>G${item.generation} / DRAW ${index + 1}</span><strong>${esc(statusLabel(item))}</strong><small>${esc(item.strategy)}<br />${complete(item) ? `YEAR ${item.year} · CHECKPOINT ${short(item.checkpoint_sha256)}` : "NO COMPLETE ENDPOINT FIELDS"}</small></button>`).join("");
  el("observation-deck").querySelectorAll<HTMLButtonElement>("button").forEach((button) => button.addEventListener("click", () => { selectedIndex = Number(button.dataset.observation); registrySelection = null; renderSelected(); }));
}

function renderDomain(): void {
  const domain = record(selected().open_domain), actors = Object.entries(record(domain.actors)), artifacts = Object.entries(record(domain.artifacts));
  if (!complete(selected())) {
    el("actor-list").innerHTML = el("artifact-list").innerHTML = `<p class="empty">No completed checkpoint. The viewer does not fabricate a domain state.</p>`;
    el("registry-inspector").innerHTML = `<p class="empty">SELECT A COMPLETE OBSERVATION</p>`; return;
  }
  if (!registrySelection) registrySelection = actors[0] ? { kind: "actor", id: actors[0][0] } : artifacts[0] ? { kind: "artifact", id: artifacts[0][0] } : null;
  const registryButton = (kind: "actor" | "artifact", [id, raw]: [string, any]): string => { const item = record(raw); return `<button type="button" data-registry-kind="${kind}" data-registry-id="${esc(id)}" aria-pressed="${registrySelection?.kind === kind && registrySelection.id === id}"><i>${kind === "actor" ? "A" : "◇"}</i><span><b>${esc(id)}</b><small>${esc(item.type)} · REV ${esc(item.revision)}</small></span></button>`; };
  el("actor-list").innerHTML = actors.length ? actors.map((item) => registryButton("actor", item)).join("") : `<p class="empty">No custom participants recorded.</p>`;
  el("artifact-list").innerHTML = artifacts.length ? artifacts.map((item) => registryButton("artifact", item)).join("") : `<p class="empty">No custom artifacts recorded.</p>`;
  document.querySelectorAll<HTMLButtonElement>("[data-registry-kind]").forEach((button) => button.addEventListener("click", () => { registrySelection = { kind: button.dataset.registryKind as "actor" | "artifact", id: button.dataset.registryId! }; renderDomain(); }));
  const item = registrySelection ? record(record(domain[registrySelection.kind === "actor" ? "actors" : "artifacts"])[registrySelection.id]) : {};
  el("registry-inspector").innerHTML = registrySelection ? `<span>${registrySelection.kind.toUpperCase()} RECORD</span><h3>${esc(registrySelection.id)}</h3><dl><div><dt>TYPE</dt><dd>${esc(item.type)}</dd></div><div><dt>REVISION</dt><dd>${esc(item.revision)}</dd></div><div><dt>ACTIVE YEARS</dt><dd>${esc(item.created_year)} → ${esc(item.updated_year)}</dd></div>${registrySelection.kind === "actor" ? `<div><dt>ROLES</dt><dd>${esc(list(item.roles).join(" / ") || "none")}</dd></div>` : `<div><dt>OWNER</dt><dd>${esc(item.owner_actor)}</dd></div><div><dt>LINKS</dt><dd>${list(item.actor_ids).length} actors · ${list(item.artifact_ids).length} artifacts · ${list(item.native_paper_ids).length} native papers</dd></div>`}</dl><pre>${esc(json(registrySelection.kind === "actor" ? item.state : item.content))}</pre>` : `<p class="empty">Domain state is valid and empty.</p>`;
}

function renderProcesses(): void {
  const receipts = list(selected().process_receipts);
  el("process-loom").innerHTML = complete(selected()) && receipts.length ? receipts.map((event, index) => {
    const payload = eventPayload(event), type = String(record(event).event_type), skipped = type.endsWith("skipped");
    return `<article data-skipped="${skipped}"><div class="process-index">${String(index + 1).padStart(2, "0")}</div><div><span>${esc(type)}</span><h3>${skipped ? "EXPLICIT SKIP" : type.endsWith("iteration") ? `ITERATION ${esc(payload.iteration)}` : `${esc(payload.executed ?? 0)} / ${esc(payload.requested ?? "—")} EXECUTED`}</h3><p>year ${esc(payload.year ?? selected().year)} · limit ${esc(payload.limit ?? "—")} · enabled ${esc(payload.enabled ?? "—")}<br />delegate ${esc(short(payload.delegate_contract_sha256, 18))}</p></div></article>`;
  }).join("") : `<p class="empty">${complete(selected()) ? "No native.process.* receipts at this endpoint." : "No completed execution; process activity remains unknown."}</p>`;
}

function renderSystem(): void {
  const system = record(selected().system), nodes = list(system.mechanisms), connections = list(system.connections);
  el("system-fingerprint").textContent = complete(selected()) ? String(system.system_fingerprint ?? selected().boundary_coverage?.system_fingerprint ?? "—") : "NO COMPLETE SYSTEM";
  if (!complete(selected())) { el("system-graph").innerHTML = `<p class="empty">No system graph is attached to this incomplete row.</p>`; el("node-inspector").innerHTML = ""; return; }
  el("system-graph").innerHTML = `<div class="graph-nodes">${nodes.map((node, index) => { const n = record(node); return `<button type="button" data-node-index="${index}"><small>${esc(n.implementation)}</small><b>${esc(n.mechanism_id)}</b><span>${esc(n.family)} · ${list(n.inputs).length} IN / ${list(n.outputs).length} OUT</span></button>`; }).join("")}</div><div class="graph-edges"><h3>DECLARED ROUTES</h3>${connections.map((edge) => { const e = record(edge); return `<p><b>${esc(e.source_mechanism)}.${esc(e.source_port)}</b><i>→</i><b>${esc(e.target_mechanism)}.${esc(e.target_port)}</b><span>${esc(e.channel)} / t+${esc(e.latency)}</span></p>`; }).join("")}</div>`;
  const inspect = (index: number): void => { const node = record(nodes[index]); document.querySelectorAll("[data-node-index]").forEach((item) => item.setAttribute("aria-pressed", String(item.getAttribute("data-node-index") === String(index)))); el("node-inspector").innerHTML = `<span>NODE ${String(index + 1).padStart(2, "0")}</span><h3>${esc(node.mechanism_id)}</h3><p>${esc(node.family)} / ${esc(node.implementation)} / VERSION ${esc(node.version)}</p><h4>PORT CONTRACT</h4><pre>${esc(json({ inputs: node.inputs, outputs: node.outputs }))}</pre><h4>SOURCE + PARAMETERS</h4><pre>${esc(json(node.parameters))}</pre>`; };
  el("system-graph").querySelectorAll<HTMLButtonElement>("[data-node-index]").forEach((button) => button.addEventListener("click", () => inspect(Number(button.dataset.nodeIndex))));
  if (nodes.length) inspect(0);
}

function renderDerivative(): void {
  const coverage = record(selected().boundary_coverage), backward = record(selected().conditional_backward);
  if (!complete(selected())) { el("coverage-panel").innerHTML = el("backward-panel").innerHTML = `<p class="empty">No derivative evidence for an incomplete endpoint.</p>`; return; }
  const edges = list(coverage.edges), represented = edges.filter((edge) => record(edge).derivative_coverage === "represented-numeric-communication").length;
  el("coverage-panel").innerHTML = `<span>BOUNDARY COVERAGE</span><h3>${represented} / ${edges.length} ROUTES REPRESENTED NUMERIC</h3><dl><div><dt>TRACE FRAMES</dt><dd>${esc(coverage.trace_frames)}</dd></div><div><dt>VERIFIED TENSOR NODES</dt><dd>${list(coverage.verified_represented_mechanisms).length}</dd></div><div><dt>OPAQUE MECHANISMS</dt><dd>${list(coverage.opaque_mechanisms).length}</dd></div></dl><p>${esc(coverage.nonnumeric_records)}</p>`;
  el("backward-panel").innerHTML = `<span>CONDITIONAL BACKWARD</span><h3 data-status="${esc(backward.status)}">${esc(String(backward.status).toUpperCase())}</h3><dl><div><dt>SOFT LOSS</dt><dd>${esc(backward.conditional_soft_loss)}</dd></div><div><dt>NUMERICAL CHECKS</dt><dd>${list(backward.numerical_checks).length}</dd></div><div><dt>EPSILON</dt><dd>${esc(backward.finite_difference_epsilon)}</dd></div></dl><pre>${esc(json(backward.gradient))}</pre>`;
}

function renderSource(): void {
  const current = selected();
  el("source-details").innerHTML = `<div><dt>CONTENT SHA256</dt><dd>${esc(evidence.content_sha256)}</dd></div><div><dt>SOURCE COMMIT</dt><dd>${esc(evidence.source_commit)}</dd></div><div><dt>GENERATION / STRATEGY</dt><dd>${current.generation} / ${esc(current.strategy)}</dd></div><div><dt>CHECKPOINT SHA256</dt><dd>${esc(current.checkpoint_sha256 ?? "NOT AVAILABLE")}</dd></div><div><dt>WORLD BINDING</dt><dd><pre>${esc(json(evidence.world_binding))}</pre></dd></div><div><dt>CAMPAIGN BINDING</dt><dd><pre>${esc(json(evidence.campaign_binding))}</pre></dd></div>`;
  el("raw-observation").textContent = json(current);
}
function renderSelected(): void { renderCampaign(); renderObservations(); renderDomain(); renderProcesses(); renderSystem(); renderDerivative(); renderSource(); }
function renderAll(mode: "actual" | "fixture"): void {
  el("truth-badge").textContent = mode === "actual" ? "HASH-VERIFIED ACTUAL EVIDENCE" : "SYNTHETIC UI FIXTURE // NOT EXPERIMENT DATA";
  el("truth-badge").classList.toggle("fixture", mode === "fixture"); el("evidence").removeAttribute("hidden");
  el("hero-source-label").textContent = mode === "actual" ? "FRONTIER ARRAY / ACTUAL NATIVE EXECUTION" : "FRONTIER ARRAY / SYNTHETIC UI COMPONENT CHECK";
  el("footer-source").textContent = `${mode === "actual" ? "ACTUAL" : "FIXTURE"} // ${evidence.content_sha256}`; renderSelected();
}
async function start(): Promise<void> {
  const fixture = new URLSearchParams(location.search).get("fixture") === "open-v7";
  const mode = fixture ? "fixture" : "actual"; const path = fixture ? "./data/native-open-evidence.synthetic.json" : "./data/native-open-integrated-v7.json";
  try { const response = await fetch(path, { cache: "no-store" }); if (!response.ok) throw new Error(`HTTP ${response.status} for ${path}`); evidence = await verifyNativeOpenEvidence(await response.json(), mode); renderAll(mode); }
  catch (error) {
    if (!fixture) { el("truth-badge").textContent = "ACTUAL EVIDENCE UNAVAILABLE"; el("truth-badge").classList.add("unverified"); el("unavailable-message").textContent = String(error); el("unavailable").removeAttribute("hidden"); return; }
    el("fatal-error").textContent = `FIXTURE CONTRACT FAILURE // ${String(error)}`; el("fatal-error").removeAttribute("hidden");
  }
}
void start();
