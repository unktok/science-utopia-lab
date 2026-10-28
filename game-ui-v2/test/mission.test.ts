import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { parseMissionBundle, verifyMissionBundle } from "../src/missionContract";

const verifiedUrl = new URL("../public/data/optimization-mission.snapshot.json", import.meta.url);
const syntheticUrl = new URL("../public/data/optimization-mission.synthetic.json", import.meta.url);
const pageUrl = new URL("../mission.html", import.meta.url);

async function raw(url = verifiedUrl): Promise<Record<string, unknown>> {
  return JSON.parse(await readFile(fileURLToPath(url), "utf8")) as Record<string, unknown>;
}

describe("optimization mission-control contract", () => {
  it("verifies the result-blind, commit-pinned registry snapshot", async () => {
    const bundle = parseMissionBundle(await raw());
    await expect(verifyMissionBundle(bundle)).resolves.toBeUndefined();
    expect(bundle.truth_status).toBe("verified_snapshot");
    expect(bundle.progress.logical_registered).toBe(27);
    expect(bundle.progress.logical_capacity).toBe(45);
    expect(bundle.arms).toHaveLength(3);
    expect(bundle.winner_freeze.status).toBe("not_frozen");
    expect(bundle.held_out).toMatchObject({ status: "locked", registry_exists: false, registered_runs: 0 });
  });

  it("keeps synthetic states in a separately labeled fixture", async () => {
    const bundle = parseMissionBundle(await raw(syntheticUrl));
    await expect(verifyMissionBundle(bundle)).resolves.toBeUndefined();
    expect(bundle.truth_status).toBe("synthetic");
    expect(bundle.disclosure).toContain("SYNTHETIC");
  });

  it("fails closed on hash mutation and held-out unlocking", async () => {
    const changed = await raw();
    (changed.progress as { logical_registered: number }).logical_registered = 45;
    await expect(verifyMissionBundle(parseMissionBundle(changed))).rejects.toThrow(/SHA-256 mismatch/);
    const leaked = await raw();
    (leaked.held_out as { registry_exists: boolean }).registry_exists = true;
    expect(() => parseMissionBundle(leaked)).toThrow(/firewall must remain locked/);
  });

  it("provides keyboard navigation and explicit claim boundaries", async () => {
    const html = await readFile(fileURLToPath(pageUrl), "utf8");
    expect(html).toContain('class="skip-link"');
    expect(html).toContain('id="arm-grid"');
    expect(html).toContain('role="status"');
    expect(html).toContain("NO RESULT INFERENCE");
    expect(html).toContain("HELD-OUT VAULT");
    expect(html).toContain("PHYSICAL ≠ LOGICAL");
  });
});
