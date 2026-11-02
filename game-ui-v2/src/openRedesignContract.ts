import { sha256Text } from './methodObservatoryContract';

export const REDESIGN_OBJECTIVES = ['native-joint-v5-throughput', 'native-joint-v5-net-reviewed-utility'] as const;
export type ObjectiveId = typeof REDESIGN_OBJECTIVES[number];
export type Evidence = Record<string, any>;
export interface RedesignObservation extends Evidence {
  generation: number; draw_index: 0; observation_id: string | null; own_loss: number | null;
  cross_scores: Record<ObjectiveId, number | null>; status: string;
}
export interface OpenRedesign extends Evidence {
  schema: 'scienceutopia.open-redesign-observatory.v12'; classification: string;
  source_binding: { report_file_sha256: string; report_content_sha256: string; source_commit: string };
  objective_order: ObjectiveId[]; arms: Record<ObjectiveId, { observations: RedesignObservation[]; [key: string]: any }>;
  physical_researcher_responses: number; live_job_control: false;
}
const fail = (message: string): never => { throw new Error(`Invalid v12 evidence: ${message}`); };
const hash = (value: unknown): boolean => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
export function parseOpenRedesign(value: unknown, allowFixture = false): OpenRedesign {
  const d = value as OpenRedesign;
  const fixture = d?.classification === 'scripted-fixture-not-native-results';
  if (!d || d.schema !== 'scienceutopia.open-redesign-observatory.v12'
      || d.classification !== (allowFixture && fixture ? 'scripted-fixture-not-native-results' : 'actual-native-qwen-objective-redesign-development-v12')) fail('actual / fixture classification');
  if (d.live_job_control !== false || d.initial_baseline !== null || d.historical_baseline !== null) fail('invented baseline or live control');
  if (!hash(d.source_binding?.report_file_sha256) || !hash(d.source_binding.report_content_sha256)
      || !/^[a-f0-9]{40}$/.test(d.source_binding.source_commit)) fail('immutable source binding');
  if (JSON.stringify(d.objective_order) !== JSON.stringify(REDESIGN_OBJECTIVES)) fail('objective order');
  if (!Number.isInteger(d.physical_researcher_responses) || d.physical_researcher_responses < 0) fail('physical replies');
  const ids = new Set<string>();
  for (const id of REDESIGN_OBJECTIVES) {
    const arm = d.arms?.[id];
    if (!arm || arm.objective_id !== id || !Array.isArray(arm.observations) || arm.observations.length > 3) fail('objective arm');
    let best = Infinity;
    arm.observations.forEach((row, index) => {
      if (row.arm !== id || row.generation !== index || row.draw_index !== 0
          || row.observation_id !== null && (typeof row.observation_id !== 'string' || ids.has(row.observation_id))) fail('observation lineage');
      if (row.observation_id !== null) ids.add(row.observation_id);
      if (row.status === 'complete') {
        if (typeof row.observation_id !== 'string' || !row.observation_id || !finite(row.own_loss) || row.loss !== row.own_loss || row.cross_scores?.[id] !== row.own_loss
            || !hash(row.system_fingerprint) || !hash(row.checkpoint_sha256)
            || !Array.isArray(row.system?.mechanisms) || !Array.isArray(row.system?.connections)
            || !row.physical_proof || !row.lineage?.vs_parent || !row.lineage.vs_initial) fail('actual native endpoint');
        for (const target of REDESIGN_OBJECTIVES) if (row.cross_scores[target] !== null && !finite(row.cross_scores[target])) fail('cross-objective score');
        best = Math.min(best, row.own_loss!);
      } else if (row.own_loss !== null || row.loss !== null || REDESIGN_OBJECTIVES.some(target => row.cross_scores?.[target] !== null)) fail('failed endpoint scored');
      if (row.running_best !== (best === Infinity ? null : best)) fail('running best');
    });
  }
  if (d.claims?.held_out !== false || d.claims.scientific_value !== false || d.claims.causal_institutional_benefit !== false
      || d.claims.external_authorship_authenticated !== false || d.claims.live_fixed_Qwen_researchers !== !fixture || d.claims.scripted_researcher_HTTP !== fixture) fail('unsupported claims');
  return d;
}
export async function verifyOpenRedesign(text: string, receipt: Evidence, allowFixture = false): Promise<OpenRedesign> {
  if (receipt?.schema !== 'scienceutopia.open-redesign-ui-export.v12' || receipt.payload_sha256 !== await sha256Text(text)
      || receipt.no_inference !== true || receipt.no_job_dispatch !== true) fail('export hash / scope');
  const d = parseOpenRedesign(JSON.parse(text), allowFixture);
  if (JSON.stringify(receipt.source_binding) !== JSON.stringify(d.source_binding)) fail('source receipt differs');
  return d;
}
