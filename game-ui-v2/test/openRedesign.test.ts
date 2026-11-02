import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { parseOpenRedesign, REDESIGN_OBJECTIVES, verifyOpenRedesign } from '../src/openRedesignContract';
import { redesignFixture, redesignHash } from './openRedesignFixture';
const ui=new URL('../',import.meta.url),script=new URL('scripts/export-open-redesign-v12.mjs',ui).pathname;
function exporting(change?:(audit:any)=>void){
  const root=mkdtempSync(resolve(tmpdir(),'scienceutopia-v12-ui-test-')),audit=redesignFixture();change?.(audit);
  const source=resolve(root,'SCRIPTED-audit.json'),bytes=JSON.stringify(audit);writeFileSync(source,bytes);
  execFileSync(process.execPath,[script,`--audit=${source}`,`--output=${root}`,`--expected-audit-sha256=${redesignHash(bytes)}`,`--expected-source=${audit.source_commit}`,'--allow-synthetic-temp-only'],{stdio:'pipe'});
  const text=readFileSync(resolve(root,'native-objective-redesign-v12.ui.json'),'utf8'),receipt=JSON.parse(readFileSync(resolve(root,'native-objective-redesign-v12.ui-receipt.json'),'utf8'));
  return {root,audit,text,receipt};
}
describe('v12 objective-conditioned free redesign evidence',()=>{
  it('defaults to awaiting actual audited data, never substitutes fixture',()=>{
    const available=JSON.parse(readFileSync(new URL('public/data/native-objective-redesign-v12.availability.json',ui),'utf8'));
    expect(['available','awaiting-audited-export']).toContain(available.status);
    if(available.status==='available')expect(available.classification).toBe('actual-native-qwen-objective-redesign-development-v12');
  });
  it('exports all six arbitrary institutional graphs with literal source and cross-scores',async()=>{
    const {audit,text,receipt}=exporting(),data=await verifyOpenRedesign(text,receipt,true);
    expect(data.objective_order).toEqual(REDESIGN_OBJECTIVES);
    for(const id of REDESIGN_OBJECTIVES){
      expect(data.arms[id].observations.map(r=>r.own_loss)).toEqual(audit.arms[id].observations.map((r:any)=>r.own_loss));
      expect(data.arms[id].observations[2]!.system.mechanisms[1].family).toBe('open-evidence-commons');
      expect(data.arms[id].observations[2]!.system.connections[1].source_port).toBe('shared_evidence');
    }
    expect(()=>parseOpenRedesign(JSON.parse(text))).toThrow('classification');
    await expect(verifyOpenRedesign(`${text} `,receipt,true)).rejects.toThrow('export hash');
  });
  it.each(['native-joint-v5-throughput','native-joint-v5-net-reviewed-utility'])('rejects changed LossSpec semantics under same ID %s',id=>{
    expect(()=>exporting(a=>{a.loss_specs[id].per_run.terms[0].coefficient+=.1;})).toThrow(/LossSpec differs/);
  });
  it('accepts canonical LossSpec independent of object key order',()=>{
    expect(()=>exporting(a=>{const id=REDESIGN_OBJECTIVES[0];a.loss_specs[id]=Object.fromEntries(Object.entries(a.loss_specs[id]).reverse());a.arms[id].loss_spec=a.loss_specs[id];})).not.toThrow();
  });
  it.each(['own','cross','source','wire','generation','replies','audit'])('rejects tampered %s evidence',kind=>{
    expect(()=>exporting(a=>{
      const r=a.arms[REDESIGN_OBJECTIVES[0]].observations[1];
      if(kind==='own')r.own_loss=42;
      if(kind==='cross')r.cross_scores[REDESIGN_OBJECTIVES[1]]=42;
      if(kind==='source')r.contracts.executable_sources['fixture-cooperative-1'].source_sha256='0'.repeat(64);
      if(kind==='wire')r.system.connections[0].source_mechanism='INVENTED';
      if(kind==='generation')r.generation=9;
      if(kind==='replies')a.physical_researcher_responses=-1;
      if(kind==='audit')a.audit.new_model_calls=1;
    })).toThrow();
  });
  it('retains technical failure as null, with no invented endpoint or best score',async()=>{
    const {text,receipt}=exporting(a=>{
      a.status='budget-complete-with-failures';a.physical_native_worlds=5;
      const r=a.arms[REDESIGN_OBJECTIVES[0]].observations[2];r.status='generation-failure';r.observation_id=null;r.loss=null;r.own_loss=null;r.cross_scores=Object.fromEntries(REDESIGN_OBJECTIVES.map(id=>[id,null]));r.system=null;r.physical_proof=null;r.metrics={};
    });
    const data=await verifyOpenRedesign(text,receipt,true),rows=data.arms[REDESIGN_OBJECTIVES[0]].observations;
    expect(rows[2]!.own_loss).toBeNull();expect(rows[2]!.running_best).toBe(rows[1]!.running_best);
    expect(rows[2]!.observation_id).toBeNull();
  });
  it('preserves missing cross-objective score rather than manufacturing zero',async()=>{
    const {text,receipt}=exporting(a=>{const r=a.arms[REDESIGN_OBJECTIVES[0]].observations[0];delete r.metrics['native.accepted_peer_score_sum'];r.cross_scores[REDESIGN_OBJECTIVES[1]]=null;});
    const d=await verifyOpenRedesign(text,receipt,true);
    expect(d.arms[REDESIGN_OBJECTIVES[0]].observations[0]!.cross_scores[REDESIGN_OBJECTIVES[1]]).toBeNull();
  });
  it('rejects invented baseline, missingness as zero, false running best and unsupported causal claim',()=>{
    const {text}=exporting();
    for(const change of [(d:any)=>d.initial_baseline={loss:0},(d:any)=>d.arms[REDESIGN_OBJECTIVES[0]].observations[1].running_best=-999,(d:any)=>d.claims.causal_institutional_benefit=true]){
      const data=JSON.parse(text);change(data);expect(()=>parseOpenRedesign(data,true)).toThrow();
    }
  });
  it('keeps synthetic exports temporary and exact audit byte-bound',()=>{
    const {root,audit}=exporting(),source=resolve(root,'SCRIPTED-audit.json');
    const base=[script,`--audit=${source}`,`--expected-source=${audit.source_commit}`];
    expect(()=>execFileSync(process.execPath,[...base,`--output=${root}`,`--expected-audit-sha256=${'0'.repeat(64)}`],{stdio:'pipe'})).toThrow();
    expect(()=>execFileSync(process.execPath,[...base,`--output=${new URL('public/data',ui).pathname}`,`--expected-audit-sha256=${redesignHash(readFileSync(source,'utf8'))}`,'--allow-synthetic-temp-only'],{stdio:'pipe'})).toThrow();
  });
  it('uses English read-only source and does not narrow freedom to two review rules',()=>{
    const html=readFileSync(new URL('native-objective-redesign.html',ui),'utf8'),code=readFileSync(new URL('src/openRedesign.ts',ui),'utf8');
    expect(html).toContain('<html lang="en">');expect(html).not.toMatch(/[\u3040-\u30ff\u3400-\u9fff]/u);
    expect(code).not.toMatch(/method:\s*['"]POST|\/api\/|setInterval/);
    expect(html).toContain('NOT MEASURED AGENT ACTIVITY');expect(html).toContain('NOT HELD OUT');
    expect(code).not.toContain('review-aggregation');expect(code).toContain('system.mechanisms');
    expect(code).toContain('record?.request?.parent_system');
    expect(code).not.toContain('observations[selectedGeneration-1]');
  });
});
