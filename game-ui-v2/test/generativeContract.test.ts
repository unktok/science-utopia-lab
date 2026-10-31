import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { parseGenerativeLab } from "../src/generativeContract";

function payload(): Record<string, any> {
  return {
    schema: "scienceutopia.generative-lab-view.v1", backend: "numeric-program-world-v1",
    source: { commit: "a".repeat(40), dirty_development: false },
    qwen_role: "none", qwen_in_autograd: false,
    arms: [{ objective: "production", projection_gap: 0.1,
      gradient_audit: { all_pass: true, records: [{ group: "node_logits", analytic: 0.2, absolute_error: 1e-10 }] },
      gradient_trace: [{ step: 0, relaxed_loss: -0.1 }], blackbox_path: [{ loss: -0.2 }],
      systems: [{ label: "Generated rule", system_fingerprint: "b".repeat(64), loss: -0.2,
        metrics: { production: 0.2 },
        system_spec: { mechanisms: [{ mechanism_id: "commons", family: "custom", parameters: {
          label: "Replication commons", program: { output: { input: "quality" } }, effects: { learning: 0.4 },
        } }], connections: [], schedules: [{ mechanism_id: "commons", phase: 0 }] },
        frames: [{ period: 0, world: { quality: [0.2, 0.3], novelty: [0.5, 0.5], resources: [0.5, 0.5], knowledge: [0.1, 0.2] },
          mechanisms: { commons: [0.2, 0.3] }, signals: { commons: [0, 0] }, execution_order: ["commons"], production: [0.1, 0.2], allocation: [1, 1] }],
        events: [{ sequence: 0, year: 0, event_type: "agent.registered", payload: {}, provenance: {} }],
      }],
    }],
  };
}
function envelope(data: unknown) {
  const payload_json = JSON.stringify(data);
  return { schema: "scienceutopia.generative-lab-envelope.v1", payload_json,
    payload_sha256: createHash("sha256").update(payload_json).digest("hex") };
}

describe("executed generative lab evidence", () => {
  it("loads a generated custom mechanism and its measured world", async () => {
    const parsed = await parseGenerativeLab(envelope(payload()));
    expect(parsed.arms[0]?.systems[0]?.system_spec.mechanisms[0]?.family).toBe("custom");
    expect(parsed.qwen_in_autograd).toBe(false);
  });
  it("rejects changed raw evidence", async () => {
    const wrapped = envelope(payload());
    wrapped.payload_json += " ";
    await expect(parseGenerativeLab(wrapped)).rejects.toThrow("hash mismatch");
  });
  it("rejects unsupported claims about differentiating Qwen", async () => {
    const data = payload(); data.qwen_in_autograd = true;
    await expect(parseGenerativeLab(envelope(data))).rejects.toThrow("differentiate Qwen");
  });
  it("rejects missing execution records instead of making up world animation", async () => {
    const data = payload(); data.arms[0].systems[0].frames = [];
    await expect(parseGenerativeLab(envelope(data))).rejects.toThrow("Missing world execution");
  });
  it("rejects dangling graph edges", async () => {
    const data = payload(); data.arms[0].systems[0].system_spec.connections.push({ source_mechanism: "ghost", target_mechanism: "commons", latency: 0 });
    await expect(parseGenerativeLab(envelope(data))).rejects.toThrow("Invalid graph edge");
  });
  it("rejects inconsistent agent vectors", async () => {
    const data = payload(); data.arms[0].systems[0].frames[0].world.knowledge = [0.1];
    await expect(parseGenerativeLab(envelope(data))).rejects.toThrow("Agent vector size mismatch");
  });
});
