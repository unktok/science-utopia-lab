import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { canonicalHash, webCanonicalHash } from "../src/hash";
import { parseAssetPack, parseReplayV2 } from "../src/replay";
import { replaySource } from "../src/source";

const fixtureUrl = new URL("../public/data/vertical-slice.replay.json", import.meta.url);
const assetPackUrl = new URL("../public/assets/noctiluca/asset-pack.json", import.meta.url);
const campaignUrl = new URL("../public/data/completed-campaign.replay.json", import.meta.url);

async function fixture(): Promise<unknown> {
  return JSON.parse(await readFile(fileURLToPath(fixtureUrl), "utf8"));
}

describe("replay-view v2 contract", () => {
  it("loads the verified completed campaign bundle", async () => {
    const raw = JSON.parse(await readFile(fileURLToPath(campaignUrl), "utf8"));
    const replay = parseReplayV2(raw);
    expect(replay.metadata).toMatchObject({
      source_kind: "verified_commit_pinned_campaign_run",
      campaign_id: "first-closed-loop-engineering",
      campaign_revision: "9a10029807d5",
      source_commit: "0b733df425405f5e2eeb953cff2a7288f13f5af9",
    });
    expect(replay.canonical.events).toHaveLength(71);
    expect(replay.projection.frames).toHaveLength(72);
    expect(replay.canonical.entities.researchers).toHaveLength(12);
    expect(replay.canonical.entities.institutions).toHaveLength(3);
    expect(replay.choreography.flows).toHaveLength(8);
    expect(replay.choreography.workflow_nodes).toHaveLength(4);
    expect(replay.choreography.epistemic_flows).toHaveLength(20);
    expect(replay.choreography.epistemic_flows.reduce<Record<string, number>>((counts, flow) => {
      counts[flow.flow_kind] = (counts[flow.flow_kind] ?? 0) + 1;
      return counts;
    }, {})).toEqual({ manuscript: 2, review: 4, decision: 2, award: 2, application: 10 });
    expect(replay.choreography.epistemic_flows.every((flow) => flow.path.every((point) => Number.isInteger(point.x) && Number.isInteger(point.y)))).toBe(true);
    expect(replay.choreography.workstations).toHaveLength(11);
    expect(replay.choreography.interior_activities).toHaveLength(20);
    expect(replay.ambient.effects.every((effect) => effect.truth_status === "ambient" && effect.derived_from_event_ids.length === 0)).toBe(true);
    expect(replay.choreography.actions).toHaveLength(56);
    expect(replay.choreography.chapters).toHaveLength(9);
    expect(replay.choreography.time_compression).toMatchObject({
      kind: "deterministic-stage-compression",
      canonical_event_count: 71,
      duration_ms: 48_000,
    });
    expect(replay.choreography.actions.reduce<Record<string, number>>((counts, action) => {
      counts[action.action_type] = (counts[action.action_type] ?? 0) + 1;
      return counts;
    }, {})).toEqual({ move: 36, write: 2, review: 4, read: 2, receive: 2, apply: 10 });
    expect(replay.choreography.actions.every((action) => (
      action.path.length >= 2
      && action.path.every((point) => Number.isInteger(point.x) && Number.isInteger(point.y))
    ))).toBe(true);
    const factTimes = replay.canonical.events.map((event) => event.logical_timestamp_ms);
    expect(factTimes).toEqual([...factTimes].sort((left, right) => left - right));
    expect(replay.projection.frames.slice(1).map((frame) => frame.logical_timestamp_ms)).toEqual(factTimes);
    expect(await webCanonicalHash(replay.canonical.raw_events)).toBe(replay.web_stream_hash);
    expect(replay.canonical.entities.researchers.every((entity) => entity.x >= 0 && entity.x <= 480)).toBe(true);
  });

  it("only resolves allowlisted replay aliases and defaults to campaign", () => {
    expect(replaySource("")).toEqual({ key: "campaign", url: "/data/completed-campaign.replay.json" });
    expect(replaySource("?replay=synthetic")).toEqual({ key: "synthetic", url: "/data/vertical-slice.replay.json" });
    expect(() => replaySource("?replay=https://attacker.invalid/raw.json")).toThrow(/Unknown replay source/);
  });

  it("loads the deterministic vertical slice with all six flow types", async () => {
    const replay = parseReplayV2(await fixture());
    expect(replay.choreography.duration_ms).toBe(48_000);
    expect(replay.canonical.events).toHaveLength(16);
    expect(replay.canonical.entities.researchers).toHaveLength(4);
    expect(replay.canonical.entities.institutions).toHaveLength(4);
    expect(new Set(replay.choreography.flows.map((flow) => flow.flow_type))).toEqual(new Set([
      "data", "paper", "review", "funding", "citation", "policy",
    ]));
    expect(replay.choreography.flows.filter((flow) => flow.flow_type === "paper")).toHaveLength(2);
    expect(replay.choreography.actions).toHaveLength(17);
    expect(new Set(replay.choreography.actions.map((action) => action.actor_entity_id))).toEqual(new Set([
      "researcher:aya", "researcher:mino", "researcher:sol", "researcher:iren",
    ]));
    expect(replay.choreography.flows.every((flow) => flow.truth_status === "derived" && flow.derived_from_event_ids.length > 0)).toBe(true);
    expect(replay.choreography.actions.every((action) => action.truth_status === "derived" && action.derived_from_event_ids.length > 0)).toBe(true);
    const publication = replay.choreography.actions.find((action) => action.action_type === "publish");
    expect(publication).toMatchObject({ actor_entity_id: "researcher:iren", truth_status: "derived" });
    expect(replay.canonical.events.find((event) => event.id === publication?.derived_from_event_ids[0])?.kind).toBe("paper.decided");
    expect(replay.ambient.effects.every((effect) => effect.truth_status === "ambient" && effect.derived_from_event_ids.length === 0)).toBe(true);
  });

  it("recomputes the declared canonical event-stream hash", async () => {
    const replay = parseReplayV2(await fixture());
    expect(await canonicalHash(replay.canonical.raw_events)).toBe(replay.stream_hash);
  });

  it("joins choreography placements without mutating canonical entities", async () => {
    const replay = parseReplayV2(await fixture());
    const aya = replay.canonical.entities.researchers.find((row) => row.id === "researcher:aya");
    expect(aya).toMatchObject({ x: 144, y: 164, asset_key: "researcher_early" });
    const bureau = replay.canonical.entities.institutions.find((row) => row.id.includes("funding-bureau"));
    expect(bureau).toMatchObject({ x: 252, y: 222, asset_key: "institution_funding" });
    const publication = replay.canonical.entities.institutions.find((row) => row.id.includes("publication-spine"));
    expect(publication).toMatchObject({ x: 420, y: 238, asset_key: "institution_publication" });
    const iren = replay.canonical.entities.researchers.find((row) => row.id === "researcher:iren");
    expect(iren).toMatchObject({ x: 426, y: 252, asset_key: "researcher_editor" });
  });

  it("rejects a derived flow without canonical evidence", async () => {
    const raw = await fixture() as { choreography: { flows: Array<{ derived_from_event_ids: string[] }> } };
    raw.choreography.flows[0]!.derived_from_event_ids = [];
    expect(() => parseReplayV2(raw)).toThrow(/requires canonical evidence references/);
  });

  it("rejects an actor action without canonical evidence", async () => {
    const raw = await fixture() as { choreography: { actions: Array<{ derived_from_event_ids: string[] }> } };
    raw.choreography.actions[0]!.derived_from_event_ids = [];
    expect(() => parseReplayV2(raw)).toThrow(/requires canonical evidence references/);
  });

  it("rejects a cinematic route whose integer path misses its declared endpoint", async () => {
    const raw = await fixture() as { choreography: { actions: Array<{ path?: Array<{ x: number; y: number }> }> } };
    const action = raw.choreography.actions[0]!;
    action.path = [{ x: 1, y: 1 }, { x: 2, y: 2 }];
    expect(() => parseReplayV2(raw)).toThrow(/path endpoints must match start\/end/);
  });

  it("rejects an epistemic route whose claimed kind contradicts its canonical event", async () => {
    const raw = JSON.parse(await readFile(fileURLToPath(campaignUrl), "utf8")) as { choreography: { epistemic_flows: Array<{ flow_kind: string }> } };
    raw.choreography.epistemic_flows[0]!.flow_kind = "award";
    expect(() => parseReplayV2(raw)).toThrow(/semantic mismatch/);
  });

  it("rejects an interior activity whose task contradicts its canonical event", async () => {
    const raw = JSON.parse(await readFile(fileURLToPath(campaignUrl), "utf8")) as { choreography: { interior_activities: Array<{ activity_type: string }> } };
    raw.choreography.interior_activities[0]!.activity_type = "receive";
    expect(() => parseReplayV2(raw)).toThrow(/semantic mismatch/);
  });

  it("rejects an actor action attached to an institution", async () => {
    const raw = await fixture() as { choreography: { actions: Array<{ actor_entity_id: string }> } };
    raw.choreography.actions[0]!.actor_entity_id = "institution:noctiluca-knowledge-lab:244054c6";
    expect(() => parseReplayV2(raw)).toThrow(/unknown researcher actor/);
  });

  it("rejects ambient presentation that claims evidence", async () => {
    const raw = await fixture() as { ambient: { effects: Array<{ derived_from_event_ids: string[] }> } };
    raw.ambient.effects[0]!.derived_from_event_ids = ["invented-event"];
    expect(() => parseReplayV2(raw)).toThrow(/must be ambient without evidence references/);
  });
});

describe("asset pack contract", () => {
  it("contains every asset required by the vertical slice", async () => {
    const pack = parseAssetPack(JSON.parse(await readFile(fileURLToPath(assetPackUrl), "utf8")));
    expect(new Set(pack.images.map((image) => image.key))).toEqual(new Set([
      "researcher_early", "researcher_pi", "researcher_reviewer", "researcher_editor",
      "institution_lab", "institution_review", "institution_publication", "institution_funding",
      "flow_data", "flow_paper", "flow_review", "flow_funding", "flow_citation", "flow_policy",
      "workflow_submission", "workflow_review", "workflow_publication", "workflow_funding",
      "token_manuscript", "token_review_seal", "token_decision", "token_application", "token_grant",
      "station_manuscript", "station_review", "station_application", "station_decision", "station_award",
      "ambient_courier_drone",
    ]));
  });

  it("accepts grid-authored images and optional frame metadata", () => {
    expect(parseAssetPack({
      version: "v1",
      palette: "noctiluca-24-v0.1",
      images: [
        { key: "researcher_early", url: "/a.png", kind: "researcher", width: 24, height: 32 },
        { key: "flow_data", url: "/b.png", kind: "flow", width: 32, height: 8, frames: { frameWidth: 8, frameHeight: 8, end: 3 } },
      ],
    }).images).toHaveLength(2);
  });

  it("rejects an unknown asset kind", () => {
    expect(() => parseAssetPack({ version: "v1", palette: "p", images: [{ key: "x", url: "/x", kind: "clipart", width: 1, height: 1 }] })).toThrow(/kind is unknown/);
  });
});
