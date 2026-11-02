import { generatedPythonNode, generatedSourceBody, recordedParentSystem, REDESIGN_OBJECTIVES, verifyOpenRedesign, type Evidence } from './openRedesignContract';
import { NESTED_OBJECTIVES, nestedStageLabel, verifyNestedFoundry } from './nestedFoundryContract';
import { initializeFoundryBranch } from './foundryBranch';
import { initializeNestedSignal } from './nestedFoundrySignal';
import './objectiveStructure.css';
import './openRedesign.css';
import './nestedFoundry.css';

const el = (id: string): HTMLElement => {const value = document.getElementById(id);if (!value) throw new Error(`Missing ${id}`);return value;};
const esc = (value: unknown): string => String(value ?? '—').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const list = (value: unknown): Evidence[] => Array.isArray(value) ? value : [];
const score = (value: number | null): string => value === null ? 'NULL' : Number.isInteger(value) ? String(value) : value.toFixed(4).replace(/0+$/,'').replace(/\.$/,'');
const short = (value: unknown, size = 13): string => typeof value === 'string' && value.length > size ? `${value.slice(0,size)}…` : String(value ?? '—');
const nested=new URLSearchParams(location.search).get('campaign')==='v13';
const objectives:readonly string[]=nested?NESTED_OBJECTIVES:REDESIGN_OBJECTIVES;
const labels = nested?['THROUGHPUT','REVIEWED PRODUCTION EFFICIENCY']:['THROUGHPUT','NET REVIEWED UTILITY'];
const formulas = nested?['L = −A','L = −Q + 0.5R']:['L = −A','L = 3.25A − Q + 0.05R'];
let data: Evidence, selectedArm = 0, selectedGeneration = 0, selectedNode = '', selectedWire = -1;
let tab: 'source' | 'protocol' | 'process' | 'native' = 'source';
const armId = (): string => objectives[selectedArm]!;
const row = (): Evidence => data.arms[armId()].observations[selectedGeneration]!;
const stageLabel=(r:Evidence):string=>nested?nestedStageLabel(r):`G${r.generation}`;

function plot(rows: Evidence[]): string {
  const values = rows.filter(r => r.own_loss !== null).map(r => r.own_loss!);
  if (!values.length) return '<p class="foundry-empty">NO COMPLETE LOSS ENDPOINT</p>';
  const width = 370, height = 155, left = 48, top = 20, bottom = 32, right = 15;
  const padding = Math.max(.2,(Math.max(...values)-Math.min(...values))*.15), lo = Math.min(...values)-padding, hi = Math.max(...values)+padding;
  const x = (g: number) => left+(width-left-right)*g/Math.max(1,rows.length-1);
  const y = (v: number) => top+(height-top-bottom)*(hi-v)/(hi-lo);
  const path = (key: 'own_loss' | 'running_best') => rows.map((r,i) => r[key] === null ? '' : `${i && rows[i-1]?.[key] !== null ? 'L' : 'M'}${x(i)} ${y(r[key])}`).join(' ');
  return `<svg class="redesign-plot" viewBox="0 0 ${width} ${height}" role="img" aria-label="Own loss and running best for this objective only">${[lo,(lo+hi)/2,hi].map(v=>`<path d="M${left} ${y(v)}H${width-right}" stroke="#2b3e59"/><text x="${left-8}" y="${y(v)+3}" text-anchor="end">${score(v)}</text>`).join('')}<path class="best-line" d="${path('running_best')}"/><path class="loss-line" d="${path('own_loss')}"/>${rows.map((r,i)=>r.own_loss===null?'':`<circle cx="${x(i)}" cy="${y(r.own_loss)}" r="4"/>`).join('')}${rows.map((r,i)=>`<text x="${x(i)}" y="${height-10}" text-anchor="middle">${nested?r.draw_index===null?'ERROR':r.stage==='initial-batch'?`D${r.draw_index+1}`:r.stage==='updated-proposal'?'POST':'G1':stageLabel(r)}</text>`).join('')}</svg>`;
}
function renderPaths(): void {
  el('objective-paths').innerHTML = objectives.map((id,index)=>{
    const arm = data.arms[id];
    const rows:Evidence[] = arm.observations;
    const ties = arm.incumbents?.best_observation_ties ?? [];
    return `<article class="redesign-arm" data-arm="${index}"><div class="redesign-arm-label"><span>${labels[index]} / MINIMIZE</span><h3>${formulas[index]}</h3><p>${nested?'Free G0 → two native draws → one conditional LR/LOO update → one fresh forward → free G1. No cross-arm feedback.':"External code redesign from this arm's own preceding observations. No cross-arm feedback."}</p><b>OBSERVED BEST ${score(rows.at(-1)?.running_best ?? null)}<br/>${ties.length} EXACT BEST TIE${ties.length===1?'':'S'} · NO INITIAL SCORE</b></div><div class="redesign-stations">${rows.map((r,i)=>`<button type="button" class="redesign-station" data-arm="${index}" data-generation="${i}" aria-pressed="${selectedArm===index&&selectedGeneration===i}" data-failed="${r.status!=='complete'}"><span>${stageLabel(r)} / ${r.status==='complete'?'NATIVE ENDPOINT':esc(r.status.toUpperCase())}</span><strong>L ${score(r.own_loss)}</strong><em>BEST ${score(r.running_best)}</em><small>${esc(short(r.system_fingerprint))}</small></button>`).join('')}</div>${plot(rows)}</article>`;
  }).join('');
  el('objective-paths').querySelectorAll<HTMLButtonElement>('.redesign-station').forEach(button=>button.addEventListener('click',()=>{
    selectedArm=Number(button.dataset.arm);selectedGeneration=Number(button.dataset.generation);selectedNode='';selectedWire=-1;renderAll();
  }));
}
const edgeKey = (edge: Evidence): string => [edge.source_mechanism,edge.source_port,edge.target_mechanism,edge.target_port].join(' / ');
function nodeAsset(node: Evidence): string {
  const key = `${node.mechanism_id} ${node.family}`.toLowerCase();
  return key.includes('fund')?'system-funding':key.includes('publication')?'institution-publication':key.includes('review')||key.includes('evaluat')?'institution-review':key.includes('govern')?'system-government':key.includes('communication')?'system-communication':node.implementation==='code.python.v1'?'native-foundry-control-room':'institution-lab';
}
function renderCircuit(): void {
  const selected = row(), system = selected.system;
  el('circuit-title').textContent=`${labels[selectedArm]} / ${nested?stageLabel(selected):`GENERATION ${selected.generation}`}`;
  el('selected-fingerprint').textContent=selected.system_fingerprint??'NO EXECUTABLE SYSTEM';
  el('selected-summary').innerHTML=`<span>OWN LOSS <b>${score(selected.own_loss)}</b></span><span>RUNNING BEST <b>${score(selected.running_best)}</b></span><span>PARENT <b>${esc(short(selected.parent_system_fingerprint,18))}</b></span><span>STATUS <b>${esc(selected.status.toUpperCase())}</b></span>`;
  if (!system) {el('system-circuit').innerHTML='<p class="foundry-empty">NO EXECUTABLE CANDIDATE / NO GRAPH INFERRED</p>';el('wire-list').innerHTML='';el('change-ledger').innerHTML='<p>Generation or execution failure is retained. Null loss is not a bad numerical score.</p>';renderInspector();return;}
  const nodes=list(system.mechanisms), edges=list(system.connections), diff=selected.lineage.vs_parent, columns=Math.min(5,Math.max(1,Math.ceil(Math.sqrt(nodes.length*1.4))));
  const width=1000, cell=width/columns, height=Math.max(310,Math.ceil(nodes.length/columns)*160+40);
  const position=new Map<string,[number,number]>(nodes.map((node,index)=>[node.mechanism_id,[cell*(index%columns+.5),75+Math.floor(index/columns)*160]]));
  if (!nodes.some(node=>node.mechanism_id===selectedNode)) selectedNode=nodes.find(node=>generatedPythonNode(node))?.mechanism_id??nodes[0]?.mechanism_id??'';
  const addedEdges=new Set((diff.edges_added??[]).map((e: any)=>Array.isArray(e)?e.join(' / '):edgeKey(e)));
  const wires=edges.map((edge,index)=>{
    const a=position.get(edge.source_mechanism), b=position.get(edge.target_mechanism);if(!a||!b)return '';
    const sx=a[0]+52,sy=a[1],tx=b[0]-52,ty=b[1];
    const d=sy===ty&&tx>sx?`M${sx} ${sy}H${tx}`:`M${sx} ${sy}C${sx+55} ${sy+42},${tx-55} ${ty-42},${tx} ${ty}`;
    return `<path class="circuit-wire${addedEdges.has(edgeKey(edge))?' added':''}${selectedWire===index?' selected':''}" d="${d}" marker-end="url(#wire-arrow)"/><circle class="circuit-port" cx="${sx}" cy="${sy}" r="4"/><circle class="circuit-port" cx="${tx}" cy="${ty}" r="4"/>`;
  }).join('');
  const nodeSvg=nodes.map(node=>{
    const [x,y]=position.get(node.mechanism_id)!;
    const added=(diff.nodes_added??[]).includes(node.mechanism_id),changed=(diff.source_changes??[]).some((v:Evidence)=>v.mechanism_id===node.mechanism_id);
    return `<g class="circuit-node${added?' added':''}${changed?' changed':''}${selectedNode===node.mechanism_id?' selected':''}" transform="translate(${x-53} ${y-47})" role="button" tabindex="0" data-node="${esc(node.mechanism_id)}" aria-label="Inspect ${esc(node.mechanism_id)}"><rect x="-5" y="-7" width="116" height="126" rx="1"/><image href="./assets/noctiluca/production/${nodeAsset(node)}.svg" x="3" y="0" width="100" height="85"/><text x="53" y="98" text-anchor="middle">${esc(short(node.mechanism_id,22))}</text><text class="node-caption" x="53" y="111" text-anchor="middle">${esc(short(node.implementation,26))}</text></g>`;
  }).join('');
  el('system-circuit').innerHTML=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Actual installed ${nodes.length}-node ${edges.length}-wire institutional graph; positions are schematic"><defs><marker id="wire-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#9fb4cc"/></marker></defs><g>${wires}</g><g>${nodeSvg}</g></svg>`;
  el('system-circuit').querySelectorAll<SVGElement>('[data-node]').forEach(element=>{
    const activate=()=>{selectedNode=element.dataset.node!;selectedWire=-1;renderCircuit();};element.addEventListener('click',activate);element.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();activate();}});
  });
  el('wire-list').innerHTML=edges.map((edge,index)=>`<button type="button" data-wire="${index}" aria-pressed="${selectedWire===index}">${esc(edge.source_mechanism)}.<b>${esc(edge.source_port)}</b> → ${esc(edge.target_mechanism)}.<b>${esc(edge.target_port)}</b></button>`).join('');
  el('wire-list').querySelectorAll<HTMLButtonElement>('button').forEach(button=>button.addEventListener('click',()=>{selectedWire=Number(button.dataset.wire);selectedNode=edges[selectedWire]!.target_mechanism;tab='protocol';renderCircuit();}));
  const counts=diff.counts??{};
  const groups=[['NODES',`+${counts.nodes_added??0} / −${counts.nodes_removed??0}`,[...(diff.nodes_added??[]).map((v:string)=>`+ ${v}`),...(diff.nodes_removed??[]).map((v:string)=>`− ${v}`)]],['WIRES',`+${counts.edges_added??0} / −${counts.edges_removed??0}`,(diff.edges_added??[]).map((v:any)=>Array.isArray(v)?`${v[0]}.${v[1]} → ${v[2]}.${v[3]}`:edgeKey(v))],['SOURCE BODIES',`+${counts.source_bodies_added??0} / −${counts.source_bodies_removed??0}`,(diff.source_changes??[]).map((v:Evidence)=>`${v.mechanism_id} ${short(v.before_sha256,8)} → ${short(v.after_sha256,8)}`)],['PROTOCOL / CONFIG',`${counts.protocol_changes??0} / ${counts.mechanism_configuration_changes??0}`,(diff.protocol_changes??[]).map((v:Evidence)=>v.mechanism_id)],['PROCESS / SCHEDULE',`+${counts.schedules_added??0} / −${counts.schedules_removed??0}`,[]]];
  el('change-ledger').innerHTML=`<span>EXACT DIFF / VS RECORDED PARENT</span><h3>${nodes.length} NODES · ${edges.length} WIRES</h3><p>Literal executed design changes. A changed file or wire is not by itself a beneficial or causally isolated intervention.</p>${groups.map(([title,value,items])=>`<section><b>${title}</b><strong>${value}</strong><small>${(items as string[]).map(esc).join('<br/>')||'NO ITEMS IN THIS DIFF'}</small></section>`).join('')}`;
  renderInspector();
}
function codeMarkup(source: string, other: string, state: 'added'|'removed'): string {
  const existing=new Set(other.split('\n'));
  return source.split('\n').map(line=>existing.has(line)?esc(line):`<span class="code-${state}">${esc(line)||' '}</span>`).join('\n');
}
function renderInspector(): void {
  const selected=row(),node=list(selected.system?.mechanisms).find(n=>n.mechanism_id===selectedNode);
  const parentSystem=recordedParentSystem(data,armId(),selected);
  const previousNode=list(parentSystem?.mechanisms).find(n=>n.mechanism_id===selectedNode),edge=list(selected.system?.connections)[selectedWire];
  el('node-title').textContent=edge?`${edge.source_mechanism}.${edge.source_port} → ${edge.target_mechanism}.${edge.target_port}`:selectedNode||'NO CANDIDATE NODE';
  el('inspector-tabs').querySelectorAll<HTMLButtonElement>('[data-tab]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.tab===tab)));
  const pane=(title:string,body:unknown)=>`<article><h4>${esc(title)}</h4><pre>${esc(typeof body==='string'?body:JSON.stringify(body,null,2))}</pre></article>`;
  if(tab==='source'){
    const source=generatedSourceBody(node),before=generatedSourceBody(previousNode);
    el('inspector-content').innerHTML=source?`<article><h4>RECORDED PARENT / SAME NODE ID${before?'':' / NO PRIOR BODY'}</h4><pre>${before?codeMarkup(before,source,'removed'):'NO PRIOR SAME-ID SOURCE BODY / renamed bodies remain separate in exact lineage'}</pre></article><article><h4>ACTUAL INSTALLED SOURCE / ${esc(node?.implementation)}${node?.implementation==='native.process.activity.v1'?` / DELEGATE ${esc(generatedPythonNode(node)?.mechanism_id)}`:''}</h4><pre>${codeMarkup(source,before,'added')}</pre></article><p>Line coloring is a text-membership aid, not a semantic or full edit-distance diff. Exact body hashes, renames and execution receipts are recorded in the audited lineage.</p>`:pane('NATIVE IMPLEMENTATION / NO GENERATED PYTHON BODY',node??'No candidate source');
  }else if(tab==='protocol'){
    el('inspector-content').innerHTML=pane('ACTUAL SELECTED NODE / INPUT-OUTPUT CONTRACT',node??null)+pane('ACTUAL SELECTED WIRE / NO INFERRED CONNECTION',edge??'Select a literal port-to-port wire below the circuit.');
  }else if(tab==='process'){
    el('inspector-content').innerHTML=pane('ACTUAL SYSTEM SCHEDULES / PROCESS CONTRACTS',{schedules:selected.system?.schedules??null,processes:selected.contracts?.processes??null})+pane('EXACT PROCESS / PROTOCOL LINEAGE',selected.lineage??null)+'<p>Schedules and process declarations are literal candidate records. The graph layout does not claim spatial coordinates, event timing, or measured activity.</p>';
  }else{
    el('inspector-content').innerHTML=pane('ACTUAL NATIVE METRICS / ORIGINAL RECORDS',selected.metrics??null)+pane('EXECUTED SOURCE / NATIVE CONTEXT / PHYSICAL RECEIPTS',selected.physical_proof??null)+'<p>Receipts establish the recorded code and context were executed. They do not by themselves identify a causal institutional effect. Cross-objective cells reuse this same world.</p>';
  }
}
function renderProfiles(): void {
  el('cross-profiles').innerHTML=`<table><caption class="sr-only">All recorded systems rescored under both explicit development losses</caption><thead><tr><th>DESIGNED UNDER / STAGE</th>${formulas.map((formula,i)=>`<th>${labels[i]}<br/>${formula}</th>`).join('')}<th>ORIGINAL NATIVE RECORDS<br/>A / Q / R</th></tr></thead><tbody>${objectives.map((id,a)=>data.arms[id].observations.map((r:Evidence,g:number)=>`<tr data-arm="${a}" data-selected="${a===selectedArm&&g===selectedGeneration}"><td>${labels[a]} / ${stageLabel(r)}<small>${esc(short(r.observation_id,25))} / ${esc(r.status)}</small></td>${objectives.map(target=>`<td data-own="${id===target}"><strong>${score(r.cross_scores[target])}</strong><small>${id===target?'OWN LOSS':'SAME-WORLD CROSS-SCORE'}</small></td>`).join('')}<td>${['native.accepted_decisions','native.accepted_peer_score_sum','native.review_records'].map(key=>{const metric=r.metrics?.[key];return score(typeof metric==='number'?metric:metric?.value??null);}).join(' / ')}</td></tr>`).join('')).join('')}</tbody></table>`;
}
function renderAll(): void {renderPaths();renderCircuit();renderProfiles();el('raw-row').textContent=JSON.stringify(row(),null,2);if(nested)initializeNestedSignal(el('nested-signal'),data,armId(),row(),id=>{selectedNode=id;tab='native';renderCircuit();});}
function render(): void {
  const fixture=data.classification==='scripted-fixture-not-native-results';if(fixture)document.body.dataset.fixture=nested?'scripted-v13':'scripted-v12';
  el('truth-badge').textContent=fixture?'SCRIPTED FIXTURE / NOT QWEN':'AUDITED ACTUAL DEVELOPMENT';el('truth-badge').dataset.mode=fixture?'fixture':'actual';
  const replyNote=data.physical_researcher_responses>0?'Observed fixed-weight Qwen3:8B replies':'Qwen3:8B configured / no replies observed';
  el('identity-strip').innerHTML=[['OBJECTIVES','TWO EXPLICIT LOSSES','No hidden fairness or quality veto'],['NATIVE WORLDS',`${data.physical_native_worlds} COMPLETE / ${nested?'EIGHT':'SIX'} ATTEMPTS`,nested?'2 inner + 1 updated + 1 redesigned per objective':'Three generations per objective'],['PHYSICAL REPLIES',String(data.physical_researcher_responses),replyNote],['DESIGNER','EXTERNAL CODEX PILOT','Not authenticated autonomous invention']].map(([title,value,note])=>`<div><span>${title}</span><strong>${esc(value)}</strong><small>${fixture?'SCRIPTED SCHEMA FIXTURE':note}</small></div>`).join('');
  const facts=[['SOURCE COMMIT',data.source_binding.source_commit],['AUDIT FILE SHA256',data.source_binding.report_file_sha256],['AUDIT CONTENT SHA256',data.source_binding.report_content_sha256],['RAW INVENTORY SHA256',data.raw_inventory_sha256],['INITIAL / HISTORICAL BASELINE','NONE SCORED'],['HELD-OUT EVALUATION','NONE / SAME-WORLD DEVELOPMENT SCORES'],['LIVE CONTROL','DISABLED / NO DISPATCH'],['CLAIM BOUNDARY','NO SCIENTIFIC-VALUE OR CAUSAL-BENEFIT CLAIM']];
  if(nested)facts.push(['SCHEDULED NATIVE SLOTS',`${data.consumed_native_slots??'UNKNOWN'} CONSUMED / ${data.planned_native_world_budget??'UNKNOWN'} RESERVED`],['ACTUAL WORLD DIRECTORIES',String(data.physical_world_directory_count??'UNKNOWN')],['COMPLETED NATIVE DRAWS',String(data.logical_completed_draws??'UNKNOWN')]);
  el('provenance').innerHTML=facts.map(([title,value])=>`<div><dt>${esc(title)}</dt><dd>${esc(value)}</dd></div>`).join('');
  el('limitations').innerHTML=[...(data.limitations??[]),'Designer sees its own arm history; one development seed does not establish generalization.','Free executable representation does not mean unconstrained or automatically successful institution invention.'].map(s=>`<p>${esc(s)}</p>`).join('');
  objectives.forEach((_id,index)=>{if(!data.arms[objectives[selectedArm]!].observations.length)selectedArm=index;});
  if(!data.arms[armId()].observations.length)throw new Error('No recorded attempt available');
  el('evidence').hidden=false;renderAll();el('footer-source').textContent='ACTUAL SOURCE-BOUND AUDIT / IMMUTABLE EXPORTED VIEW';
  if(nested)initializeFoundryBranch(el('foundry-branch'),()=>({row:row(),objective:armId(),loss:data.loss_specs[armId()],binding:data.source_binding,fixture,unsafeSystemIntegerPaths:data.numeric_encoding.paths.filter((path:string)=>path.startsWith(`/arms/${armId()}/observations/${selectedGeneration}/system/`))}));
}
el('inspector-tabs').querySelectorAll<HTMLButtonElement>('[data-tab]').forEach(button=>button.addEventListener('click',()=>{tab=button.dataset.tab as typeof tab;renderInspector();}));
async function boot(): Promise<void> {
  try {
    if(nested){
      document.body.dataset.campaign='v13';document.title='NOCTILUCA // Nested Institution Foundry V13';
      document.querySelector('.os-mark>span')!.textContent='INSTITUTION FOUNDRY // V13';
      const previous=document.querySelector<HTMLAnchorElement>('.os-topbar>a:last-of-type')!;previous.textContent='V12 FREE REDESIGN ↗';previous.href='./native-objective-redesign.html';
      document.querySelector('.foundry-copy>.eyebrow')!.textContent='INVENT THE SYSTEM. TUNE IT. RETURN TO INVENTION.';
      document.querySelector('.foundry-copy>p:last-of-type')!.textContent='Free institutional code and wiring, conditional expected-loss optimization, then a new design from actual feedback. Same original researcher world. Same fixed Qwen weights.';
      document.querySelector('#redesign-paths h2')!.textContent='ONE CONTINUOUS DESIGN LOOP.';
      document.querySelector('#unavailable>b')!.textContent='NO AUDITED V13 EXPORT AVAILABLE';
      const signal=document.createElement('section');signal.id='nested-signal';signal.className='os-board nested-signal-board';document.querySelector('.circuit-board')!.before(signal);
      const draft=document.createElement('section');draft.id='foundry-branch';draft.className='os-board foundry-branch-board';document.querySelector('.profile-board')!.before(draft);
    }else{
      const next=document.createElement('a');next.href='./native-objective-redesign.html?campaign=v13';next.textContent='V13 NESTED DESIGN LOOP ↗';document.querySelector('.os-topbar')!.append(next);
    }
    const prefix=nested?'native-nested-search-v13':'native-objective-redesign-v12';
    const response=await fetch(`./data/${prefix}.availability.json`);if(!response.ok)throw new Error('Availability manifest missing');const available=await response.json();
    if(available.schema!==(nested?'scienceutopia.nested-foundry-availability.v13':'scienceutopia.open-redesign-availability.v12'))throw new Error('Unknown availability contract');
    if(available.status!=='available')throw new Error(available.message??'Awaiting independent actual audit export');
    if(available.payload!==`${prefix}.ui.json`||available.receipt!==`${prefix}.ui-receipt.json`)throw new Error('Unrecognized evidence paths');
    const [payload,receipt]=await Promise.all([fetch(`./data/${available.payload}`),fetch(`./data/${available.receipt}`)]);if(!payload.ok||!receipt.ok)throw new Error('Complete export unavailable');
    const fixture=new URLSearchParams(location.search).get('fixture')===(nested?'scripted-v13':'scripted-v12');
    data=nested?await verifyNestedFoundry(await payload.text(),await receipt.json(),fixture):await verifyOpenRedesign(await payload.text(),await receipt.json(),fixture);render();
    const focus=new URLSearchParams(location.search).get('focus');if(focus==='paths'||focus==='circuit'||nested&&['signal','draft'].includes(focus??''))document.body.dataset.focus=focus!;
  }catch(error){el('evidence').hidden=true;el('truth-badge').textContent='NO AUDITED EXPORT';el('unavailable').hidden=false;el('unavailable-message').textContent=error instanceof Error?error.message:String(error);}
}
void boot();
