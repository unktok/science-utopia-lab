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
});
