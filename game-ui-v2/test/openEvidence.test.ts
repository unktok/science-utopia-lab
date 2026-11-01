import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { parseNativeOpenEvidence, verifyNativeOpenEvidence } from "../src/openEvidenceContract";

const fixturePath = new URL("../public/data/native-open-evidence.synthetic.json", import.meta.url);
const fixture = () => JSON.parse(readFileSync(fixturePath, "utf8"));

describe("native open integrated evidence viewer contract", () => {
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
    const changed = fixture(); changed.physical_reply_count = 0;
    expect(() => parseNativeOpenEvidence(changed, "fixture")).toThrow("physical reply evidence");
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
