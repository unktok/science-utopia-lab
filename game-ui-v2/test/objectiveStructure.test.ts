import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { objectiveStructureFixture } from "../src/objectiveStructureFixture";
import {
  OBJECTIVE_IDS, parseObjectiveStructureReport, parseObjectiveStructureReceipt, representativeRow, structuralRowState, verifyFixtureReport,
} from "../src/objectiveStructureContract";

describe("objective-conditioned native structure viewer contract", () => {
  it("accepts only the explicitly classified, hash-bound fixture channel", async () => {
    const fixture = await objectiveStructureFixture();
    const parsed = await verifyFixtureReport(fixture);
    expect(parsed.arms[OBJECTIVE_IDS[0]].selection.tie_count).toBe(2);
    expect(parsed.arms[OBJECTIVE_IDS[0]].loss_path).toEqual([-3, -4, -4, null]);
    expect(parsed.arms[OBJECTIVE_IDS[0]].binding.initial_system).not.toHaveProperty("fingerprint");
    expect(parsed.arms[OBJECTIVE_IDS[0]].rows[0]!.draw!.suggestion.candidate).not.toHaveProperty("fingerprint");
    expect(parsed.arms[OBJECTIVE_IDS[0]].rows[0]!.physical_proof!.measurement.system_fingerprint).toBe("2".repeat(64));
    expect(() => parseObjectiveStructureReport(fixture, "actual")).toThrow("actual channel rejects");
  });

  it("retains a zero-draw generation failure instead of fabricating two failed candidates", async () => {
    const parsed = parseObjectiveStructureReport(await objectiveStructureFixture(), "fixture");
    const row = parsed.arms[OBJECTIVE_IDS[0]].rows[3]!;
    expect(row.status).toBe("generation-failure");
    expect(row.draw).toBeNull();
    expect(row.cross_objective_losses[OBJECTIVE_IDS[0]]).toBeNull();
    expect(parsed.arms[OBJECTIVE_IDS[0]].generation_failures).toHaveLength(1);
  });

  it("keeps an unavailable cross-score null with its actual reason while preserving own loss", async () => {
    const parsed = parseObjectiveStructureReport(await objectiveStructureFixture(), "fixture");
    const row = parsed.arms[OBJECTIVE_IDS[0]].rows[2]!;
    expect(row.status).toBe("complete");
    expect(row.cross_objective_losses[OBJECTIVE_IDS[0]]).toBe(-4);
    expect(row.cross_objective_losses[OBJECTIVE_IDS[1]]).toBeNull();
    expect(row.loss_evaluations![OBJECTIVE_IDS[1]].rejected_runs[0].reason).toContain("other objective");
  });

  it("selects the exact later best observation when repeated systems have stochastic losses", async () => {
    const parsed = parseObjectiveStructureReport(await objectiveStructureFixture(), "fixture");
    const objectiveArm = parsed.arms[OBJECTIVE_IDS[0]];
    const [earlierSameSystem, exactRepresentative, equalCostTie] = objectiveArm.rows;
    expect(earlierSameSystem!.physical_proof!.measurement.system_fingerprint).toBe(exactRepresentative!.physical_proof!.measurement.system_fingerprint);
    expect(earlierSameSystem!.cross_objective_losses[OBJECTIVE_IDS[0]]).toBe(-3);
    expect(exactRepresentative!.cross_objective_losses[OBJECTIVE_IDS[0]]).toBe(-4);
    expect(representativeRow(objectiveArm)).toBe(exactRepresentative);
    expect(structuralRowState(earlierSameSystem!, objectiveArm)).toBe("complete");
    expect(structuralRowState(exactRepresentative!, objectiveArm)).toBe("selected");
    expect(structuralRowState(equalCostTie!, objectiveArm)).toBe("tie");
    expect(objectiveArm.selection.tied_observation_ids).toEqual([
      exactRepresentative!.observation!.observation_id,
      equalCostTie!.observation!.observation_id,
    ]);
    expect(parsed.selected_cross_objective_matrix[OBJECTIVE_IDS[0]]![OBJECTIVE_IDS[1]]).toBe(1.2);
  });

  it("rejects numeric penalties, selection drift, and graph count drift", async () => {
    const failurePenalty = structuredClone(await objectiveStructureFixture());
    failurePenalty.arms[OBJECTIVE_IDS[0]].rows[3]!.cross_objective_losses[OBJECTIVE_IDS[0]] = 999;
    expect(() => parseObjectiveStructureReport(failurePenalty, "fixture")).toThrow("path differs");

    const selection = structuredClone(await objectiveStructureFixture());
    selection.arms[OBJECTIVE_IDS[0]].selection.best_loss = -99;
    expect(() => parseObjectiveStructureReport(selection, "fixture")).toThrow("best loss differs");

    const graph = structuredClone(await objectiveStructureFixture());
    graph.arms[OBJECTIVE_IDS[0]].rows[0]!.graph_changes!.vs_parent.counts.nodes_added = 8;
    expect(() => parseObjectiveStructureReport(graph, "fixture")).toThrow("count differs");

    const fingerprint = structuredClone(await objectiveStructureFixture());
    fingerprint.arms[OBJECTIVE_IDS[0]].rows[0]!.observation!.metadata.system_fingerprint = "8".repeat(64);
    expect(() => parseObjectiveStructureReport(fingerprint, "fixture")).toThrow("fingerprint bindings differ");

    const identity = structuredClone(await objectiveStructureFixture());
    identity.arms[OBJECTIVE_IDS[0]].selection.representative_observation_id = identity.arms[OBJECTIVE_IDS[0]].rows[0]!.observation!.observation_id;
    expect(() => parseObjectiveStructureReport(identity, "fixture")).toThrow("earliest exact tied row");

    const reusedIdentity = structuredClone(await objectiveStructureFixture());
    reusedIdentity.arms[OBJECTIVE_IDS[0]].rows[1]!.observation!.observation_id = reusedIdentity.arms[OBJECTIVE_IDS[0]].rows[0]!.observation!.observation_id;
    expect(() => parseObjectiveStructureReport(reusedIdentity, "fixture")).toThrow("reuse observation or suggestion identity");

    const suggestionMismatch = structuredClone(await objectiveStructureFixture());
    suggestionMismatch.arms[OBJECTIVE_IDS[0]].rows[1]!.observation!.suggestion_id = "wrong-suggestion";
    expect(() => parseObjectiveStructureReport(suggestionMismatch, "fixture")).toThrow("observation/suggestion identity differs");
  });

  it("rejects a completed label without all eight clean worlds", async () => {
    const changed = structuredClone(await objectiveStructureFixture());
    changed.status = "complete";
    expect(() => parseObjectiveStructureReport(changed, "fixture")).toThrow("eight clean worlds");
  });

  it("binds an actual export receipt to report content and exact file identity", async () => {
    const report = await objectiveStructureFixture();
    const receipt = {
      schema: "scienceutopia.native-objective-structure-ui-export.v8",
      report_file: "fixture.json", report_file_sha256: "a".repeat(64),
      report_content_sha256: report.content_sha256, classification: report.classification,
      exported_without_transform: true,
    };
    expect(parseObjectiveStructureReceipt(receipt, report, "fixture.json").report_file_sha256).toBe("a".repeat(64));
    expect(() => parseObjectiveStructureReceipt({ ...receipt, report_content_sha256: "b".repeat(64) }, report, "fixture.json")).toThrow("does not bind");
  });

  it("keeps the page English and the research boundary visible", () => {
    const html = readFileSync(new URL("../objective-structure.html", import.meta.url), "utf8");
    for (const phrase of ["OBJECTIVE SWITCHYARD", "DEVELOPMENT — NOT HELD OUT", "NO BENEFIT GUARANTEE", "FIXED QWEN3:8B RESEARCHERS", "EXTERNAL CODEX SOURCE AUTHORSHIP"]) expect(html).toContain(phrase);
    expect(html).not.toMatch(/[\u3040-\u30ff\u3400-\u9fff]/u);
  });

  it("ships a local browser-QA harness that rejects job dispatch and binds actual report bytes", () => {
    const harness = readFileSync(new URL("../scripts/verify-objective-structure-browser.mjs", import.meta.url), "utf8");
    expect(harness).toContain('request.method !== "GET"');
    expect(harness).toContain("receipt.report_file_sha256 !== sha256(bytes)");
    expect(harness).toContain('no_job_dispatch: true');
    expect(harness).toContain('width: 390, height: 844');
    expect(harness).not.toMatch(/fetch\([^\n]+method:\s*["']POST/);
  });
});
