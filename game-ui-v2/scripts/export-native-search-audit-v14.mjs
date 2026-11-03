// Read only: exact terminal audit bytes + a separate file-integrity receipt.
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { tmpdir } from 'node:os';
const args = Object.fromEntries(process.argv.slice(2).map(value => { const [key, ...rest] = value.replace(/^--/, '').split('='); return [key, rest.join('=') || true]; }));
const source = resolve(String(args.audit ?? '')), output = resolve(String(args.output ?? 'public/data')), fixture = args['allow-scripted-temp-only'] === true;
if (!args.audit || !/^[a-f0-9]{64}$/.test(String(args['expected-audit-sha256'])) || !/^[a-f0-9]{40}$/.test(String(args['expected-source']))) throw Error('Exact audit path, file SHA256 and experiment source required');
if (fixture && ![source, output].every(path => path.startsWith(`${resolve(tmpdir())}/`))) throw Error('SCRIPTED input/output must remain temporary');
const bytes = await readFile(source), sha = value => createHash('sha256').update(value).digest('hex');
if (sha(bytes) !== args['expected-audit-sha256']) throw Error('Exact audit file SHA differs');
let supported = false; JSON.parse('1', (_key, value, context) => { supported = context?.source === '1'; return value; }); if (!supported) throw Error('Lossless JSON context required');
const audit = JSON.parse(bytes, (_key, value, context) => typeof value === 'number' && /^-?[0-9]+$/.test(context.source) && !Number.isSafeInteger(value) ? context.source : value);
if (audit.schema !== 'scienceutopia.native-autonomous-search-audit.v14' || audit.source_commit !== args['expected-source'] || !['complete', 'budget-complete-with-failures'].includes(audit.status)
  || audit.classification !== (fixture ? 'scripted-fixture-not-native-results' : 'actual-native-qwen-autonomous-search-development-v14') || !/^[a-f0-9]{64}$/.test(audit.content_sha256)
  || audit.audit?.new_model_calls !== 0 || audit.audit?.new_container_executions !== 0) throw Error('Terminal source-bound independent audit required');
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const equal = (a, b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
const order = ['throughput-blackbox', 'efficiency-blackbox', 'efficiency-nested-lr'];
if (!equal(audit.run_order, order) || !['campaign_and_lineage_replayed', 'checkpoint_loss_reextracted', 'all_failures_and_exact_ties_retained', 'designer_requests_raw_replies_and_operations_joined', 'scientist_and_designer_costs_separate'].every(key => audit.audit[key] === true)
  || !fixture && audit.audit.replay_source_proofs?.status !== 'verified-exact-replay-source-blobs') throw Error('Independent replay/source audit proofs missing');
for (const [index, id] of order.entries()) {
  const run = audit.runs?.[id], progress = run?.runtime_progress;
  if (!run?.terminal || progress?.schema !== 'scienceutopia.native-search-progress.v14' || !['complete', 'failed'].includes(progress.status)
    || progress.source_commit !== args['expected-source'] || progress.native_budget !== (index === 2 ? 4 : 2) || run.method !== (index === 2 ? 'nested-lr' : 'blackbox') || !Array.isArray(run.designer?.proofs)
    || !equal(run.request, progress.request) || !equal(run.records, progress.records) || !equal(run.pending, progress.pending) || !equal(run.runtime_plan, progress.immutable_plan) || !equal(run.loss_spec, run.request.loss_spec)) throw Error(`Audit runtime projection differs: ${id}`);
  if ((run.observations ?? []).some(row => row.status !== 'complete' && (row.loss !== null || row.own_loss !== null))) throw Error('Failed audited endpoint cannot have numeric loss');
}
if (audit.audit.raw_root && (output === resolve(audit.audit.raw_root) || output.startsWith(`${resolve(audit.audit.raw_root)}/`))) throw Error('Output cannot be inside raw evidence');
const names = ['native-autonomous-search-v14.audit.json', 'native-autonomous-search-v14.ui-receipt.json'];
if (names.some(name => resolve(output, name) === source)) throw Error('Do not overwrite source audit');
const receipt = { schema: 'scienceutopia.native-autonomous-search-ui-export.v14', classification: audit.classification, source_commit: audit.source_commit,
  audit_file_sha256: sha(bytes), audit_content_sha256: audit.content_sha256, audit_file: names[0], run_order: audit.run_order,
  no_inference: true, no_adoption: true, unchanged_audit_bytes: true, integrity_scope: 'Exact file SHA and experiment source; independent audit assertions retained. UI source may be a later report-only commit.' };
await mkdir(output, { recursive: true }); await writeFile(resolve(output, names[0]), bytes); await writeFile(resolve(output, names[1]), `${JSON.stringify(receipt, null, 2)}\n`);
console.log(JSON.stringify({ output, ...receipt }));
