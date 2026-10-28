import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { buildInstitutionalInteriorProjection, interiorAtCursor, INTERIOR_ROOM_IDS } from "../src/institutionInterior";
import { parseReplayV2 } from "../src/replay";

const campaignUrl = new URL("../public/data/completed-campaign.replay.json", import.meta.url);
const syntheticUrl = new URL("../public/data/vertical-slice.replay.json", import.meta.url);
const pageUrl = new URL("../index.html", import.meta.url);
const load = async (url = campaignUrl) => parseReplayV2(JSON.parse(await readFile(fileURLToPath(url), "utf8")));

describe("verified institutional interior projection", () => {
  it("binds every presentation scene to the exact canonical event and authoritative frame", async () => {
    const projection = buildInstitutionalInteriorProjection(await load());
    expect(projection.scenes).toHaveLength(71);
    expect(projection.scenes.every((scene) => (
      scene.evidence.truth_status === "authoritative_projection"
      && scene.presentation.truth_status === "presentation_only"
      && scene.evidence.frame.event_id === scene.evidence.event.id
      && scene.evidence.frame.cursor === scene.evidence.event.sequence + 1
    ))).toBe(true);
    expect(new Set(projection.scenes.map((scene) => scene.presentation.room_id))).toEqual(new Set(INTERIOR_ROOM_IDS));
  });

  it("reads actor and artifact state only from authoritative projection frames", async () => {
    const projection = buildInstitutionalInteriorProjection(await load());
    const review = interiorAtCursor(projection, 20_200)?.scene;
    expect(review?.evidence.event.kind).toBe("review.completed");
    expect(review?.evidence.frame.cursor).toBe(28);
    expect(review?.presentation).toMatchObject({ room_id: "review-room", pose: "review", packet_kind: "review", truth_status: "presentation_only" });
    expect(Object.values(review?.evidence.actor_states ?? {})[0]).toMatchObject({ active: true, balance: 40 });
    expect(Object.values(review?.evidence.artifact_states ?? {})[0]).toMatchObject({ status: "submitted" });
  });

  it("is invariant to cinematic choreography and ambient records", async () => {
    const replay = await load();
    const baseline = buildInstitutionalInteriorProjection(replay).scenes.map((scene) => [scene.evidence.event.id, scene.evidence.frame.cursor, scene.presentation]);
    replay.choreography.actions = [];
    replay.choreography.flows = [];
    replay.choreography.epistemic_flows = [];
    replay.choreography.interior_activities = [];
    replay.ambient.actors = [];
    replay.ambient.effects = [];
    expect(buildInstitutionalInteriorProjection(replay).scenes.map((scene) => [scene.evidence.event.id, scene.evidence.frame.cursor, scene.presentation])).toEqual(baseline);
  });

  it("fails closed for a synthetic source", async () => {
    const replay = await load(syntheticUrl);
    expect(() => buildInstitutionalInteriorProjection(replay)).toThrow(/verified commit-pinned/);
  });

  it("declares keyboard, truth, and responsive interior landmarks in the shell", async () => {
    const html = await readFile(fileURLToPath(pageUrl), "utf8");
    expect(html).toContain('id="institution-interiors"');
    expect(html).toContain('id="interior-deck-toggle"');
    expect(html).toContain("PRESENTATION-ONLY STAGE");
    expect(html).toContain("VERIFIED EVENT FEED");
    expect(html).toContain("I to toggle the institution interior deck");
    expect((html.match(/class="interior-room /g) ?? [])).toHaveLength(4);
  });
});
