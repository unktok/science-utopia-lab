export type NativeNode = { mechanism_id: string; family: string; implementation: string; parameters: Record<string, any>; inputs: { port_id: string }[]; outputs: { port_id: string }[] };
export type NativeSpec = { mechanisms: NativeNode[]; connections: { source_mechanism: string; source_port: string; target_mechanism: string; target_port: string; channel: string; latency: number }[]; schedules: { mechanism_id: string; phase: number }[] };
export type NativeRun = { seed: number; frames: { year: number; paper_count: number; actors: { id: string; type: string; resources: number; is_active: boolean; can_author: boolean }[] }[]; events: { year: number; phase: number; event_type: string; provenance: Record<string, any>; payload: Record<string, any> }[] };
export type NativeCandidate = { suggestion_id: string; system_fingerprint: string; system_spec_json: string; spec: NativeSpec; status: "complete" | "failed"; native_loss: number | null; technical_failures: unknown[]; runs: NativeRun[]; difference: { nodes_added: string[]; nodes_changed: string[]; nodes_removed: string[] } };
export type NativeLab = { schema: string; source: { world: { source_commit: string; years: number; model: string }; loss_spec_sha256: string }; systems: NativeCandidate[]; relaxation: null | { history: { step: number; conditional_soft_loss: number }[]; scope: string }; interpretation: Record<string, unknown> };

export async function shaText(text: string): Promise<string> {
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text))), b => b.toString(16).padStart(2, "0")).join("");
}

export async function parseNativeLab(value: unknown): Promise<NativeLab> {
  const envelope = value as Record<string, unknown>;
  if (!envelope || envelope.schema !== "scienceutopia.native-design-lab-envelope.v1" || typeof envelope.payload_json !== "string" || await shaText(envelope.payload_json) !== envelope.payload_sha256) throw new Error("Native evidence envelope hash mismatch");
  const lab = JSON.parse(envelope.payload_json) as NativeLab;
  if (lab.schema !== "scienceutopia.native-design-lab.v1" || lab.interpretation.full_native_world_autograd !== false || lab.interpretation.model_weights_trained !== false || lab.interpretation.live_player_intervention !== false) throw new Error("Unsupported native/gradient/intervention claim");
  if (!Array.isArray(lab.systems) || !lab.systems.length) throw new Error("Missing actual native systems");
  for (const system of lab.systems) {
    if (typeof system.system_spec_json !== "string" || await shaText(system.system_spec_json) !== system.system_fingerprint) throw new Error("Native SystemSpec fingerprint mismatch");
    system.spec = JSON.parse(system.system_spec_json) as NativeSpec;
    const ids = new Set(system.spec.mechanisms.map(n => n.mechanism_id));
    if (ids.size !== system.spec.mechanisms.length || system.spec.connections.some(e => !ids.has(e.source_mechanism) || !ids.has(e.target_mechanism))) throw new Error("Invalid native graph references");
    if ((system.status === "complete") !== (typeof system.native_loss === "number" && Number.isFinite(system.native_loss))) throw new Error("Native status/loss mismatch");
    if (system.status === "complete" && (!system.runs.length || system.runs.some(r => !r.frames.length || !r.events.length))) throw new Error("Missing native execution evidence");
    if (system.runs.some(r => r.frames.some(f => !Number.isInteger(f.year) || f.actors.some(a => !Number.isFinite(a.resources))))) throw new Error("Invalid native frame values");
  }
  return lab;
}
