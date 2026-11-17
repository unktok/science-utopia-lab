import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir,cp,stat,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {dirname,resolve,sep} from 'node:path';
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

export async function articleEvidence(projection){
  const authorPath='research/data/native-corrected-choice-search-v1/authors.json';
  const literalPath='research/results/native-author-literal-changes-all8-v1.json';
  const costPath='research/results/native-terminal-cost-pilot-closed-v1.json';
  const authors=await json(resolve(repo,authorPath)),literal=await json(resolve(repo,literalPath)),cost=await json(resolve(repo,costPath));
  const behavior={proposals:authors.rows.length,same_observed_input_path:authors.rows.filter(row=>row.observed_full_inputs_match_a_complete_parent===true).length,changed_input_path_and_worse:authors.rows.filter(row=>row.status==='complete'&&row.observed_full_inputs_match_a_complete_parent===false&&row.own_minus_measured_parent>0).length,execution_nulls:authors.rows.filter(row=>row.status!=='complete'&&row.loss===null).length,completed_actions:authors.rows.reduce((sum,row)=>sum+row.session.completed_steps,0),literal_edits:literal.literal_document_changes,equal_ast_rows:literal.changed_node_rows_with_equal_python_AST,different_ast_rows:literal.changed_node_rows_with_different_python_AST,wire_edits:literal.edits_changing_connections,schedule_edits:literal.edits_changing_schedules};
  assert.deepEqual(Object.values(behavior),[8,6,1,1,112,25,19,6,0,0]);
  const controls=cost.rows.map(row=>({condition:row.condition,utility:-row.U,collected:row.K,unpaid:row.unpaid,requested:row.requested}));
  assert.equal(cost.full_scientist_request_sequences_equal,true);assert.equal(cost.automatic_invention,false);
  assert.equal(controls[0].utility,controls[1].utility);
  assert.deepEqual(controls.map(row=>[row.collected,row.unpaid,row.requested]),[[200,0,200],[160,40,200]]);
  const sources=[];
  for(const path of [projection.source_record,projection.source_data,authorPath,literalPath,costPath])sources.push({path,sha256:digest(await readFile(resolve(repo,path)))});
  return {schema:'scienceutopia.visual-story-evidence.v1',scope:'Retrospective; no new experiment. Search, behavioral readout and separate hand-designed control are not pooled as independent replications.',snapshot_date:'2026-11-17',search:projection,behavior,controls,control_scientific_source_commit:cost.scientific_source_commit,sources,new_model_calls:0,new_scientific_worlds:0};
}

async function htmlFiles(directory){
  const result=[];
  for(const entry of await readdir(directory,{withFileTypes:true})){const path=resolve(directory,entry.name);if(entry.isDirectory())result.push(...await htmlFiles(path));else if(entry.name.endsWith('.html'))result.push(path);}
  return result;
}

async function validatePage(out,file){
  const html=await readFile(file,'utf8');
  assert(html.includes('<html lang="en">'),'Published pages must be English');
  assert(!/[\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Han}]/u.test(html),'Japanese content is not part of this release');
  assert(!html.includes('data-ja=')&&!html.includes('id="language"'));
  const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(match=>match[1]);assert.equal(ids.length,new Set(ids).size);
  let links=0;
  for(const [,reference] of html.matchAll(/(?:href|src)="([^"]+)"/g)){
    if(reference.startsWith('https://')){links++;continue;}
    const [path,anchor]=reference.split('#');
    let target=path?resolve(dirname(file),path.split('?')[0]):file;
    assert(target===out||target.startsWith(out+sep),'Local link escapes the output');
    if((await stat(target)).isDirectory())target=resolve(target,'index.html');
    assert((await stat(target)).isFile(),reference);
    if(anchor){const destination=target===file?html:await readFile(target,'utf8');assert(destination.includes(`id="${anchor}"`),reference);}
    links++;
  }
  return links;
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
  const story=await articleEvidence(projection);
  await writeFile(resolve(out,'story/evidence.json'),JSON.stringify(story,null,2)+'\n');
  const pages=await htmlFiles(out);let links=0;
  for(const page of pages)links+=await validatePage(out,page);
  for(const file of ['index.html','app.js','evidence.json','provenance.json'])assert(!(await readFile(resolve(out,file),'utf8')).includes('/Users/shiro/'));
  const report={schema:'scienceutopia.project-page-static-build.v1',status:'passed',historical_research_basis:projection.source_commit,verified_candidate_values:points,verified_unchanged_assets:assets.length,checked_links:links,english_only_pages:pages.length,article_behavioral_proposals:story.behavior.proposals,model_calls:0,scientific_worlds:0};
  await writeFile(resolve(out,'build-receipt.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
  return report;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))await build();
