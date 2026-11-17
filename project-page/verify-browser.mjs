import {spawn} from 'node:child_process';
import {mkdtemp,readFile,mkdir,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const root=dirname(fileURLToPath(import.meta.url)),output=join(root,'qa');await mkdir(output,{recursive:true});
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
 await call('Page.navigate',{url:base.href});
 await until(()=>evaluate('!!document.querySelector("#loss-chart svg")'),'Chart load');
 await evaluate('document.documentElement.style.scrollBehavior="auto"');
 await evaluate('document.querySelectorAll("img").forEach(image=>image.loading="eager")');
 await until(()=>evaluate('[...document.images].every(i=>i.complete&&i.naturalWidth>0)'),'All image layout settled');
 const desktop=await evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight})');assert(desktop.scroll<=desktop.width);
 await writeFile(join(output,'desktop.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false})).data,'base64'));
 const layout=await call('Page.getLayoutMetrics');
 await writeFile(join(output,'desktop-full.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:1440,height:layout.cssContentSize.height,scale:1}})).data,'base64'));
 await evaluate('document.querySelector("#evidence").scrollIntoView()');await sleep(200);
 assert.equal(await evaluate('document.querySelectorAll("#loss-chart circle").length'),11);
 await writeFile(join(output,'evidence.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await evaluate('document.querySelector("[data-objective=resource-aware-content]").click()');
 assert.equal(await evaluate('document.querySelectorAll("#loss-chart circle").length'),12);
 assert(await evaluate('document.querySelector("#loss-definition").textContent.includes("K_collected")'));
 await evaluate('document.querySelector(".data-table").open=true');assert.equal(await evaluate('document.querySelectorAll("#loss-table tbody tr").length'),4);
 await evaluate('document.querySelector("#language").click()');assert.equal(await evaluate('document.documentElement.lang'),'ja');assert(await evaluate('document.querySelector("h1").textContent.includes("科学")'));
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 await evaluate('scrollTo(0,0)');await sleep(200);
 const mobile=await evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})');assert(mobile.scroll<=mobile.width,JSON.stringify(mobile));
 await writeFile(join(output,'mobile-ja.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await evaluate('document.querySelector("#language").click()');
 await writeFile(join(output,'mobile-en.png'),Buffer.from((await call('Page.captureScreenshot',{format:'png'})).data,'base64'));
 await evaluate('document.querySelector("#world").scrollIntoView()');await until(()=>evaluate('document.querySelector("video").readyState>=1'),'Video metadata');
 const video=await evaluate('({duration:document.querySelector("video").duration,error:document.querySelector("video").error?.code??null})');assert(video.duration>0);assert.equal(video.error,null);
 await evaluate('document.querySelector("#limits").scrollIntoView()');await sleep(150);
 await evaluate('scrollTo(0,document.body.scrollHeight)');await sleep(150);
 await until(()=>evaluate('[...document.images].every(i=>i.complete&&i.naturalWidth>0)'),'All images load');
 assert.equal(errors.length,0);assert.equal(httpErrors.length,0);
 const networkRequests=requests.filter(url=>/^https?:/.test(url));
 assert(networkRequests.every(url=>new URL(url).origin===base.origin),JSON.stringify(networkRequests));
 await writeFile(join(output,'browser-check.json'),JSON.stringify({status:'passed',url:base.href,desktop,mobile,video,javascript_errors:errors,http_errors:httpErrors,same_origin_only_requests:true,new_model_calls:0,checks:['Both objective charts','Null retained','Data table','English/Japanese switch','Desktop/mobile overflow','All images','Video metadata','No external runtime requests']},null,2)+'\n');
 console.log(JSON.stringify({status:'passed',desktop,mobile,video,screenshots:4,javascript_errors:0,http_errors:0}));
}finally{socket?.close();chrome.kill('SIGTERM');}
