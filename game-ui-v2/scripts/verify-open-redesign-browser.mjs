import { createHash } from 'node:crypto';
import { spawn, execFileSync } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rename, writeFile } from 'node:fs/promises';
import { homedir, tmpdir } from 'node:os';
import { basename, join, resolve } from 'node:path';
import { redesignFixture, zeroReplyRedesignFixture } from '../test/openRedesignFixture.ts';

const args=Object.fromEntries(process.argv.slice(2).map(value=>{const [key,...rest]=value.replace(/^--/,'').split('=');return [key,rest.join('=')];}));
const mode=args.mode??'unavailable',port=Number(args.port??4342),base=`http://127.0.0.1:${port}`;
const scenario=args.scenario??'complete';
if(!['actual','fixture','unavailable'].includes(mode)||!Number.isInteger(port)||port<1024||port>65535)throw new Error('Invalid mode or port');
if(!['complete','zero-replies'].includes(scenario)||scenario!=='complete'&&mode!=='fixture')throw new Error('Failure scenarios are temporary fixture checks only');
const sha=value=>createHash('sha256').update(value).digest('hex'),sleep=ms=>new Promise(done=>setTimeout(done,ms));
const output=resolve(args.output??(mode==='fixture'?await mkdtemp(join(tmpdir(),'noctiluca-v12-fixture-qa-')):`screenshots/open-redesign-v12-${mode}-qa`));
if(mode==='fixture'&&!output.startsWith(`${resolve(tmpdir())}/`))throw new Error('Fixture screenshots must remain temporary');
async function until(fn,label){for(let attempt=0;attempt<100;attempt++){try{const result=await fn();if(result)return result;}catch{}await sleep(100);}throw new Error(`Timed out: ${label}`);}
class Cdp {
  constructor(url){this.url=url;this.pending=new Map();this.id=0;this.events=[];}
  async open(){this.socket=new WebSocket(this.url);await new Promise((done,fail)=>{this.socket.onopen=done;this.socket.onerror=fail;});this.socket.onmessage=({data})=>{const message=JSON.parse(data);if(message.id&&this.pending.has(message.id)){this.pending.get(message.id)(message);this.pending.delete(message.id);}else{this.events.push(message);this.onEvent?.(message);}};}
  async call(method,params={}){const response=await new Promise(done=>{const id=++this.id;this.pending.set(id,done);this.socket.send(JSON.stringify({id,method,params}));});if(response.error)throw new Error(JSON.stringify(response.error));return response.result;}
  async eval(expression){const result=await this.call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));return result.result.value;}
}
async function stop(process){if(!process||process.exitCode!==null)return;process.kill('SIGTERM');await Promise.race([new Promise(done=>process.once('exit',done)),sleep(2000)]);if(process.exitCode===null)process.kill('SIGKILL');}
const profile=await mkdtemp(join(tmpdir(),'noctiluca-v12-chrome-'));
let vite,chrome,cdp;
try {
  await mkdir(output,{recursive:true});
  const overrides={};
  if(mode==='fixture'){
    const audit=scenario==='zero-replies'?zeroReplyRedesignFixture():redesignFixture(),text=`${JSON.stringify(audit)}\n`,source=join(output,'SCRIPTED-audit.json');await writeFile(source,text);
    execFileSync(process.execPath,['scripts/export-open-redesign-v12.mjs',`--audit=${source}`,`--output=${output}`,`--expected-audit-sha256=${sha(text)}`,`--expected-source=${audit.source_commit}`,'--allow-synthetic-temp-only']);
    for(const name of ['native-objective-redesign-v12.availability.json','native-objective-redesign-v12.ui.json','native-objective-redesign-v12.ui-receipt.json'])overrides[name]=await readFile(join(output,name));
  }
  const serverErrors=[];
  vite=spawn('npm',['run','dev','--','--host','127.0.0.1','--port',String(port)],{stdio:['ignore','pipe','pipe']});vite.stderr.on('data',chunk=>serverErrors.push(String(chunk)));
  await until(async()=>{const response=await fetch(`${base}/native-objective-redesign.html`);return response.ok;},'Vite entry');
  chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',`--user-data-dir=${profile}`,'--remote-debugging-port=0','about:blank'],{stdio:['ignore','ignore','pipe']});
  const chromePort=await until(async()=>Number((await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]),'Chrome');
  const target=await until(async()=>(await(await fetch(`http://127.0.0.1:${chromePort}/json/list`)).json()).find(row=>row.type==='page'),'browser target');
  cdp=new Cdp(target.webSocketDebuggerUrl);await cdp.open();for(const domain of ['Runtime','Log','Network','Page'])await cdp.call(`${domain}.enable`);
  if(mode==='fixture'){
    cdp.onEvent=message=>{if(message.method==='Fetch.requestPaused'){const {request,requestId}=message.params,body=overrides[request.url.split('/').pop()];void cdp.call(body?'Fetch.fulfillRequest':'Fetch.continueRequest',body?{requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'application/json'}],body:body.toString('base64')}:{requestId});}};
    await cdp.call('Fetch.enable',{patterns:[{urlPattern:`${base}/data/native-objective-redesign-v12*`,requestStage:'Request'}]});
  }
  let exportBinding=null;
  if(mode!=='unavailable'){
    const payload=mode==='fixture'?overrides['native-objective-redesign-v12.ui.json']:await readFile('public/data/native-objective-redesign-v12.ui.json');
    const receipt=JSON.parse(String(mode==='fixture'?overrides['native-objective-redesign-v12.ui-receipt.json']:await readFile('public/data/native-objective-redesign-v12.ui-receipt.json')));
    if(sha(payload)!==receipt.payload_sha256)throw new Error('Payload bytes differ from receipt');
    exportBinding={payload_sha256:receipt.payload_sha256,source_binding:receipt.source_binding};
  }
  const artifacts={};
  for(const capture of [{id:'overview',width:1600,height:1120},{id:'paths',width:1600,height:1120,focus:'paths'},{id:'circuit',width:1600,height:1120,focus:'circuit'},{id:'mobile-paths',width:390,height:1120,focus:'paths',mobile:true},{id:'mobile-circuit',width:390,height:1120,focus:'circuit',mobile:true}]){
    await cdp.call('Emulation.setDeviceMetricsOverride',{width:capture.width,height:capture.height,deviceScaleFactor:1,mobile:!!capture.mobile});
    const query=new URLSearchParams();if(mode==='fixture')query.set('fixture','scripted-v12');if(capture.focus)query.set('focus',capture.focus);
    await cdp.call('Page.navigate',{url:`${base}/native-objective-redesign.html?${query}`});
    await until(()=>cdp.eval(`document.querySelector('#truth-badge').textContent!=='VERIFYING AVAILABILITY'`),'export verify/render');await sleep(180);
    const state=await cdp.eval(`({badge:document.querySelector('#truth-badge').textContent,evidence:!document.querySelector('#evidence').hidden,unavailable:!document.querySelector('#unavailable').hidden,stations:document.querySelectorAll('.redesign-station').length,nodes:document.querySelectorAll('.circuit-node').length,profileRows:document.querySelectorAll('#cross-profiles tbody tr').length,innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyWidth:document.body.scrollWidth,images:[...document.images].every(image=>image.complete&&image.naturalWidth>0)})`);
    if(state.badge!==(mode==='unavailable'?'NO AUDITED EXPORT':mode==='fixture'?'SCRIPTED FIXTURE / NOT QWEN':'AUDITED ACTUAL DEVELOPMENT')||state.evidence!==(mode!=='unavailable')||state.stations!==(mode==='unavailable'?0:6)||state.profileRows!==(mode==='unavailable'?0:6)||!state.images)throw new Error(JSON.stringify(state));
    if(state.innerWidth!==state.scrollWidth||state.innerWidth!==state.bodyWidth)throw new Error(`Horizontal overflow: ${JSON.stringify(state)}`);
    if(mode!=='unavailable'){
      const interaction=await cdp.eval(`(()=>{const button=document.querySelector('button[data-arm="1"][data-generation="2"]');button.click();const title=document.querySelector('#circuit-title').textContent;const wire=document.querySelector('#wire-list button');if(wire)wire.click();else document.querySelector('button[data-tab="protocol"]').click();const protocol=document.querySelector('#inspector-content').textContent;document.querySelector('button[data-tab="process"]').click();const process=document.querySelector('#inspector-content').textContent;document.querySelector('button[data-tab="native"]').click();const native=document.querySelector('#inspector-content').textContent;document.querySelector('button[data-tab="source"]').click();return {title,protocol:protocol.includes('ACTUAL SELECTED'),process:process.includes('ACTUAL SYSTEM SCHEDULES'),native:native.includes('ORIGINAL RECORDS'),observation_id:JSON.parse(document.querySelector('#raw-row').textContent).observation_id};})()`);
      if(!interaction.title.includes('GENERATION 2')||!interaction.protocol||!interaction.process||!interaction.native)throw new Error(`Inspector interaction failed: ${JSON.stringify(interaction)}`);
      if(scenario==='zero-replies'&&(interaction.observation_id!==null||state.nodes!==0))throw new Error(`Fabricated native endpoint in zero-reply failure fixture: ${JSON.stringify(interaction)}`);
    }
    const capturedState=mode==='unavailable'?{}:await cdp.eval(`({nodes:document.querySelectorAll('.circuit-node').length,selected_observation_id:JSON.parse(document.querySelector('#raw-row').textContent).observation_id,selected_generation:JSON.parse(document.querySelector('#raw-row').textContent).generation,selected_arm:JSON.parse(document.querySelector('#raw-row').textContent).arm})`);
    const screenshot=await cdp.call('Page.captureScreenshot',{format:'png',fromSurface:true,captureBeyondViewport:false}),bytes=Buffer.from(screenshot.data,'base64'),file=`open-redesign-v12-${mode}-${capture.id}.png`;
    await writeFile(join(output,file),bytes);artifacts[capture.id]={file,sha256:sha(bytes),...capture,...state,...capturedState};
  }
  const errors=cdp.events.filter(event=>event.method==='Runtime.exceptionThrown'||event.method==='Log.entryAdded'&&event.params.entry.level==='error');
  const failed=cdp.events.filter(event=>event.method==='Network.responseReceived'&&event.params.response.status>=400);
  const requests=cdp.events.filter(event=>event.method==='Network.requestWillBeSent'&&/^http/.test(event.params.request.url)).map(event=>event.params.request);
  if(errors.length||failed.length||requests.some(request=>request.method!=='GET'||!request.url.startsWith(`${base}/`))||serverErrors.some(text=>/error/i.test(text)))throw new Error(JSON.stringify({errors,failed,serverErrors}));
  const sources={};for(const file of ['native-objective-redesign.html','src/openRedesign.ts','src/openRedesign.css','src/openRedesignContract.ts','scripts/export-open-redesign-v12.mjs','scripts/verify-open-redesign-browser.mjs'])sources[file]=sha(await readFile(file));
  const receipt={schema:'scienceutopia.open-redesign-ui-browser-qa.v12',mode,scenario,classification:mode==='actual'?'actual-native-qwen-objective-redesign-development-v12':mode==='fixture'?'scripted-fixture-not-native-results':'no-actual-export-available',no_inference:true,no_job_dispatch:true,fixture_used:mode==='fixture',browser_errors:0,failed_http_responses:0,non_get_requests:0,external_requests:0,export_binding:exportBinding,ui_source_sha256s:sources,artifacts};
  await writeFile(join(output,'open-redesign-v12-browser-qa.json'),`${JSON.stringify(receipt,null,2)}\n`);console.log(JSON.stringify(receipt));
}finally{cdp?.socket?.close();await stop(chrome);await stop(vite);try{await rename(profile,join(homedir(),'.Trash',`${basename(profile)}-${Date.now()}`));}catch{}}
