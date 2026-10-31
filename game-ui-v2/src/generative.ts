import { parseGenerativeLab, type GenerativeLab, type ProgramNode } from "./generativeContract";
import "./generative.css";

const get = <T extends HTMLElement>(id: string): T => document.getElementById(id) as T;
const armSelect = get<HTMLSelectElement>("arm");
const systemSelect = get<HTMLSelectElement>("system");
const periodSelect = get<HTMLInputElement>("period");
const escape = (value: unknown): string => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const at = <T>(values: readonly T[], index: number): T => {
  const value = values[index];
  if (value === undefined) throw new Error(`Missing observed row ${index}`);
  return value;
};
let lab: GenerativeLab;
let selectedNode = "";
let timer: ReturnType<typeof setInterval> | undefined;

function expression(value: unknown): string {
  const row = value as Record<string, unknown>;
  if ("input" in row) return String(row.input);
  if ("state" in row) return `state.${row.state}`;
  if ("param" in row) return `θ.${row.param}`;
  if ("const" in row) return String(row.const);
  if (Array.isArray(row.args)) return `${row.op}(${row.args.map(expression).join(", ")})`;
  return JSON.stringify(value);
}

function chart(): void {
  const arm = at(lab.arms, Number(armSelect.value));
  const series = [arm.gradient_trace.map((row) => row.relaxed_loss), arm.blackbox_path.flatMap((row) => row.loss === null ? [] : [row.loss])];
  const all = series.flat();
  const low = Math.min(...all), high = Math.max(...all), spread = high - low || 1;
  const lines = series.map((values, index) => `<polyline fill="none" stroke="${index ? "#ec89d9" : "#61e4d7"}" stroke-width="2.5" points="${values.map((value, i) => `${40 + i / Math.max(1, values.length - 1) * 540},${140 - (value - low) / spread * 110}`).join(" ")}" />`).join("");
  get("chart").innerHTML = `<path d="M40 20V145H585" fill="none" stroke="#2b3f53"/><text x="0" y="25" fill="#a4b6c7" font-size="12">${high.toFixed(3)}</text><text x="0" y="145" fill="#a4b6c7" font-size="12">${low.toFixed(3)}</text>${lines}`;
  get("audit").textContent = `${arm.gradient_audit.records.length} gradient groups · central-difference audit: ${arm.gradient_audit.all_pass ? "PASS" : "FAIL"} · projection gap ${arm.projection_gap.toFixed(5)}`;
}

function inspector(node: ProgramNode): void {
  const system = at(at(lab.arms, Number(armSelect.value)).systems, Number(systemSelect.value));
  const frame = at(system.frames, Number(periodSelect.value));
  get("node-name").textContent = node.parameters.label;
  get("node-meta").textContent = `${node.family.toUpperCase()} / ${node.mechanism_id}`;
  get("rule").textContent = `out = tanh(${expression(node.parameters.program.output)})`;
  get("ast").textContent = JSON.stringify(node.parameters, null, 2);
  get("signal").textContent = `INPUT SIGNAL  ${frame.signals[node.mechanism_id]!.map((v) => v.toFixed(3)).join(" · ")}\nOUTPUT  ${frame.mechanisms[node.mechanism_id]!.map((v) => v.toFixed(3)).join(" · ")}`;
}

function render(): void {
  const arm = at(lab.arms, Number(armSelect.value));
  const system = at(arm.systems, Number(systemSelect.value));
  const spec = system.system_spec;
  periodSelect.max = String(system.frames.length - 1);
  if (Number(periodSelect.value) >= system.frames.length) periodSelect.value = "0";
  const frame = at(system.frames, Number(periodSelect.value));
  get("period-label").textContent = `T+${frame.period + 1}`;
  get("graph-count").textContent = `${spec.mechanisms.length} NODES / ${spec.connections.length} EDGES`;
  const positions = new Map(spec.mechanisms.map((node, index) => [node.mechanism_id, {
    x: 450 + Math.cos(index / spec.mechanisms.length * Math.PI * 2 - Math.PI / 2) * 285,
    y: 220 + Math.sin(index / spec.mechanisms.length * Math.PI * 2 - Math.PI / 2) * 155,
  }]));
  const edges = spec.connections.map((edge) => {
    const from = positions.get(edge.source_mechanism)!, to = positions.get(edge.target_mechanism)!;
    return `<g><line x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" class="edge ${edge.latency ? "delayed" : ""}" marker-end="url(#arrow)"/><text x="${(from.x + to.x) / 2}" y="${(from.y + to.y) / 2 - 6}" class="delay">τ=${edge.latency}</text></g>`;
  }).join("");
  const asset = (family: string): string => family === "research" ? "institution-lab.svg" : ({ evaluation: "system-evaluation.svg", publication: "system-publication.svg", funding: "institution-funding.svg" }[family] || "system-government.svg");
  const nodes = spec.mechanisms.map((node) => {
    const p = positions.get(node.mechanism_id)!;
    const rank = frame.execution_order.indexOf(node.mechanism_id) + 1;
    return `<g class="node" role="button" tabindex="0" aria-label="${escape(node.parameters.label)}" data-node="${escape(node.mechanism_id)}" transform="translate(${p.x},${p.y})"><rect x="-82" y="-47" width="164" height="106" rx="2"/><image href="/assets/noctiluca/production/${asset(node.family)}" x="-30" y="-39" width="60" height="60"/><text class="rank" x="-68" y="-23">0${rank}</text><text y="39">${escape(node.parameters.label.slice(0, 24))}</text><text class="node-value" y="53">${(frame.mechanisms[node.mechanism_id]!.reduce((a, b) => a + b, 0) / frame.world.quality.length).toFixed(3)}</text></g>`;
  }).join("");
  get("graph").innerHTML = `<svg viewBox="0 0 900 450"><defs><marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0 0L6 3L0 6" fill="#617c98"/></marker></defs>${edges}${nodes}</svg>`;
  get("graph").querySelectorAll<SVGGElement>("[data-node]").forEach((element) => {
    const activate = (): void => { selectedNode = element.dataset.node!; inspector(spec.mechanisms.find((node) => node.mechanism_id === selectedNode)!); };
    element.addEventListener("click", activate);
    element.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); activate(); } });
  });
  get("agents").innerHTML = frame.world.quality.map((quality, index) => `<article class="agent"><i aria-hidden="true" style="--coat:${["#6cd9c8", "#bf94eb", "#e3b46c"][index % 3]}"></i><b>R-${String(index + 1).padStart(2, "0")}</b><span>QUALITY ${quality.toFixed(3)}</span><span>KNOWLEDGE ${at(frame.world.knowledge, index).toFixed(3)}</span><meter min="0" max="1" value="${frame.world.knowledge[index]}" aria-label="Researcher ${index + 1} knowledge"></meter></article>`).join("");
  get("metrics").innerHTML = `<div class="primary"><small>OPTIMIZED LOSS</small><b>${system.loss.toFixed(5)}</b></div>${Object.entries(system.metrics).map(([key, value]) => `<div><small>${escape(key.toUpperCase())}</small><b>${value.toFixed(4)}</b></div>`).join("")}`;
  get("fingerprint").textContent = `SYSTEM ${system.system_fingerprint}`;
  get("events").textContent = system.events.filter((event) => event.year === frame.period).map((event) => JSON.stringify(event, null, 2)).join("\n");
  const node = spec.mechanisms.find((item) => item.mechanism_id === selectedNode) || spec.mechanisms[0];
  if (node) {
    selectedNode = node.mechanism_id;
    inspector(node);
  } else {
    get("node-name").textContent = "No institutional mechanism";
    get("node-meta").textContent = "The background numeric world still evolves.";
    get("rule").textContent = "";
    get("ast").textContent = "{}";
    get("signal").textContent = "";
  }
  chart();
}

function chooseArm(): void {
  systemSelect.replaceChildren(...at(lab.arms, Number(armSelect.value)).systems.map((system, index) => new Option(system.label, String(index))));
  periodSelect.value = "0";
  render();
}

async function load(value: unknown): Promise<void> {
  lab = await parseGenerativeLab(value);
  get("error").hidden = true;
  get("status").textContent = lab.source.dirty_development ? "LOCAL DEVELOPMENT RUN" : "CHECKSUM VERIFIED / NUMERIC EXECUTION";
  get("boundary").textContent = lab.qwen_role === "none"
    ? "生成規則を実行する数値世界。Qwenはこのrunで使っていません。"
    : "Qwen3-8Bが提案した規則・研究者特徴を凍結し、数値世界で実行。微分は数値世界全体を通り、Qwenの文章生成には通りません。";
  get("source").textContent = `SOURCE ${lab.source.commit.slice(0, 12)} · numeric miniature evidence`;
  armSelect.replaceChildren(...lab.arms.map((arm, index) => new Option(arm.objective === "production" ? "研究生産を最大化" : "制度負担を最小化", String(index))));
  chooseArm();
}
function failure(error: unknown): void {
  get("status").textContent = "EVIDENCE LOAD FAILED";
  get("error").hidden = false;
  get("error").textContent = String(error);
}
armSelect.addEventListener("change", chooseArm);
systemSelect.addEventListener("change", render);
periodSelect.addEventListener("input", render);
get("play").addEventListener("click", () => {
  if (timer) { clearInterval(timer); timer = undefined; get("play").textContent = "▶ REPLAY"; return; }
  get("play").textContent = "Ⅱ PAUSE";
  timer = setInterval(() => { periodSelect.value = String((Number(periodSelect.value) + 1) % (Number(periodSelect.max) + 1)); render(); }, 1600);
});
get<HTMLInputElement>("load").addEventListener("change", async (event) => {
  try { const file = (event.target as HTMLInputElement).files?.[0]; if (file) await load(JSON.parse(await file.text())); } catch (error) { failure(error); }
});
fetch("./data/generative-lab-v1.json").then((response) => { if (!response.ok) throw new Error("No lab run loaded. Use LOAD RUN to select viewer.json."); return response.json(); }).then(load).catch(failure);
