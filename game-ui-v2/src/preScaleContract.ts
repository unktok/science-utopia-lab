import { webCanonicalHash } from "./hash";

export interface MechanismRow {
  id: string; condition: string; seed: number; status: string;
  scores: Record<string, number | null> | null; observation_sha256: string | null;
}
export interface PreScaleSnapshot {
  schema: string; observed_utc: string; observation_kind: string; scope: string;
  scientist_model: string; designer_model: string;
  information: { source_commit: string; plan_sha256: string; closure_recorded: boolean;
    numeric_readiness: { objective: string; status: string; request_sha256: string; result_sha256: string;
      scientific_loss: null; retained_parent_explicitly: boolean | null }[];
    worlds: MechanismRow[] };
  search: { status: string; source_commit: string | null; selection_fixed: boolean;
    candidate_slots: { arm: string; generation: number; status: string; loss: number | null }[];
    evaluation_observations: number; evaluation_plan_worlds: number | null };
  boundaries: Record<string, boolean>;
}
const object = (x: unknown): x is Record<string, unknown> => !!x && typeof x === "object" && !Array.isArray(x);
const hash = (x: unknown, size = 64): x is string => typeof x === "string" && new RegExp(`^[0-9a-f]{${size}}$`).test(x);
const loss = (x: unknown) => x === null || (typeof x === "number" && Number.isFinite(x));
const integer = (x: unknown) => typeof x === "number" && Number.isSafeInteger(x) && x >= 0;
const scoresValid = (x: unknown): boolean => x === null || object(x) && ["throughput", "efficiency", "selective"].every(k => loss(x[k]));

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
  if (!["not-dispatched", "prepared-no-stage-terminal", "recorded-closed"].includes(String(search.status))
      || (search.source_commit !== null && !hash(search.source_commit, 40)) || typeof search.selection_fixed !== "boolean"
      || !Array.isArray(search.candidate_slots) || search.candidate_slots.length > 16
      || !integer(search.evaluation_observations) || Number(search.evaluation_observations) > 36
      || (search.evaluation_plan_worlds !== null && (!integer(search.evaluation_plan_worlds) || Number(search.evaluation_plan_worlds) > 36))) throw new Error("Invalid search/evaluation scope");
  for (const r of search.candidate_slots) if (!object(r) || !loss(r.loss) || typeof r.arm !== "string"
    || typeof r.generation !== "number" || ![0, 1].includes(r.generation) || typeof r.status !== "string") throw new Error("Invalid search slot");
  if ((Number(search.evaluation_observations) > 0 || search.evaluation_plan_worlds !== null) && !search.selection_fixed) throw new Error("Evaluation precedes frozen selection");
  return p as unknown as PreScaleSnapshot;
}

export const valueLabel = (x: number | null | undefined): string => x == null ? "—" : x.toLocaleString("en-US", { maximumFractionDigits: 3 });
export const statusLabel = (status: string): string => ({
  "not-dispatched": "Not dispatched", "started-no-terminal-observation": "Started · completion unverified",
  complete: "Observation complete", failed: "Technical failure", invalid: "Invalid observation",
  submitted: "Literal submission", "generation-failure": "Generation failure",
}[status] ?? status);
