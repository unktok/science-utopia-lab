import { AdoptionController, parseDesignLifecycle, type DesignArm, type DesignLifecycleSnapshot, type DesignNode, type DesignSystem } from "./designLifecycleContract";
import { initializeSameSocietyView } from "./sameSocietyView";
import "./designLifecycle.css";

const el = <T extends Element = HTMLElement>(id: string): T => { const node = document.getElementById(id); if (!node) throw new Error(`Missing lifecycle element ${id}`); return node as unknown as T; };
const escape = (value: unknown): string => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const short = (value: string, count = 14): string => `${value.slice(0, count)}…`;
const connectionLabel = (edge: { source_mechanism: string; source_port: string; target_mechanism: string; target_port: string; channel: string }): string => `${edge.source_mechanism}.${edge.source_port} → ${edge.target_mechanism}.${edge.target_port} / ${edge.channel}`;
const displayName = (nodeId: string): string => nodeId.startsWith("generated-") ? nodeId.split(".").slice(1).join(".") : nodeId.replace("world.", "");

let snapshot: DesignLifecycleSnapshot;
let armIndex = 0;
let systemIndex = 1;
let selectedNode = "";
const adoption = new AdoptionController();

function arm(): DesignArm { return snapshot.arms[armIndex]!; }
function system(): DesignSystem { return arm().systems[systemIndex]!; }

function renderHeader(): void {
  el("source-hash").textContent = `AUDIT ${short(snapshot.source.artifact_sha256, 18)}`;
  el("designer-meta").textContent = `${snapshot.experiment.designer.identity} / hash-bound manifest / provider identity self-reported, not authenticated`;
  const researchers = snapshot.experiment.researchers;
  el("researcher-meta").textContent = `${snapshot.experiment.physical_complete_runs} reset physical worlds / ${researchers.population} agents per world / ${researchers.responses_per_world} fresh responses per world`;
  el("source-meta").textContent = `SOURCE ${snapshot.source.source_commit.slice(0, 12)} // AUDIT ${snapshot.source.artifact_sha256.slice(0, 16)}`;
}

function renderArmSwitch(): void {
  const host = el("arm-switch");
  host.innerHTML = snapshot.arms.map((item, index) => `<button type="button" data-arm="${index}" aria-pressed="${index === armIndex}"><span>LOSS ARM ${index + 1}</span><b>${escape(item.short)}</b></button>`).join("");
  host.querySelectorAll<HTMLButtonElement>("button").forEach((button) => button.addEventListener("click", () => {
    armIndex = Number(button.dataset.arm); systemIndex = arm().selected_index; selectedNode = ""; renderArm();
  }));
}

function renderChart(): void {
  const losses = arm().loss_path;
  const min = Math.min(...losses), max = Math.max(...losses), span = max - min || 1;
  const points = losses.map((loss, index) => ({ x: 12 + index * 38, y: 78 - ((loss - min) / span) * 58 }));
  el<SVGSVGElement>("loss-chart").setAttribute("viewBox", "0 0 100 100");
  el("loss-chart").innerHTML = `<line class="axis" x1="5" y1="84" x2="95" y2="84"></line><polyline class="path" points="${points.map((point) => `${point.x},${point.y}`).join(" ")}"></polyline>${points.map((point, index) => `<circle class="point" cx="${point.x}" cy="${point.y}" r="3.3"></circle><text x="${point.x}" y="${Math.max(8, point.y - 7)}" text-anchor="middle" fill="currentColor" font-size="5">${escape(losses[index])}</text>`).join("")}`;
}

function renderStations(): void {
  const host = el("system-stations");
  host.innerHTML = arm().systems.map((item) => `<button class="system-station" type="button" data-system="${item.index}" data-status="${item.status}" aria-pressed="${item.index === systemIndex}"><span class="station-top"><span>STATION 0${item.index}</span><span>${item.status === "selected" ? "FIRST MIN" : item.status === "baseline" ? "ORIGIN" : "LATER TIE"}</span></span><strong class="station-loss">${item.loss}</strong><span class="station-name">${escape(item.role.toUpperCase())}</span><span class="station-nodes">${item.nodes.length} NODES / ${item.connections.length} WIRES<br />${item.generated_node_ids.length} EXECUTABLE CODE NODE${item.generated_node_ids.length === 1 ? "" : "S"}</span></button>`).join("");
  host.querySelectorAll<HTMLButtonElement>("button").forEach((button) => button.addEventListener("click", () => { systemIndex = Number(button.dataset.system); selectedNode = ""; renderSystem(); renderStations(); }));
}

function nodeClass(node: DesignNode, item: DesignSystem): string {
  const classes = ["graph-node"];
  if (node.implementation === "code.python.v1") classes.push("generated");
  if (item.diff.nodes_added.includes(node.id)) classes.push("added");
  return classes.join(" ");
}

function renderGraph(): void {
  const item = system();
  const ordered = [...item.nodes].sort((left, right) => (left.phase ?? 999) - (right.phase ?? 999) || left.id.localeCompare(right.id));
  const ghosts = item.diff.nodes_removed.filter((id) => !ordered.some((node) => node.id === id));
  el("system-graph").innerHTML = `<svg class="system-wires" aria-hidden="true"></svg><div class="system-graph__grid">${ordered.map((node) => `<button class="${nodeClass(node, item)}" type="button" data-node="${escape(node.id)}" aria-pressed="${node.id === selectedNode}"><small><span>φ${node.phase ?? "—"}</span><span>${node.implementation === "code.python.v1" ? "PY" : "WORLD"}</span></small><b>${escape(displayName(node.id))}</b><em>${escape(node.family)} / ${node.inputs.length} IN · ${node.outputs.length} OUT</em></button>`).join("")}${ghosts.map((id) => `<div class="graph-node removed"><small><span>REMOVED</span><span>Δ</span></small><b>${escape(displayName(id))}</b><em>present in parent</em></div>`).join("")}</div>`;
  el("system-graph").querySelectorAll<HTMLButtonElement>("[data-node]").forEach((button) => button.addEventListener("click", () => { selectedNode = button.dataset.node!; renderInspector(); renderGraphSelection(); drawWires(); }));
  requestAnimationFrame(drawWires);
}

function renderGraphSelection(): void {
  el("system-graph").querySelectorAll<HTMLButtonElement>("[data-node]").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.node === selectedNode)));
}

function drawWires(): void {
  const graph = el("system-graph"), svg = graph.querySelector<SVGSVGElement>(".system-wires");
  if (!svg) return;
  const origin = graph.getBoundingClientRect();
  const nodes = new Map(Array.from(graph.querySelectorAll<HTMLElement>("[data-node]")).map((node) => [node.dataset.node!, node.getBoundingClientRect()]));
  svg.setAttribute("viewBox", `0 0 ${origin.width} ${origin.height}`);
  svg.innerHTML = `<defs><marker id="life-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L8 4L0 8" fill="currentColor"/></marker></defs>${system().connections.map((edge) => {
    const from = nodes.get(edge.source_mechanism), to = nodes.get(edge.target_mechanism); if (!from || !to) return "";
    const x1 = from.left + from.width / 2 - origin.left, y1 = from.bottom - origin.top;
    const x2 = to.left + to.width / 2 - origin.left, y2 = to.top - origin.top;
    const bend = Math.max(12, Math.abs(y2 - y1) * .45), active = selectedNode && (edge.source_mechanism === selectedNode || edge.target_mechanism === selectedNode);
    return `<path class="system-wire${active ? " active" : ""}" data-channel="${escape(edge.channel)}" d="M${x1} ${y1} C${x1} ${y1 + bend},${x2} ${y2 - bend},${x2} ${y2}" marker-end="url(#life-arrow)"></path>`;
  }).join("")}`;
}

function renderInspector(): void {
  const node = system().nodes.find((candidate) => candidate.id === selectedNode) ?? system().nodes.find((candidate) => system().generated_node_ids.includes(candidate.id)) ?? system().nodes[0]!;
  selectedNode = node.id;
  el("node-title").textContent = node.id;
  el("node-meta").textContent = `${node.family.toUpperCase()} / ${node.implementation} / PHASE ${node.phase ?? "UNSCHEDULED"}`;
  el("node-ports").innerHTML = [...node.inputs.map((port) => ({ ...port, direction: "input" })), ...node.outputs.map((port) => ({ ...port, direction: "output" }))].map((port) => `<div class="node-port ${port.direction}"><b>${port.direction.toUpperCase()} / ${escape(port.port_id)}</b><br />${escape(port.artifact_type)} · ${escape(port.channel)}</div>`).join("") || `<div class="diff-empty">No typed ports declared.</div>`;
  el("node-source").textContent = node.code?.source ?? "Native researcher-world mechanism. No generated source is attributed to this node in the audited system.";
}

function diffRow(kind: "add" | "remove" | "neutral", title: string, value: string): string { return `<div class="diff-row ${kind}"><strong>${escape(title)}</strong>${escape(value)}</div>`; }
function renderDiff(): void {
  const diff = system().diff;
  el("code-diff").innerHTML = `<div class="diff-list">${diff.generated_code.map((code) => diffRow("add", `${code.label} / ${code.executions} EXECUTIONS`, `${code.mechanism_id}\nsource ${code.source_sha256}\nartifact ${code.artifact_sha256}`)).join("") || `<p class="diff-empty">No generated-code execution in this station.</p>`}${diff.nodes_removed.map((node) => diffRow("remove", "REMOVED FROM PARENT", node)).join("")}</div>`;
  const protocols = [...diff.protocol_types_added.map((type) => diffRow("add", "ADDED ARTIFACT TYPE", type)), ...diff.protocol_types_removed.map((type) => diffRow("remove", "REMOVED ARTIFACT TYPE", type))];
  el("protocol-diff").innerHTML = `<div class="diff-list">${protocols.join("") || `<p class="diff-empty">Typed ports remain within the existing artifact vocabulary. Inspect the node ports for exact input/output contracts.</p>`}</div>`;
  const wires = [...diff.connections_added.map((edge) => diffRow("add", "WIRE ADDED", connectionLabel(edge))), ...diff.connections_removed.map((edge) => diffRow("remove", "WIRE REMOVED", connectionLabel(edge)))];
  el("wiring-diff").innerHTML = `<div class="diff-list">${wires.join("") || `<p class="diff-empty">Shared baseline: no parent topology exists inside this path.</p>`}</div>`;
}

function renderLedger(): void {
  const selected = arm().systems[arm().selected_index]!;
  const laterTie = arm().systems.find((candidate, index) => index > arm().selected_index && candidate.loss === selected.loss)!;
  el("selection-reason").textContent = `${selected.selection_reason} Station 0${laterTie.index} was still executed and observed at the same loss (${laterTie.loss}), but it did not replace the earlier minimum.`;
  el("selected-index").textContent = `0${arm().selected_index}`;
  el("selected-loss").textContent = String(selected.loss);
  el("failure-count").textContent = String(arm().systems.reduce((count, candidate) => count + candidate.technical_failures.length, 0));
  el("response-count").textContent = `${snapshot.experiment.researchers.responses_per_world} / WORLD`;
}

function renderSystem(): void {
  const item = system();
  el("system-role").textContent = `${item.role.toUpperCase()} / LOSS ${item.loss}`;
  el("system-fingerprint").textContent = item.system_fingerprint;
  renderGraph(); renderInspector(); renderGraphSelection(); renderDiff();
}

function renderArm(): void {
  document.documentElement.style.setProperty("--arm", arm().accent === "violet" ? "#a86bff" : "#2dd4ff");
  el("loss-formula").textContent = arm().formula;
  el("loss-interpretation").textContent = arm().interpretation;
  renderArmSwitch(); renderChart(); renderStations(); renderSystem(); renderLedger();
}

function renderAdoption(): void {
  el("adoption-status").textContent = `${adoption.state.toUpperCase()} / ${adoption.message} Contract: ${snapshot.adoption.contract_schema}.`;
}

function renderTruth(): void {
  const claims = [
    ["ACTUAL NATIVE EXECUTION", snapshot.claims.native_code_executed_in_experiment, "Five physical worlds; six logical loss observations."],
    ["HELD-OUT EVALUATION", snapshot.claims.held_out, "Development seed 1301 only."],
    ["INDEPENDENT REPLICATES", snapshot.claims.independent_replicates, "Baseline is shared; cross-scores reuse physical worlds."],
    ["SCIENTIFIC VALUE", snapshot.claims.scientific_value, "Both objectives are explicit engineering proxies."],
    ["FULL-WORLD DIFFERENTIATION", snapshot.claims.full_world_differentiation, "Only the native selection cut was designed."],
    ["SAME-SOCIETY ADOPTION", snapshot.claims.same_society_adoption_executed, "Fresh worlds were used for the audited campaign."],
    ["RECURSIVE DESIGNER", snapshot.claims.automatic_recursive_designer, "Two externally authored revisions per loss arm."],
    ["AUTHENTICATED AUTHOR ID", snapshot.claims.author_identity_authenticated, "Codex author identity is self-reported provenance."],
  ] as const;
  el("truth-claims").innerHTML = claims.map(([label, value, note]) => `<article class="truth-card ${value ? "yes" : "no"}"><b>${value ? "YES" : "NO"} // ${escape(label)}</b><span>${escape(note)}</span></article>`).join("");
}

async function start(): Promise<void> {
  const response = await fetch("./data/native-design-lifecycle-v5.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`Lifecycle snapshot unavailable (${response.status})`);
  snapshot = parseDesignLifecycle(await response.json());
  armIndex = snapshot.arms.findIndex((candidate) => candidate.id === "native-joint-v5-throughput"); if (armIndex < 0) armIndex = 0;
  systemIndex = arm().selected_index;
  renderHeader(); renderArm(); renderAdoption(); renderTruth();
  initializeSameSocietyView();
  window.addEventListener("resize", drawWires);
  window.addEventListener("keydown", (event) => {
    if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.key === "1" || event.key === "2") { armIndex = Number(event.key) - 1; systemIndex = arm().selected_index; selectedNode = ""; renderArm(); }
    if (event.key === "3" || event.key === "4" || event.key === "5") { systemIndex = Number(event.key) - 3; selectedNode = ""; renderStations(); renderSystem(); }
  });
}

void start().catch((error) => { const fatal = el("fatal-error"); fatal.hidden = false; fatal.textContent = `DESIGN CHRONICLE FAILED CLOSED // ${String(error)}`; });
