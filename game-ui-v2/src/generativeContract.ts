export interface ProgramNode {
  mechanism_id: string;
  family: string;
  parameters: { program: Record<string, unknown>; label: string; effects: Record<string, number> };
}
export interface ProgramSystem {
  mechanisms: ProgramNode[];
  connections: { source_mechanism: string; target_mechanism: string; latency: number }[];
  schedules: { mechanism_id: string; phase: number }[];
}
export interface LabFrame {
  period: number;
  world: { quality: number[]; novelty: number[]; resources: number[]; knowledge: number[] };
  mechanisms: Record<string, number[]>;
  signals: Record<string, number[]>;
  production: number[];
  allocation: number[];
  execution_order: string[];
}
export interface LabSystem {
  label: string;
  system_spec: ProgramSystem;
  system_fingerprint: string;
  loss: number;
  metrics: Record<string, number>;
  frames: LabFrame[];
  events: { year: number; sequence: number; event_type: string; payload: unknown; provenance: unknown }[];
}
export interface LabArm {
  objective: string;
  systems: LabSystem[];
  gradient_trace: { step: number; relaxed_loss: number }[];
  blackbox_path: { loss: number | null; proposal_id: string; phase: string; parent_observation: string | null }[];
  gradient_audit: { all_pass: boolean; records: { group: string; absolute_error: number; analytic: number }[] };
  projection_gap: number;
}
export interface GenerativeLab {
  schema: "scienceutopia.generative-lab-view.v1";
  backend: "numeric-program-world-v1";
  source: { commit: string; dirty_development: boolean };
  qwen_role: "none" | "frozen-mechanism-and-initial-attributes";
  qwen_in_autograd: false;
  arms: LabArm[];
}

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Expected an object");
  return value as Record<string, unknown>;
}
function array(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new Error("Expected an array");
  return value;
}
function finite(value: unknown): void {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error("Expected a finite observed number");
}

export async function parseGenerativeLab(envelope: unknown): Promise<GenerativeLab> {
  const entry = record(envelope);
  if (entry.schema !== "scienceutopia.generative-lab-envelope.v1" || typeof entry.payload_json !== "string") throw new Error("Unsupported lab envelope");
  const buffer = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(entry.payload_json));
  const sha = [...new Uint8Array(buffer)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  if (sha !== entry.payload_sha256) throw new Error("Lab payload hash mismatch");
  const data = record(JSON.parse(entry.payload_json));
  if (data.schema !== "scienceutopia.generative-lab-view.v1" || data.backend !== "numeric-program-world-v1") throw new Error("Unsupported lab backend");
  if (data.qwen_in_autograd !== false) throw new Error("This contract does not differentiate Qwen");
  if (data.qwen_role !== "none" && data.qwen_role !== "frozen-mechanism-and-initial-attributes") throw new Error("Unknown Qwen role");
  const source = record(data.source);
  if (typeof source.commit !== "string" || !/^[a-f0-9]{40}$/.test(source.commit) || typeof source.dirty_development !== "boolean") throw new Error("Missing source commit");
  if (!array(data.arms).length) throw new Error("Lab has no objective arms");
  for (const rawArm of array(data.arms)) {
    const arm = record(rawArm);
    finite(arm.projection_gap);
    if (typeof arm.objective !== "string" || !array(arm.systems).length) throw new Error("Invalid arm");
    for (const rawSystem of array(arm.systems)) {
      const system = record(rawSystem);
      finite(system.loss);
      if (typeof system.label !== "string" || typeof system.system_fingerprint !== "string") throw new Error("Missing system identity");
      const spec = record(system.system_spec);
      const nodes = array(spec.mechanisms).map((node) => record(node));
      const ids = new Set(nodes.map((node) => node.mechanism_id));
      if (nodes.length !== ids.size) throw new Error("Invalid mechanism ids");
      for (const node of nodes) {
        const parameters = record(node.parameters);
        if (typeof node.mechanism_id !== "string" || typeof parameters.label !== "string") throw new Error("Invalid mechanism");
        record(parameters.program);
      }
      for (const rawEdge of array(spec.connections)) {
        const edge = record(rawEdge);
        if (!ids.has(edge.source_mechanism) || !ids.has(edge.target_mechanism) || (edge.latency !== 0 && edge.latency !== 1)) throw new Error("Invalid graph edge");
      }
      for (const value of Object.values(record(system.metrics))) finite(value);
      let population = 0;
      if (!array(system.frames).length) throw new Error("Missing world execution");
      for (const [index, rawFrame] of array(system.frames).entries()) {
        const frame = record(rawFrame);
        if (frame.period !== index) throw new Error("Invalid period sequence");
        const world = record(frame.world);
        if (!population) population = array(world.quality).length;
        if (population < 2 || population > 10) throw new Error("Invalid miniature population");
        for (const key of ["quality", "novelty", "knowledge", "resources"]) {
          const values = array(world[key]);
          if (values.length !== population) throw new Error("Agent vector size mismatch");
          values.forEach(finite);
        }
        for (const field of ["mechanisms", "signals"]) {
          const vectors = record(frame[field]);
          if (Object.keys(vectors).length !== ids.size) throw new Error("Missing mechanism observation");
          for (const id of ids) {
            const values = array(vectors[String(id)]);
            if (values.length !== population) throw new Error("Mechanism vector size mismatch");
            values.forEach(finite);
          }
        }
        const order = array(frame.execution_order);
        if (order.length !== ids.size || new Set(order).size !== ids.size || order.some((id) => !ids.has(id))) throw new Error("Invalid executed schedule");
      }
      if (!array(system.events).length) throw new Error("Canonical events missing");
    }
    for (const rawRow of array(arm.gradient_trace)) {
      const row = record(rawRow);
      finite(row.step); finite(row.relaxed_loss);
    }
    for (const rawRow of array(arm.blackbox_path)) {
      const row = record(rawRow);
      if (row.loss !== null) finite(row.loss);
    }
    const audit = record(arm.gradient_audit);
    if (typeof audit.all_pass !== "boolean") throw new Error("Missing gradient audit");
    for (const row of array(audit.records)) { finite(record(row).analytic); finite(record(row).absolute_error); }
  }
  return data as unknown as GenerativeLab;
}
