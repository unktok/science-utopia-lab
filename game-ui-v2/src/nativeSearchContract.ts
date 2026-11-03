import { parseExactDraft } from './foundryBranch';
import { stableStringify } from './hash';

export interface NativeSearchRequest {
  schema: 'scienceutopia.native-search-request.v14'; initial_system: Record<string, unknown>; loss_spec: Record<string, unknown>;
  seed: number; years: number; method: 'blackbox' | 'nested-lr'; native_budget: number;
  designer: { model: 'qwen3:8b'; max_attempts: number; max_tokens: number };
}
export interface StagedSearchRequest extends Omit<NativeSearchRequest, 'schema' | 'designer'> {
  schema: 'scienceutopia.native-search-request.v15';
  designer: { model: 'qwen3:8b'; max_steps: number; max_tokens: number };
}
export type AnyNativeSearchRequest = NativeSearchRequest | StagedSearchRequest;
export function stagedProviderAttemptLimit(request: StagedSearchRequest): number { return (request.method === 'nested-lr' ? 2 : request.native_budget) * request.designer.max_steps; }
const object = (value: unknown): value is Record<string, any> => !!value && typeof value === 'object' && !Array.isArray(value);
const integer = (value: number, min: number, max: number, name: string): void => { if (!Number.isSafeInteger(value) || value < min || value > max) throw new Error(`${name} must be an integer from ${min} to ${max}`); };
export function nativeSearchRequest(system: string, loss: string, seed: number, years: number, method: string, budget: number, attempts: number, tokens: number): NativeSearchRequest {
  const initial_system = parseExactDraft(system), loss_spec = parseExactDraft(loss);
  if (!object(initial_system) || !object(loss_spec)) throw new Error('Exact SystemSpec and LossSpec JSON objects required');
  integer(seed, 0, 2147483647, 'Development seed'); integer(years, 1, 4, 'Native years');
  if (method !== 'blackbox' && method !== 'nested-lr') throw new Error('Unknown search method');
  integer(budget, 1, 8, 'Native world budget');
  if (method === 'nested-lr' && budget !== 4) throw new Error('Nested LR requires exactly four native slots: 2 → 1 → 1');
  integer(attempts, 1, 3, 'Designer attempts'); integer(tokens, 512, 8192, 'Designer output tokens');
  return { schema: 'scienceutopia.native-search-request.v14', initial_system, loss_spec, seed, years, method, native_budget: budget, designer: { model: 'qwen3:8b', max_attempts: attempts, max_tokens: tokens } };
}
export function nativeSearchWireRequest(...args: Parameters<typeof nativeSearchRequest>): { request: NativeSearchRequest; request_json: string } {
  const request = nativeSearchRequest(...args), [system, loss] = args;
  // JSON.parse + JSON.stringify erases Python's float-vs-int identity for 1.0,
  // -1.0 and 0.0. Validate these substrings, then embed their original JSON.
  const request_json = `{${Object.entries(request).map(([key, value]) => `${JSON.stringify(key)}:${key === 'initial_system' ? system : key === 'loss_spec' ? loss : JSON.stringify(value)}`).join(',')}}`;
  return { request, request_json };
}
export function stagedSearchWireRequest(system: string, loss: string, seed: number, years: number, method: string, budget: number, steps: number, tokens: number): { request: StagedSearchRequest; request_json: string } {
  const base = nativeSearchRequest(system, loss, seed, years, method, budget, 1, tokens); integer(steps, 1, 64, 'Designer tool steps');
  const request: StagedSearchRequest = { ...base, schema: 'scienceutopia.native-search-request.v15', designer: { model: 'qwen3:8b', max_steps: steps, max_tokens: tokens } };
  const request_json = `{${Object.entries(request).map(([key, value]) => `${JSON.stringify(key)}:${key === 'initial_system' ? system : key === 'loss_spec' ? loss : JSON.stringify(value)}`).join(',')}}`;
  return { request, request_json };
}
export interface SearchBinding { request: AnyNativeSearchRequest; request_json: string; request_sha256: string; source_commit: string }
export function validateSearchBinding(value: any, request: AnyNativeSearchRequest, source: string, request_json = JSON.stringify(request)): SearchBinding {
  if (value?.status !== 'structurally-validated-not-native-executed' || !/^[a-f0-9]{64}$/.test(value.request_sha256)
    || value.source_commit !== source || !/^[a-f0-9]{40}$/.test(source) || value.method !== request.method || value.planned_native_world_budget !== request.native_budget) throw new Error('Runtime validation source, method or budget binding differs');
  if (stableStringify(parseExactDraft(request_json)) !== stableStringify(request)) throw new Error('Exact wire request differs from validated request');
  return { request: structuredClone(request), request_json, request_sha256: value.request_sha256, source_commit: source };
}
// Decode exact integer lexical tokens before Number can round them. Strings,
// floating lexical tokens and source-code bodies retain their original meaning.
export function decodeSearchEvidence(text: string): { value: any; integer_paths: string[] } {
  let supported = false;
  JSON.parse('1', (_key, value, context?: { source?: string }) => { supported = context?.source === '1'; return value; });
  if (!supported) throw new Error('Lossless JSON decoder unavailable; use a current browser');
  const fields = new WeakMap<object, Set<string>>();
  const value = JSON.parse(text, function (key, value, context?: { source?: string }) {
    if (typeof value === 'number' && !Number.isFinite(value)) throw new Error('Non-finite evidence number');
    if (typeof value === 'number' && /^-?[0-9]+$/.test(context?.source ?? '') && !Number.isSafeInteger(value)) {
      let keys = fields.get(this); if (!keys) { keys = new Set(); fields.set(this, keys); } keys.add(key); return context!.source;
    } return value;
  });
  const integer_paths: string[] = [];
  const visit = (item: any, path: string): void => { if (!object(item) && !Array.isArray(item)) return; for (const key of Object.keys(item)) { const next = `${path}/${key.replaceAll('~', '~0').replaceAll('/', '~1')}`; if (fields.get(item)?.has(key)) integer_paths.push(next); visit((item as any)[key], next); } };
  visit(value, ''); return { value, integer_paths };
}
export function verifySearchProgress(value: any, binding?: SearchBinding, expectedId?: string): Record<string, any> {
  if (!['scienceutopia.native-search-progress.v14', 'scienceutopia.native-search-progress.v15'].includes(value?.schema) || typeof value.search_id !== 'string' || !/^[a-f0-9]{40}$/.test(value.source_commit)
    || !/^[a-f0-9]{64}$/.test(value.request_sha256) || !['queued', 'running', 'complete', 'failed'].includes(value.status)
    || !Array.isArray(value.records) || !Array.isArray(value.observations) || !object(value.budget) || !Array.isArray(value.errors)) throw new Error('Malformed native search progress');
  if (expectedId && value.search_id !== expectedId) throw new Error('Search identity differs');
  if (binding && (value.source_commit !== binding.source_commit || value.request_sha256 !== binding.request_sha256 || stableStringify(value.request) !== stableStringify(binding.request))) throw new Error('Search request or source differs from the consented validation');
  const requestSchema = value.schema === 'scienceutopia.native-search-progress.v15' ? 'scienceutopia.native-search-request.v15' : 'scienceutopia.native-search-request.v14';
  if (value.request?.schema !== requestSchema || !['blackbox', 'nested-lr'].includes(value.method) || value.method !== value.request?.method || value.native_budget !== value.request?.native_budget) throw new Error('Search method or budget differs');
  return value;
}
export function pendingNativeDesigns(value: any): { suggestion: Record<string, any>; observation: null; pending_native_observation: true; draw_index: number }[] {
  const pending = value?.pending;
  if (!object(pending) || !Array.isArray(pending.draws) || !Array.isArray(pending.observations)) return [];
  return pending.draws.flatMap((draw: any, index: number) => {
    // Only supplied, not-yet-observed suggestions. No graph is derived from an
    // author's finish, an invalid draft, a failed draw or a request's parent.
    if (index < pending.observations.length || !object(draw) || draw.technical_error || !object(draw.suggestion) || !object(draw.suggestion.candidate) || !Array.isArray(draw.suggestion.candidate.mechanisms)) return [];
    return [{ suggestion: draw.suggestion, observation: null, pending_native_observation: true as const, draw_index: index }];
  });
}
export function nativeSearchLiveTelemetry(value: any): { phase: string; year: string; designer: string; researcher: string; note: string } {
  const phase = typeof value?.stage === 'string' ? value.stage.toUpperCase() : 'UNAVAILABLE';
  const missing = { phase, year: 'UNAVAILABLE', designer: 'UNAVAILABLE', researcher: 'UNAVAILABLE', note: 'No observed live-progress receipt. Missing counts remain unavailable; durable search status is shown separately.' };
  const live = value?.live_progress;
  if (live?.schema !== 'scienceutopia.native-search-live-progress.v14' || live.scope !== 'observed-local-files-not-final-audited-cost') return missing;
  const count = (number: unknown): string => typeof number === 'number' && Number.isSafeInteger(number) && number >= 0 ? String(number) : 'UNAVAILABLE';
  const year = count(live.researcher?.latest_checkpoint_year), years = count(value.request?.years);
  const warnings = Array.isArray(live.warnings) && live.warnings.length ? ` / WARNINGS ${live.warnings.join(', ')}` : '';
  return { phase, year: year === 'UNAVAILABLE' ? year : `${year} / ${years} MAX OBSERVED`,
    designer: `${count(live.designer?.attempts_completed)} COMPLETED / ${count(live.designer?.attempts_started)} DISPATCH INTENTS`,
    researcher: `${count(live.researcher?.cached_responses)} KNOWN CACHE ROWS`,
    note: `PROVISIONAL OBSERVED LOCAL FILES / ${typeof live.observed_at === 'string' ? live.observed_at : 'TIME UNAVAILABLE'} / Designer counts are receipt files; researcher counts are known bound cache rows. Not final audited physical calls. Checkpoint filenames do not establish world completion. Missing counts remain unavailable.${warnings}` };
}
export class NativeSearchConsent {
  revision = 0; binding: SearchBinding | null = null; consented = false; submitting = false;
  changed(): void { this.revision++; this.binding = null; this.consented = false; }
  validated(binding: SearchBinding, revision: number, current: AnyNativeSearchRequest, request_json = JSON.stringify(current)): boolean {
    if (revision !== this.revision || stableStringify(current) !== stableStringify(binding.request) || request_json !== binding.request_json) return false;
    this.binding = binding; this.consented = false; return true;
  }
  consent(value: boolean): void { this.consented = !!this.binding && value; }
  canSubmit(request: AnyNativeSearchRequest, request_json = JSON.stringify(request)): boolean {
    if (this.binding && (request_json !== this.binding.request_json || stableStringify(request) !== stableStringify(this.binding.request))) { this.changed(); return false; }
    return !this.submitting && this.consented && !!this.binding;
  }
  begin(request: AnyNativeSearchRequest, request_json = JSON.stringify(request)): SearchBinding {
    if (!this.canSubmit(request, request_json)) throw new Error('Validate this exact request, then explicitly consent to its compute budget');
    const binding = this.binding!; this.submitting = true; this.changed(); return binding;
  }
}
