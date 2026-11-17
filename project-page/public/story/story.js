import{pathSeries,accountingContrast}from'./model.js';
const scopes={
 parameters:{title:'Change a value, keep the rule.',copy:'Adjust a funding fraction without replacing the allocation algorithm.',code:'funding.fraction = 0.30 → 0.50',accent:'funding'},
 algorithm:{title:'Replace the executable rule.',copy:'Change how an evaluation mechanism makes decisions, rather than only tuning a threshold.',code:'evaluation.rule = f → g',accent:'evaluation'},
 mechanism:{title:'Introduce a new mechanism.',copy:'Add a knowledge commons and give it explicit inputs, outputs and an implementation.',code:'system.add(knowledge_commons)',accent:'commons'},
 wiring:{title:'Change who sees what, and when.',copy:'Explore sharing before evaluation instead of evaluation before sharing.',code:'research → publication → evaluation',accent:'publication'}
};
function diagram(scope){
 const active=scopes[scope].accent;
 const node=(key,x,y,w,label,sub,h=65)=>`<g><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="3" fill="${active===key?'#e0ebd8':'#f5f7ef'}" stroke="${active===key?'#177b71':'#bdcbb7'}" stroke-width="${active===key?2:1}"/><text x="${x+w/2}" y="${y+(h===65?27:18)}" text-anchor="middle">${label}</text><text x="${x+w/2}" y="${y+(h===65?46:34)}" class="svg-small" text-anchor="middle">${sub}</text></g>`;
 const normal='<path d="M157 130H197M329 130H369"/>';
 const wiring='<path d="M157 145V188H436V166M436 99V65H264V97"/>';
 const commons=scope==='mechanism'?'<path d="M92 99V65H197M329 65H436V97"/>':'';
 return `<svg viewBox="0 0 540 330" role="img" aria-label="${scopes[scope].title} Illustrative diagram, not a native execution."><defs><marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#76907c"/></marker></defs><rect x="8" y="8" width="524" height="314" rx="4" fill="#eef2e6" stroke="#d8e0ce"/><text x="26" y="30" class="svg-small">SCIENTIFIC SYSTEM / EXPLANATORY DESIGN SPACE</text><g fill="none" stroke="#76907c" stroke-width="1.6" marker-end="url(#arrow)">${scope==='wiring'?wiring:normal}${commons}<path d="M264 242V166"/></g>${node('research',27,99,130,'Research','responsive agents')}${node('evaluation',199,99,130,'Evaluation',scope==='algorithm'?'rule: g':'rule: f')}${node('publication',371,99,130,'Publication','shared artifacts')}${node('funding',199,242,130,'Funding',scope==='parameters'?'fraction: 0.50':'fraction: 0.30')}${scope==='mechanism'?node('commons',199,42,130,'Knowledge commons','new mechanism',45):''}<text x="32" y="220" class="svg-small">ILLUSTRATION ONLY</text><text x="32" y="234" class="svg-small">NO MODEL CALLS</text></svg>`;
}
function selectScope(scope){
 const value=scopes[scope];document.querySelector('#design-title').textContent=value.title;document.querySelector('#design-copy').textContent=value.copy;document.querySelector('#design-code').textContent=value.code;document.querySelector('#design-graph').innerHTML=diagram(scope);
 document.querySelectorAll('[data-scope]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.scope===scope)));
}
document.querySelectorAll('[data-scope]').forEach(button=>button.addEventListener('click',()=>selectScope(button.dataset.scope)));
selectScope('parameters');
const names={'uniform-priority':'Uniform priority','adaptive-priority':'Adaptive priority','free-code-graph':'Free code / graph'};
const colors={'uniform-priority':'#177b71','adaptive-priority':'#8a719e','free-code-graph':'#bd643c'};
let evidence,objective='content-utility';
const format=value=>value===null?'Execution null':Number(value.toFixed(4)).toString();
function draw(){
 if(!evidence)return;
 const mode=document.querySelector('#path-view').value,rows=pathSeries(evidence.search,objective,mode),values=rows.flatMap(row=>row.gaps.filter(value=>value!==null));
 const width=matchMedia('(max-width:760px)').matches?510:930;
 const high=Math.max(1,...values)*1.12,x=i=>78+i*(width-141)/3,y=value=>255-value/high*215;
 const parts=[`<svg viewBox="0 0 ${width} 305" role="img" aria-labelledby="loss-title loss-desc"><title id="loss-title">Gap to the strong reference across four proposals</title><desc id="loss-desc">Zero matches the strong reference. Lower is better. The null is not a measured score. Every submitted value is in the table below.</desc>`];
 for(let i=0;i<5;i++){const v=high*i/4,py=y(v);parts.push(`<line x1="67" x2="${width-30}" y1="${py}" y2="${py}" stroke="#dce3d5"/><text x="53" y="${py+4}" text-anchor="end">${format(v)}</text>`);}
 parts.push(`<line x1="67" x2="${width-30}" y1="255" y2="255" stroke="#6e8168" stroke-dasharray="5 5"/><text x="${width-35}" y="247" text-anchor="end">STRONG REFERENCE</text>`);
 for(let i=0;i<4;i++)parts.push(`<text x="${x(i)}" y="287" text-anchor="middle">g${i}</text>`);
 rows.forEach(row=>{
   const offset=row.method==='uniform-priority'?-4:row.method==='adaptive-priority'?0:4;
   for(let i=1;i<4;i++)if(row.gaps[i]!==null&&row.gaps[i-1]!==null)parts.push(`<line x1="${x(i-1)+offset}" x2="${x(i)+offset}" y1="${y(row.gaps[i-1])}" y2="${y(row.gaps[i])}" stroke="${colors[row.method]}" stroke-width="2.3" opacity=".8"/>`);
   row.gaps.forEach((gap,i)=>{
    if(gap===null){parts.push(`<text x="${x(i)}" y="65" text-anchor="middle">× execution null</text>`);return;}
    const label=`${names[row.method]} g${i}: ${mode==='candidate'?'submitted loss':'best own loss'} ${format(row.values[i])}${row.carried[i]?' (carried across an execution null)':''}`;
    parts.push(`<circle data-method="${row.method}" data-generation="${i}" cx="${x(i)+offset}" cy="${y(gap)}" r="5" fill="${row.carried[i]?'#fcfcf7':colors[row.method]}" stroke="${colors[row.method]}" stroke-width="1.5" role="button" tabindex="0" aria-label="${label}"><title>${label}</title></circle>`);
   });
 });parts.push('</svg>');document.querySelector('#story-chart').innerHTML=parts.join('');
 document.querySelector('#story-loss-definition').textContent=objective==='content-utility'?'Lᵤ = −U':'L꜀ = −U + 0.1 K_collected';
 document.querySelector('#path-explanation').textContent=mode==='candidate'?'Every point is a submitted candidate. The missing execution has no numeric loss; no line bridges it.':'Best own so far excludes supplied references. An outlined point carries the previous measured best across the execution null; it is not a successful candidate.';
 document.querySelector('#point-detail').textContent='Select a plotted point to inspect its actual submitted loss.';
 document.querySelectorAll('#story-chart circle').forEach(circle=>{
   const inspect=()=>{const row=rows.find(row=>row.method===circle.dataset.method),i=Number(circle.dataset.generation);document.querySelector('#point-detail').textContent=`${names[row.method]} · g${i} · Submitted: ${format(row.raw[i])} · ${mode==='incumbent'?'Best own: '+format(row.values[i])+' · ':''}Reference: ${format(evidence.search.reference_minima[objective])}${row.carried[i]?' · Carried incumbent, not a measured candidate.':''}`;};
   circle.addEventListener('click',inspect);circle.addEventListener('focus',inspect);circle.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();inspect();}});
 });
 document.querySelector('#story-table').innerHTML=`<table><caption>Actual submitted losses, regardless of chart display mode; lower is better.</caption><thead><tr><th scope="col">Method</th>${[0,1,2,3].map(i=>`<th scope="col">g${i}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr><th scope="row">${names[row.method]}</th>${row.raw.map(value=>`<td>${format(value)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}
document.querySelectorAll('[data-story-objective]').forEach(button=>button.addEventListener('click',()=>{objective=button.dataset.storyObjective;document.querySelectorAll('[data-story-objective]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));draw();}));
document.querySelector('#path-view').addEventListener('change',draw);
function ledger(){
 const weight=Number(document.querySelector('#cost-weight').value);document.querySelector('#weight-value').textContent=weight.toFixed(2);
 if(!evidence)return;const contrast=accountingContrast(evidence.controls,weight);document.querySelector('#cost-delta').textContent=(contrast.delta<0?'−':'')+Math.abs(contrast.delta).toFixed(2);
}
document.querySelector('#cost-weight').addEventListener('input',ledger);
fetch('evidence.json').then(response=>{if(!response.ok)throw Error('Article evidence unavailable');return response.json();}).then(data=>{evidence=data;draw();ledger();}).catch(()=>{document.querySelector('#story-chart').textContent='The evidence file could not be loaded. No values inferred. See the original records below.';document.querySelector('#cost-delta').textContent='Unavailable';});
function progress(){const height=document.documentElement.scrollHeight-innerHeight;document.querySelector('#reading-progress').style.width=(height>0?Math.min(100,Math.max(0,scrollY/height*100)):0)+'%';}
addEventListener('scroll',progress,{passive:true});addEventListener('resize',()=>{progress();draw();});progress();
