import { createHash } from 'node:crypto';
import { spawn, execFileSync } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rename, writeFile } from 'node:fs/promises';
import { homedir, tmpdir } from 'node:os';
import { basename, join, resolve } from 'node:path';
import { nestedFixture, failedNestedFixture } from '../test/nestedFoundryFixture.ts';

const args=Object.fromEntries(process.argv.slice(2).map(value=>{const[key,...rest]=value.replace(/^--/,'').split('=');return[key,rest.join('=')];}));
const mode=args.mode??'unavailable',scenario=args.scenario??'complete',port=Number(args.port??4343),base=`http://127.0.0.1:${port}`;
if(!['actual','fixture','unavailable'].includes(mode)||!['complete','zero-replies','encoded-system'].includes(scenario)||scenario!=='complete'&&mode!=='fixture'||!Number.isInteger(port)||port<1024||port>65535)throw new Error('Invalid browser QA mode/scenario/port');
const sha=value=>createHash('sha256').update(value).digest('hex'),sleep=ms=>new Promise(done=>setTimeout(done,ms));
const output=resolve(args.output??(mode==='fixture'?await mkdtemp(join(tmpdir(),'noctiluca-v13-fixture-qa-')):`screenshots/nested-foundry-v13-${mode}-qa`));
if(mode==='fixture'&&!output.startsWith(`${resolve(tmpdir())}/`))throw new Error('Synthetic captures must remain temporary');
async function until(fn,label){for(let attempt=0;attempt<100;attempt++){try{const result=await fn();if(result)return result;}catch{}await sleep(100);}throw new Error(`Timed out: ${label}`);}
class Cdp {
  constructor(url){this.url=url;this.pending=new Map();this.id=0;this.events=[];}
  async open(){this.socket=new WebSocket(this.url);await new Promise((done,fail)=>{this.socket.onopen=done;this.socket.onerror=fail;});this.socket.onmessage=({data})=>{const m=JSON.parse(data);if(m.id&&this.pending.has(m.id)){this.pending.get(m.id)(m);this.pending.delete(m.id);}else{this.events.push(m);this.onEvent?.(m);}};}
  async call(method,params={}){const response=await new Promise(done=>{const id=++this.id;this.pending.set(id,done);this.socket.send(JSON.stringify({id,method,params}));});if(response.error)throw new Error(JSON.stringify(response.error));return response.result;}
  async eval(expression){const r=await this.call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw new Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
}
async function stop(process){if(!process||process.exitCode!==null)return;process.kill('SIGTERM');await Promise.race([new Promise(done=>process.once('exit',done)),sleep(2000)]);if(process.exitCode===null)process.kill('SIGKILL');}
const profile=await mkdtemp(join(tmpdir(),'noctiluca-v13-chrome-'));let vite,chrome,cdp;
try {
  await mkdir(output,{recursive:true});const overrides={};
  if(mode==='fixture'){
    const audit=scenario==='zero-replies'?failedNestedFixture():nestedFixture();
    if(scenario==='encoded-system')audit.arms[audit.objective_order[1]].observations.at(-1).system.mechanisms[1].parameters.exact_native_counter='UNSAFE_SYSTEM_INTEGER_TOKEN';
    const text=`${JSON.stringify(audit).replace('"UNSAFE_SYSTEM_INTEGER_TOKEN"','1122442242526474860')}\n`,source=join(output,'SCRIPTED-audit.json');await writeFile(source,text);
    execFileSync(process.execPath,['scripts/export-nested-foundry-v13.mjs',`--audit=${source}`,`--output=${output}`,`--expected-audit-sha256=${sha(text)}`,`--expected-source=${audit.source_commit}`,'--allow-synthetic-temp-only']);
    for(const name of ['native-nested-search-v13.availability.json','native-nested-search-v13.ui.json','native-nested-search-v13.ui-receipt.json'])overrides[name]=await readFile(join(output,name));
  }
  const serverErrors=[];vite=spawn('npm',['run','dev','--','--host','127.0.0.1','--port',String(port)],{stdio:['ignore','pipe','pipe']});vite.stderr.on('data',chunk=>serverErrors.push(String(chunk)));
  await until(async()=>(await fetch(`${base}/native-objective-redesign.html`)).ok,'Vite entry');
  chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',`--user-data-dir=${profile}`,'--remote-debugging-port=0','about:blank'],{stdio:['ignore','ignore','pipe']});
  const chromePort=await until(async()=>Number((await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]),'Chrome');
  const target=await until(async()=>(await(await fetch(`http://127.0.0.1:${chromePort}/json/list`)).json()).find(row=>row.type==='page'),'browser target');
  cdp=new Cdp(target.webSocketDebuggerUrl);await cdp.open();for(const domain of ['Runtime','Log','Network','Page'])await cdp.call(`${domain}.enable`);
  if(mode==='fixture'){
    cdp.onEvent=m=>{if(m.method==='Fetch.requestPaused'){const{request,requestId}=m.params,body=overrides[request.url.split('/').pop()];void cdp.call(body?'Fetch.fulfillRequest':'Fetch.continueRequest',body?{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:body.toString('base64')}:{requestId});}};
    await cdp.call('Fetch.enable',{patterns:[{urlPattern:`${base}/data/native-nested-search-v13*`,requestStage:'Request'}]});
  }
  let binding=null,expectedRows=0;
  if(mode!=='unavailable'){
    const payload=mode==='fixture'?overrides['native-nested-search-v13.ui.json']:await readFile('public/data/native-nested-search-v13.ui.json'),receipt=JSON.parse(String(mode==='fixture'?overrides['native-nested-search-v13.ui-receipt.json']:await readFile('public/data/native-nested-search-v13.ui-receipt.json')));
    if(sha(payload)!==receipt.payload_sha256)throw new Error('Payload hash differs');binding={payload_sha256:receipt.payload_sha256,source_binding:receipt.source_binding};expectedRows=Object.values(JSON.parse(payload).arms).reduce((sum,arm)=>sum+arm.observations.length,0);
  }
  const artifacts={};
  const captures=[{id:'overview',width:1600,height:1120},{id:'paths',focus:'paths',width:1600,height:1120},{id:'signal',focus:'signal',width:1600,height:1120},{id:'circuit',focus:'circuit',width:1600,height:1120},{id:'draft',focus:'draft',width:1600,height:1120},{id:'mobile-paths',focus:'paths',width:390,height:1120,mobile:true},{id:'mobile-signal',focus:'signal',width:390,height:1120,mobile:true},{id:'mobile-circuit',focus:'circuit',width:390,height:1120,mobile:true},{id:'mobile-draft',focus:'draft',width:390,height:1120,mobile:true}];
  for(const capture of captures){
    await cdp.call('Emulation.setDeviceMetricsOverride',{width:capture.width,height:capture.height,deviceScaleFactor:1,mobile:!!capture.mobile});const query=new URLSearchParams({campaign:'v13'});if(mode==='fixture')query.set('fixture','scripted-v13');if(capture.focus)query.set('focus',capture.focus);
    await cdp.call('Page.navigate',{url:`${base}/native-objective-redesign.html?${query}`});await until(()=>cdp.eval(`document.querySelector('#truth-badge').textContent!=='VERIFYING AVAILABILITY'`),'verified render');await sleep(120);
    const state=await cdp.eval(`({badge:document.querySelector('#truth-badge').textContent,evidence:!document.querySelector('#evidence').hidden,stations:document.querySelectorAll('.redesign-station').length,profiles:document.querySelectorAll('#cross-profiles tbody tr').length,innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth,images:[...document.images].every(image=>image.complete&&image.naturalWidth>0)})`);
    if(state.badge!==(mode==='unavailable'?'NO AUDITED EXPORT':mode==='fixture'?'SCRIPTED FIXTURE / NOT QWEN':'AUDITED ACTUAL DEVELOPMENT')||state.evidence!==(mode!=='unavailable')||state.stations!==expectedRows||state.profiles!==expectedRows||!state.images||state.innerWidth!==state.scrollWidth||state.innerWidth!==state.bodyWidth)throw new Error(`Render/overflow: ${JSON.stringify(state)}`);
    if(mode!=='unavailable'){
      await cdp.eval(`(()=>{const buttons=[...document.querySelectorAll('button[data-arm="1"][data-generation]')];buttons.at(-1).click();document.querySelector('button[data-tab="protocol"]').click();document.querySelector('button[data-tab="process"]').click();document.querySelector('button[data-tab="native"]').click();const next=document.querySelector('#nested-event-next');if(!next.disabled)next.click();document.querySelector('#foundry-copy').click();document.querySelector('#foundry-check').click();})()`);
      if(scenario==='complete')await until(()=>cdp.eval(`document.querySelector('#foundry-branch-status').textContent.includes('LOCAL STRUCTURAL PRECHECK PASS')`),'local structural branch preparation');
      const interaction=await cdp.eval(`({stage:JSON.parse(document.querySelector('#raw-row').textContent).stage,draw:JSON.parse(document.querySelector('#raw-row').textContent).draw_index,sourceNodes:document.querySelectorAll('.circuit-node').length,policyStages:document.querySelectorAll('.nested-stage-grid article').length,branchStatus:document.querySelector('#foundry-branch-status').textContent,draft:document.querySelector('#foundry-draft').value,prepared:document.querySelector('#foundry-prepared').textContent,workbenchHidden:document.querySelector('#foundry-workbench').hidden,eventPosition:document.querySelector('#nested-event-position').textContent})`);
      if(interaction.stage!=='redesign'||interaction.policyStages!==3||scenario==='complete'&&(!interaction.prepared||interaction.workbenchHidden!==(mode==='fixture'))||scenario==='zero-replies'&&(interaction.sourceNodes!==0||interaction.prepared))throw new Error(`Interaction: ${JSON.stringify(interaction)}`);
      if(scenario==='encoded-system'&&(interaction.prepared||!interaction.workbenchHidden||!interaction.branchStatus.includes('LOSSLESS SERVER-SIDE IMPORT REQUIRED')||!await cdp.eval(`document.querySelector('#foundry-check').disabled&&document.querySelector('#foundry-draft').disabled`)))throw new Error('Encoded native integers were silently reinterpreted or handed off');
      if(capture.id==='draft'&&scenario==='complete'){
        const exact=JSON.parse(interaction.prepared);if(JSON.stringify(exact.system)!==JSON.stringify(JSON.parse(interaction.draft))||exact.no_execution!==true||exact.no_adoption!==true)throw new Error('Prepared branch lost exact local draft or scope');
      }
    }
    const screenshot=await cdp.call('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:false}),bytes=Buffer.from(screenshot.data,'base64'),file=`nested-foundry-v13-${mode}-${capture.id}.png`;await writeFile(join(output,file),bytes);artifacts[capture.id]={file,sha256:sha(bytes),...capture,...state};
  }
  // Verify edit invalidation and exact workbench import, without posting a job.
  let handoff={state:mode==='fixture'?'fixture-handoff-disabled':'not-applicable'};
  if(mode==='actual'){
    const href=await cdp.eval(`document.querySelector('#foundry-workbench').href`),stored=await cdp.eval(`sessionStorage.getItem('scienceutopia.foundry.prepared-branch.v13')`);
    await cdp.eval(`(()=>{const e=document.querySelector('#foundry-draft');e.value+=' ';e.dispatchEvent(new Event('input',{bubbles:true}));})()`);
    if(!await cdp.eval(`document.querySelector('#foundry-workbench').hidden&&document.querySelector('#foundry-download').disabled`))throw new Error('Edited draft retained stale authorization/export');
    await cdp.call('Page.navigate',{url:href});await until(()=>cdp.eval(`document.querySelector('#status')?.textContent==='HASH VERIFIED / NATIVE DEVELOPMENT EVIDENCE'`),'existing native workbench data');
    await cdp.eval(`document.querySelector('#design-console').open=true`);await until(()=>cdp.eval(`document.querySelector('#design-parent').textContent.startsWith('UNEXECUTED FOUNDRY BRANCH')`),'exact prepared branch import');
    const loaded=await cdp.eval(`({system:JSON.parse(document.querySelector('#design-system').value),loss:JSON.parse(document.querySelector('#design-loss').value),consent:document.querySelector('#design-consent').checked,submitDisabled:document.querySelector('#design-submit').disabled,status:document.querySelector('#design-service').textContent})`),branch=JSON.parse(stored);
    if(JSON.stringify(loaded.system)!==JSON.stringify(branch.system)||JSON.stringify(loaded.loss)!==JSON.stringify(branch.loss_spec)||loaded.consent||!loaded.submitDisabled)throw new Error('Workbench import differs or acquired consent');
    handoff={state:'exact-local-import-no-execution-no-adoption',system_exact:true,loss_exact:true,renewed_consent_required:true,service_status:loaded.status};
  }
  const errors=cdp.events.filter(e=>e.method==='Runtime.exceptionThrown'||e.method==='Log.entryAdded'&&e.params.entry.level==='error'),failed=cdp.events.filter(e=>e.method==='Network.responseReceived'&&e.params.response.status>=400),requests=cdp.events.filter(e=>e.method==='Network.requestWillBeSent'&&/^http/.test(e.params.request.url)).map(e=>e.params.request);
  if(errors.length||failed.length||requests.some(r=>r.method!=='GET'||!r.url.startsWith(`${base}/`))||serverErrors.some(text=>/error/i.test(text)))throw new Error(JSON.stringify({errors,failed,serverErrors}));
  const sources={};for(const file of ['native-objective-redesign.html','native.html','src/openRedesign.ts','src/openRedesignContract.ts','src/nestedFoundryContract.ts','src/nestedFoundrySignal.ts','src/nestedFoundry.css','src/foundryBranch.ts','src/nativeJobs.ts','src/nativeDesignGraph.ts','src/nativeDesignGraphView.ts','scripts/export-nested-foundry-v13.mjs','scripts/verify-nested-foundry-browser.mjs'])sources[file]=sha(await readFile(file));
  const receipt={schema:'scienceutopia.nested-foundry-ui-browser-qa.v13',mode,scenario,no_inference:true,no_job_dispatch:true,no_adoption:true,fixture_used:mode==='fixture',browser_errors:0,failed_http_responses:0,non_get_requests:0,external_requests:0,export_binding:binding,workbench_handoff:handoff,ui_source_sha256s:sources,artifacts};
  await writeFile(join(output,'nested-foundry-v13-browser-qa.json'),`${JSON.stringify(receipt,null,2)}\n`);console.log(JSON.stringify(receipt));
}finally{cdp?.socket?.close();await stop(chrome);await stop(vite);try{await rename(profile,join(homedir(),'.Trash',`${basename(profile)}-${Date.now()}`));}catch{}}
