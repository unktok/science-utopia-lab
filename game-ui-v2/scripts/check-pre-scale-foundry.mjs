// Read-only browser verification. Synthetic QA is explicit, never a paper result.
import {createHash} from 'node:crypto';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {basename,resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
const args=Object.fromEntries(process.argv.slice(2).map(s=>{const i=s.indexOf('=');return[s.slice(2,i),s.slice(i+1)];}));
const synthetic=args.synthetic==='true',arm=args.arm??'efficiency:parameters';
const arms=['throughput','efficiency'].flatMap(o=>['parameters','code-fixed-graph','code-and-graph','random'].map(m=>o+':'+m));
if(!arms.includes(arm))throw new Error('Explicit pre-scale arm required');
const base=args['base-url']??'http://127.0.0.1:4181';
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(base))throw new Error('Loopback-only target required');
const out=resolve(args.output??'screenshots/pre-scale-foundry-qa');await mkdir(out,{recursive:true});
const sha=value=>createHash('sha256').update(value).digest('hex');
let evidence,inputHash=null;
if(synthetic){
  evidence=JSON.parse(await readFile(new URL('../public/data/native-design-lab-v1.json',import.meta.url),'utf8'));
  const data=JSON.parse(evidence.payload_json);
  data.relaxation=null;
  Object.assign(data.source.world,{source_commit:'62388a74d071a3a4fdc8cc309c2807422f96223f',years:4,model:'qwen3:8b'});
  Object.assign(data.interpretation,{pre_scale_arm:arm,
    plan_sha256:'db2df5c5e54a68c8201b6b8c460cffa66770ee37da4f7b0d1089c7f5fc7702cb',
    scope:'closed-pre-scale-development-cells-not-unused-seed-generalization',development_only:true,
    selection_is_not_recomputed_by_viewer:true,original_audit_content_sha256:'a'.repeat(64),
    synthetic_fixture_not_scientific_evidence:true});
  for(const [i,row] of data.systems.entries()){
    row.evidence_label='SYNTHETIC QA / ROW '+i;
    for(const run of row.runs){run.seed=41001;run.frames=Array.from({length:4},(_,j)=>({...structuredClone(run.frames[0]),year:j+1}));}
  }
  const failed=structuredClone(data.systems[0]);failed.evidence_label='SYNTHETIC QA / FAILED';
  failed.status='failed';failed.native_loss=null;failed.runs=[];
  failed.technical_failures=[{error_type:'SYNTHETIC',error:'SYNTHETIC generated failure <script>not executable</script>'}];
  data.systems.push(failed);evidence.payload_json=JSON.stringify(data);evidence.payload_sha256=sha(evidence.payload_json);
}else{
  if(!args.envelope||!args.manifest)throw new Error('Actual QA requires original generated envelope and export manifest');
  const bytes=await readFile(resolve(args.envelope));inputHash=sha(bytes);evidence=JSON.parse(bytes);
  const manifest=JSON.parse(await readFile(resolve(args.manifest),'utf8'));
  if(manifest.schema!=='scienceutopia.pre-scale-foundry-export.v1'||manifest.files[basename(args.envelope)]!==inputHash
    ||basename(args.envelope)!==arm.replace(':','--')+'.json')throw new Error('Actual export manifest/file binding differs');
  if(JSON.parse(evidence.payload_json).interpretation.synthetic_fixture_not_scientific_evidence===true)throw new Error('Synthetic input is not actual QA');
}
const moduleName=args['playwright-module']?pathToFileURL(resolve(args['playwright-module'])).href:'playwright';
const {chromium}=await import(moduleName);const browser=await chromium.launch({headless:true,channel:'chrome'});
const check=(ok,message)=>{if(!ok)throw new Error(message);};
const report={schema:'scienceutopia.pre-scale-foundry-browser-qa.v1',observed_utc:new Date().toISOString(),
  story:'Closed-record envelope → explicit same-origin arm → read-only Foundry → source, wiring, years and failures',
  synthetic_fixture:synthetic,actual_export_verified:!synthetic,input_file_sha256:inputHash,
  checks:[],new_model_calls:0,simulation_submissions:0,independent_scientific_audit:false,files:{}};
try{
  const page=await browser.newPage({viewport:{width:1440,height:1100},deviceScaleFactor:1});
  const errors=[],requests=[];page.on('pageerror',error=>errors.push(String(error)));
  page.on('request',request=>requests.push({url:request.url(),method:request.method()}));
  const dataPath='/data/pre-scale-foundry-v1/'+arm.replace(':','--')+'.json',route='**'+dataPath;
  if(synthetic)await page.route(route,r=>r.fulfill({json:evidence}));
  const response=page.waitForResponse(r=>r.url().endsWith(dataPath));
  await page.goto(base+'/native.html?pre-scale-arm='+encodeURIComponent(arm));
  await page.waitForFunction(()=>/HASH VERIFIED|SYNTHETIC QA/.test(document.getElementById('status')?.textContent??''));
  const received=await(await response).json();check(received.payload_sha256===evidence.payload_sha256,'Response differs from selected envelope');
  const payload=JSON.parse(evidence.payload_json);
  check(await page.locator('#design-console').isHidden(),'Read-only mode exposes a workbench');
  check(await page.locator('#load').isDisabled(),'Read-only mode permits alternate file loading');
  check(await page.locator('#candidate option').count()===payload.systems.length,'Candidate count differs');
  const first=payload.systems[0],spec=JSON.parse(first.system_spec_json);
  check(await page.locator('[data-native-node]').count()===spec.mechanisms.length,'Mechanism count differs');
  const code=spec.mechanisms.find(n=>typeof n.parameters?.code_artifact?.source==='string');
  check(!!code,'No recorded code mechanism available for source inspection');
  const id=await page.evaluate(value=>CSS.escape(value),code.mechanism_id);
  await page.locator(`[data-native-node="${id}"]`).click();
  check(await page.locator('#native-source').textContent()===code.parameters.code_artifact.source,'Source bytes changed in display');
  const wires=await page.locator('.native-wire').count();check(wires===spec.connections.length,'Wiring count differs');
  for(const frame of first.runs[0].frames){
    await page.locator('#year').selectOption(String(frame.year));
    check(await page.locator('.native-actor').count()===frame.actors.filter(a=>a.can_author).length,'Actor frame differs');
  }
  report.checks.push('explicit selected envelope,exact candidate/node/wire counts,literal code,all committed years and actor counts');
  const frameYear=Number(await page.locator('#year').inputValue());
  const executionEvents=first.runs[0].events.filter(e=>e.year===frameYear&&typeof e.provenance.mechanism_id==='string');
  check(executionEvents.length>0,'Actual year has no execution records to inspect');
  for(const event of executionEvents){
    await page.locator('#step').click();
    const mechanism=event.provenance.mechanism_id;
    check(await page.locator('#node-name').textContent()===mechanism,'NEXT EXECUTION selects a different mechanism');
    const expected=first.runs[0].events.filter(e=>e.year===frameYear&&e.provenance.mechanism_id===mechanism);
    check(await page.locator('#native-events').textContent()===expected.map(e=>JSON.stringify(e,null,2)).join('\n'),'Displayed execution differs from recorded events');
  }
  report.checks.push('NEXT EXECUTION traverses every recorded event in the selected year; exact mechanism and event text, no replayed computation');
  check(errors.length===0,'Browser errors: '+errors.join(';'));
  check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),'Desktop overflow');
  if(synthetic)check((await page.locator('#status').innerText()).includes('SYNTHETIC QA'),'Synthetic view lacks its visible boundary');
  await page.screenshot({path:join(out,'desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),'Mobile overflow');
  report.mobile_capture=await page.evaluate(()=>({document_height:document.documentElement.scrollHeight,
    viewport_height:innerHeight,header_count:document.querySelectorAll('.top').length,
    deck_count:document.querySelectorAll('.foundry-deck').length}));
  check(report.mobile_capture.header_count===1&&report.mobile_capture.deck_count===1,'Mobile DOM duplicates its header or deck');
  // Long full-page mobile captures repeated viewport tiles in this Chrome run.
  // Keep genuine viewport screenshots instead; never deliver the repeated image.
  if(synthetic)await page.evaluate(()=>{
    const badge=document.createElement('div');badge.textContent='SYNTHETIC QA / NO SCIENTIFIC RESULT';
    badge.style.cssText='position:fixed;bottom:6px;right:6px;z-index:99999;background:#17263a;color:#bde4de;padding:5px;font:8px monospace;pointer-events:none';
    document.body.append(badge);
  });
  await page.evaluate(()=>scrollTo(0,0));
  await page.screenshot({path:join(out,'mobile.png'),fullPage:false});
  await page.evaluate(()=>document.getElementById('native-graph').scrollIntoView({block:'start'}));
  await page.screenshot({path:join(out,'mobile-network.png'),fullPage:false});
  await page.evaluate(()=>document.querySelector('.evidence').scrollIntoView({block:'start'}));
  check(await page.evaluate(()=>scrollY>0&&document.querySelector('.top').getBoundingClientRect().bottom<0),'Mobile viewport did not scroll past its original header');
  await page.screenshot({path:join(out,'mobile-evidence.png'),fullPage:false});
  report.mobile_capture.scope='Three actual390x844 viewport captures, not a full-page composite; synthetic-only visible QA annotation.';
  report.checks.push('desktop and390px mobile,no overflow,no JavaScript errors,read-only workbench/file controls');
  const failed=payload.systems.findIndex(row=>row.status==='failed');
  if(failed>=0){
    await page.locator('#candidate').selectOption(String(failed));
    check((await page.locator('#native-metrics').innerText()).includes('NO VALID LOSS'),'Failure acquired a score');
    const row=payload.systems[failed];
    if(!row.runs.length)check(await page.locator('.native-actor').count()===0,'Failure acquired fabricated actors');
    if(row.technical_failures.length)check(await page.locator('#native-failures pre').textContent()===JSON.stringify(row.technical_failures,null,2),'Failure text changed or executed');
    report.checks.push('failed policy retains unknown loss,exact technical failure text and no invented actor frame');
  }
  await page.unroute(route);await page.route(route,r=>r.fulfill({status:404,body:'unavailable'}));
  await page.reload();await page.locator('#error').waitFor({state:'visible'});
  check(await page.locator('[data-native-node]').count()===0,'404 retains stale mechanisms');
  await page.unroute(route);const tampered=structuredClone(evidence);tampered.payload_json+=' ';
  await page.route(route,r=>r.fulfill({json:tampered}));
  await page.reload();await page.locator('#error').waitFor({state:'visible'});
  check((await page.locator('#error').innerText()).includes('hash mismatch'),'Tampering not rejected');
  report.checks.push('404 and modified envelope fail closed without stale mechanisms');
  await page.goto(base+'/native.html?pre-scale-arm=https%3A%2F%2Fexample.com%2Frun.json');
  await page.locator('#error').waitFor({state:'visible'});
  check(requests.every(r=>r.method==='GET'),'Viewer sends write requests');
  check(!requests.some(r=>r.url.includes('/native-api/')||r.url.includes('/data/native-design-lab-v1.json')),'Read-only selection starts a queue or silently loads older evidence');
  check(errors.length===0,'Unhandled browser failure');
  report.checks.push('unknown arm refused,zero writes,zero queue API calls,no old-study fallback');report.passed=true;
}finally{await browser.close();}
for(const name of ['desktop.png','mobile.png','mobile-network.png','mobile-evidence.png'])report.files[name]=sha(await readFile(join(out,name)));
await writeFile(join(out,'verification.json'),JSON.stringify(report,null,2)+'\n');
process.stdout.write(JSON.stringify(report)+'\n');
