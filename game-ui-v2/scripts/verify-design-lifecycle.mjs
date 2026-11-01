// Local-only Chrome CDP QA. No experiment, inference, or external service is called.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const cdp = process.env.CHROME_CDP_URL || "http://127.0.0.1:9347";
const base = process.env.UI_BASE_URL || "http://127.0.0.1:4197";
const targets = await (await fetch(`${cdp}/json/list`)).json();
const target = targets.find((item) => item.type === "page");
assert(target, "No local browser target");
const socket = new WebSocket(target.webSocketDebuggerUrl), pending = new Map(), browserErrors = [], networkRequests = [];
await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
let sequence = 0;
socket.addEventListener("message", ({ data }) => {
  const message = JSON.parse(String(data));
  if (message.id) { const waiter = pending.get(message.id); pending.delete(message.id); if (message.error) waiter.reject(new Error(JSON.stringify(message.error))); else waiter.resolve(message.result); }
  if (message.method === "Runtime.exceptionThrown") browserErrors.push(message.params);
  if (message.method === "Network.loadingFailed" && !message.params.canceled) browserErrors.push(message.params);
  if (message.method === "Network.requestWillBeSent") networkRequests.push({ url: message.params.request.url, method: message.params.request.method });
});
const send = (method, params = {}) => new Promise((resolve, reject) => { const id = ++sequence; pending.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params })); });
async function evaluate(expression) { const result = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails)); return result.result.value; }
const output = path.resolve(process.argv[2] || "screenshots");
await mkdir(output, { recursive: true });
try {
  await send("Runtime.enable"); await send("Network.enable"); await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: `${base}/lifecycle.html` });
  await evaluate(`new Promise((resolve,reject)=>{const start=Date.now();const check=()=>{if(document.querySelectorAll('.system-station').length===3)return resolve(true);if(!document.getElementById('fatal-error')?.hidden)return reject(new Error(document.getElementById('fatal-error').textContent));if(Date.now()-start>10000)return reject(new Error('Lifecycle load timeout'));setTimeout(check,50)};check()})`);
  await evaluate(`new Promise((resolve,reject)=>{const start=Date.now();const check=()=>{const value=document.getElementById('society-truth').textContent;if(value.includes('UNAVAILABLE')||value.includes('FAILED'))return resolve(value);if(Date.now()-start>10000)return reject(new Error('Society offline boundary timeout'));setTimeout(check,50)};check()})`);
  const initial = await evaluate(`({lang:document.documentElement.lang,arms:document.querySelectorAll('[data-arm]').length,systems:document.querySelectorAll('.system-station').length,nodes:document.querySelectorAll('[data-node]').length,loss:document.getElementById('selected-loss').textContent,adoption:document.getElementById('adoption-status').textContent,confirmDisabled:document.getElementById('adoption-confirm').disabled,submitDisabled:document.getElementById('adoption-submit').disabled,liveSource:document.getElementById('society-truth').textContent,liveConfirmDisabled:document.getElementById('society-confirm').disabled,overflow:document.documentElement.scrollWidth>innerWidth})`);
  assert.equal(initial.lang, "en"); assert.equal(initial.arms, 2); assert.equal(initial.systems, 3); assert(initial.nodes >= 13); assert.equal(initial.loss, "-3");
  assert(initial.adoption.includes("UNAVAILABLE")); assert.equal(initial.confirmDisabled, true); assert.equal(initial.submitDisabled, true); assert(/UNAVAILABLE|FAILED/.test(initial.liveSource)); assert.equal(initial.liveConfirmDisabled, true); assert.equal(initial.overflow, false);
  assert(!/[\u3040-\u30ff\u3400-\u9fff]/u.test(await evaluate("document.body.innerText")), "Default UI must remain English");
  await evaluate(`document.querySelector('[data-arm="0"]').click();document.querySelector('[data-system="2"]').click()`);
  const utility = await evaluate(`({loss:document.querySelector('[data-system="2"] .station-loss').textContent,generated:document.querySelectorAll('.graph-node.generated').length,protocol:document.getElementById('protocol-diff').textContent,selection:document.getElementById('selection-reason').textContent,source:document.getElementById('node-source').textContent})`);
  assert.equal(utility.loss, "0.45"); assert.equal(utility.generated, 2); assert(utility.protocol.includes("publication-loss-offers-v1")); assert(utility.selection.includes("Station 02")); assert(utility.source.includes("def step(context)"));
  const top = await send("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 0, width: 1440, height: 1100, scale: 1 }, captureBeyondViewport: true });
  await writeFile(path.join(output, "noctiluca-design-chronicle-v5.png"), Buffer.from(top.data, "base64"));
  await evaluate(`document.querySelector('.system-bay').scrollIntoView({block:'start'})`);
  const graph = await send("Page.captureScreenshot", { format: "png", clip: { x: 0, y: await evaluate("scrollY"), width: 1440, height: 1100, scale: 1 }, captureBeyondViewport: true });
  await writeFile(path.join(output, "noctiluca-design-chronicle-two-node.png"), Buffer.from(graph.data, "base64"));
  await send("Page.navigate", { url: `${base}/lifecycle.html?society=fixture` });
  await new Promise(resolve => setTimeout(resolve, 300));
  await evaluate(`new Promise((resolve,reject)=>{const start=Date.now();const check=()=>{if(document.querySelectorAll('.interval-cell').length===2)return resolve(true);if(!document.getElementById('fatal-error')?.hidden)return reject(new Error(document.getElementById('fatal-error').textContent));if(Date.now()-start>10000)return reject(new Error('Society fixture timeout'));setTimeout(check,50)};check()})`);
  const society = await evaluate(`({truth:document.getElementById('society-truth').textContent,intervals:document.querySelectorAll('.interval-cell').length,losses:Array.from(document.querySelectorAll('.interval-cell strong'),e=>e.textContent),request:document.getElementById('society-request-id').textContent,hash:document.getElementById('society-request-hash').textContent,confirmDisabled:document.getElementById('society-confirm').disabled,consentDisabled:document.getElementById('society-consent').disabled,causal:document.querySelector('.continuity-ledger').textContent})`);
  assert.equal(society.truth, "SYNTHETIC UI FIXTURE"); assert.equal(society.intervals, 2); assert.deepEqual(society.losses, ["0.7", "0.45"]); assert(society.request.includes("eeee")); assert.equal(society.hash, "e".repeat(64)); assert.equal(society.confirmDisabled, true); assert.equal(society.consentDisabled, true); assert(society.causal.includes("NOT ESTABLISHED"));
  await evaluate(`document.getElementById('society-session').scrollIntoView({block:'start'})`);
  const societyShot = await send("Page.captureScreenshot", { format: "png", clip: { x: 0, y: await evaluate("scrollY"), width: 1440, height: 1100, scale: 1 }, captureBeyondViewport: true });
  await writeFile(path.join(output, "noctiluca-same-society-session-fixture.png"), Buffer.from(societyShot.data, "base64"));
  assert.equal(networkRequests.some(request => request.method === "POST" && request.url.includes("/native-api/society")), false, "Fixture must never authorize a worker");
  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await send("Page.navigate", { url: `${base}/lifecycle.html` });
  await evaluate(`new Promise(resolve=>{const check=()=>document.querySelectorAll('.system-station').length===3?resolve(true):setTimeout(check,50);check()})`);
  const mobileOverflow = await evaluate("document.documentElement.scrollWidth>innerWidth"); assert.equal(mobileOverflow, false);
  assert.equal(browserErrors.length, 0, JSON.stringify(browserErrors));
  const report = { actual_experiment_started: false, source: "audited v5 portable snapshot", initial, utility_two_node: utility, same_society_fixture: society, fixture_post_requests: 0, mobile_overflow: mobileOverflow, browser_errors: browserErrors, screenshots: ["noctiluca-design-chronicle-v5.png", "noctiluca-design-chronicle-two-node.png", "noctiluca-same-society-session-fixture.png"] };
  await writeFile(path.join(output, "noctiluca-design-chronicle-v5-qa.json"), `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report, null, 2));
} finally { socket.close(); }
