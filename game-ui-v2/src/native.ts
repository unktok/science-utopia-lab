import { parseNativeLab, type NativeLab, type NativeCandidate, type NativeNode } from "./nativeContract";
import "./generative.css";
import "./native.css";

const el = <T extends HTMLElement>(id: string): T => {
  const item = document.getElementById(id); if (!item) throw new Error(`Missing native UI element ${id}`); return item as T;
};
const escape = (value: unknown): string => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const candidate = el<HTMLSelectElement>("candidate"), year = el<HTMLSelectElement>("year");
let lab: NativeLab, selected = "", execution = -1;
const selectedSystem = (): NativeCandidate => { const row = lab.systems[Number(candidate.value)]; if (!row) throw new Error("Missing selected system"); return row; };
const image = (node: NativeNode): string => ({ research: "institution-lab.svg", population: "institution-lab.svg", funding: "institution-funding.svg", evaluation: "system-evaluation.svg", publication: "system-publication.svg", communication: "system-government.svg" }[node.family] || "system-government.svg");

function inspect(): void {
  const system = selectedSystem(), node = system.spec.mechanisms.find(n => n.mechanism_id === selected);
  if (!node) return;
  document.querySelectorAll<HTMLButtonElement>("[data-native-node]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.nativeNode === selected)));
  el("node-name").textContent = node.mechanism_id;
  el("node-meta").textContent = `${node.family.toUpperCase()} / ${node.implementation}`;
  el("native-ports").textContent = `INPUT  ${node.inputs.map(p => p.port_id).join(" · ") || "none"}\nOUTPUT  ${node.outputs.map(p => p.port_id).join(" · ") || "none"}`;
  el("native-source").textContent = typeof node.parameters.code_artifact?.source === "string" ? node.parameters.code_artifact.source : node.parameters.program ? JSON.stringify(node.parameters.program, null, 2) : node.parameters.instruction ? String(node.parameters.instruction) : "Original researcher-world operation. No additional code.\n" + JSON.stringify(node.parameters, null, 2);
  const events = system.runs[0]?.events.filter(e => e.year === Number(year.value) && e.provenance.mechanism_id === selected) || [];
  el("native-events").textContent = events.length ? events.map(e => JSON.stringify(e, null, 2)).join("\n") : "No execution records for this year. No activity is fabricated.";
  drawEdges();
}

function drawEdges(): void {
  const graph = el("native-graph"), overlay = graph.querySelector<SVGSVGElement>("svg");
  if (!overlay || !lab) return;
  const nodes = new Map(Array.from(graph.querySelectorAll<HTMLElement>("[data-native-node]")).map(n => [n.dataset.nativeNode!, n]));
  const origin = graph.getBoundingClientRect();
  overlay.setAttribute("viewBox", `0 0 ${origin.width} ${origin.height}`);
  overlay.innerHTML = `<defs><marker id="native-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L8 4L0 8" fill="currentColor"/></marker></defs>` + selectedSystem().spec.connections.map(edge => {
    const from = nodes.get(edge.source_mechanism)?.getBoundingClientRect(), to = nodes.get(edge.target_mechanism)?.getBoundingClientRect(); if (!from || !to) return "";
    const sameRow = Math.abs(from.y - to.y) < 8;
    const x1 = (sameRow ? from.right : from.x + from.width / 2) - origin.x, y1 = (sameRow ? from.y + from.height / 2 : from.bottom) - origin.y;
    const x2 = (sameRow ? to.left : to.x + to.width / 2) - origin.x, y2 = (sameRow ? to.y + to.height / 2 : to.top) - origin.y;
    const active = selected === edge.source_mechanism || selected === edge.target_mechanism;
    return `<path class="native-wire ${active ? "active" : ""}" d="M${x1},${y1} C${x1},${y1 + (sameRow ? 0 : 20)} ${x2},${y2 - (sameRow ? 0 : 20)} ${x2},${y2}" marker-end="url(#native-arrow)"><title>${escape(`${edge.source_mechanism}.${edge.source_port} → ${edge.target_mechanism}.${edge.target_port} / ${edge.channel} / delay ${edge.latency}`)}</title></path>`;
  }).join("");
}

function render(): void {
  const system = selectedSystem(), spec = system.spec, run = system.runs[0];
  const phase = new Map(spec.schedules.map(s => [s.mechanism_id, s.phase]));
  const ordered = [...spec.mechanisms].sort((a, b) => (phase.get(a.mechanism_id) || 0) - (phase.get(b.mechanism_id) || 0));
  if (!ordered.some(n => n.mechanism_id === selected)) selected = ordered[0]?.mechanism_id || "";
  el("graph-count").textContent = `${ordered.length} NODES / ${spec.connections.length} WIRES`;
  el("native-graph").innerHTML = `<svg class="native-wires" aria-hidden="true"></svg><div class="native-grid">` + ordered.map(node => {
    const added = system.difference.nodes_added.includes(node.mechanism_id), changed = system.difference.nodes_changed.includes(node.mechanism_id);
    const kind = node.implementation === "code.python.v1" ? "PYTHON" : node.implementation === "program.tensor.v1" ? "HARD / SOFT" : node.implementation.includes("llm") ? "LLM" : "NATIVE";
    return `<button type="button" class="native-node ${added ? "added" : changed ? "changed" : ""}" data-native-node="${escape(node.mechanism_id)}" aria-pressed="${selected === node.mechanism_id}"><span class="native-node-top"><span>PHASE ${phase.get(node.mechanism_id) ?? "—"}</span><span>${added ? "NEW" : changed ? "REPLACED" : kind}</span></span><img src="./assets/noctiluca/production/${image(node)}" alt="" /><span class="native-node-name">${escape(node.mechanism_id)}</span><span class="native-node-kind">${kind}</span></button>`;
  }).join("") + "</div>";
  document.querySelectorAll<HTMLButtonElement>("[data-native-node]").forEach(button => button.addEventListener("click", () => { selected = button.dataset.nativeNode!; inspect(); }));
  const frame = run?.frames.find(f => f.year === Number(year.value));
  el("native-actors").innerHTML = frame ? frame.actors.filter(a => a.can_author).map((actor, i) => `<article class="native-actor"><i class="native-person" aria-hidden="true"></i><b>RESEARCHER ${String(i + 1).padStart(2, "0")}</b><span>${escape(actor.id)}</span><strong>${actor.resources.toFixed(1)} RESOURCES</strong><span>${actor.is_active ? "ACTIVE" : "INACTIVE"} / YEAR ${frame.year}</span></article>`).join("") : "No completed researcher snapshot.";
  const metrics = system.runs.length ? ` <div><small>ACTUAL MODEL</small><b>${escape(lab.source.world.model)}</b></div><div><small>OBSERVED PAPERS / YEAR ${frame?.year ?? "—"}</small><b>${frame?.paper_count ?? "—"}</b></div>` : "";
  el("native-metrics").innerHTML = `<div class="primary"><small>ACTUAL NATIVE LOSS</small><b>${system.native_loss === null ? "NO VALID LOSS" : system.native_loss.toFixed(3)}</b></div>${metrics}`;
  el("fingerprint").textContent = `SYSTEM ${system.system_fingerprint}`;
  el("native-path").replaceChildren(...lab.systems.map((row, i) => {
    const line = document.createElement("div"); line.className = "native-path-row"; line.textContent = `${String(i + 1).padStart(2, "0")}  ${row.status.toUpperCase()}  NATIVE LOSS ${row.native_loss ?? "null"}  / +${row.difference.nodes_added.length} nodes · ${row.difference.nodes_changed.length} replaced`; return line;
  }));
  const fit = lab.relaxation;
  el("native-gradient").textContent = fit ? `CONDITIONAL SOFT FIT  ${fit.history[0]?.conditional_soft_loss.toFixed(4)} → ${fit.history.at(-1)?.conditional_soft_loss.toFixed(4)}\n${fit.scope}\nLLM WEIGHTS FIXED / FULL-WORLD AUTOGRAD: NO` : "No soft fitting was performed in this run.\nLLM WEIGHTS FIXED / FULL-WORLD AUTOGRAD: NO";
  el<HTMLButtonElement>("step").disabled = !run?.events.some(e => e.year === Number(year.value) && typeof e.provenance.mechanism_id === "string");
  inspect(); requestAnimationFrame(drawEdges);
}

function choose(): void {
  execution = -1;
  const frames = selectedSystem().runs[0]?.frames || [];
  year.replaceChildren(...frames.map(frame => new Option(`YEAR ${frame.year}`, String(frame.year))));
  if (frames.length) year.value = String(frames.at(-1)!.year);
  render();
}

async function load(value: unknown): Promise<void> {
  lab = await parseNativeLab(value);
  el("status").textContent = "HASH VERIFIED / NATIVE DEVELOPMENT EVIDENCE";
  el("error").hidden = true;
  el("source").textContent = `SOURCE ${lab.source.world.source_commit.slice(0, 12)} / ${lab.source.world.years} NATIVE YEARS / READ-ONLY EVIDENCE`;
  candidate.replaceChildren(...lab.systems.map((row, i) => new Option(`${i + 1}. ${i ? "REVISED DESIGN" : "INITIAL DESIGN"} / LOSS ${row.native_loss ?? "null"}`, String(i))));
  choose();
}
function failure(error: unknown): void { el("error").hidden = false; el("error").textContent = String(error); el("status").textContent = "EVIDENCE LOAD FAILED"; }
candidate.addEventListener("change", choose);
year.addEventListener("change", () => { execution = -1; render(); });
el("step").addEventListener("click", () => {
  const events = selectedSystem().runs[0]?.events.filter(e => e.year === Number(year.value) && typeof e.provenance.mechanism_id === "string") || [];
  if (!events.length) return;
  execution = (execution + 1) % events.length;
  selected = String(events[execution]!.provenance.mechanism_id); inspect();
});
el<HTMLInputElement>("load").addEventListener("change", async event => { try { const file = (event.target as HTMLInputElement).files?.[0]; if (file) await load(JSON.parse(await file.text())); } catch (error) { failure(error); } });
new ResizeObserver(drawEdges).observe(el("native-graph"));
fetch("./data/native-design-lab-v1.json").then(response => { if (!response.ok) throw new Error("Use LOAD RUN to select native execution evidence."); return response.json(); }).then(load).catch(failure);
