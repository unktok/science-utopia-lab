import { canonicalHash } from "./hash";

type Row = Record<string, any>;
export interface OpenEvidenceClaims {
  live_fixed_Qwen_researchers: boolean; scripted_researcher_HTTP: false; engineering_count_loss: true;
  held_out: false; causal_institutional_benefit: false; scientific_value: false;
  full_native_world_pathwise_autograd: false; designer_improvement_established: false; external_authorship_authenticated: false;
}
export interface OpenEvidenceObservation {
  generation: number; strategy: string; draw: Row; observation: Row | null; checkpoint_sha256?: string;
  open_domain?: Row; process_receipts?: Row[]; events?: Row[]; system?: Row; year?: number;
  boundary_coverage?: Row; conditional_backward?: Row;
}
export interface NativeOpenEvidence {
  schema: "scienceutopia.native-open-integrated-pilot.v7"; status: "in-progress" | "complete" | "budget-complete-with-failures";
  configured_researcher_provider: "qwen3:8b"; physical_response_caches: Array<{ path: string; sha256: string; outcomes: Record<string, number> }>;
  physical_reply_count: number; complete_native_worlds: number; source_commit: string; world_binding: Row; campaign_binding: Row;
  records: Row[]; observations: OpenEvidenceObservation[]; authoring: unknown; claims: OpenEvidenceClaims; content_sha256: string;
  ui_fixture?: true;
}
const SHA = /^[0-9a-f]{64}$/;
const row = (value: unknown, label: string): Row => { if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object`); return value as Row; };
const array = (value: unknown, label: string): any[] => { if (!Array.isArray(value)) throw new Error(`${label} must be an array`); return value; };
const finite = (value: unknown, label: string): number => { if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`${label} must be finite`); return value; };
const sha = (value: unknown, label: string): string => { if (typeof value !== "string" || !SHA.test(value)) throw new Error(`${label} must be lowercase SHA256`); return value; };
export function processReceiptYear(event: unknown, endpointYear: number | undefined): number | undefined {
  const envelope = row(event, "process receipt"); const payload = row(envelope.payload, "process receipt payload");
  const value = envelope.year ?? payload.year ?? endpointYear;
  return Number.isInteger(value) && value >= 1 ? value : undefined;
}
export function derivativeDiagnosticFailure(value: unknown): null | { error_type: string; error: string } {
  const report = row(value, "derivative report");
  if (report.status !== "failed-diagnostic") return null;
  if (typeof report.error_type !== "string" || !report.error_type || typeof report.error !== "string" || !report.error) throw new Error("Failed derivative diagnostic must retain its actual error");
  if (report.native_loss_gradient_verified !== false || report.full_native_world_autograd !== false) throw new Error("Failed derivative diagnostic cannot claim a native/full-world gradient");
  return { error_type: report.error_type, error: report.error };
}

function validateOpenDomain(value: unknown): void {
  const domain = row(value, "open_domain");
  if (domain.schema !== "scienceutopia.native-open-domain-state.v1") throw new Error("Unexpected NativeOpenDomain schema");
  for (const key of ["actors", "artifacts", "actor_types", "artifact_types", "values", "receipts"]) row(domain[key], `open_domain.${key}`);
  for (const [id, actorValue] of Object.entries(domain.actors)) {
    const actor = row(actorValue, `actor ${id}`); if (actor.id !== id || typeof actor.type !== "string" || !Array.isArray(actor.roles) || !Number.isInteger(actor.revision)) throw new Error(`Invalid actor ${id}`);
  }
  for (const [id, artifactValue] of Object.entries(domain.artifacts)) {
    const artifact = row(artifactValue, `artifact ${id}`); if (artifact.id !== id || typeof artifact.type !== "string" || !Array.isArray(artifact.actor_ids) || !Array.isArray(artifact.artifact_ids) || !Array.isArray(artifact.native_paper_ids)) throw new Error(`Invalid artifact ${id}`);
  }
}

export function parseNativeOpenEvidence(value: unknown, mode: "actual" | "fixture" = "actual"): NativeOpenEvidence {
  const data = row(value, "Native open evidence");
  if (data.schema !== "scienceutopia.native-open-integrated-pilot.v7") throw new Error("Unsupported native-open evidence schema");
  if ((mode === "fixture") !== (data.ui_fixture === true)) throw new Error(mode === "fixture" ? "Fixture must carry ui_fixture=true" : "Synthetic fixture cannot enter the actual evidence channel");
  if (!["in-progress", "complete", "budget-complete-with-failures"].includes(data.status) || data.configured_researcher_provider !== "qwen3:8b") throw new Error("Invalid pilot status or researcher provider");
  if (!Number.isInteger(data.physical_reply_count) || data.physical_reply_count < 0 || !Number.isInteger(data.complete_native_worlds) || data.complete_native_worlds < 0) throw new Error("Invalid physical execution counts");
  const caches = array(data.physical_response_caches, "physical_response_caches");
  for (const [index, cacheValue] of caches.entries()) { const cache = row(cacheValue, `response cache ${index}`); sha(cache.sha256, `response cache ${index} sha256`); if (typeof cache.path !== "string" || !cache.path || Object.values(row(cache.outcomes, "cache outcomes")).some((count) => !Number.isInteger(count) || count < 0)) throw new Error(`Invalid response cache ${index}`); }
  if (data.physical_reply_count !== caches.reduce((total, cache) => total + (row(row(cache, "response cache").outcomes, "cache outcomes").response ?? 0), 0)) throw new Error("Physical reply count differs from response caches");
  if (data.status === "complete" && data.complete_native_worlds !== 4) throw new Error("Complete pilot must contain all four native worlds");
  sha(data.content_sha256, "content_sha256"); row(data.world_binding, "world_binding"); row(data.campaign_binding, "campaign_binding");
  const claims = row(data.claims, "claims");
  const exact: Record<string, boolean> = { scripted_researcher_HTTP: false, engineering_count_loss: true, held_out: false, causal_institutional_benefit: false, scientific_value: false, full_native_world_pathwise_autograd: false, designer_improvement_established: false, external_authorship_authenticated: false };
  for (const [key, expected] of Object.entries(exact)) if (claims[key] !== expected) throw new Error(`Unsupported truth claim ${key}`);
  if (claims.live_fixed_Qwen_researchers !== (data.physical_reply_count > 0)) throw new Error("Live Qwen claim must follow physical reply evidence");
  const records = array(data.records, "records"); const observations = array(data.observations, "observations");
  for (const [index, valueRow] of observations.entries()) {
    const item = row(valueRow, `observation row ${index}`); if (!Number.isInteger(item.generation) || item.generation < 0 || typeof item.strategy !== "string") throw new Error(`Invalid observation identity ${index}`);
    const draw = row(item.draw, `draw ${index}`); const observation = item.observation === null ? null : row(item.observation, `observation ${index}`);
    if (observation === null || observation.status !== "complete") {
      if (observation !== null && observation.loss !== null) throw new Error("Incomplete observation must retain null loss");
      for (const forbidden of ["checkpoint_sha256", "open_domain", "process_receipts", "events", "system", "year", "boundary_coverage", "conditional_backward"]) if (forbidden in item) throw new Error(`Incomplete observation fabricated ${forbidden}`);
      continue;
    }
    finite(observation.loss, `observation ${index} loss`); sha(item.checkpoint_sha256, `observation ${index} checkpoint`); row(item.system, `system ${index}`); validateOpenDomain(item.open_domain);
    if (!Number.isInteger(item.year) || item.year < 1) throw new Error(`Invalid endpoint year ${index}`);
    const receipts = array(item.process_receipts, `process_receipts ${index}`); const events = array(item.events, `events ${index}`);
    if (receipts.some((event) => !String(row(event, "process receipt").event_type).startsWith("native.process."))) throw new Error("Non-process event in process receipts");
    const coverage = row(item.boundary_coverage, `boundary coverage ${index}`); const backward = row(item.conditional_backward, `conditional backward ${index}`);
    if (coverage.full_native_world_autograd !== false || backward.full_native_world_autograd !== false || backward.native_loss_gradient_verified !== false) throw new Error("Conditional derivative relabelled as full-world/native-loss gradient");
    derivativeDiagnosticFailure(coverage); derivativeDiagnosticFailure(backward);
    if (!Array.isArray(events) || typeof draw !== "object") throw new Error("Incomplete execution evidence");
  }
  for (const [index, valueRecord] of records.entries()) {
    const record = row(valueRecord, `record ${index}`); const request = row(record.request, `request ${index}`);
    if (request.generation !== index || typeof request.strategy_id !== "string" || !Array.isArray(record.draws) || !Array.isArray(record.observations)) throw new Error(`Invalid campaign record ${index}`);
    if (record.report !== null) { const report = row(record.report, `report ${index}`); row(report.strategy_before, "strategy_before"); row(report.strategy_after, "strategy_after"); if (report.mixed !== null) row(report.mixed, "mixed report"); }
  }
  if (data.complete_native_worlds !== observations.filter((item) => row(item, "observation row").observation?.status === "complete").length) throw new Error("Complete native-world count differs from observations");
  return data as NativeOpenEvidence;
}

export async function verifyNativeOpenEvidence(value: unknown, mode: "actual" | "fixture" = "actual"): Promise<NativeOpenEvidence> {
  const parsed = parseNativeOpenEvidence(value, mode); const payload = { ...parsed } as Row; delete payload.content_sha256;
  // The actual artifact is hash-verified by the exporter with Python's exact
  // JSON number spelling. A browser parse cannot preserve 0 versus 0.0, so it
  // must not pretend to independently reproduce that semantic hash.
  if (mode === "fixture" && await canonicalHash(payload) !== parsed.content_sha256) throw new Error("Native-open fixture content hash mismatch");
  return parsed;
}
