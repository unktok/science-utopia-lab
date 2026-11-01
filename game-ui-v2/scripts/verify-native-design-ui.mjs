// Deterministic local Chrome QA. Native API responses below are explicit fixtures;
// this script never fulfills or triggers POST /jobs and therefore cannot start inference.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const target = (await (await fetch('http://127.0.0.1:9341/json/list')).json()).find(item => item.type === 'page');
assert(target, 'No local browser target');
const ws = new WebSocket(target.webSocketDebuggerUrl), pending = new Map(), errors = [], apiRequests = [];
await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }); });
let sequence = 0;
const send = (method, params = {}) => new Promise((resolve, reject) => { const id = ++sequence; pending.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params })); });
const fixture = value => Buffer.from(JSON.stringify(value)).toString('base64');
ws.addEventListener('message', ({ data }) => {
  const message = JSON.parse(String(data));
  if (message.id) { const waiter = pending.get(message.id); pending.delete(message.id); if (message.error) waiter.reject(new Error(JSON.stringify(message.error))); else waiter.resolve(message.result); }
  if (message.method === 'Runtime.exceptionThrown') errors.push(message.params);
  if (message.method === 'Fetch.requestPaused') {
    const { requestId, request } = message.params; apiRequests.push(`${request.method} ${new URL(request.url).pathname}`);
    const pathname = new URL(request.url).pathname;
    if (pathname === '/native-api/session' && request.method === 'GET') void send('Fetch.fulfillRequest', { requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }], body: fixture({ token: 'browser-fixture-token', source_commit: 'f'.repeat(40) }) });
    else if (pathname === '/native-api/validate' && request.method === 'POST') void send('Fetch.fulfillRequest', { requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }], body: fixture({ candidate_fingerprint: '0123456789abcdef'.repeat(4), fixture: true }) });
    else void send('Fetch.fulfillRequest', { requestId, responseCode: 409, responseHeaders: [{ name: 'Content-Type', value: 'text/plain' }], body: Buffer.from('Fixture blocks all execution endpoints').toString('base64') });
  }
});
async function evaluate(expression) { const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails)); return result.result.value; }
const until = expression => evaluate(`new Promise((resolve,reject)=>{const start=Date.now();function check(){if(${expression})return resolve(true);if(Date.now()-start>15000)return reject(new Error('UI timeout: '+document.getElementById('graph-local-check')?.textContent));setTimeout(check,80)}check()})`);
const output = path.resolve(process.argv[2] || '../research/figures/native-design-ui-v4');
await mkdir(output, { recursive: true });
try {
  await send('Runtime.enable'); await send('Page.enable'); await send('Fetch.enable', { patterns: [{ urlPattern: '*://127.0.0.1:4189/native-api/*', requestStage: 'Request' }] });
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'http://127.0.0.1:4189/native.html' });
  await until(`document.getElementById('status')?.textContent.includes('HASH VERIFIED')`);
  await evaluate(`document.getElementById('design-console').open=true`);
  await until(`document.querySelectorAll('[data-author-node]').length===15 && document.getElementById('design-service')?.textContent.includes('LOCAL QUEUE')`);
  const initial = await evaluate(`({nodes:document.querySelectorAll('[data-author-node]').length,wires:document.querySelectorAll('[data-edit-wire]').length,precheck:document.getElementById('graph-local-check').textContent,json:JSON.parse(document.getElementById('design-system').value),overflow:document.documentElement.scrollWidth>innerWidth})`);
  assert.equal(initial.nodes, 15); assert.equal(initial.wires, 18); assert(initial.precheck.includes('LOCAL PRECHECK PASS')); assert.equal(initial.json.mechanisms.length, 15); assert.equal(initial.overflow, false);
  await evaluate(`(()=>{const consent=document.getElementById('design-consent');consent.checked=true;consent.dispatchEvent(new Event('change'));document.getElementById('graph-add-node').click()})()`);
  assert.equal(await evaluate(`document.getElementById('design-consent').checked`), false, 'Any graph mutation must invalidate consent');
  assert.equal(await evaluate(`document.querySelectorAll('[data-author-node]').length`), 16);
  await evaluate(`document.querySelector('[data-edit-wire="0"]').click();document.getElementById('wire-latency').value='1';document.getElementById('wire-commit').click()`);
  assert.equal(await evaluate(`JSON.parse(document.getElementById('design-system').value).connections[0].latency`), 1);
  await evaluate(`document.getElementById('graph-undo').click()`); assert.equal(await evaluate(`JSON.parse(document.getElementById('design-system').value).connections[0].latency`), 0);
  await evaluate(`document.getElementById('graph-redo').click()`); assert.equal(await evaluate(`JSON.parse(document.getElementById('design-system').value).connections[0].latency`), 1);
  await evaluate(`document.getElementById('design-validate').click()`);
  await until(`document.getElementById('design-validation')?.textContent.includes('STRUCTURALLY VALID')`);
  assert.equal(await evaluate(`document.getElementById('design-submit').disabled`), true, 'Validation alone cannot authorize execution');
  await evaluate(`document.getElementById('design-console').scrollIntoView({block:'start'})`);
  await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: await evaluate('scrollY'), width: 1440, height: 1100, scale: 1 }, captureBeyondViewport: true }).then(result => writeFile(path.join(output, 'native-visual-authoring-desktop.png'), Buffer.from(result.data, 'base64')));
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await evaluate(`document.getElementById('design-console').scrollIntoView({block:'start'})`);
  assert.equal(await evaluate('document.documentElement.scrollWidth>innerWidth'), false);
  await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: await evaluate('scrollY'), width: 390, height: 844, scale: 1 }, captureBeyondViewport: true }).then(result => writeFile(path.join(output, 'native-visual-authoring-mobile.png'), Buffer.from(result.data, 'base64')));
  assert(!apiRequests.some(value => value === 'POST /native-api/jobs'), 'Browser QA must not submit a native job');
  assert.deepEqual(apiRequests.sort(), ['GET /native-api/session', 'POST /native-api/validate'].sort());
  assert.equal(errors.length, 0, JSON.stringify(errors));
  const report = { fixture_api: true, actual_inference_started: false, initial: { nodes: initial.nodes, wires: initial.wires }, edit: { nodes: 16, rewired_latency: 1, undo_redo: true, consent_invalidated: true }, authoritative_validation_fixture: true, submit_remained_disabled: true, mobile_overflow: false, api_requests: apiRequests, errors, screenshots: ['native-visual-authoring-desktop.png', 'native-visual-authoring-mobile.png'] };
  await writeFile(path.join(output, 'browser-verification.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} finally { ws.close(); }
