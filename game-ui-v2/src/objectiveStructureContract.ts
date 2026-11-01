import { canonicalHash } from "./hash";

export const OBJECTIVE_IDS = [
  "native-joint-v5-throughput",
  "native-joint-v5-net-reviewed-utility",
] as const;

export type ObjectiveId = typeof OBJECTIVE_IDS[number];
export type EvidenceMode = "actual" | "fixture";
export type Row = Record<string, any>;

export interface StructuralRow {
  arm: ObjectiveId;
  generation: number;
  draw_index?: number;
  strategy: string;
  status: "complete" | "technical-failure" | "generation-failure";
  draw: Row | null;
  observation: Row | null;
  cross_objective_losses: Record<ObjectiveId, number | null>;
  loss_evaluations: Record<ObjectiveId, Row> | null;
  graph_changes: { vs_initial: GraphChange; vs_parent: GraphChange } | null;
  independent_metrics: Row | null;
  physical_proof: Row | null;
}

export interface GraphChange {
  from_fingerprint: string;
  to_fingerprint: string;
  nodes_added: string[];
  nodes_removed: string[];
  edges_added: unknown[][];
  edges_removed: unknown[][];
  source_changes: Row[];
  source_bodies_added: string[];
  source_bodies_removed: string[];
  same_source_body_renamed_ids: Row[];
  protocol_changes: Row[];
  mechanism_configuration_changes: string[];
  schedules_added: Row[];
  schedules_removed: Row[];
  initial_state_change: Row;
  counts: Record<string, number>;
}

export interface ObjectiveArm {
  loss_spec: Row;
  binding: Row;
  rows: StructuralRow[];
  generation_failures: StructuralRow[];
  loss_path: Array<number | null>;
  selection: {
    criterion: string;
    best_loss: number | null;
    tie_count: number;
    tied_system_fingerprints: string[];
    tied_observation_ids: string[];
    tied_suggestion_ids: string[];
    representative_system_fingerprint: string | null;
    representative_observation_id: string | null;
    representative_suggestion_id: string | null;
  };
}

export interface ObjectiveStructureReport {
  schema: "scienceutopia.native-objective-structure-audit.v8";
  classification: "actual-native-qwen-objective-structure-development-v8" | "scripted-fixture-not-native-results";
  status: "in-progress" | "complete" | "budget-complete-with-failures";
  source_commit: string;
  raw_inventory_sha256: string;
  raw_file_count: number;
  completed_physical_worlds: number;
  physical_cache_count: number;
  raw_campaign_summary: Row;
  arms: Record<ObjectiveId, ObjectiveArm>;
  selected_cross_objective_matrix: Record<ObjectiveId, Record<ObjectiveId, number | null> | null>;
  held_out_metrics: { status: "not-defined-or-measured" };
  promotion_policy: { status: "not-defined-or-applied" };
  claims: string[];
  content_sha256: string;
}

export interface ObjectiveStructureReceipt {
  schema: "scienceutopia.native-objective-structure-ui-export.v8";
  report_file: string;
  report_file_sha256: string;
  report_content_sha256: string;
  classification: ObjectiveStructureReport["classification"];
  exported_without_transform: true;
}

const SHA256 = /^[0-9a-f]{64}$/;
const SHA1 = /^[0-9a-f]{40}$/;
const actualClass = "actual-native-qwen-objective-structure-development-v8";
const fixtureClass = "scripted-fixture-not-native-results";

function object(value: unknown, label: string): Row {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object`);
  return value as Row;
}
function array(value: unknown, label: string): any[] {
  if (!Array.isArray(value)) throw new Error(`${label} must be an array`);
  return value;
}
function sha256(value: unknown, label: string): string {
  if (typeof value !== "string" || !SHA256.test(value)) throw new Error(`${label} must be lowercase SHA256`);
  return value;
}
function finite(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`${label} must be finite`);
  return value;
}
function nonemptyString(value: unknown, label: string): string {
  if (typeof value !== "string" || !value) throw new Error(`${label} must be a non-empty string`);
  return value;
}
function nullableFinite(value: unknown, label: string): number | null {
  return value === null ? null : finite(value, label);
}
function candidate(row: Row): Row | null {
  if (!row.draw) return null;
  const suggestion = object(object(row.draw, "draw").suggestion, "suggestion");
  return object(suggestion.candidate, "candidate system");
}
function validateSystem(systemValue: unknown, label: string): Row {
  const system = object(systemValue, label);
  const nodes = array(system.mechanisms, `${label}.mechanisms`);
  const ids = new Set<string>();
  for (const [index, value] of nodes.entries()) {
    const node = object(value, `${label} node ${index}`);
    if (typeof node.mechanism_id !== "string" || !node.mechanism_id || ids.has(node.mechanism_id)) throw new Error(`${label} has invalid node identity`);
    ids.add(node.mechanism_id);
    if (typeof node.family !== "string" || typeof node.implementation !== "string") throw new Error(`${label} node metadata is incomplete`);
    array(node.inputs, `${label} node inputs`); array(node.outputs, `${label} node outputs`); object(node.parameters, `${label} node parameters`);
  }
  for (const [index, value] of array(system.connections, `${label}.connections`).entries()) {
    const edge = object(value, `${label} edge ${index}`);
    if (!ids.has(edge.source_mechanism) || !ids.has(edge.target_mechanism)) throw new Error(`${label} edge has a missing endpoint`);
    for (const key of ["source_port", "target_port", "channel"]) if (typeof edge[key] !== "string") throw new Error(`${label} edge is incomplete`);
  }
  array(system.schedules, `${label}.schedules`);
  return system;
}
function validateGraphChange(value: unknown, expectedFingerprint: string, label: string): GraphChange {
  const change = object(value, label);
  sha256(change.from_fingerprint, `${label}.from_fingerprint`);
  if (sha256(change.to_fingerprint, `${label}.to_fingerprint`) !== expectedFingerprint) throw new Error(`${label} candidate fingerprint differs`);
  for (const key of ["nodes_added", "nodes_removed", "edges_added", "edges_removed", "source_changes", "protocol_changes", "mechanism_configuration_changes", "schedules_added", "schedules_removed"]) array(change[key], `${label}.${key}`);
  object(change.initial_state_change, `${label}.initial_state_change`);
  const counts = object(change.counts, `${label}.counts`);
  const exact: Record<string, number> = {
    nodes_added: change.nodes_added.length,
    nodes_removed: change.nodes_removed.length,
    edges_added: change.edges_added.length,
    edges_removed: change.edges_removed.length,
    source_changes: change.source_changes.length,
    protocol_changes: change.protocol_changes.length,
    mechanism_configuration_changes: change.mechanism_configuration_changes.length,
    schedules_added: change.schedules_added.length,
    schedules_removed: change.schedules_removed.length,
  };
  for (const [key, count] of Object.entries(exact)) if (counts[key] !== count) throw new Error(`${label} ${key} count differs from exact diff`);
  return change as GraphChange;
}
function auditedFingerprint(row: Row, label: string): string {
  const proof = object(row.physical_proof, `${label} physical proof`);
  const proofFingerprint = sha256(object(proof.measurement, `${label} proof measurement`).system_fingerprint, `${label} proof fingerprint`);
  const observationFingerprint = sha256(object(object(row.observation, `${label} observation`).metadata, `${label} observation metadata`).system_fingerprint, `${label} observation fingerprint`);
  const changes = object(row.graph_changes, `${label} graph changes`);
  const initialFingerprint = sha256(object(changes.vs_initial, `${label} vs initial`).to_fingerprint, `${label} vs-initial fingerprint`);
  const parentFingerprint = sha256(object(changes.vs_parent, `${label} vs parent`).to_fingerprint, `${label} vs-parent fingerprint`);
  if (new Set([proofFingerprint, observationFingerprint, initialFingerprint, parentFingerprint]).size !== 1) throw new Error(`${label} audited fingerprint bindings differ`);
  return proofFingerprint;
}

interface CompleteRowAudit {
  row: StructuralRow;
  fingerprint: string;
  observationId: string;
  suggestionId: string;
  ownLoss: number;
}

function completeRowAudit(row: Row, fingerprint: string, ownLoss: number, label: string): CompleteRowAudit {
  const suggestion = object(object(row.draw, `${label} draw`).suggestion, `${label} suggestion`);
  const observation = object(row.observation, `${label} observation`);
  const suggestionId = nonemptyString(suggestion.suggestion_id, `${label} suggestion_id`);
  const observationId = nonemptyString(observation.observation_id, `${label} observation_id`);
  if (observation.suggestion_id !== suggestionId) throw new Error(`${label} observation/suggestion identity differs`);
  return { row: row as StructuralRow, fingerprint, observationId, suggestionId, ownLoss };
}

function rowExactIdentity(row: StructuralRow): { observationId: string; suggestionId: string } | null {
  if (row.status !== "complete") return null;
  const observationId = row.observation?.observation_id;
  const suggestionId = row.draw?.suggestion?.suggestion_id;
  if (typeof observationId !== "string" || typeof suggestionId !== "string") return null;
  return { observationId, suggestionId };
}

export function representativeRow(arm: ObjectiveArm): StructuralRow | null {
  const observationId = arm.selection.representative_observation_id;
  const suggestionId = arm.selection.representative_suggestion_id;
  if (observationId === null || suggestionId === null) return null;
  return arm.rows.find((row) => {
    const identity = rowExactIdentity(row);
    return identity?.observationId === observationId && identity.suggestionId === suggestionId;
  }) ?? null;
}

export function structuralRowState(row: StructuralRow, arm: ObjectiveArm): "selected" | "tie" | "complete" | "failed" {
  const identity = rowExactIdentity(row);
  if (!identity) return row.status === "complete" ? "complete" : "failed";
  if (identity.observationId === arm.selection.representative_observation_id
      && identity.suggestionId === arm.selection.representative_suggestion_id) return "selected";
  const tied = arm.selection.tied_observation_ids.some((observationId, index) => observationId === identity.observationId
    && arm.selection.tied_suggestion_ids[index] === identity.suggestionId);
  return tied ? "tie" : "complete";
}
function evaluationReason(value: unknown, label: string): void {
  const evaluation = object(value, label);
  if (evaluation.status === "complete") finite(evaluation.loss, `${label}.loss`);
  else {
    if (evaluation.loss !== null) throw new Error(`${label} unavailable loss must be null`);
    const rejected = array(evaluation.rejected_runs, `${label}.rejected_runs`);
    if (!rejected.length || rejected.some((item) => typeof object(item, `${label} rejection`).reason !== "string")) throw new Error(`${label} unavailable loss must retain reasons`);
  }
}

export function parseObjectiveStructureReport(value: unknown, mode: EvidenceMode = "actual"): ObjectiveStructureReport {
  const data = object(value, "objective structure report");
  if (data.schema !== "scienceutopia.native-objective-structure-audit.v8") throw new Error("Unsupported objective-structure schema");
  const expectedClass = mode === "actual" ? actualClass : fixtureClass;
  if (data.classification !== expectedClass) throw new Error(`${mode} channel rejects classification ${String(data.classification)}`);
  if (!['in-progress', 'complete', 'budget-complete-with-failures'].includes(data.status)) throw new Error("Invalid campaign status");
  if (typeof data.source_commit !== "string" || !SHA1.test(data.source_commit)) throw new Error("Invalid source commit");
  sha256(data.raw_inventory_sha256, "raw inventory hash"); sha256(data.content_sha256, "report content hash");
  if (!Number.isInteger(data.raw_file_count) || data.raw_file_count < 0 || !Number.isInteger(data.completed_physical_worlds) || data.completed_physical_worlds < 0 || data.completed_physical_worlds > 8) throw new Error("Invalid audited execution counts");
  if (!Number.isInteger(data.physical_cache_count) || data.physical_cache_count < 0) throw new Error("Invalid physical cache count");
  const summary = object(data.raw_campaign_summary, "campaign summary");
  if (summary.configured_researcher_provider !== "qwen3:8b" || summary.complete_native_worlds !== data.completed_physical_worlds || summary.planned_native_world_budget !== 8) throw new Error("Campaign summary binding differs");
  if (data.status === "complete" && (data.completed_physical_worlds !== 8 || summary.technical_failures !== 0 || summary.budget_terminal !== true)) throw new Error("Complete status requires eight clean worlds");
  if (object(data.held_out_metrics, "held-out metrics").status !== "not-defined-or-measured" || object(data.promotion_policy, "promotion policy").status !== "not-defined-or-applied") throw new Error("Development evidence was relabelled as held-out or promoted");
  const arms = object(data.arms, "arms");
  if (Object.keys(arms).sort().join() !== [...OBJECTIVE_IDS].sort().join()) throw new Error("Expected exactly two frozen objective arms");
  const matrix = object(data.selected_cross_objective_matrix, "selected matrix");
  for (const armId of OBJECTIVE_IDS) {
    const arm = object(arms[armId], `arm ${armId}`);
    const lossSpec = object(arm.loss_spec, `${armId} LossSpec`);
    if (lossSpec.id !== armId) throw new Error(`${armId} LossSpec identity differs`);
    const initial = validateSystem(object(arm.binding, `${armId} binding`).initial_system, `${armId} initial system`);
    void initial;
    const rows = array(arm.rows, `${armId} rows`);
    const path = array(arm.loss_path, `${armId} loss path`);
    if (rows.length !== path.length) throw new Error(`${armId} loss path length differs`);
    const completeRows: CompleteRowAudit[] = [];
    for (let index = 0; index < rows.length; index += 1) {
      const row = object(rows[index], `${armId} row ${index}`);
      if (row.arm !== armId || !Number.isInteger(row.generation) || !["complete", "technical-failure", "generation-failure"].includes(row.status)) throw new Error(`${armId} invalid row identity`);
      const losses = object(row.cross_objective_losses, `${armId} cross losses`);
      if (Object.keys(losses).sort().join() !== [...OBJECTIVE_IDS].sort().join()) throw new Error(`${armId} cross-loss keys differ`);
      for (const objective of OBJECTIVE_IDS) nullableFinite(losses[objective], `${armId}/${objective} loss`);
      if (path[index] !== losses[armId]) throw new Error(`${armId} path differs from own objective`);
      if (row.status === "complete") {
        validateSystem(candidate(row), `${armId} candidate ${index}`);
        const candidateFingerprint = auditedFingerprint(row, `${armId} row ${index}`);
        const changes = object(row.graph_changes, `${armId} graph changes ${index}`);
        validateGraphChange(changes.vs_initial, candidateFingerprint, `${armId} vs initial ${index}`);
        validateGraphChange(changes.vs_parent, candidateFingerprint, `${armId} vs parent ${index}`);
        finite(losses[armId], `${armId} own loss`);
        if (object(row.observation, `${armId} observation`).status !== "complete" || row.observation.loss !== losses[armId]) throw new Error(`${armId} observation loss differs`);
        const evaluations = object(row.loss_evaluations, `${armId} loss evaluations`);
        for (const objective of OBJECTIVE_IDS) {
          evaluationReason(evaluations[objective], `${armId}/${objective} evaluation`);
          const expected = evaluations[objective].status === "complete" ? evaluations[objective].loss : null;
          if (losses[objective] !== expected) throw new Error(`${armId}/${objective} cross loss differs from evaluation`);
        }
        completeRows.push(completeRowAudit(row, candidateFingerprint, losses[armId] as number, `${armId} row ${index}`));
      } else {
        if (losses[armId] !== null || row.observation?.loss != null || row.physical_proof !== null || row.graph_changes !== null && row.status === "generation-failure") throw new Error(`${armId} failure fabricated numerical/physical evidence`);
        if (row.status === "generation-failure" && row.draw !== null) throw new Error(`${armId} generation failure fabricated a draw`);
      }
    }
    if (new Set(completeRows.map((row) => row.observationId)).size !== completeRows.length
        || new Set(completeRows.map((row) => row.suggestionId)).size !== completeRows.length) {
      throw new Error(`${armId} complete rows reuse observation or suggestion identity`);
    }
    const failures = array(arm.generation_failures, `${armId} generation failures`);
    if (failures.some((failure) => object(failure, "generation failure").status !== "generation-failure")) throw new Error(`${armId} generation failure list is invalid`);
    const selection = object(arm.selection, `${armId} selection`);
    nonemptyString(selection.criterion, `${armId} selection criterion`);
    const best = nullableFinite(selection.best_loss, `${armId} best loss`);
    const finiteOwn = rows.map((row) => object(row, "row").cross_objective_losses[armId]).filter((score) => typeof score === "number") as number[];
    const expectedBest = finiteOwn.length ? Math.min(...finiteOwn) : null;
    if (best !== expectedBest) throw new Error(`${armId} best loss differs from path`);
    const tiedFingerprints = array(selection.tied_system_fingerprints, `${armId} tied fingerprints`).map((fp, index) => sha256(fp, `${armId} tied fingerprint ${index}`));
    const tiedObservationIds = array(selection.tied_observation_ids, `${armId} tied observation ids`).map((id, index) => nonemptyString(id, `${armId} tied observation id ${index}`));
    const tiedSuggestionIds = array(selection.tied_suggestion_ids, `${armId} tied suggestion ids`).map((id, index) => nonemptyString(id, `${armId} tied suggestion id ${index}`));
    const expectedTies = best === null ? [] : completeRows.filter((row) => row.ownLoss === best);
    const expectedFingerprints = expectedTies.map((row) => row.fingerprint);
    const expectedObservationIds = expectedTies.map((row) => row.observationId);
    const expectedSuggestionIds = expectedTies.map((row) => row.suggestionId);
    const same = (actual: string[], expected: string[]): boolean => actual.length === expected.length && actual.every((value, index) => value === expected[index]);
    if (!Number.isInteger(selection.tie_count) || selection.tie_count !== expectedTies.length
        || !same(tiedFingerprints, expectedFingerprints)
        || !same(tiedObservationIds, expectedObservationIds)
        || !same(tiedSuggestionIds, expectedSuggestionIds)) {
      throw new Error(`${armId} exact tied row identities differ from minimum-loss campaign rows`);
    }
    const representativeFingerprint = selection.representative_system_fingerprint === null ? null : sha256(selection.representative_system_fingerprint, `${armId} representative fingerprint`);
    const representativeObservationId = selection.representative_observation_id === null ? null : nonemptyString(selection.representative_observation_id, `${armId} representative observation id`);
    const representativeSuggestionId = selection.representative_suggestion_id === null ? null : nonemptyString(selection.representative_suggestion_id, `${armId} representative suggestion id`);
    const expectedRepresentative = expectedTies[0] ?? null;
    if (representativeFingerprint !== (expectedRepresentative?.fingerprint ?? null)
        || representativeObservationId !== (expectedRepresentative?.observationId ?? null)
        || representativeSuggestionId !== (expectedRepresentative?.suggestionId ?? null)) {
      throw new Error(`${armId} representative is not the earliest exact tied row`);
    }
    const matrixRow = matrix[armId];
    if (representativeObservationId === null) {
      if (matrixRow !== null) throw new Error(`${armId} matrix must be null without a representative`);
    } else {
      const matrixValues = object(matrixRow, `${armId} selected matrix row`);
      if (!expectedRepresentative) throw new Error(`${armId} representative row missing`);
      for (const objective of OBJECTIVE_IDS) if (matrixValues[objective] !== expectedRepresentative.row.cross_objective_losses[objective]) throw new Error(`${armId}/${objective} selected matrix differs`);
    }
  }
  if (!Array.isArray(data.claims) || !data.claims.some((claim: unknown) => typeof claim === "string" && claim.includes("no held-out"))) throw new Error("Truth-boundary claims are absent");
  return data as ObjectiveStructureReport;
}

export function parseObjectiveStructureReceipt(value: unknown, report: ObjectiveStructureReport, fileName: string): ObjectiveStructureReceipt {
  const receipt = object(value, "UI export receipt");
  if (receipt.schema !== "scienceutopia.native-objective-structure-ui-export.v8" || receipt.exported_without_transform !== true) throw new Error("Unsupported UI export receipt");
  if (receipt.report_file !== fileName || receipt.classification !== report.classification || receipt.report_content_sha256 !== report.content_sha256) throw new Error("UI export receipt does not bind this report");
  sha256(receipt.report_file_sha256, "UI report file hash");
  return receipt as ObjectiveStructureReceipt;
}

export async function verifyFixtureReport(value: unknown): Promise<ObjectiveStructureReport> {
  const report = parseObjectiveStructureReport(value, "fixture");
  const payload = { ...report } as Row; delete payload.content_sha256;
  if (await canonicalHash(payload) !== report.content_sha256) throw new Error("Fixture content hash mismatch");
  return report;
}

export async function sha256Text(text: string): Promise<string> {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}
