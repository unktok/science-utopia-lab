import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { parseMissionBundle, verifyMissionBundle } from "../src/missionContract";
import { buildOptimizerObservatoryProjection } from "../src/optimizerObservatory";

const verifiedUrl = new URL("../public/data/optimization-mission.snapshot.json", import.meta.url);
const syntheticUrl = new URL("../public/data/optimization-mission.synthetic.json", import.meta.url);
const pageUrl = new URL("../index.html", import.meta.url);
const load = async (url = verifiedUrl) => parseMissionBundle(JSON.parse(await readFile(fileURLToPath(url), "utf8")));

describe("optimizer observatory", () => {
  it("projects the verified LossSpec → design → seed flow without exposing results", async () => {
    const bundle = await load();
    await expect(verifyMissionBundle(bundle)).resolves.toBeUndefined();
    const projection = buildOptimizerObservatoryProjection(bundle);
    expect(projection.truth_status).toBe("verified_snapshot");
    expect(projection.arms).toHaveLength(3);
    expect(projection.arms.every((arm) => arm.designs.length === 3)).toBe(true);
    expect(projection.arms.flatMap((arm) => arm.designs).flatMap((design) => design.seeds)).toHaveLength(27);
    expect(projection.arms.flatMap((arm) => arm.designs).flatMap((design) => design.seeds).every((seed) => seed.score.status === "not_observed" && seed.score.value === null)).toBe(true);
    expect(projection.winner_freeze).toMatchObject({ status: "not_frozen", frozen_arms: 0, required_arms: 3 });
    expect(projection.report.status).toBe("locked");
  });

  it("states that system design is optimized under LossSpec conditioning without inventing divergence", async () => {
    const projection = buildOptimizerObservatoryProjection(await load());
    expect(projection.metric_conditioning).toMatchObject({
      conditioning_variable: "loss_spec",
      optimized_variable: "system_design",
      registered_cross_arm_divergence: "not_observed",
    });
    expect(projection.metric_conditioning.note).toContain("not yet observed");
    expect(new Set(projection.arms.map((arm) => arm.designs[0]!.design_id)).size).toBe(1);
  });

  it("keeps the demo fixture visibly synthetic and equally result-blind", async () => {
    const bundle = await load(syntheticUrl);
    await expect(verifyMissionBundle(bundle)).resolves.toBeUndefined();
    const projection = buildOptimizerObservatoryProjection(bundle);
    expect(projection.truth_status).toBe("synthetic");
    expect(projection.source_kind).toBe("synthetic_optimization_mission_fixture");
    expect(projection.score_export.status).toBe("not_observed");
    expect(projection.winner_freeze.status).toBe("not_frozen");
  });

  it("types every spatial and cinematic choice as presentation-only", async () => {
    const projection = buildOptimizerObservatoryProjection(await load());
    expect(projection.presentation).toEqual({
      truth_status: "presentation_only",
      fields: ["district_layout", "facility_shape", "packet_routes", "packet_animation", "colour", "narrative_labels"],
    });
  });

  it("declares truth boundaries, keyboard access and optimization semantics in the city shell", async () => {
    const html = await readFile(fileURLToPath(pageUrl), "utf8");
    expect(html).toContain('id="optimizer-observatory"');
    expect(html).toContain('id="observatory-toggle"');
    expect(html).toContain("STATUS / REPORT / PROVENANCE ONLY");
    expect(html).toContain("Unexported scores are NOT OBSERVED");
    expect(html).toContain("O to open the optimizer observatory");
    expect(html).toContain("SYSTEM DESIGN FOUNDRY");
  });
});
