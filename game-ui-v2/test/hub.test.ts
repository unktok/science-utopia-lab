import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { ARCOLOGY_MODES, currentBoundary, HUB_HREF } from "../src/arcologyNav";

const read = async (relative: string): Promise<string> => readFile(fileURLToPath(new URL(relative, import.meta.url)), "utf8");

describe("NOCTILUCA research-arcology hub", () => {
  it("declares three isolated destinations with explicit truth boundaries", () => {
    expect(HUB_HREF).toBe("./hub.html");
    expect(ARCOLOGY_MODES.map((mode) => [mode.id, mode.truth, mode.href])).toEqual([
      ["replay", "VERIFIED REPLAY", "./index.html?replay=campaign&motion=reduced"],
      ["sandbox", "SYNTHETIC SANDBOX", "./sandbox.html"],
      ["mission", "VERIFIED SNAPSHOT", "./mission.html"],
    ]);
    expect(new Set(ARCOLOGY_MODES.map((mode) => mode.href)).size).toBe(3);
  });

  it("reports alternate synthetic sources instead of preserving a verified label", () => {
    expect(currentBoundary("replay", "?replay=campaign").label).toBe("VERIFIED REPLAY");
    expect(currentBoundary("replay", "?replay=synthetic").label).toBe("SYNTHETIC REPLAY");
    expect(currentBoundary("mission", "?source=synthetic").label).toBe("SYNTHETIC UI FIXTURE");
    expect(currentBoundary("hub").label).toBe("PRESENTATION-ONLY TRANSIT");
  });

  it("keeps the hub presentation-only and outside scientific contracts", async () => {
    const source = await read("../src/hub.ts");
    expect(source).not.toMatch(/from ["'].\/(?:replay|missionContract|systemSandbox|types)["']/);
    expect(source).not.toContain("fetch(");
    expect(source).not.toContain("localStorage");
    expect(source).toContain("installArcologyRail(\"hub\")");
  });

  it("provides a semantic map, native doors, truth legend, and keyboard briefing", async () => {
    const html = await read("../hub.html");
    expect(html).toContain('class="skip-link"');
    expect(html).toContain('id="district-map"');
    expect(html).toContain('id="terminal-grid"');
    expect(html).toContain("ONE WORLD · THREE EVIDENCE BOUNDARIES");
    expect(html).toContain("PRESENTATION ONLY");
    expect(html).toContain("VERIFIED REPLAY");
    expect(html).toContain("SYNTHETIC SANDBOX");
    expect(html).toContain("VERIFIED SNAPSHOT");
    expect(html).toContain("ENTER");
    expect(html).toContain("REDUCE TRANSIT MOTION");
  });

  it("installs the shared truth rail on every destination", async () => {
    for (const [file, mode] of [["../src/main.ts", "replay"], ["../src/sandbox.ts", "sandbox"], ["../src/mission.ts", "mission"]] as const) {
      expect(await read(file)).toContain(`installArcologyRail("${mode}")`);
    }
  });
});
