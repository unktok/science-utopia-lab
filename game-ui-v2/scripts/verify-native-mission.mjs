// Local Chrome QA with explicit session/validation fixtures. Execution endpoints
// are blocked: fixture responses can never become mission achievements.
import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import path from 'node:path';

const target = (await (await fetch('http://127.0.0.1:9341/json/list')).json()).find(item => item.type === 'page');
assert(target, 'No local browser target');
const ws = new WebSocket(target.webSocketDebuggerUrl), pending = new Map(), errors = [], apiRequests = [];
await new Promise((resolve, reject) => { ws.addEventListener('open', resolve, { once: true }); ws.addEventListener('error', reject, { once: true }); });
let sequence = 0;
const send = (method, params = {}) => new Promise((resolve, reject) => { const id = ++sequence; pending.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params })); });
const encoded = value => Buffer.from(JSON.stringify(value)).toString('base64');
ws.addEventListener('message', ({ data }) => {
  const message = JSON.parse(String(data));
  if (message.id) { const waiter = pending.get(message.id); pending.delete(message.id); message.error ? waiter.reject(new Error(JSON.stringify(message.error))) : waiter.resolve(message.result); }
  if (message.method === 'Runtime.exceptionThrown') errors.push(message.params);
  if (message.method === 'Fetch.requestPaused') {
    const { requestId, request } = message.params, route = `${request.method} ${new URL(request.url).pathname}`; apiRequests.push(route);
    if (route === 'GET /native-api/session') void send('Fetch.fulfillRequest', { requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }], body: encoded({ token: 'mission-browser-fixture', source_commit: 'f'.repeat(40) }) });
    else if (route === 'POST /native-api/validate') void send('Fetch.fulfillRequest', { requestId, responseCode: 200, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }], body: encoded({ candidate_fingerprint: '0123456789abcdef'.repeat(4), fixture: true }) });
    else void send('Fetch.fulfillRequest', { requestId, responseCode: 409, responseHeaders: [{ name: 'Content-Type', value: 'text/plain' }], body: Buffer.from('Browser fixture blocks job and evidence endpoints').toString('base64') });
  }
});
async function evaluate(expression) { const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails)); return result.result.value; }
const until = expression => evaluate(`new Promise((resolve,reject)=>{const start=Date.now();function check(){if(${expression})return resolve(true);if(Date.now()-start>15000)return reject(new Error('Mission UI timeout'));setTimeout(check,80)}check()})`);
const screenshots = path.resolve('screenshots');
try {
  await send('Runtime.enable'); await send('Page.enable'); await send('Fetch.enable', { patterns: [{ urlPattern: '*://127.0.0.1:4189/native-api/*', requestStage: 'Request' }] });
  await send('Page.addScriptToEvaluateOnNewDocument', { source: `localStorage.removeItem('noctiluca.native-sandbox-missions.v1');sessionStorage.removeItem('native-lab-job');` });
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'http://127.0.0.1:4189/native.html' });
  await until(`document.getElementById('status')?.textContent.includes('HASH VERIFIED')`);
  await evaluate(`document.getElementById('design-console').open=true`);
  await until(`document.getElementById('design-service')?.textContent.includes('LOCAL QUEUE') && document.getElementById('design-loss').value.includes('native-accepted-count')`);
  assert.equal(await evaluate(`document.getElementById('mission-active').hidden`), true);
  await evaluate(`document.getElementById('mission-activate').click()`);
  const first = await evaluate(`document.getElementById('mission-contract-id').textContent`); assert(first.startsWith('mission-1-'));
  assert((await evaluate(`document.getElementById('mission-history').textContent`)).includes('NO SUBMITTED TRIALS'));
  await evaluate(`(()=>{const target=document.getElementById('mission-target');target.value='-2';target.dispatchEvent(new Event('input',{bubbles:true}))})()`);
  assert((await evaluate(`document.getElementById('mission-draft-status').textContent`)).includes('DRAFT CHANGED'));
  await evaluate(`document.getElementById('mission-activate').click()`);
  const second = await evaluate(`document.getElementById('mission-contract-id').textContent`); assert(second.startsWith('mission-2-')); assert.notEqual(first, second);
  assert.equal(await evaluate(`document.getElementById('mission-archive-count').textContent`), '1');
  await evaluate(`document.getElementById('design-validate').click()`);
  await until(`document.getElementById('design-validation')?.textContent.includes('STRUCTURALLY VALID')`);
  assert.equal(await evaluate(`document.getElementById('design-submit').disabled`), true, 'Validation and a mission never replace explicit consent');
  assert.equal(await evaluate(`JSON.parse(localStorage.getItem('noctiluca.native-sandbox-missions.v1')).jobs.length`), 0);
  assert(!apiRequests.some(route => route.includes('/jobs')), 'Fixture QA must never submit or inspect a job');
  await evaluate(`document.querySelector('.mission-contract').scrollIntoView({block:'start'})`);
  await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: await evaluate('scrollY'), width: 1440, height: 1000, scale: 1 }, captureBeyondViewport: true }).then(result => writeFile(path.join(screenshots, 'noctiluca-native-sandbox-mission-desktop.png'), Buffer.from(result.data, 'base64')));
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await evaluate(`document.querySelector('.mission-contract').scrollIntoView({block:'start'})`);
  assert.equal(await evaluate(`document.documentElement.scrollWidth>innerWidth`), false);
  await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: await evaluate('scrollY'), width: 390, height: 844, scale: 1 }, captureBeyondViewport: true }).then(result => writeFile(path.join(screenshots, 'noctiluca-native-sandbox-mission-mobile.png'), Buffer.from(result.data, 'base64')));
  assert.deepEqual(apiRequests.sort(), ['GET /native-api/session', 'POST /native-api/validate'].sort());
  assert.equal(errors.length, 0, JSON.stringify(errors));
  const report = { fixture_api: true, execution_endpoints_blocked: true, contracts_created: 2, prior_contracts_separate: true, recorded_jobs: 0, explicit_consent_still_required: true, mobile_overflow: false, api_requests: apiRequests, screenshots: ['noctiluca-native-sandbox-mission-desktop.png', 'noctiluca-native-sandbox-mission-mobile.png'], errors };
  await writeFile(path.join(screenshots, 'noctiluca-native-sandbox-mission-qa.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} finally { ws.close(); }
