// Actual operator only. No fixture responses, interception, worker or model launch.
// Running this script requires the root operator's explicit start authorization.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdir, mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const sha = value => createHash('sha256').update(value).digest('hex');
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const equal = (a, b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
export function operatorArguments(argv) {
  const args = Object.fromEntries(argv.map(value => { const [key, ...rest] = value.replace(/^--/, '').split('='); return [key, rest.join('=') || true]; }));
  assert.equal(args['start-authorized-ui-search'], true, 'Explicit --start-authorized-ui-search is required; no network or submission started');
  assert(/^[a-f0-9]{40}$/.test(args['expected-source']), 'Exact experiment source required');
  assert(/^[a-f0-9]{64}$/.test(args['expected-request-sha256']), 'Exact server canonical request SHA required');
  const port = Number(args.port); assert(Number.isInteger(port) && port >= 1024 && port <= 65535, 'Loopback service port required');
  for (const key of ['request', 'provider-binding', 'output']) assert(typeof args[key] === 'string' && isAbsolute(args[key]), `Absolute --${key} path required`);
  assert(!Object.keys(args).some(key => !['start-authorized-ui-search', 'expected-source', 'expected-request-sha256', 'port', 'request', 'provider-binding', 'output'].includes(key)), 'Unknown operator option');
  return { ...args, port, base: `http://127.0.0.1:${port}` };
}
export function operatorRequest(text) {
  let exact = false; JSON.parse('1', (_key, value, context) => { exact = context?.source === '1'; return value; }); assert(exact, 'Exact JSON token decoder required');
  const request = JSON.parse(text, (_key, value, context) => { if (typeof value === 'number') { assert(Number.isFinite(value), 'Finite request numbers required'); if (/^-?[0-9]+$/.test(context.source)) assert(Number.isSafeInteger(value), 'Unsafe integer request token; no rounded submission'); } return value; });
  assert.deepEqual(Object.keys(request).sort(), ['schema', 'initial_system', 'loss_spec', 'seed', 'years', 'method', 'native_budget', 'designer'].sort());
  assert.equal(request.schema, 'scienceutopia.native-search-request.v14'); assert.equal(request.method, 'blackbox'); assert.equal(request.native_budget, 2);
  assert.equal(request.seed, 42); assert.equal(request.years, 2);
  assert.deepEqual(request.designer, { model: 'qwen3:8b', max_attempts: 2, max_tokens: 4096 });
  assert(request.initial_system && typeof request.initial_system === 'object' && !Array.isArray(request.initial_system));
  assert.equal(request.loss_spec?.id, 'native-joint-v5-throughput');
  return request;
}
class Cdp {
  id = 0; pending = new Map(); events = [];
  async open(url) { this.socket = new WebSocket(url); await new Promise((resolve, reject) => { this.socket.onopen = resolve; this.socket.onerror = reject; }); this.socket.onmessage = ({ data }) => { const m = JSON.parse(data); if (m.id) { this.pending.get(m.id)?.(m); this.pending.delete(m.id); } else { this.events.push(m); this.onEvent?.(m); } }; }
  async call(method, params = {}) { const m = await new Promise(resolve => { const id = ++this.id; this.pending.set(id, resolve); this.socket.send(JSON.stringify({ id, method, params })); }); if (m.error) throw Error(JSON.stringify(m.error)); return m.result; }
  async eval(expression) { const r = await this.call('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }); if (r.exceptionDetails) throw Error(JSON.stringify(r.exceptionDetails)); return r.result.value; }
}
async function until(fn, label) { for (let i = 0; i < 150; i++) { if (await fn()) return; await sleep(100); } throw Error(`Timeout: ${label}. Do not retry submission automatically.`); }
async function stop(process) { if (process?.exitCode === null) { process.kill('SIGTERM'); await Promise.race([new Promise(resolve => process.once('exit', resolve)), sleep(1500)]); if (process.exitCode === null) process.kill('SIGKILL'); } }
export async function runOperator(args) {
  const requestBytes = await readFile(args.request), request = operatorRequest(requestBytes.toString('utf8'));
  const providerBytes = await readFile(args['provider-binding']), providerFile = JSON.parse(providerBytes), provider = providerFile.provider_binding ?? providerFile;
  assert.equal(provider.model, 'qwen3:8b', 'Expected fixed Qwen provider');
  await mkdir(args.output, { recursive: true });
  // This operator never starts a native worker or HTTP service.
  const profile = await mkdtemp(join(tmpdir(), 'noctiluca-v14-ACTUAL-operator-'));
  const network = new Map(), responseTasks = [], failures = [], captures = [];
  let chrome, cdp, submitted = false, validatedBody, queuedBody;
  const receipt = { schema: 'scienceutopia.native-search-actual-ui-submit.v14', classification: 'ACTUAL-AUTHORIZED-ENGINEERING-QA-NOT-A1-RESULTS', expected_source: args['expected-source'], expected_request_sha256: args['expected-request-sha256'], request_file_sha256: sha(requestBytes), provider_file_sha256: sha(providerBytes), fixed_loopback_origin: args.base, no_worker_or_model_started_by_harness: true, no_adoption: true, fixture_interception: false, captures };
  const saveReceipt = async error => { receipt.status = error ? 'operator-failed-no-automatic-retry' : 'queued-once'; if (error) receipt.error = String(error); receipt.submission_clicked_once = submitted; receipt.network = [...network.values()]; receipt.failures = failures; await writeFile(join(args.output, 'actual-ui-submit-receipt.json'), `${JSON.stringify(receipt, null, 2)}\n`); };
  try {
    chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', `--user-data-dir=${profile}`, '--remote-debugging-port=0', 'about:blank'], { stdio: 'ignore' });
    let chromePort; await until(async () => { try { chromePort = Number((await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); return chromePort > 0; } catch { return false; } }, 'isolated Chrome');
    const target = (await (await fetch(`http://127.0.0.1:${chromePort}/json/list`)).json()).find(row => row.type === 'page');
    cdp = new Cdp(); await cdp.open(target.webSocketDebuggerUrl);
    for (const domain of ['Page', 'Runtime', 'Network', 'Log']) await cdp.call(`${domain}.enable`);
    cdp.onEvent = message => {
      if (message.method === 'Network.requestWillBeSent') {
        const { requestId, request: outgoing } = message.params;
        if (!/^http/.test(outgoing.url)) return;
        const row = { request_id: requestId, url: outgoing.url, method: outgoing.method, ...(outgoing.postData ? { request_body: JSON.parse(outgoing.postData), request_body_utf8_sha256: sha(outgoing.postData) } : {}) }; network.set(requestId, row);
        if (!outgoing.url.startsWith(`${args.base}/`) || !['GET', 'POST'].includes(outgoing.method) || outgoing.method === 'POST' && !['/native-api/search-validate', '/native-api/searches'].includes(new URL(outgoing.url).pathname)) failures.push('Unexpected external request or mutation observed');
      }
      if (message.method === 'Network.responseReceived') { const row = network.get(message.params.requestId); if (row) { row.http_status = message.params.response.status; if (row.http_status >= 400) failures.push(`HTTP ${row.http_status}: ${row.url}`); } }
      if (message.method === 'Network.loadingFinished') { const row = network.get(message.params.requestId); if (!row || !row.url.includes('/native-api/')) return; responseTasks.push((async () => { const result = await cdp.call('Network.getResponseBody', { requestId: row.request_id }), text = result.base64Encoded ? Buffer.from(result.body, 'base64').toString('utf8') : result.body; row.response_body_sha256 = sha(text); const body = JSON.parse(text); if (row.url.endsWith('/session')) { row.response = { source_commit: body.source_commit, search_enabled: body.search_enabled, token_present: typeof body.token === 'string' }; } else row.response = body;
        if (row.url.endsWith('/search-validate')) validatedBody = body;
        if (row.url.endsWith('/searches') && row.method === 'POST') queuedBody = body;
      })().catch(error => failures.push(`Unable to retain API response: ${String(error)}`))); }
    };
    await cdp.call('Emulation.setDeviceMetricsOverride', { width: 1600, height: 1120, deviceScaleFactor: 1, mobile: false });
    await cdp.call('Page.navigate', { url: `${args.base}/native.html` });
    await until(() => cdp.eval(`document.querySelector('#status')?.textContent.includes('HASH VERIFIED')`), 'existing native evidence');
    await cdp.eval(`document.querySelector('#design-console').open=true`);
    await until(() => cdp.eval(`!document.querySelector('#search-validate').disabled`), 'actual source-bound session');
    const sessions = [...network.values()].filter(row => row.url.endsWith('/session')); await until(() => sessions.every(row => row.response), 'session receipts');
    assert(sessions.length >= 1); assert(sessions.every(row => row.http_status === 200 && row.response.source_commit === args['expected-source'] && row.response.search_enabled === true));
    await cdp.eval(`(()=>{const r=${JSON.stringify(request)};for(const[id,value]of [['design-system',JSON.stringify(r.initial_system,null,2)],['design-loss',JSON.stringify(r.loss_spec,null,2)],['design-seed',String(r.seed)],['design-years',String(r.years)],['search-method',r.method],['search-budget',String(r.native_budget)],['search-attempts',String(r.designer.max_attempts)],['search-tokens',String(r.designer.max_tokens)]]){const input=document.getElementById(id);input.value=value;input.dispatchEvent(new Event('input',{bubbles:true}));if(id==='search-method')input.dispatchEvent(new Event('change',{bubbles:true}));}})()`);
    assert.equal(await cdp.eval(`document.querySelector('#search-submit').disabled&&!document.querySelector('#search-consent').checked&&document.querySelector('#search-consent').disabled`), true);
    assert.equal([...network.values()].filter(row => row.method === 'POST').length, 0);
    await cdp.eval(`document.querySelector('#search-validate').click()`);
    await until(() => !!validatedBody, 'single actual validation response');
    assert.equal(validatedBody.status, 'structurally-validated-not-native-executed'); assert.equal(validatedBody.source_commit, args['expected-source']); assert.equal(validatedBody.request_sha256, args['expected-request-sha256']);
    assert.equal(validatedBody.method, 'blackbox'); assert.equal(validatedBody.planned_native_world_budget, 2); assert.equal(validatedBody.maximum_designer_provider_attempts, 4); assert(equal(validatedBody.provider_binding, provider), 'Pinned provider binding differs');
    const posts = [...network.values()].filter(row => row.method === 'POST'); assert.equal(posts.length, 1); assert(posts[0].url.endsWith('/search-validate')); assert(equal(posts[0].request_body, request));
    await until(() => cdp.eval(`!document.querySelector('#search-consent').disabled&&document.querySelector('#search-submit').disabled`), 'validated request awaiting consent');
    const capture = async name => { await cdp.eval(`document.querySelector('#autonomous-search').scrollIntoView()`); const image = await cdp.call('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false }); const bytes = Buffer.from(image.data, 'base64'); await writeFile(join(args.output, name), bytes); captures.push({ file: name, sha256: sha(bytes) }); };
    await capture('actual-ui-before-consent.png');
    assert.equal(failures.length, 0, JSON.stringify(failures));
    receipt.submission_click_attempted = true;
    await cdp.eval(`(()=>{const consent=document.querySelector('#search-consent');consent.checked=true;consent.dispatchEvent(new Event('change',{bubbles:true}));if(document.querySelector('#search-submit').disabled)throw Error('Exact bound consent did not enable submission');document.querySelector('#search-submit').click();})()`);
    submitted = true;
    await until(() => !!queuedBody, 'one actual queue submission receipt');
    assert(['queued', 'running'].includes(queuedBody.status), 'Expected fresh queued/running receipt; do not retry'); assert.equal(queuedBody.source_commit, args['expected-source']); assert.equal(queuedBody.request_sha256, args['expected-request-sha256']); assert(equal(queuedBody.request, request));
    assert.equal(queuedBody.immutable_plan?.provider_binding && equal(queuedBody.immutable_plan.provider_binding, provider), true, 'Queued immutable provider plan differs');
    receipt.search_id = queuedBody.search_id; receipt.validation = validatedBody; receipt.queued = queuedBody;
    await until(() => cdp.eval(`document.querySelector('#search-identity').textContent.includes(${JSON.stringify(queuedBody.search_id)})`), 'queued UI identity');
    await capture('actual-ui-queued.png');
    await Promise.all(responseTasks);
    const allPosts = [...network.values()].filter(row => row.method === 'POST'); assert.equal(allPosts.length, 2); assert.equal(allPosts.filter(row => row.url.endsWith('/searches')).length, 1); assert.equal(allPosts.filter(row => row.url.endsWith('/search-validate')).length, 1);
    assert(equal(allPosts[1].request_body, { request, confirmed_request_sha256: args['expected-request-sha256'] })); assert.equal(failures.length, 0, JSON.stringify(failures));
    const errors = cdp.events.filter(message => message.method === 'Runtime.exceptionThrown' || message.method === 'Log.entryAdded' && message.params.entry.level === 'error'); assert.equal(errors.length, 0, JSON.stringify(errors));
    receipt.browser_errors = 0; await saveReceipt(); console.log(JSON.stringify({ receipt: join(args.output, 'actual-ui-submit-receipt.json'), search_id: queuedBody.search_id, source_commit: args['expected-source'], request_sha256: args['expected-request-sha256'], validation_posts: 1, search_submission_posts: 1 }));
  } catch (error) { await Promise.allSettled(responseTasks); await saveReceipt(error); throw error; } finally { cdp?.socket?.close(); await stop(chrome); }
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await runOperator(operatorArguments(process.argv.slice(2)));
