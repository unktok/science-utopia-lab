import { execFileSync } from 'node:child_process';
import { mkdtempSync,readFileSync,writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { describe,expect,it } from 'vitest';
import { parseOpenEstimator,verifyOpenEstimator } from '../src/openEstimatorContract';
import { fixtureAudit,h } from './openEstimatorFixture';
const ui=new URL('../',import.meta.url);
function exported(){
  const root=mkdtempSync(resolve(tmpdir(),'scienceutopia-v11-ui-test-'));
  const audit=fixtureAudit(),bytes=`${JSON.stringify(audit)}\n`,source=resolve(root,'SCRIPTED-audit.json');writeFileSync(source,bytes);
  execFileSync(process.execPath,[new URL('scripts/export-open-estimators-v11.mjs',ui).pathname,`--audit=${source}`,`--output=${root}`,`--expected-audit-sha256=${h(bytes)}`,`--expected-source=${audit.source_commit}`,'--allow-synthetic-temp-only']);
  return {root,audit,text:readFileSync(resolve(root,'native-open-estimators-v11.ui.json'),'utf8'),receipt:JSON.parse(readFileSync(resolve(root,'native-open-estimators-v11.ui-receipt.json'),'utf8'))};
}
describe('v11 open estimator view',()=>{
  it('has no public fixture and defaults to awaiting actual audited export',()=>{
    const availability=JSON.parse(readFileSync(new URL('public/data/native-open-estimators-v11.availability.json',ui),'utf8'));
    expect(['awaiting-audited-export','available']).toContain(availability.status);
    if(availability.status==='available')expect(availability.classification).toBe('actual-native-qwen-open-estimators-development-v11');
  });
  it('exports exact candidate cutoffs, all losses and explicit fixture attribution only in tmp',async()=>{
    const {audit,text,receipt}=exported();const d=await verifyOpenEstimator(text,receipt,true);
    expect(d.initial_baseline).toBeNull();expect(d.historical_baseline).toBeNull();
    expect(d.methods.flatMap(m=>m.steps)).toHaveLength(8);
    expect(d.methods[0]!.steps.map(s=>s.loss)).toEqual(audit.arms.blackbox.observations.map((s:any)=>s.loss));
    expect(d.methods[0]!.steps[3]!.cutoff).toBe(3.7);
    expect(d.methods[1]!.updates[1]!.mixed_report.expectation_estimator.prior_sample_ids).toEqual(d.methods[1]!.steps.slice(0,2).map(s=>s.observation_id));
    expect(()=>parseOpenEstimator(JSON.parse(text))).toThrow('classification');
    await expect(verifyOpenEstimator(`${text} `,receipt,true)).rejects.toThrow('export hash');
  });
  it('rejects invented baseline, wrong running best and cross-arm prior data',()=>{
    const {text}=exported();
    for(const change of [(d:any)=>d.initial_baseline={loss:0},(d:any)=>d.methods[0].steps[1].incumbent_loss=-999,(d:any)=>d.methods[1].updates[1].mixed_report.expectation_estimator.prior_sample_ids=['OTHER-ARM']]){
      const d=JSON.parse(text);change(d);expect(()=>parseOpenEstimator(d,true)).toThrow();
    }
  });
  it('rejects mismatched expected audit bytes and missing actual source proofs',()=>{
    const {root,audit}=exported(),source=resolve(root,'SCRIPTED-audit.json'),script=new URL('scripts/export-open-estimators-v11.mjs',ui).pathname;
    expect(()=>execFileSync(process.execPath,[script,`--audit=${source}`,`--output=${root}`,`--expected-audit-sha256=${'0'.repeat(64)}`,`--expected-source=${audit.source_commit}`],{stdio:'pipe'})).toThrow();
    expect(()=>execFileSync(process.execPath,[script,`--audit=${source}`,`--output=${new URL('public/data',ui).pathname}`,`--expected-audit-sha256=${h(readFileSync(source,'utf8'))}`,`--expected-source=${audit.source_commit}`,'--allow-synthetic-temp-only'],{stdio:'pipe'})).toThrow();
  });
  it('is English and read-only without changing v10 guards',()=>{
    const html=readFileSync(new URL('native-open-estimators.html',ui),'utf8'),code=readFileSync(new URL('src/openEstimator.ts',ui),'utf8');
    expect(html).toContain('<html lang="en">');expect(html).not.toMatch(/[\u3040-\u30ff\u3400-\u9fff]/u);
    expect(code).not.toMatch(/method:\s*['"]POST|\/api\/|setInterval/);
    expect(html).toContain('NO SCORED INITIAL OR HISTORICAL BASELINE');
  });
});
