// Read-only browser QA of the actual snapshot. Never submits a simulation.
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
const args=Object.fromEntries(process.argv.slice(2).map(s=>{const i=s.indexOf('=');return [s.slice(2,i),s.slice(i+1)];}));
const moduleName=args['playwright-module'] ? pathToFileURL(resolve(args['playwright-module'])).href : 'playwright';
const {chromium}=await import(moduleName);
const base=args['base-url']??'http://127.0.0.1:4181';
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(base))throw new Error('Loopback-only QA target required');
const source=args.source??'recorded';
if(!['recorded','latest'].includes(source))throw new Error('Only explicit recorded/latest QA sources are allowed');
const evidenceFile=source==='latest'?'latest':'actual';
const evidenceRoute=`**/data/pre-scale-observatory.${evidenceFile}.json`;
const out=resolve(args.output??'screenshots/pre-scale-observatory-qa');await mkdir(out,{recursive:true});
const check=(condition,message)=>{if(!condition)throw new Error(message);};
const browser=await chromium.launch({headless:true,channel:args['browser-channel']??'chrome'});
const report={schema:'scienceutopia.pre-scale-browser-qa.v1',observed_utc:new Date().toISOString(),
  story:'Recorded journals → same-origin JSON → checksum validation → read-only English UI',checks:[],
  source_mode:source,
  new_model_calls:0,simulation_submissions:0,independent_scientific_audit:false,files:{}};
try{
  const page=await browser.newPage({viewport:{width:1440,height:1100},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  const evidenceRequests=[];let writes=0;
  page.on('request',r=>{if(/\/data\/pre-scale-observatory\./.test(r.url()))evidenceRequests.push(r.url());if(r.method()!=='GET')writes++;});
  await page.goto(base+'/pre-scale.html?source='+source);
  await page.getByRole('heading',{name:'Before the scale jump'}).waitFor();
  check(await page.locator('tbody tr').count()===12,'All declared mechanism slots must be visible');
  check(errors.length===0,'Unexpected JavaScript errors: '+errors.join('; '));
  check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),'Desktop horizontal overflow');
  check(!/[\u3040-\u30ff\u3400-\u9fff]/u.test(await page.locator('body').innerText()),'UI must remain English');
  await page.screenshot({path:join(out,'desktop.png'),fullPage:true});
  report.checks.push('actual data rendered,12 rows,English,desktop no overflow,no JS errors');
  await page.setViewportSize({width:390,height:844});
  check(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),'Mobile horizontal overflow');
  const small=await page.locator('.boundary small').first().boundingBox(),button=await page.locator('.boundary button').boundingBox();
  check(small&&button&&button.y>=small.y+small.height,'Mobile reload overlaps model provenance');
  await page.screenshot({path:join(out,'mobile.png'),fullPage:true});
  report.checks.push('390px mobile no overflow and reload below provenance');
  if(source==='latest'){
    const before=evidenceRequests.length;
    await page.waitForTimeout(31_000);
    check(evidenceRequests.length>before,'Local update mode must poll its actual local JSON without a manual click');
    check(evidenceRequests.every(u=>u.includes('.latest.json')),'No silent historical fallback in local update mode');
    report.checks.push('actual latest file automatically requested again after30 seconds, without recorded-file fallback');
  }
  await page.route(evidenceRoute,r=>r.fulfill({status:404,body:'unavailable'}));
  await page.reload();await page.getByRole('heading',{name:'Evidence unavailable'}).waitFor();
  check(await page.locator('tbody tr').count()===0,'Missing data must not retain stale world rows');
  report.checks.push('404 fails closed without stale outcomes');
  await page.unroute(evidenceRoute);
  await page.route(evidenceRoute,async r=>{
    const response=await r.fetch(),body=await response.json();body.payload.scientist_model='tampered';
    await r.fulfill({json:body});
  });
  await page.reload();await page.getByRole('heading',{name:'Evidence unavailable'}).waitFor();
  check((await page.locator('body').innerText()).includes('checksum'),'Changed content must fail integrity verification');
  report.checks.push('tampered JSON fails checksum without displaying invented progress');
  check(writes===0,'Read-only observation page must submit no write request');
  if(source==='latest')check(evidenceRequests.every(u=>u.includes('.latest.json')),'404/tamper may not fetch the recorded fallback');
  report.checks.push('no write/model/simulation request or silent alternate evidence source');
  report.passed=true;
}finally{await browser.close();}
for(const name of ['desktop.png','mobile.png'])report.files[name]=createHash('sha256').update(await readFile(join(out,name))).digest('hex');
await writeFile(join(out,'verification.json'),JSON.stringify(report,null,2)+'\n');
process.stdout.write(JSON.stringify(report)+'\n');
