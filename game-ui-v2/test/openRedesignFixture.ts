import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
const REDESIGN_OBJECTIVES = ['native-joint-v5-throughput','native-joint-v5-net-reviewed-utility'] as const;
export const redesignHash = (value: string): string => createHash('sha256').update(value).digest('hex');
export function redesignFixture(): any {
  const loss_specs = Object.fromEntries(REDESIGN_OBJECTIVES.map(id=>[id,JSON.parse(readFileSync(new URL(`../../research/objectives/losses/${id}.json`,import.meta.url),'utf8'))]));
  const arms = Object.fromEntries(REDESIGN_OBJECTIVES.map((id,a)=>{
    let best=Infinity;
    const observations=[0,1,2].map(g=>{
      const source=`def mechanism(inputs, state):\n    # SCRIPTED UI FIXTURE / NOT ACTUAL QWEN\n    return {"shared_evidence": ${g+a}}, state\n`;
      const metrics={'native.accepted_decisions':{value:g+a},'native.accepted_peer_score_sum':{value:(g+a)*3.5},'native.review_records':{value:24}};
      const cross_scores={[REDESIGN_OBJECTIVES[0]]:g+a===0?0:-(g+a),[REDESIGN_OBJECTIVES[1]]:3.25*(g+a)-(g+a)*3.5+.05*24};
      const own_loss=cross_scores[id];best=Math.min(best,own_loss);
      const identity=`fixture-cooperative-${g}`;
      const sourceHash=redesignHash(source);
      const system={mechanisms:[{mechanism_id:'world.review',family:'review',implementation:'native.review.v1',parameters:{}},{mechanism_id:identity,family:'open-evidence-commons',implementation:'code.python.v1',parameters:{code_artifact:{source}}},{mechanism_id:'world.publication',family:'publication',implementation:'native.publication.v1',parameters:{}}],connections:[{source_mechanism:'world.review',source_port:'world',target_mechanism:identity,target_port:'world'},{source_mechanism:identity,source_port:'shared_evidence',target_mechanism:'world.publication',target_port:'world'}],schedules:[{phase:'review',order:g}]};
      const change={nodes_added:[identity],nodes_removed:g?[`fixture-cooperative-${g-1}`]:[],edges_added:system.connections.map(e=>[e.source_mechanism,e.source_port,e.target_mechanism,e.target_port]),edges_removed:[],source_changes:[],protocol_changes:[{mechanism_id:identity}],mechanism_configuration_changes:[],source_bodies_added:[sourceHash],source_bodies_removed:[],counts:{nodes_added:1,nodes_removed:g?1:0,edges_added:2,edges_removed:0,source_bodies_added:1,source_bodies_removed:0,protocol_changes:1,mechanism_configuration_changes:0,schedules_added:1,schedules_removed:0}};
      return {arm:id,generation:g,draw_index:0,observation_id:`SCRIPTED-${a}-${g}`,status:'complete',own_loss,loss:own_loss,cross_scores,metrics,running_best:best,system_fingerprint:redesignHash(`system-${a}-${g}`),checkpoint_sha256:redesignHash(`checkpoint-${a}-${g}`),system,parent_system_fingerprint:redesignHash(`parent-${a}-${g}`),lineage:{vs_initial:change,vs_parent:change},contracts:{executable_sources:{[identity]:{source,source_sha256:sourceHash,artifact:{},runtime_image_id:'SCRIPTED-IMAGE'}},protocols:{[identity]:{inputs:['world'],outputs:['shared_evidence']}},processes:{cooperative_reuse:{generation:g}}},physical_proof:{code_proof:{sources:[{mechanism_id:identity,source_sha256:sourceHash}]},native_counts:{review_records:24},response_proof:{scripted:true}}};
    });
    return [id,{objective_id:id,loss_spec:loss_specs[id],observations,records:observations.map((_row,g)=>({request:{generation:g,parent_system:observations[Math.max(0,g-1)]!.system}})),incumbents:{path:observations.map(o=>({best_loss_so_far:o.running_best})),best_loss:best,best_observation_ties:observations.filter(o=>o.own_loss===best).map(o=>o.observation_id)},selection:{}}];
  }));
  return {schema:'scienceutopia.native-objective-redesign-independent-audit.v12',status:'complete',classification:'scripted-fixture-not-native-results',source_commit:'a'.repeat(40),content_sha256:'b'.repeat(64),objective_order:[...REDESIGN_OBJECTIVES],loss_specs,arms,physical_native_worlds:6,physical_researcher_responses:12,claims:{held_out:false,causal_institutional_benefit:false,scientific_value:false,external_authorship_authenticated:false,live_fixed_Qwen_researchers:false,scripted_researcher_HTTP:true},audit:{new_model_calls:0,new_container_executions:0,checkpoint_loss_reextracted:true,campaign_and_lineage_replayed:true,raw_inventory_sha256:'c'.repeat(64),limits:['SCRIPTED UI FIXTURE / NOT ACTUAL QWEN']}};
}
export function zeroReplyRedesignFixture(): any {
  const audit=redesignFixture();audit.status='budget-complete-with-failures';audit.physical_native_worlds=0;audit.physical_researcher_responses=0;
  for(const arm of Object.values(audit.arms) as any[]){
    arm.observations=arm.observations.map((row:any)=>({...row,status:'generation-failure',observation_id:null,own_loss:null,loss:null,running_best:null,cross_scores:Object.fromEntries(REDESIGN_OBJECTIVES.map(id=>[id,null])),system:null,system_fingerprint:null,checkpoint_sha256:null,lineage:null,contracts:null,physical_proof:null,metrics:{}}));
    arm.incumbents={path:[],best_loss:null,best_observation_ties:[]};
  }
  return audit;
}
