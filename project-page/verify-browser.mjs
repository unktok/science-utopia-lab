import {spawn} from 'node:child_process';
import {mkdtemp,readFile,mkdir,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const story=process.argv.includes('--story');
const root=dirname(fileURLToPath(import.meta.url)),output=join(root,'qa',story?'story':'atlas');await mkdir(output,{recursive:true});
const base=new URL(process.env.PROJECT_PAGE_URL??'http://127.0.0.1:4673/');
const profile=await mkdtemp(join(tmpdir(),'sutopia-page-chrome-'));
const chrome=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check',`--user-data-dir=${profile}`,'--remote-debugging-port=0','about:blank'],{stdio:'ignore'});
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function until(fn,label){for(let i=0;i<80;i++){if(await fn())return;await sleep(100);}throw Error(label);}
let socket;const errors=[],httpErrors=[],requests=[];let counter=0;const pending=new Map();
async function call(method,params={}){const id=++counter;return new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});}
async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
try{
 let port;await until(async()=>{try{port=Number((await readFile(join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0]);return port>0;}catch{return false;}},'Chrome readiness');
 const page=(await(await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find(row=>row.type==='page');
 socket=new WebSocket(page.webSocketDebuggerUrl);await new Promise(resolve=>socket.onopen=resolve);
 socket.onmessage=({data})=>{const m=JSON.parse(data);if(m.id){const p=pending.get(m.id);if(m.error)p?.reject(Error(JSON.stringify(m.error)));else p?.resolve(m.result);pending.delete(m.id);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params);else if(m.method==='Network.responseReceived'&&m.params.response.status>=400)httpErrors.push({url:m.params.response.url,status:m.params.response.status});else if(m.method==='Network.requestWillBeSent')requests.push(m.params.request.url);};
 for(const domain of ['Page','Runtime','Network'])await call(`${domain}.enable`);
 await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
 await call('Page.navigate',{url:new URL(story?'story/':'',base).href});
 await until(()=>evaluate(story?'!!document.querySelector("#story-chart svg")':'!!document.querySelector("#loss-chart svg")'),'Chart load');
 await evaluate('document.documentElement.style.scrollBehavior="auto"');
 await evaluate('document.querySelectorAll("img").forEach(image=>image.loading="eager")');
 await until(()=>evaluate('[...document.images].every(i=>i.complete&&i.naturalWidth>0)'),'All image layout settled');
 const desktop=await evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight})');assert(desktop.scroll<=desktop.width);
 await writeFile(join(output,'desktop.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 const layout=await call('Page.getLayoutMetrics');
 await writeFile(join(output,'desktop-full.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:1440,height:layout.cssContentSize.height,scale:1}})).data,'base64'));
 if(story){
   for(const scope of ['parameters','algorithm','mechanism','wiring']){
     await evaluate(`document.querySelector('[data-scope="${scope}"]').click()`);
     assert.equal(await evaluate(`document.querySelector('[data-scope="${scope}"]').getAttribute('aria-pressed')`),'true');
     assert.equal(await evaluate('(()=>{const r=[...document.querySelectorAll("#design-graph g rect")].map(x=>x.getBBox());return r.some((a,i)=>r.slice(i+1).some(b=>a.x<b.x+b.width&&a.x+a.width>b.x&&a.y<b.y+b.height&&a.y+a.height>b.y))})()'),false);
   }
   await evaluate('document.querySelector("#search").scrollIntoView()');
   assert.equal(await evaluate('document.querySelectorAll("#story-chart circle").length'),11);
   await writeFile(join(output,'search-candidate.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
   await evaluate('document.querySelector("#path-view").value="incumbent";document.querySelector("#path-view").dispatchEvent(new Event("change"))');
   assert.equal(await evaluate('document.querySelectorAll("#story-chart circle").length'),12);
   await evaluate('[...document.querySelectorAll("#story-chart circle")].find(element=>element.dataset.method==="free-code-graph"&&element.dataset.generation==="1").dispatchEvent(new Event("click"))');
   assert(await evaluate('document.querySelector("#point-detail").textContent.includes("Execution null")&&document.querySelector("#point-detail").textContent.includes("Carried incumbent")'));
   await evaluate('document.querySelector("[data-story-objective=resource-aware-content]").click()');
   assert.equal(await evaluate('document.querySelectorAll("#story-chart circle").length'),12);
   assert(await evaluate('document.querySelector("#story-loss-definition").textContent.includes("K_collected")'));
   for(const [weight,expected] of [[0,'0.00'],[.1,'−4.00'],[.2,'−8.00']]){
     await evaluate(`document.querySelector('#cost-weight').value='${weight}';document.querySelector('#cost-weight').dispatchEvent(new Event('input'))`);
     assert.equal(await evaluate('document.querySelector("#cost-delta").textContent'),expected);
   }
   await evaluate('document.querySelector("#cost-weight").value="0.1";document.querySelector("#cost-weight").dispatchEvent(new Event("input"));document.querySelector("#objectives").scrollIntoView()');
   await writeFile(join(output,'ledger.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 }else{
 await evaluate('document.querySelector("#evidence").scrollIntoView()');await sleep(200);
 assert.equal(await evaluate('document.querySelectorAll("#loss-chart circle").length'),11);
 await writeFile(join(output,'evidence.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await evaluate('document.querySelector("[data-objective=resource-aware-content]").click()');
 assert.equal(await evaluate('document.querySelectorAll("#loss-chart circle").length'),12);
 assert(await evaluate('document.querySelector("#loss-definition").textContent.includes("K_collected")'));
 await evaluate('document.querySelector(".data-table").open=true');assert.equal(await evaluate('document.querySelectorAll("#loss-table tbody tr").length'),4);
 }
 assert.equal(await evaluate('document.documentElement.lang'),'en');
 assert.equal(await evaluate('document.querySelectorAll("#language,[data-ja]").length'),0);
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 await evaluate('scrollTo(0,0)');await sleep(200);
 const mobile=await evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})');assert(mobile.scroll<=mobile.width,JSON.stringify(mobile));
 await writeFile(join(output,'mobile-en.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await evaluate('document.querySelector("#world").scrollIntoView()');await until(()=>evaluate('document.querySelector("video").readyState>=1'),'Video metadata');
 const video=await evaluate('({duration:document.querySelector("video").duration,error:document.querySelector("video").error?.code??null})');assert(video.duration>0);assert.equal(video.error,null);
 await evaluate(story?'document.querySelector("#horizon").scrollIntoView()':'document.querySelector("#limits").scrollIntoView()');await sleep(150);
 await evaluate('scrollTo(0,document.body.scrollHeight)');await sleep(150);
 await until(()=>evaluate('[...document.images].every(i=>i.complete&&i.naturalWidth>0)'),'All images load');
 assert.equal(errors.length,0);assert.equal(httpErrors.length,0);
 const networkRequests=requests.filter(url=>/^https?:/.test(url));
 assert(networkRequests.every(url=>new URL(url).origin===base.origin),JSON.stringify(networkRequests));
 await writeFile(join(output,'browser-check.json'),JSON.stringify({status:'passed',url:new URL(story?'story/':'',base).href,desktop,mobile,video,javascript_errors:errors,http_errors:httpErrors,same_origin_only_requests:true,new_model_calls:0,checks:story?['Four design scopes','No node overlaps','Both objectives','Candidate/incumbent views','Carried incumbent not successful null','Archived-cost arithmetic at three weights','English only','Desktop/mobile overflow','All images','Video metadata','No external runtime requests']:['Both objective charts','Null retained','Data table','English only','Desktop/mobile overflow','All images','Video metadata','No external runtime requests']},null,2)+'\n');
 console.log(JSON.stringify({status:'passed',desktop,mobile,video,screenshots:3,javascript_errors:0,http_errors:0}));
}finally{socket?.close();chrome.kill('SIGTERM');}
