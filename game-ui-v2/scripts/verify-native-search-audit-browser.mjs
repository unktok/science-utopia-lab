// Actual immutable audit only. Browser may issue GETs; no native POST permitted.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFile, writeFile, mkdir, mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
const args = Object.fromEntries(process.argv.slice(2).map(value => { const [key, ...rest] = value.replace(/^--/, '').split('='); return [key, rest.join('=')]; }));
assert(args.audit && /^[a-f0-9]{64}$/.test(args['expected-audit-sha256']) && /^[a-f0-9]{40}$/.test(args['expected-source']), 'Explicit immutable audit, file SHA and source required');
const sha = value => createHash('sha256').update(value).digest('hex'), sourceBytes = await readFile(args.audit), exported = await readFile('public/data/native-autonomous-search-v14.audit.json'), receipt = JSON.parse(await readFile('public/data/native-autonomous-search-v14.ui-receipt.json', 'utf8'));
assert.equal(sha(sourceBytes), args['expected-audit-sha256']); assert.deepEqual(exported, sourceBytes); assert.equal(receipt.audit_file_sha256, args['expected-audit-sha256']); assert.equal(receipt.source_commit, args['expected-source']);
const audit = JSON.parse(sourceBytes), order = ['throughput-blackbox', 'efficiency-blackbox', 'efficiency-nested-lr'];
assert.equal(audit.classification, 'actual-native-qwen-autonomous-search-development-v14'); assert.equal(audit.status, 'budget-complete-with-failures'); assert.equal(audit.physical_native_worlds, 0); assert.equal(audit.physical_researcher_responses, 0); assert.deepEqual(audit.run_order, order);
const output = resolve(args.output ?? 'screenshots/autonomous-search-v14-a1-actual-qa'), port = Number(args.port ?? 4386), base = `http://127.0.0.1:${port}`, profile = await mkdtemp(join(tmpdir(), 'noctiluca-v14-actual-audit-chrome-'));
assert(Number.isInteger(port) && port >= 1024 && port <= 65535);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(fn, label) { for (let i = 0; i < 150; i++) { try { if (await fn()) return; } catch {} await sleep(100); } throw Error(`Timeout: ${label}`); }
async function stop(process) { if (process?.exitCode === null) { process.kill('SIGTERM'); await Promise.race([new Promise(resolve => process.once('exit', resolve)), sleep(1500)]); if (process.exitCode === null) process.kill('SIGKILL'); } }
class Cdp {
  id = 0; pending = new Map(); events = [];
  async open(url) { this.socket = new WebSocket(url); await new Promise(resolve => { this.socket.onopen = resolve; }); this.socket.onmessage = ({ data }) => { const message = JSON.parse(data); if (message.id) { this.pending.get(message.id)?.(message); this.pending.delete(message.id); } else this.events.push(message); }; }
  async call(method, params = {}) { const message = await new Promise(resolve => { const id = ++this.id; this.pending.set(id, resolve); this.socket.send(JSON.stringify({ id, method, params })); }); if (message.error) throw Error(JSON.stringify(message.error)); return message.result; }
  async eval(expression) { const result = await this.call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails)); return result.result.value; }
}
let vite, chrome, cdp;
const artifacts = [];
try {
  await mkdir(output, { recursive: true }); vite = spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(port)], { stdio: 'ignore' }); await until(async () => (await fetch(`${base}/native.html`)).ok, 'owned Vite');
  chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', `--user-data-dir=${profile}`, '--remote-debugging-port=0', 'about:blank'], { stdio: 'ignore' });
  let chromePort; await until(async () => { chromePort = Number((await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); return chromePort > 0; }, 'isolated Chrome'); const target = (await (await fetch(`http://127.0.0.1:${chromePort}/json/list`)).json()).find(row => row.type === 'page');
  cdp = new Cdp(); await cdp.open(target.webSocketDebuggerUrl); for (const domain of ['Page', 'Runtime', 'Network', 'Log']) await cdp.call(`${domain}.enable`);
  await cdp.call('Page.navigate', { url: `${base}/native.html?audited-search=v14` }); await until(() => cdp.eval(`document.querySelector('#search-audit-status')?.textContent.includes('EXACT AUDIT BYTES VERIFIED')`), 'actual audit integrity import');
  assert.equal(await cdp.eval(`document.querySelector('#search-audit-run').options.length===3&&document.querySelector('#search-submit').disabled&&!document.querySelector('#search-consent').checked`), true);
  for (const id of order) {
    await cdp.eval(`document.querySelector('#search-audit-run').value=${JSON.stringify(id)};document.querySelector('#search-audit-run').dispatchEvent(new Event('change'))`);
    const actual = await cdp.eval(`({attempts:document.querySelector('#search-designer-attempts').children.length,stages:document.querySelector('#search-timeline').children.length,graph:document.querySelectorAll('#search-graph .search-node').length,best:document.querySelector('#search-best').textContent,physical:document.querySelector('#search-physical').textContent,origin:document.querySelector('#search-evidence-origin').textContent,replies:document.querySelector('#search-replies').textContent})`);
    assert.equal(actual.attempts, 4); assert.equal(actual.stages, audit.runs[id].records.length); assert.equal(actual.graph, 0); assert.equal(actual.best, 'UNOBSERVED'); assert.equal(actual.physical, '0'); assert(actual.origin.includes(args['expected-source']) && actual.origin.includes(args['expected-audit-sha256'])); assert(actual.replies.includes('DESIGNER 4 / RESEARCHER 0'));
    await cdp.call('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1120, deviceScaleFactor: 1, mobile: false }); await cdp.eval(`document.querySelector('.search-monitor').scrollIntoView()`); const screen = await cdp.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }), bytes = Buffer.from(screen.data, 'base64'), file = `actual-${id}.png`; await writeFile(join(output, file), bytes); artifacts.push({ file, sha256: sha(bytes), ...actual });
  }
  await cdp.eval(`document.querySelector('#search-audit-run').value='throughput-blackbox';document.querySelector('#search-audit-run').dispatchEvent(new Event('change'));document.querySelector('#search-designer-attempts details').open=true;document.querySelector('#search-designer-attempts button').click();document.querySelector('.search-inspection').scrollIntoView()`);
  const sourceText = await cdp.eval(`document.querySelector('#search-source').textContent`); assert(sourceText.includes('ORIGINAL AUTHORED VALUE / /mechanisms/17/parameters/code_artifact/source')); assert(sourceText.includes('def '));
  for (const [name, width] of [['source-desktop', 1600], ['source-mobile', 390]]) { await cdp.call('Emulation.setDeviceMetricsOverride', { width, height: 1120, deviceScaleFactor: 1, mobile: width === 390 }); await cdp.eval(`document.querySelector('.search-inspection').scrollIntoView()`); await sleep(100); assert.equal(await cdp.eval('document.documentElement.scrollWidth>innerWidth'), false); const capture = await cdp.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }), bytes = Buffer.from(capture.data, 'base64'), file = `actual-${name}.png`; await writeFile(join(output, file), bytes); artifacts.push({ file, sha256: sha(bytes), width }); }
  const errors = cdp.events.filter(message => message.method === 'Runtime.exceptionThrown' || message.method === 'Log.entryAdded' && message.params.entry.level === 'error'), failed = cdp.events.filter(message => message.method === 'Network.responseReceived' && message.params.response.status >= 400), requests = cdp.events.filter(message => message.method === 'Network.requestWillBeSent' && /^http/.test(message.params.request.url)).map(message => ({ url: message.params.request.url, method: message.params.request.method }));
  assert.equal(errors.length, 0, JSON.stringify(errors)); assert.equal(failed.length, 0, JSON.stringify(failed)); assert(requests.every(request => request.method === 'GET' && request.url.startsWith(`${base}/`))); assert.deepEqual(await readFile(args.audit), sourceBytes); assert.deepEqual(await readFile('public/data/native-autonomous-search-v14.audit.json'), sourceBytes);
  const sourceFiles = ['native.html', 'src/native.ts', 'src/nativeSearchContract.ts', 'src/nativeSearchView.ts', 'src/nativeSearchAudit.ts', 'src/nativeSearch.css', 'scripts/export-native-search-audit-v14.mjs', 'scripts/verify-native-search-audit-browser.mjs'];
  const uiSources = Object.fromEntries(await Promise.all(sourceFiles.map(async file => [file, sha(await readFile(file))])));
  const result = { schema: 'scienceutopia.native-autonomous-search-actual-browser-qa.v14', classification: audit.classification, experiment_source: args['expected-source'], audit_file_sha256: sha(sourceBytes), audit_content_sha256: audit.content_sha256, ui_source_sha256s: uiSources, no_inference: true, no_post: true, no_adoption: true, all_three_requests: true, designer_attempts: 12, native_worlds: 0, native_replies: 0, raw_authored_source_inspected: true, browser_errors: 0, failed_http: 0, no_overflow: true, artifacts, requests };
  await writeFile(join(output, 'actual-browser-qa.json'), `${JSON.stringify(result, null, 2)}\n`); console.log(JSON.stringify({ output, ...result }));
} finally { cdp?.socket?.close(); await stop(chrome); await stop(vite); }
