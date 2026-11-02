import type { Evidence } from './openRedesignContract';
import { nestedStageLabel } from './nestedFoundryContract';

const esc=(v:unknown)=>String(v??'UNKNOWN').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const pretty=(v:unknown)=>v===undefined?'NOT RECORDED':JSON.stringify(v,null,2);
const changed=(before:unknown,after:unknown)=>JSON.stringify(before)!==JSON.stringify(after);
export function nativeRecordedEvents(row:Evidence):Evidence[]{
  const activity=row.physical_proof?.activity_effect_proof;
  const capability=row.physical_proof?.capability_effect_proof;
  const base=(activity?.annual??[]).flatMap((annual:Evidence)=>(annual.effects??[]).map((effect:Evidence)=>({...effect,year:annual.year,receipt_kind:'native-plan-effect'})));
  const extension=(capability?.annual??[]).flatMap((annual:Evidence)=>[...(annual.complete_plan_effects??[]).map((effect:Evidence)=>({...effect,year:annual.year,receipt_kind:'complete-plan-effect'})),...(annual.review_routings??[]).map((effect:Evidence)=>({...effect,year:annual.year,receipt_kind:'original-review-routing'}))]);
  // The stronger complete-plan receipt supersedes a duplicate old summary,
  // without inventing a second native event or interpolating its timestamp.
  const unique=new Map<string,Evidence>();for(const effect of [...base,...extension])if(effect.event&&effect.event_id===effect.event.event_id)unique.set(effect.event_id,effect);
  return [...unique.values()].sort((a:Evidence,b:Evidence)=>a.year-b.year||a.event.sequence-b.event.sequence);
}
export function initializeNestedSignal(container:HTMLElement,data:Evidence,objective:string,row:Evidence,onRecordedNode?:(id:string)=>void):void {
  const arm=data.arms[objective],records:Evidence[]=arm.records;
  const initial=records.find(r=>r.stage==='initial-batch'),report=initial?.report??{},weights=[report.weights_before,report.weights_after];
  const dimensions=[...new Set(weights.flatMap(w=>w?Object.keys(w.logits??{}):[]))];
  const table=dimensions.map(key=>`<tr><th>FACTOR LOGITS / ${esc(key)}</th><td>${esc(pretty(weights[0]?.logits?.[key]))}</td><td>${esc(pretty(weights[1]?.logits?.[key]))}</td></tr>`).join('')+`<tr><th>CONTINUOUS LATENT MEAN</th><td>${esc(pretty(weights[0]?.continuous_mean))}</td><td>${esc(pretty(weights[1]?.continuous_mean))}</td></tr>`;
  const stages=[['initial-batch','01','INVENT + ESTIMATE','TWO ACTUAL NATIVE COSTS → ONE LR / LOO UPDATE'],['updated-proposal','02','TEST THE UPDATED POLICY','ONE FRESH DRAW → FORWARD ONLY / NO SECOND UPDATE'],['redesign','03','RETURN TO INVENTION','OWN THREE OBSERVATIONS → FREE G1 CODE / GRAPH → ONE DRAW']] as const;
  const events=nativeRecordedEvents(row);
  container.innerHTML=`<header><div><p class="eyebrow">THE SAME INSTITUTION / OUTER INVENTION + INNER EXPECTED-LOSS OPTIMIZATION</p><h2>CODE. GRADIENT. WORLD. CODE AGAIN.</h2></div><span>LLM WEIGHTS FIXED / NO WHOLE-WORLD BACKPROP CLAIM</span></header><div class="nested-stage-grid">${stages.map(([key,num,title,note])=>{const record=records.find(r=>r.stage===key),active=row.stage===key;return `<article data-stage="${key}" data-selected="${active}"><span>${num} / ${key.toUpperCase()}</span><h3>${title}</h3><p>${note}</p><b>${esc(record?.report?.status??record?.generation_error?.status??'NO RECORD')}</b><small>${record?`${record.draws?.length??0} RECORDED DRAWS / ${esc(record.version_sha256?.slice(0,14)??'NO VOCABULARY')}`:'NO STAGE RECORD'}</small></article>`;}).join('')}</div><div class="nested-policy-grid"><div><p class="nested-kicker">G0 CONDITIONAL POLICY / ${changed(weights[0],weights[1])?'RECORDED WEIGHTS CHANGED':'NO RECORDED WEIGHT CHANGE'}</p><table><thead><tr><th>DECLARED COORDINATE</th><th>BEFORE</th><th>AFTER</th></tr></thead><tbody>${table}</tbody></table><p>The derivative is of the declared sampling distribution, conditional on the generated vocabulary. It is not a derivative through arbitrary Python or fixed-Qwen token generation. Equal costs, technical failures and zero updates are retained.</p><details><summary>EXACT INITIAL UPDATE / GRADIENT / LOSS / COMPATIBILITY RECORD</summary><pre>${esc(pretty(report))}</pre></details></div><div class="nested-native-replay"><p class="nested-kicker">SELECTED OBSERVATION / ${esc(nestedStageLabel(row))}</p><h3>STEP THE RECORDED EFFECTS.</h3><p>Inspect actual audited native plan-effect receipts in recorded year/sequence order. No missing event, time interpolation, researcher motion or downstream benefit is inferred.</p><button type="button" id="nested-event-next" ${events.length?'':'disabled'}>STEP RECORDED NATIVE EFFECT / ${events.length}</button><p id="nested-event-position" role="status">${events.length?'NO EVENT SELECTED / PRESS STEP':'NO AUDITED NATIVE PLAN-EFFECT EVENTS FOR THIS OBSERVATION'}</p><pre id="nested-event-detail">${esc(pretty({selected_stage:row.stage,selected_draw_index:row.draw_index,observation_id:row.observation_id,report:records.find(r=>r.stage===row.stage)?.report}))}</pre></div></div>`;
  container.querySelector('.nested-native-replay>p:not(.nested-kicker)')!.textContent='Inspect audited complete-plan and original-review-routing receipts in recorded year/sequence order. No missing event, time interpolation, researcher motion or downstream benefit is inferred.';
  const capability=row.physical_proof?.capability_effect_proof;
  if(capability){const counts=document.createElement('p');counts.className='nested-capability-counts';counts.textContent=`BOUND COMPLETE PLANS ${capability.complete_plan_effect_count} / ROUTING EVENTS ${capability.routing_event_count} / ACTUAL ROUTED REVIEWS ${capability.routed_actual_review_count}`;container.querySelector('#nested-event-next')!.before(counts);}
  let position=-1;
  container.querySelector('#nested-event-next')!.addEventListener('click',()=>{
    position=(position+1)%events.length;const value=events[position]!;
    container.querySelector('#nested-event-position')!.textContent=`RECORDED ${position+1}/${events.length} / YEAR ${value.year} / SEQUENCE ${value.event.sequence} / ${value.event_id}`;
    container.querySelector('#nested-event-detail')!.textContent=pretty(value);
    if(typeof value.event.provenance?.mechanism_id==='string')onRecordedNode?.(value.event.provenance.mechanism_id);
  });
}
