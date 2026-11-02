import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { NESTED_OBJECTIVES, parseNestedFoundry, verifyNestedFoundry } from '../src/nestedFoundryContract';
import { nativeRecordedEvents } from '../src/nestedFoundrySignal';
import { prepareFoundryBranch, readPreparedFoundryBranch } from '../src/foundryBranch';
import { recordedParentSystem } from '../src/openRedesignContract';
import { failedNestedFixture, nestedFixture } from './nestedFoundryFixture';
import { redesignHash } from './openRedesignFixture';
const ui=new URL('../',import.meta.url),script=new URL('scripts/export-nested-foundry-v13.mjs',ui).pathname;
function exporting(change?:(audit:any)=>void,transform?:(bytes:string)=>string){
  const audit=nestedFixture();change?.(audit);const root=mkdtempSync(resolve(tmpdir(),'scienceutopia-v13-ui-test-')),source=resolve(root,'SCRIPTED-audit.json'),serialized=JSON.stringify(audit),bytes=transform?transform(serialized):serialized;writeFileSync(source,bytes);
  execFileSync(process.execPath,[script,`--audit=${source}`,`--output=${root}`,`--expected-audit-sha256=${redesignHash(bytes)}`,`--expected-source=${audit.source_commit}`,'--allow-synthetic-temp-only'],{stdio:'pipe'});
  const text=readFileSync(resolve(root,'native-nested-search-v13.ui.json'),'utf8'),receipt=JSON.parse(readFileSync(resolve(root,'native-nested-search-v13.ui-receipt.json'),'utf8'));return {audit,root,text,receipt};
}
describe('continuous nested Institution Foundry',()=>{
  it('adds a mode to existing page and does not publish synthetic evidence',()=>{
    const a=JSON.parse(readFileSync(new URL('public/data/native-nested-search-v13.availability.json',ui),'utf8'));
    expect(['available','awaiting-audited-export']).toContain(a.status);
    if(a.status==='available')expect(a.classification).toBe('actual-native-qwen-nested-search-development-v13');
    const source=readFileSync(new URL('src/openRedesign.ts',ui),'utf8');expect(source).toContain("get('campaign')==='v13'");expect(source).not.toMatch(/method:\s*['"]POST|setInterval/);
  });
  it('retains eight real endpoint slots, 2→1→1 stages, policy before/after and literal native events',async()=>{
    const {text,receipt}=exporting(),d=await verifyNestedFoundry(text,receipt,true);expect(d.objective_order).toEqual(NESTED_OBJECTIVES);
    for(const id of NESTED_OBJECTIVES){expect(d.arms[id].observations.map((r:any)=>r.stage)).toEqual(['initial-batch','initial-batch','updated-proposal','redesign']);expect(d.arms[id].records[0].report.weights_before).not.toEqual(d.arms[id].records[0].report.weights_after);expect(nativeRecordedEvents(d.arms[id].observations[0])).toHaveLength(1);}
    expect(()=>parseNestedFoundry(JSON.parse(text))).toThrow('classification');await expect(verifyNestedFoundry(`${text} `,receipt,true)).rejects.toThrow('export hash');
  });
  it.each(['loss','cross','source','wire','stage','draw','record','update','vocabulary','weights','audit','claim'])('rejects tampered %s',kind=>{
    expect(()=>exporting(a=>{const id=NESTED_OBJECTIVES[0],arm=a.arms[id],row=arm.observations[1];
      if(kind==='loss')a.loss_specs[id].per_run.terms[0].coefficient=.1;
      if(kind==='cross')row.cross_scores[NESTED_OBJECTIVES[1]]=999;
      if(kind==='source')row.contracts.executable_sources[row.system.mechanisms[1].mechanism_id].source_sha256='0'.repeat(64);
      if(kind==='wire')row.system.connections[0].target_mechanism='MISSING';
      if(kind==='stage')row.stage='redesign';if(kind==='draw')row.draw_index=0;
      if(kind==='record')arm.records.reverse();
      if(kind==='update')arm.records[1].report.gradient={continuous_mean:[1]};
      if(kind==='vocabulary')arm.records[1].version_sha256='0'.repeat(64);
      if(kind==='weights')arm.records[1].report.weights_before={logits:{},continuous_mean:[9]};
      if(kind==='audit')a.audit.sole_conditional_LR_update_analytically_rederived=false;if(kind==='claim')a.claims.full_native_world_pathwise_autograd=true;
    })).toThrow();
  });
  it('does not invent physical worlds for failed generation or assign a penalty',async()=>{
    const {text,receipt}=exporting(a=>Object.assign(a,failedNestedFixture())),d=await verifyNestedFoundry(text,receipt,true);
    expect(d.physical_native_worlds).toBe(0);expect(d.physical_researcher_responses).toBe(0);
    expect(d.arms[NESTED_OBJECTIVES[0]].observations).toHaveLength(3);expect(d.arms[NESTED_OBJECTIVES[0]].observations.every((r:any)=>r.own_loss===null&&r.observation_id===null)).toBe(true);
  });
  it('retains unsuccessful singleton forward as null without silently updating policy',async()=>{
    const {text,receipt}=exporting(a=>{a.status='budget-complete-with-failures';a.physical_native_worlds=7;const row=a.arms[NESTED_OBJECTIVES[0]].observations[2];row.status='technical-failure';row.own_loss=row.loss=null;row.cross_scores=Object.fromEntries(NESTED_OBJECTIVES.map(id=>[id,null]));});
    const d=await verifyNestedFoundry(text,receipt,true);expect(d.arms[NESTED_OBJECTIVES[0]].observations[2].running_best).toBe(-1);
  });
  it('looks up exact stage parent, not first matching generation zero record',async()=>{
    const {text,receipt}=exporting(a=>{const arm=a.arms[NESTED_OBJECTIVES[0]];arm.records[1].request.parent_system={marker:'UPDATED-STAGE-PARENT'};});
    const d=await verifyNestedFoundry(text,receipt,true);expect(recordedParentSystem(d,NESTED_OBJECTIVES[0],d.arms[NESTED_OBJECTIVES[0]].observations[2])).toEqual({marker:'UPDATED-STAGE-PARENT'});
  });
  it('losslessly carries large integer identities through both record and observation histories',async()=>{
    const {text,receipt}=exporting(a=>{a.arms[NESTED_OBJECTIVES[0]].records[0].request.rng_seed='UNSAFE_TOKEN';},s=>s.replace('"UNSAFE_TOKEN"','1122442242526474860'));
    const d=await verifyNestedFoundry(text,receipt,true);expect(d.arms[NESTED_OBJECTIVES[0]].records[0].request.rng_seed).toBe('1122442242526474860');expect(d.numeric_encoding.paths).toContain(`/arms/${NESTED_OBJECTIVES[0]}/records/0/request/rng_seed`);
  });
  it('creates an exact local branch using existing structural helpers without mutating evidence or narrowing mechanism families',async()=>{
    const audit=nestedFixture(),row=audit.arms[NESTED_OBJECTIVES[0]].observations[0],parent=structuredClone(row.system),edited=structuredClone(parent);edited.mechanisms[1].parameters.new_parameter=4;
    const origin={source_binding:{source_commit:audit.source_commit},objective_id:NESTED_OBJECTIVES[0],observation_id:row.observation_id,system_fingerprint:row.system_fingerprint};
    const branch=prepareFoundryBranch(origin,parent,JSON.stringify(edited),audit.loss_specs[NESTED_OBJECTIVES[0]]),text=JSON.stringify(branch);
    expect(branch.state).toBe('local-unexecuted-draft');expect(branch.no_adoption).toBe(true);expect(branch.system).toEqual(edited);expect(branch.parent_system).toEqual(parent);expect(row.system).toEqual(parent);
    expect((await readPreparedFoundryBranch(text,redesignHash(text))).system).toEqual(edited);
    await expect(readPreparedFoundryBranch(`${text} `,redesignHash(text))).rejects.toThrow('hash');
    expect(()=>prepareFoundryBranch(origin,parent,JSON.stringify({...edited,connections:[{source_mechanism:'MISSING'}]}),{})).toThrow('structural');
  });
  it('never turns branch preparation into experiment execution or society adoption',()=>{
    const source=readFileSync(new URL('src/foundryBranch.ts',ui),'utf8');expect(source).not.toContain('fetch(');expect(source).toContain('FIXTURE HANDOFF DISABLED');expect(source).toContain('LOCAL UNEXECUTED DRAFT');expect(source).not.toContain('adoption-request');
    const jobs=readFileSync(new URL('src/nativeJobs.ts',ui),'utf8');expect(jobs).toContain('readPreparedFoundryBranch');expect(jobs).toContain('Validate the exact edited design and explicitly authorize its execution first');
  });
  it('ignores mismatched/missing event IDs instead of fabricating replay activity',()=>{
    const row=nestedFixture().arms[NESTED_OBJECTIVES[0]].observations[0];row.physical_proof.activity_effect_proof.annual[0].effects[0].event_id='MISMATCH';expect(nativeRecordedEvents(row)).toEqual([]);expect(nativeRecordedEvents({})).toEqual([]);
  });
  it('steps original-review-routing events in measured order and merges duplicate complete-plan receipts',()=>{
    const row=nestedFixture().arms[NESTED_OBJECTIVES[0]].observations[0],plan=row.physical_proof.activity_effect_proof.annual[0].effects[0];
    const routing={event_id:'routing-event',event_sha256:'d'.repeat(64),actual_review_count:4,event:{event_id:'routing-event',sequence:plan.event.sequence+2,year:1,event_type:'native.system.review_routed',provenance:{mechanism_id:'world.review'}}};
    row.physical_proof.capability_effect_proof={annual:[{year:1,complete_plan_effects:[{...plan,applied_plan:{full:true}}],review_routings:[routing]}]};
    const events=nativeRecordedEvents(row);expect(events).toHaveLength(2);expect(events[0]!.receipt_kind).toBe('complete-plan-effect');expect(events[0]!.applied_plan).toEqual({full:true});expect(events[1]!.receipt_kind).toBe('original-review-routing');expect(events[1]!.actual_review_count).toBe(4);
  });
  it('retains editor custom families and keeps runtime validation separate',()=>{
    const editor=readFileSync(new URL('src/nativeDesignGraphView.ts',ui),'utf8');expect(editor).toContain('allowOpenFamilies:true');expect(editor).toContain('DECLARED CUSTOM FAMILY');expect(editor).toContain('still not server-validated or executed');
  });
});
