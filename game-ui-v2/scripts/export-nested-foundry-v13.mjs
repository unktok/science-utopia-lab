import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';

const args=Object.fromEntries(process.argv.slice(2).map(arg=>{const[key,...rest]=arg.replace(/^--/,'').split('=');return[key,rest.join('=')||true];}));
const ui=resolve(dirname(fileURLToPath(import.meta.url)),'..'),objectives=['native-joint-v5-throughput','native-reviewed-production-efficiency-v13'],stages=['initial-batch','updated-proposal','redesign'];
const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;
const equal=(a,b)=>JSON.stringify(canonical(a))===JSON.stringify(canonical(b));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex'),hash=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
const source=resolve(String(args.audit??'')),output=resolve(String(args.output??resolve(ui,'public/data'))),fixture=args['allow-synthetic-temp-only']===true;
if(!args.audit||!hash(args['expected-audit-sha256'])||!/^[a-f0-9]{40}$/.test(String(args['expected-source'])))throw new Error('Required exact audit path, SHA256 and source commit');
if(fixture&&![source,output].every(path=>path.startsWith(`${resolve(tmpdir())}/`)))throw new Error('Synthetic input/output must remain temporary');
const bytes=await readFile(source);if(sha(bytes)!==args['expected-audit-sha256'])throw new Error('Explicit expected audit file hash differs');
let supported=false;JSON.parse('1',(_key,value,context)=>{supported=context?.source==='1';return value;});if(!supported)throw new Error('Lossless JSON.parse context.source required');
const integerFields=new WeakMap();
const audit=JSON.parse(bytes,function(key,value,context){if(typeof value==='number'&&/^-?[0-9]+$/.test(context.source)&&!Number.isSafeInteger(value)){let fields=integerFields.get(this);if(!fields){fields=new Set();integerFields.set(this,fields);}fields.add(key);return context.source;}return value;});
const integerPaths=[];
function collect(value,path=''){if(!value||typeof value!=='object')return;for(const key of Object.keys(value)){const pointer=`${path}/${key.replaceAll('~','~0').replaceAll('/','~1')}`;if(integerFields.get(value)?.has(key))integerPaths.push(pointer);collect(value[key],pointer);}}
collect(audit);
if(audit.schema!=='scienceutopia.native-nested-search-independent-audit.v13'||!['complete','budget-complete-with-failures'].includes(audit.status)
    ||audit.classification!==(fixture?'scripted-fixture-not-native-results':'actual-native-qwen-nested-search-development-v13')||audit.source_commit!==args['expected-source']||!hash(audit.content_sha256)||!equal(audit.objective_order,objectives))throw new Error('Expected terminal source-bound independent v13 audit');
if(audit.audit?.new_model_calls!==0||audit.audit?.new_container_executions!==0||audit.audit?.checkpoint_loss_reextracted!==true||audit.audit?.campaign_and_lineage_replayed!==true||audit.audit?.campaign_updates_replayed!==true||audit.audit?.sole_conditional_LR_update_analytically_rederived!==true)throw new Error('Independent read-only native/update audit proofs missing');
if(audit.audit.raw_root&&(output===resolve(audit.audit.raw_root)||output.startsWith(`${resolve(audit.audit.raw_root)}/`)))throw new Error('Do not write inside raw evidence');
const names=['native-nested-search-v13.ui.json','native-nested-search-v13.ui-receipt.json','native-nested-search-v13.availability.json'];
if(names.some(name=>resolve(output,name)===source))throw new Error('Do not overwrite source audit');
const arms={};let completed=0;
const ids=new Set();
for(const id of objectives){
  const expected=JSON.parse(await readFile(resolve(ui,`../research/objectives/losses/${id}.json`),'utf8'));
  const arm=audit.arms?.[id];if(!equal(audit.loss_specs?.[id],expected)||!equal(arm?.loss_spec,expected))throw new Error(`Full semantic LossSpec differs: ${id}`);
  if(arm.objective_id!==id||!Array.isArray(arm.records)||!equal(arm.records.map(record=>record.stage),stages)||!Array.isArray(arm.observations))throw new Error('All three stage records required');
  const slots=arm.records.flatMap(record=>Array.from({length:Math.max(1,record.draws?.length??0)},(_,draw_index)=>({stage:record.stage,generation:record.stage==='redesign'?1:0,draw_index:record.draws?.length?draw_index:null})));
  if(arm.observations.length!==slots.length)throw new Error('Native draws / explicit failure sentinel differ');
  let best=Infinity;
  const observations=arm.observations.map((row,index)=>{
    const slot=slots[index];if(row.arm!==id||row.stage!==slot.stage||row.generation!==slot.generation||row.draw_index!==slot.draw_index)throw new Error('Stage / draw identity differs');
    if(row.observation_id!==null&&(typeof row.observation_id!=='string'||ids.has(row.observation_id)))throw new Error('Duplicate / invalid observation identity');if(row.observation_id!==null)ids.add(row.observation_id);
    if(row.status==='complete'){
      completed++;
      if(!row.observation_id||!Number.isFinite(row.own_loss)||row.loss!==row.own_loss||row.cross_scores?.[id]!==row.own_loss||!hash(row.system_fingerprint)||!hash(row.checkpoint_sha256)||!row.physical_proof||!row.lineage?.vs_parent||!Array.isArray(row.system?.mechanisms)||!Array.isArray(row.system?.connections))throw new Error('Actual native endpoint proof missing');
      const metric=key=>{const raw=row.metrics?.[key];return typeof raw==='number'?raw:raw?.value;},A=metric('native.accepted_decisions'),Q=metric('native.accepted_peer_score_sum'),R=metric('native.review_records');
      const scores=[Number.isFinite(A)?-A:null,[Q,R].every(Number.isFinite)?-Q+.5*R:null];
      if(objectives.some((key,i)=>row.cross_scores[key]!==null&&(scores[i]===null||!Number.isFinite(row.cross_scores[key])||Math.abs(row.cross_scores[key]-scores[i])>1e-10)))throw new Error('Cross-score differs from native metrics');
      const nodes=new Set(row.system.mechanisms.map(node=>node.mechanism_id));if(nodes.size!==row.system.mechanisms.length||row.system.connections.some(edge=>!nodes.has(edge.source_mechanism)||!nodes.has(edge.target_mechanism)))throw new Error('Invalid literal graph endpoints');
      for(const outer of row.system.mechanisms){
        const node=outer.implementation==='native.process.activity.v1'?outer.parameters?.delegate:outer;
        if(outer.implementation==='native.process.activity.v1'&&node?.implementation==='native.process.activity.v1')throw new Error('Recursive process delegates forbidden');
        if(node?.implementation!=='code.python.v1')continue;
        const body=node.parameters?.code_artifact?.source,proof=row.contracts?.executable_sources?.[node.mechanism_id];
        if(typeof body!=='string'||proof?.source!==body||proof.source_sha256!==sha(body))throw new Error('Exact executable source differs');
      }
      best=Math.min(best,row.own_loss);
    }else if(row.own_loss!==null||row.loss!==null||objectives.some(key=>row.cross_scores?.[key]!==null)||row.status==='generation-failure'&&row.observation_id!==null)throw new Error('Failed slot scored / fabricated native observation');
    return {...row,running_best:best===Infinity?null:best};
  });
  for(const record of arm.records){
    const report=record.report;if(!report)throw new Error('Missing nested update record');
    if(record.draws?.length===0&&(record.generation_error||report.no_update_reason))continue;
    for(const weights of [report.weights_before,report.weights_after])if(!weights||!Array.isArray(weights.continuous_mean)||!weights.continuous_mean.every(Number.isFinite)||!weights.logits||Object.values(weights.logits).some(values=>!Array.isArray(values)||!values.every(Number.isFinite)))throw new Error('Invalid inner policy weights');
    if(record.stage!=='initial-batch'&&(report.gradient!==null||!equal(report.weights_before,report.weights_after)||!report.no_update_reason))throw new Error('Forward-only stage updated');
    if(record.stage==='updated-proposal'&&(!equal(record.definition,arm.records[0].definition)||record.version_sha256!==arm.records[0].version_sha256||!equal(report.weights_before,arm.records[0].report.weights_after)))throw new Error('Updated forward vocabulary / updated weights differ from G0');
  }
  arms[id]={...arm,observations};
}
if(audit.physical_native_worlds!==completed||!Number.isInteger(audit.physical_researcher_responses)||audit.physical_researcher_responses<0)throw new Error('Physical count differs');
for(const key of ['held_out','scientific_value','causal_institutional_benefit','external_authorship_authenticated','full_native_world_pathwise_autograd','designer_improvement_established','variance_reduction_established'])if(audit.claims?.[key]!==false)throw new Error(`Unsupported ${key} claim`);
if(audit.claims.live_fixed_Qwen_researchers!==(!fixture&&audit.physical_researcher_responses>0)||audit.claims.scripted_researcher_HTTP!==fixture)throw new Error('Researcher attribution differs');
const binding={report_file_sha256:sha(bytes),report_content_sha256:audit.content_sha256,source_commit:audit.source_commit};
const payload={schema:'scienceutopia.nested-foundry-observatory.v13',classification:audit.classification,status:audit.status,source_binding:binding,objective_order:objectives,loss_specs:audit.loss_specs,arms,
  physical_native_worlds:completed,physical_researcher_responses:audit.physical_researcher_responses,raw_inventory_sha256:audit.audit.raw_inventory_sha256,
  planned_native_world_budget:audit.planned_native_world_budget,consumed_native_slots:audit.consumed_native_slots,physical_world_directory_count:audit.physical_world_directory_count,logical_completed_draws:audit.logical_completed_draws,
  claims:audit.claims,initial_baseline:null,historical_baseline:null,live_job_control:false,limitations:audit.audit.limits??[]};
const readPointer=(document,path)=>path.split('/').slice(1).reduce((owner,key)=>owner?.[key.replaceAll('~1','/').replaceAll('~0','~')],document);
payload.numeric_encoding={schema:'scienceutopia.json-unsafe-integer-decimal-strings.v1',integer_encoding:'base10-decimal-string',paths:integerPaths.filter(path=>typeof readPointer(payload,path)==='string')};
const text=`${JSON.stringify(payload,null,2)}\n`,receipt={schema:'scienceutopia.nested-foundry-ui-export.v13',payload_file:names[0],payload_sha256:sha(text),source_binding:binding,numeric_encoding:payload.numeric_encoding,no_inference:true,no_job_dispatch:true};
await mkdir(output,{recursive:true});await writeFile(resolve(output,names[0]),text);await writeFile(resolve(output,names[1]),`${JSON.stringify(receipt,null,2)}\n`);await writeFile(resolve(output,names[2]),`${JSON.stringify({schema:'scienceutopia.nested-foundry-availability.v13',status:'available',classification:audit.classification,payload:names[0],receipt:names[1]},null,2)}\n`);
console.log(JSON.stringify(receipt));
