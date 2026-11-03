// Entire API is intercepted SCRIPTED QA. No model, native worker or inference.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
const output = await mkdtemp(join(tmpdir(), 'noctiluca-v14-SCRIPTED-qa-')), profile = await mkdtemp(join(tmpdir(), 'noctiluca-v14-chrome-'));
const port = 4384, base = `http://127.0.0.1:${port}`, source = 'a'.repeat(40), hash = 'b'.repeat(64), sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(fn, label) { for (let i = 0; i < 120; i++) { if (await fn()) return; await sleep(100); } throw new Error(`Timeout: ${label}`); }
class Cdp {
  id = 0; pending = new Map(); events = [];
  async open(url) { this.socket = new WebSocket(url); await new Promise(resolve => { this.socket.onopen = resolve; }); this.socket.onmessage = ({ data }) => { const m = JSON.parse(data); if (m.id) { this.pending.get(m.id)?.(m); this.pending.delete(m.id); } else { this.events.push(m); this.onEvent?.(m); } }; }
  async call(method, params = {}) { const m = await new Promise(resolve => { const id = ++this.id; this.pending.set(id, resolve); this.socket.send(JSON.stringify({ id, method, params })); }); if (m.error) throw Error(JSON.stringify(m.error)); return m.result; }
  async eval(expression) { const r = await this.call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw Error(JSON.stringify(r.exceptionDetails)); return r.result.value; }
}
let vite, chrome, cdp, request, requests = [], submitted = 0;
const progress = status => ({ schema: 'scienceutopia.native-search-progress.v14', classification: 'SCRIPTED-NOT-NATIVE-RESULTS', search_id: 'SCRIPTED-search', status, source_commit: source, request_sha256: hash, request, method: request.method, native_budget: request.native_budget, stage: status === 'queued' ? 'generation' : 'redesign', records: status === 'queued' ? [] : [{ stage: 'initial-batch', status: 'complete', native_years: [1, 2], technical_checks: 'SCRIPTED PASS', policy_update: { before: [0, 0], gradient: [1, -1], after: [-0.1, 0.1] } }, { stage: 'updated-proposal', status: 'failed', error: 'SCRIPTED native failure', loss: null }, { stage: 'redesign', status: 'complete', designer_source: 'SCRIPTED' }], observations: status === 'queued' ? [] : [{ suggestion: { system: request.initial_system }, observation: { observation_id: 'SCRIPTED-o1', status: 'complete', loss: -3 } }, { suggestion: null, observation: { status: 'failed', loss: null } }], current: status === 'queued' ? null : { suggestion: { system: request.initial_system }, observation: { observation_id: 'SCRIPTED-o1', status: 'complete', loss: -3 } }, best: { loss: status === 'queued' ? null : -3, ties: status === 'queued' ? [] : ['SCRIPTED-o1'] }, errors: status === 'queued' ? [] : ['SCRIPTED failure retained'], budget: { scheduled: 4, consumed: status === 'queued' ? 0 : 4, native_observations: status === 'queued' ? 0 : 3, remaining: status === 'queued' ? 4 : 0 }, replies: { designer: 2, researcher: 17 }, exact_identity: 'UNSAFE_INTEGER' });
async function stop(process) { if (process?.exitCode === null) { process.kill('SIGTERM'); await Promise.race([new Promise(resolve => process.once('exit', resolve)), sleep(1500)]); if (process.exitCode === null) process.kill('SIGKILL'); } }
try {
  vite = spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(port)], { stdio: 'ignore' });
  await until(async () => { try { return (await fetch(`${base}/native.html`)).ok; } catch { return false; } }, 'Vite');
  chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', `--user-data-dir=${profile}`, '--remote-debugging-port=0', 'about:blank'], { stdio: 'ignore' });
  let chromePort; await until(async () => { try { chromePort = Number((await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); return chromePort > 0; } catch { return false; } }, 'Chrome');
  const target = (await (await fetch(`http://127.0.0.1:${chromePort}/json/list`)).json()).find(row => row.type === 'page');
  cdp = new Cdp(); await cdp.open(target.webSocketDebuggerUrl);
  for (const domain of ['Page', 'Runtime', 'Network', 'Log']) await cdp.call(`${domain}.enable`);
  cdp.onEvent = m => { if (m.method !== 'Fetch.requestPaused') return; const { request: incoming, requestId } = m.params; requests.push({ url: incoming.url, method: incoming.method });
    let value, code = 200; const path = new URL(incoming.url).pathname;
    if (path.endsWith('/session')) value = { token: 'SCRIPTED-TOKEN', source_commit: source };
    else if (path.endsWith('/search-validate')) { request = JSON.parse(incoming.postData); value = { status: 'structurally-validated-not-native-executed', request_sha256: hash, source_commit: source, planned_native_world_budget: request.native_budget, method: request.method }; }
    else if (path.endsWith('/searches')) { submitted++; const body = JSON.parse(incoming.postData); assert.equal(body.confirmed_request_sha256, hash); assert.deepEqual(body.request, request); value = progress('queued'); }
    else if (path.includes('/searches/')) value = progress('complete');
    else { code = 404; value = { error: 'SCRIPTED unsupported API' }; }
    // Match the runtime's actual suggestion shape, rather than the older
    // manual-job SystemSpec spelling used to construct this temporary fixture.
    for (const row of [...(value.observations ?? []), value.current].filter(Boolean)) {
      if (row.suggestion?.system) { row.suggestion.candidate = row.suggestion.system; delete row.suggestion.system; }
    }
    if (value.schema === 'scienceutopia.native-search-progress.v14') value.live_progress = { schema: 'scienceutopia.native-search-live-progress.v14', scope: 'observed-local-files-not-final-audited-cost', observed_at: '2026-11-03T01:20:00Z', designer: { generation_directories: 1, attempts_started: 2, attempts_completed: 1 }, researcher: { runs: [{ run_id: 'SCRIPTED-one', checkpoint_year: 1, cached_responses: 17, cache_binding_status: 'matched' }], cached_responses: 17, latest_checkpoint_year: 1 }, warnings: [] };
    const body = JSON.stringify(value).replace('"UNSAFE_INTEGER"', '9007199254740993');
    void cdp.call('Fetch.fulfillRequest', { requestId, responseCode: code, responseHeaders: [{ name: 'Content-Type', value: 'application/json' }], body: Buffer.from(body).toString('base64') });
  };
  await cdp.call('Fetch.enable', { patterns: [{ urlPattern: `${base}/native-api/*`, requestStage: 'Request' }] });
  await cdp.call('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1120, deviceScaleFactor: 1, mobile: false });
  await cdp.call('Page.navigate', { url: `${base}/native.html` });
  await until(() => cdp.eval(`document.querySelector('#status')?.textContent.includes('HASH VERIFIED')`), 'base evidence');
  await cdp.eval(`document.querySelector('#design-console').open=true`);
  await until(() => cdp.eval(`!document.querySelector('#search-validate').disabled`), 'session');
  assert.equal(await cdp.eval(`document.querySelector('#search-submit').disabled`), true);
  await cdp.eval(`(()=>{const warning=document.createElement('div');warning.textContent='SCRIPTED BROWSER QA / NO INFERENCE / NOT NATIVE RESULTS';warning.style='position:fixed;top:0;left:0;right:0;padding:10px;text-align:center;background:#633956;color:white;z-index:9999;font:13px monospace';document.body.append(warning);const method=document.querySelector('#search-method');method.value='nested-lr';method.dispatchEvent(new Event('change'));document.querySelector('#search-validate').click()})()`);
  await until(() => cdp.eval(`document.querySelector('#search-validation').textContent.includes('RUNTIME VALID')`), 'validation');
  assert.equal(await cdp.eval(`document.querySelector('#search-submit').disabled`), true);
  await cdp.eval(`(()=>{const c=document.querySelector('#search-consent');c.checked=true;c.dispatchEvent(new Event('change'));const seed=document.querySelector('#design-seed');seed.value='1401';seed.dispatchEvent(new Event('input'))})()`);
  assert.equal(await cdp.eval(`document.querySelector('#search-submit').disabled&&!document.querySelector('#search-consent').checked&&document.querySelector('#search-consent').disabled`), true);
  await cdp.eval(`document.querySelector('#search-validate').click()`);
  await until(() => cdp.eval(`document.querySelector('#search-validation').textContent.includes('RUNTIME VALID')`), 'revalidation');
  await cdp.eval(`(()=>{const c=document.querySelector('#search-consent');c.checked=true;c.dispatchEvent(new Event('change'));document.querySelector('#search-submit').click();document.querySelector('#search-submit').click()})()`);
  await until(() => cdp.eval(`document.querySelector('#search-status').textContent.startsWith('COMPLETE')`), 'terminal receipts');
  assert.equal(submitted, 1); assert.equal(await cdp.eval(`document.querySelector('#search-observations').children.length`), 2);
  assert.equal(await cdp.eval(`document.querySelector('#search-timeline').children.length`), 3);
  assert.equal(await cdp.eval(`document.querySelector('#search-charged').textContent.startsWith('4 / 4')&&document.querySelector('#search-physical').textContent==='3'`), true);
  assert.equal(await cdp.eval(`document.querySelector('#search-raw').textContent.includes('9007199254740993')&&document.querySelector('#search-raw').textContent.includes('/exact_identity')`), true);
  assert.equal(await cdp.eval(`document.querySelector('#search-replies').textContent.includes('DESIGNER 2 / RESEARCHER 17')`), true);
  assert.equal(await cdp.eval(`document.querySelector('#search-live-year').textContent==='1 / 2 MAX OBSERVED'&&document.querySelector('#search-live-designer').textContent==='1 COMPLETED / 2 DISPATCH INTENTS'&&document.querySelector('#search-live-researcher').textContent==='17 KNOWN CACHE ROWS'&&document.querySelector('#search-live-note').textContent.includes('Not final audited physical calls')`), true);
  await cdp.eval(`document.querySelector('#search-observations button').click();document.querySelector('#autonomous-search').scrollIntoView()`);
  assert.equal(await cdp.eval(`document.querySelectorAll('#search-graph .search-node').length===JSON.parse(document.querySelector('#design-system').value).mechanisms.length`), true);
  const captures = [];
  for (const [name, width, height, focus] of [['desktop', 1600, 1120, '#autonomous-search'], ['desktop-progress', 1600, 1120, '.search-live'], ['mobile', 390, 1120, '#autonomous-search'], ['mobile-progress', 390, 1120, '.search-live']]) {
    await cdp.call('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width < 500 });
    await cdp.eval(`document.querySelector(${JSON.stringify(focus)}).scrollIntoView()`); await sleep(100);
    assert.equal(await cdp.eval('document.documentElement.scrollWidth>innerWidth'), false);
    const image = await cdp.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }); const bytes = Buffer.from(image.data, 'base64'); const file = `SCRIPTED-native-search-v14-${name}.png`; await writeFile(join(output, file), bytes); captures.push({ file, sha256: createHash('sha256').update(bytes).digest('hex') });
  }
  await cdp.eval(`document.querySelector('#search-evidence').click()`); await sleep(100);
  const errors = cdp.events.filter(m => m.method === 'Runtime.exceptionThrown' || m.method === 'Log.entryAdded' && m.params.entry.level === 'error');
  const failed = cdp.events.filter(m => m.method === 'Network.responseReceived' && m.params.response.status >= 400);
  assert.equal(errors.length, 0, JSON.stringify(errors)); assert.equal(failed.length, 0, JSON.stringify(failed));
  const receipt = { schema: 'scienceutopia.native-search-scripted-browser-qa.v14', classification: 'SCRIPTED-NOT-NATIVE-RESULTS', no_inference: true, intercepted_dispatches: submitted, consent_invalidation: true, duplicate_dispatch_blocked: true, exact_integer_display: true, charged_vs_physical: true, no_overflow: true, browser_errors: errors.length, failed_http: failed.length, captures, intercepted_requests: requests };
  await writeFile(join(output, 'SCRIPTED-browser-qa.json'), JSON.stringify(receipt, null, 2)); console.log(JSON.stringify({ output, ...receipt }));
} finally { cdp?.socket?.close(); await stop(chrome); await stop(vite); }
