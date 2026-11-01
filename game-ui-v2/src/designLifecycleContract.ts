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
  parent_observation_id: string; expected_checkpoint_sha256: string; candidate_fingerprint: string; candidate_system: unknown;
  loss_spec_sha256: string; state_actions: unknown[]; discard_deliveries: unknown[]; authoring: unknown;
}
export interface AdoptionReceipt { status: "adopted" | "failed"; request_id: string; request_sha256: string; migration_receipt_sha256?: string; error?: string }
export interface AdoptionTransport { dispatch(candidate: AdoptionCandidate): Promise<{ status: "pending"; request_id: string; request_sha256: string }>; receipt(requestId: string): Promise<AdoptionReceipt> }

export class AdoptionController {
  state: AdoptionState;
  requestId = "";
  message = "Transport not connected. Viewing audited evidence cannot adopt a system.";
  constructor(private readonly transport?: AdoptionTransport) { this.state = transport ? "confirm-required" : "unavailable"; }
  async submit(candidate: AdoptionCandidate, explicitlyConfirmed: boolean): Promise<void> {
    if (!this.transport) { this.state = "unavailable"; throw new Error(this.message); }
    if (!explicitlyConfirmed) { this.state = "confirm-required"; throw new Error("Explicit confirmation of the exact staged request is required"); }
    this.state = "pending"; this.message = "Dispatching exact request; no adoption receipt yet.";
    try {
      const pending = await this.transport.dispatch(candidate);
      if (pending.status !== "pending" || !pending.request_id || !pending.request_sha256) throw new Error("Invalid pending adoption response");
      this.requestId = pending.request_id;
      this.message = `Pending durable migration receipt / ${pending.request_sha256.slice(0, 16)}`;
    } catch (error) { this.state = "failed"; this.message = String(error); throw error; }
  }
  async refresh(): Promise<void> {
    if (!this.transport || this.state !== "pending" || !this.requestId) throw new Error("No pending adoption request");
    try {
      const receipt = await this.transport.receipt(this.requestId);
      if (receipt.status === "adopted" && receipt.migration_receipt_sha256) { this.state = "completed"; this.message = `Durable migration receipt verified / ${receipt.migration_receipt_sha256.slice(0, 16)}`; return; }
      if (receipt.status === "failed") { this.state = "failed"; this.message = receipt.error || "Migration failed"; return; }
      throw new Error("Completed adoption requires a verified durable migration receipt");
    } catch (error) { this.state = "failed"; this.message = String(error); throw error; }
  }
}
