import { readFileSync } from 'node:fs';
// @ts-expect-error Native Node type-stripping needs the explicit .ts file suffix.
import { redesignFixture, redesignHash } from './openRedesignFixture.ts';
const ids=['native-joint-v5-throughput','native-reviewed-production-efficiency-v13'];
export function nestedFixture():any {
  const old=redesignFixture(),loss_specs=Object.fromEntries(ids.map(id=>[id,JSON.parse(readFileSync(new URL(`../../research/objectives/losses/${id}.json`,import.meta.url),'utf8'))]));
  const arms=Object.fromEntries(ids.map((id,a)=>{
    const oldArm=old.arms[old.objective_order[a]],stages=['initial-batch','initial-batch','updated-proposal','redesign'];let best=Infinity;
    const observations=stages.map((stage,index)=>{
      const row=structuredClone(oldArm.observations[[0,1,1,2][index]!]),A=index+a,Q=A*3.5,R=24;
      for(const node of row.system.mechanisms){
        node.family=node.implementation==='code.python.v1'?'invented-evidence-commons':node.family;
        node.inputs=node.mechanism_id==='world.review'?[]:[{port_id:'world',channel:'artifact',required:true}];
        node.outputs=node.mechanism_id==='world.publication'?[]:[{port_id:node.implementation==='code.python.v1'?'shared_evidence':'world',channel:'artifact',required:false}];
      }
      row.system.connections=row.system.connections.map((edge:any)=>({...edge,channel:'artifact',latency:0}));
      row.system.schedules=row.system.mechanisms.map((node:any,index:number)=>({mechanism_id:node.mechanism_id,phase:index*20,trigger:'annual'}));
      const cross_scores={[ids[0]!]:-A,[ids[1]!]:-Q+.5*R};best=Math.min(best,cross_scores[id]!);
      const event_id=redesignHash(`SCRIPTED-effect-${a}-${index}`),event={event_id,event_type:'native.system.research_plan_applied',year:1,sequence:index,provenance:{mechanism_id:row.system.mechanisms[1].mechanism_id},payload:{scripted:true}};
      return {...row,arm:id,stage,generation:stage==='redesign'?1:0,draw_index:index===1?1:0,observation_id:`SCRIPTED-NESTED-${a}-${index}`,own_loss:cross_scores[id],loss:cross_scores[id],cross_scores,running_best:best,
        metrics:{'native.accepted_decisions':{value:A},'native.accepted_peer_score_sum':{value:Q},'native.review_records':{value:R}},
        physical_proof:{...row.physical_proof,activity_effect_proof:{effect_event_count:1,annual:[{year:1,effects:[{event_id,event_sha256:redesignHash(JSON.stringify(event)),event,amendments:[],applied_plan_proof:{upstream_plan_binding:'not-recorded'}}]}]}}};
    });
    const before={logits:{'open-protocol-choice':[0,0]},continuous_mean:[0]},after={logits:{'open-protocol-choice':[-.2,.2]},continuous_mean:[.3]};
    const definition={base_patch:null,factors:[],continuous:[],provenance:{source:'SCRIPTED UI FIXTURE / NOT ACTUAL QWEN'}};
    const version=redesignHash(`fixture-vocabulary-${a}`);
    const records=['initial-batch','updated-proposal','redesign'].map((stage,index)=>({stage,generation:stage==='redesign'?1:0,generation_error:null,definition:stage==='redesign'?{...definition,provenance:{source:'SCRIPTED G1'}}:definition,
      version_sha256:stage==='redesign'?redesignHash(`fixture-G1-${a}`):version,draw_version_sha256:redesignHash(`fixture-draw-stage-${a}-${index}`),request:{generation:stage==='redesign'?1:0,count:index===0?2:1,parent_system:observations[0]!.system},
      draws:Array.from({length:index===0?2:1},(_,draw_index)=>({draw_index,rng_seed:42,assignment:{}})),report:{status:index===0?'score-updated':'forward-only-observed',weights_before:index===0?before:after,weights_after:after,gradient:index===0?{logits:{'open-protocol-choice':[1,-1]},continuous_mean:[-1.5]}:null,
        losses:observations.filter((r:any)=>r.stage===stage).map((r:any)=>r.own_loss),...(index===0?{}:{no_update_reason:'single scheduled forward only / no new estimate'})}}));
    return[id,{objective_id:id,loss_spec:loss_specs[id],records,observations,incumbents:{best_loss:best,best_observation_ties:observations.filter((r:any)=>r.own_loss===best).map((r:any)=>r.observation_id)}}];
  }));
  return {...old,schema:'scienceutopia.native-nested-search-independent-audit.v13',objective_order:ids,loss_specs,arms,physical_native_worlds:8,physical_researcher_responses:16,
    planned_native_world_budget:8,consumed_native_slots:8,physical_world_directory_count:8,logical_completed_draws:8,
    claims:{...old.claims,full_native_world_pathwise_autograd:false,designer_improvement_established:false,variance_reduction_established:false},audit:{...old.audit,campaign_updates_replayed:true,sole_conditional_LR_update_analytically_rederived:true}};
}
export function failedNestedFixture():any {
  const audit=nestedFixture();audit.status='budget-complete-with-failures';audit.physical_native_worlds=0;audit.physical_researcher_responses=0;
  for(const arm of Object.values(audit.arms) as any[]){
    arm.observations=arm.records.map((record:any,index:number)=>({...arm.observations[index],stage:record.stage,generation:record.generation,draw_index:null,status:'generation-failure',observation_id:null,own_loss:null,loss:null,running_best:null,cross_scores:Object.fromEntries(ids.map(id=>[id,null])),system:null,system_fingerprint:null,checkpoint_sha256:null,lineage:null,contracts:null,physical_proof:null,metrics:{}}));
    arm.records.forEach((record:any)=>{record.draws=[];record.generation_error={message:'SCRIPTED technical authoring failure / no native world'};record.report={status:'not-updated-technical-failure',no_update_reason:'No executable vocabulary / no native draw'};});
    arm.incumbents={best_loss:null,best_observation_ties:[]};
  }audit.physical_world_directory_count=0;audit.logical_completed_draws=0;return audit;
}
