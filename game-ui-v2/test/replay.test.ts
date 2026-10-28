import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { canonicalHash } from "../src/hash";
import { parseAssetPack, parseReplayV2 } from "../src/replay";

const fixtureUrl = new URL("../public/data/vertical-slice.replay.json", import.meta.url);
const assetPackUrl = new URL("../public/assets/noctiluca/asset-pack.json", import.meta.url);

async function fixture(): Promise<unknown> {
  return JSON.parse(await readFile(fileURLToPath(fixtureUrl), "utf8"));
}

describe("replay-view v2 contract", () => {
  it("loads the deterministic six-flow vertical slice", async () => {
    const replay = parseReplayV2(await fixture());
    expect(replay.choreography.duration_ms).toBe(48_000);
    expect(replay.canonical.events).toHaveLength(14);
    expect(replay.canonical.entities.researchers).toHaveLength(3);
    expect(replay.canonical.entities.institutions).toHaveLength(3);
    expect(replay.choreography.flows.map((flow) => flow.flow_type)).toEqual([
      "data", "paper", "review", "funding", "citation", "policy",
    ]);
    expect(replay.choreography.actions).toHaveLength(15);
    expect(new Set(replay.choreography.actions.map((action) => action.actor_entity_id))).toEqual(new Set([
      "researcher:aya", "researcher:mino", "researcher:sol",
    ]));
    expect(replay.choreography.flows.every((flow) => flow.truth_status === "derived" && flow.derived_from_event_ids.length > 0)).toBe(true);
    expect(replay.choreography.actions.every((action) => action.truth_status === "derived" && action.derived_from_event_ids.length > 0)).toBe(true);
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
      "researcher_early", "researcher_pi", "researcher_reviewer",
      "institution_lab", "institution_review", "institution_publication", "institution_funding",
      "flow_data", "flow_paper", "flow_review", "flow_funding", "flow_citation", "flow_policy",
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
