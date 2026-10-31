import { readFileSync, readdirSync } from "node:fs";
import { describe, expect, it } from "vitest";

const root = new URL("../", import.meta.url);
describe("English game interface", () => {
  it("declares English on every game page", () => {
    for (const file of readdirSync(root).filter(name => name.endsWith(".html"))) {
      expect(readFileSync(new URL(file, root), "utf8"), file).toContain('<html lang="en">');
    }
  });
  it.each(["native.html", "generative.html", "src/native.ts", "src/generative.ts"])("keeps %s UI copy in English", file => {
    // Imported scientific evidence is preserved verbatim, not translated.
    expect(readFileSync(new URL(file, root), "utf8")).not.toMatch(/[\u3040-\u30ff\u3400-\u9fff]/u);
  });
  it("identifies the foundry scene as art and record inspection, not live simulation", () => {
    const html = readFileSync(new URL("native.html", root), "utf8");
    expect(html).toContain("ART / NOT SIMULATION STATE");
    expect(html).toContain("READ ONLY");
    expect(html).toContain("NO LIVE INSTALLATION");
    expect(html).toContain('id="deck-summary"');
    expect(html).toContain('id="deck-focus"');
    expect(html).not.toContain("Rewire institutions.");
  });
  it("uses original self-contained crisp vector art without remote resources or scripts", () => {
    const svg = readFileSync(new URL("public/assets/noctiluca/production/native-foundry-control-room.svg", root), "utf8");
    expect(svg).toContain('viewBox="0 0 640 280"');
    expect(svg).toContain('shape-rendering="crispEdges"');
    expect(svg).not.toMatch(/<(?:script|foreignObject|image)\b|\bon\w+=/i);
    for (const [, ref] of svg.matchAll(/href="([^"]+)"/g)) expect(ref).toMatch(/^#/);
  });
});
