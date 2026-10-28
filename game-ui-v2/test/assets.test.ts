import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { parseAssetPack } from "../src/replay";

const root = new URL("../public/", import.meta.url);
const manifestUrl = new URL("assets/noctiluca/asset-pack.json", root);

const PALETTE = new Set([
  "#070814", "#10142A", "#1A2140", "#2A3560",
  "#46527A", "#6A769A", "#9EA8C2", "#EEE9D8",
  "#39F5C8", "#2DD4FF", "#4F7CFF", "#A86BFF",
  "#F653D8", "#FF617D", "#FFC857", "#B7F34A",
  "#382330", "#704154", "#A85F62", "#D88E70",
  "#F1BD91", "#F7DEC0", "#6E4C2E", "#B07A44",
]);

const EXPECTED: Record<string, { kind: "researcher" | "institution" | "flow" | "environment"; width: number; height: number }> = {
  researcher_early: { kind: "researcher", width: 24, height: 32 },
  researcher_pi: { kind: "researcher", width: 24, height: 32 },
  researcher_reviewer: { kind: "researcher", width: 24, height: 32 },
  researcher_editor: { kind: "researcher", width: 24, height: 32 },
  institution_lab: { kind: "institution", width: 96, height: 80 },
  institution_review: { kind: "institution", width: 96, height: 80 },
  institution_publication: { kind: "institution", width: 96, height: 80 },
  institution_funding: { kind: "institution", width: 96, height: 80 },
  flow_data: { kind: "flow", width: 8, height: 8 },
  flow_paper: { kind: "flow", width: 8, height: 8 },
  flow_review: { kind: "flow", width: 8, height: 8 },
  flow_funding: { kind: "flow", width: 8, height: 8 },
  flow_citation: { kind: "flow", width: 8, height: 8 },
  flow_policy: { kind: "flow", width: 8, height: 8 },
  workflow_submission: { kind: "institution", width: 32, height: 32 },
  workflow_review: { kind: "institution", width: 32, height: 32 },
  workflow_publication: { kind: "institution", width: 32, height: 32 },
  workflow_funding: { kind: "institution", width: 32, height: 32 },
  token_manuscript: { kind: "flow", width: 10, height: 10 },
  token_review_seal: { kind: "flow", width: 10, height: 10 },
  token_decision: { kind: "flow", width: 10, height: 10 },
  token_application: { kind: "flow", width: 10, height: 10 },
  token_grant: { kind: "flow", width: 10, height: 10 },
  station_manuscript: { kind: "institution", width: 32, height: 24 },
  station_review: { kind: "institution", width: 32, height: 24 },
  station_application: { kind: "institution", width: 32, height: 24 },
  station_decision: { kind: "institution", width: 32, height: 24 },
  station_award: { kind: "institution", width: 32, height: 24 },
  ambient_courier_drone: { kind: "environment", width: 16, height: 8 },
};

async function loadPack() {
  return parseAssetPack(JSON.parse(await readFile(fileURLToPath(manifestUrl), "utf8")));
}

describe("NOCTILUCA production pixel assets", () => {
  it("maps every required key to its exact fixed-grid production SVG", async () => {
    const pack = await loadPack();
    expect(pack.version).toBe("noctiluca-production-v0.5");
    expect(pack.palette).toBe("noctiluca-24-v0.1");
    expect(new Set(pack.images.map((image) => image.key))).toEqual(new Set(Object.keys(EXPECTED)));
    expect(new Set(pack.images.map((image) => image.url)).size).toBe(pack.images.length);
    for (const image of pack.images) {
      expect(image).toMatchObject(EXPECTED[image.key]!);
      expect(image.url).toBe(`/assets/noctiluca/production/${image.key.replaceAll("_", "-")}.svg`);
      if (image.kind === "researcher") expect(image.frames).toEqual({ frameWidth: 24, frameHeight: 32, end: 5 });
    }
  });

  it("uses only palette colours and integer-aligned rectangles", async () => {
    const pack = await loadPack();
    for (const image of pack.images) {
      const assetUrl = new URL(image.url.replace(/^\//, ""), root);
      const svg = await readFile(fileURLToPath(assetUrl), "utf8");
      const sourceWidth = image.frames ? image.frames.frameWidth * (image.frames.end + 1) : image.width;
      const sourceHeight = image.frames ? image.frames.frameHeight : image.height;
      expect(svg, image.key).toMatch(new RegExp(`<svg[^>]+width="${sourceWidth}"[^>]+height="${sourceHeight}"[^>]+viewBox="0 0 ${sourceWidth} ${sourceHeight}"`));
      expect(svg, image.key).toContain('shape-rendering="crispEdges"');
      expect(svg, image.key).not.toMatch(/<(?:path|circle|ellipse|polygon|polyline|line|image|filter|linearGradient|radialGradient)\b/i);
      expect(svg, image.key).not.toMatch(/\b(?:transform|opacity|style|stroke|mask|clip-path)=/i);

      const colours = [...svg.matchAll(/#[0-9A-Fa-f]{6}/g)].map((match) => match[0].toUpperCase());
      expect(colours.length, `${image.key} must contain visible palette marks`).toBeGreaterThan(0);
      expect(colours.filter((colour) => !PALETTE.has(colour)), image.key).toEqual([]);

      const geometry = [...svg.matchAll(/\b(?:x|y|width|height)="([^"]+)"/g)].map((match) => match[1]!);
      expect(geometry.every((value) => /^\d+$/.test(value)), `${image.key} contains non-integer geometry`).toBe(true);
    }
  });
});
