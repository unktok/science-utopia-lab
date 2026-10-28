import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { buildEvidenceQuayProjection, cueAtCursor } from "../src/evidenceQuay";
import { parseReplayV2 } from "../src/replay";

const campaignUrl = new URL("../public/data/completed-campaign.replay.json", import.meta.url);
const syntheticUrl = new URL("../public/data/vertical-slice.replay.json", import.meta.url);
const pageUrl = new URL("../index.html", import.meta.url);
const load = async (url = campaignUrl) => parseReplayV2(JSON.parse(await readFile(fileURLToPath(url), "utf8")));

describe("Evidence Quay authoritative activity projection", () => {
  it("joins every canonical event to its exact authoritative frame", async () => {
    const replay = await load();
    const quay = buildEvidenceQuayProjection(replay);
    expect(quay.truth_status).toBe("verified_replay");
    expect(quay.cues).toHaveLength(71);
    expect(quay.cues.every((cue) => (
      cue.frame.event_id === cue.event.id
      && cue.frame.cursor === cue.event.sequence + 1
      && cue.motion.truth_status === "presentation_only"
    ))).toBe(true);
    expect(new Set(quay.cues.map((cue) => cue.activity))).toEqual(new Set([
      "arrival", "writing", "research", "review", "decision", "funding", "reporting", "year-close",
    ]));
    expect(new Set(quay.cues.map((cue) => cue.motion.packet_kind))).toEqual(new Set(["none", "paper", "knowledge", "review", "funding"]));
  });

  it("does not depend on cinematic choreography or ambient records", async () => {
    const replay = await load();
    const baseline = buildEvidenceQuayProjection(replay).cues.map((cue) => [cue.event.id, cue.frame.cursor, cue.activity, cue.motion]);
    replay.choreography.actions = [];
    replay.choreography.flows = [];
    replay.choreography.epistemic_flows = [];
    replay.choreography.interior_activities = [];
    replay.ambient.actors = [];
    replay.ambient.effects = [];
    expect(buildEvidenceQuayProjection(replay).cues.map((cue) => [cue.event.id, cue.frame.cursor, cue.activity, cue.motion])).toEqual(baseline);
  });

  it("fails closed for synthetic sources and mismatched projection frames", async () => {
    const synthetic = await load(syntheticUrl);
    expect(() => buildEvidenceQuayProjection(synthetic)).toThrow(/verified commit-pinned/);
    const replay = await load();
    replay.projection.frames[13]!.event_id = "forged-event";
    expect(() => buildEvidenceQuayProjection(replay)).toThrow(/no matching authoritative frame/);
  });

  it("uses cursor time only for presentation progress between recorded events", async () => {
    const quay = buildEvidenceQuayProjection(await load());
    const selected = cueAtCursor(quay, 20_200);
    expect(selected?.cue.event.kind).toBe("review.completed");
    expect(selected?.cue.frame.cursor).toBe(28);
    expect(selected?.progress).toBeGreaterThan(0);
    expect(selected?.progress).toBeLessThan(1);
  });

  it("exposes the truth boundary and keyboard target in the static shell", async () => {
    const html = await readFile(fileURLToPath(pageUrl), "utf8");
    expect(html).toContain('id="evidence-quay"');
    expect(html).toContain('id="quay-event"');
    expect(html).toContain("AUTHORITATIVE OPERATIONS");
    expect(html).toContain("PRESENTATION-ONLY");
    expect(html).toContain("Q to focus the Evidence Quay event");
  });
});
