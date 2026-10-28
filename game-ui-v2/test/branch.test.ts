import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { parseBranchManifest, verifyBranchBundle } from "../src/branch";
import { parseReplayV2 } from "../src/replay";

const data = (name: string): URL => new URL(`../public/data/${name}`, import.meta.url);
const json = async (name: string): Promise<unknown> => JSON.parse(await readFile(fileURLToPath(data(name)), "utf8"));

describe("canonical intervention branch bundle", () => {
  it("parses and verifies two streams plus their shared origin", async () => {
    const manifest = parseBranchManifest(await json("intervention-branches.manifest.json"));
    const replays = await Promise.all(manifest.branches.map(async (branch) => parseReplayV2(await json(branch.replay_url.split("/").at(-1)!))));

    await expect(verifyBranchBundle(manifest, [replays[0]!, replays[1]!])).resolves.toBeUndefined();
    expect(manifest.shared_origin.event_count).toBe(6);
    expect(manifest.empirical).toBe(false);
  });

  it("rejects a manifest that points to the wrong intervention", async () => {
    const manifest = parseBranchManifest(await json("intervention-branches.manifest.json"));
    const replays = await Promise.all(manifest.branches.map(async (branch) => parseReplayV2(await json(branch.replay_url.split("/").at(-1)!))));
    manifest.branches[0].intervention_event_id = replays[0]!.canonical.events[0]!.id;

    await expect(verifyBranchBundle(manifest, [replays[0]!, replays[1]!])).rejects.toThrow(/intervention event is absent/);
  });

  it("rejects a forged shared-origin hash", async () => {
    const manifest = parseBranchManifest(await json("intervention-branches.manifest.json"));
    const replays = await Promise.all(manifest.branches.map(async (branch) => parseReplayV2(await json(branch.replay_url.split("/").at(-1)!))));
    manifest.shared_origin.stream_hash = "0".repeat(64);

    await expect(verifyBranchBundle(manifest, [replays[0]!, replays[1]!])).rejects.toThrow(/common origin/);
  });
});
