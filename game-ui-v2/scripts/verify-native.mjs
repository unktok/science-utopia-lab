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
  const language = await evaluate(`({lang:document.documentElement.lang,text:document.body.innerText,labels:Array.from(document.querySelectorAll('[aria-label]'),e=>e.getAttribute('aria-label')).join(' '),uploadWidth:document.getElementById('load').getBoundingClientRect().width})`);
  assert.equal(language.lang, 'en');
  assert(!/[\u3040-\u30ff\u3400-\u9fff]/u.test(language.text + language.labels), 'Non-English default UI copy');
  assert.equal(language.uploadWidth, 1, 'OS-localized file input must not be visible');
  const initial = await evaluate(`({candidates:document.getElementById('candidate').options.length,actors:document.querySelectorAll('.native-actor').length,nodes:document.querySelectorAll('[data-native-node]').length,overflow:document.documentElement.scrollWidth>innerWidth})`);
  assert.equal(initial.candidates, 2); assert.equal(initial.actors, 5); assert.equal(initial.overflow, false);
  const deck = await evaluate(`({artLoaded:document.querySelector('.deck-art').complete && document.querySelector('.deck-art').naturalWidth===640,summary:document.getElementById('deck-summary').textContent,mode:document.querySelector('.deck-mode').textContent})`);
  assert.equal(deck.artLoaded, true); assert(deck.summary.includes('15 MECHANISMS')); assert(deck.mode.includes('READ ONLY'));
  await evaluate(`document.getElementById('candidate').value='1';document.getElementById('candidate').dispatchEvent(new Event('change'))`);
  await evaluate(`document.querySelector('[data-native-node="deliberation-assembly"]')?.click() || document.querySelector('[data-native-node="addressed-selection"]')?.click()`);
  const selected = await evaluate(`({name:document.getElementById('node-name').textContent,source:document.getElementById('native-source').textContent,loss:document.getElementById('native-metrics').textContent,nodes:document.querySelectorAll('[data-native-node]').length,events:document.getElementById('native-events').textContent})`);
  assert(selected.source.includes('def step(context)') || selected.source.includes('tensor-program.v1'));
  assert(selected.events.length > 50); assert(selected.loss.includes('ACTUAL NATIVE LOSS'));
  assert(!/[\u3040-\u30ff\u3400-\u9fff]/u.test(await evaluate('document.body.innerText')));
  assert.equal(await evaluate('document.getElementById("deck-focus").textContent'), selected.name);
  await send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: 1440, height: 600, scale: 1 } }).then(s => writeFile(path.join(output, 'native-foundry-deck.png'), Buffer.from(s.data, 'base64')));
  await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true }).then(s => writeFile(path.join(output, 'native-foundry-desktop.png'), Buffer.from(s.data, 'base64')));
  await evaluate(`document.getElementById('step').click()`);
  assert((await evaluate(`document.querySelector('[data-native-node][aria-pressed="true"]')?.dataset.nativeNode`)));
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  const mobileOverflow = await evaluate('document.documentElement.scrollWidth>innerWidth'); assert.equal(mobileOverflow, false);
  const mobileTitleFits = await evaluate(`(()=>{const title=document.getElementById('foundry-title').getBoundingClientRect();const scene=document.querySelector('.deck-scene').getBoundingClientRect();return title.right<=scene.right && title.left>=scene.left})()`);
  assert.equal(mobileTitleFits, true);
  await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true }).then(s => writeFile(path.join(output, 'native-foundry-mobile.png'), Buffer.from(s.data, 'base64')));
  const responsiveWidths = [320, 768, 1024];
  for (const width of responsiveWidths) {
    await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: width < 760 });
    assert.equal(await evaluate('document.documentElement.scrollWidth>innerWidth'), false, `Overflow at ${width}px`);
  }
  await evaluate(`document.getElementById('year').value='1';document.getElementById('year').dispatchEvent(new Event('change'))`);
  assert((await evaluate('document.getElementById("deck-summary").textContent')).endsWith('YEAR 1'));
  await evaluate(`document.querySelector('.deck-enter').click()`);
  assert.equal(await evaluate('location.hash'), '#network-heading');
  assert.equal(errors.length, 0, JSON.stringify(errors));
  const report = { initial, deck, language: { lang: language.lang, englishCopy: true, localizedFileInputHidden: true }, selected: { name: selected.name, nodes: selected.nodes, sourceCharacters: selected.source.length }, mobileOverflow, mobileTitleFits, responsiveWidths, yearTelemetry: true, graphNavigation: true, errors,
    screenshots: ['native-foundry-deck.png', 'native-foundry-desktop.png', 'native-foundry-mobile.png'] };
  await writeFile(path.join(output, 'browser-verification.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
} finally { ws.close(); }
