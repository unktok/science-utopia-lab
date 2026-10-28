import { canonicalHash, stableStringify } from "./hash";

export const CHANNELS = ["artifact", "score", "decision", "feedback", "resource", "signal", "constraint"] as const;
export type Channel = (typeof CHANNELS)[number];

export interface PortSpec {
  port_id: string;
  channel: Channel;
  artifact_type: string | null;
  required: boolean;
}

export interface MechanismSpec {
  mechanism_id: string;
  family: string;
  implementation: string;
  version: number;
  inputs: PortSpec[];
  outputs: PortSpec[];
  parameters: Record<string, unknown>;
}

export interface ConnectionSpec {
  source_mechanism: string;
  source_port: string;
  target_mechanism: string;
  target_port: string;
  channel: Channel;
  latency: number;
}

export interface SystemSpec {
  system_id: string;
  version: number;
  agent_types: unknown[];
  artifact_types: Array<{ artifact_type_id: string; description: string }>;
  mechanisms: MechanismSpec[];
  connections: ConnectionSpec[];
  schedules: Array<{ mechanism_id: string; phase: number; trigger: string }>;
  initial_state: Record<string, unknown>;
  global_invariants: string[];
  metadata: Record<string, unknown>;
}

export interface ValidationIssue {
  code: string;
  path: string;
  message: string;
  severity: "error" | "warning";
}

export interface ValidationReport {
  valid: boolean;
  issues: ValidationIssue[];
}

export interface SandboxNode {
  mechanism_id: string;
  label: string;
  asset_key: string;
  description: string;
  x: number;
  y: number;
  implementations: Array<{ id: string; label: string }>;
}

export interface SandboxEdge {
  edge_id: string;
  label: string;
  connection: ConnectionSpec;
  allowed_latencies: number[];
}

export interface SandboxBundle {
  schema_version: "scienceutopia.system-sandbox.v1";
  truth_status: "synthetic";
  source_kind: "synthetic_system_design_sandbox";
  disclosure: string;
  system_spec_contract: string;
  validator_contract: string;
  bundle_hash: string;
  base_spec: SystemSpec;
  node_catalog: SandboxNode[];
  edge_catalog: SandboxEdge[];
  authoritative_fixtures: Array<{
    id: string;
    spec: SystemSpec;
    fingerprint: string;
    validation: ValidationReport;
  }>;
}

export interface SandboxState {
  nodes: Record<string, { enabled: boolean; implementation: string }>;
  edges: Record<string, { enabled: boolean; latency: number }>;
}

const record = (value: unknown, path: string): Record<string, unknown> => {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${path} must be an object`);
  return value as Record<string, unknown>;
};
const array = (value: unknown, path: string): unknown[] => {
  if (!Array.isArray(value)) throw new Error(`${path} must be an array`);
  return value;
};
const string = (value: unknown, path: string): string => {
  if (typeof value !== "string" || value.length === 0) throw new Error(`${path} must be a non-empty string`);
  return value;
};
const number = (value: unknown, path: string): number => {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`${path} must be a finite number`);
  return value;
};

const parsePort = (value: unknown, path: string): PortSpec => {
  const row = record(value, path);
  const channel = string(row.channel, `${path}.channel`);
  if (!CHANNELS.includes(channel as Channel)) throw new Error(`${path}.channel is unknown`);
  return {
    port_id: string(row.port_id, `${path}.port_id`),
    channel: channel as Channel,
    artifact_type: row.artifact_type === null ? null : string(row.artifact_type, `${path}.artifact_type`),
    required: row.required === true,
  };
};

const parseConnection = (value: unknown, path: string): ConnectionSpec => {
  const row = record(value, path);
  const channel = string(row.channel, `${path}.channel`);
  if (!CHANNELS.includes(channel as Channel)) throw new Error(`${path}.channel is unknown`);
  return {
    source_mechanism: string(row.source_mechanism, `${path}.source_mechanism`),
    source_port: string(row.source_port, `${path}.source_port`),
    target_mechanism: string(row.target_mechanism, `${path}.target_mechanism`),
    target_port: string(row.target_port, `${path}.target_port`),
    channel: channel as Channel,
    latency: number(row.latency, `${path}.latency`),
  };
};

export function parseSystemSpec(value: unknown, path = "spec"): SystemSpec {
  const row = record(value, path);
  return {
    system_id: string(row.system_id, `${path}.system_id`),
    version: number(row.version, `${path}.version`),
    agent_types: array(row.agent_types, `${path}.agent_types`),
    artifact_types: array(row.artifact_types, `${path}.artifact_types`).map((item, index) => {
      const artifact = record(item, `${path}.artifact_types[${index}]`);
      return {
        artifact_type_id: string(artifact.artifact_type_id, `${path}.artifact_types[${index}].artifact_type_id`),
        description: typeof artifact.description === "string" ? artifact.description : "",
      };
    }),
    mechanisms: array(row.mechanisms, `${path}.mechanisms`).map((item, index) => {
      const mechanismPath = `${path}.mechanisms[${index}]`;
      const mechanism = record(item, mechanismPath);
      return {
        mechanism_id: string(mechanism.mechanism_id, `${mechanismPath}.mechanism_id`),
        family: string(mechanism.family, `${mechanismPath}.family`),
        implementation: string(mechanism.implementation, `${mechanismPath}.implementation`),
        version: number(mechanism.version, `${mechanismPath}.version`),
        inputs: array(mechanism.inputs, `${mechanismPath}.inputs`).map((port, portIndex) => parsePort(port, `${mechanismPath}.inputs[${portIndex}]`)),
        outputs: array(mechanism.outputs, `${mechanismPath}.outputs`).map((port, portIndex) => parsePort(port, `${mechanismPath}.outputs[${portIndex}]`)),
        parameters: record(mechanism.parameters, `${mechanismPath}.parameters`),
      };
    }),
    connections: array(row.connections, `${path}.connections`).map((item, index) => parseConnection(item, `${path}.connections[${index}]`)),
    schedules: array(row.schedules, `${path}.schedules`).map((item, index) => {
      const schedule = record(item, `${path}.schedules[${index}]`);
      return {
        mechanism_id: string(schedule.mechanism_id, `${path}.schedules[${index}].mechanism_id`),
        phase: number(schedule.phase, `${path}.schedules[${index}].phase`),
        trigger: string(schedule.trigger, `${path}.schedules[${index}].trigger`),
      };
    }),
    initial_state: record(row.initial_state, `${path}.initial_state`),
    global_invariants: array(row.global_invariants, `${path}.global_invariants`).map((item, index) => string(item, `${path}.global_invariants[${index}]`)),
    metadata: record(row.metadata, `${path}.metadata`),
  };
}

export function parseSandboxBundle(value: unknown): SandboxBundle {
  const root = record(value, "sandbox");
  if (root.schema_version !== "scienceutopia.system-sandbox.v1") throw new Error("sandbox schema version is not supported");
  if (root.truth_status !== "synthetic" || root.source_kind !== "synthetic_system_design_sandbox") throw new Error("sandbox may not claim verified or empirical provenance");
  const nodeCatalog = array(root.node_catalog, "sandbox.node_catalog").map((item, index) => {
    const path = `sandbox.node_catalog[${index}]`;
    const node = record(item, path);
    return {
      mechanism_id: string(node.mechanism_id, `${path}.mechanism_id`),
      label: string(node.label, `${path}.label`),
      asset_key: string(node.asset_key, `${path}.asset_key`),
      description: string(node.description, `${path}.description`),
      x: number(node.x, `${path}.x`),
      y: number(node.y, `${path}.y`),
      implementations: array(node.implementations, `${path}.implementations`).map((implementation, implementationIndex) => {
        const choice = record(implementation, `${path}.implementations[${implementationIndex}]`);
        return { id: string(choice.id, `${path}.implementations[${implementationIndex}].id`), label: string(choice.label, `${path}.implementations[${implementationIndex}].label`) };
      }),
    };
  });
  const edgeCatalog = array(root.edge_catalog, "sandbox.edge_catalog").map((item, index) => {
    const path = `sandbox.edge_catalog[${index}]`;
    const edge = record(item, path);
    return {
      edge_id: string(edge.edge_id, `${path}.edge_id`),
      label: string(edge.label, `${path}.label`),
      connection: parseConnection(edge.connection, `${path}.connection`),
      allowed_latencies: array(edge.allowed_latencies, `${path}.allowed_latencies`).map((latency, latencyIndex) => number(latency, `${path}.allowed_latencies[${latencyIndex}]`)),
    };
  });
  const fixtures = array(root.authoritative_fixtures, "sandbox.authoritative_fixtures").map((item, index) => {
    const path = `sandbox.authoritative_fixtures[${index}]`;
    const fixture = record(item, path);
    const validation = record(fixture.validation, `${path}.validation`);
    return {
      id: string(fixture.id, `${path}.id`),
      spec: parseSystemSpec(fixture.spec, `${path}.spec`),
      fingerprint: string(fixture.fingerprint, `${path}.fingerprint`),
      validation: {
        valid: validation.valid === true,
        issues: array(validation.issues, `${path}.validation.issues`).map((issue, issueIndex) => {
          const issueRow = record(issue, `${path}.validation.issues[${issueIndex}]`);
          const severityValue = string(issueRow.severity, `${path}.validation.issues[${issueIndex}].severity`);
          const severity: "error" | "warning" = severityValue === "warning" ? "warning" : "error";
          if (severityValue !== "error" && severityValue !== "warning") throw new Error(`${path}.validation.issues[${issueIndex}].severity is unknown`);
          return {
            code: string(issueRow.code, `${path}.validation.issues[${issueIndex}].code`),
            path: string(issueRow.path, `${path}.validation.issues[${issueIndex}].path`),
            message: string(issueRow.message, `${path}.validation.issues[${issueIndex}].message`),
            severity,
          };
        }),
      },
    };
  });
  const bundle: SandboxBundle = {
    schema_version: "scienceutopia.system-sandbox.v1",
    truth_status: "synthetic",
    source_kind: "synthetic_system_design_sandbox",
    disclosure: string(root.disclosure, "sandbox.disclosure"),
    system_spec_contract: string(root.system_spec_contract, "sandbox.system_spec_contract"),
    validator_contract: string(root.validator_contract, "sandbox.validator_contract"),
    bundle_hash: string(root.bundle_hash, "sandbox.bundle_hash"),
    base_spec: parseSystemSpec(root.base_spec, "sandbox.base_spec"),
    node_catalog: nodeCatalog,
    edge_catalog: edgeCatalog,
    authoritative_fixtures: fixtures,
  };
  const baseIds = new Set(bundle.base_spec.mechanisms.map((mechanism) => mechanism.mechanism_id));
  if (new Set(nodeCatalog.map((node) => node.mechanism_id)).size !== nodeCatalog.length || nodeCatalog.some((node) => !baseIds.has(node.mechanism_id))) throw new Error("node catalog must uniquely cover base mechanisms");
  if (new Set(edgeCatalog.map((edge) => edge.edge_id)).size !== edgeCatalog.length) throw new Error("edge catalog ids must be unique");
  return bundle;
}

export async function verifySandboxBundle(bundle: SandboxBundle): Promise<void> {
  const unhashed = JSON.parse(stableStringify(bundle)) as Record<string, unknown>;
  delete unhashed.bundle_hash;
  if (await canonicalHash(unhashed) !== bundle.bundle_hash) throw new Error("synthetic sandbox bundle hash mismatch");
  if (bundle.authoritative_fixtures.length < 2) throw new Error("sandbox parity fixtures are incomplete");
  for (const fixture of bundle.authoritative_fixtures) {
    if (await canonicalHash(fixture.spec) !== fixture.fingerprint) throw new Error(`${fixture.id} fingerprint parity failed`);
    if (stableStringify(validateSystemSpec(fixture.spec)) !== stableStringify(fixture.validation)) throw new Error(`${fixture.id} validation parity failed`);
  }
  if (!bundle.authoritative_fixtures.some((fixture) => fixture.validation.valid) || !bundle.authoritative_fixtures.some((fixture) => !fixture.validation.valid)) throw new Error("sandbox requires valid and invalid parity fixtures");
}

export function initialSandboxState(bundle: SandboxBundle): SandboxState {
  return {
    nodes: Object.fromEntries(bundle.node_catalog.map((node) => {
      const base = bundle.base_spec.mechanisms.find((mechanism) => mechanism.mechanism_id === node.mechanism_id)!;
      return [node.mechanism_id, { enabled: true, implementation: base.implementation }];
    })),
    edges: Object.fromEntries(bundle.edge_catalog.map((edge) => [edge.edge_id, { enabled: true, latency: edge.connection.latency }])),
  };
}

export function materializeSystemSpec(bundle: SandboxBundle, state: SandboxState): SystemSpec {
  const activeMechanisms = bundle.base_spec.mechanisms
    .filter((mechanism) => state.nodes[mechanism.mechanism_id]?.enabled)
    .map((mechanism) => ({ ...mechanism, implementation: state.nodes[mechanism.mechanism_id]!.implementation }));
  return {
    ...bundle.base_spec,
    mechanisms: activeMechanisms,
    connections: bundle.edge_catalog
      .filter((edge) => state.edges[edge.edge_id]?.enabled)
      .map((edge) => ({ ...edge.connection, latency: state.edges[edge.edge_id]!.latency })),
    schedules: bundle.base_spec.schedules.filter((schedule) => state.nodes[schedule.mechanism_id]?.enabled),
  };
}

const ID = /^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$/;

export function validateSystemSpec(spec: SystemSpec): ValidationReport {
  const issues: ValidationIssue[] = [];
  const error = (code: string, path: string, message: string): void => { issues.push({ code, path, message, severity: "error" }); };
  const warning = (code: string, path: string, message: string): void => { issues.push({ code, path, message, severity: "warning" }); };
  if (!ID.test(spec.system_id)) error("invalid_id", "system_id", "must be a lowercase dotted/dashed identifier");
  if (!Number.isInteger(spec.version) || spec.version < 1) error("invalid_version", "version", "must be a positive integer");
  const artifacts = new Set(spec.artifact_types.map((artifact) => artifact.artifact_type_id));
  const mechanismById = new Map<string, MechanismSpec>();
  spec.mechanisms.forEach((mechanism, index) => {
    const base = `mechanisms[${index}]`;
    if (mechanismById.has(mechanism.mechanism_id)) error("duplicate_mechanism", `${base}.mechanism_id`, `duplicates ${JSON.stringify(mechanism.mechanism_id)}`);
    mechanismById.set(mechanism.mechanism_id, mechanism);
    if (!ID.test(mechanism.mechanism_id)) error("invalid_id", `${base}.mechanism_id`, "must be a lowercase dotted/dashed identifier");
    if (!mechanism.implementation.trim()) error("empty_implementation", `${base}.implementation`, "must not be empty");
    if (!Number.isInteger(mechanism.version) || mechanism.version < 1) error("invalid_version", `${base}.version`, "must be a positive integer");
    [...mechanism.inputs, ...mechanism.outputs].forEach((port) => {
      if (port.artifact_type !== null && !artifacts.has(port.artifact_type)) error("unknown_artifact_type", `${base}.${port.port_id}.artifact_type`, `references ${JSON.stringify(port.artifact_type)}`);
    });
  });
  const connectedInputs = new Set<string>();
  const seenConnections = new Set<string>();
  spec.connections.forEach((connection, index) => {
    const path = `connections[${index}]`;
    const key = `${connection.source_mechanism}\0${connection.source_port}\0${connection.target_mechanism}\0${connection.target_port}`;
    if (seenConnections.has(key)) error("duplicate_connection", path, "duplicates an existing graph edge");
    seenConnections.add(key);
    if (!Number.isInteger(connection.latency) || connection.latency < 0) error("invalid_latency", `${path}.latency`, "must be a non-negative integer");
    const source = mechanismById.get(connection.source_mechanism);
    const target = mechanismById.get(connection.target_mechanism);
    if (!source) error("unknown_source", `${path}.source_mechanism`, "mechanism does not exist");
    if (!target) error("unknown_target", `${path}.target_mechanism`, "mechanism does not exist");
    const sourcePort = source?.outputs.find((port) => port.port_id === connection.source_port);
    const targetPort = target?.inputs.find((port) => port.port_id === connection.target_port);
    if (source && !sourcePort) error("unknown_source_port", `${path}.source_port`, "output port does not exist");
    if (target && !targetPort) error("unknown_target_port", `${path}.target_port`, "input port does not exist");
    if (sourcePort && sourcePort.channel !== connection.channel) error("source_channel_mismatch", `${path}.channel`, "does not match source port");
    if (targetPort && targetPort.channel !== connection.channel) error("target_channel_mismatch", `${path}.channel`, "does not match target port");
    if (sourcePort?.artifact_type && targetPort?.artifact_type && sourcePort.artifact_type !== targetPort.artifact_type) error("artifact_type_mismatch", path, "source and target artifact types differ");
    if (targetPort) connectedInputs.add(`${connection.target_mechanism}\0${connection.target_port}`);
  });
  for (const mechanism of spec.mechanisms) {
    for (const port of mechanism.inputs) {
      if (port.required && !connectedInputs.has(`${mechanism.mechanism_id}\0${port.port_id}`)) error("unconnected_required_input", `mechanisms.${mechanism.mechanism_id}.inputs.${port.port_id}`, "required input has no incoming connection");
    }
  }
  const scheduled = new Set<string>();
  spec.schedules.forEach((schedule, index) => {
    const path = `schedules[${index}]`;
    if (!mechanismById.has(schedule.mechanism_id)) error("unknown_scheduled_mechanism", `${path}.mechanism_id`, "mechanism does not exist");
    if (scheduled.has(schedule.mechanism_id)) error("duplicate_schedule", path, "mechanism is scheduled more than once");
    scheduled.add(schedule.mechanism_id);
    if (!Number.isInteger(schedule.phase) || schedule.phase < 0) error("invalid_phase", `${path}.phase`, "must be a non-negative integer");
    if (!schedule.trigger.trim()) error("empty_trigger", `${path}.trigger`, "must not be empty");
  });
  for (const mechanismId of mechanismById.keys()) if (!scheduled.has(mechanismId)) warning("unscheduled_mechanism", `mechanisms.${mechanismId}`, "has no schedule; this is valid only for externally triggered or passive mechanisms");
  return { valid: !issues.some((issue) => issue.severity === "error"), issues };
}
