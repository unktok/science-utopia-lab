export type AdoptionState = "unavailable" | "confirm-required" | "pending" | "completed" | "failed";

export interface DesignPort { port_id: string; artifact_type: string; channel: string; required: boolean }
export interface DesignNode {
  id: string; family: string; implementation: string; phase: number | null; trigger: string | null;
  inputs: DesignPort[]; outputs: DesignPort[];
  code: null | { label: string; source: string; schema: string; input_schema: unknown; output_schema: unknown; state_schema: unknown };
}
export interface DesignConnection { source_mechanism: string; source_port: string; target_mechanism: string; target_port: string; channel: string; latency: number }
export interface DesignSystem {
  index: number; role: string; status: "baseline" | "selected" | "observed-not-selected"; selection_reason: string; loss: number;
  system_fingerprint: string; run_id: string; checkpoint_sha256: string; response_count: number; technical_failures: unknown[];
  metrics: Record<string, { status: string; value: number }>;
  nodes: DesignNode[]; connections: DesignConnection[]; generated_node_ids: string[];
  diff: { nodes_added: string[]; nodes_removed: string[]; nodes_changed: string[]; connections_added: DesignConnection[]; connections_removed: DesignConnection[]; protocol_types_added: string[]; protocol_types_removed: string[]; generated_code: Array<{ mechanism_id: string; label: string; source_sha256: string; artifact_sha256: string; executions: number }> };
}
export interface DesignArm {
  id: string; short: string; formula: string; accent: "cyan" | "violet"; direction: "minimize"; interpretation: string;
  loss_spec: unknown; loss_spec_sha256: string; loss_path: number[]; selected_index: number; selected_fingerprint: string; systems: DesignSystem[];
}
export interface DesignLifecycleSnapshot {
  schema: "scienceutopia.native-design-lifecycle-ui.v1";
  truth_status: "audited-development-result";
  source: { artifact: string; artifact_sha256: string; artifact_schema: string; source_commit: string; input_manifest_sha256: string };
  experiment: {
    classification: string; status: string;
    designer: { role: string; model: string; identity: string; transport: string; provider_authenticated: boolean; nonblinded_across_objectives: boolean };
    researchers: { role: string; model: string; population: number; seed: number; years: number; responses_per_world: number; total_responses: number };
    physical_complete_runs: number; logical_observations: number; shared_initial_physical_runs: number;
  };
  claims: { held_out: boolean; independent_replicates: boolean; scientific_value: boolean; full_world_differentiation: boolean; same_society_adoption_executed: boolean; automatic_recursive_designer: boolean; author_identity_authenticated: boolean; native_code_executed_in_experiment: boolean };
  arms: DesignArm[];
  adoption: { transport: "unavailable"; contract_schema: "scienceutopia.native-society-design-session.v1"; available_states: AdoptionState[]; completion_boundary: string };
  limits: string[];
}

const object = (value: unknown, label: string): Record<string, any> => {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object`);
  return value as Record<string, any>;
};

export function parseDesignLifecycle(value: unknown): DesignLifecycleSnapshot {
  const data = object(value, "Design lifecycle snapshot");
  if (data.schema !== "scienceutopia.native-design-lifecycle-ui.v1" || data.truth_status !== "audited-development-result") throw new Error("Unsupported design lifecycle truth contract");
  const claims = object(data.claims, "claims");
  for (const forbidden of ["held_out", "independent_replicates", "scientific_value", "full_world_differentiation", "same_society_adoption_executed", "automatic_recursive_designer", "author_identity_authenticated"]) {
    if (claims[forbidden] !== false) throw new Error(`Unsupported positive claim: ${forbidden}`);
  }
  if (claims.native_code_executed_in_experiment !== true) throw new Error("Audited native execution must remain explicit");
  if (!Array.isArray(data.arms) || data.arms.length !== 2) throw new Error("Expected exactly two audited loss arms");
  for (const armValue of data.arms) {
    const arm = object(armValue, "loss arm");
    if (!Array.isArray(arm.systems) || arm.systems.length !== 3 || !Array.isArray(arm.loss_path) || arm.loss_path.length !== 3) throw new Error("Each loss arm must retain all three observed systems");
    if (!Number.isInteger(arm.selected_index) || arm.selected_index < 0 || arm.selected_index >= arm.systems.length) throw new Error("Invalid selected index");
    if (arm.systems[arm.selected_index]?.system_fingerprint !== arm.selected_fingerprint || arm.systems[arm.selected_index]?.status !== "selected") throw new Error("Selected system binding mismatch");
    for (let index = 0; index < 3; index += 1) {
      const system = object(arm.systems[index], "observed system");
      if (system.index !== index || system.loss !== arm.loss_path[index]) throw new Error("Observed system/loss path mismatch");
      if (!Array.isArray(system.nodes) || !Array.isArray(system.connections) || !Array.isArray(system.technical_failures)) throw new Error("Incomplete observed system evidence");
      if (system.technical_failures.length) throw new Error("This snapshot only supports completed audited observations");
    }
    const tiedLater = arm.systems.find((system: any, index: number) => index > arm.selected_index && system.loss === arm.loss_path[arm.selected_index]);
    if (!tiedLater || tiedLater.status !== "observed-not-selected") throw new Error("First-best tie evidence was dropped");
  }
  const adoption = object(data.adoption, "adoption");
  if (adoption.transport !== "unavailable" || data.claims.same_society_adoption_executed !== false) throw new Error("Unconnected adoption transport must fail closed");
  return data as DesignLifecycleSnapshot;
}

export interface AdoptionCandidate {
  request_id: string; request_sha256: string;
  parent_observation_id: string; expected_checkpoint_sha256: string; candidate_fingerprint: string; candidate_system: unknown;
  loss_spec_sha256: string; state_actions: Record<string, unknown>; discard_deliveries: Record<string, string>; authoring: unknown;
}
export interface AdoptionReceipt {
  status: "pending" | "adopted" | "failed"; request_id: string; request_sha256: string;
  migration_receipt_sha256?: string; verified_receipt?: true; error?: string;
}
export interface AdoptionTransport {
  dispatch(candidate: AdoptionCandidate, confirmedRequestSha256: string): Promise<{ status: "pending"; request_id: string; request_sha256: string }>;
  receipt(requestId: string): Promise<AdoptionReceipt>;
}

const SHA256 = /^[0-9a-f]{64}$/;
function exactSha256(value: unknown, label: string): string {
  if (typeof value !== "string" || !SHA256.test(value)) throw new Error(`${label} must be a lowercase 64-hex SHA256`);
  return value;
}
function nonEmptyString(value: unknown, label: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${label} must be a non-empty string`);
  return value;
}
function record(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be a record`);
  return value as Record<string, unknown>;
}

export interface AdoptionConfirmation {
  request_id: string; confirmed_request_sha256: string; candidate_fingerprint: string; expected_checkpoint_sha256: string;
}

export function adoptionConfirmation(candidate: AdoptionCandidate): AdoptionConfirmation {
  const requestId = nonEmptyString(candidate.request_id, "request_id");
  const requestSha256 = exactSha256(candidate.request_sha256, "request_sha256");
  const candidateFingerprint = exactSha256(candidate.candidate_fingerprint, "candidate_fingerprint");
  const expectedCheckpointSha256 = exactSha256(candidate.expected_checkpoint_sha256, "expected_checkpoint_sha256");
  exactSha256(candidate.loss_spec_sha256, "loss_spec_sha256");
  nonEmptyString(candidate.parent_observation_id, "parent_observation_id");
  record(candidate.candidate_system, "candidate_system");
  record(candidate.state_actions, "state_actions");
  const discards = record(candidate.discard_deliveries, "discard_deliveries");
  if (Object.values(discards).some((reason) => typeof reason !== "string")) throw new Error("discard_deliveries values must be strings");
  record(candidate.authoring, "authoring");
  return { request_id: requestId, confirmed_request_sha256: requestSha256, candidate_fingerprint: candidateFingerprint, expected_checkpoint_sha256: expectedCheckpointSha256 };
}

export class AdoptionController {
  state: AdoptionState;
  requestId = "";
  requestSha256 = "";
  message = "Transport not connected. This historical v5 snapshot is not a live design session and cannot be adopted directly.";
  private operation = 0;
  private dispatching = false;
  private refreshing = false;
  constructor(private readonly transport?: AdoptionTransport) { this.state = transport ? "confirm-required" : "unavailable"; }
  async submit(candidate: AdoptionCandidate, confirmedRequestSha256: string): Promise<void> {
    if (!this.transport) { this.state = "unavailable"; throw new Error(this.message); }
    if (this.dispatching || this.refreshing || this.state === "pending" || this.state === "completed") throw new Error("An adoption request is already active or completed");
    const confirmation = adoptionConfirmation(candidate);
    if (confirmedRequestSha256 !== confirmation.confirmed_request_sha256) {
      this.state = "confirm-required";
      throw new Error("confirmed_request_sha256 must exactly match the staged request SHA256 shown to the user");
    }
    const operation = ++this.operation;
    this.requestId = confirmation.request_id;
    this.requestSha256 = confirmation.confirmed_request_sha256;
    this.dispatching = true;
    this.state = "pending"; this.message = `Dispatching exact request ${this.requestSha256.slice(0, 16)} / no adoption receipt yet.`;
    try {
      const pending = await this.transport.dispatch(candidate, confirmation.confirmed_request_sha256);
      if (operation !== this.operation) return;
      if (pending.status !== "pending" || pending.request_id !== this.requestId || pending.request_sha256 !== this.requestSha256) throw new Error("Pending adoption response does not match the exact confirmed request");
      this.message = `Pending durable migration receipt / ${this.requestSha256.slice(0, 16)}`;
    } catch (error) {
      if (operation === this.operation) { this.state = "failed"; this.message = String(error); }
      throw error;
    } finally { if (operation === this.operation) this.dispatching = false; }
  }
  async refresh(): Promise<void> {
    if (!this.transport || this.state !== "pending" || !this.requestId) throw new Error("No pending adoption request");
    if (this.dispatching) { this.message = `Dispatch acknowledgement pending / ${this.requestSha256.slice(0, 16)}`; return; }
    if (this.refreshing) return;
    const operation = this.operation, requestId = this.requestId, requestSha256 = this.requestSha256;
    this.refreshing = true;
    try {
      const receipt = await this.transport.receipt(requestId);
      if (operation !== this.operation || requestId !== this.requestId || requestSha256 !== this.requestSha256) return;
      if (receipt.request_id !== requestId || receipt.request_sha256 !== requestSha256) throw new Error("Adoption receipt identity does not match the pending request");
      if (receipt.status === "pending") { this.message = `Pending durable migration receipt / ${requestSha256.slice(0, 16)}`; return; }
      if (receipt.status === "failed") { this.state = "failed"; this.message = receipt.error || "Migration failed"; return; }
      if (receipt.status === "adopted" && receipt.verified_receipt === true) {
        const migrationHash = exactSha256(receipt.migration_receipt_sha256, "migration_receipt_sha256");
        this.state = "completed"; this.message = `Durable migration receipt verified / ${migrationHash.slice(0, 16)}`; return;
      }
      throw new Error("Completed adoption requires backend verified_receipt=true and a valid durable migration receipt SHA256");
    } catch (error) {
      if (operation === this.operation && requestId === this.requestId && requestSha256 === this.requestSha256) { this.state = "failed"; this.message = String(error); }
      throw error;
    } finally { if (operation === this.operation) this.refreshing = false; }
  }
}
