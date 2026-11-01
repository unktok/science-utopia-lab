import { stableStringify } from "./hash";

export type MissionDirection = "minimize" | "maximize";
export type MissionContract = {
  contract_id: string;
  loss_spec_json: string;
  loss_id: string;
  direction: MissionDirection;
  target_loss: number;
  trial_limit: number;
};
export type MissionJobLink = {
  job_id: string;
  contract_id: string;
  request_sha256: string;
};
export type MissionObservation = {
  job_id: string;
  request_sha256: string;
  status: "complete" | "failed";
  native_loss: number | null;
  seed: number;
  years: number;
  source_commit: string;
  evidence_loaded: boolean;
};
export type MissionRecord = { contract: MissionContract; observations: MissionObservation[] };
export type MissionBook = {
  schema: "scienceutopia.native-sandbox-missions.v1";
  generation: number;
  active_contract_id: string | null;
  contracts: MissionRecord[];
  jobs: MissionJobLink[];
};
export type MissionDraft = { loss_spec: unknown; target_loss: number; trial_limit: number };
export type MissionProgress = {
  attempted: number;
  remaining: number;
  observed: number;
  complete_scores: number[];
  best_loss: number | null;
  target_achieved: boolean;
};

const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;
const object = (value: unknown): value is Record<string, unknown> => Boolean(value) && typeof value === "object" && !Array.isArray(value);
const compactFingerprint = (value: string): string => {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index++) { hash ^= value.charCodeAt(index); hash = Math.imul(hash, 16777619); }
  return (hash >>> 0).toString(16).padStart(8, "0");
};

export const emptyMissionBook = (): MissionBook => ({ schema: "scienceutopia.native-sandbox-missions.v1", generation: 0, active_contract_id: null, contracts: [], jobs: [] });

const contractFields = (draft: MissionDraft): Omit<MissionContract, "contract_id"> => {
  if (!object(draft.loss_spec)) throw new Error("LossSpec must be a JSON object");
  const direction = draft.loss_spec.direction;
  if (direction !== "minimize" && direction !== "maximize") throw new Error("LossSpec direction must be minimize or maximize");
  if (typeof draft.loss_spec.id !== "string" || !draft.loss_spec.id.trim()) throw new Error("LossSpec requires a nonempty id");
  if (!Number.isFinite(draft.target_loss)) throw new Error("Target loss must be finite");
  if (!Number.isInteger(draft.trial_limit) || draft.trial_limit < 1 || draft.trial_limit > 99) throw new Error("Trial limit must be an integer from 1 to 99");
  return { loss_spec_json: stableStringify(draft.loss_spec), loss_id: draft.loss_spec.id, direction, target_loss: draft.target_loss, trial_limit: draft.trial_limit };
};

export function activateMissionContract(book: MissionBook, draft: MissionDraft): MissionBook {
  const fields = contractFields(draft), active = book.contracts.find(row => row.contract.contract_id === book.active_contract_id)?.contract;
  if (active && active.loss_spec_json === fields.loss_spec_json && active.loss_id === fields.loss_id && active.direction === fields.direction && active.target_loss === fields.target_loss && active.trial_limit === fields.trial_limit) return clone(book);
  const next = clone(book), generation = next.generation + 1;
  const identity = stableStringify(fields);
  const contract: MissionContract = { contract_id: `mission-${generation}-${compactFingerprint(identity)}`, ...fields };
  next.generation = generation; next.active_contract_id = contract.contract_id;
  next.contracts.push({ contract, observations: [] });
  return next;
}

export function activeMission(book: MissionBook): MissionRecord | null {
  return book.contracts.find(row => row.contract.contract_id === book.active_contract_id) || null;
}

export function missionMatchesDraft(book: MissionBook, draft: MissionDraft): boolean {
  const active = activeMission(book); if (!active) return false;
  try {
    const fields = contractFields(draft);
    return active.contract.loss_spec_json === fields.loss_spec_json && active.contract.target_loss === fields.target_loss && active.contract.trial_limit === fields.trial_limit;
  } catch { return false; }
}

export function linkMissionJob(book: MissionBook, job: MissionJobLink): MissionBook {
  if (!job.job_id || !job.request_sha256) throw new Error("Durable job identity and request hash are required");
  const existing = book.jobs.find(row => row.job_id === job.job_id);
  if (existing) {
    if (stableStringify(existing) !== stableStringify(job)) throw new Error("Durable job is already bound to a different design contract");
    return clone(book);
  }
  const record = book.contracts.find(row => row.contract.contract_id === job.contract_id);
  if (!record) throw new Error("Mission contract does not exist");
  if (book.jobs.filter(row => row.contract_id === job.contract_id).length >= record.contract.trial_limit) throw new Error("Mission trial limit reached");
  const next = clone(book); next.jobs.push(clone(job)); return next;
}

export function observeMissionJob(book: MissionBook, observation: MissionObservation): MissionBook {
  const link = book.jobs.find(row => row.job_id === observation.job_id);
  if (!link || link.request_sha256 !== observation.request_sha256) throw new Error("Observed job does not match a submitted mission trial");
  if (observation.status === "complete" && (!observation.evidence_loaded || typeof observation.native_loss !== "number" || !Number.isFinite(observation.native_loss))) throw new Error("Completed score requires loaded evidence and a finite actual loss");
  if (observation.status === "failed" && observation.native_loss !== null) throw new Error("Failed jobs cannot carry a numeric score");
  const record = book.contracts.find(row => row.contract.contract_id === link.contract_id);
  if (!record) throw new Error("Linked mission contract is missing");
  const previous = record.observations.find(row => row.job_id === observation.job_id);
  if (previous) {
    if (stableStringify(previous) !== stableStringify(observation)) throw new Error("Mission job already has a different terminal observation");
    return clone(book);
  }
  const next = clone(book), target = next.contracts.find(row => row.contract.contract_id === link.contract_id)!;
  target.observations.push(clone(observation)); return next;
}

export function missionProgress(book: MissionBook, contractId: string): MissionProgress {
  const record = book.contracts.find(row => row.contract.contract_id === contractId);
  if (!record) throw new Error("Mission contract does not exist");
  const attempted = book.jobs.filter(row => row.contract_id === contractId).length;
  const completeScores = record.observations.filter(row => row.status === "complete" && row.evidence_loaded).map(row => row.native_loss as number);
  const best = completeScores.length ? (record.contract.direction === "minimize" ? Math.min(...completeScores) : Math.max(...completeScores)) : null;
  const achieved = best !== null && (record.contract.direction === "minimize" ? best <= record.contract.target_loss : best >= record.contract.target_loss);
  return { attempted, remaining: Math.max(0, record.contract.trial_limit - attempted), observed: record.observations.length, complete_scores: completeScores, best_loss: best, target_achieved: achieved };
}

export function parseMissionBook(value: unknown): MissionBook {
  if (!object(value) || value.schema !== "scienceutopia.native-sandbox-missions.v1" || !Number.isInteger(value.generation) || Number(value.generation) < 0 || !Array.isArray(value.contracts) || !Array.isArray(value.jobs)) throw new Error("Mission storage schema differs");
  const book = clone(value) as MissionBook;
  if (book.active_contract_id !== null && typeof book.active_contract_id !== "string") throw new Error("Mission active contract is invalid");
  for (const row of book.contracts) {
    if (!object(row) || !object(row.contract) || !Array.isArray(row.observations)) throw new Error("Mission record is invalid");
    const fields = contractFields({ loss_spec: JSON.parse(row.contract.loss_spec_json), target_loss: row.contract.target_loss, trial_limit: row.contract.trial_limit });
    if (typeof row.contract.contract_id !== "string" || typeof row.contract.loss_id !== "string") throw new Error("Mission contract identity is invalid");
    if (row.contract.loss_id !== fields.loss_id || row.contract.direction !== fields.direction || row.contract.loss_spec_json !== fields.loss_spec_json) throw new Error("Mission contract differs from its LossSpec");
  }
  if (new Set(book.contracts.map(row => row.contract.contract_id)).size !== book.contracts.length || new Set(book.jobs.map(row => row.job_id)).size !== book.jobs.length) throw new Error("Mission storage contains duplicate identities");
  for (const job of book.jobs) if (!object(job) || !book.contracts.some(row => row.contract.contract_id === job.contract_id) || typeof job.job_id !== "string" || !job.job_id || typeof job.request_sha256 !== "string" || !job.request_sha256) throw new Error("Mission job link is invalid");
  for (const record of book.contracts) {
    if (book.jobs.filter(row => row.contract_id === record.contract.contract_id).length > record.contract.trial_limit) throw new Error("Mission storage exceeds its trial limit");
    if (record.observations.some(row => !object(row))) throw new Error("Mission observation provenance is invalid");
    if (new Set(record.observations.map(row => row.job_id)).size !== record.observations.length) throw new Error("Mission observations contain duplicate jobs");
    for (const observation of record.observations) {
      if (!object(observation) || typeof observation.job_id !== "string" || typeof observation.request_sha256 !== "string" || !Number.isInteger(observation.seed) || !Number.isInteger(observation.years) || typeof observation.source_commit !== "string") throw new Error("Mission observation provenance is invalid");
      const link = book.jobs.find(row => row.job_id === observation.job_id && row.contract_id === record.contract.contract_id);
      if (!link || link.request_sha256 !== observation.request_sha256) throw new Error("Mission observation is not linked to its contract");
      if (observation.status === "complete" && (!observation.evidence_loaded || typeof observation.native_loss !== "number" || !Number.isFinite(observation.native_loss))) throw new Error("Mission completed observation is not evidence-backed");
      if (observation.status === "failed" && (observation.native_loss !== null || observation.evidence_loaded)) throw new Error("Mission failure cannot contain evidence score");
      if (observation.status !== "complete" && observation.status !== "failed") throw new Error("Mission observation status is invalid");
    }
  }
  if (book.active_contract_id && !book.contracts.some(row => row.contract.contract_id === book.active_contract_id)) throw new Error("Active mission contract is missing");
  return book;
}
