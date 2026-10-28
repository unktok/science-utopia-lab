import { canonicalHash, stableStringify } from "./hash";
import { installArcologyRail } from "./arcologyNav";
import {
  initialSandboxState,
  materializeSystemSpec,
  parseSandboxBundle,
  validateSystemSpec,
  verifySandboxBundle,
  type SandboxBundle,
  type SandboxState,
  type ValidationReport,
} from "./systemSandbox";
import "./style.css";
import "./sandbox.css";

installArcologyRail("sandbox");

const CONTRACT_URL = "/data/system-sandbox.contract.json";
const required = <T extends Element>(id: string): T => {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Missing #${id}`);
  return element as unknown as T;
};
const escapeHtml = (value: unknown): string => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
const cloneState = (state: SandboxState): SandboxState => JSON.parse(JSON.stringify(state)) as SandboxState;

let bundle: SandboxBundle;
let state: SandboxState;
let baseState: SandboxState;
let renderRevision = 0;

function nodeAsset(assetKey: string): string {
  return `/assets/noctiluca/production/${assetKey.replaceAll("_", "-")}.svg`;
}

function buildNodeControls(): void {
  const layer = required<HTMLDivElement>("system-node-layer");
  layer.innerHTML = bundle.node_catalog.map((node) => `
    <article class="system-node" id="node-${escapeHtml(node.mechanism_id)}" style="--node-x:${node.x}%;--node-y:${node.y}%" data-node-id="${escapeHtml(node.mechanism_id)}">
      <label class="node-power"><input type="checkbox" data-node-toggle="${escapeHtml(node.mechanism_id)}" checked /><span>ACTIVE</span></label>
      <img src="${nodeAsset(node.asset_key)}" width="48" height="40" alt="" />
      <div class="node-copy"><span>${escapeHtml(node.label)}</span><small>${escapeHtml(node.description)}</small></div>
      <label class="implementation-control"><span>IMPLEMENTATION</span><select data-node-implementation="${escapeHtml(node.mechanism_id)}" aria-label="${escapeHtml(node.label)} implementation">${node.implementations.map((choice) => `<option value="${escapeHtml(choice.id)}">${escapeHtml(choice.label)}</option>`).join("")}</select></label>
    </article>`).join("");
  layer.querySelectorAll<HTMLInputElement>("[data-node-toggle]").forEach((input) => input.addEventListener("change", () => {
    const id = input.dataset.nodeToggle!;
    state.nodes[id]!.enabled = input.checked;
    void render();
  }));
  layer.querySelectorAll<HTMLSelectElement>("[data-node-implementation]").forEach((select) => select.addEventListener("change", () => {
    const id = select.dataset.nodeImplementation!;
    state.nodes[id]!.implementation = select.value;
    void render();
  }));
}

function buildEdgeControls(): void {
  const controls = required<HTMLOListElement>("edge-controls");
  controls.innerHTML = bundle.edge_catalog.map((edge) => `
    <li id="control-${escapeHtml(edge.edge_id)}" data-channel="${escapeHtml(edge.connection.channel)}">
      <label class="edge-power"><input type="checkbox" data-edge-toggle="${escapeHtml(edge.edge_id)}" checked /><span>${escapeHtml(edge.label)}</span></label>
      <p><code>${escapeHtml(edge.connection.source_mechanism)}.${escapeHtml(edge.connection.source_port)}</code><b>→</b><code>${escapeHtml(edge.connection.target_mechanism)}.${escapeHtml(edge.connection.target_port)}</code></p>
      <label class="latency-control"><span>LATENCY / PERIODS</span><select data-edge-latency="${escapeHtml(edge.edge_id)}" aria-label="${escapeHtml(edge.label)} latency">${edge.allowed_latencies.map((latency) => `<option value="${latency}">${latency}</option>`).join("")}</select></label>
    </li>`).join("");
  controls.querySelectorAll<HTMLInputElement>("[data-edge-toggle]").forEach((input) => input.addEventListener("change", () => {
    const id = input.dataset.edgeToggle!;
    state.edges[id]!.enabled = input.checked;
    void render();
  }));
  controls.querySelectorAll<HTMLSelectElement>("[data-edge-latency]").forEach((select) => select.addEventListener("change", () => {
    const id = select.dataset.edgeLatency!;
    state.edges[id]!.latency = Number(select.value);
    void render();
  }));
}

function syncControls(): void {
  for (const node of bundle.node_catalog) {
    const nodeState = state.nodes[node.mechanism_id]!;
    const card = required<HTMLElement>(`node-${node.mechanism_id}`);
    card.dataset.enabled = String(nodeState.enabled);
    card.querySelector<HTMLInputElement>("[data-node-toggle]")!.checked = nodeState.enabled;
    card.querySelector<HTMLSelectElement>("[data-node-implementation]")!.value = nodeState.implementation;
  }
  for (const edge of bundle.edge_catalog) {
    const edgeState = state.edges[edge.edge_id]!;
    const control = required<HTMLElement>(`control-${edge.edge_id}`);
    control.dataset.enabled = String(edgeState.enabled);
    control.querySelector<HTMLInputElement>("[data-edge-toggle]")!.checked = edgeState.enabled;
    control.querySelector<HTMLSelectElement>("[data-edge-latency]")!.value = String(edgeState.latency);
  }
}

function renderEdges(): void {
  const byId = new Map(bundle.node_catalog.map((node) => [node.mechanism_id, node]));
  required<SVGGElement>("system-edge-layer").innerHTML = bundle.edge_catalog.map((edge, index) => {
    const source = byId.get(edge.connection.source_mechanism)!;
    const target = byId.get(edge.connection.target_mechanism)!;
    const edgeState = state.edges[edge.edge_id]!;
    const sourceActive = state.nodes[source.mechanism_id]!.enabled;
    const targetActive = state.nodes[target.mechanism_id]!.enabled;
    const x1 = source.x * 10;
    const y1 = source.y * 6.4 + 55;
    const x2 = target.x * 10;
    const y2 = target.y * 6.4 + 10;
    const bend = index % 2 === 0 ? 34 : -34;
    const midY = Math.round((y1 + y2) / 2 + bend);
    const points = `${x1},${y1} ${x1},${midY} ${x2},${midY} ${x2},${y2}`;
    return `<g class="system-edge" data-channel="${edge.connection.channel}" data-enabled="${edgeState.enabled}" data-endpoints-active="${sourceActive && targetActive}"><polyline points="${points}" marker-end="url(#sandbox-arrow)"/><text x="${Math.round((x1 + x2) / 2)}" y="${midY - 7}" text-anchor="middle">L${edgeState.latency} · ${escapeHtml(edge.connection.channel.toUpperCase())}</text></g>`;
  }).join("");
}

function markIssues(report: ValidationReport): void {
  document.querySelectorAll<HTMLElement>(".system-node, .edge-controls li").forEach((element) => { element.dataset.issue = "false"; });
  for (const issue of report.issues) {
    for (const node of bundle.node_catalog) if (issue.path.includes(node.mechanism_id)) required<HTMLElement>(`node-${node.mechanism_id}`).dataset.issue = "true";
    const connectionMatch = issue.path.match(/^connections\[(\d+)\]/);
    if (connectionMatch) bundle.edge_catalog[Number(connectionMatch[1])] && (required<HTMLElement>(`control-${bundle.edge_catalog[Number(connectionMatch[1])]!.edge_id}`).dataset.issue = "true");
  }
}

async function render(): Promise<void> {
  const revision = ++renderRevision;
  syncControls();
  renderEdges();
  const spec = materializeSystemSpec(bundle, state);
  const report = validateSystemSpec(spec);
  const fingerprint = await canonicalHash(spec);
  if (revision !== renderRevision) return;
  const chip = required<HTMLElement>("validity-chip");
  chip.dataset.valid = String(report.valid);
  chip.textContent = report.valid ? "VALID STRUCTURE" : `${report.issues.filter((issue) => issue.severity === "error").length} STRUCTURAL ERROR${report.issues.filter((issue) => issue.severity === "error").length === 1 ? "" : "S"}`;
  required<HTMLElement>("spec-fingerprint").textContent = fingerprint;
  required<HTMLElement>("node-count").textContent = String(spec.mechanisms.length);
  required<HTMLElement>("edge-count").textContent = String(spec.connections.length);
  required<HTMLElement>("latency-count").textContent = String(Math.max(0, ...spec.connections.map((connection) => connection.latency)));
  required<HTMLElement>("validation-title").textContent = report.valid ? "Python-parity structural checks pass" : "Technical graph contract rejected";
  required<HTMLUListElement>("validation-issues").innerHTML = report.issues.length
    ? report.issues.map((issue) => `<li data-severity="${issue.severity}"><strong>${escapeHtml(issue.code)}</strong><code>${escapeHtml(issue.path)}</code><span>${escapeHtml(issue.message)}</span></li>`).join("")
    : "<li data-severity=\"ok\"><strong>NO ISSUES</strong><span>All typed endpoints, required inputs, schedules, and latencies are structurally valid.</span></li>";
  required<HTMLElement>("spec-json").textContent = JSON.stringify(spec, null, 2);
  const changedNodes = bundle.node_catalog.filter((node) => stableStringify(state.nodes[node.mechanism_id]) !== stableStringify(baseState.nodes[node.mechanism_id])).length;
  const changedEdges = bundle.edge_catalog.filter((edge) => stableStringify(state.edges[edge.edge_id]) !== stableStringify(baseState.edges[edge.edge_id])).length;
  required<HTMLElement>("change-summary").textContent = changedNodes + changedEdges === 0 ? "BASE SPEC" : `${changedNodes} NODE / ${changedEdges} EDGE MUTATIONS`;
  markIssues(report);
}

function reset(): void {
  state = cloneState(baseState);
  void render();
}

function disconnectPublication(): void {
  state = cloneState(baseState);
  state.edges["edge:3"]!.enabled = false;
  void render();
}

async function boot(): Promise<void> {
  try {
    const response = await fetch(CONTRACT_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`System sandbox contract returned HTTP ${response.status}`);
    bundle = parseSandboxBundle(await response.json());
    await verifySandboxBundle(bundle);
    state = initialSandboxState(bundle);
    baseState = cloneState(state);
    required<HTMLElement>("sandbox-disclosure").textContent = bundle.disclosure;
    const status = required<HTMLElement>("contract-status");
    status.dataset.state = "verified";
    status.textContent = "PYTHON PARITY VERIFIED";
    status.title = `synthetic contract SHA-256 ${bundle.bundle_hash}`;
    buildNodeControls();
    buildEdgeControls();
    required<HTMLButtonElement>("reset-spec").addEventListener("click", reset);
    required<HTMLButtonElement>("break-publication").addEventListener("click", disconnectPublication);
    const parameters = new URLSearchParams(location.search);
    required<HTMLElement>("sandbox-app").dataset.motion = parameters.get("motion") === "reduced" || matchMedia("(prefers-reduced-motion: reduce)").matches ? "reduced" : "full";
    if (parameters.get("preset") === "invalid-publication") disconnectPublication(); else await render();
  } catch (error) {
    const panel = required<HTMLElement>("sandbox-error");
    panel.hidden = false;
    panel.querySelector("span")!.textContent = error instanceof Error ? error.message : String(error);
    const status = required<HTMLElement>("contract-status");
    status.dataset.state = "error";
    status.textContent = "CONTRACT REJECTED";
  }
}

window.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement || event.target instanceof HTMLButtonElement) return;
  if (event.key.toLowerCase() === "r") reset();
  if (event.key.toLowerCase() === "b") disconnectPublication();
});

void boot();
