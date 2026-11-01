import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { derivativeDiagnosticFailure, parseNativeOpenEvidence, processReceiptYear, verifyNativeOpenEvidence } from "../src/openEvidenceContract";

const fixturePath = new URL("../public/data/native-open-evidence.synthetic.json", import.meta.url);
const actualPath = new URL("../public/data/native-open-integrated-v7.json", import.meta.url);
const fixture = () => JSON.parse(readFileSync(fixturePath, "utf8"));

describe("native open integrated evidence viewer contract", () => {
  it("loads the independently audited four-world actual export", () => {
    const parsed = parseNativeOpenEvidence(JSON.parse(readFileSync(actualPath, "utf8")), "actual");
    expect(parsed.status).toBe("complete");
    expect(parsed.physical_reply_count).toBe(342);
    expect(parsed.complete_native_worlds).toBe(4);
    expect(parsed.observations.map((row) => row.observation?.loss)).toEqual([-1.2, -0.2, -0.8, -0.2]);
    expect(parsed.content_sha256).toBe("cce6b6b8af54f96bd5b68c00e938b218198ad6dae5cd1241f6427a1c7cabf4fe");
  });

  it("accepts only an explicitly labelled and hash-bound UI fixture", async () => {
    const parsed = await verifyNativeOpenEvidence(fixture(), "fixture");
    expect(parsed.observations).toHaveLength(2);
    expect(parsed.physical_reply_count).toBe(8);
    expect(parsed.observations[0]!.observation!.loss).toBe(0);
    expect(parsed.observations[1]!.observation).toMatchObject({ status: "failed", loss: null });
    expect(() => parseNativeOpenEvidence(fixture(), "actual")).toThrow("Synthetic fixture");
  });

  it("fails closed instead of manufacturing endpoint fields or numeric losses", () => {
    const changed = fixture(); changed.observations[1].checkpoint_sha256 = "a".repeat(64);
    expect(() => parseNativeOpenEvidence(changed, "fixture")).toThrow("fabricated checkpoint_sha256");
    const numerical = fixture(); numerical.observations[1].observation.loss = 1000;
    expect(() => parseNativeOpenEvidence(numerical, "fixture")).toThrow("retain null loss");
  });

  it("does not relabel a conditional derivative as full-world or native-loss gradient", () => {
    const changed = fixture(); changed.observations[0].conditional_backward.native_loss_gradient_verified = true;
    expect(() => parseNativeOpenEvidence(changed, "fixture")).toThrow("relabelled");
    const causal = fixture(); causal.claims.causal_institutional_benefit = true;
    expect(() => parseNativeOpenEvidence(causal, "fixture")).toThrow("causal_institutional_benefit");
  });

  it("binds the live-Qwen claim to physical replies rather than configuration", () => {
    const changed = fixture(); changed.physical_reply_count = 0; changed.physical_response_caches[0].outcomes.response = 0;
    expect(() => parseNativeOpenEvidence(changed, "fixture")).toThrow("physical reply evidence");
  });

  it("uses each process event's actual envelope year before endpoint fallback", () => {
    const event = fixture().observations[0].process_receipts[0];
    expect(processReceiptYear(event, 2)).toBe(1);
    expect(processReceiptYear({ event_type: "native.process.completed", payload: { year: 2 } }, 3)).toBe(2);
    expect(processReceiptYear({ event_type: "native.process.iteration", payload: {} }, 3)).toBe(3);
  });

  it("requires status complete to mean all four native worlds and exact cache reply totals", () => {
    const complete = fixture(); complete.status = "complete";
    expect(() => parseNativeOpenEvidence(complete, "fixture")).toThrow("all four");
    const mismatched = fixture(); mismatched.physical_reply_count = 7; mismatched.claims.live_fixed_Qwen_researchers = true;
    expect(() => parseNativeOpenEvidence(mismatched, "fixture")).toThrow("response caches");
  });

  it("accepts a configured zero-world in-progress stage without fabricating outcomes", () => {
    const pending = fixture(); pending.status = "in-progress"; pending.records = []; pending.observations = [];
    pending.complete_native_worlds = 0; pending.physical_reply_count = 0; pending.physical_response_caches = [];
    pending.claims.live_fixed_Qwen_researchers = false;
    const parsed = parseNativeOpenEvidence(pending, "fixture");
    expect(parsed.observations).toEqual([]);
    expect(parsed.claims.live_fixed_Qwen_researchers).toBe(false);
  });

  it("retains derivative diagnostic failure errors without fabricating gradients or counts", () => {
    const changed = fixture(); const failure = { status: "failed-diagnostic", error_type: "TraceUnavailable", error: "actual tensor trace was absent", native_loss_gradient_verified: false, full_native_world_autograd: false };
    changed.observations[0].boundary_coverage = failure; changed.observations[0].conditional_backward = failure;
    const parsed = parseNativeOpenEvidence(changed, "fixture");
    expect(derivativeDiagnosticFailure(parsed.observations[0]!.boundary_coverage)).toEqual({ error_type: "TraceUnavailable", error: "actual tensor trace was absent" });
    expect(parsed.observations[0]!.observation!.loss).toBe(0);
    const malformed = fixture(); malformed.observations[0].conditional_backward = { ...failure, error: "" };
    expect(() => parseNativeOpenEvidence(malformed, "fixture")).toThrow("actual error");
  });

  it("retains actual participants, artifacts, process iteration and skip receipts", () => {
    const parsed = parseNativeOpenEvidence(fixture(), "fixture"); const row = parsed.observations[0]!;
    expect(Object.keys(row.open_domain!.actors)).toEqual(["night-lab"]);
    expect(Object.keys(row.open_domain!.artifacts)).toEqual(["signal-atlas"]);
    expect(row.process_receipts!.map((item) => item.event_type)).toEqual(["native.process.iteration", "native.process.completed", "native.process.skipped"]);
  });

  it("keeps the page English and makes every scientific boundary visible", () => {
    const html = readFileSync(new URL("../open-evidence.html", import.meta.url), "utf8");
    expect(html).toContain('lang="en"');
    for (const phrase of ["NOT HELD OUT", "NO CAUSAL BENEFIT CLAIM", "NOT FULL-WORLD AUTOGRAD", "PARTICIPANT + ARTIFACT REGISTRY", "SYSTEM GRAPH + SOURCE DETAILS"]) expect(html).toContain(phrase);
    expect(html).not.toMatch(/[\u3040-\u30ff\u3400-\u9fff]/u);
  });
});
