// Local-only CDP QA over an already-running Vite preview and clean Chrome.
// It reads actual exported evidence; it starts no model, experiment, or worker.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const cdp = process.env.CHROME_CDP_URL || "http://127.0.0.1:9352";
const base = process.env.UI_BASE_URL || "http://127.0.0.1:4193";
const output = path.resolve(process.argv[2] || "screenshots");
await mkdir(output, { recursive: true });
const targets = await (await fetch(`${cdp}/json/list`)).json();
const target = targets.find((item) => item.type === "page");
assert(target, "No local browser target");
const socket = new WebSocket(target.webSocketDebuggerUrl), pending = new Map(), browserErrors = [];
await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
let sequence = 0;
socket.addEventListener("message", ({ data }) => {
  const message = JSON.parse(String(data));
  if (message.id) { const waiter = pending.get(message.id); pending.delete(message.id); message.error ? waiter.reject(new Error(JSON.stringify(message.error))) : waiter.resolve(message.result); }
  if (message.method === "Runtime.exceptionThrown") browserErrors.push(message.params);
  if (message.method === "Network.loadingFailed" && !message.params.canceled) browserErrors.push(message.params);
});
const send = (method, params = {}) => new Promise((resolve, reject) => { const id = ++sequence; pending.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params })); });
async function evaluate(expression) { const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails)); return result.result.value; }
async function capture(name, selector) {
  const box = await evaluate(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});const r=e.getBoundingClientRect();return{x:Math.max(0,r.left+scrollX-8),y:Math.max(0,r.top+scrollY-8),width:Math.min(document.documentElement.scrollWidth,r.width+16),height:r.height+16}})()`);
  const image = await send("Page.captureScreenshot", { format: "png", clip: { ...box, scale: 1 }, captureBeyondViewport: true });
  await writeFile(path.join(output, name), Buffer.from(image.data, "base64"));
}
try {
  await send("Runtime.enable"); await send("Network.enable"); await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1600, height: 1100, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: `${base}/open-evidence.html` });
  await evaluate(`new Promise((resolve,reject)=>{let n=0;const check=()=>{if(document.querySelectorAll('[data-observation]').length===4)return resolve(true);if(!document.getElementById('fatal-error')?.hidden)return reject(new Error(document.getElementById('fatal-error').textContent));if(n++>200)return reject(new Error('actual evidence timeout'));setTimeout(check,50)};check()})`);
  const overview = await evaluate(`({lang:document.documentElement.lang,truth:document.getElementById('truth-badge').textContent,campaign:document.getElementById('campaign-meta').textContent,losses:[...document.querySelectorAll('[data-observation] strong')].map(e=>e.textContent),audit:document.getElementById('observation-audit').textContent,actors:document.querySelectorAll('[data-registry-kind="actor"]').length,artifacts:document.querySelectorAll('[data-registry-kind="artifact"]').length,process:[...document.querySelectorAll('.process-loom article p')].map(e=>e.textContent),nodes:document.querySelectorAll('[data-node-index]').length,edges:document.querySelectorAll('.graph-edges p').length,coverage:document.getElementById('coverage-panel').textContent,backward:document.getElementById('backward-panel').textContent,boundary:document.querySelector('.derivative-grid aside').textContent,fixture:document.body.innerText.includes('SYNTHETIC UI FIXTURE'),japanese:/[\\u3040-\\u30ff\\u3400-\\u9fff]/u.test(document.body.innerText),overflow:document.documentElement.scrollWidth>innerWidth})`);
  assert.equal(overview.lang, "en"); assert.equal(overview.truth, "HASH-VERIFIED ACTUAL EVIDENCE");
  assert(overview.campaign.includes("COMPLETE // 4 COMPLETE WORLDS // 342 PHYSICAL QWEN REPLIES"));
  assert.deepEqual(overview.losses, ["LOSS -1.2", "LOSS -0.2", "LOSS -0.8", "LOSS -0.2"]);
  assert(overview.audit.includes("INDEPENDENT ENDPOINT RECOMPUTATION")); assert(overview.audit.includes("PROCESS INVOCATIONS"));
  assert.equal(overview.actors, 1); assert.equal(overview.artifacts, 2); assert.equal(overview.nodes, 19); assert.equal(overview.edges, 27);
  assert.deepEqual(overview.process.map((text) => text.match(/year (\d)/)?.[1]), ["1", "1", "2", "2"]);
  assert(overview.coverage.includes("REPRESENTED TENSOR NODES2")); assert(overview.backward.includes("PASSED"));
  assert(overview.boundary.includes("not the campaign's joint engineering loss")); assert(overview.boundary.includes("causal institutional benefit"));
  assert.equal(overview.fixture, false); assert.equal(overview.japanese, false); assert.equal(overview.overflow, false);
  const full = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
  await writeFile(path.join(output, "noctiluca-open-native-v7-actual-full.png"), Buffer.from(full.data, "base64"));
  await capture("noctiluca-open-native-v7-observations.png", ".observation-board");
  await capture("noctiluca-open-native-v7-domain.png", ".domain-board");
  await capture("noctiluca-open-native-v7-process.png", ".process-board");
  await capture("noctiluca-open-native-v7-system.png", ".system-board");
  await capture("noctiluca-open-native-v7-derivative-boundary.png", ".derivative-board");
  for (let index = 0; index < 4; index += 1) { await evaluate(`document.querySelector('[data-observation="${index}"]').click()`); const label = await evaluate(`document.querySelector('[data-observation="${index}"] strong').textContent`); assert.equal(label, overview.losses[index]); }
  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await send("Page.navigate", { url: `${base}/open-evidence.html` });
  await evaluate(`new Promise(resolve=>{const check=()=>document.querySelectorAll('[data-observation]').length===4?resolve(true):setTimeout(check,50);check()})`);
  const mobileOverflow = await evaluate("document.documentElement.scrollWidth>innerWidth"); assert.equal(mobileOverflow, false);
  assert.equal(browserErrors.length, 0, JSON.stringify(browserErrors));
  const report = { source: "independently audited native-open-integrated-v7-a2 actual export", actual_experiment_started_by_ui_qa: false, overview, mobile_overflow: mobileOverflow, browser_errors: browserErrors, screenshots: ["noctiluca-open-native-v7-actual-full.png", "noctiluca-open-native-v7-observations.png", "noctiluca-open-native-v7-domain.png", "noctiluca-open-native-v7-process.png", "noctiluca-open-native-v7-system.png", "noctiluca-open-native-v7-derivative-boundary.png"] };
  await writeFile(path.join(output, "noctiluca-open-native-v7-qa.json"), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));
} finally { socket.close(); }
