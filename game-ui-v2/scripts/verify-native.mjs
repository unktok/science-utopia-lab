// Local Chrome CDP QA; no browser installation or external service.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const target = (await (await fetch('http://127.0.0.1:9341/json/list')).json()).find(t => t.type === 'page');
assert(target, 'No local browser target');
const ws = new WebSocket(target.webSocketDebuggerUrl), pending = new Map(), errors = [];
await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }); });
let id = 0;
ws.addEventListener('message', ({ data }) => {
  const message = JSON.parse(String(data));
  if (message.id) { const waiter = pending.get(message.id); pending.delete(message.id); if (message.error) waiter.reject(new Error(JSON.stringify(message.error))); else waiter.resolve(message.result); }
  if (message.method === 'Runtime.exceptionThrown') errors.push(message.params);
  if (message.method === 'Network.loadingFailed' && !message.params.canceled) errors.push(message.params);
});
const send = (method, params = {}) => new Promise((resolve, reject) => { const next = ++id; pending.set(next, { resolve, reject }); ws.send(JSON.stringify({ id: next, method, params })); });
async function evaluate(expression) { const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails)); return result.result.value; }
const output = path.resolve(process.argv[2] || '../outputs/native-design-ui');
await mkdir(output, { recursive: true });
try {
  await send('Runtime.enable'); await send('Network.enable'); await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1250, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'http://127.0.0.1:4189/native.html' });
  await evaluate(`new Promise((resolve,reject)=>{const start=Date.now();const check=()=>{const status=document.getElementById('status')?.textContent||'';if(status.includes('HASH VERIFIED'))return resolve(status);if(status.includes('FAILED'))return reject(new Error(document.getElementById('error')?.textContent));if(Date.now()-start>15000)return reject(new Error('Native evidence timeout'));setTimeout(check,100)};check()})`);
  const initial = await evaluate(`({candidates:document.getElementById('candidate').options.length,actors:document.querySelectorAll('.native-actor').length,nodes:document.querySelectorAll('[data-native-node]').length,overflow:document.documentElement.scrollWidth>innerWidth})`);
  assert.equal(initial.candidates, 2); assert.equal(initial.actors, 5); assert.equal(initial.overflow, false);
  await evaluate(`document.getElementById('candidate').value='1';document.getElementById('candidate').dispatchEvent(new Event('change'))`);
  await evaluate(`document.querySelector('[data-native-node="deliberation-assembly"]')?.click() || document.querySelector('[data-native-node="addressed-selection"]')?.click()`);
  const selected = await evaluate(`({name:document.getElementById('node-name').textContent,source:document.getElementById('native-source').textContent,loss:document.getElementById('native-metrics').textContent,nodes:document.querySelectorAll('[data-native-node]').length,events:document.getElementById('native-events').textContent})`);
  assert(selected.source.includes('def step(context)') || selected.source.includes('tensor-program.v1'));
  assert(selected.events.length > 50); assert(selected.loss.includes('ACTUAL NATIVE LOSS'));
  await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true }).then(s => writeFile(path.join(output, 'native-foundry-desktop.png'), Buffer.from(s.data, 'base64')));
  await evaluate(`document.getElementById('step').click()`);
  assert((await evaluate(`document.querySelector('[data-native-node][aria-pressed="true"]')?.dataset.nativeNode`)));
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  const mobileOverflow = await evaluate('document.documentElement.scrollWidth>innerWidth'); assert.equal(mobileOverflow, false);
  await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true }).then(s => writeFile(path.join(output, 'native-foundry-mobile.png'), Buffer.from(s.data, 'base64')));
  assert.equal(errors.length, 0, JSON.stringify(errors));
  const report = { initial, selected: { name: selected.name, nodes: selected.nodes, sourceCharacters: selected.source.length }, mobileOverflow, errors,
    screenshots: ['native-foundry-desktop.png', 'native-foundry-mobile.png'] };
  await writeFile(path.join(output, 'browser-verification.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} finally { ws.close(); }
