import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rename, writeFile } from 'node:fs/promises';
import { homedir, tmpdir } from 'node:os';
import { basename, join, resolve } from 'node:path';

const port = Number(process.argv.find((v) => v.startsWith('--port='))?.split('=')[1] ?? 4329);
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Invalid local port');
const output = resolve(process.argv.find((v) => v.startsWith('--output='))?.slice(9) ?? 'screenshots/method-observatory-v10-qa');
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
const sleep = (ms) => new Promise((done) => setTimeout(done, ms));
async function waitFor(check, label) {
  for (let i = 0; i < 100; i++) { try { const result = await check(); if (result) return result; } catch {} await sleep(100); }
  throw new Error(`Timed out: ${label}`);
}
class Cdp {
  constructor(url) { this.url = url; this.sequence = 0; this.pending = new Map(); this.events = []; }
  async open() {
    this.socket = new WebSocket(this.url);
    await new Promise((done, reject) => { this.socket.onopen = done; this.socket.onerror = reject; });
    this.socket.onmessage = ({ data }) => { const msg = JSON.parse(data); if (msg.id && this.pending.has(msg.id)) { this.pending.get(msg.id)(msg); this.pending.delete(msg.id); } else this.events.push(msg); };
  }
  async call(method, params = {}) {
    const response = await new Promise((done) => { const id = ++this.sequence; this.pending.set(id, done); this.socket.send(JSON.stringify({ id, method, params })); });
    if (response.error) throw new Error(JSON.stringify(response.error));
    return response.result;
  }
  async evaluate(expression) { const result = await this.call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails)); return result.result.value; }
  close() { this.socket?.close(); }
}
async function stop(proc) {
  if (!proc || proc.exitCode !== null) return;
  proc.kill('SIGTERM'); await Promise.race([new Promise((done) => proc.once('exit', done)), sleep(2500)]);
  if (proc.exitCode === null) proc.kill('SIGKILL');
}
const profile = await mkdtemp(join(tmpdir(), 'noctiluca-method-observatory-'));
const url = `http://127.0.0.1:${port}/method-observatory.html`;
let vite, chrome, cdp;
try {
  await mkdir(output, { recursive: true });
  const payloadBytes = await readFile(resolve('public/data/native-method-paths-v10-observatory.json'));
  const receipt = JSON.parse(await readFile(resolve('public/data/native-method-paths-v10-observatory.receipt.json'), 'utf8'));
  const auditBytes = await readFile(resolve('../research/results/native-method-paths-v10-a1.json'));
  if (sha(payloadBytes) !== receipt.payload_sha256 || sha(auditBytes) !== receipt.source_binding.report_file_sha256) throw new Error('Immutable source/payload binding failed');
  const stderr = [];
  vite = spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(port)], { stdio: ['ignore', 'pipe', 'pipe'] });
  vite.stderr.on('data', (bytes) => stderr.push(String(bytes)));
  await waitFor(async () => (await fetch(url)).ok, 'Vite route');
  chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', `--user-data-dir=${profile}`, '--remote-debugging-port=0', 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
  const chromePort = await waitFor(async () => Number((await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]), 'Chrome endpoint');
  const target = await waitFor(async () => (await (await fetch(`http://127.0.0.1:${chromePort}/json/list`)).json()).find((item) => item.type === 'page'), 'page target');
  cdp = new Cdp(target.webSocketDebuggerUrl); await cdp.open();
  for (const domain of ['Runtime', 'Log', 'Network', 'Page']) await cdp.call(`${domain}.enable`);
  const artifacts = {};
  const checks = [];
  for (const capture of [{ id: 'overview', width: 1600, height: 1100 }, { id: 'paths', width: 1600, height: 1040, focus: true }, { id: 'mobile', width: 390, height: 844, mobile: true }, { id: 'mobile-paths', width: 390, height: 1100, mobile: true, focus: true }]) {
    await cdp.call('Emulation.setDeviceMetricsOverride', { width: capture.width, height: capture.height, deviceScaleFactor: 1, mobile: Boolean(capture.mobile) });
    await cdp.call('Page.navigate', { url: `${url}${capture.focus ? '?focus=paths' : ''}` });
    await waitFor(() => cdp.evaluate(`!document.querySelector('#evidence').hidden`), `${capture.id} verified evidence`);
    await sleep(200);
    const state = await cdp.evaluate(`({badge:document.querySelector('#truth-badge').textContent,innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth,stations:document.querySelectorAll('.mo-station').length,svgCharts:document.querySelectorAll('.mo-charts svg').length,source:document.querySelector('#footer-source').textContent,images:[...document.images].every(i=>i.complete&&i.naturalWidth>0)})`);
    if (state.badge !== 'AUDITED ACTUAL DEVELOPMENT' || state.stations !== 6 || state.svgCharts !== 2 || !state.images) throw new Error(`${capture.id} incomplete evidence/image rendering`);
    if (state.scrollWidth !== state.innerWidth || state.bodyWidth !== state.innerWidth) throw new Error(`${capture.id} horizontal overflow: ${JSON.stringify(state)}`);
    const shot = await cdp.call('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
    const bytes = Buffer.from(shot.data, 'base64'); const file = `method-observatory-v10-${capture.id}.png`; await writeFile(join(output, file), bytes);
    artifacts[capture.id] = { file, sha256: sha(bytes), width: capture.width, height: capture.height, ...state };
  }
  await cdp.call('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1000, deviceScaleFactor: 1, mobile: false });
  await cdp.call('Page.navigate', { url: `${url}?focus=paths` });
  await waitFor(() => cdp.evaluate(`!document.querySelector('#evidence').hidden`), 'interactive evidence');
  for (const [method, step, title, needle] of [[1, 0, 'BLACK-BOX BISECTION / DRAW 1', 'NO GRADIENT CONSUMED'], [0, 1, 'RESPONSE-AWARE GRADIENT / DRAW 2', 'Computed BEFORE this draw at θ = 0.6']]) {
    const state = await cdp.evaluate(`(()=>{document.querySelector('button[data-method="${method}"][data-step="${step}"]').click();return {title:document.querySelector('#detail-title').textContent,detail:document.querySelector('#endpoint-detail').textContent,pressed:document.querySelectorAll('button[aria-pressed="true"]').length}})()`);
    if (state.title !== title || !state.detail.includes(needle) || state.pressed !== 1) throw new Error(`Endpoint interaction failed: ${JSON.stringify(state)}`);
    checks.push({ method, step, title: state.title, passed: true });
  }
  await cdp.evaluate(`document.querySelector('.mo-detail-board').scrollIntoView({block:'start'})`); await sleep(100);
  const shot = await cdp.call('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
  const detailBytes = Buffer.from(shot.data, 'base64'); const detailFile = 'method-observatory-v10-detail.png'; await writeFile(join(output, detailFile), detailBytes);
  artifacts.detail = { file: detailFile, sha256: sha(detailBytes), width: 1600, height: 1000 };
  const exceptions = cdp.events.filter((e) => e.method === 'Runtime.exceptionThrown' || e.method === 'Log.entryAdded' && e.params.entry.level === 'error');
  const failed = cdp.events.filter((e) => e.method === 'Network.responseReceived' && e.params.response.status >= 400);
  const requests = cdp.events.filter((e) => e.method === 'Network.requestWillBeSent' && /^http/.test(e.params.request.url)).map((e) => ({ method: e.params.request.method, url: e.params.request.url }));
  const nonGet = requests.filter((r) => r.method !== 'GET'); const external = requests.filter((r) => !r.url.startsWith(`http://127.0.0.1:${port}/`));
  if (exceptions.length || failed.length || nonGet.length || external.length || stderr.some((line) => /error/i.test(line))) throw new Error(JSON.stringify({ exceptions, failed, nonGet, external, stderr }));
  const uiSources = {};
  for (const file of ['method-observatory.html', 'src/methodObservatory.ts', 'src/methodObservatory.css', 'src/methodObservatoryContract.ts', 'src/objectiveStructure.css', 'scripts/export-method-paths-v10.mjs', 'scripts/verify-method-observatory-browser.mjs']) uiSources[file] = sha(await readFile(resolve(file)));
  const qa = { schema: 'scienceutopia.method-observatory-browser-qa.v1', story: 'Read-only page -> immutable campaign export and receipt -> actual native endpoints, charts, selected-step provenance', engine: 'headless Chrome CDP', classification: 'actual-native-qwen-method-paths-development-v10', source_binding: receipt.source_binding, payload_sha256: receipt.payload_sha256, ui_source_sha256s: uiSources, local_only: true, no_inference: true, no_job_dispatch: true, browser_errors: 0, failed_http_responses: 0, non_get_requests: 0, external_requests: 0, artifacts, interactions: checks };
  await writeFile(join(output, 'method-observatory-v10-browser-qa.json'), `${JSON.stringify(qa, null, 2)}\n`);
  console.log(JSON.stringify(qa));
} finally {
  cdp?.close(); await stop(chrome); await stop(vite);
  try { await rename(profile, join(homedir(), '.Trash', `${basename(profile)}-${Date.now()}`)); } catch {}
}
