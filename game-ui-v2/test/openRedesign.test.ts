import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { generatedPythonNode, generatedSourceBody, parseOpenRedesign, recordedParentSystem, REDESIGN_OBJECTIVES, verifyOpenRedesign } from '../src/openRedesignContract';
import { redesignFixture, redesignHash, zeroReplyRedesignFixture } from './openRedesignFixture';
const ui=new URL('../',import.meta.url),script=new URL('scripts/export-open-redesign-v12.mjs',ui).pathname;
function exporting(change?:(audit:any)=>void,fixture=true,rawTransform?:(bytes:string)=>string){
  const root=mkdtempSync(resolve(tmpdir(),'scienceutopia-v12-ui-test-')),audit=redesignFixture();change?.(audit);
  const source=resolve(root,'SCRIPTED-audit.json'),serialized=JSON.stringify(audit),bytes=rawTransform?rawTransform(serialized):serialized;writeFileSync(source,bytes);
  execFileSync(process.execPath,[script,`--audit=${source}`,`--output=${root}`,`--expected-audit-sha256=${redesignHash(bytes)}`,`--expected-source=${audit.source_commit}`,...(fixture?['--allow-synthetic-temp-only']:[])],{stdio:'pipe'});
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
  it('accepts terminal actual zero-reply failure records without claiming observed Qwen execution',async()=>{
    // Synthetic producer used only in this temporary export contract test; no actual result is published.
    const {text,receipt}=exporting(a=>{Object.assign(a,zeroReplyRedesignFixture());a.classification='actual-native-qwen-objective-redesign-development-v12';a.claims.scripted_researcher_HTTP=false;},false);
    const d=await verifyOpenRedesign(text,receipt);
    expect(d.physical_researcher_responses).toBe(0);expect(d.claims.live_fixed_Qwen_researchers).toBe(false);
    expect(d.arms[REDESIGN_OBJECTIVES[0]].observations.every(r=>r.observation_id===null&&r.own_loss===null)).toBe(true);
    const lie=JSON.parse(text);lie.claims.live_fixed_Qwen_researchers=true;expect(()=>parseOpenRedesign(lie)).toThrow('unsupported claims');
    expect(()=>exporting(a=>{Object.assign(a,zeroReplyRedesignFixture());a.classification='actual-native-qwen-objective-redesign-development-v12';a.claims.scripted_researcher_HTTP=false;a.claims.live_fixed_Qwen_researchers=true;},false)).toThrow('Researcher attribution');
  });
  it('compares G2 source with the recorded incumbent G0, not worse chronological G1',async()=>{
    const {text,receipt}=exporting(a=>{
      const arm=a.arms[REDESIGN_OBJECTIVES[0]],rows=arm.observations;
      for(const r of rows){
        const node=r.system.mechanisms[1],old=node.mechanism_id;node.mechanism_id='same-open-commons';
        r.system.connections.forEach((e:any)=>{if(e.source_mechanism===old)e.source_mechanism=node.mechanism_id;if(e.target_mechanism===old)e.target_mechanism=node.mechanism_id;});
        r.contracts.executable_sources[node.mechanism_id]=r.contracts.executable_sources[old];delete r.contracts.executable_sources[old];
      }
      rows[0].own_loss=rows[0].loss=rows[0].cross_scores[REDESIGN_OBJECTIVES[0]]=-5;rows[0].metrics['native.accepted_decisions'].value=5;rows[0].cross_scores[REDESIGN_OBJECTIVES[1]]=3.25*5+.05*24;
      rows[2].parent_system_fingerprint=rows[0].system_fingerprint;
      arm.records[2].request.parent_system=rows[0].system;
    });
    const d=await verifyOpenRedesign(text,receipt,true),id=REDESIGN_OBJECTIVES[0],arm=d.arms[id];
    expect(arm.observations[1]!.own_loss!>arm.observations[0]!.own_loss!).toBe(true);
    expect(recordedParentSystem(d,id,arm.observations[2]!)).toEqual(arm.observations[0]!.system);
    expect(recordedParentSystem(d,id,arm.observations[2]!)).not.toEqual(arm.observations[1]!.system);
    const parentNode=recordedParentSystem(d,id,arm.observations[2]!)!.mechanisms.find((node:any)=>node.mechanism_id==='same-open-commons');
    expect(parentNode.parameters.code_artifact.source).toContain('"shared_evidence": 0');
    expect(parentNode.parameters.code_artifact.source).not.toContain('"shared_evidence": 1');
    delete arm.records;expect(recordedParentSystem(d,id,arm.observations[2]!)).toEqual(arm.observations[0]!.system);
  });
  it('rejects a fabricated native observation ID on a failed authoring generation',()=>{
    expect(()=>exporting(a=>{Object.assign(a,zeroReplyRedesignFixture());a.arms[REDESIGN_OBJECTIVES[0]].observations[0].observation_id='INVENTED-NATIVE-ID';})).toThrow('cannot invent');
  });
  it('retains and validates a generated Python delegate inside one process wrapper, including its exact parent body',async()=>{
    const {text,receipt}=exporting(a=>{
      const arm=a.arms[REDESIGN_OBJECTIVES[0]],rows=arm.observations;
      for(const r of rows){
        const delegate=r.system.mechanisms[1],old=delegate.mechanism_id;
        r.system.mechanisms[1]={mechanism_id:'open-process',family:'process',implementation:'native.process.activity.v1',parameters:{delegate,repeat:1,initial_delegate_state:{}}};
        r.system.connections.forEach((e:any)=>{if(e.source_mechanism===old)e.source_mechanism='open-process';if(e.target_mechanism===old)e.target_mechanism='open-process';});
        r.contracts.processes={'open-process':r.system.mechanisms[1].parameters};
      }
      rows[2].parent_system_fingerprint=rows[0].system_fingerprint;arm.records[2].request.parent_system=rows[0].system;
    });
    const d=await verifyOpenRedesign(text,receipt,true),id=REDESIGN_OBJECTIVES[0],r=d.arms[id].observations[2]!,node=r.system.mechanisms[1];
    expect(node.implementation).toBe('native.process.activity.v1');expect(node.parameters.repeat).toBe(1);
    expect(generatedPythonNode(node)?.mechanism_id).toBe('fixture-cooperative-2');
    expect(generatedSourceBody(node)).toContain('"shared_evidence": 2');
    const parentNode=recordedParentSystem(d,id,r)!.mechanisms.find((n:any)=>n.mechanism_id==='open-process');
    expect(generatedSourceBody(parentNode)).toContain('"shared_evidence": 0');
    expect(generatedSourceBody(parentNode)).not.toContain('"shared_evidence": 1');
    expect(r.contracts.processes['open-process']).toEqual(node.parameters);
    expect(()=>exporting(a=>{
      const r=a.arms[REDESIGN_OBJECTIVES[0]].observations[0],delegate=r.system.mechanisms[1];
      r.system.mechanisms[1]={...delegate,implementation:'native.process.activity.v1',parameters:{delegate}};
      r.contracts.executable_sources[delegate.mechanism_id].source_sha256='0'.repeat(64);
    })).toThrow('source contract differs');
  });
  it('never recursively unwraps nested process delegates',()=>{
    const python={implementation:'code.python.v1',parameters:{code_artifact:{source:'SCRIPTED'}}};
    const nested={implementation:'native.process.activity.v1',parameters:{delegate:{implementation:'native.process.activity.v1',parameters:{delegate:python}}}};
    expect(generatedPythonNode(nested)).toBeUndefined();expect(generatedSourceBody(nested)).toBe('');
    expect(()=>exporting(a=>{const r=a.arms[REDESIGN_OBJECTIVES[0]].observations[0];r.system.mechanisms[1]={...nested,mechanism_id:r.system.mechanisms[1].mechanism_id};})).toThrow('Recursive process delegates');
  });
  it('preserves unsafe integer lexical tokens exactly without changing source strings, floats or exponents',async()=>{
    const {text,receipt}=exporting(a=>{
      const r=a.arms[REDESIGN_OBJECTIVES[0]].observations[0];
      r.draw={rng_seed:'__UNSAFE_RNG__',negative_probe:'__UNSAFE_NEGATIVE__',large_float:'__LARGE_FLOAT__',large_exponent:'__LARGE_EXPONENT__',quoted_seed:'1122442242526474860'};
      const artifact=r.system.mechanisms[1].parameters.code_artifact;
      artifact.source+='\n# literal 1122442242526474860; quoted "1122442242526474860"; exponent 1e20; float 10000000000000000.0\n';
      const proof=r.contracts.executable_sources['fixture-cooperative-0'];proof.source=artifact.source;proof.source_sha256=redesignHash(artifact.source);
    },true,bytes=>bytes.replace('"__UNSAFE_RNG__"','1122442242526474860').replace('"__UNSAFE_NEGATIVE__"','-714974383112699265').replace('"__LARGE_FLOAT__"','10000000000000000.0').replace('"__LARGE_EXPONENT__"','1e20'));
    const d=await verifyOpenRedesign(text,receipt,true),r=d.arms[REDESIGN_OBJECTIVES[0]].observations[0]!;
    expect(r.draw.rng_seed).toBe('1122442242526474860');expect(r.draw.negative_probe).toBe('-714974383112699265');
    expect(r.draw.quoted_seed).toBe('1122442242526474860');expect(typeof r.draw.large_float).toBe('number');expect(r.draw.large_exponent).toBe(1e20);
    expect(generatedSourceBody(r.system.mechanisms[1])).toContain('literal 1122442242526474860; quoted "1122442242526474860"; exponent 1e20; float 10000000000000000.0');
    expect(d.numeric_encoding.paths).toEqual([`/arms/${REDESIGN_OBJECTIVES[0]}/observations/0/draw/rng_seed`,`/arms/${REDESIGN_OBJECTIVES[0]}/observations/0/draw/negative_probe`]);
    const tampered=structuredClone(receipt);tampered.numeric_encoding.paths=[];await expect(verifyOpenRedesign(text,tampered,true)).rejects.toThrow('integer encoding receipt');
    const wrong=JSON.parse(text);wrong.arms[REDESIGN_OBJECTIVES[0]].observations[0].draw.rng_seed=1122442242526474860;expect(()=>parseOpenRedesign(wrong,true)).toThrow('unsafe integer text');
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
    expect(code).toContain('recordedParentSystem(data,armId(),selected)');
    expect(code).not.toContain('observations[selectedGeneration-1]');
  });
});
