import { sha256Text } from './methodObservatoryContract';

export type RecordValue = Record<string, any>;
export interface OpenEstimatorCampaign {
  schema:'scienceutopia.open-estimator-observatory.v11'; classification:string;campaign_id:string;status:'complete';
  source_binding:{report_file_sha256:string;report_content_sha256:string;source_commit:string};
  objective:{id:string;formula:string};methods:{id:string;label:string;steps:RecordValue[];updates:RecordValue[];incumbents:RecordValue}[];
  physical_researcher_responses:number;claims:RecordValue;raw_inventory_sha256:string;
  initial_baseline:null;historical_baseline:null;live_job_control:false;limitations:string[];
}
const fail = (message:string):never => {throw new Error(`Invalid v11 evidence: ${message}`);};
const finite = (v:unknown):v is number => typeof v === 'number' && Number.isFinite(v);
const hash = (v:unknown):boolean => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
export function parseOpenEstimator(value:unknown,allowFixture=false):OpenEstimatorCampaign {
  const d = value as OpenEstimatorCampaign;
  const synthetic = d?.classification === 'scripted-fixture-not-native-results';
  if (!d || d.schema !== 'scienceutopia.open-estimator-observatory.v11' || d.status !== 'complete'
      || d.classification !== (synthetic && allowFixture ? 'scripted-fixture-not-native-results' : 'actual-native-qwen-open-estimators-development-v11')) fail('actual/fixture classification');
  if (d.initial_baseline !== null || d.historical_baseline !== null || d.live_job_control !== false) fail('invented baseline or live control');
  if (!hash(d.source_binding?.report_file_sha256) || !hash(d.source_binding.report_content_sha256) || !/^[a-f0-9]{40}$/.test(d.source_binding.source_commit)) fail('immutable source binding');
  if (d.claims?.variance_reduction_established !== false || d.claims.held_out !== false || d.claims.scientific_value !== false
      || d.claims.live_fixed_Qwen_researchers !== !synthetic || d.claims.scripted_researcher_HTTP !== synthetic) fail('unsupported claims');
  if (!Array.isArray(d.methods) || d.methods.map(m=>m.id).join(',') !== 'blackbox,score-control-variate') fail('method arms');
  const ids = new Set<string>();
  for (const method of d.methods) {
    if (method.steps?.length !== 4 || method.updates?.length !== 2 || method.incumbents?.initial_unevaluated_system_scored !== false) fail('eight draws / no baseline');
    let best = Infinity;
    method.steps.forEach((step,index)=>{
      if (step.generation !== Math.floor(index/2) || step.draw_index !== index%2 || step.status !== 'complete' || !finite(step.loss)
          || !finite(step.cutoff) || !Array.isArray(step.latent) || step.latent.length !== 1 || !finite(step.latent[0])
          || !hash(step.system_fingerprint) || !hash(step.checkpoint_sha256) || typeof step.observation_id !== 'string'
          || ids.has(step.observation_id) || !step.assignment?.['review-aggregation']) fail('actual native endpoint');
      ids.add(step.observation_id);best = Math.min(best,step.loss);
      if (step.incumbent_loss !== best || method.incumbents.path[index].best_loss_so_far !== best) fail('running best');
    });
    if (method.id === 'score-control-variate') method.updates.forEach((update,generation)=>{
      const e = update.mixed_report?.expectation_estimator;
      if (update.generation !== generation || e?.status !== 'valid' || e.estimator !== (generation === 0 ? 'plain-likelihood-ratio' : 'frozen-prior-control-variate-lr')) fail('LR / prior-CV boundary');
      const ownPrior = method.steps.slice(0,2).map(s=>s.observation_id).sort();
      const current = method.steps.slice(generation*2,generation*2+2).map(s=>s.observation_id).sort();
      if (!Array.isArray(e.prior_sample_ids) || !Array.isArray(e.sample_ids)
          || JSON.stringify([...e.sample_ids].sort()) !== JSON.stringify(current)
          || generation === 0 && e.prior_sample_ids.length || generation === 1 && JSON.stringify([...e.prior_sample_ids].sort()) !== JSON.stringify(ownPrior)) fail('own prior / current IDs');
    });
  }
  return d;
}
export async function verifyOpenEstimator(text:string,receipt:any,allowFixture=false):Promise<OpenEstimatorCampaign> {
  if (receipt?.schema !== 'scienceutopia.open-estimator-ui-export.v11' || receipt.payload_sha256 !== await sha256Text(text)
      || receipt.no_inference !== true || receipt.no_job_dispatch !== true) fail('export hash / scope');
  const d = parseOpenEstimator(JSON.parse(text),allowFixture);
  if (JSON.stringify(d.source_binding) !== JSON.stringify(receipt.source_binding)) fail('source receipt differs');
  return d;
}
