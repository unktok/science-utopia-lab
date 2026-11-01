import {
  OBJECTIVE_IDS, parseObjectiveStructureReceipt, parseObjectiveStructureReport, sha256Text, verifyFixtureReport,
  type ObjectiveArm, type ObjectiveId, type ObjectiveStructureReport, type Row, type StructuralRow,
} from "./objectiveStructureContract";
import { objectiveStructureFixture } from "./objectiveStructureFixture";
import "./objectiveStructure.css";

const labels: Record<ObjectiveId, { short: string; formula: string; detail: string; accent: string }> = {
  [OBJECTIVE_IDS[0]]: { short: "THROUGHPUT", formula: "L = −A", detail: "minimize negative accepted-decision count", accent: "cyan" },
  [OBJECTIVE_IDS[1]]: { short: "NET REVIEWED UTILITY", formula: "L = 3.25A − Q + 0.05R", detail: "illustrative accepted / peer-score / review-count tradeoff", accent: "violet" },
};
const el = <T extends Element = HTMLElement>(id: string): T => { const value = document.getElementById(id); if (!value) throw new Error(`Missing objective-structure element ${id}`); return value as unknown as T; };
const esc = (value: unknown): string => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const short = (value: unknown, size = 12): string => typeof value === "string" && value.length > size ? `${value.slice(0, size)}…` : String(value ?? "—");
const record = (value: unknown): Row => value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
const list = (value: unknown): any[] => Array.isArray(value) ? value : [];

let report: ObjectiveStructureReport;
let mode: "actual" | "fixture" = "actual";
let selectedArm: ObjectiveId = OBJECTIVE_IDS[0];
let selectedIndex = 0;

function arm(): ObjectiveArm { return report.arms[selectedArm]; }
function selected(): StructuralRow { return arm().rows[selectedIndex]!; }
function candidate(row: StructuralRow): Row | null { return row.draw?.suggestion?.candidate ?? null; }
function score(value: number | null): string { return value === null ? "N/A" : Number.isInteger(value) ? String(value) : value.toFixed(3).replace(/0+$/, "").replace(/\.$/, ""); }
function rowFingerprint(row: StructuralRow): string | null { return candidate(row)?.fingerprint ?? null; }
function rowState(row: StructuralRow, objective: ObjectiveId): string {
  const selection = report.arms[objective].selection;
  const fingerprint = rowFingerprint(row);
  if (fingerprint && fingerprint === selection.representative_system_fingerprint) return "selected";
  if (fingerprint && selection.tied_system_fingerprints.includes(fingerprint)) return "tie";
  return row.status === "complete" ? "complete" : "failed";
}
function statusCopy(row: StructuralRow): string {
  if (row.status === "complete") return `LOSS ${score(row.cross_objective_losses[row.arm])}`;
  if (row.status === "generation-failure") return "GENERATION FAILED / ZERO DRAWS";
  return "TECHNICAL FAILURE / LOSS NULL";
}

function renderPaths(): void {
  el("campaign-summary").textContent = `${report.status.toUpperCase()} // ${report.completed_physical_worlds}/8 COMPLETE WORLDS // ${report.raw_campaign_summary.physical_reply_count ?? "—"} PHYSICAL QWEN REPLIES`;
  el("objective-lines").innerHTML = OBJECTIVE_IDS.map((objective) => {
    const objectiveArm = report.arms[objective]; const meta = labels[objective];
    const stations = objectiveArm.rows.map((row, index) => {
      const state = rowState(row, objective); const pressed = selectedArm === objective && selectedIndex === index;
      return `<button type="button" class="path-station" data-arm="${objective}" data-index="${index}" data-state="${state}" aria-pressed="${pressed}">
        <span>G${row.generation}${row.draw_index === undefined ? "" : ` · D${row.draw_index + 1}`}</span><i></i><strong>${esc(statusCopy(row))}</strong>
        <small>${row.status === "complete" ? `SYSTEM ${esc(short(rowFingerprint(row), 15))}` : row.status === "generation-failure" ? "INVALID VOCABULARY · NO CANDIDATE" : "NO COMPLETE NATIVE ENDPOINT"}</small>
      </button>`;
    }).join("");
    return `<article class="objective-line" data-accent="${meta.accent}">
      <header><div><span>${meta.short}</span><h3>${meta.formula}</h3><p>${meta.detail}</p></div><div class="selection-chip"><b>FIRST BEST ${score(objectiveArm.selection.best_loss)}</b><small>${objectiveArm.selection.tie_count > 1 ? `${objectiveArm.selection.tie_count}-WAY EXACT TIE · EARLIEST SHOWN` : objectiveArm.selection.tie_count === 1 ? "ONE OBSERVED BEST" : "NO ELIGIBLE SYSTEM"}</small></div></header>
      <div class="station-rail">${stations}</div>
    </article>`;
  }).join("");
  for (const button of el("objective-lines").querySelectorAll<HTMLButtonElement>("button[data-arm]")) button.addEventListener("click", () => {
    selectedArm = button.dataset.arm as ObjectiveId; selectedIndex = Number(button.dataset.index); renderAll();
  });
}

function layout(system: Row): { positions: Map<string, [number, number]>; width: number; height: number } {
  const nodes = list(system.mechanisms); const columns = Math.min(5, Math.max(1, Math.ceil(Math.sqrt(nodes.length * 1.4))));
  const width = 920; const cellW = width / columns; const rows = Math.ceil(nodes.length / columns); const height = Math.max(270, rows * 124 + 42);
  const positions = new Map<string, [number, number]>();
  nodes.forEach((node, index) => positions.set(node.mechanism_id, [cellW * (index % columns + .5), 64 + Math.floor(index / columns) * 124]));
  return { positions, width, height };
}
function renderGraph(): void {
  const row = selected(); const system = candidate(row); const fingerprint = rowFingerprint(row);
  el("selected-fingerprint").textContent = `${labels[selectedArm].short} // ${row.status.toUpperCase()} // ${fingerprint ?? "NO SYSTEM"}`;
  el("graph-title").innerHTML = `<span>PATH STATION G${row.generation}${row.draw_index === undefined ? "" : ` / DRAW ${row.draw_index + 1}`}</span><strong>${esc(statusCopy(row))}</strong><small>${esc(row.strategy ?? "—")}</small>`;
  if (!system || !row.graph_changes) {
    el("system-graph").innerHTML = `<div class="empty-blueprint"><i></i><b>NO EXECUTABLE BLUEPRINT</b><p>${row.status === "generation-failure" ? "The generation failed before any draw existed. One failure event is shown—not two invented candidate failures." : "No complete candidate graph is bound to this station."}</p></div>`;
    el("change-ledger").innerHTML = `<span>EXACT CHANGE LEDGER</span><h3>NULL STRUCTURAL STATE</h3><p>No node, edge, source, protocol, or process change is inferred from a failed station.</p>`;
    el("source-inspector").innerHTML = `<div><span>SOURCE BAY</span><strong>NO CANDIDATE SOURCE</strong></div>`;
    return;
  }
  const change = row.graph_changes.vs_parent; const nodes = list(system.mechanisms); const connections = list(system.connections); const graph = layout(system);
  const edges = connections.map((edge) => {
    const from = graph.positions.get(edge.source_mechanism), to = graph.positions.get(edge.target_mechanism); if (!from || !to) return "";
    const added = change.edges_added.some((item) => item[0] === edge.source_mechanism && item[2] === edge.target_mechanism);
    return `<path class="graph-edge${added ? " is-added" : ""}" d="M ${from[0]} ${from[1] + 31} C ${from[0]} ${from[1] + 72}, ${to[0]} ${to[1] - 72}, ${to[0]} ${to[1] - 31}"/><circle class="packet" cx="${(from[0] + to[0]) / 2}" cy="${(from[1] + to[1]) / 2}" r="4"/>`;
  }).join("");
  const nodeSvg = nodes.map((node) => {
    const [x, y] = graph.positions.get(node.mechanism_id)!; const added = change.nodes_added.includes(node.mechanism_id); const sourceChanged = change.source_changes.some((item) => item.mechanism_id === node.mechanism_id);
    return `<g class="graph-node${added ? " is-added" : ""}${sourceChanged ? " is-source-changed" : ""}" transform="translate(${x - 68} ${y - 31})"><rect width="136" height="62"/><path d="M0 0h12v4H4v8H0zM136 0h-12v4h8v8h4zM0 62h12v-4H4v-8H0zM136 62h-12v-4h8v-8h4z"/><text x="10" y="20">${esc(short(node.mechanism_id, 19))}</text><text class="node-family" x="10" y="38">${esc(short(node.family, 20))}</text><text class="node-impl" x="10" y="52">${esc(short(node.implementation, 23))}</text>${added ? `<text class="change-mark" x="118" y="20">+</text>` : ""}</g>`;
  }).join("");
  el("system-graph").innerHTML = `<svg viewBox="0 0 ${graph.width} ${graph.height}" role="img" aria-label="Actual candidate system graph with ${nodes.length} nodes and ${connections.length} edges"><defs><filter id="glow"><feGaussianBlur stdDeviation="2" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><g>${edges}</g><g>${nodeSvg}</g></svg>`;
  const c = change.counts;
  const groups = [
    ["NODES", `+${c.nodes_added} / −${c.nodes_removed}`, [...change.nodes_added.map((v) => `+ ${v}`), ...change.nodes_removed.map((v) => `− ${v}`)]],
    ["WIRES", `+${c.edges_added} / −${c.edges_removed}`, [...change.edges_added.map((v) => `+ ${v[0]} → ${v[2]}`), ...change.edges_removed.map((v) => `− ${v[0]} → ${v[2]}`)]],
    ["SOURCE BODIES", `+${c.source_bodies_added ?? 0} / −${c.source_bodies_removed ?? 0}`, [...list(change.source_bodies_added).map((v) => `+ ${short(v, 16)}`), ...list(change.source_bodies_removed).map((v) => `− ${short(v, 16)}`)]],
    ["PROTOCOL / CONFIG", `${c.protocol_changes} / ${c.mechanism_configuration_changes}`, [...change.protocol_changes.map((v) => `protocol ${v.mechanism_id}`), ...change.mechanism_configuration_changes.map((v) => `config ${v}`)]],
    ["SCHEDULE", `+${c.schedules_added} / −${c.schedules_removed}`, []],
  ];
  el("change-ledger").innerHTML = `<span>EXACT CHANGE LEDGER · VS GENERATION PARENT</span><h3>${nodes.length} NODES / ${connections.length} EDGES</h3><p>Literal set and source differences. No semantic effect is inferred.</p>${groups.map(([name, value, items]) => `<section><b>${name}</b><strong>${value}</strong><small>${(items as string[]).map(esc).join("<br>") || "NO CHANGE"}</small></section>`).join("")}`;
  const codeNodes = nodes.filter((node) => node.implementation === "code.python.v1");
  el("source-inspector").innerHTML = codeNodes.length ? codeNodes.map((node) => {
    const artifact = record(record(node.parameters).code_artifact); const source = typeof artifact.source === "string" ? artifact.source : "SOURCE BODY NOT EXPORTED";
    const receipt = [...change.source_changes, ...list(change.same_source_body_renamed_ids)].find((item) => item.mechanism_id === node.mechanism_id || item.after_mechanism_id === node.mechanism_id);
    return `<article><div><span>EXECUTABLE SOURCE NODE</span><strong>${esc(node.mechanism_id)}</strong><small>${esc(node.implementation)} // ${esc(receipt ? short(receipt.after_sha256 ?? receipt.source_sha256, 20) : "BODY HASH IN DIFF MULTISET")}</small></div><pre>${esc(source)}</pre></article>`;
  }).join("") : `<div><span>SOURCE BAY</span><strong>NO PYTHON SOURCE NODE IN THIS CANDIDATE</strong></div>`;
}

function unavailableReason(row: StructuralRow, objective: ObjectiveId): string {
  const evaluation = row.loss_evaluations?.[objective];
  return evaluation?.rejected_runs?.map((item: Row) => item.reason).filter(Boolean).join(" · ") || "required metric unavailable at this checkpoint";
}
function renderCrossscores(): void {
  const matrix = report.selected_cross_objective_matrix;
  el("crossscore-grid").innerHTML = `<div class="matrix-corner"><span>SELECTED UNDER ↓</span><b>RESCORED AS →</b></div>${OBJECTIVE_IDS.map((id) => `<div class="matrix-head"><span>${labels[id].short}</span><b>${labels[id].formula}</b></div>`).join("")}${OBJECTIVE_IDS.map((source) => {
    const row = report.arms[source].rows.find((value) => rowFingerprint(value) === report.arms[source].selection.representative_system_fingerprint);
    return `<div class="matrix-label"><span>${labels[source].short}</span><b>${row ? short(rowFingerprint(row), 15) : "NO REPRESENTATIVE"}</b><small>${report.arms[source].selection.tie_count > 1 ? `EARLIEST OF ${report.arms[source].selection.tie_count} TIED` : "DEVELOPMENT REPRESENTATIVE"}</small></div>${OBJECTIVE_IDS.map((target) => {
      const value = matrix[source]?.[target] ?? null; const reason = value === null && row ? unavailableReason(row, target) : "";
      return `<div class="matrix-cell" data-null="${value === null}" data-own="${source === target}"><span>${source === target ? "OWN LOSS" : "SAME-WORLD CROSS-SCORE"}</span><strong>${score(value)}</strong><small>${value === null ? esc(reason) : esc(labels[target].formula)}</small></div>`;
    }).join("")}`;
  }).join("")}`;
}

function renderFailures(): void {
  const failures: Array<{ arm: ObjectiveId; row: StructuralRow; type: string; detail: string }> = [];
  for (const objective of OBJECTIVE_IDS) for (const row of report.arms[objective].rows) {
    if (row.status !== "complete") failures.push({ arm: objective, row, type: row.status, detail: record(row as Row).generation_error?.message ?? "No complete native observation; loss remains null." });
    if (row.status === "complete") for (const target of OBJECTIVE_IDS) if (row.cross_objective_losses[target] === null) failures.push({ arm: objective, row, type: "cross-score-unavailable", detail: unavailableReason(row, target) });
  }
  el("failure-dock").innerHTML = failures.length ? failures.map((failure, index) => `<article data-type="${failure.type}"><i>${String(index + 1).padStart(2, "0")}</i><div><span>${labels[failure.arm].short} · G${failure.row.generation}</span><h3>${failure.type.replaceAll("-", " ").toUpperCase()}</h3><p>${esc(failure.detail)}</p><b>NUMERICAL LOSS: ${failure.type === "cross-score-unavailable" ? "OTHER CELL NULL" : "NULL / EXCLUDED FROM SELECTION"}</b></div></article>`).join("") : `<p class="empty-dock">No technical or metric-missingness record in this audit. This does not establish scientific benefit.</p>`;
}

function renderProvenance(): void {
  const values = [
    ["EVIDENCE CLASS", report.classification], ["AUDIT CONTENT SHA256", report.content_sha256], ["RAW INVENTORY SHA256", report.raw_inventory_sha256],
    ["FROZEN SOURCE COMMIT", report.source_commit], ["RAW FILES", report.raw_file_count], ["COMPLETE NATIVE WORLDS", `${report.completed_physical_worlds} / 8`],
    ["HELD-OUT METRICS", report.held_out_metrics.status], ["PROMOTION POLICY", report.promotion_policy.status],
  ];
  el("provenance").innerHTML = values.map(([term, value]) => `<div><dt>${term}</dt><dd>${esc(value)}</dd></div>`).join("");
  el("raw-row").textContent = JSON.stringify(selected(), null, 2);
  el("footer-source").textContent = `${mode.toUpperCase()} // ${short(report.content_sha256, 24)} // SOURCE ${short(report.source_commit, 12)}`;
}

function renderAll(): void { renderPaths(); renderGraph(); renderCrossscores(); renderFailures(); renderProvenance(); }

async function loadActual(): Promise<ObjectiveStructureReport> {
  const fileName = "native-objective-structure-v8-a2.json";
  const [reportResponse, receiptResponse] = await Promise.all([fetch(`./data/${fileName}`, { cache: "no-store" }), fetch("./data/native-objective-structure-v8-a2.ui-export.json", { cache: "no-store" })]);
  if (!reportResponse.ok || !receiptResponse.ok) throw new Error(`audited export unavailable (${reportResponse.status}/${receiptResponse.status})`);
  if (!reportResponse.headers.get("content-type")?.includes("application/json") || !receiptResponse.headers.get("content-type")?.includes("application/json")) throw new Error("audited export unavailable (server returned a non-JSON fallback)");
  const text = await reportResponse.text(); const parsed = parseObjectiveStructureReport(JSON.parse(text), "actual");
  const receipt = parseObjectiveStructureReceipt(await receiptResponse.json(), parsed, fileName);
  if (await sha256Text(text) !== receipt.report_file_sha256) throw new Error("Audited report bytes differ from the UI export receipt");
  return parsed;
}

async function boot(): Promise<void> {
  const fixtureRequested = new URLSearchParams(location.search).get("fixture") === "objective-v8";
  mode = fixtureRequested ? "fixture" : "actual";
  try {
    report = fixtureRequested ? await verifyFixtureReport(await objectiveStructureFixture()) : await loadActual();
    const first = report.arms[selectedArm].rows.findIndex((row) => row.status === "complete"); selectedIndex = first < 0 ? 0 : first;
    el("truth-badge").textContent = mode === "fixture" ? "LABELLED UI FIXTURE" : "AUDITED ACTUAL DEVELOPMENT";
    el("truth-badge").setAttribute("data-mode", mode);
    el("evidence").removeAttribute("hidden"); renderAll();
    const focus = new URLSearchParams(location.search).get("focus");
    if (focus === "graph" || focus === "crossscore") document.body.dataset.focus = focus;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (!fixtureRequested && message.includes("unavailable")) { el("unavailable-message").textContent = message; el("unavailable").removeAttribute("hidden"); return; }
    el("fatal-error").textContent = `OBJECTIVE-STRUCTURE CONTRACT REJECTED\n${message}`; el("fatal-error").removeAttribute("hidden");
  }
}

void boot();
