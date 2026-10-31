// Verify the produced artifact through a real local Chrome instance.
// Start Chrome with --headless=new --remote-debugging-port=9338 and an isolated
// temporary user-data-dir, and Vite at 127.0.0.1:4188 before invoking this file.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const targets = await (await fetch(`${process.env.CHROME_CDP_URL || "http://127.0.0.1:9338"}/json/list`)).json();
const target = targets.find((item) => item.type === "page");
assert(target, "No browser target");
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});
let sequence = 0;
const pending = new Map();
const errors = [];
socket.addEventListener("message", ({ data }) => {
  const message = JSON.parse(String(data));
  if (message.id) {
    const waiter = pending.get(message.id);
    if (!waiter) return;
    pending.delete(message.id);
    if (message.error) waiter.reject(new Error(JSON.stringify(message.error)));
    else waiter.resolve(message.result);
  }
  if (message.method === "Runtime.exceptionThrown") errors.push(message.params);
  if (message.method === "Network.loadingFailed" && !message.params.canceled) errors.push(message.params);
});
function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++sequence;
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const value = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (value.exceptionDetails) throw new Error(JSON.stringify(value.exceptionDetails));
  return value.result.value;
}
const output = path.resolve(process.argv[2] || "../output/generative-lab-browser");
await mkdir(output, { recursive: true });
try {
  await send("Runtime.enable");
  await send("Network.enable");
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1350, deviceScaleFactor: 1, mobile: false });
  await send("Page.navigate", { url: `${process.env.UI_BASE_URL || "http://127.0.0.1:4188"}/generative.html` });
  await evaluate(`new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      const status = document.getElementById('status')?.textContent || '';
      if (status.includes('VERIFIED')) return resolve(status);
      if (status.includes('FAILED')) return reject(new Error(document.getElementById('error').textContent));
      if (Date.now()-start > 10000) return reject(new Error('Evidence did not load'));
      setTimeout(check, 50);
    }; check();
  })`);
  const initial = await evaluate(`({status:document.getElementById('status').textContent,
    arms:document.getElementById('arm').options.length,
    systems:document.getElementById('system').options.length,
    nodes:document.querySelectorAll('[data-node]').length,
    agents:document.querySelectorAll('.agent').length,
    errorHidden:document.getElementById('error').hidden})`);
  assert.equal(initial.arms, 2);
  assert.equal(initial.systems, 4);
  assert.equal(initial.agents, 6);
  assert.equal(initial.errorHidden, true);
  assert.equal(await evaluate('document.documentElement.lang'), 'en');
  assert(!/[\u3040-\u30ff\u3400-\u9fff]/u.test(await evaluate('document.body.innerText')), 'Non-English default UI copy');
  assert.equal(await evaluate('document.getElementById("load").getBoundingClientRect().width'), 1);
  await evaluate(`document.getElementById('system').value='3';document.getElementById('system').dispatchEvent(new Event('change'))`);
  const productionRule = await evaluate(`document.getElementById('rule').textContent`);
  assert(productionRule.includes("out = tanh("));
  const production = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
  await writeFile(path.join(output, "generative-lab-production.png"), Buffer.from(production.data, "base64"));
  await evaluate(`document.getElementById('arm').value='1';document.getElementById('arm').dispatchEvent(new Event('change'));document.getElementById('system').value='3';document.getElementById('system').dispatchEvent(new Event('change'));document.getElementById('period').value='2';document.getElementById('period').dispatchEvent(new Event('input'))`);
  const burden = await evaluate(`({period:document.getElementById('period-label').textContent,
    fingerprint:document.getElementById('fingerprint').textContent,
    agents:document.querySelectorAll('.agent').length,
    nodes:document.querySelectorAll('[data-node]').length})`);
  assert.equal(burden.period, "T+3");
  assert.equal(burden.agents, 6);
  assert(!/[\u3040-\u30ff\u3400-\u9fff]/u.test(await evaluate('document.body.innerText')));
  const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
  await writeFile(path.join(output, "generative-lab-burden.png"), Buffer.from(shot.data, "base64"));
  await evaluate(`document.querySelector('[data-node]').dispatchEvent(new MouseEvent('click',{bubbles:true}))`);
  assert((await evaluate(`document.getElementById('ast').textContent`)).includes('"program"'));
  await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  const overflow = await evaluate(`document.documentElement.scrollWidth>window.innerWidth`);
  assert.equal(overflow, false, "Mobile layout overflows");
  assert.equal(errors.length, 0, JSON.stringify(errors));
  const evidence = { initial, burden, browserErrors: errors, mobileOverflow: overflow,
    screenshots: ["generative-lab-production.png", "generative-lab-burden.png"] };
  await writeFile(path.join(output, "verification.json"), JSON.stringify(evidence, null, 2) + "\n");
  console.log(JSON.stringify(evidence, null, 2));
} finally {
  socket.close();
}
