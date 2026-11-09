import { webCanonicalHash } from "./hash";

export interface MechanismRow {
  id: string; condition: string; seed: number; status: string;
  scores: Record<string, number | null> | null; observation_sha256: string | null;
}
export interface ReferenceRow {
  id: string; seed: number; status: string;
  scores: Record<string, number | null> | null; observation_sha256: string | null;
}
export interface ReadinessReceipt {
  accepted: number; total: number; passed: boolean; certificate_sha256: string;
}
export interface PreScaleSnapshot {
  schema: string; observed_utc: string; observation_kind: string; scope: string;
  scientist_model: string; designer_model: string;
  information: { source_commit: string; plan_sha256: string; closure_recorded: boolean;
    numeric_readiness: { objective: string; status: string; request_sha256: string; result_sha256: string;
      scientific_loss: null; retained_parent_explicitly: boolean | null }[];
    worlds: MechanismRow[] };
  search: { status: string; source_commit: string | null; selection_fixed: boolean;
    observed_stage?: string | null; stage_error_type?: string | null;
    reference_worlds?: ReferenceRow[];
    readiness?: { numeric: ReadinessReceipt | null; editor: ReadinessReceipt | null };
    candidate_slots: { arm: string; generation: number; status: string; loss: number | null }[];
    evaluation_observations: number; evaluation_plan_worlds: number | null };
  boundaries: Record<string, boolean>;
}
const object = (x: unknown): x is Record<string, unknown> => !!x && typeof x === "object" && !Array.isArray(x);
const hash = (x: unknown, size = 64): x is string => typeof x === "string" && new RegExp(`^[0-9a-f]{${size}}$`).test(x);
const loss = (x: unknown) => x === null || (typeof x === "number" && Number.isFinite(x));
const integer = (x: unknown) => typeof x === "number" && Number.isSafeInteger(x) && x >= 0;
const scoresValid = (x: unknown): boolean => x === null || object(x) && ["throughput", "efficiency", "selective"].every(k => loss(x[k]));

export function snapshotSource(search: string): "recorded" | "latest" {
  const source = new URLSearchParams(search).get("source") ?? "recorded";
  if (source !== "recorded" && source !== "latest") throw new Error("Unknown snapshot source; only local recorded/latest files are allowed");
  return source;
}

export async function validatePreScale(envelope: unknown): Promise<PreScaleSnapshot> {
  if (!object(envelope) || envelope.schema !== "scienceutopia.pre-scale-observatory.v1.envelope"
      || !object(envelope.payload) || !hash(envelope.web_sha256) || !hash(envelope.payload_sha256)) throw new Error("Missing evidence envelope");
  const p = envelope.payload;
  const boundaries = p.boundaries;
  if (await webCanonicalHash([p]) !== envelope.web_sha256) throw new Error("Evidence checksum mismatch");
  if (p.schema !== "scienceutopia.pre-scale-observatory.v1"
      || p.observation_kind !== "timestamped-journal-projection-not-live-heartbeat-or-independent-audit"
      || typeof p.observed_utc !== "string" || !Number.isFinite(Date.parse(p.observed_utc))
      || typeof p.scope !== "string" || p.scientist_model !== "qwen3:8b"
      || p.designer_model !== "qwen3.6:35b-mlx-64k" || !object(p.information) || !object(p.search)
      || !object(boundaries) || ["loss_is_not_scientific_truth", "unknown_is_not_zero", "source_specific_certificates", "no_submission_from_viewer"].some(k => boundaries[k] !== true)) throw new Error("Unrecognized scientific boundary");
  const info = p.information;
  if (!hash(info.source_commit, 40) || !hash(info.plan_sha256) || typeof info.closure_recorded !== "boolean"
      || !Array.isArray(info.worlds) || info.worlds.length !== 12 || !Array.isArray(info.numeric_readiness)
      || info.numeric_readiness.length > 2) throw new Error("Invalid information-study scope");
  const ids = new Set<string>();
  for (const r of info.worlds) {
    if (!object(r) || typeof r.id !== "string" || ids.has(r.id) || !["M0", "M1", "M2", "M3"].includes(String(r.condition))
        || typeof r.seed !== "number" || ![41001, 41011, 41017].includes(r.seed) || r.id !== `${r.condition}-s${r.seed}`
        || !["not-dispatched", "started-no-terminal-observation", "complete", "failed", "invalid"].includes(String(r.status))
        || (r.observation_sha256 !== null && !hash(r.observation_sha256))
        || !scoresValid(r.scores)) throw new Error("Invalid or duplicated world record");
    if (r.status === "complete" && (!hash(r.observation_sha256) || r.scores === null)) throw new Error("Complete world lacks recorded measurements");
    ids.add(r.id);
  }
  if (info.closure_recorded && info.worlds.some(r => !object(r) || r.status !== "complete")) throw new Error("Premature mechanism closure");
  for (const r of info.numeric_readiness) {
    if (!object(r) || !["throughput", "efficiency"].includes(String(r.objective))
        || !["submitted", "failed"].includes(String(r.status)) || r.scientific_loss !== null
        || !hash(r.request_sha256) || !hash(r.result_sha256)
        || (r.retained_parent_explicitly !== null && typeof r.retained_parent_explicitly !== "boolean")) throw new Error("Readiness is not a scientific outcome");
  }
  const search = p.search;
  if (!["not-dispatched", "prepared-no-stage-terminal", "stage-started-no-terminal", "stage-stopped", "stage-closed", "recorded-closed"].includes(String(search.status))
      || (search.source_commit !== null && !hash(search.source_commit, 40)) || typeof search.selection_fixed !== "boolean"
      || !Array.isArray(search.candidate_slots) || search.candidate_slots.length > 16
      || !integer(search.evaluation_observations) || Number(search.evaluation_observations) > 36
      || (search.evaluation_plan_worlds !== null && (!integer(search.evaluation_plan_worlds) || Number(search.evaluation_plan_worlds) > 36))) throw new Error("Invalid search/evaluation scope");
  const slots = new Set<string>();
  if (search.reference_worlds !== undefined) {
    const names = ["open-seed", "legacy", "reviewed-accept-all", "no-review-accept-all", "no-review-reject-all", "information-disconnected"];
    const refs = new Set<string>();
    if (!Array.isArray(search.reference_worlds) || search.reference_worlds.length !== 6) throw new Error("Six declared reference worlds required");
    for (const r of search.reference_worlds) {
      if (!object(r) || typeof r.id !== "string" || !names.includes(r.id) || refs.has(r.id) || r.seed !== 41001
        || !["not-dispatched", "started-no-terminal-observation", "complete", "failed", "invalid"].includes(String(r.status))
        || !scoresValid(r.scores) || (r.observation_sha256 !== null && !hash(r.observation_sha256))) throw new Error("Invalid reference world");
      if (r.status === "complete" && (!hash(r.observation_sha256) || r.scores === null
        || !object(r.scores) || Object.values(r.scores).some(v => v === null))) throw new Error("Complete reference lacks measurements");
      if (r.status !== "complete" && (r.scores !== null || String(r.status).startsWith("not-") && r.observation_sha256 !== null)) throw new Error("Noncomplete reference cannot acquire a score");
      refs.add(r.id);
    }
  }
  if (search.readiness !== undefined) {
    if (!object(search.readiness)) throw new Error("Invalid source-specific readiness");
    for (const [name, total] of [["numeric", 2], ["editor", 28]] as const) {
      const r = search.readiness[name];
      if (r !== null && (!object(r) || !integer(r.accepted) || r.total !== total || Number(r.accepted) > total
        || typeof r.passed !== "boolean" || !hash(r.certificate_sha256)
        || r.passed && r.accepted !== total)) throw new Error("Readiness pass/count differs");
    }
  }
  const arms = ["throughput", "efficiency"].flatMap(o => ["parameters", "code-fixed-graph", "code-and-graph", "random"].map(m => `${o}:${m}`));
  for (const r of search.candidate_slots) {
    if (!object(r) || !loss(r.loss) || typeof r.arm !== "string" || !arms.includes(r.arm)
      || typeof r.generation !== "number" || ![0, 1].includes(r.generation)
      || !["complete", "failed", "invalid", "generation-failure", "unknown"].includes(String(r.status))) throw new Error("Invalid search slot");
    const key = `${r.arm}:${r.generation}`;
    if (slots.has(key) || (r.status === "complete" ? r.loss === null : r.loss !== null)) throw new Error("Duplicated or inconsistent search outcome");
    slots.add(key);
  }
  if (search.observed_stage !== undefined && search.observed_stage !== null
    && !["readiness", "search", "evaluation"].includes(String(search.observed_stage))) throw new Error("Invalid recorded stage");
  if (search.stage_error_type !== undefined && search.stage_error_type !== null && typeof search.stage_error_type !== "string") throw new Error("Invalid recorded stage error");
  if (["stage-started-no-terminal", "stage-stopped", "stage-closed"].includes(String(search.status))
    && !["readiness", "search", "evaluation"].includes(String(search.observed_stage))) throw new Error("Stage status lacks its recorded stage");
  if ((Number(search.evaluation_observations) > 0 || search.evaluation_plan_worlds !== null) && !search.selection_fixed) throw new Error("Evaluation precedes frozen selection");
  return p as unknown as PreScaleSnapshot;
}

export const valueLabel = (x: number | null | undefined): string => x == null ? "—" : x.toLocaleString("en-US", { maximumFractionDigits: 3 });
export const statusLabel = (status: string): string => ({
  "not-dispatched": "Not dispatched", "started-no-terminal-observation": "Started · completion unverified",
  complete: "Observation complete", failed: "Failed observation", invalid: "Invalid observation",
  submitted: "Literal submission", "generation-failure": "Generation failure",
  "prepared-no-stage-terminal": "Prepared · no stage started", "recorded-closed": "Scientific completion recorded",
  "stage-started-no-terminal": "Stage started · completion unverified", "stage-stopped": "Stage stopped", "stage-closed": "Stage completed",
}[status] ?? status);
