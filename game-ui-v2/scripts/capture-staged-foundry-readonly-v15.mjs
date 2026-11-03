// Actual GET-only progress inspection. No validation, consent, queue or adoption.
import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir, mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
const args = Object.fromEntries(process.argv.slice(2).map(value => { const [key, ...rest] = value.replace(/^--/, '').split('='); return [key, rest.join('=') || true]; }));
const phase = args.phase ?? 'snapshot'; assert(['snapshot', 'terminal'].includes(phase));
assert(isAbsolute(args.pilot) && isAbsolute(args.output), 'Absolute pilot/fresh output directory required');
assert(['throughput', 'efficiency'].includes(args.run), 'Exact frozen run ID required');
for (const [key, size] of [['expected-source', 40], ['expected-pilot-plan-sha256', 64], ['expected-request-sha256', 64], ['expected-plan-sha256', 64]]) assert(new RegExp(`^[a-f0-9]{${size}}$`).test(String(args[key])), `Exact ${key} required`);
const port = Number(args.port); assert(Number.isInteger(port) && port >= 1024 && port <= 65535);
const base = `http://127.0.0.1:${port}`, pilot = resolve(args.pilot), output = resolve(args.output), sha = value => createHash('sha256').update(value).digest('hex');
const planBytes = await readFile(join(pilot, 'plan.json')); assert.equal(sha(planBytes), args['expected-pilot-plan-sha256']);
const plan = JSON.parse(planBytes); assert.equal(plan.schema, 'scienceutopia.staged-native-search-pilot.v15'); assert.equal(plan.classification, 'actual-local-qwen-staged-native-search-development-v15'); assert.equal(plan.source_commit, args['expected-source']);
const run = plan.runs.find(row => row.id === args.run); assert(run); assert.equal(run.plan_sha256, args['expected-plan-sha256']); assert.equal(run.runtime_plan.request_sha256, args['expected-request-sha256']); assert.equal(run.request.schema, 'scienceutopia.native-search-request.v15');
const mappingBytes = await readFile(join(pilot, 'searches.json')), id = JSON.parse(mappingBytes)[args.run]; assert(/^search-[a-f0-9]{32}$/.test(id));
let writerBytes, writer;
if (phase === 'terminal') { assert.equal(args['writer-stopped'], true, 'Explicit stopped-writer notice required'); assert(isAbsolute(args['writer-receipt'])); writerBytes = await readFile(args['writer-receipt']); writer = JSON.parse(writerBytes); assert.equal(writer.status, 'exited'); assert.equal(writer.exit_code, 0); assert.equal(typeof writer.ended_utc, 'string'); }
const sessionResponse = await fetch(`${base}/native-api/session`); assert.equal(sessionResponse.status, 200); const session = await sessionResponse.json(); assert.equal(session.source_commit, args['expected-source']); assert.equal(session.search_protocol, 'staged-v15'); assert.equal(typeof session.token, 'string');
const endpoint = `${base}/native-api/searches/${id}${phase === 'terminal' ? '/evidence' : ''}`, response = await fetch(endpoint, { headers: { 'X-Native-Lab-Token': session.token } }); assert.equal(response.status, 200);
const bytes = Buffer.from(await response.arrayBuffer()), value = JSON.parse(bytes); assert.equal(value.schema, 'scienceutopia.native-search-progress.v15'); assert.equal(value.search_id, id); assert.equal(value.source_commit, args['expected-source']); assert.equal(value.request_sha256, args['expected-request-sha256']); assert.equal(value.plan_sha256, args['expected-plan-sha256']); assert.deepEqual(value.request, run.request); assert.deepEqual(value.immutable_plan, run.runtime_plan);
// Python's original int/float types, never a JavaScript reserialization, bind
// the request and plan. The browser display itself remains unaudited.
const canonical = JSON.parse(execFileSync('/Users/shiro/unktok/dev/science-utopia-lab/.venv/bin/python', ['-c', 'import sys,json,hashlib; v=json.load(sys.stdin); d=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()).hexdigest(); print(json.dumps({"request":d(v["request"]),"plan":d(v["immutable_plan"])}))'], { input: bytes, encoding: 'utf8' }));
assert.equal(canonical.request, args['expected-request-sha256']); assert.equal(canonical.plan, args['expected-plan-sha256']);
if (phase === 'terminal') assert(['complete', 'failed'].includes(value.status));
await mkdir(output); const snapshotFile = join(output, `${phase}-progress-exact.json`); await writeFile(snapshotFile, bytes);
const profile = await mkdtemp(join(tmpdir(), 'noctiluca-v15-actual-readonly-')), sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(fn, label) { for (let i = 0; i < 150; i++) { try { if (await fn()) return; } catch {} await sleep(100); } throw Error(`Timeout: ${label}`); }
async function stop(child) { if (child?.exitCode === null) { child.kill('SIGTERM'); await Promise.race([new Promise(resolve => child.once('exit', resolve)), sleep(1500)]); if (child.exitCode === null) child.kill('SIGKILL'); } }
class Cdp {
  id = 0; pending = new Map(); events = [];
  async open(url) { this.socket = new WebSocket(url); await new Promise(resolve => { this.socket.onopen = resolve; }); this.socket.onmessage = ({ data }) => { const m = JSON.parse(data); if (m.id) { this.pending.get(m.id)?.(m); this.pending.delete(m.id); } else { this.events.push(m); this.onEvent?.(m); } }; }
  async call(method, params = {}) { const m = await new Promise(resolve => { const id = ++this.id; this.pending.set(id, resolve); this.socket.send(JSON.stringify({ id, method, params })); }); if (m.error) throw Error(JSON.stringify(m.error)); return m.result; }
  async eval(expression) { const r = await this.call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw Error(JSON.stringify(r.exceptionDetails)); return r.result.value; }
}
let chrome, cdp; const captures = [];
try {
  chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', `--user-data-dir=${profile}`, '--remote-debugging-port=0', 'about:blank'], { stdio: 'ignore' }); let chromePort;
  await until(async () => { chromePort = Number((await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); return chromePort > 0; }, 'isolated Chrome'); const target = (await (await fetch(`http://127.0.0.1:${chromePort}/json/list`)).json()).find(row => row.type === 'page');
  cdp = new Cdp(); await cdp.open(target.webSocketDebuggerUrl); for (const domain of ['Page', 'Runtime', 'Network', 'Log']) await cdp.call(`${domain}.enable`);
  // Block all writes before navigation, independently of disabled UI controls.
  const blockedWrites = [];
  cdp.onEvent = event => { if (event.method !== 'Fetch.requestPaused') return; const { request, requestId } = event.params; if (request.method !== 'GET' || !request.url.startsWith(`${base}/`)) { blockedWrites.push({ method: request.method, url: request.url }); void cdp.call('Fetch.failRequest', { requestId, errorReason: 'BlockedByClient' }); } else void cdp.call('Fetch.continueRequest', { requestId }); };
  await cdp.call('Fetch.enable', { patterns: [{ urlPattern: '*', requestStage: 'Request' }] });
  await cdp.call('Page.navigate', { url: `${base}/native.html` }); await until(() => cdp.eval(`document.querySelector('#status')?.textContent.includes('HASH VERIFIED')`), 'pinned existing workbench'); await cdp.eval(`document.querySelector('#design-console').open=true`);
  await until(() => cdp.eval(`document.querySelector('#search-file')&&document.querySelector('#design-system').value.length>0`), 'workbench inputs');
  const documentNode = await cdp.call('DOM.getDocument'), fileNode = await cdp.call('DOM.querySelector', { nodeId: documentNode.root.nodeId, selector: '#search-file' }); await cdp.call('DOM.setFileInputFiles', { nodeId: fileNode.nodeId, files: [snapshotFile] });
  await until(() => cdp.eval(`document.querySelector('#search-validation').textContent.startsWith('SAVED EVIDENCE / READ ONLY')&&document.querySelector('#search-identity').textContent.includes(${JSON.stringify(id)})`), 'saved source-bound progress');
  assert.equal(await cdp.eval(`document.querySelector('#search-submit').disabled&&!document.querySelector('#search-consent').checked&&document.querySelector('#search-refresh').disabled`), true);
  assert.equal(await cdp.eval(`!!document.querySelector('.author-summary[data-invalid]')`), false);
  const expectedSteps = value.authoring_trace.generations.reduce((sum, generation) => sum + generation.steps.length, 0); assert.equal(await cdp.eval(`document.querySelectorAll('.author-events button').length`), expectedSteps);
  const annotation = `ACTUAL STAGED SEARCH / ${args.run.toUpperCase()} / ${phase.toUpperCase()} / SAVED PROGRESS IS NOT AN INDEPENDENT AUDIT / EXACT SNAPSHOT SHA256 ${sha(bytes)}`;
  await cdp.eval(`(()=>{const n=document.createElement('p');n.textContent=${JSON.stringify(annotation)};n.style='border-left:3px solid #bc9ad9;padding:12px;color:#d1c0e7;font:10px/1.8 monospace;overflow-wrap:anywhere';document.querySelector('.search-monitor-heading').after(n)})()`);
  for (const [name, width, focus, inspectSource] of [['desktop-mission', 1600, '.search-monitor', false], ['desktop-workshop', 1600, '#author-chronicle', false], ['desktop-tool-detail', 1600, '#author-chronicle', true], ['mobile-workshop', 390, '#author-chronicle', false], ['mobile-tool-detail', 390, '.author-inspector', true]]) {
    await cdp.call('Emulation.setDeviceMetricsOverride', { width, height: 1120, deviceScaleFactor: 1, mobile: width < 500 });
    if (inspectSource) await cdp.eval(`(()=>{const b=[...document.querySelectorAll('.author-events button')].find(x=>/EDIT|SPLICE/.test(x.querySelector('b').textContent));if(b)b.click();document.querySelector('.author-literal-source details')?.setAttribute('open','')})()`);
    await cdp.eval(`document.querySelector(${JSON.stringify(focus)}).scrollIntoView()`); await sleep(100); assert.equal(await cdp.eval('document.documentElement.scrollWidth>innerWidth'), false);
    assert.equal(await cdp.eval(`(()=>{const list=document.querySelector('.author-events').getBoundingClientRect(),selected=document.querySelector('.author-events button[aria-pressed=true]').getBoundingClientRect();return selected.top>=list.top-1&&selected.bottom<=list.bottom+1})()`), true, 'selected actual tool row must remain visible inside list after resize');
    const image = await cdp.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }), capture = Buffer.from(image.data, 'base64'), file = `${args.run}-${phase}-${name}.png`; await writeFile(join(output, file), capture); captures.push({ file, sha256: sha(capture), width });
  }
  const requests = cdp.events.filter(m => m.method === 'Network.requestWillBeSent' && /^http/.test(m.params.request.url)).map(m => ({ url: m.params.request.url, method: m.params.request.method })), failed = cdp.events.filter(m => m.method === 'Network.responseReceived' && m.params.response.status >= 400), errors = cdp.events.filter(m => m.method === 'Runtime.exceptionThrown' || m.method === 'Log.entryAdded' && m.params.entry.level === 'error');
  assert.equal(blockedWrites.length, 0, JSON.stringify(blockedWrites)); assert(requests.every(request => request.method === 'GET' && request.url.startsWith(`${base}/`))); assert.equal(failed.length, 0, JSON.stringify(failed)); assert.equal(errors.length, 0, JSON.stringify(errors)); assert.deepEqual(await readFile(snapshotFile), bytes); assert.deepEqual(await readFile(join(pilot, 'plan.json')), planBytes);
  const loaded = {};
  for (const event of cdp.events.filter(m => m.method === 'Network.responseReceived' && /(?:\.js|\.css|\/native\.html)$/.test(new URL(m.params.response.url).pathname))) { const body = await cdp.call('Network.getResponseBody', { requestId: event.params.requestId }); loaded[event.params.response.url] = sha(body.base64Encoded ? Buffer.from(body.body, 'base64') : Buffer.from(body.body, 'utf8')); }
  const result = { schema: 'scienceutopia.staged-foundry-readonly-browser.v15', classification: plan.classification, source_commit: args['expected-source'], request_sha256: value.request_sha256, plan_sha256: value.plan_sha256, pilot_plan_file_sha256: sha(planBytes), run: args.run, search_id: id, phase, writer_stopped_notice: phase === 'terminal', writer_receipt_sha256: writerBytes ? sha(writerBytes) : null, writer_ended_utc: writer?.ended_utc ?? null, snapshot_file: `${phase}-progress-exact.json`, snapshot_file_sha256: sha(bytes), capture_ui_code_git_head: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(), harness_sha256: sha(await readFile(fileURLToPath(import.meta.url))), served_decoded_asset_sha256s: loaded, display_only_annotation: annotation, independent_audit_applied_to_display: false, status: value.status, budget: value.budget, observed_tool_steps: expectedSteps, no_post: true, no_consent: true, no_adoption: true, no_new_model_calls: true, browser_errors: 0, failed_http: 0, no_overflow: true, captures, requests };
  await writeFile(join(output, `${phase}-readonly-browser-qa.json`), `${JSON.stringify(result, null, 2)}\n`); console.log(JSON.stringify({ output, ...result }));
} catch (error) {
  await writeFile(join(output, `${phase}-readonly-browser-failure.json`), `${JSON.stringify({ schema: 'scienceutopia.staged-foundry-readonly-browser-failure.v15', run: args.run, phase, source_commit: args['expected-source'], status: 'failed-not-QA-passed', error: String(error), snapshot_file_sha256: sha(bytes), partial_captures: captures, ended_utc: new Date().toISOString(), no_native_worker_started: true }, null, 2)}\n`);
  throw error;
} finally { cdp?.socket?.close(); await stop(chrome); }
