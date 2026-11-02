/** Explicit scripted schema fixture. Never written into public/data. */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
export const h=(s:string):string=>createHash('sha256').update(s).digest('hex');
export function fixtureAudit():any {
  const arms:any={};
  for(const arm of ['blackbox','score-control-variate']){
    const rows:any[]=[],records:any[]=[],updates:any[]=[],path:any[]=[];let best=Infinity;
    for(let generation=0;generation<2;generation++){
      const draws:any[]=[],observations:any[]=[];
      for(let draw_index=0;draw_index<2;draw_index++){
        const index=2*generation+draw_index,cutoff=3.1+.2*index;
        const assignment={'review-aggregation':index%2?'minimum-evidence':'mean-evidence'};
        const mechanisms=[{mechanism_id:'world.review',implementation:'native.phase.review.v1',parameters:{}},{mechanism_id:'review-evidence',implementation:'code.python.v1',parameters:{code_artifact:{source:'def step(context):\n    # SCRIPTED UI FIXTURE ONLY\n    return {}'}}},{mechanism_id:'world.selection',implementation:'code.python.v1',parameters:{cutoff,code_artifact:{source:'def step(context):\n    # SCRIPTED UI FIXTURE ONLY\n    return {}'}}},{mechanism_id:'world.publication',implementation:'native.phase.publication.v1',parameters:{}}];
        const connections=[{source_mechanism:'world.review',source_port:'world',target_mechanism:'review-evidence',target_port:'world'},{source_mechanism:'review-evidence',source_port:'evidence',target_mechanism:'world.selection',target_port:'evidence'},{source_mechanism:'world.selection',source_port:'decisions',target_mechanism:'world.publication',target_port:'decisions'}];
        const accepted=[0,1,1,2][index]!,q=[0,3.3,3.9,6.8][index]!,loss=3.25*accepted-q+.9;
        const metrics=Object.fromEntries(Object.entries({'native.accepted_decisions':accepted,'native.accepted_peer_score_sum':q,'native.review_records':18}).map(([k,value])=>[k,{status:'measured',value}]));
        const id=`SCRIPTED-${arm}-${index}`;
        rows.push({arm,generation,draw_index,status:'complete',loss,latent:[-.5+.4*index],assignment,metrics,observation_id:id,system_fingerprint:h(`system${id}`),checkpoint_sha256:h(`checkpoint${id}`)});
        const observation={observation_id:id,status:'complete',loss,metadata:{runs:[{run_id:`SCRIPTED-RUN-${id}`} ]}};
        draws.push({assignment,latent:[-.5+.4*index],suggestion:{candidate:{mechanisms,connections,schedules:[]}},continuous_operations:[{path:'/mechanisms/2/parameters/cutoff',value:cutoff}]});observations.push(observation);
        best=Math.min(best,loss);path.push({best_loss_so_far:best});
      }
      const plain={logits:{'review-aggregation':[.1,-.1]},continuous_mean:[.3]};
      const estimator={status:'valid',estimator:generation===0?'plain-likelihood-ratio':'frozen-prior-control-variate-lr',gradient:plain,plain_gradient:plain,correction_gradient:{logits:{'review-aggregation':[0,0]},continuous_mean:[0]},sample_ids:observations.map(o=>o.observation_id),prior_sample_ids:generation===0?[]:rows.slice(0,2).map(r=>r.observation_id)};
      records.push({draws,observations,definition:{continuous:[{id:'evidence-cutoff',path:'/mechanisms/2/parameters/cutoff'}]}});
      updates.push({generation,generation_error:null,mixed_report:arm==='blackbox'?{gradient:null}:{gradient:plain,expectation_estimator:estimator}});
    }
    arms[arm]={observations:rows,records,updates,incumbents:{path,best_loss:best,initial_unevaluated_system_scored:false}};
  }
  const loss=JSON.parse(readFileSync(new URL('../../research/objectives/losses/native-joint-v5-net-reviewed-utility.json',import.meta.url),'utf8'));
  return {schema:'scienceutopia.native-open-estimators-independent-audit.v11',classification:'scripted-fixture-not-native-results',status:'complete',source_commit:'a'.repeat(40),content_sha256:h('SCRIPTED-NOT-AN-AUDIT'),physical_native_worlds:8,logical_completed_draws:8,matched_initial_definitions:{matched:true},loss_spec:loss,physical_researcher_responses:16,logical_completed_researcher_responses:16,completed_wire_requests:16,reused_responses_in_completed_worlds:0,claims:{held_out:false,causal_institutional_benefit:false,scientific_value:false,designer_improvement_established:false,full_native_world_pathwise_autograd:false,variance_reduction_established:false,external_authorship_authenticated:false,live_fixed_Qwen_researchers:false,scripted_researcher_HTTP:true},audit:{checkpoint_loss_reextracted:true,campaign_updates_and_prior_refits_replayed:true,new_model_calls:0,new_container_executions:0,raw_inventory_sha256:h('SCRIPTED-INVENTORY'),limits:['SCRIPTED SCHEMA FIXTURE ONLY — NO ACTUAL QWEN RESULT']},arms};
}
