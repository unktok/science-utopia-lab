// Actual local browser -> API -> durable queue -> native worker -> evidence.
// --submit explicitly authorizes one two-year developer integration run.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
const submit = process.argv.includes('--submit');
const output = path.resolve('../outputs/native-jobs-browser');
await mkdir(output, { recursive: true });
const target = (await (await fetch('http://127.0.0.1:9341/json/list')).json()).find(t => t.type === 'page');
const socket = new WebSocket(target.webSocketDebuggerUrl), pending = new Map(), errors = [];
await new Promise(resolve => socket.addEventListener('open', resolve, { once: true }));
let next = 0;
socket.addEventListener('message', ({ data }) => {
  const message = JSON.parse(String(data));
  if (message.id) { const waiter = pending.get(message.id); pending.delete(message.id); message.error ? waiter.reject(new Error(JSON.stringify(message.error))) : waiter.resolve(message.result); }
  if (message.method === 'Runtime.exceptionThrown') errors.push(message.params);
});
const send = (method, params = {}) => new Promise((resolve, reject) => { const id = ++next; pending.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params })); });
async function evaluate(expression) { const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails)); return result.result.value; }
const until = expression => evaluate(`new Promise((resolve,reject)=>{const start=Date.now();function check(){if(${expression})return resolve(true);if(Date.now()-start>20000)return reject(new Error('UI timeout: '+document.getElementById('design-job-error')?.textContent));setTimeout(check,100)}check()})`);
try {
  await send('Runtime.enable'); await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1200, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'http://127.0.0.1:4591/native.html' });
  await until(`document.getElementById('status')?.textContent.includes('HASH VERIFIED')`);
  await evaluate(`document.getElementById('design-console').open=true`);
  await until(`document.getElementById('design-service')?.textContent.includes('LOCAL QUEUE')`);
  if (submit) {
    assert.equal(await evaluate(`document.getElementById('design-submit').disabled`), true);
    await evaluate(`(()=>{const input=document.getElementById('design-system');const spec=JSON.parse(input.value);spec.mechanisms.find(n=>n.mechanism_id==='addressed-selection').parameters.program.parameters.bias=-2;input.value=JSON.stringify(spec,null,2);input.dispatchEvent(new Event('input'));document.getElementById('design-validate').click()})()`);
    await until(`document.getElementById('design-validation')?.textContent.includes('STRUCTURALLY VALID')`);
    assert.equal(await evaluate(`document.getElementById('design-submit').disabled`), true);
    await evaluate(`document.getElementById('design-consent').checked=true;document.getElementById('design-consent').dispatchEvent(new Event('change'));document.getElementById('design-submit').click()`);
    await until(`document.getElementById('design-job-status')?.textContent.includes('QUEUED')`);
    const result = await evaluate(`({jobId:document.getElementById('design-job-id').textContent,status:document.getElementById('design-job-status').textContent,source:document.getElementById('design-service').textContent})`);
    assert(result.status.includes('NO MEASURED RESULT'));
    await writeFile(path.join(output, 'submitted-job.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } else {
    await until(`document.getElementById('design-job-status')?.textContent.includes('COMPLETE')`);
    assert.equal(await evaluate(`document.getElementById('design-result').disabled`), false);
    await evaluate(`document.getElementById('design-result').click()`);
    await until(`document.getElementById('design-validation')?.textContent.includes('Loaded completed native evidence')`);
    const result = await evaluate(`({jobId:document.getElementById('design-job-id').textContent,status:document.getElementById('design-job-status').textContent,candidates:document.getElementById('candidate').options.length,model:document.getElementById('native-metrics').textContent,authors:document.querySelectorAll('.native-actor').length,rendererService:document.getElementById('design-service').textContent,runProvenance:document.getElementById('design-job-provenance').textContent})`);
    assert.equal(result.candidates, 1); assert.equal(result.authors, 5); assert(result.model.includes('qwen3:8b'));
    await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 470, width: 1440, height: 1050, scale: 1 }, captureBeyondViewport: true }).then(s => writeFile(path.join(output, 'native-design-completed.png'), Buffer.from(s.data, 'base64')));
    await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    assert.equal(await evaluate('document.documentElement.scrollWidth>innerWidth'), false);
    assert.equal(errors.length, 0, JSON.stringify(errors));
    await writeFile(path.join(output, 'completed-browser-verification.json'), JSON.stringify({ ...result, mobileOverflow: false, errors }, null, 2));
    console.log(JSON.stringify(result));
  }
} finally { socket.close(); }
