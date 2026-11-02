import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const args = Object.fromEntries(process.argv.slice(2).map(arg => { const [key, ...rest] = arg.replace(/^--/, '').split('='); return [key, rest.join('=') || true]; }));
const ui = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const objectives = ['native-joint-v5-throughput', 'native-joint-v5-net-reviewed-utility'];
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const equal = (a,b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const source = resolve(String(args.audit ?? ''));
const output = resolve(String(args.output ?? resolve(ui, 'public/data')));
const fixture = args['allow-synthetic-temp-only'] === true;
if (!args.audit || !hash(args['expected-audit-sha256']) || !/^[a-f0-9]{40}$/.test(String(args['expected-source']))) throw new Error('Required exact audit path, SHA256 and source commit');
if (fixture && ![source, output].every(path => path.startsWith(`${resolve(tmpdir())}/`))) throw new Error('Synthetic input/output must remain temporary');
const bytes = await readFile(source);
if (sha(bytes) !== args['expected-audit-sha256']) throw new Error('Explicit expected audit file hash differs');
const audit = JSON.parse(bytes);
if (audit.schema !== 'scienceutopia.native-objective-redesign-independent-audit.v12' || !['complete', 'budget-complete-with-failures'].includes(audit.status)
    || audit.classification !== (fixture ? 'scripted-fixture-not-native-results' : 'actual-native-qwen-objective-redesign-development-v12')
    || audit.source_commit !== args['expected-source'] || !hash(audit.content_sha256) || !equal(audit.objective_order, objectives)) throw new Error('Expected source-bound independent v12 audit');
if (audit.audit?.new_model_calls !== 0 || audit.audit?.new_container_executions !== 0
    || audit.audit?.checkpoint_loss_reextracted !== true || audit.audit?.campaign_and_lineage_replayed !== true) throw new Error('Independent read-only audit proofs missing');
if (audit.audit.raw_root && (output === resolve(audit.audit.raw_root) || output.startsWith(`${resolve(audit.audit.raw_root)}/`))) throw new Error('Export must remain outside immutable raw evidence');
const names = ['native-objective-redesign-v12.ui.json', 'native-objective-redesign-v12.ui-receipt.json', 'native-objective-redesign-v12.availability.json'];
if (names.some(name => resolve(output,name) === source)) throw new Error('Export must not overwrite source audit');
const arms = {};
let completed = 0;
for (const id of objectives) {
  const expected = JSON.parse(await readFile(resolve(ui, `../research/objectives/losses/${id}.json`), 'utf8'));
  if (!equal(audit.loss_specs?.[id], expected) || !equal(audit.arms?.[id]?.loss_spec, expected)) throw new Error(`Full semantic LossSpec differs: ${id}`);
  const arm = audit.arms[id];
  if (arm.objective_id !== id || !Array.isArray(arm.observations) || arm.observations.length > 3) throw new Error('Recorded three-generation arm required');
  let best = Infinity;
  const observations = arm.observations.map((row, index) => {
    if (row.arm !== id || row.generation !== index || row.draw_index !== 0) throw new Error('Observation order differs');
    if (row.status === 'complete') {
      completed++;
      if (!Number.isFinite(row.own_loss) || row.own_loss !== row.loss || row.cross_scores?.[id] !== row.own_loss || !hash(row.system_fingerprint) || !hash(row.checkpoint_sha256)
          || !row.physical_proof || !row.lineage?.vs_parent || !row.lineage.vs_initial || !Array.isArray(row.system?.mechanisms) || !Array.isArray(row.system?.connections)) throw new Error('Actual native endpoint proof missing');
      const metric = key => {const raw = row.metrics?.[key];return typeof raw === 'number' ? raw : raw?.value;};
      const A = metric('native.accepted_decisions'), Q = metric('native.accepted_peer_score_sum'), R = metric('native.review_records');
      const scores = [Number.isFinite(A)?-A:null,[A,Q,R].every(Number.isFinite)?3.25*A-Q+.05*R:null];
      if (objectives.some((key,i) => row.cross_scores[key] !== null && (scores[i] === null || !Number.isFinite(row.cross_scores[key]) || Math.abs(row.cross_scores[key]-scores[i]) > 1e-10))) throw new Error('Cross-score differs from native checkpoint metrics');
      const nodes = new Set(row.system.mechanisms.map(node => node.mechanism_id));
      if (nodes.size !== row.system.mechanisms.length || row.system.connections.some(edge => !nodes.has(edge.source_mechanism) || !nodes.has(edge.target_mechanism))) throw new Error('Actual graph has invalid endpoints');
      for (const node of row.system.mechanisms.filter(node => node.implementation === 'code.python.v1')) {
        const body = node.parameters?.code_artifact?.source, receipt = row.contracts?.executable_sources?.[node.mechanism_id];
        if (typeof body !== 'string' || receipt?.source !== body || receipt.source_sha256 !== sha(body)) throw new Error('Actual executable source contract differs');
      }
      best = Math.min(best,row.own_loss);
    } else if (row.own_loss !== null || row.loss !== null || objectives.some(key => row.cross_scores?.[key] !== null)) throw new Error('Failed endpoint must have null losses');
    return {...row,running_best:best === Infinity ? null : best};
  });
  if (audit.status === 'complete' && observations.length !== 3) throw new Error('Complete campaign needs all six attempted observations');
  arms[id] = {...arm, observations};
}
if (audit.physical_native_worlds !== completed || !Number.isInteger(audit.physical_researcher_responses) || audit.physical_researcher_responses < 0) throw new Error('Physical cost/count differs');
for (const key of ['held_out', 'causal_institutional_benefit', 'scientific_value', 'external_authorship_authenticated']) if (audit.claims?.[key] !== false) throw new Error(`Unsupported ${key} claim`);
if (audit.claims.live_fixed_Qwen_researchers !== !fixture || audit.claims.scripted_researcher_HTTP !== fixture) throw new Error('Researcher attribution differs');
const binding = {report_file_sha256:sha(bytes),report_content_sha256:audit.content_sha256,source_commit:audit.source_commit};
const payload = {schema:'scienceutopia.open-redesign-observatory.v12',classification:audit.classification,status:audit.status,source_binding:binding,objective_order:objectives,loss_specs:audit.loss_specs,arms,
  physical_native_worlds:completed,physical_researcher_responses:audit.physical_researcher_responses,raw_inventory_sha256:audit.audit.raw_inventory_sha256,
  claims:audit.claims,initial_baseline:null,historical_baseline:null,live_job_control:false,limitations:audit.audit.limits ?? []};
const text = `${JSON.stringify(payload,null,2)}\n`;
const receipt = {schema:'scienceutopia.open-redesign-ui-export.v12',payload_file:names[0],payload_sha256:sha(text),source_binding:binding,no_inference:true,no_job_dispatch:true};
await mkdir(output,{recursive:true});
await writeFile(resolve(output,names[0]),text);
await writeFile(resolve(output,names[1]),`${JSON.stringify(receipt,null,2)}\n`);
await writeFile(resolve(output,names[2]),`${JSON.stringify({schema:'scienceutopia.open-redesign-availability.v12',status:'available',classification:audit.classification,payload:names[0],receipt:names[1]},null,2)}\n`);
console.log(JSON.stringify(receipt));
