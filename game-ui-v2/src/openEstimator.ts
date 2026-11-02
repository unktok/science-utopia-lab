import { verifyOpenEstimator,type OpenEstimatorCampaign,type RecordValue } from './openEstimatorContract';
import './objectiveStructure.css';
import './methodObservatory.css';
import './openEstimator.css';
const el=(id:string):HTMLElement=>{const e=document.getElementById(id);if(!e)throw new Error(`Missing ${id}`);return e;};
const esc=(v:unknown):string=>String(v??'—').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const n=(v:number):string=>Number.isInteger(v)?String(v):v.toFixed(6).replace(/0+$/,'').replace(/\.$/,'');
let data:OpenEstimatorCampaign;let selectedMethod=1;let selectedStep=3;
function chart(kind:'loss'|'cutoff'):string{
  const width=640,height=265,left=65,right=24,top=26,bottom=44;
  const all=data.methods.flatMap(m=>m.steps.map(s=>s[kind]));const minimum=Math.min(...all),maximum=Math.max(...all);const padding=Math.max(.05,(maximum-minimum)*.15);
  const low=minimum-padding,high=maximum+padding;const x=(i:number)=>left+(width-left-right)*i/3;const y=(v:number)=>top+(height-top-bottom)*(high-v)/(high-low);
  const grid=Array.from({length:4},(_,i)=>{const tick=low+(high-low)*i/3;return `<path class="plot-grid" d="M${left} ${y(tick)}H${width-right}"/><text x="${left-10}" y="${y(tick)+4}" text-anchor="end">${n(tick)}</text>`;}).join('');
  const paths=data.methods.map((method,index)=>{const color=index===0?'#a86bff':'#2dd4ff';const points=method.steps.map((s,i)=>`${i?'L':'M'}${x(i)} ${y(s[kind])}`).join(' ');const incumbent=kind==='loss'?`<path d="${method.steps.map((s,i)=>`${i?'L':'M'}${x(i)} ${y(s.incumbent_loss)}`).join(' ')}" fill="none" stroke="${color}" stroke-width="1.3" stroke-dasharray="5 5"/>`:'';return `<g>${incumbent}<path d="${points}" fill="none" stroke="${color}" stroke-width="2"/>${method.steps.map((s,i)=>index===0?`<path d="M${x(i)} ${y(s[kind])-6}l6 6-6 6-6-6z" fill="#08101f" stroke="${color}" stroke-width="2"/>`:`<circle cx="${x(i)}" cy="${y(s[kind])}" r="${selectedMethod===index&&selectedStep===i?7:4}" fill="#08101f" stroke="${color}" stroke-width="2"/>`).join('')}</g>`;}).join('');
  const ticks=[0,1,2,3].map(i=>`<text x="${x(i)}" y="${height-16}" text-anchor="middle">G${Math.floor(i/2)} D${i%2+1}</text>`).join('');
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Actual ${kind} for all eight separate physical worlds">${grid}<path d="M${x(1.5)} ${top}V${height-bottom}" stroke="#64748b" stroke-dasharray="3 5"/>${paths}${ticks}</svg>`;
}
function paths():void{
  el('loss-chart').innerHTML=chart('loss');el('cutoff-chart').innerHTML=chart('cutoff');
  el('method-paths').innerHTML=data.methods.map((method,index)=>`<article class="mo-method" data-method="${index===0?1:0}"><div class="mo-method-label"><span>${index===0?'DERIVATIVE FREE':'CONDITIONAL EXPECTED-LOSS GRADIENT'}</span><h3>${esc(method.label)}</h3><small>NO INITIAL SCORE · NO HISTORICAL BEST</small><b>BEST OBSERVED L ${n(method.incumbents.best_loss)}</b></div><div class="mo-stations" style="grid-template-columns:repeat(4,minmax(0,1fr))">${method.steps.map((step,i)=>`<button class="mo-station" data-method="${index}" data-step="${i}" aria-pressed="${selectedMethod===index&&selectedStep===i}"><span>G${step.generation} / DRAW ${step.draw_index+1}</span><strong>L ${n(step.loss)}</strong><b>CUTOFF ${n(step.cutoff)}</b><small>${esc(step.assignment['review-aggregation'])}</small></button>`).join('')}</div></article>`).join('');
  for(const button of el('method-paths').querySelectorAll<HTMLButtonElement>('button'))button.addEventListener('click',()=>{selectedMethod=Number(button.dataset.method);selectedStep=Number(button.dataset.step);paths();detail();});
}
function detail():void{
  const method=data.methods[selectedMethod]!,step=method.steps[selectedStep]!,update=method.updates[step.generation]!,estimator=update.mixed_report?.expectation_estimator;
  el('detail-title').textContent=`${method.label} / G${step.generation} DRAW ${step.draw_index+1}`;
  el('detail-kind').textContent=step.observation_id;
  const gradient=estimator?.gradient;
  const prior=(estimator?.prior_sample_ids??[]) as string[],current=(estimator?.sample_ids??[]) as string[];
  el('endpoint-detail').innerHTML=`<article class="actual-pane"><span>ORIGINAL WORLD · OBSERVED</span><h3>L = ${n(step.loss)}</h3><p>Actual cutoff ${n(step.cutoff)} · latent z ${n(step.latent[0])}</p><p>${esc(step.assignment['review-aggregation'])}</p><dl>${Object.entries(step.metrics as Record<string,RecordValue>).map(([key,value])=>`<div><dt>${esc(key.replace('native.',''))}</dt><dd>${esc(value.value)}</dd></div>`).join('')}</dl></article><article class="gradient-pane"><span>${estimator?'BATCH UPDATE AFTER BOTH DRAWS':'BLACK BOX · NO GRADIENT'}</span><h3>${estimator?step.generation===0?'PLAIN LR':'FROZEN-PRIOR CV':'OWN LOSS FEEDBACK'}</h3><p>${estimator?'The gradient updates the distribution for subsequent proposals; it is not a derivative of this world or of source code.':'External redesign uses this arm’s own native outcomes. It has no gradient or reviewer-response surrogate.'}</p>${gradient?`<p>Mean gradient: ${esc(JSON.stringify(gradient.continuous_mean))}<br/>Categorical logits: ${esc(JSON.stringify(gradient.logits))}</p>`:''}<small>Two samples do not establish variance reduction, optimizer superiority, or improved scientific value.</small></article><article class="binding-pane"><span>EXACT NATIVE ENDPOINT</span><dl><div><dt>SYSTEM</dt><dd>${esc(step.system_fingerprint)}</dd></div><div><dt>CHECKPOINT</dt><dd>${esc(step.checkpoint_sha256)}</dd></div><div><dt>PRIOR-ONLY FIT IDS</dt><dd>${prior.map(esc).join('<br/>')||'NONE · FIRST BATCH / BLACK BOX'}</dd></div><div><dt>CURRENT ESTIMATOR IDS</dt><dd>${current.map(esc).join('<br/>')||'NOT APPLICABLE'}</dd></div></dl></article>`;
  const nodes=step.system.mechanisms as RecordValue[],edges=step.system.connections as RecordValue[];
  el('graph-counts').textContent=`${nodes.length} ACTUAL NODES / ${edges.length} ACTUAL WIRES`;
  const focus=new Set(['world.review','review-evidence','world.selection','world.publication']);
  const selectedEdges=edges.filter(e=>focus.has(e.source_mechanism)&&focus.has(e.target_mechanism));
  el('wiring').innerHTML=`<p><b>ACTUAL REVIEW / DECISION SUBGRAPH</b><br/>${selectedEdges.map(e=>`${esc(e.source_mechanism)}.${esc(e.source_port)} → ${esc(e.target_mechanism)}.${esc(e.target_port)}`).join('<br/>')}</p><p><b>SOURCE AND PROCESS SCOPE</b><br/>The original tensor/router chain is replaced with a new evidence producer and executable decision consumer. The other native researcher-world activities remain. These are literal recorded wires, not an inferred process diagram.</p>`;
  el('source-inspector').innerHTML=nodes.filter(node=>['review-evidence','world.selection'].includes(node.mechanism_id)).map(node=>`<article><div><span>ACTUAL INSTALLED SOURCE</span><strong>${esc(node.mechanism_id)}</strong><small>${esc(node.implementation)}</small></div><pre>${esc(node.parameters.code_artifact.source)}</pre></article>`).join('');
  el('raw-update').textContent=JSON.stringify(update,null,2);
  if(estimator&&step.generation===1){const note=document.createElement('p');note.textContent='FINAL BATCH UPDATE: no subsequent policy or next batch was evaluated within this budget.';el('endpoint-detail').querySelector('.gradient-pane')?.append(note);}
}
function render():void{
  const fixture=data.classification==='scripted-fixture-not-native-results';
  if(fixture)document.body.dataset.fixture='scripted-v11';
  el('truth-badge').textContent=fixture?'SCRIPTED FIXTURE / NOT QWEN':'AUDITED ACTUAL DEVELOPMENT';el('truth-badge').dataset.mode=fixture?'fixture':'actual';
  el('identity-strip').innerHTML=[['OBJECTIVE',data.objective.formula,'fixed objective · no additional promotion veto'],['PHYSICAL WORLDS','8 COMPLETE · NO REUSE','two methods × two generations × two draws'],['RESEARCHER REPLIES',String(data.physical_researcher_responses),'Qwen3:8B actual replies · fixed weights'],['AUTHORSHIP','EXTERNAL CODEX PILOT','self-reported · not autonomous invention']].map(([k,v,note])=>`<div><span>${esc(k)}</span><strong>${esc(v)}</strong><small>${esc(fixture?'SCRIPTED SCHEMA FIXTURE':note)}</small></div>`).join('');
  const facts=[['CAMPAIGN',data.campaign_id],['SOURCE COMMIT',data.source_binding.source_commit],['AUDIT FILE SHA256',data.source_binding.report_file_sha256],['AUDIT CONTENT SHA256',data.source_binding.report_content_sha256],['RAW INVENTORY',data.raw_inventory_sha256],['PHYSICAL REPLIES',data.physical_researcher_responses],['BASELINES','NONE SCORED · NO HISTORICAL BEST'],['CLAIM BOUNDARY','NO SUPERIORITY · NO VARIANCE REDUCTION · NO WORLD DERIVATIVE']];
  el('provenance').innerHTML=facts.map(([k,v])=>`<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`).join('');
  el('limitations').innerHTML=[...data.limitations,'G1 deliberately retains the same conditional algorithms / wiring for prior-fit compatibility; it does not invent a new source family.'].map(s=>`<p>${esc(s)}</p>`).join('');
  paths();detail();el('evidence').hidden=false;el('footer-source').textContent='IMMUTABLE EXPORTED AUDIT / HASH-VERIFIED PAYLOAD';
}
async function boot():Promise<void>{
  try{
    const response=await fetch('./data/native-open-estimators-v11.availability.json');if(!response.ok)throw new Error('Availability manifest missing.');const available=await response.json();
    if(available.schema!=='scienceutopia.open-estimator-availability.v11')throw new Error('Unknown availability contract.');
    if(available.status!=='available')throw new Error(available.message??'Awaiting a completed actual v11 audit export.');
    if(available.payload!=='native-open-estimators-v11.ui.json'||available.receipt!=='native-open-estimators-v11.ui-receipt.json')throw new Error('Unrecognized evidence paths.');
    const [payload,receipt]=await Promise.all([fetch(`./data/${available.payload}`),fetch(`./data/${available.receipt}`)]);if(!payload.ok||!receipt.ok)throw new Error('Complete export is unavailable.');
    data=await verifyOpenEstimator(await payload.text(),await receipt.json(),new URLSearchParams(location.search).get('fixture')==='scripted-v11');render();
    if(new URLSearchParams(location.search).get('focus')==='paths')document.body.dataset.focus='paths';
  }catch(error){el('truth-badge').textContent='NO AUDITED EXPORT';el('unavailable').hidden=false;el('unavailable-message').textContent=error instanceof Error?error.message:String(error);}
}
void boot();
