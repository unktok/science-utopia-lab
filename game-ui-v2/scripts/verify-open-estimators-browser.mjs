import { createHash } from 'node:crypto';
import { spawn,execFileSync } from 'node:child_process';
import { mkdir,mkdtemp,readFile,rename,writeFile } from 'node:fs/promises';
import { homedir,tmpdir } from 'node:os';
import { basename,join,resolve } from 'node:path';
import { fixtureAudit } from '../test/openEstimatorFixture.ts';
const args=Object.fromEntries(process.argv.slice(2).map(s=>{const [k,...v]=s.replace(/^--/,'').split('=');return [k,v.join('=')];}));
const mode=args.mode??'unavailable',port=Number(args.port??4330),base=`http://127.0.0.1:${port}`;
if(!['actual','fixture','unavailable'].includes(mode)||!Number.isInteger(port)||port<1024||port>65535)throw new Error('Invalid mode/port');
const sha=b=>createHash('sha256').update(b).digest('hex'),sleep=ms=>new Promise(r=>setTimeout(r,ms));
const output=resolve(args.output??(mode==='fixture'?await mkdtemp(join(tmpdir(),'noctiluca-v11-fixture-qa-')):`screenshots/open-estimators-v11-${mode}-qa`));
if(mode==='fixture'&&!output.startsWith(`${resolve(tmpdir())}/`))throw new Error('Fixture screenshots must stay temporary');
async function waitFor(fn,label){for(let i=0;i<100;i++){try{const v=await fn();if(v)return v;}catch{}await sleep(100);}throw new Error(`Timed out ${label}`);}
class Cdp{
  constructor(url){this.url=url;this.pending=new Map();this.id=0;this.events=[];}
  async open(){this.socket=new WebSocket(this.url);await new Promise((r,j)=>{this.socket.onopen=r;this.socket.onerror=j;});this.socket.onmessage=({data})=>{const m=JSON.parse(data);if(m.id&&this.pending.has(m.id)){this.pending.get(m.id)(m);this.pending.delete(m.id);}else{this.events.push(m);this.onEvent?.(m);}};}
  async call(method,params={}){const r=await new Promise(done=>{const id=++this.id;this.pending.set(id,done);this.socket.send(JSON.stringify({id,method,params}));});if(r.error)throw new Error(JSON.stringify(r.error));return r.result;}
  async eval(expression){const r=await this.call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
}
async function stop(p){if(!p||p.exitCode!==null)return;p.kill('SIGTERM');await Promise.race([new Promise(r=>p.once('exit',r)),sleep(2000)]);if(p.exitCode===null)p.kill('SIGKILL');}
const profile=await mkdtemp(join(tmpdir(),'noctiluca-v11-chrome-'));
let vite,chrome,cdp;
try{
  await mkdir(output,{recursive:true});
  const overrides={};
  if(mode==='fixture'){
    const audit=fixtureAudit(),text=`${JSON.stringify(audit)}\n`,source=join(output,'SCRIPTED-audit.json');await writeFile(source,text);
    execFileSync(process.execPath,['scripts/export-open-estimators-v11.mjs',`--audit=${source}`,`--output=${output}`,`--expected-audit-sha256=${sha(text)}`,`--expected-source=${audit.source_commit}`,'--allow-synthetic-temp-only']);
    for(const file of ['native-open-estimators-v11.availability.json','native-open-estimators-v11.ui.json','native-open-estimators-v11.ui-receipt.json'])overrides[file]=await readFile(join(output,file));
  }
  vite=spawn('npm',['run','dev','--','--host','127.0.0.1','--port',String(port)],{stdio:['ignore','pipe','pipe']});const serverErrors=[];vite.stderr.on('data',b=>serverErrors.push(String(b)));
  await waitFor(async()=>{const r=await fetch(`${base}/native-open-estimators.html`);return r.ok;},'Vite');
  chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',`--user-data-dir=${profile}`,'--remote-debugging-port=0','about:blank'],{stdio:['ignore','ignore','pipe']});
  const cp=await waitFor(async()=>Number((await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]),'Chrome');
  const target=await waitFor(async()=>(await(await fetch(`http://127.0.0.1:${cp}/json/list`)).json()).find(t=>t.type==='page'),'target');cdp=new Cdp(target.webSocketDebuggerUrl);await cdp.open();
  for(const domain of ['Runtime','Log','Network','Page'])await cdp.call(`${domain}.enable`);
  if(mode==='fixture'){
    cdp.onEvent=m=>{if(m.method==='Fetch.requestPaused'){const file=m.params.request.url.split('/').pop(),body=overrides[file];void cdp.call(body?'Fetch.fulfillRequest':'Fetch.continueRequest',body?{requestId:m.params.requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:body.toString('base64')}:{requestId:m.params.requestId});}};
    await cdp.call('Fetch.enable',{patterns:[{urlPattern:`${base}/data/native-open-estimators-v11*`,requestStage:'Request'}]});
  }
  const artifacts={};
  let exportBinding=null;
  if(mode!=='unavailable'){
    const payload=mode==='fixture'?overrides['native-open-estimators-v11.ui.json']:await readFile('public/data/native-open-estimators-v11.ui.json');
    const receipt=JSON.parse(String(mode==='fixture'?overrides['native-open-estimators-v11.ui-receipt.json']:await readFile('public/data/native-open-estimators-v11.ui-receipt.json')));
    if(sha(payload)!==receipt.payload_sha256)throw new Error('Payload bytes differ from export receipt');
    exportBinding={payload_sha256:receipt.payload_sha256,source_binding:receipt.source_binding};
  }
  for(const capture of [{id:'overview',width:1600,height:1100},{id:'paths',width:1600,height:1100,focus:true},{id:'mobile-paths',width:390,height:1100,focus:true,mobile:true}]){
    await cdp.call('Emulation.setDeviceMetricsOverride',{width:capture.width,height:capture.height,deviceScaleFactor:1,mobile:!!capture.mobile});
    const query=new URLSearchParams();if(mode==='fixture')query.set('fixture','scripted-v11');if(capture.focus)query.set('focus','paths');
    await cdp.call('Page.navigate',{url:`${base}/native-open-estimators.html?${query}`});
    await waitFor(()=>cdp.eval(`document.querySelector('#truth-badge').textContent!=='VERIFYING AVAILABILITY'`),'availability and render');await sleep(150);
    const state=await cdp.eval(`({badge:document.querySelector('#truth-badge').textContent,unavailable:!document.querySelector('#unavailable').hidden,evidence:!document.querySelector('#evidence').hidden,stations:document.querySelectorAll('.mo-station').length,innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth,images:[...document.images].every(i=>i.complete&&i.naturalWidth>0)})`);
    if(state.badge!==(mode==='unavailable'?'NO AUDITED EXPORT':mode==='fixture'?'SCRIPTED FIXTURE / NOT QWEN':'AUDITED ACTUAL DEVELOPMENT')||state.evidence!==(mode!=='unavailable')||state.stations!==(mode==='unavailable'?0:8)||!state.images)throw new Error(JSON.stringify(state));
    if(state.innerWidth!==state.scrollWidth||state.innerWidth!==state.bodyWidth)throw new Error(`Overflow ${JSON.stringify(state)}`);
    if(mode!=='unavailable'){const checked=await cdp.eval(`(()=>{document.querySelector('button[data-method="1"][data-step="0"]').click();const first=document.querySelector('#endpoint-detail').textContent;document.querySelector('button[data-method="1"][data-step="3"]').click();return first.includes('PLAIN LR')&&document.querySelector('#endpoint-detail').textContent.includes('FROZEN-PRIOR CV')})()`);if(!checked)throw new Error('G0/G1 diagnostics interaction failed');}
    const shot=await cdp.call('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:false});const bytes=Buffer.from(shot.data,'base64'),file=`open-estimators-v11-${mode}-${capture.id}.png`;await writeFile(join(output,file),bytes);artifacts[capture.id]={file,sha256:sha(bytes),...capture,...state};
  }
  const errors=cdp.events.filter(e=>e.method==='Runtime.exceptionThrown'||e.method==='Log.entryAdded'&&e.params.entry.level==='error');
  const failed=cdp.events.filter(e=>e.method==='Network.responseReceived'&&e.params.response.status>=400);
  const requests=cdp.events.filter(e=>e.method==='Network.requestWillBeSent'&&/^http/.test(e.params.request.url)).map(e=>e.params.request);
  if(errors.length||failed.length||requests.some(r=>r.method!=='GET'||!r.url.startsWith(`${base}/`))||serverErrors.some(s=>/error/i.test(s)))throw new Error(JSON.stringify({errors,failed,serverErrors}));
  const sources={};for(const file of ['native-open-estimators.html','src/openEstimator.ts','src/openEstimator.css','src/openEstimatorContract.ts','scripts/export-open-estimators-v11.mjs','scripts/verify-open-estimators-browser.mjs'])sources[file]=sha(await readFile(file));
  const receipt={schema:'scienceutopia.open-estimator-ui-browser-qa.v11',mode,classification:mode==='actual'?'actual-native-qwen-open-estimators-development-v11':mode==='fixture'?'scripted-fixture-not-native-results':'no-actual-export-available',no_inference:true,no_job_dispatch:true,fixture_used:mode==='fixture',browser_errors:0,failed_http_responses:0,non_get_requests:0,external_requests:0,export_binding:exportBinding,ui_source_sha256s:sources,artifacts};
  await writeFile(join(output,'open-estimators-v11-browser-qa.json'),`${JSON.stringify(receipt,null,2)}\n`);console.log(JSON.stringify(receipt));
}finally{cdp?.socket?.close();await stop(chrome);await stop(vite);try{await rename(profile,join(homedir(),'.Trash',`${basename(profile)}-${Date.now()}`));}catch{}}
