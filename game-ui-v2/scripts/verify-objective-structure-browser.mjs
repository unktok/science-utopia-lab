#!/usr/bin/env node
import { createHash } from "node:crypto";
import { spawn } from "node:child_process";
import { mkdir, mkdtemp, readFile, rename, writeFile } from "node:fs/promises";
import { homedir, tmpdir } from "node:os";
import { basename, join, resolve } from "node:path";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const args = Object.fromEntries(process.argv.slice(2).map((item) => {
  const [key, ...rest] = item.replace(/^--/, "").split("="); return [key, rest.join("=") || true];
}));
const mode = args.mode === "fixture" ? "fixture" : "actual";
const port = Number(args.port === true || args.port === undefined ? 4318 : args.port);
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error("--port must be an unprivileged TCP port");
const baseUrl = `http://127.0.0.1:${port}`;
const outputDirectory = resolve(String(args.output ?? `screenshots/objective-structure-v8-${mode}-qa`));
const expectedClass = mode === "actual" ? "actual-native-qwen-objective-structure-development-v8" : "scripted-fixture-not-native-results";
const sha256 = (value) => createHash("sha256").update(value).digest("hex");
const sleep = (ms) => new Promise((resolveSleep) => setTimeout(resolveSleep, ms));
const isExpectedChromeNoise = (text) => /CVDisplayLinkCreateWithCGDisplay|Trying to load the allocator|task_policy_set|Created TensorFlow Lite/.test(text);

async function waitFor(check, label, attempts = 80) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try { const value = await check(); if (value) return value; } catch {}
    await sleep(100);
  }
  throw new Error(`timed out waiting for ${label}`);
}

class Cdp {
  constructor(url) { this.url = url; this.sequence = 0; this.pending = new Map(); this.events = []; }
  async open() {
    this.socket = new WebSocket(this.url);
    await new Promise((resolveOpen, reject) => { this.socket.onopen = resolveOpen; this.socket.onerror = reject; });
    this.socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.id && this.pending.has(message.id)) { this.pending.get(message.id)(message.result); this.pending.delete(message.id); }
      else this.events.push(message);
    };
  }
  call(method, params = {}) {
    return new Promise((resolveCall) => { const id = ++this.sequence; this.pending.set(id, resolveCall); this.socket.send(JSON.stringify({ id, method, params })); });
  }
  close() { this.socket?.close(); }
}

async function terminate(process, label) {
  if (!process || process.exitCode !== null) return;
  process.kill("SIGTERM");
  await Promise.race([new Promise((resolveExit) => process.once("exit", resolveExit)), sleep(2500)]);
  if (process.exitCode === null) process.kill("SIGKILL");
  if (process.exitCode !== null && ![0, 143].includes(process.exitCode) && process.signalCode !== "SIGTERM") console.warn(`${label} exited ${process.exitCode}/${process.signalCode}`);
}

async function actualReceipt() {
  if (mode !== "actual") return null;
  const reportPath = resolve("public/data/native-objective-structure-v8-a2.json");
  const receiptPath = resolve("public/data/native-objective-structure-v8-a2.ui-export.json");
  const [bytes, receiptBytes] = await Promise.all([readFile(reportPath), readFile(receiptPath)]);
  const report = JSON.parse(bytes.toString("utf8")); const receipt = JSON.parse(receiptBytes.toString("utf8"));
  if (report.schema !== "scienceutopia.native-objective-structure-audit.v8" || report.classification !== expectedClass) throw new Error("actual report schema/classification differs");
  if (!['complete', 'budget-complete-with-failures'].includes(report.status)) throw new Error("actual browser QA requires a terminal audit");
  if (receipt.schema !== "scienceutopia.native-objective-structure-ui-export.v8" || receipt.exported_without_transform !== true) throw new Error("actual export receipt differs");
  if (receipt.report_file !== basename(reportPath) || receipt.report_file_sha256 !== sha256(bytes) || receipt.report_content_sha256 !== report.content_sha256 || receipt.classification !== report.classification) throw new Error("actual report bytes/content are not bound by the export receipt");
  return { report_file: receipt.report_file, report_file_sha256: receipt.report_file_sha256, report_content_sha256: report.content_sha256, source_commit: report.source_commit, classification: report.classification };
}

const profile = await mkdtemp(join(tmpdir(), "noctiluca-objective-v8-qa-"));
let server; let chrome; let cdp;
try {
  const pinned = await actualReceipt();
  await mkdir(outputDirectory, { recursive: true });
  const serverErrors = [];
  server = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1", "--port", String(port)], { cwd: resolve("."), stdio: ["ignore", "pipe", "pipe"] });
  server.stderr.on("data", (chunk) => serverErrors.push(String(chunk)));
  await waitFor(async () => { const response = await fetch(`${baseUrl}/objective-structure.html`); return response.ok; }, "local Vite preview");

  const chromeErrors = [];
  chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--user-data-dir=${profile}`, "--remote-debugging-port=0", "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
  chrome.stderr.on("data", (chunk) => { const text = String(chunk); if (!isExpectedChromeNoise(text) && !text.includes("DevTools listening")) chromeErrors.push(text.trim()); });
  const activePort = await waitFor(async () => {
    const text = await readFile(join(profile, "DevToolsActivePort"), "utf8"); const value = Number(text.split("\n")[0]); return Number.isInteger(value) ? value : null;
  }, "Chrome DevTools endpoint");
  const targets = await waitFor(async () => { const response = await fetch(`http://127.0.0.1:${activePort}/json/list`); const values = await response.json(); return values.find((item) => item.type === "page") ? values : null; }, "Chrome page target");
  cdp = new Cdp(targets.find((item) => item.type === "page").webSocketDebuggerUrl); await cdp.open();
  await cdp.call("Runtime.enable"); await cdp.call("Log.enable"); await cdp.call("Network.enable"); await cdp.call("Page.enable");

  const route = mode === "fixture" ? "?fixture=objective-v8" : "";
  const captures = [
    { id: "overview", width: 1600, height: 1100, suffix: "" },
    { id: "graph", width: 1500, height: 1000, suffix: `${route ? "&" : "?"}focus=graph` },
    { id: "crossscore", width: 1500, height: 900, suffix: `${route ? "&" : "?"}focus=crossscore` },
    { id: "mobile", width: 390, height: 844, suffix: "", mobile: true },
  ];
  const artifacts = {};
  for (const capture of captures) {
    const eventStart = cdp.events.length;
    await cdp.call("Emulation.setDeviceMetricsOverride", { width: capture.width, height: capture.height, deviceScaleFactor: 1, mobile: Boolean(capture.mobile) });
    await cdp.call("Page.navigate", { url: `${baseUrl}/objective-structure.html${route}${capture.suffix}` });
    await sleep(1400);
    const state = await cdp.call("Runtime.evaluate", { expression: `JSON.stringify({badge:document.querySelector('#truth-badge')?.textContent,evidenceVisible:!document.querySelector('#evidence')?.hidden,fatalHidden:document.querySelector('#fatal-error')?.hidden,innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth,stations:document.querySelectorAll('.path-station').length,graphNodes:document.querySelectorAll('.graph-node').length})`, returnByValue: true });
    const qa = JSON.parse(state.result.value);
    if (!qa.evidenceVisible || !qa.fatalHidden || qa.badge !== (mode === "actual" ? "AUDITED ACTUAL DEVELOPMENT" : "LABELLED UI FIXTURE")) throw new Error(`${capture.id} truth channel did not render`);
    if (qa.scrollWidth !== qa.innerWidth || qa.bodyWidth !== qa.innerWidth) throw new Error(`${capture.id} has horizontal overflow ${qa.innerWidth}/${qa.scrollWidth}/${qa.bodyWidth}`);
    if (!qa.stations || !qa.graphNodes) throw new Error(`${capture.id} omitted objective paths or graph nodes`);
    const events = cdp.events.slice(eventStart);
    const exceptions = events.filter((event) => event.method === "Runtime.exceptionThrown" || event.method === "Log.entryAdded" && event.params.entry.level === "error");
    const failedResponses = events.filter((event) => event.method === "Network.responseReceived" && event.params.response.status >= 400);
    const nonGet = events.filter((event) => event.method === "Network.requestWillBeSent" && event.params.request.url.startsWith("http") && event.params.request.method !== "GET");
    if (exceptions.length || failedResponses.length || nonGet.length) throw new Error(`${capture.id} browser errors or non-GET dispatch: ${JSON.stringify({ exceptions, failedResponses, nonGet })}`);
    const screenshot = await cdp.call("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: false });
    const bytes = Buffer.from(screenshot.data, "base64"); const file = `objective-structure-v8-${mode}-${capture.id}.png`;
    await writeFile(join(outputDirectory, file), bytes);
    artifacts[capture.id] = { file, sha256: sha256(bytes), width: capture.width, height: capture.height, ...qa, browser_errors: 0, failed_http_responses: 0, non_get_requests: 0 };
  }
  if (serverErrors.some((value) => /error/i.test(value))) throw new Error(`Vite preview error: ${serverErrors.join("\n")}`);
  if (chromeErrors.length) throw new Error(`unexpected Chrome diagnostics: ${chromeErrors.join("\n")}`);
  const receipt = {
    schema: "scienceutopia.native-objective-structure-browser-qa.v8", mode,
    classification: expectedClass, local_only: true, no_inference: true, no_job_dispatch: true,
    report_binding: pinned, artifacts,
  };
  receipt.content_sha256 = sha256(Buffer.from(JSON.stringify(receipt)));
  await writeFile(join(outputDirectory, `objective-structure-v8-${mode}-browser-qa.json`), `${JSON.stringify(receipt, null, 2)}\n`);
  console.log(JSON.stringify(receipt));
} finally {
  cdp?.close(); await terminate(chrome, "Chrome"); await terminate(server, "Vite");
  const trash = join(homedir(), ".Trash", `${basename(profile)}-${Date.now()}`);
  try { await rename(profile, trash); } catch {}
}
