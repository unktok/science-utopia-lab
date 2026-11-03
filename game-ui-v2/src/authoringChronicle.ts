// Read-only observed journals, never a source of consent or native outcomes.
export const AUTHOR_TOOLS = ['inspect', 'edit', 'splice', 'configure', 'validate', 'finish'] as const;
export type AuthorTool = typeof AUTHOR_TOOLS[number];
export interface AuthorStep {
  step: number; status: 'pending' | 'dispatched-response-not-receipted' | 'invalid-response' | 'applied' | 'rejected' | 'transport-error' | 'finished';
  dispatch_intent: boolean; completed: boolean; tool: AuthorTool | null;
  draft_before_sha256: string | null; draft_after_sha256: string | null;
  errors: string[]; result: unknown; authored_output?: unknown; model_call_seconds: number | null;
}
export interface AuthorGeneration { request_sha256: string; status: string; steps: AuthorStep[]; definition_sha256?: string | null }
export interface AuthorTrace {
  schema: 'scienceutopia.authoring-chronicle.v15';
  scope: 'observed-local-journals-not-independent-audit';
  generations: AuthorGeneration[]; warnings: string[];
}
const object = (v: unknown): v is Record<string, any> => !!v && typeof v === 'object' && !Array.isArray(v);
const hash = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const nullableHash = (v: unknown): boolean => v === null || hash(v);
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(x => typeof x === 'string');
export function decodeAuthorTrace(value: unknown): AuthorTrace | null {
  if (value === undefined || value === null) return null;
  const fail = (): never => { throw new Error('Authoring journal projection is malformed; no activity inferred'); };
  if (!object(value) || value.schema !== 'scienceutopia.authoring-chronicle.v15' || value.scope !== 'observed-local-journals-not-independent-audit' || !Array.isArray(value.generations) || value.generations.length > 100 || !strings(value.warnings)) return fail();
  const seen = new Set<string>();
  for (const g of value.generations) {
    if (!object(g) || !hash(g.request_sha256) || seen.has(g.request_sha256) || typeof g.status !== 'string' || !Array.isArray(g.steps) || g.steps.length > 256 || (g.definition_sha256 !== undefined && !nullableHash(g.definition_sha256))) return fail();
    seen.add(g.request_sha256); let prior = -1;
    for (const s of g.steps) {
      if (!object(s) || !Number.isSafeInteger(s.step) || s.step < 0 || s.step <= prior || !['pending', 'dispatched-response-not-receipted', 'invalid-response', 'applied', 'rejected', 'transport-error', 'finished'].includes(s.status) || typeof s.dispatch_intent !== 'boolean' || typeof s.completed !== 'boolean' || !(s.tool === null || AUTHOR_TOOLS.includes(s.tool)) || !nullableHash(s.draft_before_sha256) || !nullableHash(s.draft_after_sha256) || !strings(s.errors) || !('result' in s) || !(s.model_call_seconds === null || typeof s.model_call_seconds === 'number' && Number.isFinite(s.model_call_seconds) && s.model_call_seconds >= 0)) return fail();
      const unknownReply = s.status === 'pending' || s.status === 'dispatched-response-not-receipted';
      if (unknownReply && (s.completed || s.tool !== null || s.draft_after_sha256 !== null || s.model_call_seconds !== null)) return fail();
      if (!unknownReply && !s.completed) return fail();
      if (s.status === 'finished' && s.tool !== 'finish') return fail();
      if (s.status === 'rejected' && s.draft_before_sha256 !== s.draft_after_sha256) return fail();
      prior = s.step;
    }
  }
  return value as AuthorTrace;
}
export function authorStepChanges(step: AuthorStep): string[] {
  const output = step.authored_output;
  if (!object(output)) return [];
  const operations = Array.isArray(output.operations) ? output.operations : Array.isArray(output.arguments?.operations) ? output.arguments.operations : output.tool === 'splice' ? [{ ...output, op: 'splice' }] : object(step.result) && Array.isArray(step.result.applied_operations) ? step.result.applied_operations : [];
  return operations.filter(object).map((op: Record<string, any>) => {
    const path = typeof op.path === 'string' ? op.path : '';
    const owner = typeof op.selector?.mechanism_id === 'string' ? ` @ ${op.selector.mechanism_id}` : '';
    const field = /(?:source|code_artifact)/.test(path) ? 'SOURCE' : /connections/.test(path) ? 'WIRE' : /mechanisms/.test(path) || owner ? 'NODE' : /schedule|process|execution_order/.test(path) ? 'PROCESS' : 'FIELD';
    return `${field} / ${String(op.op ?? 'unknown').toUpperCase()}${owner} ${path || '(whole selected object)'}`;
  });
}
export function authorStepSource(step: AuthorStep): string[] {
  const bodies = new Set<string>();
  const visit = (value: unknown, depth: number, key = ''): void => {
    if (depth > 32 || !value || typeof value !== 'object') return;
    if (Array.isArray(value)) { value.forEach(item => visit(item, depth + 1, key)); return; }
    const item = value as Record<string, unknown>;
    if (key === 'code_artifact' && typeof item.source === 'string') bodies.add(item.source);
    if (typeof item.path === 'string' && /\/source$/.test(item.path)) {
      if (typeof item.value === 'string') bodies.add(item.value);
      if (item.tool === 'splice' && typeof item.text === 'string') bodies.add(item.text);
    }
    Object.entries(item).forEach(([childKey, child]) => visit(child, depth + 1, childKey));
  };
  visit(step.authored_output, 0); return [...bodies];
}
