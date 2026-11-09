// SYNTHETIC envelope-shape QA, never a pre-scale scientific result.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { parseNativeLab } from "../src/nativeContract";
import { PRE_SCALE_ARMS, PRE_SCALE_SOURCE, PRE_SCALE_PLAN, PRE_SCALE_FOUNDRY_SCOPE,
  preScaleFoundryArm, preScaleFoundryFile, parsePreScaleFoundry } from "../src/preScaleFoundry";

const oldEnvelope = () => JSON.parse(readFileSync(new URL("../public/data/native-design-lab-v1.json", import.meta.url), "utf8"));
const seal = (data: any) => {
  const payload_json = JSON.stringify(data);
  return { schema: "scienceutopia.native-design-lab-envelope.v1", payload_json,
    payload_sha256: createHash("sha256").update(payload_json).digest("hex") };
};
function synthetic(edit: (data: any) => void = () => {}): any {
  const data = JSON.parse(oldEnvelope().payload_json);
  data.source.world = { ...data.source.world, source_commit: PRE_SCALE_SOURCE, years: 4, model: "qwen3:8b" };
  Object.assign(data.interpretation, { pre_scale_arm: "efficiency:parameters", plan_sha256: PRE_SCALE_PLAN,
    scope: PRE_SCALE_FOUNDRY_SCOPE, development_only: true, selection_is_not_recomputed_by_viewer: true,
    original_audit_content_sha256: "a".repeat(64), synthetic_fixture_not_scientific_evidence: true });
  for (const [index, row] of data.systems.entries()) {
    row.evidence_label = `SYNTHETIC QA / ROW ${index}`;
    for (const run of row.runs) {
      run.seed = 41001;
      run.frames = Array.from({ length: 4 }, (_, year) => ({ ...structuredClone(run.frames[0]), year: year + 1 }));
      run.events = run.events.filter((event: any) => event.year <= 4);
    }
  }
  edit(data); return seal(data);
}

describe("pre-scale closed-record Foundry channel", () => {
  it("allows exactly eight explicit same-origin arm files", () => {
    expect(PRE_SCALE_ARMS).toHaveLength(8);
    expect(preScaleFoundryArm("")).toBeNull();
    for (const arm of PRE_SCALE_ARMS) {
      expect(preScaleFoundryArm(`?pre-scale-arm=${encodeURIComponent(arm)}`)).toBe(arm);
      expect(preScaleFoundryFile(arm)).toBe(`./data/pre-scale-foundry-v1/${arm.replace(":", "--")}.json`);
    }
    for (const query of ["?pre-scale-arm=", "?pre-scale-arm=https://example.com/run.json",
      "?pre-scale-arm=../../old", "?pre-scale-arm=throughput:parameters&pre-scale-arm=efficiency:parameters"]) {
      expect(() => preScaleFoundryArm(query)).toThrow();
    }
  });
  it("preserves a labelled, checksum-verified development envelope", async () => {
    const lab = await parsePreScaleFoundry(synthetic(), "efficiency:parameters");
    expect(lab.systems[0]!.evidence_label).toContain("SYNTHETIC QA");
    expect(lab.systems[0]!.runs[0]!.frames).toHaveLength(4);
    expect(lab.interpretation.development_only).toBe(true);
  });
  it("does not silently load the older study into the pre-scale channel", async () => {
    await expect(parseNativeLab(oldEnvelope())).resolves.toBeDefined();
    await expect(parsePreScaleFoundry(oldEnvelope(), "efficiency:parameters")).rejects.toThrow();
  });
  it.each(["source", "plan", "arm", "horizon", "model", "audit", "scope", "selection", "label",
    "seed", "year", "short-complete"])("rejects correctly rehashed %s mismatch", async kind => {
    const value = synthetic(data => {
      if (kind === "source") data.source.world.source_commit = "0".repeat(40);
      if (kind === "plan") data.interpretation.plan_sha256 = "0".repeat(64);
      if (kind === "arm") data.interpretation.pre_scale_arm = "throughput:parameters";
      if (kind === "horizon") data.source.world.years = 2;
      if (kind === "model") data.source.world.model = "different-model";
      if (kind === "audit") data.interpretation.original_audit_content_sha256 = null;
      if (kind === "scope") data.interpretation.scope = "live-heartbeat";
      if (kind === "selection") data.interpretation.selection_is_not_recomputed_by_viewer = false;
      if (kind === "label") data.systems[0].evidence_label = 17;
      if (kind === "seed") data.systems[0].runs[0].seed = 51001;
      if (kind === "year") data.systems[0].runs[0].frames[0].year = 2;
      if (kind === "short-complete") data.systems[0].runs[0].frames.pop();
    });
    await expect(parsePreScaleFoundry(value, "efficiency:parameters")).rejects.toThrow();
  });
  it("retains a failed policy without fabricating researcher frames or zero loss", async () => {
    const lab = await parsePreScaleFoundry(synthetic(data => {
      data.systems[0].status = "failed"; data.systems[0].native_loss = null;
      data.systems[0].runs = []; data.systems[0].technical_failures = [{ error: "SYNTHETIC" }];
    }), "efficiency:parameters");
    expect(lab.systems[0]!.runs).toEqual([]);
    expect(lab.systems[0]!.native_loss).toBeNull();
  });
});
