import { sha256Text } from './methodObservatoryContract';
import type { Evidence } from './openRedesignContract';

export const NESTED_OBJECTIVES=['native-joint-v5-throughput','native-reviewed-production-efficiency-v13'] as const;
export const NESTED_STAGES=['initial-batch','updated-proposal','redesign'] as const;
export const NESTED_CLASS='actual-native-qwen-nested-search-development-v13';
export const nestedStageLabel=(row:Evidence):string=>row.draw_index===null?`${row.stage==='redesign'?'G1':'G0'} · NO NATIVE DRAW`:row.stage==='initial-batch'?`G0 · DRAW ${row.draw_index+1}`:row.stage==='updated-proposal'?'G0 · AFTER UPDATE':'G1 · REDESIGN';
const fail=(message:string):never=>{throw new Error(`Invalid v13 nested evidence: ${message}`);};
const hash=(value:unknown):value is string=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
const finite=(value:unknown):value is number=>typeof value==='number'&&Number.isFinite(value);
export function validateExactIntegerEncoding(d:Evidence):void {
  if(d.numeric_encoding?.schema!=='scienceutopia.json-unsafe-integer-decimal-strings.v1'||d.numeric_encoding.integer_encoding!=='base10-decimal-string'||!Array.isArray(d.numeric_encoding.paths))fail('lossless integer encoding');
  const seen=new Set();
  for(const path of d.numeric_encoding.paths){
    if(typeof path!=='string'||!path.startsWith('/')||seen.has(path))fail('integer pointer');seen.add(path);
    const value=path.split('/').slice(1).reduce((owner:any,key:string)=>owner?.[key.replaceAll('~1','/').replaceAll('~0','~')],d);
    if(typeof value!=='string'||!/^\-?[0-9]+$/.test(value)||BigInt(value)>=-9007199254740991n&&BigInt(value)<=9007199254740991n)fail('exact integer text');
  }
}
export function parseNestedFoundry(value:unknown,allowFixture=false):Evidence {
  const d=value as Evidence,fixture=d?.classification==='scripted-fixture-not-native-results';
  if(d?.schema!=='scienceutopia.nested-foundry-observatory.v13'||d.classification!==(fixture&&allowFixture?'scripted-fixture-not-native-results':NESTED_CLASS))fail('actual / fixture classification');
  if(!['complete','budget-complete-with-failures'].includes(d.status)||d.live_job_control!==false||d.initial_baseline!==null||d.historical_baseline!==null)fail('terminal status / baseline / control');
  if(!hash(d.source_binding?.report_file_sha256)||!hash(d.source_binding.report_content_sha256)||!/^[a-f0-9]{40}$/.test(d.source_binding.source_commit))fail('source binding');
  if(JSON.stringify(d.objective_order)!==JSON.stringify(NESTED_OBJECTIVES))fail('objective order');
  if(!Number.isInteger(d.physical_researcher_responses)||d.physical_researcher_responses<0)fail('physical replies');
  validateExactIntegerEncoding(d);
  const ids=new Set<string>();let completed=0;
  for(const id of NESTED_OBJECTIVES){
    const arm=d.arms?.[id];if(arm?.objective_id!==id||!Array.isArray(arm.observations)||!Array.isArray(arm.records)||arm.records.length>3)fail('objective arm');
    if(JSON.stringify(arm.records.map((record:Evidence)=>record.stage))!==JSON.stringify(NESTED_STAGES.slice(0,arm.records.length)))fail('stage order');
    const expected=arm.records.flatMap((record:Evidence)=>Array.from({length:Math.max(1,record.draws?.length??0)},(_,draw_index)=>({stage:record.stage,generation:record.stage==='redesign'?1:0,draw_index:record.draws?.length?draw_index:null})));
    if(arm.observations.length!==expected.length)fail('all attempted slots must remain visible');
    let best=Infinity;
    arm.observations.forEach((row:Evidence,index:number)=>{
      const slot=expected[index];
      if(row.arm!==id||row.stage!==slot.stage||row.generation!==slot.generation||row.draw_index!==slot.draw_index)fail('observation stage / draw identity');
      if(row.observation_id!==null&&(typeof row.observation_id!=='string'||ids.has(row.observation_id)))fail('observation identity');if(row.observation_id!==null)ids.add(row.observation_id);
      if(row.status==='complete'){
        if(!row.observation_id||!finite(row.own_loss)||row.loss!==row.own_loss||row.cross_scores?.[id]!==row.own_loss||!hash(row.system_fingerprint)||!hash(row.checkpoint_sha256)||!Array.isArray(row.system?.mechanisms)||!Array.isArray(row.system?.connections)||!row.lineage?.vs_parent||!row.physical_proof)fail('native endpoint');
        for(const target of NESTED_OBJECTIVES)if(row.cross_scores[target]!==null&&!finite(row.cross_scores[target]))fail('cross-score');
        completed++;best=Math.min(best,row.own_loss);
      }else if(row.own_loss!==null||row.loss!==null||NESTED_OBJECTIVES.some(target=>row.cross_scores?.[target]!==null)||row.status==='generation-failure'&&row.observation_id!==null)fail('failed slot scored / fabricated observation');
      if(row.running_best!==(best===Infinity?null:best))fail('running best');
    });
    for(const record of arm.records){
      const report=record.report;if(!report)fail('inner update record');
      if(record.draws?.length===0&&(record.generation_error||report.no_update_reason))continue;
      if(!report.weights_before||!report.weights_after)fail('inner policy weights');
      for(const weights of [report.weights_before,report.weights_after])if(!Array.isArray(weights.continuous_mean)||!weights.continuous_mean.every(finite)||!weights.logits||Object.values(weights.logits).some(values=>!Array.isArray(values)||!values.every(finite)))fail('policy weights');
      if(record.stage!=='initial-batch'&&(report.gradient!==null||JSON.stringify(report.weights_before)!==JSON.stringify(report.weights_after)||!report.no_update_reason))fail('forward-only stage updated');
    }
  }
  if(d.physical_native_worlds!==completed)fail('native count');
  for(const key of ['held_out','scientific_value','causal_institutional_benefit','external_authorship_authenticated','full_native_world_pathwise_autograd','designer_improvement_established','variance_reduction_established'])if(d.claims?.[key]!==false)fail('unsupported claim');
  if(d.claims.live_fixed_Qwen_researchers!==(!fixture&&d.physical_researcher_responses>0)||d.claims.scripted_researcher_HTTP!==fixture)fail('researcher attribution');
  return d;
}
export async function verifyNestedFoundry(text:string,receipt:Evidence,allowFixture=false):Promise<Evidence>{
  if(receipt?.schema!=='scienceutopia.nested-foundry-ui-export.v13'||receipt.payload_sha256!==await sha256Text(text)||receipt.no_inference!==true||receipt.no_job_dispatch!==true)fail('export hash / scope');
  const d=parseNestedFoundry(JSON.parse(text),allowFixture);
  if(JSON.stringify(receipt.source_binding)!==JSON.stringify(d.source_binding)||JSON.stringify(receipt.numeric_encoding)!==JSON.stringify(d.numeric_encoding))fail('export binding');
  return d;
}
