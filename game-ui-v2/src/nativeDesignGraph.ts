export const mechanismFamilies = ["population", "research", "evaluation", "publication", "funding", "governance", "communication", "collaboration", "employment", "education", "custom"] as const;
export const channelKinds = ["artifact", "score", "decision", "feedback", "resource", "signal", "constraint"] as const;

export type DesignPort = {
  port_id: string;
  channel: string;
  artifact_type?: string | null;
  required?: boolean;
};

export type DesignMechanism = {
  mechanism_id: string;
  family: string;
  implementation: string;
  version?: number;
  inputs: DesignPort[];
  outputs: DesignPort[];
  parameters: Record<string, unknown>;
  [key: string]: unknown;
};

export type DesignConnection = {
  source_mechanism: string;
  source_port: string;
  target_mechanism: string;
  target_port: string;
  channel: string;
  latency: number;
  [key: string]: unknown;
};

export type DesignSchedule = {
  mechanism_id: string;
  phase: number;
  trigger: string;
  [key: string]: unknown;
};

export type EditableSystemSpec = Record<string, unknown> & {
  mechanisms: DesignMechanism[];
  connections: DesignConnection[];
  schedules: DesignSchedule[];
};

export type StructuralCheck = { valid: boolean; errors: string[]; warnings: string[] };

const identifier = /^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$/;
const object = (value: unknown): value is Record<string, unknown> => Boolean(value) && typeof value === "object" && !Array.isArray(value);
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

export function parseEditableSystemSpec(value: unknown): EditableSystemSpec {
  if (!object(value)) throw new Error("SystemSpec must be a JSON object");
  if (!Array.isArray(value.mechanisms) || !Array.isArray(value.connections) || !Array.isArray(value.schedules)) throw new Error("SystemSpec needs mechanisms, connections and schedules arrays");
  const spec = clone(value) as EditableSystemSpec;
  for (const [index, node] of spec.mechanisms.entries()) {
    if (!object(node)) throw new Error(`mechanisms[${index}] must be an object`);
    node.inputs ??= [];
    node.outputs ??= [];
    node.parameters ??= {};
    if (!Array.isArray(node.inputs) || !Array.isArray(node.outputs) || !object(node.parameters)) throw new Error(`mechanisms[${index}] has malformed ports or parameters`);
  }
  return spec;
}

export function structuralCheck(spec: EditableSystemSpec): StructuralCheck {
  const errors: string[] = [], warnings: string[] = [];
  const nodeIds = new Set<string>(), schedules = new Set<string>();
  const nodeById = new Map<string, DesignMechanism>();
  for (const [index, node] of spec.mechanisms.entries()) {
    const at = `mechanisms[${index}]`;
    if (!identifier.test(node.mechanism_id)) errors.push(`${at}.mechanism_id must be a lowercase dotted/dashed identifier`);
    if (nodeIds.has(node.mechanism_id)) errors.push(`${at}.mechanism_id duplicates ${node.mechanism_id}`);
    nodeIds.add(node.mechanism_id); nodeById.set(node.mechanism_id, node);
    if (!mechanismFamilies.includes(node.family as typeof mechanismFamilies[number])) errors.push(`${at}.family is not a known family`);
    if (!node.implementation?.trim()) errors.push(`${at}.implementation must not be empty`);
    const ports = new Set<string>();
    for (const [direction, list] of [["inputs", node.inputs], ["outputs", node.outputs]] as const) for (const [portIndex, port] of list.entries()) {
      const path = `${at}.${direction}[${portIndex}]`;
      if (!identifier.test(port.port_id)) errors.push(`${path}.port_id must be a lowercase dotted/dashed identifier`);
      if (ports.has(port.port_id)) errors.push(`${path}.port_id duplicates ${port.port_id}`);
      ports.add(port.port_id);
      if (!channelKinds.includes(port.channel as typeof channelKinds[number])) errors.push(`${path}.channel is not a known channel`);
    }
  }
  const edgeKeys = new Set<string>(), connectedInputs = new Set<string>();
  for (const [index, edge] of spec.connections.entries()) {
    const at = `connections[${index}]`, source = nodeById.get(edge.source_mechanism), target = nodeById.get(edge.target_mechanism);
    const key = `${edge.source_mechanism}\u0000${edge.source_port}\u0000${edge.target_mechanism}\u0000${edge.target_port}`;
    if (edgeKeys.has(key)) errors.push(`${at} duplicates an existing edge`); edgeKeys.add(key);
    if (!source) errors.push(`${at}.source_mechanism does not exist`);
    if (!target) errors.push(`${at}.target_mechanism does not exist`);
    const output = source?.outputs.find(port => port.port_id === edge.source_port), input = target?.inputs.find(port => port.port_id === edge.target_port);
    if (source && !output) errors.push(`${at}.source_port is not an output on ${edge.source_mechanism}`);
    if (target && !input) errors.push(`${at}.target_port is not an input on ${edge.target_mechanism}`);
    if (!Number.isInteger(edge.latency) || edge.latency < 0) errors.push(`${at}.latency must be a non-negative integer`);
    if (!channelKinds.includes(edge.channel as typeof channelKinds[number])) errors.push(`${at}.channel is not a known channel`);
    if (output && output.channel !== edge.channel) errors.push(`${at}.channel does not match source port`);
    if (input && input.channel !== edge.channel) errors.push(`${at}.channel does not match target port`);
    if (output?.artifact_type && input?.artifact_type && output.artifact_type !== input.artifact_type) errors.push(`${at} connects different artifact types`);
    if (target && input) connectedInputs.add(`${target.mechanism_id}\u0000${input.port_id}`);
  }
  for (const node of spec.mechanisms) for (const port of node.inputs) if (port.required !== false && !connectedInputs.has(`${node.mechanism_id}\u0000${port.port_id}`)) errors.push(`${node.mechanism_id}.${port.port_id} is a required input without a connection`);
  for (const [index, schedule] of spec.schedules.entries()) {
    if (!nodeById.has(schedule.mechanism_id)) errors.push(`schedules[${index}].mechanism_id does not exist`);
    if (schedules.has(schedule.mechanism_id)) errors.push(`schedules[${index}] duplicates a node schedule`);
    schedules.add(schedule.mechanism_id);
    if (!Number.isInteger(schedule.phase) || schedule.phase < 0) errors.push(`schedules[${index}].phase must be a non-negative integer`);
    if (!schedule.trigger?.trim()) errors.push(`schedules[${index}].trigger must not be empty`);
  }
  for (const id of nodeIds) if (!schedules.has(id)) warnings.push(`${id} has no schedule`);
  return { valid: errors.length === 0, errors, warnings };
}

export function addMechanism(spec: EditableSystemSpec, id: string): EditableSystemSpec {
  const next = clone(spec), used = new Set(next.mechanisms.map(node => node.mechanism_id));
  let mechanismId = id, suffix = 2; while (used.has(mechanismId)) mechanismId = `${id}-${suffix++}`;
  next.mechanisms.push({ mechanism_id: mechanismId, family: "custom", implementation: "replace.with.registered.implementation", version: 1, inputs: [], outputs: [], parameters: {} });
  next.schedules.push({ mechanism_id: mechanismId, phase: Math.max(0, ...next.schedules.map(row => row.phase)) + 20, trigger: "annual" });
  return next;
}

export function removeMechanism(spec: EditableSystemSpec, id: string): EditableSystemSpec {
  const next = clone(spec);
  next.mechanisms = next.mechanisms.filter(node => node.mechanism_id !== id);
  next.connections = next.connections.filter(edge => edge.source_mechanism !== id && edge.target_mechanism !== id);
  next.schedules = next.schedules.filter(row => row.mechanism_id !== id);
  return next;
}

export function renameMechanism(spec: EditableSystemSpec, before: string, after: string): EditableSystemSpec {
  const next = clone(spec), node = next.mechanisms.find(item => item.mechanism_id === before);
  if (!node) throw new Error(`Unknown mechanism ${before}`);
  node.mechanism_id = after;
  for (const edge of next.connections) { if (edge.source_mechanism === before) edge.source_mechanism = after; if (edge.target_mechanism === before) edge.target_mechanism = after; }
  for (const schedule of next.schedules) if (schedule.mechanism_id === before) schedule.mechanism_id = after;
  return next;
}

export function removePort(spec: EditableSystemSpec, mechanismId: string, direction: "inputs" | "outputs", portId: string): EditableSystemSpec {
  const next = clone(spec), node = next.mechanisms.find(item => item.mechanism_id === mechanismId);
  if (!node) throw new Error(`Unknown mechanism ${mechanismId}`);
  node[direction] = node[direction].filter(port => port.port_id !== portId);
  next.connections = next.connections.filter(edge => direction === "outputs" ? !(edge.source_mechanism === mechanismId && edge.source_port === portId) : !(edge.target_mechanism === mechanismId && edge.target_port === portId));
  return next;
}

export function setConnection(spec: EditableSystemSpec, index: number | null, edge: DesignConnection): EditableSystemSpec {
  const next = clone(spec);
  if (index === null) next.connections.push(clone(edge));
  else if (index >= 0 && index < next.connections.length) next.connections[index] = clone(edge);
  else throw new Error("Unknown connection");
  return next;
}

export function removeConnection(spec: EditableSystemSpec, index: number): EditableSystemSpec {
  const next = clone(spec); next.connections.splice(index, 1); return next;
}

export function serializeSystemSpec(spec: EditableSystemSpec): string { return JSON.stringify(spec, null, 2); }
