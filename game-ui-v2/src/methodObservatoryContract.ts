export interface Point { coordinates: number[]; actual_loss: number; }
export interface MethodStep extends Point {
  id: string; step: number; hard_represented_loss: number | null;
  backward: null | { coordinates: number[]; gradient: number[]; represented_loss: number; temperature: number; scope: string; operator_file_sha256: string; native_derivative_verified: boolean };
  native_receipt_sha256: string; checkpoint_sha256: string; system_fingerprint: string;
  measurements: Record<string, number>; fresh_replies: number; replayed_replies: number; elapsed_seconds: number;
}
export interface MethodArm {
  id: string; label: string; gradient_kind: 'none' | 'represented-pathwise' | 'score-function' | 'mixed';
  oracle: string; initial: Point; historical_incumbent: Point; final_incumbent: Point;
  cost: { fresh_native_worlds: number; fresh_physical_replies: number; historical_observations_charged: number }; steps: MethodStep[];
}
export interface MethodObservatory {
  schema: 'scienceutopia.method-observatory.v1'; campaign_id: string; classification: string; status: 'complete'; execution_kind: 'actual-native-qwen' | 'scripted-fixture';
  source_binding: { report_path: string; report_file_sha256: string; report_content_sha256: string; source_commit: string };
  objective: { id: string; formula: string; direction: 'minimize' }; coordinate_labels: string[];
  world: { model: string; seed: number; researchers: number; years: number; corpus_years: number; weights: string };
  methods: MethodArm[];
  cost_accounting: { native_world_elapsed_seconds: number; new_fresh_physical_replies: number; total_unique_actual_calls_supporting_paths: number; shared_historical_unique_actual_support: number };
  claims: { ongoing_jobs: false; viewing_starts_jobs: false; optimizer_superiority: false }; raw_binding: { file_count: number; inventory_sha256: string }; limitations: string[];
}
const fail = (message: string): never => { throw new Error(`Invalid method evidence: ${message}`); };
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
const hash = (value: unknown): boolean => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
export function parseMethodObservatory(value: unknown): MethodObservatory {
  const d = value as MethodObservatory;
  if (!d || d.schema !== 'scienceutopia.method-observatory.v1' || d.status !== 'complete') fail('schema / terminal status');
  if (!['actual-native-qwen', 'scripted-fixture'].includes(d.execution_kind)) fail('execution kind');
  if (d.execution_kind === 'scripted-fixture' && !d.classification.includes('fixture')) fail('fixture attribution');
  if (d.execution_kind === 'actual-native-qwen' && !d.classification.startsWith('actual-native-qwen-')) fail('actual attribution');
  if (d.claims?.ongoing_jobs !== false || d.claims.viewing_starts_jobs !== false || d.claims.optimizer_superiority !== false) fail('unsupported live / superiority claim');
  if (!hash(d.source_binding?.report_file_sha256) || !hash(d.source_binding.report_content_sha256) || !/^[a-f0-9]{40}$/.test(d.source_binding.source_commit)) fail('source binding');
  if (!d.objective || d.objective.direction !== 'minimize' || !d.objective.formula) fail('objective');
  if (!Array.isArray(d.methods) || !d.methods.length || new Set(d.methods.map((m) => m.id)).size !== d.methods.length) fail('methods');
  const dimension = d.coordinate_labels?.length;
  const point = (p: Point) => p && finite(p.actual_loss) && Array.isArray(p.coordinates) && p.coordinates.length === dimension && p.coordinates.every(finite);
  for (const method of d.methods) {
    if (!['none', 'represented-pathwise', 'score-function', 'mixed'].includes(method.gradient_kind) || !point(method.initial) || !point(method.historical_incumbent) || !point(method.final_incumbent)) fail('method state');
    if (!Array.isArray(method.steps) || !method.steps.length) fail('empty steps');
    method.steps.forEach((step, index) => {
      if (!point(step) || step.step !== index || !hash(step.native_receipt_sha256) || !hash(step.system_fingerprint) || !hash(step.checkpoint_sha256)) fail('endpoint binding');
      if (method.gradient_kind === 'none' && step.backward !== null) fail('black-box gradient leakage');
      if (step.backward && (!step.backward.gradient.every(finite) || step.backward.gradient.length !== dimension || !finite(step.backward.represented_loss) || !point({ coordinates: step.backward.coordinates, actual_loss: step.backward.represented_loss }) || !hash(step.backward.operator_file_sha256))) fail('backward binding');
    });
  }
  return d;
}
export async function sha256Text(text: string): Promise<string> {
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(bytes)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}
export async function verifyMethodExport(text: string, receipt: any): Promise<MethodObservatory> {
  if (receipt?.schema !== 'scienceutopia.method-observatory-export.v1' || receipt.no_inference !== true || receipt.no_job_dispatch !== true || receipt.payload_sha256 !== await sha256Text(text)) fail('export receipt');
  const data = parseMethodObservatory(JSON.parse(text));
  if (JSON.stringify(data.source_binding) !== JSON.stringify(receipt.source_binding)) fail('receipt / source mismatch');
  return data;
}
