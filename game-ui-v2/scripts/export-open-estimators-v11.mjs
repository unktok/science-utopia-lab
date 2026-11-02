import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const args = Object.fromEntries(process.argv.slice(2).map((arg) => { const [key,...rest] = arg.replace(/^--/,'').split('='); return [key,rest.join('=') || true]; }));
const ui = resolve(dirname(fileURLToPath(import.meta.url)),'..');
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
const hash = (value) => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const finite = (value) => typeof value === 'number' && Number.isFinite(value);
const actual = 'actual-native-qwen-open-estimators-development-v11';
const fixture = 'scripted-fixture-not-native-results';
const source = resolve(String(args.audit ?? ''));
const output = resolve(String(args.output ?? resolve(ui,'public/data')));
const synthetic = args['allow-synthetic-temp-only'] === true;
if (!args.audit || !hash(args['expected-audit-sha256']) || !/^[a-f0-9]{40}$/.test(String(args['expected-source']))) throw new Error('Required: --audit=PATH --expected-audit-sha256=HASH --expected-source=COMMIT');
if (synthetic && ![source,output].every((path) => path.startsWith(`${resolve(tmpdir())}/`))) throw new Error('Synthetic input/output must remain in system temporary directory');
const bytes = await readFile(source);
if (sha(bytes) !== args['expected-audit-sha256']) throw new Error('Explicit expected audit file hash differs');
const audit = JSON.parse(bytes);
if (audit.schema !== 'scienceutopia.native-open-estimators-independent-audit.v11' || audit.status !== 'complete'
    || audit.classification !== (synthetic ? fixture : actual) || audit.source_commit !== args['expected-source']
    || !hash(audit.content_sha256) || audit.physical_native_worlds !== 8 || audit.logical_completed_draws !== 8
    || audit.matched_initial_definitions?.matched !== true || audit.loss_spec?.id !== 'native-joint-v5-net-reviewed-utility'
    || audit.audit?.checkpoint_loss_reextracted !== true || audit.audit?.campaign_updates_and_prior_refits_replayed !== true
    || audit.audit?.new_model_calls !== 0 || audit.audit?.new_container_executions !== 0) throw new Error('Expected complete source/hash-bound independent v11 audit');
if (!synthetic && audit.audit.replay_source_proofs?.status !== 'verified-exact-replay-source-blobs') throw new Error('Actual replay source proof missing');
if (audit.audit.raw_root && (output === resolve(audit.audit.raw_root) || output.startsWith(`${resolve(audit.audit.raw_root)}/`))) throw new Error('UI export must remain outside immutable raw evidence');
if (['native-open-estimators-v11.ui.json','native-open-estimators-v11.ui-receipt.json','native-open-estimators-v11.availability.json'].some(file=>resolve(output,file)===source)) throw new Error('UI export must not overwrite the source audit');
const replies = audit.physical_researcher_responses;
if (!Number.isInteger(replies) || replies <= 0 || audit.logical_completed_researcher_responses !== replies || audit.completed_wire_requests !== replies || audit.reused_responses_in_completed_worlds !== 0) throw new Error('Actual physical/logical/wire cost mismatch');
for (const key of ['held_out','causal_institutional_benefit','scientific_value','designer_improvement_established','full_native_world_pathwise_autograd','variance_reduction_established','external_authorship_authenticated']) if (audit.claims?.[key] !== false) throw new Error(`Unsupported ${key} claim`);
if (audit.claims.live_fixed_Qwen_researchers !== !synthetic || audit.claims.scripted_researcher_HTTP !== synthetic) throw new Error('Actual/fixture researcher attribution differs');
const methods = ['blackbox','score-control-variate'].map((id) => {
  const arm = audit.arms[id];
  if (arm.observations.length !== 4 || arm.records.length !== 2 || arm.updates.length !== 2 || arm.incumbents.initial_unevaluated_system_scored !== false) throw new Error('Complete four-draw arm with no initial baseline required');
  const steps = arm.observations.map((row,index) => {
    const generation = Math.floor(index/2), drawIndex = index%2;
    const record = arm.records[generation], draw = record.draws[drawIndex];
    const system = draw.suggestion.candidate;
    const coordinate = record.definition.continuous[0];
    if (!coordinate || !Array.isArray(row.latent) || row.latent.length !== 1 || !finite(row.latent[0])) throw new Error('Actual coordinate/latent records required');
    const readPointer = (doc,path) => path.split('/').slice(1).reduce((owner,key) => owner[key.replaceAll('~1','/').replaceAll('~0','~')],doc);
    const cutoff = readPointer(system,coordinate.path);
    const observed = record.observations[drawIndex];
    const metrics = row.metrics;
    const nativeLoss = 3.25*metrics['native.accepted_decisions'].value - metrics['native.accepted_peer_score_sum'].value + .05*metrics['native.review_records'].value;
    if (row.generation !== generation || row.draw_index !== drawIndex || row.status !== 'complete' || !finite(row.loss)
        || row.loss !== observed.loss || row.observation_id !== observed.observation_id || Math.abs(nativeLoss-row.loss)>1e-12
        || !hash(row.system_fingerprint) || !hash(row.checkpoint_sha256) || !finite(cutoff)
        || !draw.continuous_operations.some((op) => op.path === coordinate.path && op.value === cutoff)
        || JSON.stringify(row.assignment) !== JSON.stringify(draw.assignment)) throw new Error('Actual observation/coordinate/assignment join differs');
    return { ...row, cutoff, coordinate_id:coordinate.id, coordinate_path:coordinate.path,
      incumbent_loss:arm.incumbents.path[index].best_loss_so_far,
      system:{ mechanisms:system.mechanisms, connections:system.connections, schedules:system.schedules },
      native_runs: observed.metadata.runs };
  });
  return { id, label:id === 'blackbox' ? 'BLACK BOX' : 'EXPECTATION GRADIENT + PRIOR CV', steps,
    updates:arm.updates, incumbents:arm.incumbents };
});
const binding = { report_file_sha256:sha(bytes), report_content_sha256:audit.content_sha256, source_commit:audit.source_commit };
const payload = { schema:'scienceutopia.open-estimator-observatory.v11', classification:audit.classification,
  campaign_id:'native-open-estimators-v11-a1', status:'complete', source_binding:binding,
  objective:{id:audit.loss_spec.id,formula:'L = 3.25A − Q + 0.05R'}, methods,
  physical_researcher_responses:replies, claims:audit.claims, raw_inventory_sha256:audit.audit.raw_inventory_sha256,
  initial_baseline:null, historical_baseline:null, live_job_control:false,
  limitations:audit.audit.limits ?? [] };
const text = `${JSON.stringify(payload,null,2)}\n`;
const receipt = {schema:'scienceutopia.open-estimator-ui-export.v11',payload_file:'native-open-estimators-v11.ui.json',payload_sha256:sha(text),source_binding:binding,no_inference:true,no_job_dispatch:true};
await mkdir(output,{recursive:true});
await writeFile(resolve(output,receipt.payload_file),text);
await writeFile(resolve(output,'native-open-estimators-v11.ui-receipt.json'),`${JSON.stringify(receipt,null,2)}\n`);
await writeFile(resolve(output,'native-open-estimators-v11.availability.json'),`${JSON.stringify({schema:'scienceutopia.open-estimator-availability.v11',status:'available',classification:audit.classification,payload:receipt.payload_file,receipt:'native-open-estimators-v11.ui-receipt.json'},null,2)}\n`);
console.log(JSON.stringify(receipt));
