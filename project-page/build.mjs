import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,cp,stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {dirname,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
export const root=dirname(fileURLToPath(import.meta.url));
const repo=resolve(root,'..');
const json=async path=>JSON.parse(await readFile(path,'utf8'));
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');

export function validateEvidence(projection,readout,closed){
  assert.equal(projection.scientific_source_commit,readout.scientific_source_commit);
  assert.equal(projection.held_out_evaluation,false);
  assert.equal(projection.paths.length,6);
  const keys=new Set();let points=0;
  for(const path of projection.paths){
    const key=`${path.method}/0/${path.objective}`;
    assert(!keys.has(key),'Duplicate path');keys.add(key);
    const actual=readout.paths[key];assert(actual,'Missing original path');
    assert.equal(actual.length,4);
    assert.deepEqual(path.losses,actual.map(row=>row.observed_loss));
    assert(actual.every(row=>row.reference_loss===projection.reference_minima[path.objective]));
    points+=actual.length;
  }
  assert.equal(points,24);
  assert.equal(closed.coverage.declared_own_slots,projection.own_attempts);
  assert.equal(closed.coverage.complete_own_slots,projection.measured_own);
  for(const [source,target] of [['better','better'],['tie','tied'],['worse','worse'],['unavailable','execution_nulls']])assert.equal(closed.own_vs_assigned_reference_counts[source],projection[target]);
  return points;
}

export async function build(){
  const source=resolve(root,'public'),out=resolve(root,'dist');
  const projection=await json(resolve(source,'evidence.json'));
  const readout=await json(resolve(repo,projection.source_data));
  const closed=await json(resolve(repo,projection.source_record));
  const points=validateEvidence(projection,readout,closed);
  const provenance=await json(resolve(source,'provenance.json'));
  assert.equal(provenance.research_source_commit,projection.source_commit);
  const receipt=await json(resolve(repo,'paper/integrated-corrected-choice-build-v1.json'));
  assert.deepEqual([receipt.pages,receipt.figures,receipt.tables,receipt.cited_references],[117,54,56,32]);
  const assets=[];
  for(const asset of provenance.assets){
    assert(asset.file.startsWith('assets/')&&!asset.file.includes('..'));
    assert(!asset.source.includes('..')&&!asset.source.startsWith('/'));
    const bytes=await readFile(resolve(repo,asset.source));
    assert.equal(digest(bytes),asset.sha256,`Historical artifact differs: ${asset.source}`);
    assert.equal(bytes.length,asset.bytes);
    if(asset.file==='assets/working-paper.pdf')assert.equal(asset.sha256,receipt.pdf_sha256);
    assets.push({asset,bytes});
  }
  assert.equal(assets.length,6);
  await mkdir(resolve(out,'assets'),{recursive:true});
  await cp(source,out,{recursive:true});
  for(const {asset,bytes} of assets)await writeFile(resolve(out,asset.file),bytes);
  const html=await readFile(resolve(out,'index.html'),'utf8');
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);assert.equal(ids.length,new Set(ids).size);
  let links=0;
  for(const [,path] of html.matchAll(/(?:href|src)="([^"]+)"/g)){
    if(path.startsWith('#'))assert(!path.slice(1)||ids.includes(path.slice(1)),path);
    else if(!path.startsWith('https://'))assert((await stat(resolve(out,path))).isFile(),path);
    links++;
  }
  for(const file of ['index.html','app.js','evidence.json','provenance.json'])assert(!(await readFile(resolve(out,file),'utf8')).includes('/Users/shiro/'));
  const report={schema:'scienceutopia.project-page-static-build.v1',status:'passed',historical_research_basis:projection.source_commit,verified_candidate_values:points,verified_unchanged_assets:assets.length,checked_links:links,model_calls:0,scientific_worlds:0};
  await writeFile(resolve(out,'build-receipt.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
  return report;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))await build();
